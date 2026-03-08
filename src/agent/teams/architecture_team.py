"""Architecture team subgraph."""

from datetime import datetime
from typing import Literal, cast

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

from agent.utils.load_models import load_models
from agent.utils.skill_tool import get_skill_instructions

ARCHITECT_INSTRUCTIONS = get_skill_instructions("architect-specialist")
BACKEND_INSTRUCTIONS = get_skill_instructions("backend-engineer")
FRONTEND_INSTRUCTIONS = get_skill_instructions("frontend-engineer")
QA_INSTRUCTIONS = get_skill_instructions("qa-engineer")


class ArchitectureTeamState(TypedDict, total=False):
    """State carried inside the architecture team subgraph."""

    request_text: str
    specialist_choice: Literal[
        "architect_specialist",
        "backend_engineer",
        "frontend_engineer",
        "qa_engineer",
    ]
    specialist_reason: str
    specialist_output: str
    team_status: Literal["completed", "needs_input", "in_progress"]
    team_summary: str
    open_questions: list[str]
    artifacts: dict[str, str]


class ArchitectureSupervisorDecision(BaseModel):
    """Routing decision made by the architecture supervisor."""

    specialist: Literal[
        "architect_specialist",
        "backend_engineer",
        "frontend_engineer",
        "qa_engineer",
    ]
    reason: str


class ArchitectureReview(BaseModel):
    """Structured architecture review returned to the top graph."""

    team_status: Literal["completed", "needs_input", "in_progress"]
    summary: str
    open_questions: list[str] = []
    artifacts: dict[str, str] = {}


ARCHITECTURE_SUPERVISOR_PROMPT = """
你是架构团队的 supervisor。
请为当前技术阶段选择最合适的下属角色。

- `architect_specialist`：系统架构、API 规范、数据模型、模块拆分。
- `backend_engineer`：服务端逻辑、数据流、接口实现细节。
- `frontend_engineer`：界面结构、路由、页面状态与前后端联调。
- `qa_engineer`：测试计划、质量风险评估、验收策略。

当前时间：{time}
"""

ARCHITECT_SPECIALIST_PROMPT = """
{instructions}

你当前扮演架构专员。
请为 supervisor 输出可执行的架构说明笔记。
"""

BACKEND_SPECIALIST_PROMPT = """
{instructions}

你当前扮演后端专员。
请为 supervisor 输出可执行的后端实现说明笔记。
"""

FRONTEND_SPECIALIST_PROMPT = """
{instructions}

你当前扮演前端专员。
请为 supervisor 输出可执行的前端实现说明笔记。
"""

QA_SPECIALIST_PROMPT = """
{instructions}

你当前扮演测试专员。
请为 supervisor 输出可执行的质量与测试说明笔记。
"""

ARCHITECTURE_REVIEW_PROMPT = """
你是架构团队 supervisor，正在审阅下属输出。
请判断当前架构/设计阶段是否已完成、仍在进行、或因信息缺失而阻塞。

输出要求：
- `team_status`
- `summary`
- `open_questions`
- `artifacts`
"""


async def architecture_supervisor_node(
    state: ArchitectureTeamState,
) -> ArchitectureTeamState:
    """Choose the next architecture specialist for the current request."""
    llm = load_models()
    decision = cast(
        ArchitectureSupervisorDecision,
        await llm.with_structured_output(ArchitectureSupervisorDecision).ainvoke(
            [
                SystemMessage(
                    content=ARCHITECTURE_SUPERVISOR_PROMPT.format(
                        time=datetime.now().isoformat()
                    )
                ),
                {
                    "role": "user",
                    "content": state.get("request_text", ""),
                },
            ]
        ),
    )
    return {
        "specialist_choice": decision.specialist,
        "specialist_reason": decision.reason,
    }


def route_architecture_specialist(state: ArchitectureTeamState) -> str:
    """Route to the specialist chosen by the architecture supervisor."""
    return state.get("specialist_choice", "architect_specialist")


async def architect_specialist_node(
    state: ArchitectureTeamState,
) -> ArchitectureTeamState:
    """Produce system-level architecture notes."""
    llm = load_models()
    response = await llm.ainvoke(
        [
            SystemMessage(
                content=ARCHITECT_SPECIALIST_PROMPT.format(
                    instructions=ARCHITECT_INSTRUCTIONS
                )
            ),
            {"role": "user", "content": state.get("request_text", "")},
        ]
    )
    return {"specialist_output": str(response.content)}


async def backend_engineer_node(state: ArchitectureTeamState) -> ArchitectureTeamState:
    """Produce backend implementation notes."""
    llm = load_models()
    response = await llm.ainvoke(
        [
            SystemMessage(
                content=BACKEND_SPECIALIST_PROMPT.format(
                    instructions=BACKEND_INSTRUCTIONS
                )
            ),
            {"role": "user", "content": state.get("request_text", "")},
        ]
    )
    return {"specialist_output": str(response.content)}


async def frontend_engineer_node(
    state: ArchitectureTeamState,
) -> ArchitectureTeamState:
    """Produce frontend implementation notes."""
    llm = load_models()
    response = await llm.ainvoke(
        [
            SystemMessage(
                content=FRONTEND_SPECIALIST_PROMPT.format(
                    instructions=FRONTEND_INSTRUCTIONS
                )
            ),
            {"role": "user", "content": state.get("request_text", "")},
        ]
    )
    return {"specialist_output": str(response.content)}


async def qa_engineer_node(state: ArchitectureTeamState) -> ArchitectureTeamState:
    """Produce quality and testing notes."""
    llm = load_models()
    response = await llm.ainvoke(
        [
            SystemMessage(
                content=QA_SPECIALIST_PROMPT.format(instructions=QA_INSTRUCTIONS)
            ),
            {"role": "user", "content": state.get("request_text", "")},
        ]
    )
    return {"specialist_output": str(response.content)}


async def architecture_review_node(
    state: ArchitectureTeamState,
) -> ArchitectureTeamState:
    """Review architecture team output and decide whether the phase is done."""
    llm = load_models()
    review = cast(
        ArchitectureReview,
        await llm.with_structured_output(ArchitectureReview).ainvoke(
            [
                SystemMessage(content=ARCHITECTURE_REVIEW_PROMPT),
                {
                    "role": "user",
                    "content": (
                        f"request:\n{state.get('request_text', '')}\n\n"
                        f"specialist_output:\n{state.get('specialist_output', '')}"
                    ),
                },
            ]
        ),
    )
    return {
        "team_status": review.team_status,
        "team_summary": review.summary,
        "open_questions": review.open_questions,
        "artifacts": review.artifacts,
    }


architecture_team_graph = (
    StateGraph(ArchitectureTeamState)
    .add_node("architecture_supervisor", architecture_supervisor_node)
    .add_node("architect_specialist", architect_specialist_node)
    .add_node("backend_engineer", backend_engineer_node)
    .add_node("frontend_engineer", frontend_engineer_node)
    .add_node("qa_engineer", qa_engineer_node)
    .add_node("architecture_review", architecture_review_node)
    .add_edge(START, "architecture_supervisor")
    .add_conditional_edges(
        "architecture_supervisor",
        route_architecture_specialist,
        {
            "architect_specialist": "architect_specialist",
            "backend_engineer": "backend_engineer",
            "frontend_engineer": "frontend_engineer",
            "qa_engineer": "qa_engineer",
        },
    )
    .add_edge("architect_specialist", "architecture_review")
    .add_edge("backend_engineer", "architecture_review")
    .add_edge("frontend_engineer", "architecture_review")
    .add_edge("qa_engineer", "architecture_review")
    .add_edge("architecture_review", END)
    .compile(name="architecture-team")
)
