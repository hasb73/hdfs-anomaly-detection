#!/usr/bin/env python3
"""
Test script to verify the HDFS log processor only processes block operations (containing "blk_")
Creates a test log file with block and non-block entries to verify filtering
"""

import time
import os
import threading
import subprocess

def create_test_log_file():
    """Create a test log file with block and non-block content"""
    test_log = "test_hdfs_datanode.log"
    
    # Create initial log content - mix of block and non-block entries
    initial_logs = [
        "2025-09-27 10:00:01,001 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: Regular log entry without blocks",
        "2025-09-27 10:00:02,002 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: block=BP-904282469-172.31.36.192-1758638658492:blk_1073742025_1201", 
        "2025-09-27 10:00:03,003 INFO org.apache.hadoop.hdfs.server.datanode.DataNode: Another non-block entry",
        "2025-09-27 10:00:04,004 WARN org.apache.hadoop.hdfs.server.datanode.DataNode: Warning without block reference",
    ]
    
    with open(test_log, 'w') as f:
        for log in initial_logs:
            f.write(log + '\n')
    
    print(f"✅ Created test log file: {test_log}")
    print(f"📝 Initial entries: {len(initial_logs)} (only 1 contains 'blk_' and should be processed)")
    return test_log

def append_new_entries(test_log):
    """Append new entries to the log file after a delay - mix of block and non-block operations"""
    time.sleep(5)  # Wait for processor to start
    
    new_logs = [
        "2025-09-27 10:00:10,010 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: NEW ERROR without block reference",
        "2025-09-27 10:00:11,011 WARN org.apache.hadoop.hdfs.server.datanode.DataNode: Block operation blk_1073742025_1201 failed",
        "2025-09-27 10:00:12,012 INFO org.apache.hadoop.hdfs.server.datanode.DataNode: Regular info message",
        "2025-09-27 10:00:13,013 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: blockid: BP-904282469-172.31.36.192-1758638658492:blk_1073742026_1202",
        "2025-09-27 10:00:14,014 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Cannot read block blk_123_456 from disk",
        "2025-09-27 10:00:15,015 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: Connection established",
        "2025-09-27 10:00:16,016 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: getBlockURI() = file:/mnt/hdfs/current/BP-904282469-172.31.36.192-1758638658492/current/finalized/subdir0/subdir0/blk_1073742027",
    ]
    
    print(f"\n🔄 Appending {len(new_logs)} NEW entries to log file...")
    print(f"📊 Expected: Only {sum(1 for log in new_logs if 'blk_' in log)} entries should be processed (contain 'blk_')")
    
    with open(test_log, 'a') as f:
        for i, log in enumerate(new_logs, 1):
            f.write(log + '\n')
            f.flush()  # Force write to disk
            block_indicator = "🧱 BLOCK" if "blk_" in log else "⚪ NON-BLOCK"
            print(f"   Added entry {i} {block_indicator}: {log[:80]}...")
            time.sleep(2)  # Add entries with delay
    
    print("✅ Finished appending new entries")

def main():
    """Main test function"""
    print("🧪 Testing HDFS Log Processor - BLOCK OPERATIONS ONLY")
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
    print(f"   🧱 BLOCK FILTERING: Only log entries containing 'blk_' should be processed")
    print(f"   ❌ Non-block entries should be skipped")
    print(f"   ✅ Block operation entries should be sent to Kafka")
    print(f"   🔍 Check Kafka topic 'logs' for block operations only")
    
    # Wait for appending to complete
    append_thread.join()
    
    print(f"\n🏁 Test complete!")
    print(f"📄 Test log file: {os.path.abspath(test_log)}")
    print(f"🧹 Clean up: rm {test_log}")

if __name__ == "__main__":
    main()
