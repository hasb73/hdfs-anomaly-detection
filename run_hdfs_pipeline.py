#!/usr/bin/env python3
"""
HDFS Pipeline Runner
Orchestrates the complete HDFS log anomaly detection pipeline
"""
# Suppress urllib3 SSL warnings
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

import subprocess
import time
import sys
import os
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
import json

class HDFSPipelineRunner:
    def __init__(self):
        self.processes = {}
        self.running = False
        
    def run_command(self, name, command, cwd=None, background=True):
        """Run a command and track the process"""
        print(f"🚀 Starting {name}...")
        try:
            if background:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
                self.processes[name] = process
                print(f"✅ {name} started (PID: {process.pid})")
                return process
            else:
                result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {name} completed successfully")
                    return result
                else:
                    print(f"❌ {name} failed: {result.stderr}")
                    return None
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return None
    
    def wait_for_service(self, name, url, timeout=60):
        """Wait for a service to be ready"""
        print(f"⏳ Waiting for {name} to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {name} is ready!")
                    return True
            except:
                pass
            time.sleep(2)
        
        print(f"❌ {name} failed to start within {timeout} seconds")
        return False
    
    def start_infrastructure(self):
        """Start Docker Compose infrastructure"""
        print("\n📦 Starting infrastructure services...")
        
        # Check if docker-compose is available
        result = self.run_command(
            "Docker Compose",
            "docker-compose --version",
            background=False
        )
        
        if result is None:
            print("❌ Docker Compose not found. Please install Docker Compose.")
            return False
        
        # Start services
        result = self.run_command(
            "Infrastructure",
            "docker-compose up -d",
            background=False
        )
        
        if result is None:
            return False
        
        # Wait for services to be ready
        services = [
            ("Qdrant", "http://localhost:6333/health"),
            ("Kafka", "http://localhost:9092"),  # This might not work, just wait
            ("Embedding Service", "http://localhost:8000/health")
        ]
        
        for name, url in services:
            if name == "Kafka":
                print("⏳ Waiting for Kafka (30 seconds)...")
                time.sleep(30)
            else:
                if not self.wait_for_service(name, url):
                    return False
        
        return True
    
    def train_model(self):
        """Train the ensemble model"""
        print("\n🧠 Training ensemble model...")
        
        result = self.run_command(
            "Model Training",
            "python3 anomaly_trainer_hdfs.py",
            background=False
        )
        
        return result is not None
    
    def start_scoring_service(self):
        """Start the scoring service"""
        print("\n🎯 Starting scoring service...")
        
        # Check if model exists
        if not os.path.exists("ensemble/models/ensemble/ensemble_results.joblib"):
            print("❌ Ensemble model not found. Please train the model first.")
            return False
        
        self.run_command(
            "Scoring Service",
            "cd scoring_service && python3 app.py",
            background=True
        )
        
        # Wait for scoring service to be ready
        return self.wait_for_service("Scoring Service", "http://localhost:8080/health")
    
    def start_spark_job(self):
        """Start the Spark streaming job"""
        print("\n⚡ Starting Spark streaming job...")
        
        # Check if Spark is available
        result = subprocess.run("spark-submit --version", shell=True, capture_output=True)
        if result.returncode != 0:
            print("❌ Spark not found. Please install Apache Spark.")
            return False
        
        self.run_command(
            "Spark Job",
            "spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 spark_job.py",
            background=True
        )
        
        time.sleep(10)  # Give Spark time to start
        return True
    
    def start_kafka_producer(self, rate=2.0, duration=None):
        """Start the HDFS Kafka producer"""
        print(f"\n📡 Starting HDFS Kafka producer (rate: {rate} msgs/sec)...")
        
        cmd = f"python3 kafka_producer_hdfs.py --rate {rate}"
        if duration:
            cmd += f" --duration {duration}"
        
        self.run_command(
            "Kafka Producer",
            cmd,
            background=True
        )
        
        return True
    
    def run_pipeline(self, train_model=True, producer_rate=2.0, producer_duration=None):
        """Run the complete pipeline"""
        self.running = True
        
        print("🎯 Starting HDFS Log Anomaly Detection Pipeline")
        print("=" * 50)
        
        try:
            # Step 1: Start infrastructure
            if not self.start_infrastructure():
                return False
            
            # Step 2: Train model (optional)
            if train_model:
                if not self.train_model():
                    print("⚠️  Model training failed, continuing with existing model...")
            
            # Step 3: Start scoring service
            if not self.start_scoring_service():
                return False
            
            # Step 4: Start Spark job
            if not self.start_spark_job():
                return False
            
            # Step 5: Start Kafka producer
            if not self.start_kafka_producer(producer_rate, producer_duration):
                return False
            
            print("\n🎉 Pipeline started successfully!")
            print("\nServices running:")
            print("  📊 Qdrant:          http://localhost:6333")
            print("  🧠 Embedding:       http://localhost:8000")
            print("  🎯 Scoring:         http://localhost:8080")
            print("  📡 Kafka:           localhost:9092")
            print("  ⚡ Spark:           Processing streams")
            print("  📨 Producer:        Sending HDFS logs")
            
            print("\nAPI Endpoints:")
            print("  🔍 Health Check:    http://localhost:8080/health")
            print("  📈 Statistics:      http://localhost:8080/stats")
            print("  🎯 Score Text:      POST http://localhost:8080/score_text")
            print("  📊 Batch Score:     POST http://localhost:8080/score_batch")
            
            print("\nPress Ctrl+C to stop the pipeline...")
            
            # Monitor processes
            while self.running:
                time.sleep(5)
                # Check if critical processes are still running
                critical_processes = ["Scoring Service", "Spark Job"]
                for name in critical_processes:
                    if name in self.processes:
                        if self.processes[name].poll() is not None:
                            print(f"⚠️  {name} has stopped unexpectedly")
            
            return True
            
        except KeyboardInterrupt:
            print("\n🛑 Pipeline shutdown requested...")
            return True
        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            return False
    
    def stop_pipeline(self):
        """Stop all running processes"""
        print("\n🛑 Stopping pipeline...")
        self.running = False
        
        # Stop tracked processes
        for name, process in self.processes.items():
            try:
                print(f"  Stopping {name}...")
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                process.wait(timeout=10)
            except Exception as e:
                print(f"  Error stopping {name}: {e}")
        
        # Stop Docker Compose
        print("  Stopping infrastructure...")
        subprocess.run("docker-compose down", shell=True)
        
        print("✅ Pipeline stopped")
    
    def demo_scoring(self):
        """Demonstrate the scoring API"""
        print("\n🎯 Demonstrating scoring API...")
        
        # Wait for scoring service
        if not self.wait_for_service("Scoring Service", "http://localhost:8080/health"):
            print("❌ Scoring service not available")
            return
        
        # Test texts (some normal, some potentially anomalous)
        test_texts = [
            "Received block blk_123456789 of size 64MB from 192.168.1.100",
            "CRITICAL ERROR: Block corruption detected in blk_987654321",
            "Verification succeeded for blk_555666777",
            "FATAL: OutOfMemoryError in DataNode process",
            "Served block blk_111222333 to 192.168.1.200"
        ]
        
        print("\nTesting individual text scoring:")
        for i, text in enumerate(test_texts):
            try:
                response = requests.post(
                    "http://localhost:8080/score_text",
                    json={"text": text},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    status = "🔴 ANOMALY" if result['prediction'] == 1 else "🟢 NORMAL"
                    print(f"  {status} [{result['anomaly_score']:.3f}] {text[:50]}...")
                else:
                    print(f"  ❌ Error scoring text {i+1}: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Error scoring text {i+1}: {e}")
        
        # Test batch scoring
        print("\nTesting batch scoring:")
        try:
            response = requests.post(
                "http://localhost:8080/score_batch",
                json={"texts": test_texts},
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result['summary']
                print(f"  📊 Batch Results: {summary['total']} total, {summary['anomalies']} anomalies ({summary['anomaly_rate']:.1%})")
            else:
                print(f"  ❌ Batch scoring error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Batch scoring error: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='HDFS Pipeline Runner')
    parser.add_argument('--no-train', action='store_true', help='Skip model training')
    parser.add_argument('--rate', type=float, default=2.0, help='Producer rate (msgs/sec)')
    parser.add_argument('--duration', type=int, help='Producer duration (seconds)')
    parser.add_argument('--demo-only', action='store_true', help='Only run scoring demo')
    
    args = parser.parse_args()
    
    runner = HDFSPipelineRunner()
    
    def signal_handler(sig, frame):
        runner.stop_pipeline()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.demo_only:
            runner.demo_scoring()
        else:
            success = runner.run_pipeline(
                train_model=not args.no_train,
                producer_rate=args.rate,
                producer_duration=args.duration
            )
            
            if not success:
                print("❌ Pipeline failed to start")
                sys.exit(1)
    
    finally:
        runner.stop_pipeline()

if __name__ == "__main__":
    main()
