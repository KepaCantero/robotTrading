"""Agent Swarm execution package.

Runs the CAPA 2 parametrization pipeline (T1.1-T10.1) as a swarm of agents,
emitting per-agent events (input, output, duration, status) that feed the
Mission Control dashboard and persisting runs to SQLite for replay.
"""

from app.services.agent_swarm.events import AgentEvent, AgentEventBus
from app.services.agent_swarm.executor import AGENT_SPECS, Capa2PipelineExecutor, SwarmRunRequest
from app.services.agent_swarm.serialization import safe_json
from app.services.agent_swarm.store import DEFAULT_SWARM_DB_PATH, SwarmRunStore

__all__ = [
    "AGENT_SPECS",
    "AgentEvent",
    "AgentEventBus",
    "Capa2PipelineExecutor",
    "DEFAULT_SWARM_DB_PATH",
    "SwarmRunRequest",
    "SwarmRunStore",
    "safe_json",
]
