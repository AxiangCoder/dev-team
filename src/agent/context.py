from dataclasses import dataclass, field, fields
from typing_extensions import Annotated, TypedDict
import os


system_prompt = """
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


@dataclass(kw_only=True)
class Context:
    """Main context class for the memory graph system."""

    project_id: str
    """The ID of the user to remember in the conversation."""

    user_id: str

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="anthropic/claude-sonnet-4-5-20250929",
        metadata={
            "description": "The name of the language model to use for the agent. "
            "Should be in the form: provider/model-name."
        },
    )

    system_prompt: str = system_prompt

    def __post_init__(self):
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))