from pathlib import Path

import pytest
from skill_adapter import build_skill_registry
from skill_adapter.exceptions import (
    SkillConflictError,
    SkillExecutionError,
    SkillNotFoundError,
    SkillPermissionError,
)
from skill_adapter.loader import SkillLoader
from skill_adapter.middleware import PermissionMiddleware, TimingMiddleware
from skill_adapter.registry import SkillRegistry


@pytest.fixture
def loaded_registry() -> SkillRegistry:
    loader = SkillLoader()
    runtimes = loader.load_directory(Path("tests/fixtures/skills/native"))
    registry = SkillRegistry(conflict_policy="error")
    registry.register_many(runtimes)
    return registry


def test_execute_success(loaded_registry: SkillRegistry) -> None:
    result = loaded_registry.execute("project-manager", {"text": "hello"}, context={})
    assert result.output["skill_name"] == "project-manager"
    assert result.status == "success"


def test_execute_missing_skill_raises(loaded_registry: SkillRegistry) -> None:
    with pytest.raises(SkillNotFoundError):
        loaded_registry.execute("missing", {"text": "hello"})


def test_duplicate_registration_raises() -> None:
    loader = SkillLoader()
    runtime = loader.load_skill(Path("tests/fixtures/skills/native/project-manager"))

    registry = SkillRegistry(conflict_policy="error")
    registry.register(runtime)
    with pytest.raises(SkillConflictError):
        registry.register(runtime)


def test_permission_middleware_blocks_skill(loaded_registry: SkillRegistry) -> None:
    loaded_registry.use(PermissionMiddleware())
    with pytest.raises(SkillPermissionError):
        loaded_registry.execute(
            "project-manager",
            {"text": "hello"},
            context={"allowed_skills": ["backend-engineer"]},
        )


def test_timing_middleware_adds_duration_and_logs(loaded_registry: SkillRegistry) -> None:
    loaded_registry.use(TimingMiddleware())
    context = {"logs": []}

    result = loaded_registry.execute("backend-engineer", {"text": "hello"}, context=context)

    assert result.duration_ms is not None
    assert result.metadata["duration_ms"] >= 0
    assert context["logs"]
    assert context["logs"][0].startswith("skill:backend-engineer:duration_ms:")


def test_handler_failure_wraps_error() -> None:
    def broken_handler(_input_data):
        raise RuntimeError("boom")

    registry = SkillRegistry()
    from skill_adapter.models import SkillRuntime

    registry.register(
        SkillRuntime(name="broken", description="broken", handler=broken_handler)
    )
    with pytest.raises(SkillExecutionError):
        registry.execute("broken", {"text": "x"})


def test_factory_builds_registry_with_single_call() -> None:
    registry = build_skill_registry("tests/fixtures/skills/native")

    result = registry.execute(
        "project-manager",
        {"text": "plan"},
        context={"allowed_skills": ["project-manager"], "logs": []},
    )
    assert result.output["skill_name"] == "project-manager"


def test_build_skills_prompt_returns_prompt_text() -> None:
    registry = build_skill_registry("tests/fixtures/skills/native")

    skills_prompt = registry.build_skills_prompt()

    assert skills_prompt.startswith("Available skills:")
    assert "- backend-engineer:" in skills_prompt
    assert "- project-manager:" in skills_prompt
