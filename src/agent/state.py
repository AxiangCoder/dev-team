"""Shared state schema for the hierarchical supervisor graph."""

import operator

from langchain_core.messages import AnyMessage
from typing_extensions import Annotated, Literal, TypedDict


class MessagesState(TypedDict, total=False):
    """State shared across the top-level graph and team wrappers."""

    messages: Annotated[list[AnyMessage], operator.add]
    current_team: Literal["product_manager", "architecture"]
    supervisor_reason: str
    team_status: Literal["completed", "needs_input", "in_progress"]
    team_summary: str
    team_open_questions: list[str]
    team_artifacts: dict[str, str]
    team_name: str
    final_response: str
    current_specialist: str
