import operator
from typing import Any, cast
from typing_extensions import Annotated, TypedDict
from pydantic import BaseModel

from langchain_core.messages import AnyMessage
from langchain_core.messages import RemoveMessage, HumanMessage
from src.agent.utils.load_models import load_models


class MessagesState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], operator.add]  # 主对话状态
    selected_skill: str  # 本轮选中的 skill
    skill_input: dict[str, Any]  # skill 入参
    skill_output: Any  # skill 结果
    skills_prompt: str  # 注入系统提示的技能摘要
    logs: list[str]  # 观测/调试
    error: str  # 错误信息
    summary: str  # 对话总结


def summarize_conversation(state: MessagesState):

    # First, we get any existing summary
    summary = state.get("summary", "")

    # Create our summarization prompt
    if summary:

        # A summary already exists
        summary_message = (
            f"This is a summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )

    else:
        summary_message = "Create a summary of the conversation above:"

    # Add prompt to our history
    messages = state.get ("messages", []) + [HumanMessage(content=summary_message)]
    model = load_models()
    response = model.invoke(messages)

    # Delete all but the 2 most recent messages
    delete_messages = [RemoveMessage(id=cast(str, m.id)) for m in state.get("messages", [])[:-2]]
    return {"summary": response.content, "messages": delete_messages}
