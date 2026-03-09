import json
import operator
from typing import cast
from typing_extensions import Annotated, TypedDict
from pydantic import BaseModel


from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from langchain_core.messages import SystemMessage, AIMessage, AnyMessage, HumanMessage
from langgraph.runtime import Runtime


from src.pm.state import Node1Output
from src.utils.load_models import load_models
from src.pm.context import Context


SUMMERY_PROMPT = """
**Role:** 你是一位拥有 10 年经验的资深资深产品架构师，擅长将复杂的业务愿景拆解为可落地的功能矩阵。

**Task:**
根据用户的原始输入: {user_input} 和之前收集的用户对话信息: {log}，定义业务全景（Epic）和核心目标，并将其拆解为一组独立的、颗粒度适中的用户故事（User Stories）。

**Guidelines:**
1. **模块化拆解：** 识别业务流程中的关键阶段（例如：鉴权、搜索、支付、通知）。每个模块即为一个 Feature Group。
2. **定义故事：** 针对每个模块，识别 1-2 个最核心的用户故事。
3. **优先级排序：** 使用 P0 (核心/阻断性)、P1 (重要/非阻断)、P2 (增强型) 进行标注。确保 P0 构成 MVP（最小可行性产品）路径。
4. **输出状态：** 此时仅需填充故事的基础信息，验收标准（AC）留空。

**Output Requirements:**
- `epic`: 项目的宏观名称。
- `business_goal`: 一句话描述该项目要解决的核心商业价值。
- `stories`: 包含 `story_id`, `feature_group`, `title`, `priority`, `user_description` 的列表。

**Constraint:**
- 不要输出具体的验收标准（AC）, 保持输出简洁，聚焦于“做什么”而非“怎么做”。
"""

STORE_PROMPT = """
**Role:** 你是一位拥有 10 年经验的资深资深产品架构师，说话言简意赅，追求效率，擅长将复杂的业务愿景拆解为可落地的功能矩阵。

**Task:**
- 分析用户的原始输入: `user_input`, 
- 定义业务全景和核心目标
- 向用户确认 软件用户角色列表 `persona`
- 生成用户故事梗概（ 那个软件用户角色？+ 做什么等 ），并立即加入 `pedding_story` 
- 基于用户的回复 `last_aws`，更新 `pedding_story`
- 基于用户的回复 `last_aws`，更新 `persona`
- 基于 `user_input` 继续生成其他区需求
- 如果用户表示不再有需求，则 is_current_finished 设置为 True

**Output Requirements:**
- `content`: 与用户的交流
- `pedding_story`: 已经挖掘出的需求列表。
- `persona`: 已经挖掘出的用户角色。
- `is_current_finished`: 是否已经将需求挖掘完成。


**Output.content Requirements**
- 需要列举 `persona`
- 需要用户角色列举 `pedding_story`
- 需要想用户确认当前需求或者询问用户是否有新需求

**Constraint:**
- 少用专业名词
- 不要输出具体的验收标准（AC），保持输出简洁，聚焦于“做什么”而非“怎么做”。
- 如果所有功能都以收集完成，is_current_finished 设置为 True 否则为 False
- 用户补充的，直接加入 `pedding_story`
- 每个需求最多 2 轮挖掘，你的目的是让挖掘用户更多的实际需求
- 不要去深入分析需求的完整性


**pedding_story**
{pedding_story}

**user_input**
{user_input}

**last_aws**
{last_aws}

**persona**
{persona}
"""


class RawStoryState(TypedDict, total=False):
    """State shared across the top-level graph and team wrappers."""

    messages: Annotated[list[AnyMessage], operator.add]
    user_input: str
    pedding_story: list[str]
    persona: list[str]
    is_current_finished: bool
    last_aws: str
    log: list[dict[str, str]]


class RawStoreOutput(BaseModel):
    content: str
    pedding_story: list[str]
    persona: list[str]
    is_current_finished: bool


def raw_story_route(state: RawStoryState):
    if state.get("is_current_finished", False):
        return "_summery"
    return "ask_raw_story"


async def ask_raw_story(state: RawStoryState, runtime: Runtime[Context]):
    """
    笼统定义用户故事，并询问用户是否还有新增的需求（用户故事）
    """
    llm = load_models(temperature="0.7")
    messages = state.get("messages", [])
    user_input = state.get("user_input", "我想做一个相机租赁小程序")
    last_aws = state.get("last_aws", "")
    pedding_story = state.get("pedding_story", [])
    persona = state.get("persona", [])
    sys_prompt = SystemMessage(
        content=STORE_PROMPT.format(
            user_input=user_input,
            last_aws=last_aws,
            pedding_story=json.dumps(
                pedding_story,
                ensure_ascii=False,
            ),
            persona=json.dumps(persona, ensure_ascii=False),
            name="raw_story",
        )
    )
    output = cast(
        RawStoreOutput,
        await llm.with_structured_output(RawStoreOutput).ainvoke(
            input=[sys_prompt, *messages]
        ),
    )

    # 只返回增量消息，避免 Annotated[list, operator.add] 场景下重复叠加历史
    return {
        "messages": [
            AIMessage(content=output.content, name="raw_story"),
        ],
        "pedding_story": output.pedding_story,
        "persona": output.persona,
    }


async def wait_raw_story_input(state: RawStoryState, runtime: Runtime[Context]):
    """中断等待用户输入，并把用户回答写入状态。"""
    messages = state.get("messages", [])
    question = cast(str, messages[len(messages) - 1].content)
    approve = interrupt(question)
    return {
        "messages": [HumanMessage(content=str(approve), name="raw_story")],
        "last_aws": str(approve),
        "log": [*state.get("log", []), {"q": question, "a": str(approve)}],
    }


async def apply_raw_story_answer(state: RawStoryState, runtime: Runtime[Context]):
    """应用本轮模型提案，准备下一轮路由。"""
    return {
        "is_current_finished": bool(state.get("is_current_finished", False)),
        "pedding_story": state.get(
            "pedding_story", state.get("pedding_story", [])
        ),
    }


async def _summery(state: RawStoryState, runtime: Runtime[Context]):
    """
    格式化用户输出用户故事
    """
    messages = state.get("messages", [])
    user_input = state.get("user_input", "我想做一个相机租赁小程序")
    log = state.get("log", "")
    sys_prompt = SystemMessage(
        content=SUMMERY_PROMPT.format(user_input=user_input, log=log)
    )
    llm = load_models()
    res = await llm.with_structured_output(Node1Output).ainvoke(
        input=[*messages, sys_prompt]
    )

    return {"messages": messages}


_state_grapy = StateGraph(state_schema=RawStoryState, context_schema=Context)
_state_grapy.add_node(ask_raw_story)
_state_grapy.add_node(wait_raw_story_input)
_state_grapy.add_node(apply_raw_story_answer)
_state_grapy.add_node(_summery)

_state_grapy.add_edge(START, "ask_raw_story")
_state_grapy.add_edge("ask_raw_story", "wait_raw_story_input")
_state_grapy.add_edge("wait_raw_story_input", "apply_raw_story_answer")
_state_grapy.add_conditional_edges(
    "apply_raw_story_answer",
    raw_story_route,
    {"ask_raw_story": "ask_raw_story", "_summery": "_summery"},
)
_state_grapy.add_edge("_summery", END)


raw_story_graph = _state_grapy.compile(name="raw_story_graph")
