from pathlib import Path

import pytest

from skill_adapter.executors.tool_call import ToolCallExecutor
from skill_adapter.exceptions import SkillConflictError
from skill_adapter.factory import build_skill_registry
from skill_adapter.loader import SkillLoader
from skill_adapter.registry import SkillRegistry


def _write_skill(root: Path, name: str, description: str = "demo") -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# Body\n",
        encoding="utf-8",
    )
    return skill_dir


def test_conflict_policy_error_raises(tmp_path: Path) -> None:
    _write_skill(tmp_path, "sql-expert")
    spec = SkillLoader().load_skill(tmp_path / "sql-expert")
    registry = SkillRegistry(conflict_policy="error")
    registry.register(spec)

    with pytest.raises(SkillConflictError):
        registry.register(spec)


def test_conflict_policy_keep_existing_keeps_first(tmp_path: Path) -> None:
    _write_skill(tmp_path, "sql-expert", "first")
    first = SkillLoader().load_skill(tmp_path / "sql-expert")
    (tmp_path / "sql-expert" / "SKILL.md").write_text(
        "---\nname: sql-expert\ndescription: second\n---\n# Body\n", encoding="utf-8"
    )
    second = SkillLoader().load_skill(tmp_path / "sql-expert")

    registry = SkillRegistry(conflict_policy="keep_existing")
    registry.register(first)
    registry.register(second)

    assert registry.get("sql-expert").description == "first"


def test_tool_call_success_path(tmp_path: Path) -> None:
    _write_skill(tmp_path, "sql-expert")

    def sql_tool(payload: dict) -> dict:
        return {"ok": True, "payload": payload}

    registry = build_skill_registry(
        tmp_path,
        executors={
            "tool_call": ToolCallExecutor(
                lambda skill_name: sql_tool if skill_name == "sql-expert" else None
            )
        },
    )

    result = registry.execute_by_name(
        "sql-expert",
        {"sql": "select 1"},
        context={"allowed_skills": ["sql-expert"], "logs": []},
        mode="tool_call",
    )

    assert result.status == "success"
    assert result.output["ok"] is True
    assert result.error is None
    assert result.metadata["mode"] == "tool_call"


def test_tool_call_permission_denied(tmp_path: Path) -> None:
    _write_skill(tmp_path, "sql-expert")

    def sql_tool(payload: dict) -> dict:
        return {"ok": True, "payload": payload}

    registry = build_skill_registry(
        tmp_path,
        executors={"tool_call": ToolCallExecutor(lambda _: sql_tool)},
    )

    result = registry.execute_by_name(
        "sql-expert",
        {"sql": "select 1"},
        context={"allowed_skills": ["other"], "logs": []},
        mode="tool_call",
    )

    assert result.status == "error"
    assert result.error is not None
    assert result.error.code == "SKILL_PERMISSION_DENIED"


def test_tool_call_tool_failure_returns_structured_error(tmp_path: Path) -> None:
    _write_skill(tmp_path, "sql-expert")

    def bad_tool(_payload: dict) -> dict:
        raise RuntimeError("boom")

    registry = build_skill_registry(
        tmp_path,
        executors={"tool_call": ToolCallExecutor(lambda _: bad_tool)},
    )

    result = registry.execute_by_name(
        "sql-expert",
        {"sql": "select 1"},
        context={"allowed_skills": ["sql-expert"], "logs": []},
        mode="tool_call",
    )

    assert result.status == "error"
    assert result.error is not None
    assert result.error.code == "TOOL_EXECUTION_FAILED"
