from pathlib import Path

import pytest

from skill_adapter.exceptions import SkillDefinitionError
from skill_adapter.loader import SkillLoader


def test_load_skill_parses_frontmatter_and_body(tmp_path: Path) -> None:
    skill_dir = tmp_path / "sql-expert"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: sql-expert\n"
        "description: SQL helper\n"
        "version: 0.1.0\n"
        "---\n"
        "\n"
        "# SQL Expert\n"
        "Use read-only SQL.\n",
        encoding="utf-8",
    )

    spec = SkillLoader().load_skill(skill_dir)

    assert spec.name == "sql-expert"
    assert spec.description == "SQL helper"
    assert spec.version == "0.1.0"
    assert spec.body.startswith("# SQL Expert")
    assert spec.metadata["skill_markdown_path"].endswith("SKILL.md")


def test_load_directory_rejects_missing_skill_markdown(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    root.mkdir()
    (root / "empty-dir").mkdir()

    with pytest.raises(SkillDefinitionError):
        SkillLoader().load_directory(root)
