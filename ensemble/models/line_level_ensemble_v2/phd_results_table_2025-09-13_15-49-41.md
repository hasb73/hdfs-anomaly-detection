
# HDFS Line-Level Anomaly Detection Ensemble V2 Results
# Generated: 2025-09-13 15:49:41
# Dataset: HDFS Line-Level Logs
# Total Samples: 200,000
# Anomaly Ratio: 0.0046 (0.46%)
# Models: Decision Tree (DT), Multi-Layer Perceptron (MLP), Stochastic Gradient Descent (SGD), Qdrant Similarity
# Ensemble Method: Weighted Voting with F1-based weights


## Individual Model Performance

| Model | Precision | Recall | F1-Score | Weight | Hyperparameters |
|-------|-----------|--------|----------|--------|-----------------|
| Decision Tree | 0.0279 | 0.9892 | 0.0543 | 0.1084 | criterion=gini, max_depth=None |
| Multi-Layer Perceptron | 1.0000 | 0.2204 | 0.3612 | 0.3916 | hidden_sizes=(50,), activation=relu |
| Stochastic Gradient Descent | 0.0276 | 0.9946 | 0.0536 | 0.1084 | loss=log_loss, penalty=l2 |
| Qdrant Similarity | 1.0000 | 0.2204 | 0.3612 | 0.3916 | threshold=0.5 |

## Ensemble Performance

| Metric | Value |
|--------|-------|
| Precision | 0.2486 |
| Recall | 0.2473 |
| F1-Score | 0.2480 |
| Weighting Method | F1-based |
| Combination Method | Weighted Voting |

## Model Comparison

| Rank | Model | F1-Score | Improvement over Best Individual |
|------|-------|----------|----------------------------------|
| 1 | Multi-Layer Perceptron | 0.3612 | +0.00% |
| 2 | Qdrant Similarity | 0.3612 | +0.00% |
| 3 | Decision Tree | 0.0543 | -84.97% |
| 4 | Stochastic Gradient Descent | 0.0536 | -85.15% |
| - | **Ensemble** | **0.2480** | **-31.35%** |

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
| Normal Samples | 199,072 (99.54%) |
| Anomalous Samples | 928 (0.46%) |
| Class Imbalance Ratio | 214.5:1 |

## Key Findings

1. **Best Individual Model**: Multi-Layer Perceptron (F1=0.3612)
2. **Ensemble Improvement**: -31.35% over best individual model
3. **Most Weighted Model**: Multi-Layer Perceptron (Weight=0.3916)
4. **Class Imbalance Challenge**: 215:1 ratio requires careful evaluation metrics
