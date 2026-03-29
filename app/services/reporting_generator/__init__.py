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
    "AdvancedMetrics",
    "AdvancedVisualizationGenerator",
    "AllocationSnapshot",
    "BrandingConfig",
    "CapacityFade",
    "ChartMetadata",
    "DeliveryChannel",
    "DeliveryResult",
    "EmailConfig",
    "ExportConfig",
    "ExportFormat",
    "ExportResult",
    "FactorAnalysis",
    "FactorExposure",
    "HTMLReport",
    "HTMLTemplateEngine",
    "PerformanceMetric",
    "PerformanceReport",
    "PlotlyChart",
    "PositionConcentration",
    "PyFolioIntegrator",
    "QuantStatsIntegrator",
    "ReportConfig",
    "ReportDeliveryManager",
    "ReportGenerationRequest",
    "ReportSection",
    "ReportingGenerator",
    "S3Config",
    "StatisticsReport",
    "StrategyMetrics",
    "Tearsheet",
    "get_delivery_manager",
    "get_html_template_engine",
    "get_pyfolio_integrator",
    "get_quantstats_integrator",
    "get_reporting_generator",
    "get_visualization_generator",
]
