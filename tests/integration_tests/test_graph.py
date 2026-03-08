import os

import pytest
from langchain_core.messages import HumanMessage

from agent import graph

pytestmark = pytest.mark.anyio


async def test_agent_simple_passthrough() -> None:
    if os.getenv("RUN_LANGSMITH_INTEGRATION") != "1":
        pytest.skip("Set RUN_LANGSMITH_INTEGRATION=1 to enable integration test")
    inputs = {"messages": [HumanMessage(content="帮我设计一个相机租赁小程序")]}
    res = await graph.ainvoke(inputs)
    assert res is not None
