from typing_extensions import TypedDict, Annotated
from typing import cast
from pathlib import Path
from datetime import datetime
import os
import logging


from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from lib.skill_adapter import build_skill_registry

from src.agent.utils import context_tools
from src.agent.context import Context
from src.agent.state import MessagesState, summarize_conversation
from src.agent.utils.load_models import load_models


skill_registry = build_skill_registry(Path("src/agent/skills"))
skill_prompts = skill_registry.build_skills_prompt()

logger = logging.getLogger(__name__)


async def team(state: MessagesState, runtime: Runtime[Context]):
    project_id = runtime.context.project_id
    # model = runtime.context.model
    system_prompt = runtime.context.system_prompt + "\n\n" + skill_prompts
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
    sys_content = system_prompt.format(
        memories=memories_text, time=datetime.now().isoformat()
    )

    messages = state.get("messages", [])
    if messages and len(messages) > 10:
        messages = summarize_conversation(state)["messages"] + messages[-10:]
    ai_msg = await llm.ainvoke(
        [
            {"role": "system", "content": sys_content},
            # *cleaned_messages,
            *messages[-10:],
        ]
    )
    return {"messages": [ai_msg]}
