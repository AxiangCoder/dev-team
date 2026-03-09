import operator

from langchain_core.messages import AnyMessage
from typing_extensions import Annotated, TypedDict


class MessagesState(TypedDict, total=False):
    """State shared across the top-level graph and team wrappers."""
    messages: Annotated[list[AnyMessage], operator.add]

def output_node (state: MessagesState):
    return {
        **state
    }