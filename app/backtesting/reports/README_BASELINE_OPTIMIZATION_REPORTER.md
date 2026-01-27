# Baseline vs Optimization Comparison Reporter

Professional HTML report generator for comparing baseline and optimized trading strategies.

## Features

- **Executive Summary**: Quick overview with key metrics and improvements
- **Detailed Comparison**: Side-by-side metrics table with statistical significance
- **Parameter Analysis**: What changed and its estimated impact
- **Interactive Charts**: Plotly-powered visualizations
  - Dual equity curves (baseline vs optimized)
  - Underwater drawdown comparison
  - Risk-adjusted returns radar chart
  - Walk-forward validation charts
  - Parameter sensitivity heatmap
- **Recommendation Engine**: Automated decision logic with confidence scores
- **Implementation Guide**: Step-by-step deployment instructions

## Installation

The reporter uses the following dependencies:

```bash
pip install jinja2 plotly pandas numpy scipy
```

## Quick Start

```python
from decimal import Decimal
from app.backtesting.reports.baseline_optimization_reporter import BaselineOptimizationReporter
from app.core.models.input_profile import InputProfile

# Create input profile
profile = InputProfile(
    capital_initial=Decimal("100000"),
    objetivo_inversion="maximizar_capital",
    risk_tolerance="medio",
    investment_horizon=24,
)

# Define your results
baseline_results = {
    "start_date": "2024-01-01",
    "end_date": "2025-12-31",
    "equity_curve": [(date, value), ...],  # Your data
    "performance": {
        "sharpe_ratio": 1.2,
        "total_return": 25.0,
        "max_drawdown_percentage": -15.0,
        "win_rate": 52.0,
        "profit_factor": 1.4,
        # ... more metrics
    },
    "parameters": {
        "lookback_period": 20,
        "entry_threshold": 2.0,
        # ... more parameters
    },
}

optimized_results = {
    # Same structure as baseline_results
    # with optimized values
}

# Initialize reporter
reporter = BaselineOptimizationReporter()

# Generate HTML report
html = reporter.generate_report(
    profile=profile,
    baseline_results=baseline_results,
    optimization_results=optimized_results,
)

# Save to file
reporter.save_report(html, "reports/comparison.html")
```

## Input Data Format

### Baseline/Optimized Results Dictionary

```python
{
    # Period information
    "start_date": "2024-01-01",  # ISO format date string
    "end_date": "2025-12-31",

    # Equity curve (required)
    "equity_curve": [
        (datetime(2024, 1, 1), 100000.0),
        (datetime(2024, 2, 1), 102000.0),
        # ... more points
    ],

    # Performance metrics (required)
    "performance": {
        # Risk-adjusted returns
        "sharpe_ratio": 1.2,
        "sortino_ratio": 1.8,
        "calmar_ratio": 0.9,
        "omega_ratio": 1.3,

        # Return metrics
        "total_return": 25.0,  # Percentage

        # Risk metrics
        "max_drawdown_percentage": -15.0,
        "volatility_annualized": 12.5,
        "ulcer_index": 5.2,
        "var_95": -2.1,
        "cvar_95": -3.5,

        # Trade statistics
        "win_rate": 52.0,  # Percentage
        "profit_factor": 1.4,
        "avg_win": 1.8,
        "avg_loss": -1.3,
        "largest_win": 8.5,
        "largest_loss": -6.2,
        "total_trades": 156,
        "winning_trades": 81,
        "losing_trades": 75,
    },

    # Strategy parameters (optional, for comparison)
    "parameters": {
        "lookback_period": 20,
        "entry_threshold": 2.0,
        "exit_threshold": 1.0,
        # ... more parameters
    },
}
```

### Walk-Forward Validation Results (Optional)

```python
walk_forward_results = {
    "windows": [
        {
            "is_sharpe": 1.5,
            "oos_sharpe": 1.3,
            "period": "2024-Q1"
        },
        # ... more windows
    ],
    "is_sharpe": 1.6,  # Average in-sample Sharpe
    "oos_sharpe": 1.35,  # Average out-of-sample Sharpe
    "is_oos_ratio": 0.84,  # OOS/IS ratio (stability indicator)
}
```

### Parameter Sensitivity Results (Optional)

```python
sensitivity_results = {
    "parameters": ["lookback_period", "entry_threshold", "exit_threshold"],
    "sharpe_matrix": [
        [1.2, 1.3, 1.4, 1.35, 1.3],
        [1.4, 1.5, 1.65, 1.55, 1.45],
        # ... more rows
    ],
    "optimal_region": {
        "lookback_period": [20, 30],
        "entry_threshold": [2.0, 2.5]
    },
}
```

## Recommendation Logic

The reporter automatically generates recommendations based on:

```python
# USE_OPTIMIZED
if optimized_sharpe > 1.2 * baseline_sharpe and oos_sharpe > 0.8 * is_sharpe:
    # Strong improvement with stable OOS performance
    recommendation = "USE_OPTIMIZED"
    confidence = 0.85

# CONSIDER_OPTIMIZED
elif optimized_sharpe > 1.05 * baseline_sharpe:
    # Moderate improvement - proceed with caution
    recommendation = "CONSIDER_OPTIMIZED"
    confidence = 0.65

# USE_BASELINE
else:
    # Marginal or no improvement
    recommendation = "USE_BASELINE"
    confidence = 0.75
```

## Report Sections

### 1. Executive Summary
- 4 key metric cards (Sharpe, Return, Drawdown, Win Rate)
- Color-coded by improvement
- Comparison table with all key metrics
- Statistical significance indicators

### 2. Parameter Analysis
- Side-by-side parameter comparison
- Changed parameters highlighted
- Estimated impact descriptions

### 3. Equity Curves
- Individual baseline and optimized charts
- Normalized dual overlay chart
- Interactive Plotly charts

### 4. Drawdown Analysis
- Underwater drawdown comparison
- Side-by-side visualization
- Drawdown metrics table

### 5. Risk Metrics
- Comprehensive risk metrics table
- Risk-adjusted returns radar chart
- Status indicators (Good/Fair/Poor)

### 6. Out-of-Sample Validation (if available)
- Walk-forward window performance
- IS/OOS ratio analysis
- Stability assessment

### 7. Implementation Guide
- Step-by-step deployment instructions
- Recommended configuration (YAML format)
- Monitoring checklist

## Customization

### Using a Custom Template

```python
# Create your Jinja2 template
custom_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ strategy_name }} Comparison</title>
    <!-- Your custom CSS -->
</head>
<body>
    <h1>{{ strategy_name }}</h1>
    <!-- Your custom layout -->
    <p>Sharpe Improvement: {{ sharpe_improvement }}%</p>
</body>
</html>
"""

# Save template
template_path = "reports/templates/custom_report.html"
with open(template_path, "w") as f:
    f.write(custom_template)

# Use custom template
reporter = BaselineOptimizationReporter(template_path=template_path)
html = reporter.generate_report(...)
```

### Styling

The default template uses CSS variables for easy customization:

```css
:root {
    --primary-color: #2c3e50;
    --secondary-color: #34495e;
    --accent-color: #3498db;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --danger-color: #e74c3c;
}
```

## Examples

See `examples/baseline_optimization_reporter_example.py` for comprehensive examples:

1. **Basic Usage**: Minimal inputs, quick comparison
2. **With Walk-Forward**: Include OOS validation
3. **With Sensitivity**: Add parameter analysis
4. **Comprehensive**: All features combined
5. **Custom Template**: Using your own template

Run examples:

```bash
python examples/baseline_optimization_reporter_example.py
```

## Testing

Run the test suite:

```bash
# Unit tests
pytest tests/unit/backtesting/test_baseline_optimization_reporter.py -v

# With coverage
pytest tests/unit/backtesting/test_baseline_optimization_reporter.py -v --cov=app.backtesting.reports.baseline_optimization_reporter
```

## Output

The reporter generates:

1. **HTML File**: Interactive report with embedded charts
   - Open in any modern web browser
   - Fully responsive design
   - Export to PDF via browser print

2. **JSON Chart Data**: Embedded in HTML for interactivity
   - Plotly charts
   - Zoom, pan, hover tooltips
   - Download as PNG

## Performance

- Report generation: ~1-2 seconds for typical backtests
- File size: ~500KB-2MB (depending on data size)
- Compatible with datasets up to 10,000 data points

## Best Practices

1. **Data Quality**: Ensure equity curves have consistent timestamps
2. **Metric Completeness**: Provide all performance metrics for best results
3. **Parameter Documentation**: Include meaningful parameter names
4. **Walk-Forward**: Always include OOS validation for robust decisions
5. **Review**: Always review recommendations in context of market conditions

## Limitations

- PDF generation requires browser print (native PDF export planned)
- Statistical significance tests require sufficient trade history
- Sensitivity heatmap is currently placeholder (implementation pending)
- Maximum recommended data points: 10,000 (for chart performance)

## Future Enhancements

- [ ] Native PDF export (weasyprint integration)
- [ ] Advanced statistical tests (bootstrap, permutation)
- [ ] Multi-strategy comparison (3+ strategies)
- [ ] Real-time report updates (WebSocket)
- [ ] Cloud report hosting
- [ ] Custom branding templates
- [ ] Automated email reports
- [ ] API integration

## Troubleshooting

### Template Not Found

```
FileNotFoundError: Template not found
```

**Solution**: Ensure template path is correct or use default (no argument)

### Missing Metrics

```
KeyError: 'sharpe_ratio'
```

**Solution**: Provide all required metrics in `performance` dictionary

### Chart Not Rendering

**Solution**: Check browser console for JavaScript errors. Ensure Plotly CDN is accessible.

### Large File Size

**Solution**: Reduce equity curve resolution or limit date range

## Support

For issues, questions, or contributions:
- GitHub Issues: [project repository]
- Documentation: [project docs]
- Email: [support email]

## License

[Your License Here]

## Changelog

### Version 1.0.0 (2025-01-26)
- Initial release
- HTML report generation
- Interactive Plotly charts
- Recommendation engine
- Walk-forward validation support
- Parameter analysis
