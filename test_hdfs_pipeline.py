#!/usr/bin/env python3
"""
HDFS Pipeline Integration Tests
Tests all components of the HDFS log anomaly detection pipeline
"""
# Suppress urllib3 SSL warnings
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

import unittest
import requests
import time
import subprocess
import os
import sys
import json
from qdrant_client import QdrantClient
from kafka import KafkaProducer, KafkaConsumer
import pickle
import pandas as pd

class HDFSPipelineIntegrationTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_dir = os.path.dirname(os.path.abspath(__file__))
        cls.embedding_url = "http://localhost:8000"
        cls.scoring_url = "http://localhost:8002"
        cls.qdrant_url = "http://localhost:6333"
        cls.kafka_bootstrap = "localhost:9092"
        
    def test_01_hdfs_data_loader(self):
        """Test HDFS data loader functionality"""
        print("\n🧪 Testing HDFS data loader...")
        
        # Import and test data loader
        sys.path.append(self.base_dir)
        try:
            from hdfs_data_loader import HDFSDataLoader
            
            loader = HDFSDataLoader()
            
            # Test data loading
            train_df = loader.load_training_data()
            self.assertIsInstance(train_df, pd.DataFrame)
            self.assertGreater(len(train_df), 0)
            self.assertIn('message', train_df.columns)
            self.assertIn('label', train_df.columns)
            
            # Test streaming data
            stream_data = list(loader.get_streaming_data(batch_size=10))
            self.assertGreater(len(stream_data), 0)
            
            print("✅ HDFS data loader test passed")
            
        except Exception as e:
            self.fail(f"HDFS data loader test failed: {e}")
    
    def test_02_embedding_service(self):
        """Test embedding service API"""
        print("\n🧪 Testing embedding service...")
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.embedding_url}/health", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            # Test embedding generation
            test_text = "Test log message for embedding generation"
            response = requests.post(
                f"{self.embedding_url}/embed",
                json={"text": test_text},
                timeout=10
            )
            
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertIn("embedding", result)
            self.assertIsInstance(result["embedding"], list)
            self.assertEqual(len(result["embedding"]), 384)  # Sentence-BERT dimension
            
            print("✅ Embedding service test passed")
            
        except Exception as e:
            self.fail(f"Embedding service test failed: {e}")
    
    def test_03_qdrant_connection(self):
        """Test Qdrant vector database connection"""
        print("\n🧪 Testing Qdrant connection...")
        
        try:
            client = QdrantClient(host="localhost", port=6333)
            
            # Test connection
            collections = client.get_collections()
            self.assertIsInstance(collections, object)
            
            # Check if hdfs_logs collection exists or can be created
            collection_name = "hdfs_logs"
            try:
                info = client.get_collection(collection_name)
                print(f"  Collection '{collection_name}' exists with {info.vectors_count} vectors")
            except:
                print(f"  Collection '{collection_name}' not found (will be created by Spark job)")
            
            print("✅ Qdrant connection test passed")
            
        except Exception as e:
            self.fail(f"Qdrant connection test failed: {e}")
    
    def test_04_kafka_connection(self):
        """Test Kafka connection"""
        print("\n🧪 Testing Kafka connection...")
        
        try:
            # Test producer connection
            producer = KafkaProducer(
                bootstrap_servers=[self.kafka_bootstrap],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            # Send test message
            test_message = {
                "timestamp": "2024-01-01T12:00:00Z",
                "message": "Test HDFS log message",
                "label": 0
            }
            
            producer.send("hdfs_logs", value=test_message)
            producer.flush()
            producer.close()
            
            print("✅ Kafka connection test passed")
            
        except Exception as e:
            self.fail(f"Kafka connection test failed: {e}")
    
    def test_05_ensemble_model(self):
        """Test ensemble model loading and prediction"""
        print("\n🧪 Testing ensemble model...")
        
        try:
            model_path = os.path.join(self.base_dir, "models", "ensemble", "ensemble_results.joblib")
            
            if not os.path.exists(model_path):
                self.skipTest("Ensemble model not found. Run training first.")
            
            # Load model
            with open(model_path, 'rb') as f:
                ensemble_results = pickle.load(f)
            
            self.assertIn('best_model', ensemble_results)
            self.assertIn('vectorizer', ensemble_results)
            
            # Test prediction
            vectorizer = ensemble_results['vectorizer']
            model = ensemble_results['best_model']
            
            test_texts = [
                "Normal HDFS operation completed successfully",
                "CRITICAL ERROR: Block corruption detected"
            ]
            
            X = vectorizer.transform(test_texts)
            predictions = model.predict(X)
            probabilities = model.predict_proba(X)
            
            self.assertEqual(len(predictions), 2)
            self.assertEqual(len(probabilities), 2)
            
            print(f"  Predictions: {predictions}")
            print(f"  Probabilities: {probabilities}")
            print("✅ Ensemble model test passed")
            
        except Exception as e:
            self.fail(f"Ensemble model test failed: {e}")
    
    def test_06_scoring_service(self):
        """Test scoring service API"""
        print("\n🧪 Testing scoring service...")
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.scoring_url}/health", timeout=10)
            self.assertEqual(response.status_code, 200)
            
            # Test text scoring
            test_text = "HDFS block verification completed"
            response = requests.post(
                f"{self.scoring_url}/score_text",
                json={"text": test_text},
                timeout=10
            )
            
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertIn("prediction", result)
            self.assertIn("anomaly_score", result)
            self.assertIn("processing_time", result)
            
            # Test batch scoring
            test_texts = [
                "Normal log message",
                "ERROR: Something went wrong",
                "INFO: Process completed"
            ]
            
            response = requests.post(
                f"{self.scoring_url}/score_batch",
                json={"texts": test_texts},
                timeout=15
            )
            
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertIn("results", result)
            self.assertIn("summary", result)
            self.assertEqual(len(result["results"]), 3)
            
            print("✅ Scoring service test passed")
            
        except Exception as e:
            self.fail(f"Scoring service test failed: {e}")
    
    def test_07_end_to_end_flow(self):
        """Test end-to-end pipeline flow"""
        print("\n🧪 Testing end-to-end pipeline flow...")
        
        try:
            # 1. Generate embedding for test text
            test_text = "Test HDFS log message for end-to-end validation"
            
            embed_response = requests.post(
                f"{self.embedding_url}/embed",
                json={"text": test_text},
                timeout=10
            )
            self.assertEqual(embed_response.status_code, 200)
            embedding = embed_response.json()["embedding"]
            
            # 2. Score the embedding
            score_response = requests.post(
                f"{self.scoring_url}/score_embedding",
                json={"embedding": embedding},
                timeout=10
            )
            self.assertEqual(score_response.status_code, 200)
            score_result = score_response.json()
            
            # 3. Verify scoring results
            self.assertIn("prediction", score_result)
            self.assertIn("anomaly_score", score_result)
            
            print(f"  Text: {test_text}")
            print(f"  Prediction: {'ANOMALY' if score_result['prediction'] == 1 else 'NORMAL'}")
            print(f"  Score: {score_result['anomaly_score']:.3f}")
            
            print("✅ End-to-end flow test passed")
            
        except Exception as e:
            self.fail(f"End-to-end flow test failed: {e}")

class HDFSPipelineValidator:
    """Comprehensive pipeline validation"""
    
    def __init__(self):
        self.checks = []
        self.errors = []
    
    def add_check(self, name, func):
        """Add a validation check"""
        self.checks.append((name, func))
    
    def run_validation(self):
        """Run all validation checks"""
        print("🔍 Running HDFS Pipeline Validation")
        print("=" * 50)
        
        for name, check_func in self.checks:
            try:
                print(f"\n📋 {name}...")
                result = check_func()
                if result:
                    print(f"✅ {name} - PASSED")
                else:
                    print(f"❌ {name} - FAILED")
                    self.errors.append(name)
            except Exception as e:
                print(f"❌ {name} - ERROR: {e}")
                self.errors.append(name)
        
        # Summary
        print(f"\n📊 Validation Summary")
        print(f"  Total checks: {len(self.checks)}")
        print(f"  Passed: {len(self.checks) - len(self.errors)}")
        print(f"  Failed: {len(self.errors)}")
        
        if self.errors:
            print(f"\n❌ Failed checks: {', '.join(self.errors)}")
            return False
        else:
            print(f"\n🎉 All validations passed!")
            return True
    
    def check_file_exists(self, filepath):
        """Check if file exists"""
        return os.path.exists(filepath)
    
    def check_service_health(self, url):
        """Check if service is healthy"""
        try:
            response = requests.get(f"{url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_model_files(self):
        """Check if model files exist"""
        model_files = [
            "ensemble/models/ensemble/ensemble_results.joblib",
            "ensemble/models/ensemble/training_metrics.json"
        ]
        return all(os.path.exists(f) for f in model_files)
    
    def check_data_files(self):
        """Check if HDFS data files exist"""
        data_files = [
            "HDFS_v1/HDFS.log",
            "HDFS_v1/HDFS_preprocessed.csv",
            "HDFS_v1/anomaly_label.csv"
        ]
        return all(os.path.exists(f) for f in data_files)

def run_integration_tests():
    """Run integration tests"""
    print("🧪 Running HDFS Pipeline Integration Tests")
    print("=" * 50)
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(HDFSPipelineIntegrationTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_validation():
    """Run pipeline validation"""
    validator = HDFSPipelineValidator()
    
    # Add validation checks
    validator.add_check(
        "HDFS Data Files",
        validator.check_data_files
    )
    
    validator.add_check(
        "Model Files",
        validator.check_model_files
    )
    
    validator.add_check(
        "Embedding Service",
        lambda: validator.check_service_health("http://localhost:8000")
    )
    
    validator.add_check(
        "Scoring Service",
        lambda: validator.check_service_health("http://localhost:8002")
    )
    
    validator.add_check(
        "Qdrant Service",
        lambda: validator.check_service_health("http://localhost:6333")
    )
    
    return validator.run_validation()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='HDFS Pipeline Testing')
    parser.add_argument('--test', action='store_true', help='Run integration tests')
    parser.add_argument('--validate', action='store_true', help='Run validation checks')
    parser.add_argument('--all', action='store_true', help='Run both tests and validation')
    
    args = parser.parse_args()
    
    success = True
    
    if args.all or args.validate:
        success &= run_validation()
    
    if args.all or args.test:
        success &= run_integration_tests()
    
    if not (args.test or args.validate or args.all):
        print("Please specify --test, --validate, or --all")
        return False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
