"""Top-level supervisor node for the main graph."""

from datetime import datetime
from typing import Literal, cast

from langchain_core.messages import SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel

from agent.context import Context
from agent.state import MessagesState
from agent.utils.load_models import load_models
from agent.utils.skill_tool import get_skill_adapter

SUPERVISOR_PROMPT = """
# 顶层 Supervisor

你是主流程唯一的路由决策者。
请判断用户请求应该进入产品经理团队、架构团队，还是由你直接回复。

输出协议（必须严格遵守）：
- 仅允许两种结果：`reply` 或 `route`。
- 当 `action = "reply"` 时：
  - `team` 必须为 `null`
  - `idea_summary` 必须为 `null`
  - `message` 必须是非空字符串
- 当 `action = "route"` 时：
  - `team` 必须为 `product_manager` 或 `architecture`
  - `idea_summary` 必须为用户的需求
  - `message` 必须为 `null`
- 严禁同时给出有效 `team` 和有效 `message`。
- 严禁 `team` 与 `message` 同时为空。

业务规则：
- 当请求仍处于需求澄清、用户场景、流程定义、PRD 范围时，选择 `product_manager`。
- 当请求聚焦系统设计、API、数据库、前后端实现规划或测试规划时，选择 `architecture`。
- 当需要专业团队时，总结用户的需求，并赋值给 idea_summary
- 仅在不需要进入任何专业团队时，选择 `reply`。
- 当更适合交给团队处理时，你不能直接给出完整方案。

合法示例（reply）：
{{
  "action": "reply",
  "team": null,
  "idea_summary": null,
  "reason": "用户信息不足，需先补充约束后再路由。",
  "message": "请先补充目标用户、核心功能和时间范围。"
}}

合法示例（route）：
{{
  "action": "route",
  "team": "product_manager",
  "reason": "用户处于需求初期，需要先完成 PRD 澄清。",
  "idea_summary": "xxx"
  "message": null
}}

非法示例（禁止）：
{{
  "action": "reply",
  "team": "product_manager",
  "reason": "xxx",
  "message": "xxx"
  "idea_summary": "xxx"
}}

当前时间：{time}
"""


class TopLevelDecision(BaseModel):
    """Structured decision returned by the top-level supervisor."""

    action: Literal["route", "reply"]
    team: Literal["product_manager", "architecture"] | None = None
    reason: str
    message: str | None = None
    idea_summary: str | None = None


async def assistant_node(state: MessagesState, runtime: Runtime[Context]):
    """Route the request to a team or reply directly."""
    llm = load_models()
    messages = state.get("messages", [])
    decision = cast(
        TopLevelDecision,
        await llm.with_structured_output(TopLevelDecision).ainvoke(
            [
                SystemMessage(
                    content=SUPERVISOR_PROMPT.format(
                        time=datetime.now().isoformat(),
                    )
                ),
                *messages,
            ]
        ),
    )

    if decision.action == "reply":
        return {
            "current_team": None,
            "supervisor_reason": None,
            "idea_summary": None,
            "final_response": decision.message or "请补充你的目标和约束。",
            "supervisor_reason": decision.reason,
        }

    return {
        "current_team": decision.team,
        "supervisor_reason": decision.reason,
        "idea_summary": decision.idea_summary,
        "final_response": None,
    }
