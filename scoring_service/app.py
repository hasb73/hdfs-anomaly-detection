# Suppress urllib3 SSL warnings
import warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import joblib, numpy as np, os, hashlib, time
import requests
import json
import redis
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from kafka import KafkaConsumer
from typing import List, Dict, Optional
import threading
import queue
import asyncio
import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('anomaly_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InputPayload(BaseModel):
    embedding: list

class TextPayload(BaseModel):
    text: str

class BatchPayload(BaseModel):
    texts: List[str]

app = FastAPI(title="HDFS Anomaly Scoring Service", version="1.0.0")

# Configuration
MODEL_PATH = os.environ.get('ENSEMBLE_MODEL_PATH', '/Users/hasanb/Desktop/MDX-DOCS/CST-4090/code/thesis_real_time_log_anomaly_repo/ensemble/models/line_level_ensemble/line_level_ensemble_results.joblib')
EMBEDDING_SERVICE_URL = os.environ.get('EMBEDDING_SERVICE_URL', 'http://localhost:8000')
KAFKA_SERVERS = os.environ.get('KAFKA_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'logs')
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
QDRANT_HOST = os.environ.get('QDRANT_HOST', 'localhost')
QDRANT_PORT = int(os.environ.get('QDRANT_PORT', '6333'))
QDRANT_COLLECTION = os.environ.get('QDRANT_COLLECTION', 'logs_embeddings')

# Global variables
models_cache = None
scaler = None
prediction_queue = queue.Queue()
redis_client = None
qdrant_client = None

# Statistics
stats = {
    'total_predictions': 0,
    'anomalies_detected': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'kafka_messages_processed': 0,
    'qdrant_queries': 0,
    'redis_operations': 0
}

# Store detailed anomaly records
anomaly_history = []

def initialize_connections():
    """Initialize Redis and Qdrant connections"""
    global redis_client, qdrant_client
    
    try:
        # Initialize Redis
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        redis_client.ping()
        logger.info(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        redis_client = None
    
    try:
        # Initialize Qdrant
        qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        logger.info(f"✅ Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
    except Exception as e:
        logger.error(f"❌ Qdrant connection failed: {e}")
        qdrant_client = None

def get_text_hash(text: str) -> str:
    """Generate hash for text for caching"""
    return hashlib.md5(text.encode()).hexdigest()

def get_cached_result(text_hash: str) -> Optional[Dict]:
    """Get cached anomaly result from Redis"""
    global stats
    
    if redis_client is None:
        return None
    
    try:
        cached = redis_client.get(f"anomaly:{text_hash}")
        stats['redis_operations'] += 1
        
        if cached:
            stats['cache_hits'] += 1
            result = json.loads(cached)
            logger.info(f"🎯 Cache HIT for hash {text_hash[:8]}...")
            return result
        else:
            stats['cache_misses'] += 1
            return None
            
    except Exception as e:
        logger.error(f"Redis get error: {e}")
        return None

def cache_result(text_hash: str, result: Dict, ttl: int = 3600):
    """Cache anomaly result in Redis"""
    global stats
    
    if redis_client is None:
        return
    
    try:
        redis_client.setex(
            f"anomaly:{text_hash}", 
            ttl, 
            json.dumps(result)
        )
        stats['redis_operations'] += 1
        logger.info(f"💾 Cached result for hash {text_hash[:8]}... (TTL: {ttl}s)")
        
    except Exception as e:
        logger.error(f"Redis set error: {e}")

def delete_cached_result(text_hash: str):
    """Delete cached result from Redis"""
    global stats
    
    if redis_client is None:
        return False
    
    try:
        deleted = redis_client.delete(f"anomaly:{text_hash}")
        stats['redis_operations'] += 1
        logger.info(f"🗑️ Deleted cache for hash {text_hash[:8]}...")
        return deleted > 0
        
    except Exception as e:
        logger.error(f"Redis delete error: {e}")
        return False

def search_qdrant_by_text(text: str, limit: int = 1) -> Optional[List[Dict]]:
    """Search for existing embeddings in Qdrant by text similarity"""
    global stats
    
    if qdrant_client is None:
        return None
    
    try:
        # First, get embedding for the query text
        embedding = get_embedding(text)
        if not embedding:
            return None
        
        # Search in Qdrant
        results = qdrant_client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=embedding,
            limit=limit,
            score_threshold=0.95,  # High similarity threshold
            with_payload=True
        )
        
        stats['qdrant_queries'] += 1
        
        if results:
            logger.info(f"🎯 Qdrant found {len(results)} similar embeddings")
            return [
                {
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload,
                    'embedding': result.vector if hasattr(result, 'vector') else None
                } for result in results
            ]
        
        return None
        
    except Exception as e:
        logger.error(f"Qdrant search error: {e}")
        return None

def get_embedding_from_qdrant_or_service(text: str) -> Optional[List[float]]:
    """Get embedding from Qdrant first, then embedding service as fallback"""
    
    # Try Qdrant first
    qdrant_results = search_qdrant_by_text(text)
    if qdrant_results and len(qdrant_results) > 0:
        # Use the most similar embedding from Qdrant
        best_match = qdrant_results[0]
        if best_match['score'] > 0.98:  # Very high similarity
            logger.info(f"🎯 Using Qdrant embedding (similarity: {best_match['score']:.3f})")
            return best_match['embedding'] if best_match['embedding'] else get_embedding(text)
    
    # Fallback to embedding service
    logger.info("🔄 Fallback to embedding service")
    return get_embedding(text)

def load_ensemble_model():
    """Load the trained ensemble model"""
    global models_cache, scaler
    
    if os.path.exists(MODEL_PATH):
        logger.info(f"📥 Loading ensemble model from {MODEL_PATH}")
        models_cache = joblib.load(MODEL_PATH)
        scaler = models_cache.get('scaler', None)
        models = models_cache.get('models', {})
        logger.info(f"✅ Loaded ensemble with {len(models)} models")
        
        # Print model performance
        if 'ensemble_score' in models_cache:
            score = models_cache['ensemble_score']
            logger.info(f"   Model Performance - P: {score.get('precision', 0):.3f}, R: {score.get('recall', 0):.3f}, F1: {score.get('f1', 0):.3f}")
            
        return True
    else:
        logger.error(f"❌ Model not found at {MODEL_PATH}")
        return False

@app.on_event('startup')
async def startup_event():
    """Initialize the scoring service"""
    global models_cache, scaler
    
    logger.info("🚀 Starting Enhanced HDFS Anomaly Scoring Service...")
    
    # Initialize connections
    initialize_connections()
    
    # Load model
    if not load_ensemble_model():
        logger.warning("⚠️ Warning: No ensemble model loaded. Training required.")
    
    # Start Kafka consumer in background (optional)
    if os.environ.get('ENABLE_KAFKA_CONSUMER', 'false').lower() == 'true':
        threading.Thread(target=kafka_consumer_worker, daemon=True).start()
        logger.info("📡 Kafka consumer started")
    
    logger.info("✅ Enhanced service ready with Redis caching and Qdrant integration!")

def get_embedding(text: str) -> Optional[List[float]]:
    """Get embedding for a single text"""
    try:
        response = requests.post(
            f"{EMBEDDING_SERVICE_URL}/embed",
            json={"texts": [text]},
            timeout=10
        )
        if response.status_code == 200:
            embeddings = response.json().get("embeddings", [])
            return embeddings[0] if embeddings else None
        return None
    except Exception as e:
        logger.error(f"Embedding service error: {e}")
        return None

def predict_ensemble(embedding: np.ndarray) -> Dict:
    """Make prediction using ensemble model with weighted voting"""
    global stats
    
    if models_cache is None:
        raise HTTPException(status_code=500, detail='Ensemble model not loaded')
    
    # Reshape embedding
    vec = embedding.reshape(1, -1)
    
    # Scale features
    if scaler is not None:
        try:
            vec_scaled = scaler.transform(vec)
        except Exception:
            vec_scaled = vec
    else:
        vec_scaled = vec
    
    # Get predictions from all models
    predictions = []
    model_names = []
    
    models = models_cache.get('models', {})
    for name, model in models.items():
        if hasattr(model, 'predict'):
            try:
                pred = int(model.predict(vec_scaled)[0])
                predictions.append(pred)
                model_names.append(name)
            except Exception as e:
                logger.warning(f"Model {name} prediction failed: {e}")
                predictions.append(0)
                model_names.append(name)
    
    votes = np.array(predictions)
    
    # Check if we have saved model weights for weighted voting
    model_weights = models_cache.get('model_weights', {})
    if model_weights and len(model_weights) > 0:
        # Use weighted voting
        weights = []
        for name in model_names:
            weight = model_weights.get(name, 0.1)  # Default weight if not found
            weights.append(weight)
        
        weights = np.array(weights)
        if weights.sum() > 0:
            weights = weights / weights.sum()  # Normalize weights
            anomaly_score = float(np.average(votes, weights=weights))
            logger.debug(f"Using weighted voting: {dict(zip(model_names, weights))}")
        else:
            # Fallback to simple average
            anomaly_score = float(votes.mean())
            logger.warning("All weights are zero, falling back to simple average")
    else:
        # Fallback to simple average voting
        anomaly_score = float(votes.mean())
        logger.debug("Using simple average voting (no weights available)")
    
    final_prediction = int(anomaly_score > 0.5)
    
    # Update statistics
    stats['total_predictions'] += 1
    if final_prediction == 1:
        stats['anomalies_detected'] += 1
    
    return {
        'prediction': final_prediction,
        'anomaly_score': anomaly_score,
        'confidence': max(anomaly_score, 1 - anomaly_score),
        'model_votes': dict(zip(model_names, predictions)),
        'vote_counts': {'normal': int(np.sum(votes == 0)), 'anomaly': int(np.sum(votes == 1))},
        'weights_used': model_weights if model_weights else 'equal_weights'
    }

@app.post('/score_embedding')
def score_embedding(payload: InputPayload):
    """Score a pre-computed embedding"""
    try:
        embedding = np.array(payload.embedding, dtype=float)
        result = predict_ensemble(embedding)
        result['input_type'] = 'embedding'
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

@app.post('/score')
def score_text(payload: TextPayload):
    """Score a single text for anomaly detection with caching"""
    try:
        text = payload.text
        text_hash = get_text_hash(text)
        
        # Check cache first
        cached_result = get_cached_result(text_hash)
        if cached_result:
            logger.info(f"🎯 Returning cached result for: {text[:50]}...")
            return cached_result
        
        # Get embedding from Qdrant or embedding service
        embedding = get_embedding_from_qdrant_or_service(text)
        
        if embedding is None:
            raise HTTPException(status_code=500, detail="Failed to get embedding")
        
        # Make prediction
        result = predict_ensemble(np.array(embedding))
        result['text'] = text
        result['text_hash'] = text_hash
        
        # Cache the result
        cache_result(text_hash, result)
        
        # Log anomalies
        if result['prediction'] == 1:
            logger.warning(f"� ANOMALY DETECTED: {text[:80]}... (score: {result['anomaly_score']:.3f})")
            
            # Store in anomaly history
            anomaly_record = {
                'timestamp': datetime.datetime.now().isoformat(),
                'text': text,
                'text_hash': text_hash,
                'anomaly_score': result['anomaly_score'],
                'confidence': result['confidence'],
                'model_votes': result['model_votes'],
                'vote_counts': result['vote_counts']
            }
            anomaly_history.append(anomaly_record)
            
            # Keep only last 500 anomalies
            if len(anomaly_history) > 500:
                anomaly_history.pop(0)
        
        return result
        
    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

@app.post('/score_batch')
def score_batch(payload: BatchPayload):
    """Score multiple texts for anomaly detection with caching"""
    try:
        results = []
        cache_hits = 0
        
        for i, text in enumerate(payload.texts):
            text_hash = get_text_hash(text)
            
            # Check cache first
            cached_result = get_cached_result(text_hash)
            if cached_result:
                cached_result['text'] = text
                cached_result['index'] = i
                cached_result['from_cache'] = True
                results.append(cached_result)
                cache_hits += 1
                continue
            
            # Get embedding from Qdrant or embedding service
            embedding = get_embedding_from_qdrant_or_service(text)
            if embedding:
                result = predict_ensemble(np.array(embedding))
                result['text'] = text
                result['text_hash'] = text_hash
                result['index'] = i
                result['from_cache'] = False
                
                # Cache the result
                cache_result(text_hash, result)
                results.append(result)
                
                # Log anomalies
                if result['prediction'] == 1:
                    logger.warning(f"🚨 BATCH ANOMALY: {text[:60]}... (score: {result['anomaly_score']:.3f})")
            else:
                results.append({
                    'text': text,
                    'index': i,
                    'error': 'Failed to get embedding',
                    'prediction': 0,
                    'anomaly_score': 0.0,
                    'from_cache': False
                })
        
        # Summary statistics
        anomaly_count = sum(1 for r in results if r.get('prediction', 0) == 1)
        
        logger.info(f"📊 Batch scoring: {len(results)} texts, {cache_hits} cache hits, {anomaly_count} anomalies")
        
        return {
            'results': results,
            'summary': {
                'total': len(results),
                'anomalies': anomaly_count,
                'normal': len(results) - anomaly_count,
                'anomaly_rate': anomaly_count / len(results) if results else 0,
                'cache_hits': cache_hits,
                'cache_hit_rate': cache_hits / len(results) if results else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Batch scoring failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch scoring failed: {str(e)}")

@app.get('/stats')
def get_stats():
    """Get service statistics"""
    return stats

@app.get('/anomalies')
def get_anomaly_history():
    """Get detailed history of detected anomalies"""
    return {
        'total_anomalies': len(anomaly_history),
        'anomalies': anomaly_history[-50:]  # Return last 50 anomalies
    }

@app.post('/cache/clear')
def clear_cache():
    """Clear all cached results"""
    if redis_client is None:
        raise HTTPException(status_code=500, detail="Redis not available")
    
    try:
        # Delete all anomaly cache keys
        keys = redis_client.keys("anomaly:*")
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"🗑️ Cleared {deleted} cached results")
            return {'message': f'Cleared {deleted} cached results'}
        else:
            return {'message': 'No cached results to clear'}
            
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@app.delete('/cache/{text_hash}')
def delete_cache_entry(text_hash: str):
    """Delete specific cached result"""
    if delete_cached_result(text_hash):
        return {'message': f'Deleted cache entry for {text_hash}'}
    else:
        raise HTTPException(status_code=404, detail="Cache entry not found")

@app.get('/cache/stats')
def get_cache_stats():
    """Get cache statistics"""
    if redis_client is None:
        return {'redis_available': False}
    
    try:
        cache_keys = redis_client.keys("anomaly:*")
        return {
            'redis_available': True,
            'cached_entries': len(cache_keys),
            'cache_hit_rate': stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses']) if (stats['cache_hits'] + stats['cache_misses']) > 0 else 0,
            'total_cache_operations': stats['redis_operations']
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {'redis_available': False, 'error': str(e)}

@app.get('/health')
def health_check():
    """Health check endpoint"""
    model_loaded = models_cache is not None
    embedding_service_available = False
    redis_available = False
    qdrant_available = False
    
    # Check embedding service
    try:
        response = requests.get(f"{EMBEDDING_SERVICE_URL}/health", timeout=5)
        embedding_service_available = response.status_code == 200
    except:
        pass
    
    # Check Redis
    if redis_client:
        try:
            redis_client.ping()
            redis_available = True
        except:
            pass
    
    # Check Qdrant
    if qdrant_client:
        try:
            qdrant_client.get_collections()
            qdrant_available = True
        except:
            pass
    
    all_services_ok = all([model_loaded, embedding_service_available, redis_available, qdrant_available])
    
    return {
        'status': 'healthy' if all_services_ok else 'degraded',
        'services': {
            'model_loaded': model_loaded,
            'embedding_service_available': embedding_service_available,
            'redis_available': redis_available,
            'qdrant_available': qdrant_available
        },
        'stats': stats
    }

@app.get('/reload_model')
def reload_model():
    """Reload the ensemble model"""
    if load_ensemble_model():
        return {'message': 'Model reloaded successfully'}
    else:
        raise HTTPException(status_code=500, detail='Failed to reload model')

def kafka_consumer_worker():
    """Background worker to consume Kafka messages and score them with caching"""
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_SERVERS,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            group_id=f'scoring_service_{int(time.time())}',
            auto_offset_reset='latest'
        )
        
        logger.info(f"📡 Enhanced Kafka consumer listening to topic: {KAFKA_TOPIC}")
        
        for message in consumer:
            try:
                data = message.value
                text = data.get('message', '')
                
                if text:
                    text_hash = get_text_hash(text)
                    
                    # Check cache first
                    cached_result = get_cached_result(text_hash)
                    if cached_result:
                        result = cached_result
                        logger.info(f"🎯 Kafka: Using cached result for {text[:50]}...")
                    else:
                        # Get embedding from Qdrant or embedding service
                        embedding = get_embedding_from_qdrant_or_service(text)
                        if embedding:
                            result = predict_ensemble(np.array(embedding))
                            result['text_hash'] = text_hash
                            
                            # Cache the result
                            cache_result(text_hash, result, ttl=1800)  # 30 min TTL for Kafka results
                        else:
                            continue
                    
                    # Store result in queue for potential retrieval
                    prediction_queue.put({
                        'kafka_offset': message.offset,
                        'text': text,
                        'text_hash': text_hash,
                        'result': result,
                        'timestamp': time.time()
                    })
                    
                    stats['kafka_messages_processed'] += 1
                    
                    # Log and store significant anomalies
                    if result['prediction'] == 1:
                        anomaly_score = result.get('anomaly_score', 0)
                        
                        anomaly_record = {
                            'timestamp': datetime.datetime.now().isoformat(),
                            'text': text,
                            'text_hash': text_hash,
                            'anomaly_score': anomaly_score,
                            'confidence': result.get('confidence', 0),
                            'model_votes': result.get('model_votes', []),
                            'vote_counts': result.get('vote_counts', {}),
                            'source': 'kafka_stream'
                        }
                        anomaly_history.append(anomaly_record)
                        
                        # Keep only last 500 anomalies
                        if len(anomaly_history) > 500:
                            anomaly_history.pop(0)
                        
                        if anomaly_score > 0.7:
                            logger.warning(f"🚨 HIGH KAFKA ANOMALY: {text[:80]}... (score: {anomaly_score:.3f})")
                        else:
                            logger.info(f"⚠️ KAFKA ANOMALY: {text[:80]}... (score: {anomaly_score:.3f})")
                
            except Exception as e:
                logger.error(f"Error processing Kafka message: {e}")
                
    except Exception as e:
        logger.error(f"Kafka consumer error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
