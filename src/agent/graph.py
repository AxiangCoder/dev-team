"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations


from langgraph.graph import StateGraph


from src.agent.context import Context
from src.agent.state import MessagesState
from src.agent.nodes.team import team


# Define the graph
graph = (
    StateGraph(MessagesState, context_schema=Context)
    .add_node(team)
    .add_edge("__start__", "team")
    .add_edge("team", "__end__")
    .compile()
)
