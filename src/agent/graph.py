"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations


from langgraph.graph import StateGraph


from src.agent.context import Context
from src.agent.state import MessagesState
from agent.nodes.assistant_node import assistant_node
from src.agent.nodes.skill_node import skill_node
from src.agent.nodes.route_node import router_node


# Define the graph
graph = (
    StateGraph(state_schema=MessagesState, context_schema=Context)
    .add_node("assistant", assistant_node)
    .add_node("skill_node", skill_node)
    .add_edge("__start__", "assistant")
    .add_conditional_edges("assistant", router_node, ["skill_node", "__end__"])
    .add_edge("skill_node", "__end__")
    .compile()
)
