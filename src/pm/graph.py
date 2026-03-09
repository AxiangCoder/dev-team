from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langchain_core.messages import AIMessage



from src.pm.context import Context
from src.pm.state import MessagesState
from src.pm.node.raw_story import raw_story_graph
from src.pm.node.output_node import output_node


async def call_raw_story_graph (state: MessagesState):
    output = await raw_story_graph.ainvoke({"user_input": "我想做一个相机租赁小程序"})
    return {
        **state,
        "messages": [
            *state.get("messages", []),
            AIMessage(content="finish")
        ]
    }

stateGraph = StateGraph(state_schema=MessagesState, context_schema=Context)
# stateGraph.add_node (call_raw_story_graph)
stateGraph.add_node (raw_story_graph)
stateGraph.add_edge("__start__", "raw_story_graph")
stateGraph.add_edge("raw_story_graph", "__end__")


# graph = (
#     stateGraph.compile(name="pm-agent")
# )

graph = raw_story_graph