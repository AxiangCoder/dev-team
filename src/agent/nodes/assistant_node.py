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
你是一个开发团队的助理，负责收集客户的输入，并协助团队成员完成软件开发相关的任务。
要求：
1. message 和 current_skill 只能有一个有值
1. 用户说的和你的任意技能无关，则引导用户提出真实需求，输出 message
2. 若有关，则直接说出 skill 名字，输出 current_skill

你具备以下技能：
{skill_prompts}
memories: {memories}
当前时间: {time}
"""

class MainResponse(BaseModel):
    message: str = ""
    current_skill: str | None = None


async def assistant_node(state: MessagesState, runtime: Runtime[Context]):
    project_id = runtime.context.project_id
    # model = runtime.context.model
    # cleaned_messages = context_tools.clear_image_data(list(state.messages))
    memories_text = "无相关记忆"
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
    ai_msg = cast(MainResponse, await llm.with_structured_output(MainResponse).ainvoke(
        [   
            *messages,
            SystemMessage(content=system_prompt),
            # *cleaned_messages,
            # *messages[-10:],
        ]
    ))
    if ai_msg.current_skill:
        skill = skill_registry.get_skill(ai_msg.current_skill)
        skill_prompt = skill.handler(ai_msg.current_skill)
        return {"current_skill": ai_msg.current_skill, "skill_prompt": skill_prompt}

    return {"messages": [
        AIMessage(ai_msg.message)
    ]}
