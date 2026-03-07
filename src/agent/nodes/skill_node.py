from datetime import datetime


from langgraph.runtime import Runtime
from langchain_core.messages import AIMessage, SystemMessage


from src.agent.context import Context
from src.agent.state import MessagesState, summarize_conversation
from src.agent.utils.load_models import load_models


async def skill_node (state: MessagesState, runtime: Runtime[Context]):
    messages = state.get("messages", [])
    memories_text = ""
    llm = load_models()
    skill_prompt = state.get("skill_prompt", "")
    skill_prompt += "\n\n" + "memories: " + memories_text
    skill_prompt += "\n\n" + "time: " + datetime.now().isoformat()
    ai_msg = await llm.ainvoke([SystemMessage(content=skill_prompt), *messages])
    ai_msg.name = "skill_node"
    return {
        "messages": [
            ai_msg,
        ]
    }
