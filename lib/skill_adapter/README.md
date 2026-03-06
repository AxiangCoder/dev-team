# skill_adapter

A reusable skill adapter library for LangGraph workflows.

## Features

- Load native skill directories that contain `SKILL.md`
- Build a ready-to-use `SkillRegistry` from one directory
- Support middleware for permission checks and timing
- Return typed execution results for observability

## Directory convention

```text
skills/
  backend-engineer/
    SKILL.md
    scripts/        # optional
    assets/         # optional
    references/     # optional
```

## Quick usage (one step)

```python
from skill_adapter import build_skill_registry

registry = build_skill_registry("./src/agent/skills")

result = registry.execute(
    "backend-engineer",
    {"task": "Design order API"},
    context={"allowed_skills": ["backend-engineer"], "logs": []},
)
print(result.output)
```

`result.output` is an instruction packet with `skill_name`, `instructions` (from `SKILL.md`) and your `input`.
