#!/usr/bin/env python3
"""
Test script to verify the HDFS log processor only processes NEW entries
Creates a test log file and appends new entries to verify real-time processing
"""

import time
import os
import threading
import subprocess

def create_test_log_file():
    """Create a test log file with initial content"""
    test_log = "test_hdfs_datanode.log"
    
    # Create initial log content (should NOT be processed)
    initial_logs = [
        "2025-09-26 10:00:01,001 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: Initial log entry 1",
        "2025-09-26 10:00:02,002 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: Initial log entry 2", 
        "2025-09-26 10:00:03,003 INFO org.apache.hadoop.hdfs.server.datanode.DataNode: Initial log entry 3",
        "2025-09-26 10:00:04,004 WARN org.apache.hadoop.hdfs.server.datanode.DataNode: Initial warning (should NOT be processed)",
    ]
    
    with open(test_log, 'w') as f:
        for log in initial_logs:
            f.write(log + '\n')
    
    print(f"✅ Created test log file: {test_log}")
    print(f"📝 Initial entries: {len(initial_logs)} (these should NOT be processed)")
    return test_log

def append_new_entries(test_log):
    """Append new entries to the log file after a delay"""
    time.sleep(5)  # Wait for processor to start
    
    new_logs = [
        "2025-09-26 10:00:10,010 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: NEW ERROR - should be processed",
        "2025-09-26 10:00:11,011 WARN org.apache.hadoop.hdfs.server.datanode.DataNode: NEW WARNING - should be processed",
        "2025-09-26 10:00:12,012 INFO org.apache.hadoop.hdfs.server.datanode.DataNode: NEW INFO - should be processed",
        "2025-09-26 10:00:13,013 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: Failed connection - should be processed",
        "2025-09-26 10:00:14,014 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Cannot read block blk_123_456 - should be processed",
    ]
    
    print(f"\n🔄 Appending {len(new_logs)} NEW entries to log file...")
    
    with open(test_log, 'a') as f:
        for i, log in enumerate(new_logs, 1):
            f.write(log + '\n')
            f.flush()  # Force write to disk
            print(f"   Added entry {i}: {log[:50]}...")
            time.sleep(2)  # Add entries with delay
    
    print("✅ Finished appending new entries")

def main():
    """Main test function"""
    print("🧪 Testing HDFS Log Processor - NEW ENTRIES ONLY")
    print("=" * 60)
    
    # Create test log file
    test_log = create_test_log_file()
    
    print(f"\n🚀 Start the HDFS log processor in another terminal:")
    print(f"python3 hdfs_production_log_processor.py {os.path.abspath(test_log)} localhost:9092 logs http://localhost:8003")
    print(f"\nWait for the processor to start, then press Enter to continue...")
    input()
    
    # Start appending new entries in background
    append_thread = threading.Thread(target=append_new_entries, args=(test_log,))
    append_thread.start()
    
    print(f"\n📊 Expected behavior:")
    print(f"   ❌ Initial 4 log entries should NOT be processed")
    print(f"   ✅ NEW 5 log entries should be processed and sent to Kafka")
    print(f"   🔍 Check Kafka topic 'logs' for the NEW entries only")
    
    # Wait for appending to complete
    append_thread.join()
    
    print(f"\n🏁 Test complete!")
    print(f"📄 Test log file: {os.path.abspath(test_log)}")
    print(f"🧹 Clean up: rm {test_log}")

if __name__ == "__main__":
    main()
