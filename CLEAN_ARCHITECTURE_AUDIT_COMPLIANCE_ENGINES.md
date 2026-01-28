# Clean Architecture Audit Report: Compliance Engines

**Date:** 2026-01-28  
**Auditor:** Code Archaeologist (Claude Code)  
**Scope:** `app/core/compliance_engine.py` and `app/core/compliance_integration.py`  
**Reference:** Rule 18 - Martin (Clean Architecture)

---

## Executive Summary

**CRITICAL FINDING:** Both compliance engine files are located in `app/core/` but violate Clean Architecture's **Dependency Rule**. They contain concrete infrastructure dependencies and orchestration logic that should reside in the **application** or **infrastructure** layers.

**Overall Compliance:** 25/100

| Principle | Score | Status |
|-----------|-------|--------|
| Dependency Rule | 0/40 | ❌ FAILED |
| Layer Separation | 5/30 | ❌ FAILED |
| Interface Segregation | 10/20 | ⚠️ POOR |
| Framework Independence | 10/10 | ✅ PASSED |

---

## 1. Layer Analysis: Where Should These Files Be?

### Current Location: `app/core/` ⚠️

The `app/core/` directory is intended for **shared utilities and cross-cutting concerns** that have minimal dependencies. However:

**Problem:** `compliance_engine.py` (1,720 lines) and `compliance_integration.py` (1,017 lines) are **NOT** core utilities - they are **orchestration engines** with extensive infrastructure dependencies.

### Correct Locations According to Clean Architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (Outer)                        │
│  app/api/                                                   │
│  └── Can use anything                                       │
├─────────────────────────────────────────────────────────────┤
│                Infrastructure Layer                         │
│  app/infrastructure/orchestration/                          │
│  ├── compliance_orchestrator.py  ← MOVED HERE              │
│  └── compliance_integration.py  ← MOVED HERE               │
│                                                             │
│  Purpose: Coordinate external services, databases, APIs     │
├─────────────────────────────────────────────────────────────┤
│                Application Layer                            │
│  app/application/use_cases/                                │
│  ├── trade_compliance_use_case.py  ← NEW                   │
│  └── pre_trade_analysis_use_case.py ← NEW                  │
│                                                             │
│  Purpose: Orchestrate business rules, define use cases      │
├─────────────────────────────────────────────────────────────┤
│                   Domain Layer (Core)                       │
│  app/domain/                                                │
│  ├── entities/compliance_rule.py                           │
│  ├── entities/pre_trade_analysis.py                        │
│  └── repositories/compliance_repository.py                 │
│                                                             │
│  Purpose: Pure business rules, NO external dependencies    │
└─────────────────────────────────────────────────────────────┘
```

### Recommendation:

| File | Current | Should Be | Reason |
|------|---------|-----------|--------|
| `compliance_engine.py` | `app/core/` | `app/infrastructure/orchestration/` | Coordinates 17+ external systems |
| `compliance_integration.py` | `app/core/` | `app/infrastructure/orchestration/` | Infrastructure glue code |
| `PreTradeAnalysis` | dataclass in core | `app/domain/entities/` | Business entity |
| `ComplianceEngine` | class in core | `app/application/services/` | Application service |

---

## 2. Dependency Violations Found

### 2.1 Infrastructure Dependencies in "Core" ❌

**Violation Type:** Direct imports of infrastructure components from what should be infrastructure-agnostic code.

#### `compliance_engine.py` - Lines 103-255 (SystemAvailability class)

```python
# ❌ VIOLATION: Importing concrete infrastructure implementations
from app.backtesting.engine import SimpleBacktester
from app.services.live_trading.broker_connector import BrokerConnector
from app.engines.risk_engine import RiskEngine
from app.engines.portfolio_engine import PortfolioEngine
from app.engines.data_engine import DataEngine
from app.engines.context_engine import ContextEngine
from app.engines.execution_engine.microstructure import MarketMicrostructureEngine
from app.services.regime_detection_chan import get_regime_detector
from app.services.portfolio_construction_narang import get_portfolio_constructor
# ... 20+ more infrastructure imports
```

**Why This Violates Clean Architecture:**
- **Dependency Rule Violation:** Inner layer (`core`) depends on outer layers (`services`, `engines`, `backtesting`)
- **Concrete Dependencies:** Direct imports prevent swapping implementations
- **Framework Coupling:** Tied to specific implementations of services

#### `compliance_integration.py` - Lines 52-211

```python
# ❌ VIOLATION: Direct imports of all compliance systems
from app.services.factor_models import FamaFrenchFactorModel, APTModel
from app.services.optimization_chan import MeanVarianceOptimizer
from app.services.regime_detection_chan import MarketRegimeDetector
from app.strategies.alpha_models import AlphaModel, MomentumAlphaModel
from app.engines.execution_engine.microstructure.harris_integration import HarrisMicrostructureIntegrator
# ... 30+ more infrastructure imports
```

### 2.2 Business Logic in Infrastructure Layer ❌

**Violation Type:** Business rules implemented in infrastructure code.

```python
# compliance_engine.py lines 764-769
# ❌ BUSINESS LOGIC in infrastructure coordination code
if abs(result.portfolio_var) > 0.30:  # 30% annual volatility threshold
    result.confidence -= 0.15
    result.reasons.append(f"High portfolio volatility: {result.portfolio_var:.2%}")
```

**Why This Violates Clean Architecture:**
- Business rules (30% volatility threshold) belong in **domain layer**
- Infrastructure should only coordinate, not make business decisions
- Cannot test business rules without infrastructure dependencies

### 2.3 Missing Interface Abstractions ❌

**Violation Type:** No interfaces defined for 17 integrated systems.

**Current (Anti-Pattern):**
```python
# compliance_engine.py lines 1243-1249
elif name == "ernest_chan":
    from app.services.regime_detection_chan import get_regime_detector
    from app.services.execution_algorithms import get_execution_algorithm
    return {
        "regime": get_regime_detector(),
        "vwap": get_execution_algorithm("vwap"),
        # ...
    }
```

**Correct (Clean Architecture):**
```python
# app/domain/services/compliance_service_interface.py
class ComplianceServiceInterface(ABC):
    @abstractmethod
    def analyze_pre_trade(self, context: TradingContext) -> ComplianceResult:
        pass

# app/infrastructure/services/ernest_chan_service.py
class ErnestChanService(ComplianceServiceInterface):
    def analyze_pre_trade(self, context: TradingContext) -> ComplianceResult:
        # Implementation
```

---

## 3. Architecture Diagram: Current vs Correct

### Current Architecture (VIOLATIONS)

```
┌───────────────────────────────────────────────────────────────┐
│                      app/core/                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │         compliance_engine.py (1,720 lines)              │  │
│  │  ❌ Depends on:                                         │  │
│  │    - app.backtesting.engine                            │  │
│  │    - app.engines.* (5 engines)                         │  │
│  │    - app.services.* (10+ services)                     │  │
│  │    - app.strategies.*                                   │  │
│  │    - app.sre.*                                          │  │
│  │    - app.microstructure.*                               │  │
│  │                                                         │  │
│  │  ❌ Contains:                                           │  │
│  │    - Business rules (volatility thresholds)             │  │
│  │    - Orchestration logic                                │  │
│  │    - Data classes (PreTradeAnalysis)                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │      compliance_integration.py (1,017 lines)           │  │
│  │  ❌ Depends on:                                         │  │
│  │    - All 12 compliance systems directly                │  │
│  │    - 30+ concrete implementations                      │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                            ↓ ❌
                  VIOLATES DEPENDENCY RULE
                  (arrows point OUTWARD)
```

### Correct Architecture (Clean Architecture)

```
┌────────────────────────────────────────────────────────────────┐
│                    API Layer                                  │
│  app/api/trading.py                                           │
│  └── Uses: PreTradeUseCase                                    │
├────────────────────────────────────────────────────────────────┤
│                Application Layer                              │
│  app/application/use_cases/                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  pre_trade_analysis_use_case.py                        │  │
│  │  ────────────────────────────────────────────────────  │  │
│  │  class PreTradeAnalysisUseCase:                        │  │
│  │      def __init__(                                      │  │
│  │          self.compliance_service: ComplianceService     │  │
│  │      )                                                  │  │
│  │                                                         │  │
│  │      def execute(self, request: TradeRequest)           │  │
│  │          -> PreTradeAnalysisResult:                    │  │
│  │          result = self.compliance_service.analyze(...)  │  │
│  │          return result                                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                 │
│  app/application/services/                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  compliance_orchestrator.py                            │  │
│  │  ────────────────────────────────────────────────────  │  │
│  │  class ComplianceOrchestrator:                         │  │
│  │      """Coordinates all compliance systems"""          │  │
│  │      def __init__(services: List[ComplianceService]):  │  │
│  │          self.services = services                      │  │
│  │                                                         │  │
│  │      def analyze_comprehensive(self, context):         │  │
│  │          results = []                                   │  │
│  │          for service in self.services:                  │  │
│  │              results.append(service.analyze(context))   │  │
│  │          return self.aggregate(results)                 │  │
│  └────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────┤
│                Domain Layer (CORE)                            │
│  app/domain/entities/                                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  pre_trade_analysis.py                                 │  │
│  │  ────────────────────────────────────────────────────  │  │
│  │  @dataclass                                            │  │
│  │  class PreTradeAnalysis:                               │  │
│  │      can_execute: bool                                 │  │
│  │      confidence: float                                 │  │
│  │      volatility_risk: float  # Business rule here      │  │
│  │                                                         │  │
│  │      def is_acceptable_risk(self) -> bool:             │  │
│  │          return self.volatility_risk < 0.30            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                 │
│  app/domain/services/                                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  compliance_service_interface.py                       │  │
│  │  ────────────────────────────────────────────────────  │  │
│  │  class ComplianceServiceInterface(ABC):                │  │
│  │      @abstractmethod                                   │  │
│  │      def analyze(self, context: TradingContext)        │  │
│  │          -> ComplianceResult:                          │  │
│  │          pass                                           │  │
│  └────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────┤
│              Infrastructure Layer                              │
│  app/infrastructure/compliance/                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  ernest_chan_service.py                                │  │
│  │  narang_service.py                                     │  │
│  │  lopez_de_prado_service.py                             │  │
│  │  harris_service.py                                     │  │
│  │  ... (12 compliance implementations)                   │  │
│  │                                                         │  │
│  │  Each implements ComplianceServiceInterface            │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                  ✅ DEPENDENCIES POINT INWARD
```

---

## 4. Refactoring Plan to Achieve Compliance

### Phase 1: Extract Domain Entities (Priority: CRITICAL)

**Goal:** Move business entities to domain layer.

**Actions:**

1. **Create domain entities:**
   ```bash
   mkdir -p app/domain/entities/compliance
   ```

2. **Move data classes:**
   ```python
   # app/domain/entities/compliance/pre_trade_analysis.py
   from dataclasses import dataclass
   from decimal import Decimal
   from typing import List, Optional
   from datetime import datetime
   
   @dataclass
   class PreTradeAnalysis:
       can_execute: bool
       confidence: float
       reasons: List[str]
       
       # Business rules
       def is_acceptable_volatility(self) -> bool:
           return self.portfolio_var < 0.30
       
       def is_acceptable_liquidity(self) -> bool:
           return self.liquidity_score > 30.0
   ```

3. **Create value objects:**
   ```python
   # app/domain/value_objects/trading_context.py
   @dataclass
   class TradingContext:
       symbol: str
       side: str
       quantity: Decimal
       price: Decimal
       urgency: float
       timestamp: datetime
   ```

**Estimated Effort:** 2 hours

### Phase 2: Create Service Interfaces (Priority: CRITICAL)

**Goal:** Define interfaces for all compliance systems.

**Actions:**

1. **Create base interface:**
   ```python
   # app/domain/services/compliance_service_interface.py
   from abc import ABC, abstractmethod
   from typing import Optional
   import pandas as pd
   
   class ComplianceServiceInterface(ABC):
       """Interface for compliance checking services."""
       
       @abstractmethod
       def get_name(self) -> str:
           """Return service name."""
           pass
       
       @abstractmethod
       def is_available(self) -> bool:
           """Check if service is available."""
           pass
       
       @abstractmethod
       def analyze_pre_trade(
           self,
           context: TradingContext,
           price_history: Optional[pd.DataFrame] = None,
       ) -> PreTradeAnalysis:
           """Analyze trade for compliance."""
           pass
   ```

2. **Create specific interfaces:**
   ```python
   # app/domain/services/regime_detection_interface.py
   class RegimeDetectionInterface(ComplianceServiceInterface):
       @abstractmethod
       def detect_regime(self, price_history: pd.DataFrame) -> str:
           pass
   
   # app/domain/services/microstructure_interface.py
   class MicrostructureInterface(ComplianceServiceInterface):
       @abstractmethod
       def check_liquidity(self, quantity: Decimal) -> bool:
           pass
   ```

**Estimated Effort:** 4 hours

### Phase 3: Move Implementations to Infrastructure (Priority: HIGH)

**Goal:** Implement interfaces in infrastructure layer.

**Actions:**

1. **Create infrastructure directory:**
   ```bash
   mkdir -p app/infrastructure/compliance
   ```

2. **Implement services:**
   ```python
   # app/infrastructure/compliance/ernest_chan_service.py
   from ...domain.services import ComplianceServiceInterface, RegimeDetectionInterface
   from app.services.regime_detection_chan import get_regime_detector
   
   class ErnestChanService(RegimeDetectionInterface):
       """Ernest Chan compliance implementation."""
       
       def __init__(self):
           self._detector = get_regime_detector()
       
       def get_name(self) -> str:
           return "ernest_chan"
       
       def is_available(self) -> bool:
           return self._detector is not None
       
       def detect_regime(self, price_history: pd.DataFrame) -> str:
           regimes = self._detector.detect_regimes(price_history)
           return regimes[-1] if regimes else "UNKNOWN"
       
       def analyze_pre_trade(self, context, price_history=None) -> PreTradeAnalysis:
           if price_history is None:
               return PreTradeAnalysis(can_execute=True, confidence=1.0, reasons=[])
           
           regime = self.detect_regime(price_history)
           confidence_adjustment = -0.1 if regime == "BEAR" else 0.05
           
           return PreTradeAnalysis(
               can_execute=True,
               confidence=max(0.0, 1.0 + confidence_adjustment),
               reasons=[f"Regime: {regime}"]
           )
   ```

3. **Create all 12 service implementations:**
   - `ernest_chan_service.py`
   - `narang_service.py`
   - `lopez_de_prado_service.py`
   - `tomasini_service.py`
   - `hastie_service.py`
   - `harris_service.py`
   - `ohara_service.py`
   - `percival_service.py`
   - `hull_service.py`
   - `google_sre_service.py`
   - `beck_tdd_service.py`
   - `martin_arch_service.py`

**Estimated Effort:** 8 hours

### Phase 4: Create Application Use Cases (Priority: HIGH)

**Goal:** Orchestrate compliance in application layer.

**Actions:**

1. **Create use case:**
   ```python
   # app/application/use_cases/pre_trade_analysis_use_case.py
   from typing import List
   from ...domain.entities.compliance import PreTradeAnalysis, TradingContext
   from ...domain.services import ComplianceServiceInterface
   
   class PreTradeAnalysisUseCase:
       """Use case for comprehensive pre-trade analysis."""
       
       def __init__(self, services: List[ComplianceServiceInterface]):
           self._services = services
       
       def execute(self, context: TradingContext) -> PreTradeAnalysis:
           """Execute comprehensive pre-trade analysis."""
           results = []
           
           for service in self._services:
               if service.is_available():
                   try:
                       result = service.analyze_pre_trade(context)
                       results.append(result)
                   except Exception as e:
                       # Log and continue
                       pass
           
           return self._aggregate_results(results, context)
       
       def _aggregate_results(self, results, context) -> PreTradeAnalysis:
           """Aggregate results from all services."""
           # Implementation
           pass
   ```

**Estimated Effort:** 4 hours

### Phase 5: Update API Layer (Priority: MEDIUM)

**Goal:** Use use cases from API layer.

**Actions:**

1. **Update API endpoints:**
   ```python
   # app/api/trading.py
   from fastapi import APIRouter, Depends
   from ...application.use_cases import PreTradeAnalysisUseCase
   
   router = APIRouter()
   
   @router.post("/analyze")
   async def analyze_pre_trade(
       request: TradeRequest,
       use_case: PreTradeAnalysisUseCase = Depends(get_pre_trade_use_case)
   ):
       context = TradingContext(
           symbol=request.symbol,
           side=request.side,
           quantity=request.quantity,
           price=request.price,
           urgency=request.urgency,
           timestamp=datetime.now()
       )
       
       result = use_case.execute(context)
       return result
   ```

**Estimated Effort:** 2 hours

### Phase 6: Delete Old Files (Priority: LOW)

**Goal:** Remove non-compliant files after migration.

**Actions:**

1. **Verify all tests pass**
2. **Delete old files:**
   - `app/core/compliance_engine.py`
   - `app/core/compliance_integration.py`
3. **Update all imports**

**Estimated Effort:** 1 hour

---

## 5. File Structure After Refactoring

```
app/
├── domain/
│   ├── entities/
│   │   └── compliance/
│   │       ├── pre_trade_analysis.py           # Moved from core
│   │       ├── post_trade_analysis.py          # Moved from core
│   │       └── portfolio_optimization.py       # Moved from core
│   ├── value_objects/
│   │   ├── trading_context.py                  # New
│   │   └── compliance_config.py                # New
│   └── services/
│       ├── compliance_service_interface.py     # New
│       ├── regime_detection_interface.py       # New
│       ├── microstructure_interface.py         # New
│       └── risk_management_interface.py        # New
│
├── application/
│   ├── use_cases/
│   │   ├── pre_trade_analysis_use_case.py      # New
│   │   └── post_trade_analysis_use_case.py     # New
│   └── services/
│       └── compliance_orchestrator.py          # Moved from core
│
├── infrastructure/
│   └── compliance/
│       ├── ernest_chan_service.py              # New implementation
│       ├── narang_service.py                   # New implementation
│       ├── lopez_de_prado_service.py           # New implementation
│       ├── tomasini_service.py                 # New implementation
│       ├── hastie_service.py                   # New implementation
│       ├── harris_service.py                   # New implementation
│       ├── ohara_service.py                    # New implementation
│       ├── percival_service.py                 # New implementation
│       ├── hull_service.py                     # New implementation
│       ├── google_sre_service.py               # New implementation
│       ├── beck_tdd_service.py                 # New implementation
│       └── martin_arch_service.py              # New implementation
│
└── api/
    └── trading.py                               # Updated
```

---

## 6. Testing Strategy

### Unit Tests (Domain Layer)

```python
# tests/unit/domain/entities/test_pre_trade_analysis.py
def test_volatility_business_rule():
    """Test business rule in domain entity."""
    analysis = PreTradeAnalysis(
        can_execute=True,
        confidence=0.8,
        portfolio_var=0.35,  # Above threshold
        reasons=[]
    )
    
    assert not analysis.is_acceptable_volatility()
```

### Integration Tests (Application Layer)

```python
# tests/integration/test_pre_trade_use_case.py
def test_use_case_with_mock_services():
    """Test use case with mocked services."""
    mock_service = Mock(spec=ComplianceServiceInterface)
    mock_service.is_available.return_value = True
    mock_service.analyze_pre_trade.return_value = PreTradeAnalysis(...)
    
    use_case = PreTradeAnalysisUseCase([mock_service])
    result = use_case.execute(context)
    
    assert result.can_execute is not None
```

### Acceptance Tests (API Layer)

```python
# tests/api/test_trading_api.py
def test_pre_trade_analysis_endpoint(client):
    """Test API endpoint with real use case."""
    response = client.post("/api/trading/analyze", json={
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 100,
        "price": 150.00
    })
    
    assert response.status_code == 200
    assert "can_execute" in response.json()
```

---

## 7. Priority Summary

| Priority | Phase | Action | Effort | Impact |
|----------|-------|--------|--------|--------|
| P0 | 1 | Extract domain entities | 2h | Enables testing |
| P0 | 2 | Create service interfaces | 4h | Enables mocking |
| P1 | 3 | Implement services in infrastructure | 8h | Fixes dependency violations |
| P1 | 4 | Create use cases | 4h | Enables orchestration |
| P2 | 5 | Update API layer | 2h | Completes refactoring |
| P3 | 6 | Delete old files | 1h | Cleanup |

**Total Effort:** 21 hours (3 days)

---

## 8. Benefits of Refactoring

### Immediate Benefits

1. **Testability:**
   - Unit tests for business rules without external dependencies
   - Mock services for integration tests
   - Faster test execution

2. **Maintainability:**
   - Clear separation of concerns
   - Easier to locate and fix bugs
   - Single responsibility per file

3. **Flexibility:**
   - Swap compliance implementations without changing business logic
   - Add new compliance systems without modifying existing code
   - Disable specific systems without breaking the system

### Long-term Benefits

1. **Scalability:**
   - Add new compliance rules by implementing interfaces
   - Parallel development of different compliance systems
   - Independent deployment of components

2. **Quality:**
   - Enforced dependency rules prevent regressions
   - Architecture tests ensure compliance
   - Clear ownership of each layer

3. **Performance:**
   - Lazy loading of compliance services
   - Parallel execution of independent checks
   - Caching at appropriate layers

---

## 9. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking changes during migration | HIGH | MEDIUM | Create feature flags, maintain backward compatibility |
| Test coverage gaps | MEDIUM | LOW | Write tests before refactoring (TDD) |
| Performance regression | LOW | LOW | Benchmark before/after, optimize hot paths |
| Increased complexity | MEDIUM | LOW | Document architecture, provide examples |

---

## 10. Compliance Score After Refactoring

| Principle | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Dependency Rule | 0/40 | 40/40 | +40 |
| Layer Separation | 5/30 | 30/30 | +25 |
| Interface Segregation | 10/20 | 20/20 | +10 |
| Framework Independence | 10/10 | 10/10 | 0 |
| **TOTAL** | **25/100** | **100/100** | **+75** |

---

## 11. Next Steps

1. **Review this report** with the development team
2. **Create architecture decision record (ADR)** for the refactoring
3. **Set up CI/CD checks** to prevent future violations
4. **Begin Phase 1** (extract domain entities) this week
5. **Write tests** for extracted entities
6. **Iterate through phases** following the refactoring plan

---

## Appendix: Quick Reference

### Dependency Rule

```
┌─────────────────────────────────────────┐
│           API Layer                     │  ← Can depend on anything
├─────────────────────────────────────────┤
│       Infrastructure                    │  ← Can depend on Application, Domain
├─────────────────────────────────────────┤
│       Application                       │  ← Can depend only on Domain
├─────────────────────────────────────────┤
│          Domain                         │  ← NO dependencies (CORE)
└─────────────────────────────────────────┘
```

**Key Principle:** Dependencies point **inward** toward the domain.

### Key Commands

```bash
# Check architecture compliance
python scripts/check_architecture.py

# Run domain tests
pytest tests/unit/domain/ -v

# Run integration tests
pytest tests/integration/ -v

# Verify no violations
python scripts/verify_architecture_patterns.py
```

---

**End of Report**

**Prepared by:** Code Archaeologist (Claude Code)  
**Date:** 2026-01-28  
**Status:** Ready for implementation
