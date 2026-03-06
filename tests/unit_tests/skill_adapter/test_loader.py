from pathlib import Path

import pytest
from skill_adapter.exceptions import SkillDefinitionError
from skill_adapter.loader import SkillLoader


def test_load_directory_success() -> None:
    loader = SkillLoader()
    runtimes = loader.load_directory(Path("tests/fixtures/skills/native"))

    names = sorted(runtime.name for runtime in runtimes)
    assert names == ["backend-engineer", "project-manager"]


def test_load_directory_without_skill_markdown_raises() -> None:
    loader = SkillLoader()
    with pytest.raises(SkillDefinitionError):
        loader.load_directory(Path("tests/fixtures/skills/manifests"))


def test_runtime_handler_returns_instruction_packet() -> None:
    loader = SkillLoader()
    runtime = loader.load_skill(Path("tests/fixtures/skills/native/project-manager"))

    output = runtime.handler({"query": "plan q2"})
    assert output["skill_name"] == "project-manager"
    assert "Create milestones" in output["instructions"]
    assert output["input"] == {"query": "plan q2"}
