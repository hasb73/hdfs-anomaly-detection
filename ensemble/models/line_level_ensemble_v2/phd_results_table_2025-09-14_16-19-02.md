
# HDFS Line-Level Anomaly Detection Ensemble V2 Results
# Generated: 2025-09-14 16:19:02
# Dataset: HDFS Line-Level Logs
# Total Samples: 200,000
# Anomaly Ratio: 0.0022 (0.22%)
# Models: Decision Tree (DT), Multi-Layer Perceptron (MLP), Stochastic Gradient Descent (SGD), Qdrant Similarity
# Ensemble Method: Weighted Voting with F1-based weights


## Individual Model Performance

| Model | Precision | Recall | F1-Score | Weight | Hyperparameters |
|-------|-----------|--------|----------|--------|-----------------|
| Decision Tree | 0.0654 | 1.0000 | 0.1228 | 0.0790 | criterion=entropy, max_depth=None |
| Multi-Layer Perceptron | 0.8065 | 0.5747 | 0.6711 | 0.4315 | hidden_sizes=(50,), activation=tanh |
| Stochastic Gradient Descent | 0.0617 | 0.9885 | 0.1161 | 0.0747 | loss=hinge, penalty=l1 |
| Qdrant Similarity | 0.7353 | 0.5747 | 0.6452 | 0.4148 | threshold=0.9 |

## Ensemble Performance

| Metric | Value |
|--------|-------|
| Precision | 0.5747 |
| Recall | 0.5747 |
| F1-Score | 0.5747 |
| Weighting Method | F1-based |
| Combination Method | Weighted Voting |

## Model Comparison

| Rank | Model | F1-Score | Improvement over Best Individual |
|------|-------|----------|----------------------------------|
| 1 | Multi-Layer Perceptron | 0.6711 | +0.00% |
| 2 | Qdrant Similarity | 0.6452 | -3.87% |
| 3 | Decision Tree | 0.1228 | -81.70% |
| 4 | Stochastic Gradient Descent | 0.1161 | -82.70% |
| - | **Ensemble** | **0.5747** | **-14.37%** |

## Training Configuration

| Parameter | Value |
|-----------|-------|
| Validation Split | 20.0% |
| Feature Scaling | StandardScaler |
| Cross-Validation | 3-fold (except SGD: 2-fold) |
| Hyperparameter Tuning | GridSearchCV |
| Random State | 42 |
| Class Balancing | Stratified sampling |

## Dataset Statistics

| Statistic | Value |
|-----------|-------|
| Total Samples | 200,000 |
| Training Samples | 160,000 |
| Validation Samples | 40,000 |
| Feature Dimensions | 384 |
| Normal Samples | 199,565 (99.78%) |
| Anomalous Samples | 434 (0.22%) |
| Class Imbalance Ratio | 458.8:1 |

## Key Findings

1. **Best Individual Model**: Multi-Layer Perceptron (F1=0.6711)
2. **Ensemble Improvement**: -14.37% over best individual model
3. **Most Weighted Model**: Multi-Layer Perceptron (Weight=0.4315)
4. **Class Imbalance Challenge**: 459:1 ratio requires careful evaluation metrics
