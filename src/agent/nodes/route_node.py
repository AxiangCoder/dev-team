from langgraph.runtime import Runtime
from langchain.messages import RemoveMessage, AIMessage


from src.agent.state import MessagesState
from src.agent.utils.skill_tool import get_skill_adapter
from src.agent.context import Context

skill_registry = get_skill_adapter()
def router_node(state: MessagesState):
    """Route to the appropriate node based on the state and context."""
    if (
        state.get("current_skill", None) is not None
        and state.get("skills_prompt", None) is not None
    ):
        return "skill_node"
    return "__end__"
