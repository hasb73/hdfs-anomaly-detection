#!/usr/bin/env python3
"""
Test script for HDFS Log Preprocessing
Tests the preprocessing logic with sample HDFS DataNode logs
"""

import sys
import os

# Add current directory to path to import the processor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hdfs_production_log_processor import HDFSLogPreprocessor

def test_preprocessing():
    """Test HDFS log preprocessing with sample logs"""
    
    preprocessor = HDFSLogPreprocessor()
    
    # Sample HDFS DataNode logs from your EMR cluster
    sample_logs = [
        "2025-09-25 09:30:54,737 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode.clienttrace (DataXceiver for client DFSClient_NONMAPREDUCE_-56011767_1 at /172.31.36.192:38172 [Sending block BP-904282469-172.31.36.192-1758638658492:blk_1073742023_1199]): src: /172.31.39.152:9866, dest: /172.31.36.192:38172, volume: , bytes: 40, op: HDFS_READ, cliID: DFSClient_NONMAPREDUCE_-56011767_1, offset: 0, srvID: 4afa7677-552a-4246-84f6-54ae00a35b76, blockid: BP-904282469-172.31.36.192-1758638658492:blk_1073742023_1199, duration(ns): 119030",
        
        "2025-09-25 09:30:54,745 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode (DataXceiver for client DFSClient_NONMAPREDUCE_-56011767_1 at /172.31.36.192:38172 [Sending block BP-904282469-172.31.36.192-1758638658492:blk_1073742023_1199]): Error reading client status response. Will close connection.",
        
        "2025-09-25 09:31:02,123 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Failed to read block blk_1073742024_1200 from disk: java.io.IOException: Block file /data/hdfs/current/BP-904282469-172.31.36.192-1758638658492/current/finalized/subdir0/subdir1/blk_1073742024 not found",
        
        "2025-09-25 09:31:15,456 WARN org.apache.hadoop.hdfs.server.datanode.DataXceiver: IOException in BlockReceiver constructor. Cause: java.net.SocketTimeoutException: Read timed out",
        
        "2025-09-25 09:31:20,789 INFO org.apache.hadoop.hdfs.server.datanode.DataNode: Successfully wrote block BP-904282469-172.31.36.192-1758638658492:blk_1073742025_1201 to disk",
        
        "2025-09-25 09:31:30,012 ERROR org.apache.hadoop.hdfs.server.datanode.fsdataset.impl.FsDatasetImpl: Volume /data/hdfs failed, removing from active volumes: java.io.IOException: Too many open files"
    ]
    
    print("🧪 Testing HDFS Log Preprocessing")
    print("=" * 60)
    
    for i, log_line in enumerate(sample_logs, 1):
        print(f"\n📝 Test {i}:")
        print("─" * 40)
        
        # Test relevance filtering
        is_relevant = preprocessor.is_relevant_log(log_line)
        log_level = preprocessor.extract_log_level(log_line)
        
        print(f"Original ({log_level}):")
        print(f"  {log_line}")
        
        print(f"Relevant: {'✅ Yes' if is_relevant else '❌ No'}")
        
        if is_relevant:
            processed = preprocessor.preprocess_log_line(log_line)
            print(f"Processed:")
            print(f"  {processed}")
        else:
            print("  (Skipped - not relevant for anomaly detection)")
    
    print("\n" + "=" * 60)
    print("✅ Preprocessing test completed!")
    
    # Test pattern matching
    print("\n🔍 Testing Pattern Matching:")
    print("─" * 40)
    
    test_patterns = {
        "IP Address": "172.31.36.192",
        "Block ID": "blk_1073742023_1199", 
        "Client ID": "DFSClient_NONMAPREDUCE_-56011767_1",
        "UUID": "4afa7677-552a-4246-84f6-54ae00a35b76",
        "Hostname": "ip-172-31-36-192.eu-west-1.compute.internal",
        "Timestamp": "2025-09-25 09:30:54,737"
    }
    
    for pattern_name, test_value in test_patterns.items():
        test_line = f"Test {test_value} in log"
        processed = preprocessor.preprocess_log_line(test_line)
        print(f"{pattern_name:12}: {test_value} → {processed}")

def test_kafka_message_format():
    """Test Kafka message format creation"""
    print("\n📡 Testing Kafka Message Format:")
    print("─" * 40)
    
    preprocessor = HDFSLogPreprocessor()
    
    sample_log = "2025-09-25 09:31:02,123 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: Failed to read block blk_1073742024_1200"
    processed_log = preprocessor.preprocess_log_line(sample_log)
    log_level = preprocessor.extract_log_level(sample_log)
    
    # Simulate Kafka message creation
    from datetime import datetime
    import json
    
    message = {
        'text': processed_log,
        'original_text': sample_log,
        'log_level': log_level,
        'source': 'hdfs_datanode',
        'timestamp': datetime.now().isoformat(),
        'node_type': 'datanode',
        'label': None
    }
    
    print("Kafka Message:")
    print(json.dumps(message, indent=2))

def main():
    """Main test function"""
    try:
        test_preprocessing()
        test_kafka_message_format()
        print("\n🎉 All tests passed!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
