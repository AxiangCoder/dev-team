"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations


from langgraph.graph import StateGraph


from src.agent.context import Context
from src.agent.state import MessagesState
from src.agent.nodes.team import hello_node


# Define the graph
graph = (
    StateGraph(MessagesState, context_schema=Context)
    .add_node(hello_node)
    .add_edge("__start__", "hello_node")
    .add_edge("hello_node", "__end__")
    .compile()
)
