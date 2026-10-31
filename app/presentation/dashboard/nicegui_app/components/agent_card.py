"""Pipeline step track for the Agent Swarm page.

Replaces the old step list with a visual progress rail: ten numbered
nodes joined by connectors that fill as steps complete, the active node
pulsing, plus a "NOW" narration panel showing what the pipeline is doing
at this moment. Every node opens the step details dialog on click.
"""

from __future__ import annotations

from app.services.agent_swarm.executor import AGENT_SPECS

# Plain-English, novice-friendly presentation of each pipeline stage
STEP_TITLES: dict[str, tuple[str, str]] = {
    "t11": ("Check your inputs", "Makes sure capital, goal and time frame make sense"),
    "t21": ("Build your profile", "Classifies your capital and picks which modules to enable"),
    "t31": ("Tune the modules", "Sets each module's parameters to match your profile"),
    "t41": ("Simulate the strategy", "Backtest: runs the portfolio over the selected test period"),
    "t51": ("Validate the result", "Checks costs, capital and feasibility gates"),
    "t61": ("Pick the best strategy", "Scores the strategies and recommends the best fit"),
    "t71": ("Allocate capital", "Works out how much to invest in each module"),
    "t81": ("Adjust risk", "Adapts positions to market regime and volatility"),
    "t91": ("Generate the report", "Summarises strengths and weaknesses"),
    "t101": ("Decide", "Approved, conditional or rejected"),
}


def step_title(agent_id: str) -> tuple[str, str]:
    fallback = next((spec.name for spec in AGENT_SPECS if spec.agent_id == agent_id), "Step")
    return STEP_TITLES.get(agent_id, (fallback, ""))
