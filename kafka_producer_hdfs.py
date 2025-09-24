#!/usr/bin/env python3
"""
HDFS Kafka Producer (Line-Level)
Streams real HDFS log lines with proper line-level anomaly labels
"""
import json
import time
import random
from kafka import KafkaProducer
from datetime import datetime
import argparse
import os
import sys
from hdfs_line_level_loader import HDFSLineLevelLoader

class HDFSKafkaProducer:
    def __init__(self, bootstrap_servers='localhost:9092', topic='logs', max_records=50000):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            batch_size=16384,
            linger_ms=10,
            buffer_memory=33554432
        )
        self.topic = topic
        self.hdfs_loader = HDFSLineLevelLoader()
        
        # Get line-level data for streaming
        print("Loading line-level HDFS data for streaming...")
        messages, labels = self.hdfs_loader.get_line_level_data(sample_size=max_records)
        
        # Create streaming data format
        self.streaming_data = []
        for i, (message, label) in enumerate(zip(messages, labels)):
            self.streaming_data.append({
                'message': message,
                'label': int(label),
                'id': i
            })
        
        self.data_index = 0
        
        print(f"🚀 HDFS Kafka Producer initialized (Line-Level)")
        print(f"   Topic: {topic}")
        print(f"   Bootstrap servers: {bootstrap_servers}")
        print(f"   Loaded {len(self.streaming_data)} HDFS line-level records")
        if max_records:
            print(f"   Sample size: {max_records} (limited for performance)")
        
        # Calculate anomaly ratio
        anomaly_count = sum(1 for record in self.streaming_data if record['label'] == 1)
        anomaly_ratio = anomaly_count / len(self.streaming_data) * 100
        print(f"   Anomaly ratio: {anomaly_ratio:.2f}% ({anomaly_count}/{len(self.streaming_data)})")

    def send_hdfs_record(self):
        """Send next HDFS log record"""
        if self.data_index >= len(self.streaming_data):
            # Reset to beginning for continuous streaming
            self.data_index = 0
            print("🔄 Restarting HDFS dataset streaming...")
        
        record = self.streaming_data[self.data_index].copy()
        record['timestamp'] = datetime.now().isoformat()
        record['index'] = self.data_index
        
        # Send to Kafka
        key = f"hdfs_{self.data_index}"
        
        try:
            future = self.producer.send(self.topic, key=key, value=record)
            result = future.get(timeout=10)
            
            # Log message type
            msg_type = "🔴 ANOMALY" if record['label'] == 1 else "🟢 NORMAL"
            print(f"{msg_type} [{self.data_index:06d}] {record['message'][:80]}...")
            
            self.data_index += 1
            return True
            
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False

    def stream_hdfs_data(self, 
                        messages_per_second=2.0, 
                        duration_seconds=None, 
                        total_messages=None,
                        anomaly_burst=False):
        """
        Stream HDFS data to Kafka
        
        Args:
            messages_per_second: Rate of message sending
            duration_seconds: Total duration to stream (None for unlimited)
            total_messages: Total messages to send (None for unlimited)
            anomaly_burst: Whether to send anomalies in bursts
        """
        print(f"\n📡 Starting HDFS data streaming...")
        print(f"   Rate: {messages_per_second} msgs/sec")
        if duration_seconds:
            print(f"   Duration: {duration_seconds} seconds")
        if total_messages:
            print(f"   Total messages: {total_messages}")
        print(f"   Anomaly burst mode: {anomaly_burst}")
        
        start_time = time.time()
        message_count = 0
        interval = 1.0 / messages_per_second
        
        try:
            while True:
                # Check stopping conditions
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break
                if total_messages and message_count >= total_messages:
                    break
                
                # Send message
                if self.send_hdfs_record():
                    message_count += 1
                    
                    # Status update every 100 messages
                    if message_count % 100 == 0:
                        elapsed = time.time() - start_time
                        rate = message_count / elapsed
                        print(f"📊 Sent {message_count} messages in {elapsed:.1f}s (avg {rate:.1f} msgs/sec)")
                
                # Dynamic rate adjustment for anomaly bursts
                if anomaly_burst and self.streaming_data[self.data_index % len(self.streaming_data)]['label'] == 1:
                    # Send anomalies faster (burst mode)
                    time.sleep(interval * 0.1)  # 10x faster for anomalies
                else:
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            print("\n⏹️  Streaming stopped by user")
        except Exception as e:
            print(f"\n❌ Error during streaming: {e}")
        finally:
            elapsed = time.time() - start_time
            avg_rate = message_count / elapsed if elapsed > 0 else 0
            print(f"\n📈 Streaming completed:")
            print(f"   Total messages: {message_count}")
            print(f"   Duration: {elapsed:.1f} seconds")
            print(f"   Average rate: {avg_rate:.2f} msgs/sec")
            
            self.producer.flush()
            self.producer.close()

def main():
    parser = argparse.ArgumentParser(description='HDFS Kafka Producer')
    parser.add_argument('--bootstrap-servers', default='localhost:9092',
                       help='Kafka bootstrap servers')
    parser.add_argument('--topic', default='logs',
                       help='Kafka topic to send messages to')
    parser.add_argument('--rate', type=float, default=2.0,
                       help='Messages per second')
    parser.add_argument('--duration', type=int,
                       help='Duration in seconds (unlimited if not specified)')
    parser.add_argument('--count', type=int,
                       help='Total number of messages to send')
    parser.add_argument('--anomaly-burst', action='store_true',
                       help='Send anomalies in burst mode (faster)')
    parser.add_argument('--max-records', type=int, default=50000,
                       help='Maximum number of records to load (for performance)')
    
    args = parser.parse_args()
    
    # Create producer
    producer = HDFSKafkaProducer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        max_records=args.max_records
    )
    
    # Start streaming
    producer.stream_hdfs_data(
        messages_per_second=args.rate,
        duration_seconds=args.duration,
        total_messages=args.count,
        anomaly_burst=args.anomaly_burst
    )

if __name__ == '__main__':
    main()
