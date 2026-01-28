# 📘 26. Designing Data-Intensive Applications - Trading Systems

**Libro:** Designing Data-Intensive Applications - Martin Kleppmann
**Objetivo:** Construir sistemas de trading robustos, escalables y confiables

## 🎯 Resumen Ejecutivo

Claude Code DEBE aplicar estos patrones para:
1. **Auditoría completa** con event sourcing
2. **Alta disponibilidad** con replicación
3. **Consistencia** en operaciones críticas
4. **Escalabilidad** con particionamiento

---

## 📋 Las 15 Reglas Críticas para Claude Code

### Regla 26.1 — Event Sourcing para Auditoría

```python
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass(frozen=True)
class Event:
    event_id: str
    aggregate_id: str
    event_type: str
    data: dict
    timestamp: datetime

class EventStore:
    def append(self, aggregate_id: str, events: list[Event]):
        for event in events:
            self.db.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?)",
                (aggregate_id, event.event_type, json.dumps(event.data), event.timestamp)
            )
    
    def get_events(self, aggregate_id: str) -> list[Event]:
        rows = self.db.execute("SELECT * FROM events WHERE aggregate_id = ?", (aggregate_id,))
        return [Event(*row) for row in rows]
```

**Regla:** USAR event sourcing para auditoría completa.

---

### Regla 26.2 — Write-Ahead Logging (WAL)

```python
class WriteAheadLog:
    def write(self, operation: str, data: dict):
        entry = {'op': operation, 'data': data, 'ts': time.time()}
        self.log_file.write(json.dumps(entry) + '\n')
        self.log_file.flush()
    
    def recover(self):
        with open(self.log_path) as f:
            return [json.loads(line) for line in f]
```

**Regla:** USAR WAL para recuperación después de fallos.

---

### Regla 26.3 — LSM-Trees para Escrituras Rápidas

```python
import plyvel

class LevelDBStore:
    def __init__(self, db_path: str):
        self.db = plyvel.DB(db_path, create_if_missing=True)
    
    def put(self, key: str, value: bytes):
        self.db.put(key.encode(), value)
```

**Regla:** USAR LSM-trees (LevelDB, RocksDB) para escrituras optimizadas.

---

### Regla 26.4 — Replicación para HA

```python
class ReplicatedOrderStore:
    async def write(self, order: Order):
        await self._write_to_primary(order)
        tasks = [self._write_to_replica(r, order) for r in self.replicas]
        await asyncio.gather(*tasks, return_exceptions=True)
```

**Regla:** IMPLEMENTAR replicación para alta disponibilidad.

---

### Regla 26.5 — Consistency Levels (Quorums)

```python
class DistributedStore:
    def __init__(self, replication_factor: int = 3):
        self.quorum = (replication_factor // 2) + 1
    
    async def write(self, key: str, value: bytes):
        responses = await self._write_to_all_nodes(key, value)
        if sum(responses) < self.quorum:
            raise Exception("Write quorum failed")
```

**Regla:** CONFIGURAR quorums apropiados para lectura/escritura.

---

### Regla 26.6 — CAP Theorem en Trading

**En trading, priorizar CONSISTENCY sobre availability.**

```python
class TradingSystem:
    def handle_partition(self):
        if self.preference == 'consistency':
            self.stop_accepting_orders()  # Mejor: perder dinero que inconsistencias
```

**Regla:** EN TRADING, consistencia > disponibilidad.

---

### Regla 26.7 — Two-Phase Commit (2PC)

```python
class TwoPhaseCommit:
    async def execute(self, transaction):
        # Phase 1: Prepare
        for participant in self.participants:
            await participant.prepare(transaction)
        
        # Phase 2: Commit
        for participant in self.participants:
            await participant.commit(transaction)
```

**Regla:** USAR 2PC para transacciones distribuidas críticas.

---

### Regla 26.8 — Idempotent Operations

```python
@dataclass(frozen=True)
class Order:
    order_id: str  # UUID único

class IdempotentOrderManager:
    def place_order(self, order: Order):
        if order.order_id in self.processed:
            return self.store.get_result(order.order_id)
        result = self._execute(order)
        self.processed.add(order.order_id)
        return result
```

**Regla:** DISEÑAR todas las operaciones como idempotentes (UUIDs).

---

### Regla 26.9 — Snapshot Isolation

```python
class SnapshotIsolationDB:
    def begin_transaction(self):
        tx_id = uuid4()
        self._create_snapshot(tx_id)
        return tx_id
    
    def commit(self, tx_id: str):
        if not self._check_conflicts(tx_id):
            self._apply_changes(tx_id)
```

**Regla:** USAR snapshot isolation para prevenir dirty reads.

---

### Regla 26.10 — Distributed Transactions (SAGA)

```python
class SagaOrchestrator:
    async def execute(self):
        completed = []
        for step in self.steps:
            try:
                await step['execute']()
                completed.append(step)
            except Exception:
                for s in reversed(completed):
                    await s['compensate']()
                raise
```

**Regla:** USAR pattern SAGA para transacciones de larga duración.

---

### Regla 26.11 — Partition Tolerance (Sharding)

```python
class ShardManager:
    def get_shard(self, key: str) -> int:
        return hash(key) % self.num_shards
    
    def route_order(self, order: Order):
        return f"shard_{self.get_shard(order.symbol)}"
```

**Regla:** IMPLEMENTAR sharding por símbolo para escalabilidad.

---

### Regla 26.12 — CRDTs para Réplicas

```python
class GCounter:
    def increment(self, amount: int = 1):
        self.counts[self.node_id] += amount
    
    def merge(self, other: 'GCounter'):
        for node, count in other.counts.items():
            self.counts[node] = max(self.counts.get(node, 0), count)
```

**Regla:** USAR CRDTs para réplicas eventualmente consistentes.

---

### Regla 26.13 — Backpressure Handling

```python
class BackpressureQueue:
    async def put(self, item):
        if self.queue.full():
            self.queue.get_nowait()  # Descartar más viejo
        await self.queue.put(item)
```

**Regla:** IMPLEMENTAR backpressure para evitar sobrecarga.

---

### Regla 26.14 — Index Strategies

```python
class IndexedStore:
    def put(self, key: str, value: dict):
        self.data[key] = value
        for field, index in self.indexes.items():
            if field in value:
                index[value[field]].add(key)
```

**Regla:** CREAR índices por campos consultados frecuentemente.

---

### Regla 26.15 — Data Versioning

```python
@dataclass
class VersionedData:
    key: str
    value: dict
    version: int
    timestamp: datetime

class VersionedStore:
    def put(self, key: str, value: dict):
        current = self.versions.get(key, VersionedData(key, {}, 0, datetime.min))
        self.versions[key] = VersionedData(key, value, current.version + 1, datetime.now())
```

**Regla:** MANTENER versiones de datos críticos para auditoría.

---

**Última actualización:** 2026-01-28
**Version:** 1.0
