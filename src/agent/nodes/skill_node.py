from datetime import datetime


from langgraph.runtime import Runtime
from langchain_core.messages import AIMessage, SystemMessage


from src.agent.context import Context
from src.agent.state import MessagesState, summarize_conversation
from src.agent.utils.load_models import load_models


async def skill_node (state: MessagesState, runtime: Runtime[Context]):
    messages = state.get("messages", [])
    memories_text = "无相关记忆"
    llm = load_models()
    skills_prompt = state.get("skills_prompt", "")
    skills_prompt += "\n\n" + "memories: " + memories_text
    skills_prompt += "\n\n" + "time: " + datetime.now().isoformat()
    ai_msg = await llm.ainvoke([*messages, SystemMessage(skills_prompt)])
    return {
        "messages": [
            ai_msg,
        ]
    }
