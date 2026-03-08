"""Product manager team subgraph."""

from datetime import datetime
from typing import Literal, cast

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

from agent.utils.load_models import load_models
from agent.utils.skill_tool import get_skill_instructions

PRODUCT_MANAGER_INSTRUCTIONS = get_skill_instructions("product-manager")


class ProductTeamState(TypedDict, total=False):
    """State carried inside the product manager subgraph."""

    request_text: str
    specialist_choice: Literal["product_explorer", "product_synthesizer"]
    specialist_reason: str
    specialist_output: str
    team_status: Literal["completed", "needs_input", "in_progress"]
    team_summary: str
    open_questions: list[str]
    artifacts: dict[str, str]


class ProductSupervisorDecision(BaseModel):
    """Routing decision made by the product team supervisor."""

    specialist: Literal["product_explorer", "product_synthesizer"]
    reason: str


class ProductReview(BaseModel):
    """Structured product team review returned to the top graph."""

    team_status: Literal["completed", "needs_input", "in_progress"]
    summary: str
    open_questions: list[str] = []
    artifacts: dict[str, str] = {}


PRODUCT_SUPERVISOR_PROMPT = """
你是产品经理团队的 supervisor。
请判断下一步应该走发散探索还是收敛整理。

- 当请求仍然模糊、信息不足时，选择 `product_explorer`。
- 当信息足够形成产品定义摘要时，选择 `product_synthesizer`。

当前时间：{time}
"""

PRODUCT_EXPLORER_PROMPT = """
{instructions}

你当前扮演产品探索专员（发散角色）。
你的任务是识别范围、用户、流程、约束和缺失信息。
请为产品 supervisor 产出简洁且可执行的工作笔记。
"""

PRODUCT_SYNTHESIZER_PROMPT = """
{instructions}

你当前扮演产品收敛专员（收敛角色）。
请将请求整理为紧凑的 PRD 风格摘要，至少包含范围、流程和优先级。
请为产品 supervisor 产出简洁且可执行的工作笔记。
"""

PRODUCT_REVIEW_PROMPT = """
你是产品经理团队 supervisor，正在审阅下属输出。
请判断产品设计是否已完成、仍在进行、或因信息缺失而阻塞。

输出要求：
- `team_status`
- `summary`
- `open_questions`
- `artifacts`
"""


async def product_supervisor_node(state: ProductTeamState) -> ProductTeamState:
    """Choose the next product specialist for the current request."""
    llm = load_models()
    decision = cast(
        ProductSupervisorDecision,
        await llm.with_structured_output(ProductSupervisorDecision).ainvoke(
            [
                SystemMessage(
                    content=PRODUCT_SUPERVISOR_PROMPT.format(
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


def route_product_specialist(state: ProductTeamState) -> str:
    """Route to the specialist chosen by the product supervisor."""
    return state.get("specialist_choice", "product_explorer")


async def product_explorer_node(state: ProductTeamState) -> ProductTeamState:
    """Expand ambiguous product requirements into working notes."""
    llm = load_models()
    response = await llm.ainvoke(
        [
            SystemMessage(
                content=PRODUCT_EXPLORER_PROMPT.format(
                    instructions=PRODUCT_MANAGER_INSTRUCTIONS
                )
            ),
            {"role": "user", "content": state.get("request_text", "")},
        ]
    )
    return {"specialist_output": str(response.content)}


async def product_synthesizer_node(state: ProductTeamState) -> ProductTeamState:
    """Synthesize a compact product definition from the request."""
    llm = load_models()
    response = await llm.ainvoke(
        [
            SystemMessage(
                content=PRODUCT_SYNTHESIZER_PROMPT.format(
                    instructions=PRODUCT_MANAGER_INSTRUCTIONS
                )
            ),
            {"role": "user", "content": state.get("request_text", "")},
        ]
    )
    return {"specialist_output": str(response.content)}


async def product_review_node(state: ProductTeamState) -> ProductTeamState:
    """Review product team output and decide whether the phase is done."""
    llm = load_models()
    review = cast(
        ProductReview,
        await llm.with_structured_output(ProductReview).ainvoke(
            [
                SystemMessage(content=PRODUCT_REVIEW_PROMPT),
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


product_team_graph = (
    StateGraph(ProductTeamState)
    .add_node("product_supervisor", product_supervisor_node)
    .add_node("product_explorer", product_explorer_node)
    .add_node("product_synthesizer", product_synthesizer_node)
    .add_node("product_review", product_review_node)
    .add_edge(START, "product_supervisor")
    .add_conditional_edges(
        "product_supervisor",
        route_product_specialist,
        {
            "product_explorer": "product_explorer",
            "product_synthesizer": "product_synthesizer",
        },
    )
    .add_edge("product_explorer", "product_review")
    .add_edge("product_synthesizer", "product_review")
    .add_edge("product_review", END)
    .compile(name="product-team")
)
