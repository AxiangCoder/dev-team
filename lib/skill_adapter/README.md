# skill_adapter

`skill_adapter` is a tool-first runtime library for Claude Skill-style `SKILL.md` definitions.

Current milestone supports:

- Skill loading from `SKILL.md`
- Skill registration and conflict handling
- `tool_call` execution mode
- Middleware pipeline (validation, permission, timing)
- LangChain and LangGraph helper adapters

Current milestone does **not** support:

- Script execution from `scripts/`
- Sandboxed process runtime

## Installation

Copy this library into your project or install it as your internal package.

If you want LangChain adapter APIs, install:

```bash
pip install langchain-core
```

## Skill Directory Convention

```text
skills/
  sql-expert/
    SKILL.md
  order-analyst/
    SKILL.md
```

Minimal `SKILL.md` example:

```md
---
name: sql-expert
description: Query order analytics
version: 0.1.0
---
# SQL Expert

Use read-only SQL for analytics queries.
```

## Quick Start (Tool-Only)

```python
from langchain_core.tools import tool

from skill_adapter import (
    PermissionMiddleware,
    ToolCallExecutor,
    ValidationMiddleware,
    build_skill_registry,
)


@tool
def sql_tool(payload: dict) -> dict:
    return {"rows": [], "payload": payload}


tool_map = {"sql-expert": sql_tool}

registry = build_skill_registry(
    "./skills",
    executors={
        "tool_call": ToolCallExecutor(
            tool_resolver=lambda skill_name: tool_map.get(skill_name)
        )
    },
    middleware=[ValidationMiddleware(), PermissionMiddleware()],
)

result = registry.execute_by_name(
    "sql-expert",
    {"sql": "select * from orders limit 10"},
    context={"allowed_skills": ["sql-expert"], "logs": []},
    mode="tool_call",
)

if result.status == "success":
    print(result.output)
else:
    print(result.error.code, result.error.message)
```

## Core API

### Loader

- `SkillLoader.load_skill(path) -> SkillSpec`
- `SkillLoader.load_directory(path) -> list[SkillSpec]`

### Registry

- `SkillRegistry(conflict_policy="error")`
- `register(spec)`
- `register_many(specs)`
- `get(skill_name)`
- `list()`
- `unregister(skill_name)`
- `add_executor(mode, executor)`
- `use(middleware)`
- `execute(request_or_skill_name, input_data=None, context=None, mode="tool_call")`
- `execute_by_name(skill_name, input_data, context=None, mode="tool_call")`

### Models

- `SkillSpec`
- `SkillExecutionRequest`
- `SkillExecutionResult`
- `SkillError`

### Executors

- `ToolCallExecutor(tool_resolver=...)`

### Middleware

- `ValidationMiddleware`
- `PermissionMiddleware`
- `TimingMiddleware`

### Factory

- `build_skill_registry(...)`
- `build_registry(...)` (alias)

### Adapters

- `to_langchain_tool(registry, skill_name, mode="tool_call")`
- `build_skills_prompt(registry, title="Available skills:")`
- `execute_skill(registry, skill_name=..., input_data=..., context=..., mode="tool_call")`

## Conflict Policy

`SkillRegistry(conflict_policy=...)` supports:

- `"error"`: raise on duplicate names
- `"override"`: latest wins
- `"keep_existing"`: ignore duplicates

## Execution Contract

All execution modes should return `SkillExecutionResult`:

```python
SkillExecutionResult(
    skill_name="sql-expert",
    status="success" | "error",
    output=...,
    error=SkillError(code="...", message="...", details={...}) | None,
    metadata={...},
)
```

## LangChain Adapter Example

```python
from skill_adapter import to_langchain_tool

skill_tool = to_langchain_tool(registry, "sql-expert", mode="tool_call")
```

This exposes one registered skill as a LangChain tool. The wrapped tool internally calls `registry.execute_by_name(...)`.

## LangGraph Node Example

```python
from skill_adapter import execute_skill


def execute_skill_node(state):
    result = execute_skill(
        registry,
        skill_name=state["chosen_skill"],
        input_data={"query": state["user_query"]},
        context={"allowed_skills": [state["chosen_skill"]], "logs": []},
        mode="tool_call",
    )
    return {"skill_result": result}
```

## Migration Notes from Older Versions

- Loader now returns `SkillSpec` (not runtime handlers).
- Skill execution is now executor-driven (`ToolCallExecutor`).
- Prefer `execute_by_name(...)` or request-based `execute(...)`.
- `mode="tool_call"` is the active production path.

## Roadmap

- Keep tool-only runtime stable
- Add richer schema validation
- Add async tool execution
- Add script runner in a later phase
