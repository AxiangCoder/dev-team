from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
import os
import logging


from langgraph.runtime import Runtime
from langchain_core.messages import AIMessage, SystemMessage

from src.agent.context import Context
from src.agent.state import MessagesState, summarize_conversation
from src.agent.utils.load_models import load_models
from src.agent.utils.skill_tool import get_skill_adapter

skill_registry = get_skill_adapter()
skill_prompts = skill_registry.build_skills_prompt()

logger = logging.getLogger(__name__)


class MainResponse(BaseModel):
    message: str = ""
    nest_skill: str | None = None


async def team(state: MessagesState, runtime: Runtime[Context]):
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
    last = messages[-1]
    last_content = getattr(last, "content", "")
    if not isinstance(last_content, str) and isinstance(last_content, dict):
        last_content = last.get("content", "")
    skills = skill_registry.list_skills()
    for skill_name in skills:
        if skill_name in last_content:
            skill = skill_registry.get_skill(skill_name)
            result = skill.handler({"messages": messages, "context": runtime.context})
            ai_msg = await llm.ainvoke([SystemMessage(content=result["instructions"])])
            return {"messages": [ai_msg]}
    else:
        system_prompt = runtime.context.system_prompt.format(
            memories=memories_text,
            time=datetime.now().isoformat(),
            skill_prompts=skill_prompts,
            next_skill="",
        )
        messages = state.get("messages", [])
        if messages and len(messages) > 10:
            messages = summarize_conversation(state)["messages"] + messages[-10:]
        # ai_msg = await llm.with_structured_output(MainResponse).ainvoke(
        #     [
        #         {"role": "system", "content": system_prompt},
        #         # *cleaned_messages,
        #         *messages[-10:],
        #     ]
        # )
        ai_msg = await llm.ainvoke(
            [
                {"role": "system", "content": system_prompt},
                # *cleaned_messages,
                # *messages[-10:],
            ]
        )
        return {"messages": [ai_msg]}
