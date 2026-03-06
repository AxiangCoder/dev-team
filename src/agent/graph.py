"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations


from langgraph.graph import StateGraph


from src.agent.context import Context
from src.agent.state import MessagesState
from src.agent.nodes.team import team
from src.agent.nodes.route_node import router_node


# Define the graph
graph = (
    StateGraph(MessagesState, context_schema=Context)
    .add_node("assistant", team)
    .add_node("team", team)
    .add_edge("__start__", "assistant")
    .add_conditional_edges("assistant", router_node, ["team", "__end__"])
    .add_edge("team", "__end__")
    .compile()
)
