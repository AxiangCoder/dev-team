"""Final response node for the hierarchical supervisor graph."""

from langchain_core.messages import AIMessage

from agent.state import MessagesState


def finalize_node(state: MessagesState):
    """Convert structured team output into the final assistant message."""
    if state.get("final_response"):
        return {"messages": [AIMessage(content=state["final_response"], name="finalize_node")]}

    team_name = state.get("team_name", "team")
    summary = state.get("team_summary", "")
    open_questions = state.get("team_open_questions", [])
    artifacts = state.get("team_artifacts", {})
    status = state.get("team_status", "completed")

    parts = [f"当前负责团队：{team_name}", f"状态：{status}", summary]
    if open_questions:
        parts.append("待补充信息：")
        parts.extend(f"- {question}" for question in open_questions)
    if artifacts:
        parts.append("建议产物：")
        parts.extend(f"- {name}: {value}" for name, value in artifacts.items())

    return {
        "final_response": "\n".join(part for part in parts if part),
        "messages": [AIMessage(content="\n".join(part for part in parts if part), name="finalize_node")],
    }
