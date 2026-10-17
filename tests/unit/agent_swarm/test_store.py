"""Unit tests for the SwarmRunStore SQLite persistence."""

import pytest

from app.services.agent_swarm.events import AgentEvent
from app.services.agent_swarm.store import SwarmRunStore


@pytest.fixture
async def store(tmp_path):
    store = SwarmRunStore(str(tmp_path / "swarm_test.db"))
    await store.initialize()
    yield store
    await store.close()


class TestLifecycle:
    async def test_create_and_finish_run(self, store):
        await store.create_run("run_1", {"capital": "100000"}, "2026-10-17T10:00:00")
        await store.finish_run(
            "run_1",
            "completed",
            "2026-10-17T10:00:05",
            total_xp=600,
            achievements=[{"id": "first_launch"}],
            results={"decision": "APPROVED"},
        )

        runs = await store.list_runs()
        assert len(runs) == 1
        run = runs[0]
        assert run["workflow_id"] == "run_1"
        assert run["status"] == "completed"
        assert run["total_xp"] == 600
        assert run["achievements"] == [{"id": "first_launch"}]

    async def test_count_runs(self, store):
        assert await store.count_runs() == 0
        await store.create_run("run_1", {}, "t1")
        await store.create_run("run_2", {}, "t2")
        assert await store.count_runs() == 2

    async def test_list_runs_orders_by_started_at_desc(self, store):
        await store.create_run("old", {}, "2026-10-01T00:00:00")
        await store.create_run("new", {}, "2026-10-17T00:00:00")

        runs = await store.list_runs()
        assert [r["workflow_id"] for r in runs] == ["new", "old"]

    async def test_list_runs_limit(self, store):
        for i in range(5):
            await store.create_run(f"run_{i}", {}, f"2026-10-0{i + 1}T00:00:00")

        runs = await store.list_runs(limit=3)
        assert len(runs) == 3


class TestEvents:
    async def test_append_and_fetch_events_in_order(self, store):
        await store.create_run("run_1", {}, "t0")
        for i, etype in enumerate(["run_started", "stage_started", "stage_completed"]):
            await store.append_event(AgentEvent(etype, "run_1", agent_id=f"t{i}", payload={"i": i}))

        events = await store.get_run_events("run_1")
        assert [e["type"] for e in events] == ["run_started", "stage_started", "stage_completed"]
        assert events[1]["agent_id"] == "t1"
        assert events[2]["payload"] == {"i": 2}

    async def test_events_isolated_per_run(self, store):
        await store.create_run("a", {}, "t")
        await store.create_run("b", {}, "t")
        await store.append_event(AgentEvent("run_started", "a"))
        await store.append_event(AgentEvent("run_started", "b"))

        assert len(await store.get_run_events("a")) == 1
        assert len(await store.get_run_events("b")) == 1


class TestDurability:
    async def test_data_survives_reopen(self, tmp_path):
        db_path = str(tmp_path / "swarm_reopen.db")
        store = SwarmRunStore(db_path)
        await store.initialize()
        await store.create_run("run_1", {"capital": "5"}, "t")
        await store.append_event(AgentEvent("run_started", "run_1"))
        await store.close()

        reopened = SwarmRunStore(db_path)
        await reopened.initialize()
        runs = await reopened.list_runs()
        assert runs[0]["workflow_id"] == "run_1"
        assert runs[0]["request"] == {"capital": "5"}
        assert len(await reopened.get_run_events("run_1")) == 1
        await reopened.close()


class TestGuards:
    async def test_operations_require_initialize(self, tmp_path):
        store = SwarmRunStore(str(tmp_path / "nope.db"))
        with pytest.raises(RuntimeError, match="not initialized"):
            await store.list_runs()

    async def test_initialize_is_idempotent(self, tmp_path):
        store = SwarmRunStore(str(tmp_path / "idem.db"))
        await store.initialize()
        await store.initialize()
        await store.close()
