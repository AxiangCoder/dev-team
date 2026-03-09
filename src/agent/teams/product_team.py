"""产品经理团队子图."""

import operator
import json
from datetime import datetime
from typing import Literal, cast, TypedDict
from typing_extensions import TypedDict, Annotated

from langchain_core.messages import SystemMessage, AnyMessage, HumanMessage, AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from agent.utils.load_models import load_models


class ConversionLog(TypedDict):
    question: str
    user_answer: str


class ProductTeamState(TypedDict, total=False):
    """产品经理子图内部流转状态."""
    # 默认
    messages: Annotated[list[AnyMessage], operator.add]
    # 父图传入
    idea_summary: str  # 当前轮的需求文本（含用户补充信息）

    specialist_choice: Literal[
        "product_explorer", "product_synthesizer"
    ]  # 当前选择的下属角色
    specialist_reason: str  # 选择该下属角色的理由
    specialist_output: str  # 下属角色产出的自然语言内容

    # 共用
    current_ques: str
    pending_questions: list[str]  # 历史未回答的关键问题列表
    latest_user_answer: str  # 最近一次用户恢复（resume）时提交的回答
    discovery_snapshot: dict[str, str]  # 发散阶段沉淀的事实快照

    # explorer_node
    conversation_log: list[ConversionLog]
    critical_gaps: list[str]  # 关键缺口列表（按优先级）
    current_question: str  # 下一轮仅允许提出的单个问题
    recommended_options: list[str]  # 对 current_question 的推荐选项
    assumptions: list[str]  # 暂时采用的假设及简述
    readiness_score: int  # 需求就绪度（0-100）
    team_status: Literal["completed", "needs_input", "in_progress"]  # 子图阶段状态
    team_summary: str  # 子图摘要输出
    open_questions: list[str]  # 当前仍需外部回答的问题列表
    artifacts: dict[str, str]  # 结构化产物（供上层图消费）


class ProductSupervisorDecision(BaseModel):
    """产品团队 supervisor 的路由决策."""

    specialist: Literal["product_explorer", "product_synthesizer"]
    reason: str


class ProductReview(BaseModel):
    """回传给主图的产品评审结果."""

    team_status: Literal["completed", "needs_input", "in_progress"]
    summary: str
    open_questions: list[str] = []
    artifacts: dict[str, str] = {}


class ProductExplorerOutput(BaseModel):
    """产品发散专员的结构化输出."""

    discovery_snapshot: dict[str, str]  # 已确认事实快照（用户、场景、范围、约束等）
    critical_gaps: list[str]  # 关键缺口列表（按优先级排序）
    current_question: str  # 下一轮唯一要问的问题
    recommended_options: list[str]  # 对 current_question 的推荐选项（2-4 个）
    assumptions: list[str]  # 当前采用的假设说明
    readiness_score: int  # 需求就绪度分数（0-100）
    deferred_questions: list[str]  # 用户暂时不想回答的问题
    notes: str  # 给产品 supervisor 的简要工作笔记


PRODUCT_SUPERVISOR_PROMPT = """
你是产品经理团队的 supervisor。
请判断下一步应该走发散探索还是收敛整理。

- 当请求仍然模糊、信息不足时，选择 `product_explorer`。
- 当信息足够形成产品定义摘要时，选择 `product_synthesizer`。

当前时间：{time}
"""

PRODUCT_EXPLORER_PROMPT = """
# 角色：产品探索专员（发散）

你是产品经理团队中的产品探索专员。

角色目标：
- 将模糊想法转化为明确需求，聚焦用户、场景、价值和边界。
- 优先识别阻塞后续设计的关键信息缺口。

工作准则：
- 以需求定义为核心，不直接输出开发实现方案。
- 对不确定信息明确标注假设，不要伪造事实。

你的任务是挖掘用户故事，识别范围、用户、流程、约束和缺失信息，并输出结构化探索结果。

工作流程：
- 根据 `latest_user_answer` 和 current_question（如果存在的话），以及历史聊天记录判断是否需要生成新的问题，如果生成新问题，则追加进 pending_questions
- 如果用户的回答比较消极（ 比如 "这个问题后续在说","或者是暂时不想回答"这种类似），先将这个问题放入 `deferred_questions`字段，然后删除 `critical_gap` 和 `pending_questions` 和这个问题相关的问题，
- 每次提问前，根据 pending_questions 中的问题以及 `critical_gaps` 的优先级进行排序
- 将 `pending_questions` 中，排序第一的问题向用户提问
- 当有 `conversation_log` 输入，且`pending_questions`中不再有问题时，则生成一篇完整的需求发散文档，并完成 `discovery_snapshot`字段


硬性要求：
- 每轮只允许提出 1 个问题（`current_question`）, 其他问题以记录在（`pending_questions`）中。
- 给出不超过 3 个推荐选项（`recommended_options`），第 1 个应是最推荐选项。
- `critical_gaps` 必须按优先级排序。
- 结合`current_question`分析用户的回答`latest_user_answer`，是继续基于`current_question`继续追问，还是基于`pending_questions`和`critical_gaps`继续提问
- `readiness_score` 取值 0-100。
- 如果已有待回答问题，请合并到 `critical_gaps` 并继续保留在输出逻辑中。

"""

PRODUCT_SYNTHESIZER_PROMPT = """
# 角色：产品收敛专员（收敛）

你是产品经理团队中的产品收敛专员。

角色目标：
- 将探索结果沉淀为紧凑且可执行的产品定义。
- 保持需求可被架构与研发直接消费。

工作准则：
- 输出聚焦于范围、流程、优先级和验收标准。
- 对未决问题显式列出，不要假装已解决。

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
    """根据当前需求选择下一位产品下属角色."""
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
                {"role": "user", "content": state.get("idea_summary")},
            ]
        ),
    )
    return {
        "specialist_choice": decision.specialist,
        "specialist_reason": decision.reason,
        "latest_user_answer": state.get("idea_summary", ""),
    }


def route_product_specialist(state: ProductTeamState) -> str:
    """路由到产品 supervisor 选中的下属节点."""
    return state.get("specialist_choice", "product_explorer")


def route_after_explorer(state: ProductTeamState) -> str:
    """保留函数：当前未接入路由，后续用于发散阶段分支控制."""
    if len(state.get("recommended_options", [])) == 0:
        return "product_review"
    return "product_explorer"


async def product_explorer_node(state: ProductTeamState) -> ProductTeamState:
    """执行需求发散，沉淀结构化探索结果."""
    messages = state.get("messages", [])
    llm = load_models()
    pending_questions = state.get("pending_questions", [])
    conversion_log = state.get("conversion_log", [])
    if len(pending_questions) == 0 and len(conversion_log) != 0:
        return {
            "specialist_output": state.get("notes", ""),
            "discovery_snapshot": state.get("discovery_snapshot", {}),
        }
    payload = {
        "latest_user_answer": state.get("latest_user_answer", ""),
        "pending_questions": pending_questions,
        "critical_gaps": state.get("critical_gaps"),
    }

    result = cast(
        ProductExplorerOutput,
        await llm.with_structured_output(ProductExplorerOutput).ainvoke(
            [
                SystemMessage(content=PRODUCT_EXPLORER_PROMPT),
                *messages,
                HumanMessage(content=f"{json.dumps(payload, ensure_ascii=False)}"),
            ]
        ),
    )
    options_str = "\n".join(result.recommended_options)
    display_text = f"{result.current_question}\n{options_str}"
    latest_user_answer = interrupt(display_text)
    return {
        "messages": [
            AIMessage("result.current_question", name="product_explorer_node"),
            HumanMessage("latest_user_answer"),
        ],
        "latest_user_answer": latest_user_answer,
        "pending_questions": pending_questions,
        "critical_gaps": result.critical_gaps,
        "current_question": result.current_question,
        "conversation_log": [
            *state.get("exploration", []),
            {"question": result.current_question, "user_answer": ""},
        ],
    }


async def product_synthesizer_node(state: ProductTeamState) -> ProductTeamState:
    """执行需求收敛，生成紧凑产品定义摘要."""
    llm = load_models()
    response = await llm.ainvoke(
        [
            SystemMessage(content=PRODUCT_SYNTHESIZER_PROMPT),
            {
                "role": "user",
                "content": (
                    f"用户请求：{state.get('request_text', '')}\n\n"
                    f"发现快照：{state.get('discovery_snapshot', {})}\n\n"
                    f"关键缺口：{state.get('critical_gaps', [])}\n\n"
                    f"假设：{state.get('assumptions', [])}"
                ),
            },
        ]
    )
    return {"specialist_output": str(response.content)}


async def product_review_node(state: ProductTeamState) -> ProductTeamState:
    """评审下属输出，并在必要时通过 interrupt 发起人机澄清."""
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
    needs_input = state.get("readiness_score", 0) < 75 or bool(
        state.get("pending_questions")
    )
    if needs_input:
        current_question = state.get("current_question", "")
        if not current_question and state.get("pending_questions"):
            current_question = state["pending_questions"][0]

        resume_payload = interrupt(
            {
                "team_name": "product_manager",
                "team_status": "needs_input",
                "question": current_question,
                "recommended_options": state.get("recommended_options", []),
                "pending_questions": state.get("pending_questions", []),
                "summary": review.summary,
            }
        )

        if isinstance(resume_payload, dict):
            user_answer = str(
                resume_payload.get("answer")
                or resume_payload.get("message")
                or resume_payload
            ).strip()
        else:
            user_answer = str(resume_payload).strip()

        merged_request = state.get("request_text", "")
        if user_answer:
            merged_request = f"{merged_request}\n\n用户补充：{user_answer}".strip()

        pending = list(state.get("pending_questions", []))
        if current_question and user_answer:
            pending = [item for item in pending if item != current_question]

        return {
            "request_text": merged_request,
            "latest_user_answer": user_answer,
            "pending_questions": pending,
            "team_status": "in_progress",
            "team_summary": "已接收用户补充信息，继续产品需求澄清。",
            "open_questions": pending,
            "artifacts": {
                **review.artifacts,
                "discovery_snapshot": str(state.get("discovery_snapshot", {})),
                "critical_gaps": str(state.get("critical_gaps", [])),
                "current_question": current_question,
                "recommended_options": str(state.get("recommended_options", [])),
                "assumptions": str(state.get("assumptions", [])),
                "readiness_score": str(state.get("readiness_score", 0)),
            },
        }

    return {
        "team_status": review.team_status,
        "team_summary": review.summary,
        "open_questions": review.open_questions,
        "artifacts": {
            **review.artifacts,
            "discovery_snapshot": str(state.get("discovery_snapshot", {})),
            "critical_gaps": str(state.get("critical_gaps", [])),
            "current_question": state.get("current_question", ""),
            "recommended_options": str(state.get("recommended_options", [])),
            "assumptions": str(state.get("assumptions", [])),
            "readiness_score": str(state.get("readiness_score", 0)),
        },
    }


def route_after_product_review(state: ProductTeamState) -> str:
    """评审后路由：进行中回到 supervisor，完成则结束子图."""
    if state.get("team_status") == "in_progress":
        return "product_supervisor"
    return "__end__"


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
    # .add_edge("product_explorer", "product_review")
    .add_conditional_edges(
        "product_explorer",
        route_after_explorer,
        {"product_explorer": "product_explorer", "product_review": "product_review"},
    )
    .add_edge("product_synthesizer", "product_review")
    .add_conditional_edges(
        "product_review",
        route_after_product_review,
        {
            "product_supervisor": "product_supervisor",
            "__end__": END,
        },
    )
    .compile(name="product-team")
)
