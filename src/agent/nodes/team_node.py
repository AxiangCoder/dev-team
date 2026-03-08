"""Wrapper nodes that invoke team-level subgraphs."""

from typing import Any

from langgraph.runtime import Runtime

from agent.context import Context
from agent.state import MessagesState
from agent.teams.architecture_team import architecture_team_graph
from agent.teams.product_team import product_team_graph


def _latest_user_text(state: MessagesState) -> str:
    for message in reversed(state.get("messages", [])):
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


async def product_manager_team_node(state: MessagesState, runtime: Runtime[Context]):
    """Invoke the product manager subgraph and normalize its output."""
    result: dict[str, Any] = await product_team_graph.ainvoke(
        {"request_text": _latest_user_text(state)}
    )
    return {
        "team_name": "product_manager",
        "team_status": result.get("team_status", "in_progress"),
        "team_summary": result.get("team_summary", ""),
        "team_open_questions": result.get("open_questions", []),
        "team_artifacts": result.get("artifacts", {}),
        "current_specialist": result.get("specialist_choice", ""),
    }


async def architecture_team_node(state: MessagesState, runtime: Runtime[Context]):
    """Invoke the architecture subgraph and normalize its output."""
    result: dict[str, Any] = await architecture_team_graph.ainvoke(
        {"request_text": _latest_user_text(state)}
    )
    return {
        "team_name": "architecture",
        "team_status": result.get("team_status", "in_progress"),
        "team_summary": result.get("team_summary", ""),
        "team_open_questions": result.get("open_questions", []),
        "team_artifacts": result.get("artifacts", {}),
        "current_specialist": result.get("specialist_choice", ""),
    }
