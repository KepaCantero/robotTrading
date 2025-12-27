# FASE 6: Advanced Modules - XAI, Synthetic Data, Knowledge Graph

Comprehensive documentation for advanced AI/ML modules enabling explainability, synthetic data generation, and knowledge-based trading analysis.

## Overview

FASE 6 implements three cutting-edge capabilities for algorithmic trading:

1. **Explainable AI (XAI)**: Understand why models make predictions using SHAP and LIME
2. **Synthetic Data Generation**: Augment training data using GANs for improved model robustness
3. **Knowledge Graph**: Model trading relationships and discover trading patterns using Neo4j

## Table of Contents

1. [Module 1: Explainable AI (XAI)](#module-1-explainable-ai-xai)
2. [Module 2: Synthetic Data Generation](#module-2-synthetic-data-generation)
3. [Module 3: Knowledge Graph](#module-3-knowledge-graph)
4. [Integration & Usage](#integration--usage)
5. [Performance Considerations](#performance-considerations)
6. [Troubleshooting](#troubleshooting)

---

## Module 1: Explainable AI (XAI)

### Purpose

Provides transparency and interpretability for trading model predictions, crucial for:
- **Regulatory Compliance**: Understand model decisions for auditing
- **Risk Management**: Identify which factors drive predictions
- **Model Debugging**: Find biases and improvement areas
- **Stakeholder Trust**: Explain trading decisions to non-technical teams

### Architecture

```
┌─────────────────────────────────────────────────┐
│         XAI Explainer Interface                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐    ┌──────────────┐          │
│  │ SHAP         │    │ LIME         │          │
│  │ Explainer    │    │ Explainer    │          │
│  └──────────────┘    └──────────────┘          │
│         │                   │                  │
│         └───────────┬───────┘                  │
│                     │                          │
│         ┌───────────▼────────────┐             │
│         │ Feature Importance     │             │
│         │ Calculator            │             │
│         └───────────┬────────────┘             │
│                     │                          │
│         ┌───────────▼────────────┐             │
│         │ Interpretation         │             │
│         │ Report Generator       │             │
│         └────────────────────────┘             │
└─────────────────────────────────────────────────┘
```

### Components

#### 1. SHAPExplainer

**SHAP (SHapley Additive exPlanations)**: Game theory-based approach to explain predictions

```python
from app.services.xai import SHAPExplainer, get_shap_explainer

# Initialize explainer
explainer = get_shap_explainer(model, training_data)
await explainer.connect()

# Explain single prediction
explanation = await explainer.explain_prediction(
    sample=input_features,
    feature_names=['feature_1', 'feature_2', ...],
    prediction_id='pred_001',
    model_name='trading_model_v1'
)

# Get SHAP values
shap_values = explanation['shap_values']
# [
#     {
#         "feature_name": "volume",
#         "feature_value": 1500000,
#         "shap_value": 0.15,  # Contribution to prediction
#         "base_value": 0.5     # Model's average prediction
#     },
#     ...
# ]

# Explain multiple predictions
explanations = await explainer.explain_batch(
    samples=batch_data,
    feature_names=feature_names
)
```

**Use Cases:**
- Why was this trade executed?
- Which factors contributed most to this prediction?
- How much did volume affect the prediction vs. price?

#### 2. LIMEExplainer

**LIME (Local Interpretable Model-agnostic Explanations)**: Local surrogate models for interpretability

```python
from app.services.xai import LIMEExplainer, get_lime_explainer

# Initialize explainer (model-agnostic, works with any model)
explainer = get_lime_explainer(model, training_data)
await explainer.connect()

# Explain prediction with top 5 features
explanation = await explainer.explain_prediction(
    sample=input_features,
    feature_names=['price', 'volume', 'rsi', 'macd', 'atr'],
    prediction_id='pred_001',
    num_features=5
)

# Get LIME explanation
for feature in explanation['explanation']:
    print(f"{feature['feature_name']}: {feature['contribution']:.3f}")
    # Output:
    # price: 0.350
    # rsi: 0.250
    # volume: 0.200
    # ...
```

**Use Cases:**
- Local explanations for specific market conditions
- Simplified feature importance for specific prediction
- Compare explanations across different models

#### 3. FeatureImportanceCalculator

**Multiple importance calculation methods:**

```python
from app.services.xai import FeatureImportanceCalculator, get_importance_calculator

# Initialize calculator
calc = get_importance_calculator(model, X_data, y_data)

# Permutation importance (model-agnostic)
perm_importance = await calc.calculate_permutation_importance(
    feature_names=feature_names,
    n_repeats=10
)

# Tree-based importance (for tree models)
tree_importance = await calc.calculate_tree_importance(feature_names)

# All methods at once
all_importance = await calc.calculate_all_importance_methods(feature_names)

# Results
# {
#     "permutation": {
#         "price": 0.45,
#         "volume": 0.30,
#         ...
#     },
#     "tree": {
#         "price": 0.42,
#         "volume": 0.28,
#         ...
#     }
# }
```

### Output Models

```python
from app.services.xai import PredictionExplanation, InterpretationReport

# Single prediction explanation
explanation = PredictionExplanation(
    prediction_id="pred_001",
    prediction_value=0.75,
    actual_value=0.80,
    prediction_confidence=0.85,
    shap_explanation={...},      # SHAP details
    lime_explanation={...},      # LIME details
    feature_importance=[...],    # Importance scores
    model_name="trading_model_v1"
)

# Comprehensive interpretation report
report = InterpretationReport(
    model_name="trading_model_v1",
    num_samples_analyzed=1000,
    feature_importance={...},
    sample_explanations=[...],   # Multiple explained predictions
    insights={
        "most_important_feature": "volume",
        "model_stability": "high",
        ...
    },
    recommendations=[
        "Feature 'price' is surprisingly unimportant; consider removing",
        "Model relies heavily on short-term momentum signals",
        ...
    ]
)
```

---

## Module 2: Synthetic Data Generation

### Purpose

Generate synthetic market data to:
- **Augment Training Data**: Increase dataset size without additional collection cost
- **Test Robustness**: Evaluate strategy performance on diverse market conditions
- **Reduce Overfitting**: Train models on synthesized variations
- **Backtesting**: Generate alternative market scenarios
- **Privacy**: Protect real market data while maintaining characteristics

### Architecture

```
┌─────────────────────────────────────────────────┐
│         Synthetic Data Generator                │
├─────────────────────────────────────────────────┤
│                                                 │
│  Real Market Data                               │
│         │                                       │
│         ▼                                       │
│  ┌──────────────────┐                          │
│  │ Data Preparation │ (Normalization)          │
│  └────────┬─────────┘                          │
│           │                                    │
│           ▼                                    │
│  ┌──────────────────┐     ┌────────────────┐  │
│  │ Generator        │────▶│ Discriminator  │  │
│  │ (G Network)      │     │ (D Network)    │  │
│  └──────┬───────────┘     └────────┬───────┘  │
│         │                         │           │
│         │◀────── Adversarial Training ─────▶│ │
│         │                                    │
│         ▼                                    │
│  Synthetic Data (OHLCV)                      │
│         │                                    │
│         ▼                                    │
│  ┌──────────────────┐                       │
│  │ Quality          │ (Metrics & Validation)│
│  │ Evaluation       │                       │
│  └──────────────────┘                       │
└─────────────────────────────────────────────────┘
```

### Components

#### 1. SyntheticDataGenerator

**GAN-based generator for OHLCV data:**

```python
from app.services.synthetic_data import (
    SyntheticDataGenerator,
    GANConfig,
    get_gan_generator
)

# Configure GAN
config = GANConfig(
    epochs=1000,
    batch_size=64,
    learning_rate=0.0002,
    latent_dim=100,
    output_dim=5,  # OHLCV
    normalize_data=True,
    normalization_method="minmax"
)

# Initialize generator
gen = get_gan_generator(config)
await gen.connect()

# Train on historical data
historical_data = load_ohlcv_data()  # Shape: [samples, 5]
result = await gen.train(historical_data)

# Generate synthetic data
num_synthetic_samples = 1000
synthetic_data = await gen.generate_samples(num_synthetic_samples)

# Structure: [1000, 5] representing 1000 OHLCV bars

# Evaluate quality
quality_metrics = await gen.evaluate_quality(synthetic_data, historical_data)

# {
#     "mean_difference": 0.02,     # Mean price difference
#     "std_difference": 0.05,      # Volatility difference
#     "correlation_difference": 0.03,
#     "wasserstein_distance": 0.15,
#     "quality_score": 0.92        # 0-1, higher is better
# }
```

#### 2. TimeSeriesGANGenerator

**Specialized for time series sequences:**

```python
from app.services.synthetic_data import TimeSeriesGANGenerator, get_ts_gan_generator

# Initialize time series GAN
ts_gen = get_ts_gan_generator()
await ts_gen.connect()

# Generate sequences of 30-day OHLCV data
num_sequences = 100
sequences = await ts_gen.generate_sequences(num_sequences, sequence_length=30)

# Structure: [100, 30, 5] = 100 sequences of 30 days of OHLCV

# Use for:
# - Training LSTM/Transformer models
# - Backtesting with alternative market sequences
# - Stress testing on synthesized scenarios
```

### Quality Metrics

```python
quality_metrics = {
    "mean_difference": float,          # Average price difference
    "std_difference": float,           # Volatility difference
    "correlation_difference": float,   # Feature correlation difference
    "wasserstein_distance": float,     # Distribution distance
    "quality_score": float             # Overall quality (0-1)
}

# Interpretation:
# Quality Score > 0.9: Excellent synthetic data
# Quality Score 0.8-0.9: Good synthetic data
# Quality Score < 0.8: Needs improvement
```

### Use Cases

```python
# 1. Data Augmentation
synthetic_data = await gen.generate_samples(5000)
combined_data = np.vstack([historical_data, synthetic_data])
model.train(combined_data)  # Train on more data

# 2. Stress Testing
for crisis_scenario in stress_scenarios:
    synthetic = await gen.generate_samples(1000, conditions=crisis_scenario)
    backtest_results = strategy.backtest(synthetic)

# 3. Alternative Futures
alternative_markets = await ts_gen.generate_sequences(100)
for market in alternative_markets:
    portfolio_pnl.append(strategy.simulate(market))
```

---

## Module 3: Knowledge Graph

### Purpose

Build and leverage knowledge graphs to:
- **Discover Relationships**: Find correlated assets and co-moving pairs
- **Pattern Discovery**: Identify strategy clusters and historical patterns
- **Portfolio Optimization**: Recommendations based on relationship analysis
- **Risk Analysis**: Understand systemic correlations and dependencies
- **Strategy Backtesting**: Test hypotheses against historical patterns

### Architecture

```
┌──────────────────────────────────────────────────┐
│         Knowledge Graph (Neo4j)                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │           Node Types                     │   │
│  ├──────────────────────────────────────────┤   │
│  │ • Asset (stocks, ETFs, crypto)           │   │
│  │ • Strategy (momentum, value, arbitrage)  │   │
│  │ • Performance (historical results)       │   │
│  │ • Market Events (earnings, dividends)    │   │
│  └──────────────────────────────────────────┘   │
│                    │                             │
│  ┌──────────────────▼──────────────────────┐   │
│  │        Relationship Types                │   │
│  ├──────────────────────────────────────────┤   │
│  │ • CORRELATED_WITH (strength 0-1)        │   │
│  │ • TRADES (strategy→asset)                │   │
│  │ • HAS_PERFORMANCE (strategy→performance) │   │
│  │ • AFFECTS (event→asset)                 │   │
│  └──────────────────┬──────────────────────┘   │
│                     │                          │
│  ┌──────────────────▼──────────────────────┐   │
│  │      Query Engine                        │   │
│  ├──────────────────────────────────────────┤   │
│  │ • Path finding (strategy→profitable)     │   │
│  │ • Similarity (find similar assets)       │   │
│  │ • Community detection (asset clusters)   │   │
│  │ • Centrality analysis (important assets) │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

### Components

#### 1. Asset Graph

```python
from app.services.knowledge_graph import KnowledgeGraphBuilder, get_knowledge_graph_builder

# Initialize builder
builder = get_knowledge_graph_builder(
    graph_uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)
await builder.connect()

# Create asset nodes
assets = [
    {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "stock"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "type": "stock"},
]
await builder.create_asset_nodes(assets)

# Create correlations
correlations = [
    {"symbol1": "AAPL", "symbol2": "MSFT", "strength": 0.85},
    {"symbol1": "GOOGL", "symbol2": "MSFT", "strength": 0.78},
]
await builder.create_correlation_relationships(correlations)
```

#### 2. Strategy Graph

```python
# Create strategy nodes
strategies = [
    {"name": "momentum_strategy", "type": "momentum", "risk_level": 0.5},
    {"name": "value_strategy", "type": "value", "risk_level": 0.3},
]
await builder.create_strategy_nodes(strategies)

# Create strategy-asset relationships (which strategies trade which assets)
relationships = [
    {"strategy": "momentum_strategy", "symbol": "AAPL", "weight": 1.0},
    {"strategy": "momentum_strategy", "symbol": "GOOGL", "weight": 0.8},
    {"strategy": "value_strategy", "symbol": "MSFT", "weight": 1.0},
]
await builder.create_strategy_asset_relationships(relationships)
```

#### 3. Performance Graph

```python
# Create performance nodes
performances = [
    {
        "strategy": "momentum_strategy",
        "return": 0.25,
        "sharpe": 1.8,
        "date": "2025-01-31"
    },
    {
        "strategy": "value_strategy",
        "return": 0.18,
        "sharpe": 1.5,
        "date": "2025-01-31"
    }
]
await builder.create_performance_nodes(performances)
```

### Queries

#### Find Similar Assets

```python
# Find assets most correlated with AAPL
similar = await builder.find_similar_assets("AAPL", limit=10)

# Result:
# [
#     {"symbol": "MSFT", "correlation": 0.85},
#     {"symbol": "GOOGL", "correlation": 0.78},
#     ...
# ]
```

#### Find Best Strategies for Asset

```python
# Which strategies perform best on AAPL?
best_strategies = await builder.find_best_strategies_for_asset("AAPL", limit=5)

# Result:
# [
#     {
#         "strategy": "momentum_strategy",
#         "return_pct": 25.0,
#         "sharpe_ratio": 1.8,
#         "win_rate": 0.65
#     },
#     ...
# ]
```

#### Network Analysis

```python
# Get strategy network statistics
network = await builder.get_strategy_network()

# {
#     "num_strategies": 10,
#     "num_assets": 50,
#     "num_relationships": 150,
#     "average_degree": 15,
#     "clustering_coefficient": 0.35
# }
```

#### Portfolio Recommendations

```python
# Get recommendations for current holdings
current_holdings = ["AAPL", "GOOGL"]
recommendations = await builder.get_asset_portfolio_recommendations(
    current_holdings,
    target_diversification=0.5
)

# Result:
# [
#     {
#         "symbol": "JPM",
#         "reason": "Low correlation with current holdings",
#         "expected_return_pct": 12.0,
#         "correlation_with_portfolio": 0.25
#     },
#     ...
# ]
```

---

## Integration & Usage

### End-to-End Example: Interpretable Trading System

```python
# 1. Train model and explain predictions
model = train_trading_model()
explainer = get_shap_explainer(model, training_data)
await explainer.connect()

# Explain trading signal
signal = model.predict(current_market_data)
explanation = await explainer.explain_prediction(
    current_market_data,
    feature_names=feature_names,
    model_name="trading_model_v1"
)

print(f"Signal: {signal}")
print(f"Explanation: {explanation['shap_values']}")
# Output:
# Signal: BUY
# Explanation:
#   - volume (high): +0.35
#   - rsi (low): +0.25
#   - price_trend (positive): +0.15
#   - ... (other factors)

# 2. Generate synthetic data for testing
gen = get_gan_generator()
await gen.connect()
await gen.train(historical_ohlcv)
synthetic_data = await gen.generate_samples(5000)

# 3. Backtest on synthetic scenarios
backtest_results = strategy.backtest(synthetic_data)

# 4. Analyze trading relationships
builder = get_knowledge_graph_builder()
await builder.connect()

# Find assets that benefit from same strategies
related = await builder.find_similar_assets(trading_symbol)

# Get portfolio recommendations
recommendations = await builder.get_asset_portfolio_recommendations(
    current_holdings
)

# 5. Generate interpretation report
report = InterpretationReport(
    model_name="trading_model_v1",
    num_samples_analyzed=1000,
    feature_importance=await calc.calculate_all_importance_methods(features),
    sample_explanations=[explanation],
    insights={
        "top_3_factors": ["volume", "rsi", "price_trend"],
        "model_bias": "prefers momentum over fundamental value"
    }
)
```

---

## Performance Considerations

### SHAP Computation

- **Complexity**: O(2^f) for f features (exponential)
- **Solution**: Use approximate methods (sampling, kernel SHAP)
- **Typical Time**: 100-500ms per prediction for 10-20 features
- **Optimization**: Batch processing, caching base values

### LIME Computation

- **Complexity**: O(n*s) for n samples, s LIME samples (linear)
- **Typical Time**: 50-200ms per prediction
- **Advantage**: Faster than SHAP, model-agnostic
- **Trade-off**: Local approximation, less globally informative

### GAN Training

- **Computation**: GPU recommended (100x+ speedup)
- **Memory**: 4-8GB typical
- **Training Time**: Minutes to hours depending on data size
- **Inference**: <10ms per sample

### Knowledge Graph Queries

- **Node Creation**: O(n) for n nodes
- **Path Finding**: O(V+E) for V vertices, E edges
- **Typical Scale**: 1000s of nodes, 10000s of edges
- **Query Time**: <100ms for most queries

---

## Troubleshooting

### SHAP Issues

```python
# Problem: Memory error with large datasets
# Solution: Use SHAP's sample-based explanation
from shap import KernelExplainer
explainer = KernelExplainer(model.predict, shap.sample(X, 100))

# Problem: Slow computation
# Solution: Use background sample subset
background = X[:100]  # Use 100 samples instead of all
explainer = shap.TreeExplainer(model, data=background)
```

### GAN Issues

```python
# Problem: Mode collapse (generator produces limited variety)
# Solution: Adjust training parameters
config = GANConfig(
    learning_rate=0.0002,
    gradient_penalty_weight=10.0,  # Increase penalty
    discriminator_loss_weight=0.5  # Balance losses
)

# Problem: Poor synthetic data quality
# Solution: Longer training and more epochs
config = GANConfig(epochs=10000, batch_size=32)
```

### Neo4j Connection Issues

```python
# Problem: Cannot connect to Neo4j
# Solution: Verify connection parameters
builder = KnowledgeGraphBuilder(
    graph_uri="bolt://localhost:7687",  # Check port
    user="neo4j",
    password="password"  # Check credentials
)

# Verify database is running
# docker ps | grep neo4j
# http://localhost:7474  # Neo4j browser
```

---

## Dependencies

Add to `requirements.txt`:

```
# FASE 6.1: Explainable AI
shap>=0.42.0,<1.0.0
lime>=0.2.0,<1.0.0
eli5>=0.11.0,<1.0.0

# FASE 6.2: Synthetic Data
tensorflow>=2.13.0,<3.0.0  # For GAN implementation
torch>=2.0.0,<3.0.0  # Alternative to TensorFlow

# FASE 6.3: Knowledge Graph
neo4j>=5.0.0,<6.0.0
networkx>=3.0,<4.0.0  # Graph analysis
```

---

## Next Steps

1. **Model Interpretability**: Generate SHAP values for all predictions
2. **Data Augmentation**: Train models on 50/50 real/synthetic data
3. **Strategy Optimization**: Use knowledge graph to discover new strategies
4. **Regulatory Reporting**: Generate interpretability reports for compliance
5. **Real-time Explanations**: Serve explanations alongside predictions via API

---

## References

- **SHAP**: https://github.com/slundberg/shap
- **LIME**: https://github.com/marcotcr/lime
- **GANs**: https://arxiv.org/abs/1406.2661
- **Knowledge Graphs**: https://neo4j.com/
