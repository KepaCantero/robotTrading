"""
T9.1: ReportingGenerator - Comprehensive performance report generation
"""

from .delivery_manager import (
    DeliveryChannel,
    DeliveryResult,
    EmailConfig,
    ExportConfig,
    ExportFormat,
    ExportResult,
    ReportDeliveryManager,
    S3Config,
    get_delivery_manager,
)
from .html_template_engine import (
    BrandingConfig,
    HTMLReport,
    HTMLTemplateEngine,
    ReportConfig,
    ReportSection,
    get_html_template_engine,
)
from .models import (
    AllocationSnapshot,
    PerformanceMetric,
    PerformanceReport,
    ReportGenerationRequest,
    StrategyMetrics,
)
from .pyfolio_integrator import (
    CapacityFade,
    FactorAnalysis,
    FactorExposure,
    PositionConcentration,
    PyFolioIntegrator,
    Tearsheet,
    get_pyfolio_integrator,
)
from .quantstats_integrator import (
    AdvancedMetrics,
    QuantStatsIntegrator,
    StatisticsReport,
    get_quantstats_integrator,
)
from .reporting_generator import ReportingGenerator, get_reporting_generator
from .visualization_generator import (
    AdvancedVisualizationGenerator,
    ChartMetadata,
    PlotlyChart,
    get_visualization_generator,
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
