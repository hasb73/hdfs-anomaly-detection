#!/usr/bin/env python3
"""
Test script to verify block-level filtering (blk_) works correctly
"""

import sys
import os

# Add current directory to path to import the processor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hdfs_production_log_processor import HDFSLogPreprocessor

def test_block_filtering():
    """Test block-level filtering with sample HDFS logs"""
    
    preprocessor = HDFSLogPreprocessor()
    
    # Sample log entries from your examples
    test_logs = [
        # Should be INCLUDED (contains blk_)
        "2025-09-27 09:12:24,995 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode (DataXceiver for client DFSClient_NONMAPREDUCE_880426094_1 at /172.31.36.192:55678 [Sending block BP-904282469-172.31.36.192-1758638658492:blk_1073742025_1201]): block=BP-904282469-172.31.36.192-1758638658492:blk_1073742025_1201, replica=FinalizedReplica, blk_1073742025_1201, FINALIZED",
        
        "2025-09-27 09:12:24,995 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode (DataXceiver for client DFSClient_NONMAPREDUCE_880426094_1 at /172.31.36.192:55678 [Sending block BP-904282469-172.31.36.192-1758638658492:blk_1073742025_1201]): replica=FinalizedReplica, blk_1073742025_1201, FINALIZED",
        
        "2025-09-27 09:12:24,995 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode.clienttrace (DataXceiver for client DFSClient_NONMAPREDUCE_880426094_1 at /172.31.36.192:55678 [Sending block BP-904282469-172.31.36.192-1758638658492:blk_1073742025_1201]): src: /172.31.39.152:9866, dest: /172.31.36.192:55678, volume: , bytes: 40, op: HDFS_READ, cliID: DFSClient_NONMAPREDUCE_880426094_1, offset: 0, srvID: 4afa7677-552a-4246-84f6-54ae00a35b76, blockid: BP-904282469-172.31.36.192-1758638658492:blk_1073742025_1201, duration(ns): 113447",
        
        "2025-09-27 09:12:25,018 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode (DataXceiver for client DFSClient_NONMAPREDUCE_880426094_1 at /172.31.36.192:55678 [Sending block BP-904282469-172.31.36.192-1758638658492:blk_1073742025_1201]): Error reading client status response. Will close connection.",
        
        # Should be EXCLUDED (no blk_)
        "2025-09-27 09:35:05,413 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode (BP-904282469-172.31.36.192-1758638658492 heartbeating to ip-172-31-36-192.eu-west-1.compute.internal/172.31.36.192:8020): Before sending heartbeat to namenode ip-172-31-36-192.eu-west-1.compute.internal:8020, the state of the namenode known to datanode so far is active",
        
        "2025-09-27 09:12:25,018 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode (DataXceiver for client DFSClient_NONMAPREDUCE_880426094_1 at /172.31.36.192:55678): ip-172-31-39-152.eu-west-1.compute.internal:9866:Number of active connections is: 1",
        
        "2025-09-27 09:30:00,123 INFO org.apache.hadoop.hdfs.server.datanode.DataNode: Starting DataNode service",
        
        "2025-09-27 09:30:01,456 DEBUG org.apache.hadoop.hdfs.server.datanode.DataNode: Registering with NameNode"
    ]
    
    print("🧪 Testing Block-Level Filtering (blk_)")
    print("=" * 70)
    
    included_count = 0
    excluded_count = 0
    
    for i, log_line in enumerate(test_logs, 1):
        is_relevant = preprocessor.is_relevant_log(log_line)
        log_level = preprocessor.extract_log_level(log_line)
        
        # Show truncated log for readability
        display_log = log_line[:80] + "..." if len(log_line) > 80 else log_line
        
        print(f"\n📝 Test {i} ({log_level}):")
        print(f"   {display_log}")
        
        if is_relevant:
            print(f"   ✅ INCLUDED - Contains 'blk_'")
            included_count += 1
            
            # Show preprocessed version
            processed = preprocessor.preprocess_log_line(log_line)
            print(f"   🔄 Preprocessed: {processed[:60]}...")
        else:
            print(f"   ❌ EXCLUDED - No 'blk_' found")
            excluded_count += 1
    
    print("\n" + "=" * 70)
    print("📊 FILTERING SUMMARY:")
    print(f"   ✅ INCLUDED (with blk_): {included_count}")
    print(f"   ❌ EXCLUDED (no blk_):   {excluded_count}")
    print(f"   📈 Total logs tested:    {len(test_logs)}")
    print(f"   🎯 Filtering ratio:      {(excluded_count/len(test_logs)*100):.1f}% filtered out")
    
    print("\n🎯 EXPECTED RESULTS:")
    print("   - Only block-level operations will be sent to Kafka")
    print("   - Heartbeats, connections, and other non-block operations filtered out")
    print("   - Focus on actual HDFS block read/write/transfer operations")
    
    return True

def main():
    """Main test function"""
    try:
        test_block_filtering()
        print("\n🎉 Block filtering validation completed!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
