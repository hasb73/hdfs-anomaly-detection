#!/usr/bin/env python3
"""
HDFS Real-Time Log Processor for EMR Production Environment
Reads HDFS DataNode logs, preprocesses them, and streams to Kafka for anomaly detection
"""
# Suppress urllib3 SSL warnings
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

import time
import re
import json
import sys
import os
from kafka import KafkaProducer
from typing import Dict, List, Optional
import threading
import logging
from datetime import datetime
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hdfs_log_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HDFSLogPreprocessor:
    """Preprocesses HDFS logs to remove dynamic content for anomaly detection"""
    
    def __init__(self):
        # Regex patterns for dynamic content removal
        self.patterns = {
            # Timestamp patterns
            'timestamp': r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}',
            
            # IP addresses (IPv4)
            'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            
            # Port numbers
            'port': r':\d{4,5}(?=\s|,|])',
            
            # Block IDs
            'block_id': r'blk_\d+_\d+',
            'block_pool': r'BP-\d+-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-\d+',
            
            # Client IDs
            'client_id': r'DFSClient_[A-Z_-]+\d+',
            
            # Server/Node IDs (UUIDs)
            'uuid': r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',
            
            # Hostnames
            'hostname': r'ip-\d+-\d+-\d+-\d+\.[\w-]+\.compute\.internal',
            
            # Numbers (bytes, durations, offsets)
            'bytes': r'bytes: \d+',
            'duration': r'duration\(ns\): \d+',
            'offset': r'offset: \d+',
            
            # Paths with dynamic components
            'volume_path': r'volume: [^,]*',
        }
        
        # Replacement tokens
        self.replacements = {
            'timestamp': 'TIMESTAMP',
            'ip_address': 'IP_ADDR',
            'port': ':PORT',
            'block_id': 'BLOCK_ID',
            'block_pool': 'BLOCK_POOL',
            'client_id': 'CLIENT_ID',
            'uuid': 'UUID',
            'hostname': 'HOSTNAME',
            'bytes': 'bytes: NUM',
            'duration': 'duration(ns): NUM',
            'offset': 'offset: NUM',
            'volume_path': 'volume: PATH',
        }
    
    def preprocess_log_line(self, log_line: str) -> str:
        """
        Preprocess a single log line to remove dynamic content
        
        Args:
            log_line: Raw HDFS log line
            
        Returns:
            Preprocessed log line with dynamic content replaced
        """
        if not log_line or not log_line.strip():
            return ""
        
        processed_line = log_line.strip()
        
        # Apply all preprocessing patterns
        for pattern_name, pattern in self.patterns.items():
            replacement = self.replacements[pattern_name]
            processed_line = re.sub(pattern, replacement, processed_line)
        
        # Additional cleanup for common dynamic patterns
        # Remove thread names with dynamic IDs
        processed_line = re.sub(r'\(DataXceiver for client [^)]+\)', '(DataXceiver for client CLIENT)', processed_line)
        
        # Normalize multiple spaces
        processed_line = re.sub(r'\s+', ' ', processed_line)
        
        return processed_line.strip()
    
    def extract_log_level(self, log_line: str) -> str:
        """Extract log level from log line"""
        # Common HDFS log levels
        for level in ['ERROR', 'WARN', 'INFO', 'DEBUG', 'TRACE', 'FATAL']:
            if f' {level} ' in log_line:
                return level
        return 'UNKNOWN'
    
    def is_relevant_log(self, log_line: str) -> bool:
        """
        Check if log line is relevant for anomaly detection
        
        Args:
            log_line: Raw log line
            
        Returns:
            True if log should be processed, False otherwise
        """
        if not log_line or not log_line.strip():
            return False
        
        # Only process log entries that contain block operations (blk_)
        # This focuses on block-level operations in HDFS
        if 'blk_' in log_line:
            return True
        
        return False

class HDFSLogTailer(FileSystemEventHandler):
    """Tails HDFS log files and processes new log entries"""
    
    def __init__(self, log_file_path: str, kafka_producer, preprocessor: HDFSLogPreprocessor, kafka_topic: str = "logs"):
        self.log_file_path = log_file_path
        self.kafka_producer = kafka_producer
        self.preprocessor = preprocessor
        self.kafka_topic = kafka_topic
        self.file_handle = None
        self.position = 0
        self.running = True
        
        # Statistics
        self.stats = {
            'lines_read': 0,
            'lines_processed': 0,
            'lines_sent_to_kafka': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # Open log file
        self._open_log_file()
    
    def _open_log_file(self):
        """Open the log file and seek to end"""
        try:
            if os.path.exists(self.log_file_path):
                self.file_handle = open(self.log_file_path, 'r')
                # Start from end of file for real-time processing
                self.file_handle.seek(0, 2)  # Seek to end
                self.position = self.file_handle.tell()
                logger.info(f"Opened log file: {self.log_file_path} (position: {self.position})")
            else:
                logger.error(f" Log file not found: {self.log_file_path}")
        except Exception as e:
            logger.error(f" Failed to open log file: {e}")
    
    def _close_log_file(self):
        """Close the log file"""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
    
    def read_new_lines(self):
        """Read new lines from the log file"""
        if not self.file_handle:
            return []
        
        try:
            # Read new content
            new_lines = []
            while True:
                line = self.file_handle.readline()
                if not line:
                    break
                new_lines.append(line.rstrip('\n\r'))
                self.stats['lines_read'] += 1
            
            return new_lines
        except Exception as e:
            logger.error(f" Error reading log file: {e}")
            self.stats['errors'] += 1
            return []
    
    def process_and_send_lines(self, lines: List[str]):
        """Process log lines and send relevant ones to Kafka"""
        for line in lines:
            try:
                # Check if line is relevant for anomaly detection
                if not self.preprocessor.is_relevant_log(line):
                    continue
                
                # Preprocess the log line
                processed_line = self.preprocessor.preprocess_log_line(line)
                
                if not processed_line:
                    continue
                
                # Extract metadata
                log_level = self.preprocessor.extract_log_level(line)
                
                # Create Kafka message
                message = {
                    'text': processed_line,
                    'original_text': line,
                    'log_level': log_level,
                    'source': 'hdfs_datanode',
                    'timestamp': datetime.now().isoformat(),
                    'node_type': 'datanode',
                    'label': None  # Will be determined by anomaly detection
                }
                
                # Send to Kafka
                future = self.kafka_producer.send(self.kafka_topic, value=message)
                future.get(timeout=10)  # Wait for confirmation
                
                self.stats['lines_sent_to_kafka'] += 1
                self.stats['lines_processed'] += 1
                
                # Log all processed entries (with level indication)
                if log_level in ['ERROR', 'WARN']:
                    logger.info(f"🚨 {log_level}: {processed_line[:100]}...")
                elif log_level in ['DEBUG', 'TRACE']:
                    logger.debug(f"🔍 {log_level}: {processed_line[:100]}...")
                else:
                    logger.debug(f"📝 {log_level}: {processed_line[:100]}...")
                
            except Exception as e:
                logger.error(f" Error processing line: {e}")
                self.stats['errors'] += 1
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and event.src_path == self.log_file_path:
            new_lines = self.read_new_lines()
            if new_lines:
                self.process_and_send_lines(new_lines)
    
    def start_initial_processing(self, lines_from_end: int = 0):
        """
        Process last N lines from the log file for context
        Set lines_from_end=0 to skip initial processing and only process new entries
        """
        if lines_from_end <= 0:
            logger.info("Skipping initial processing - will only process NEW log entries")
            return
            
        logger.info(f" Processing last {lines_from_end} lines for context...")
        
        try:
            if self.file_handle:
                # Read last N lines
                self.file_handle.seek(0, 0)  # Go to beginning
                all_lines = self.file_handle.readlines()
                recent_lines = all_lines[-lines_from_end:] if len(all_lines) > lines_from_end else all_lines
                
                # Process recent lines
                recent_lines = [line.rstrip('\n\r') for line in recent_lines]
                self.process_and_send_lines(recent_lines)
                
                # Return to end for real-time processing
                self.file_handle.seek(0, 2)
                
                logger.info(f" Processed {len(recent_lines)} recent log lines for context")
        except Exception as e:
            logger.error(f" Error during initial processing: {e}")
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        elapsed = time.time() - self.stats['start_time']
        return {
            **self.stats,
            'elapsed_seconds': elapsed,
            'lines_per_second': self.stats['lines_read'] / elapsed if elapsed > 0 else 0,
            'processing_rate': self.stats['lines_processed'] / elapsed if elapsed > 0 else 0
        }
    
    def stop(self):
        """Stop the log tailer"""
        self.running = False
        self._close_log_file()

class HDFSProductionLogProcessor:
    """Main class for HDFS log processing in production environment"""
    
    def __init__(self, 
                 log_file_path: str,
                 kafka_servers: str = "localhost:9092",
                 kafka_topic: str = "logs",
                 scoring_service_url: str = "http://localhost:8003"):
        self.log_file_path = log_file_path
        self.kafka_servers = kafka_servers
        self.kafka_topic = kafka_topic
        self.scoring_service_url = scoring_service_url
        
        self.producer = None
        self.preprocessor = HDFSLogPreprocessor()
        self.log_tailer = None
        self.observer = None
        self.running = False
        
        # Statistics reporting
        self.last_stats_time = time.time()
        self.stats_interval = 5  # Report stats every specified seconds
        
    def initialize_kafka(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                batch_size=16384,
                linger_ms=10,
                acks='all',
                retries=3
            )
            logger.info(f" Kafka producer initialized: {self.kafka_servers}")
            return True
        except Exception as e:
            logger.error(f" Kafka initialization failed: {e}")
            return False
    
    def check_scoring_service(self):
        """Check if scoring service is available"""
        try:
            response = requests.get(f"{self.scoring_service_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                logger.info(f" Scoring service healthy: {health['status']}")
                return True
            else:
                logger.warning(f" Scoring service unhealthy: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f" Scoring service check failed: {e}")
            return False
    
    def validate_log_file(self):
        """Validate that the log file exists and is readable"""
        if not os.path.exists(self.log_file_path):
            logger.error(f" Log file not found: {self.log_file_path}")
            return False
        
        if not os.access(self.log_file_path, os.R_OK):
            logger.error(f" Log file not readable: {self.log_file_path}")
            return False
        
        # Get file size
        file_size = os.path.getsize(self.log_file_path)
        logger.info(f"Log file found: {self.log_file_path} ({file_size:,} bytes)")
        return True
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f" Received signal {signum}, shutting down gracefully...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start_stats_reporter(self):
        """Start background thread for statistics reporting"""
        def report_stats():
            while self.running:
                time.sleep(self.stats_interval)
                if self.log_tailer and self.running:
                    stats = self.log_tailer.get_stats()
                    logger.info(f" Stats: {stats['lines_read']} read, "
                              f"{stats['lines_processed']} processed, "
                              f"{stats['lines_sent_to_kafka']} sent to Kafka, "
                              f"{stats['errors']} errors, "
                              f"{stats['processing_rate']:.1f} lines/sec")
        
        stats_thread = threading.Thread(target=report_stats, daemon=True)
        stats_thread.start()
        logger.info(f"Statistics reporter started (interval: {self.stats_interval}s)")
    
    def start(self, initial_lines: int = 0):
        """
        Start the HDFS log processor
        
        Args:
            initial_lines: Number of recent lines to process for context (0 = only new entries)
        """
        logger.info(" Starting HDFS Production Log Processor")
        logger.info("=" * 60)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Validate prerequisites
        if not self.validate_log_file():
            logger.error(" Log file validation failed")
            return False
        
        if not self.initialize_kafka():
            logger.error(" Kafka initialization failed")
            return False
        
        # Check scoring service (optional)
        self.check_scoring_service()
        
        # Initialize log tailer
        self.log_tailer = HDFSLogTailer(
            self.log_file_path,
            self.producer,
            self.preprocessor,
            self.kafka_topic
        )
        
        # Process recent log lines for context (or skip if initial_lines=0)
        self.log_tailer.start_initial_processing(initial_lines)
        
        # Setup file system watcher
        self.observer = Observer()
        self.observer.schedule(self.log_tailer, os.path.dirname(self.log_file_path), recursive=False)
        self.observer.start()
        
        # Start statistics reporter
        self.running = True
        self.start_stats_reporter()
        
        logger.info(f" Watching log file: {self.log_file_path}")
        logger.info(f"Streaming to Kafka topic: {self.kafka_topic}")
        if initial_lines == 0:
            logger.info(" Real-time processing started - ONLY NEW log entries will be processed")
        else:
            logger.info(f" Real-time processing started - processed {initial_lines} recent lines for context")
        logger.info("Press Ctrl+C to stop.")
        
        try:
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⌨️ Keyboard interrupt received")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the log processor gracefully"""
        logger.info(" Stopping HDFS log processor...")
        
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        if self.log_tailer:
            final_stats = self.log_tailer.get_stats()
            logger.info(f" Final stats: {final_stats}")
            self.log_tailer.stop()
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        logger.info(" HDFS log processor stopped gracefully")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 hdfs_production_log_processor.py <log_file_path> [kafka_servers] [kafka_topic] [scoring_service_url]")
        print("Example: python3 hdfs_production_log_processor.py /var/log/hadoop-hdfs/hadoop-hdfs-datanode-*.log")
        print("         python3 hdfs_production_log_processor.py /var/log/hadoop-hdfs/hadoop-hdfs-datanode-*.log localhost:9092 logs http://localhost:8003")
        print("")
        print("This processor monitors the log file in real-time and ONLY processes NEW log entries as they are written.")
        print("It does NOT process the entire existing file - only new lines that arrive after startup.")
        sys.exit(1)
    
    # Parse command line arguments
    log_file_path = sys.argv[1]
    kafka_servers = sys.argv[2] if len(sys.argv) > 2 else "localhost:9092"
    kafka_topic = sys.argv[3] if len(sys.argv) > 3 else "logs"
    scoring_service_url = sys.argv[4] if len(sys.argv) > 4 else "http://localhost:8003"
    
    # Expand wildcard patterns for log file path
    import glob
    matching_files = glob.glob(log_file_path)
    
    if not matching_files:
        logger.error(f" No log files found matching pattern: {log_file_path}")
        sys.exit(1)
    
    if len(matching_files) > 1:
        logger.warning(f" Multiple files found, using: {matching_files[0]}")
    
    actual_log_file = matching_files[0]
    
    logger.info(f"   Configuration:")
    logger.info(f"   Log File: {actual_log_file}")
    logger.info(f"   Kafka Servers: {kafka_servers}")
    logger.info(f"   Kafka Topic: {kafka_topic}")
    logger.info(f"   Scoring Service: {scoring_service_url}")
    
    # Create and start processor
    processor = HDFSProductionLogProcessor(
        log_file_path=actual_log_file,
        kafka_servers=kafka_servers,
        kafka_topic=kafka_topic,
        scoring_service_url=scoring_service_url
    )
    
    success = processor.start(initial_lines=0)  # Only process NEW log entries
    
    if success:
        logger.info(" HDFS log processing completed successfully!")
        sys.exit(0)
    else:
        logger.error(" HDFS log processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
