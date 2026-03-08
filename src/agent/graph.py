"""Hierarchical supervisor graph for the agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.context import Context
from agent.nodes.assistant_node import assistant_node
from agent.nodes.finalize_node import finalize_node
from agent.nodes.team_node import (
    architecture_team_node,
    product_manager_team_node,
)
from agent.state import MessagesState


def route_after_top_supervisor(state: MessagesState) -> str:
    """Route from the top supervisor to the selected team or finalizer."""
    if state.get("final_response"):
        return "finalize_node"
    if state.get("current_team") == "product_manager":
        return "product_manager_team"
    if state.get("current_team") == "architecture":
        return "architecture_team"
    return "finalize_node"


graph = (
    StateGraph(state_schema=MessagesState, context_schema=Context)
    .add_node("assistant_node", assistant_node)
    .add_node("product_manager_team", product_manager_team_node)
    .add_node("architecture_team", architecture_team_node)
    .add_node("finalize_node", finalize_node)
    .add_edge(START, "assistant_node")
    .add_conditional_edges(
        "assistant_node",
        route_after_top_supervisor,
        {
            "product_manager_team": "product_manager_team",
            "architecture_team": "architecture_team",
            "finalize_node": "finalize_node",
        },
    )
    .add_edge("product_manager_team", "finalize_node")
    .add_edge("architecture_team", "finalize_node")
    .add_edge("finalize_node", END)
    .compile(name="hierarchical-supervisor")
)
