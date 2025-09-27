#!/usr/bin/env python3
"""
Test script to verify improved logging in enhanced scoring service
"""
import requests
import json
import logging
import time

# Configure logging to see the output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_improved_logging():
    """Test the improved logging format"""
    
    # Sample HDFS log entries with block-level operations  
    test_logs = [
        "2024-01-15 10:30:45,123 INFO org.apache.hadoop.hdfs.server.datanode.DataNode: Received blk_1073741825_1001 from /10.0.0.1:45678",
        "2024-01-15 10:30:46,456 WARN org.apache.hadoop.hdfs.server.datanode.DataNode: Block blk_1073741826_1002 replication failed to /10.0.0.2:50010",
        "2024-01-15 10:30:47,789 ERROR org.apache.hadoop.hdfs.server.namenode.FSNamesystem: Corrupt block blk_1073741827_1003 detected on datanode /10.0.0.3:50010"
    ]
    
    scoring_service_url = "http://localhost:8800"
    
    print("🔍 Testing improved logging format...")
    print("=" * 60)
    
    for i, log_entry in enumerate(test_logs, 1):
        print(f"\n📋 Test {i}: Sending log entry for scoring...")
        print(f"Log: {log_entry[:80]}...")
        
        try:
            # Send request to scoring service
            response = requests.post(
                f"{scoring_service_url}/score",
                json={"text": log_entry},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Prediction: {result.get('predicted_label')} (Score: {result.get('anomaly_score', 0):.4f})")
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection failed - make sure scoring service is running on port 8800")
            print("   Start it with: uvicorn enhanced_scoring_service:app --host 0.0.0.0 --port 8800")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)  # Small delay between requests
    
    print("\n" + "=" * 60)
    print("🔍 Check the scoring service logs to see the improved format:")
    print("   - Full HDFS log entry should be shown")
    print("   - Weighted voting on separate lines")
    print("   - Anomaly score and prediction on separate lines")
    print("   - No PydanticDeprecated or search method deprecation warnings")

if __name__ == "__main__":
    test_improved_logging()
