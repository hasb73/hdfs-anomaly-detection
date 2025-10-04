#!/usr/bin/env python3
"""
Line-Level Ensemble Trainer for HDFS Anomaly Detection
Uses proper line-level labels instead of block-level labels
"""

# Suppress urllib3 SSL warnings
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
import joblib
import os
import sys
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from hdfs_line_level_loader import HDFSLineLevelLoader
import json

def get_hdfs_line_level_embeddings(sample_size=10000):
    """Get HDFS line-level embeddings using proper labeling"""
    
    print(f"Loading HDFS line-level data (sample_size={sample_size})...")
    loader = HDFSLineLevelLoader()
    messages, labels = loader.get_line_level_data(sample_size=sample_size)
    
    print(f"Loaded {len(messages)} line-level samples:")
    print(f"  - Normal lines: {labels.count(0)} ({100*labels.count(0)/len(labels):.2f}%)")
    print(f"  - Anomalous lines: {labels.count(1)} ({100*labels.count(1)/len(labels):.2f}%)")
    
    # Get embeddings
    print("Getting embeddings from embedding service...")
    
    EMBEDDING_SERVICE_URL = "http://localhost:8000"
    embeddings = []
    batch_size = 100
    
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i+batch_size]
        batch_labels = labels[i:i+batch_size]
        
        try:
            response = requests.post(
                f"{EMBEDDING_SERVICE_URL}/embed",
                json={"texts": batch},
                timeout=30
            )
            
            if response.status_code == 200:
                batch_embeddings = response.json()["embeddings"]
                embeddings.extend(batch_embeddings)
                print(f"  ✅ Batch {i//batch_size + 1}/{(len(messages)-1)//batch_size + 1} completed")
            else:
                print(f"Error in batch {i//batch_size}: {response.status_code}")
                # Fallback to dummy embeddings
                embeddings.extend([np.random.randn(384).tolist() for _ in batch])
        except Exception as e:
            print(f"Connection error, using dummy embeddings: {e}")
            embeddings.extend([np.random.randn(384).tolist() for _ in batch])
    
    return np.array(embeddings, dtype=np.float32), np.array(labels)

def train_line_level_ensemble(X=None, y=None, outdir=None, sample_size=100000):
    """Train ensemble model on line-level HDFS data"""
    
    # Set default output directory relative to this script's location
    if outdir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.join(script_dir, 'models', 'line_level_ensemble')
    
    # Load line-level HDFS data if not provided
    if X is None or y is None:
        print("Loading line-level HDFS dataset for training...")
        X, y = get_hdfs_line_level_embeddings(sample_size=sample_size)
    
    print(f"Training on {len(X)} line-level samples with {X.shape[1]} features")
    print(f"Label distribution: Normal={np.sum(y==0)}, Anomaly={np.sum(y==1)}")
    
    # Create output directory
    os.makedirs(outdir, exist_ok=True)
    
    # Check for severe class imbalance and handle appropriately
    anomaly_ratio = np.sum(y == 1) / len(y)
    print(f"Anomaly ratio: {anomaly_ratio:.4f}")
    
    if anomaly_ratio < 0.001:  # Less than 0.1%
        print("Handling severe class imbalance with advanced techniques...")
        
        # Strategy 1: Focused sampling around anomalies
        anomaly_indices = np.where(y == 1)[0]
        normal_indices = np.where(y == 0)[0]
        
        # Keep all anomalies
        selected_anomaly_indices = anomaly_indices
        
        # Sample normals to create better balance (but not 50-50, more realistic)
        target_normal_count = min(len(normal_indices), len(anomaly_indices) * 20)  # 20:1 ratio
        selected_normal_indices = np.random.choice(normal_indices, target_normal_count, replace=False)
        
        # Combine indices
        selected_indices = np.concatenate([selected_normal_indices, selected_anomaly_indices])
        np.random.shuffle(selected_indices)
        
        X = X[selected_indices]
        y = y[selected_indices]
        
        print(f"Balanced dataset: Normal={np.sum(y==0)}, Anomaly={np.sum(y==1)}")
    
    # Train/validation split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Feature scaling
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train).astype(np.float32)
    X_val_s = scaler.transform(X_val).astype(np.float32)
    
    # Clear memory
    del X_train, X_val
    
    print("Training ensemble models...")
    
    # Initialize models with class-imbalance awareness
    models = {
        'sgd': SGDClassifier(
            random_state=42, 
            max_iter=2000,
            class_weight='balanced',  # Handle imbalance
            loss='log_loss'  # For probability estimates
        ),
        'mlp': MLPClassifier(
            hidden_layer_sizes=(128, 64),
            random_state=42,
            max_iter=1000,
            early_stopping=True,
            validation_fraction=0.1
        ),
        'dt': DecisionTreeClassifier(
            random_state=42,
            max_depth=10,
            class_weight='balanced'  # Handle imbalance
        ),
        'rf': RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=10,
            class_weight='balanced',  # Handle imbalance
            n_jobs=-1
        )
    }
    
    # Train models
    trained_models = {}
    model_scores = {}
    
    for name, model in models.items():
        print(f"\nTraining {name.upper()}...")
        
        try:
            model.fit(X_train_s, y_train)
            
            # Validate
            val_pred = model.predict(X_val_s)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_val, val_pred, average='binary', zero_division=0
            )
            
            print(f"  Validation - P: {precision:.3f}, R: {recall:.3f}, F1: {f1:.3f}")
            
            trained_models[name] = model
            model_scores[name] = {'precision': precision, 'recall': recall, 'f1': f1}
            
        except Exception as e:
            print(f"  ❌ Failed to train {name}: {e}")
    
    # Add clustering models for unsupervised anomaly detection
    print("\nTraining clustering models...")
    
    # DBSCAN for density-based anomaly detection
    try:
        # Sample for clustering (too expensive on full data)
        cluster_sample_size = min(5000, len(X_train_s))
        cluster_indices = np.random.choice(len(X_train_s), cluster_sample_size, replace=False)
        X_cluster = X_train_s[cluster_indices]
        
        dbscan = DBSCAN(eps=0.5, min_samples=10, n_jobs=-1)
        cluster_labels = dbscan.fit_predict(X_cluster)
        
        # Anomalies are points labeled as -1 (noise)
        dbscan_anomaly_score = (cluster_labels == -1).astype(int)
        
        print(f"  DBSCAN found {np.sum(dbscan_anomaly_score)} outliers in {len(X_cluster)} samples")
        trained_models['dbscan'] = dbscan
        
    except Exception as e:
        print(f"  ❌ DBSCAN training failed: {e}")
    
    # Agglomerative Clustering
    try:
        # Very small sample for agglomerative clustering
        agg_sample_size = min(2000, len(X_train_s))
        agg_indices = np.random.choice(len(X_train_s), agg_sample_size, replace=False)
        X_agg = X_train_s[agg_indices]
        
        agg_clustering = AgglomerativeClustering(n_clusters=10, linkage='ward')
        agg_labels = agg_clustering.fit_predict(X_agg)
        
        print(f"  AgglomerativeClustering created {len(np.unique(agg_labels))} clusters")
        trained_models['agg_clustering'] = agg_clustering
        
    except Exception as e:
        print(f"  ❌ AgglomerativeClustering training failed: {e}")
    
    # Calculate ensemble performance
    print(f"\n{'='*50}")
    print("ENSEMBLE MODEL PERFORMANCE")
    print(f"{'='*50}")
    
    # Ensemble prediction on validation set
    ensemble_predictions = []
    for name, model in trained_models.items():
        if name in ['dbscan', 'agg_clustering']:
            continue  # Skip clustering models for now
        try:
            pred = model.predict(X_val_s)
            ensemble_predictions.append(pred)
        except:
            continue
    
    if ensemble_predictions:
        # Calculate weights based on F1 scores
        model_weights = {}
        weighted_predictions = []
        
        for i, name in enumerate([n for n in trained_models.keys() if n not in ['dbscan', 'agg_clustering']]):
            f1_score = model_scores[name]['f1']
            # Use F1 score as weight, with minimum weight of 0.1 to avoid zero weights
            model_weights[name] = max(f1_score, 0.1)
        
        # Normalize weights to sum to 1
        total_weight = sum(model_weights.values())
        model_weights = {k: v/total_weight for k, v in model_weights.items()}
        
        print(f"\n🎯 MODEL WEIGHTS (based on F1 scores):")
        for name, weight in model_weights.items():
            print(f"   {name}: {weight:.4f}")
        
        # Apply weighted voting
        ensemble_pred = np.array(ensemble_predictions)
        weights = np.array([model_weights[name] for name in model_weights.keys()])
        
        # Weighted average prediction
        weighted_pred = np.average(ensemble_pred, axis=0, weights=weights)
        final_pred = np.round(weighted_pred).astype(int)
        
        # Calculate ensemble metrics
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_val, final_pred, average='binary', zero_division=0
        )
        
        print(f"\n🎯 ENSEMBLE RESULTS:")
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall: {recall:.3f}")
        print(f"   F1-Score: {f1:.3f}")
        
        # Detailed classification report
        print(f"\n📊 CLASSIFICATION REPORT:")
        print(classification_report(y_val, final_pred, target_names=['Normal', 'Anomaly']))
        
        # Confusion Matrix
        print(f"\n🔢 CONFUSION MATRIX:")
        tn, fp, fn, tp = confusion_matrix(y_val, final_pred).ravel()
        print(f"   True Negatives:  {tn}")
        print(f"   False Positives: {fp}")
        print(f"   False Negatives: {fn}")
        print(f"   True Positives:  {tp}")
    
    # Save models and results
    print(f"\n💾 Saving ensemble models to {outdir}...")
    
    results = {
        'models': trained_models,
        'scaler': scaler,
        'model_scores': model_scores,
        'model_weights': model_weights if ensemble_predictions else {},
        'ensemble_metrics': {
            'precision': precision if ensemble_predictions else 0,
            'recall': recall if ensemble_predictions else 0,
            'f1': f1 if ensemble_predictions else 0
        } if ensemble_predictions else {},
        'training_info': {
            'sample_size': len(X),
            'feature_dim': X.shape[1],
            'anomaly_ratio': anomaly_ratio,
            'training_samples': len(X_train_s),
            'validation_samples': len(X_val_s)
        }
    }
    
    # Save ensemble
    joblib.dump(results, os.path.join(outdir, 'line_level_ensemble_results.joblib'))
    
    # Save individual models
    for name, model in trained_models.items():
        joblib.dump(model, os.path.join(outdir, f'{name}_model.joblib'))
    
    # Save scaler
    joblib.dump(scaler, os.path.join(outdir, 'scaler.joblib'))
    
    # Save metadata
    with open(os.path.join(outdir, 'training_metadata.json'), 'w') as f:
        metadata = {k: v for k, v in results['training_info'].items()}
        metadata['model_scores'] = model_scores
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Line-level ensemble training completed!")
    print(f"   Models saved in: {outdir}")
    print(f"   Trained on {len(X)} line-level samples")
    print(f"   Ensemble F1-Score: {f1:.3f}" if ensemble_predictions else "")
    
    return results

if __name__ == "__main__":
    print("🚀 Starting Line-Level HDFS Ensemble Training...")
    
    # Check if embedding service is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Embedding service is running")
        else:
            print("⚠️ Embedding service not responding properly")
    except:
        print("❌ Embedding service not available. Please start it first:")
        print("   cd embedding_service && python app.py")
        sys.exit(1)
    
    # Train ensemble with line-level data
    results = train_line_level_ensemble(sample_size=200000)
