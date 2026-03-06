from langchain.messages import RemoveMessage, AIMessage
from src.agent.state import MessagesState
from src.agent.utils.skill_tool import get_skill_adapter

skill_registry = get_skill_adapter()
def router_node(state: MessagesState):
    """Route to the appropriate node based on the state and context."""
    # For this template, we simply route to the "team" node.
    messages = state.get("messages", [])
    skills = skill_registry.list_skills ()
    if len(messages) < 0:
        return "__end__"
    last = messages[-1]

    # next_skill = [skill_name for skill_name in skills if skill_name in last.content]
    for skill_name in skills:
        if skill_name in last.content:
            return "team"

    return "__end__"