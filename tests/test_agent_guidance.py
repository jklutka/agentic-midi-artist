"""Agent workflow files stay discoverable and aligned across supported tools."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SKILLS = (
    ROOT / ".claude" / "skills" / "compose-midi-art" / "SKILL.md",
    ROOT / ".agents" / "skills" / "compose-midi-art" / "SKILL.md",
)


def test_composition_skills_are_aligned() -> None:
    contents = [path.read_text(encoding="utf-8") for path in SKILLS]
    assert contents[0] == contents[1]

    skill = contents[0]
    assert skill.startswith("---\n")
    assert "\nname: compose-midi-art\n" in skill
    assert "description:" in skill
    assert "Use when the user wants" in skill


def test_composition_skill_references_resolve() -> None:
    for skill_path in SKILLS:
        skill = skill_path.read_text(encoding="utf-8")
        references = re.findall(r"\]\(([^)]+)\)", skill)
        resolved = {(skill_path.parent / reference).resolve() for reference in references}
        assert ROOT / "AGENTS.md" in resolved
        assert ROOT / "docs" / "COMPOSING.md" in resolved
        assert all(path.is_file() for path in resolved)
