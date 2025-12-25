# Advanced Monitoring & Real-Time Dashboard Implementation Roadmap

**Date**: 2025-12-25
**Status**: Planning Phase
**Scope**: T18.1-T18.6 - Enterprise-Grade Monitoring System
**Estimated Effort**: 2-3 weeks
**Expected Tests**: 400-500 new tests

---

## 📊 Current State Analysis

### ✅ Already Complete (95% Infrastructure)
- Risk Scaling Monitoring (real-time risk adjustment tracking)
- Portfolio Analytics Service (comprehensive metrics)
- WebSocket Streaming (real-time data delivery)
- Streamlit Dashboards (3 variants)
- Advanced Visualizations (plotly + matplotlib)
- REST API Endpoints (50+ endpoints)
- Performance Tracking (cycle-level metrics)
- Reporting Generator (HTML/PDF export)

### ❌ Missing Components
1. **Real-time Metrics Database** - No time-series persistence (QuestDB/InfluxDB)
2. **Advanced Alerting** - Infrastructure exists but needs rules engine + webhooks
3. **Live Trading Bridge** - Test structure only, core implementation unclear
4. **Event Streaming** - Basic pub/sub only, no Kafka/EventBridge
5. **Custom WebUI** - Only Streamlit (no React/Vue frontend)
6. **Distributed Tracing** - No APM/observability layer
7. **Metrics Aggregation** - No centralized metrics collection

---

## 🎯 Implementation Plan: T18.1-T18.6

### T18.1: Real-Time Metrics Database (High Priority)
**Purpose**: Persist all metrics to time-series database for historical analysis

#### Components to Create
1. **MetricsCollector** (100 LOC)
   - Collects metrics from all monitors (risk, performance, execution)
   - Batches and sends to database
   - Handles connection pooling and retries

2. **QuestDBConnector** (150 LOC)
   - Async QuestDB client
   - Bulk insert optimization
   - Query builder for common patterns
   - Connection management

3. **MetricsQueryEngine** (120 LOC)
   - Query builder for time-range queries
   - Aggregation support (OHLC, average, etc.)
   - Downsampling for large date ranges
   - Caching layer

4. **MetricsModels** (80 LOC)
   - MetricPoint dataclass (timestamp, symbol, metric_name, value, tags)
   - TimeSeriesQuery model
   - AggregatedMetrics model

#### Tests (80-100 tests)
- Unit: MetricsCollector, QuestDBConnector, QueryEngine
- Integration: End-to-end metrics collection and querying
- Performance: Bulk insert speed, query latency

#### Dependencies
- QuestDB client library
- Existing monitors (risk_scaling_monitor, portfolio_analytics_service)
- CAPA 2 components (already have portfolio data)

**Effort**: 1 week
**Estimated LOC**: 450
**Test Count**: 100

---

### T18.2: Advanced Alerting System (Medium Priority)
**Purpose**: Create rule-based alerting with webhook integration

#### Components to Create
1. **AlertRuleEngine** (120 LOC)
   - Define rules: `metric > threshold`, `metric < threshold`, `change > X%`
   - Rule composition: AND/OR logic
   - Time windows (e.g., "alert if >50% loss in 5 min window")
   - Severity levels (INFO, WARNING, CRITICAL)

2. **AlertManager** (100 LOC)
   - Rule evaluation on incoming metrics
   - De-duplication (don't spam same alert)
   - Alert state machine (triggered, resolved, acknowledged)
   - History tracking

3. **NotificationChannels** (150 LOC)
   - Webhook integration (HTTP POST)
   - Email alerts (SMTP)
   - Slack integration
   - Discord integration
   - Push notifications (optional)

4. **AlertModels** (70 LOC)
   - AlertRule, AlertEvent, AlertHistory
   - NotificationTarget (webhook, email, slack, etc.)

#### Tests (80-100 tests)
- Unit: Rule evaluation, state machine, notification routing
- Integration: End-to-end alert triggering and notification
- Performance: Alert evaluation at scale

#### Dependencies
- T18.1 (MetricsCollector provides metrics)
- Existing risk monitoring components
- Third-party APIs (Slack, Discord, etc.)

**Effort**: 5-7 days
**Estimated LOC**: 440
**Test Count**: 100

---

### T18.3: Live Trading Bridge Completion (Medium Priority)
**Purpose**: Verify and complete broker integration for live trading

#### Analysis Required First
- Review `/tests/unit/live_trading/test_live_trading_bridge.py`
- Check implementation status of:
  - BrokerConnector (IB, Alpaca, Paper)
  - OrderManager (lifecycle management)
  - RiskGateExecutor (hard stops)
  - AccountSynchronizer (position tracking)
  - PerformanceMonitor (live PnL)

#### Likely Components to Create/Complete
1. **BrokerConnector Implementations** (200 LOC)
   - Interactive Brokers API integration
   - Alpaca API integration
   - Paper trading connector

2. **OrderExecutor** (150 LOC)
   - Order placement and lifecycle
   - Fill tracking and confirmation
   - Error handling and retries
   - Order cancellation logic

3. **AccountSynchronizer** (100 LOC)
   - Real-time position tracking
   - Cash balance monitoring
   - Margin requirements validation
   - Account restrictions enforcement

4. **RiskGateExecutor** (80 LOC)
   - Hard stops (max loss per day)
   - Circuit breakers (max consecutive losses)
   - Buying power enforcement
   - Position limits

#### Tests (80-120 tests)
- Unit: Each broker connector, order executor, risk gates
- Integration: Full order lifecycle (order → fill → tracking)
- Mock broker tests: Simulate various scenarios

#### Dependencies
- CAPA 2 deployment decisions (T10.1)
- Portfolio data (existing)
- Live market data (existing via data engine)

**Effort**: 1-1.5 weeks
**Estimated LOC**: 530
**Test Count**: 120

---

### T18.4: Event Streaming Integration (Lower Priority)
**Purpose**: Unified event pipeline for scalable event-driven architecture

#### Components to Create
1. **EventBus** (100 LOC)
   - Define event types (OrderPlaced, RiskAlert, PortfolioRebalanced, etc.)
   - Event schema with metadata
   - Event versioning support

2. **KafkaConnector** (120 LOC)
   - Async Kafka producer/consumer
   - Topic management (auto-create with partition count)
   - Serialization (JSON/Protobuf)
   - Error handling and retry logic

3. **EventProcessor** (100 LOC)
   - Event handlers for each event type
   - Fanout to subscribers
   - Event ordering guarantees
   - Exactly-once processing

4. **EventStore** (80 LOC)
   - Event persistence (QuestDB or PostgreSQL)
   - Event replay capability
   - Event filtering and querying

#### Tests (60-80 tests)
- Unit: Event schemas, KafkaConnector, processors
- Integration: End-to-end event flow
- Reliability: Event delivery guarantees

#### Dependencies
- T18.1 (metrics database)
- Kafka infrastructure (external)

**Effort**: 1 week
**Estimated LOC**: 400
**Test Count**: 80

---

### T18.5: Custom WebUI Frontend (Lower Priority, High Effort)
**Purpose**: Modern React dashboard replacing Streamlit

#### Architecture
```
Frontend (React + Redux):
├── Components
│   ├── Dashboard Layout
│   ├── Risk Monitoring Panel
│   ├── Portfolio View
│   ├── Trade Execution Panel
│   ├── Performance Charts
│   ├── Alert Manager
│   └── Settings/Configuration
├── Stores (Redux)
│   ├── Portfolio state
│   ├── Risk state
│   ├── Alert state
│   └── Live prices state
└── API Integration (WebSocket + REST)
    ├── Real-time updates (WebSocket)
    ├── Historical data (REST)
    └── Configuration management

Backend API (already exists):
├── WebSocket endpoint (real-time)
├── REST endpoints (50+ existing)
└── GraphQL endpoint (optional)
```

#### Components to Create
1. **React Dashboard** (800-1000 LOC)
   - Navigation and layout
   - All dashboard panels
   - Real-time updates via WebSocket
   - Responsive design

2. **Redux Store** (300 LOC)
   - State management for all data
   - Actions and reducers
   - Async action handlers

3. **WebSocket Client** (150 LOC)
   - Subscription management
   - Automatic reconnection
   - Message handling

4. **Styling/UI Library** (400 LOC)
   - CSS/Tailwind styles
   - Reusable components
   - Theme management

#### Tests (100-150 tests)
- Component unit tests (Jest/React Testing Library)
- Redux store tests
- Integration tests (WebSocket + API)
- Visual regression tests (Storybook)

#### Dependencies
- React 18+, Redux, TypeScript
- Existing FastAPI backend
- WebSocket endpoint (exists)

**Effort**: 2-3 weeks
**Estimated LOC**: 1,650
**Test Count**: 150

---

### T18.6: Distributed Tracing & APM (Nice-to-Have)
**Purpose**: Observability and performance monitoring across the system

#### Components to Create
1. **TraceProvider** (100 LOC)
   - OpenTelemetry integration
   - Tracer initialization
   - Exporter configuration

2. **Instrumentation** (200 LOC)
   - FastAPI middleware for request tracing
   - Database query tracing (QuestDB, Redis)
   - Async task tracing
   - WebSocket tracing

3. **Metrics Export** (80 LOC)
   - Prometheus metrics endpoint
   - Custom metrics (order latency, backtest time, etc.)
   - Histogram and gauge metrics

4. **Dashboards in Grafana** (if using external APM)
   - Performance dashboard
   - Error rate dashboard
   - Latency percentiles (p50, p95, p99)

#### Tests (40-60 tests)
- Unit: Tracer initialization, instrumentation
- Integration: Trace collection and export
- Performance: Tracing overhead measurement

#### Dependencies
- OpenTelemetry libraries
- Jaeger or Datadog (external service)
- Prometheus (if self-hosted)

**Effort**: 4-5 days
**Estimated LOC**: 380
**Test Count**: 60

---

## 📈 Implementation Priorities

### Phase 1 (Week 1): Foundation
- **T18.1**: Real-time Metrics Database (CRITICAL for any monitoring)
- **Start verification**: T18.3 Live Trading Bridge

### Phase 2 (Week 2): Alerting & Live Trading
- **T18.2**: Advanced Alerting System (enables proactive monitoring)
- **Complete**: T18.3 Live Trading Bridge

### Phase 3 (Week 3): Scalability & Observability
- **T18.4**: Event Streaming (optional, enables scalability)
- **T18.6**: Distributed Tracing (optional, improves observability)
- **T18.5**: Custom WebUI (optional, nice UX improvement)

---

## 📊 Scope Summary

| Task | Priority | Effort | LOC | Tests | Duration | Status |
|------|----------|--------|-----|-------|----------|--------|
| T18.1 | 🔴 Critical | 1 week | 450 | 100 | Week 1 | Planning |
| T18.2 | 🟡 High | 5-7 days | 440 | 100 | Week 2 | Planning |
| T18.3 | 🟡 High | 1-1.5 weeks | 530 | 120 | Week 2-3 | Verify First |
| T18.4 | 🟢 Medium | 1 week | 400 | 80 | Week 3 | Optional |
| T18.5 | 🟢 Medium | 2-3 weeks | 1,650 | 150 | Week 3-4 | Optional |
| T18.6 | 🟢 Medium | 4-5 days | 380 | 60 | Week 3 | Optional |
| **TOTAL** | - | **2-3 weeks** | **3,850** | **~610** | - | - |

---

## ✅ Next Steps

### Immediate (This Session)
1. ✅ Analysis complete
2. Update .memory with roadmap
3. Decide: Implement T18.1-T18.3 or verify T18.3 first?

### User Decision Needed
**Which approach do you prefer?**

**Option A** (Recommended): Implement in priority order
```
Week 1: T18.1 (Metrics Database)
Week 2: T18.2 (Alerting) + Start T18.3 (Live Trading Verify)
Week 3: Complete T18.3 + Optional (T18.4, T18.6)
```

**Option B** (Risk-Mitigation): Verify T18.3 first
```
Today: Audit and complete T18.3 Live Trading Bridge
Then: T18.1 + T18.2 as planned
```

**Option C** (MVP Focus): T18.1 + T18.2 only
```
Week 1-2: T18.1 + T18.2 (metrics + alerting)
Skip: T18.4, T18.5, T18.6 (not critical for trading)
```

---

**Session Status**: Analysis complete, awaiting your direction on implementation approach.
