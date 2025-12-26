"""
T9.1: ReportingGenerator - Comprehensive performance report generation
"""

from .reporting_generator import (
    ReportingGenerator,
    get_reporting_generator,
)
from .models import (
    PerformanceReport,
    ReportGenerationRequest,
    StrategyMetrics,
    AllocationSnapshot,
    PerformanceMetric,
)
from .quantstats_integrator import (
    QuantStatsIntegrator,
    AdvancedMetrics,
    StatisticsReport,
    get_quantstats_integrator,
)
from .pyfolio_integrator import (
    PyFolioIntegrator,
    FactorExposure,
    FactorAnalysis,
    PositionConcentration,
    CapacityFade,
    Tearsheet,
    get_pyfolio_integrator,
)
from .html_template_engine import (
    HTMLTemplateEngine,
    BrandingConfig,
    ReportSection,
    ReportConfig,
    HTMLReport,
    get_html_template_engine,
)
from .visualization_generator import (
    AdvancedVisualizationGenerator,
    PlotlyChart,
    ChartMetadata,
    get_visualization_generator,
)
from .delivery_manager import (
    ReportDeliveryManager,
    ExportFormat,
    DeliveryChannel,
    ExportConfig,
    EmailConfig,
    S3Config,
    ExportResult,
    DeliveryResult,
    get_delivery_manager,
)

__all__ = [
    "ReportingGenerator",
    "get_reporting_generator",
    "PerformanceReport",
    "ReportGenerationRequest",
    "StrategyMetrics",
    "AllocationSnapshot",
    "PerformanceMetric",
    "QuantStatsIntegrator",
    "AdvancedMetrics",
    "StatisticsReport",
    "get_quantstats_integrator",
    "PyFolioIntegrator",
    "FactorExposure",
    "FactorAnalysis",
    "PositionConcentration",
    "CapacityFade",
    "Tearsheet",
    "get_pyfolio_integrator",
    "HTMLTemplateEngine",
    "BrandingConfig",
    "ReportSection",
    "ReportConfig",
    "HTMLReport",
    "get_html_template_engine",
    "AdvancedVisualizationGenerator",
    "PlotlyChart",
    "ChartMetadata",
    "get_visualization_generator",
    "ReportDeliveryManager",
    "ExportFormat",
    "DeliveryChannel",
    "ExportConfig",
    "EmailConfig",
    "S3Config",
    "ExportResult",
    "DeliveryResult",
    "get_delivery_manager",
]
