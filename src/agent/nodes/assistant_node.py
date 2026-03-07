from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
import os
import logging
from typing import cast


from langgraph.runtime import Runtime
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from src.agent.context import Context
from src.agent.state import MessagesState, summarize_conversation
from src.agent.utils.load_models import load_models
from src.agent.utils.skill_tool import get_skill_adapter

skill_registry = get_skill_adapter()
skill_prompts = skill_registry.build_skills_prompt()
skill_list = skill_registry.list_skills()

logger = logging.getLogger(__name__)


system_prompt_1 = """
# Role: 全能软件开发中枢 (Dev-Central Intelligence)

## Profile
你是一个集成了全生命周期软件开发能力的 AI 调度中枢。你负责接收用户的原始创意，并调用你具备的专业技能（Skills）将其转化为可落地的技术方案和代码。

## Operational Logic (工作逻辑)
1. **意图解析**：首先识别用户请求处于开发生命周期的哪个阶段（需求调研、产品设计、架构、编码、测试等）。
2. **技能调用**：根据当前阶段，激活对应的专业技能模块。

## Global Constraints (全局约束)
- **工程化标准**：所有输出必须符合生产环境标准（代码规范、错误处理、注释清晰）。
- **交互规范**：如果需求不明确，必须追问，严禁盲目猜测。
- **语言要求**：技术讨论与文档使用中文，代码逻辑与变量命名遵循行业标准英文。

## memories (记忆)
- {memories}

## Current Time (当前时间)
- {time}
"""

sys_prompt = """
# 研发路由助理 (分发专用)

## 绝对禁止
* **禁止输出两项：** 严禁同时出现 `message` 和 `current_skill`。
* **禁止描述技能：** 除非前三名分差 < 1.0 需要用户选择，否则**禁止**列出或描述 Skill 详情。
* **禁止执行任务：** 你不是开发者，拒绝处理任何具体需求。

## 决策逻辑
1. **评分：** 关联度评分 Score in [1, 10]。
2. **全员低分 Score < 4.0：** 仅输出 `message: [言简意赅的说明拒绝理由与说明]`。
3. **高分唯一 Diff \ge 1.0：** 仅输出 `current_skill: [skill_name]`。
4. **高分重叠 Diff < 1.0：** 仅输出 `message: [对比前两名 Skill 作用并请用户选择]`。



## 上下文
* **Skills:** {skill_prompts}
* **Memories:** {memories}
* **Time:** {time}
"""

class MainResponse(BaseModel):
    message: str | None = None
    current_skill: str | None = None


async def assistant_node(state: MessagesState, runtime: Runtime[Context]):
    project_id = runtime.context.project_id
    # model = runtime.context.model
    # cleaned_messages = context_tools.clear_image_data(list(state.messages))
    memories_text = ""
    # query = context_tools.get_clean_query(cleaned_messages)
    # if query.strip():
    #     try:
    #         memories = await cast(BaseStore, runtime.store).asearch(
    #             ("memories", project_id), query=query, limit=3
    #         )
    #         if memories:
    #             memories_text = "\n".join([f"- {m.value}" for m in memories])
    #     except Exception as exc:
    #         logger.error("Memory search failed in hello_node: %s", exc)
    llm = load_models()
    messages = state.get("messages", [])
    system_prompt = sys_prompt.format(
        memories=memories_text,
        time=datetime.now().isoformat(),
        skill_prompts=skill_prompts,
        next_skill="",
    )
    messages = state.get("messages", [])
    if messages and len(messages) > 10:
        messages = summarize_conversation(state)["messages"] + messages[-10:]
    cus_message = cast(
        MainResponse,
        await llm.with_structured_output(MainResponse).ainvoke(
            [
                SystemMessage(content=system_prompt),
                *messages,
                # *cleaned_messages,
                # *messages[-10:],
            ]
        ),
    )
    if cus_message.current_skill:
        skill = skill_registry.get_skill(cus_message.current_skill)
        skill_prompt = skill.handler(cus_message.current_skill)["instructions"]
        return {
            "current_skill": cus_message.current_skill,
            "skill_prompt": skill_prompt,
        }
    ai_msg = AIMessage(content=cus_message.message, name="assistant_node")
    return {"messages": [ai_msg]}
