"""Creative brief: persistence, scaffolding, linting, and manifest linkage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from midi_art.analysis.lint import lint_brief_document, lint_document
from midi_art.analysis.validation import IssueLevel
from midi_art.app.cli import main
from midi_art.domain.brief import CreativeBrief, is_brief_document
from midi_art.domain.project import Project
from midi_art.presets import scaffold_from_brief

FULL_BRIEF = CreativeBrief(
    title="Glass Rain",
    logline="A storm builds until the sky itself shatters.",
    mood_arc=("hush", "gathering", "shatter", "afterglow"),
    energy_shape="slow build, cliff-edge drop, long decay",
    duration_seconds=180.0,
    tempo_feel="relentless ~150",
    imagery=("rain on glass", "collapsing tower"),
    palette=("ember", "ash"),
    must_have_moments=("total silence right before the climax",),
    avoid=("cheerful major-key brightness",),
    style_hint="controlled_chaos",
    notes="finale should feel physical",
)


def test_brief_round_trip(tmp_path: Path) -> None:
    path = FULL_BRIEF.save(tmp_path / "glass.brief.json")
    assert CreativeBrief.load(path) == FULL_BRIEF
    assert CreativeBrief.from_dict(FULL_BRIEF.to_dict()) == FULL_BRIEF


def test_brief_detection() -> None:
    assert is_brief_document(FULL_BRIEF.to_dict())
    assert not is_brief_document(Project(name="x").to_dict())


def test_brief_missing_title_raises_value_error() -> None:
    with pytest.raises(ValueError, match="title"):
        CreativeBrief.from_dict({"brief_format_version": 1})


def test_brief_newer_version_rejected(tmp_path: Path) -> None:
    path = tmp_path / "b.brief.json"
    data = FULL_BRIEF.to_dict()
    data["brief_format_version"] = 99
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="newer"):
        CreativeBrief.load(path)


def test_full_brief_lints_clean() -> None:
    assert lint_brief_document(FULL_BRIEF.to_dict()) == []


def test_brief_lint_flags_unknown_key_and_bad_style() -> None:
    data = FULL_BRIEF.to_dict()
    data["mood_ark"] = data.pop("mood_arc")
    data["style_hint"] = "chaos"
    issues = lint_brief_document(data)
    assert any("mood_ark" in i.path and "mood_arc" in i.message for i in issues)
    hint = next(i for i in issues if i.path == "style_hint")
    assert hint.level is IssueLevel.WARNING
    assert "controlled_chaos" in hint.message


def test_scaffold_uses_style_hint_and_links_brief() -> None:
    project = scaffold_from_brief(FULL_BRIEF, seed=9, brief_file="projects/g.brief.json")
    assert project.name == "Glass Rain"
    assert project.seed == 9
    assert project.brief_file == "projects/g.brief.json"
    assert project.artistic_direction.theme == FULL_BRIEF.logline
    assert project.artistic_direction.mood_start == "hush"
    assert project.artistic_direction.mood_middle == "gathering, shatter"
    assert project.artistic_direction.mood_end == "afterglow"
    assert project.artistic_direction.visual_focus == FULL_BRIEF.imagery
    # controlled_chaos style skeleton
    assert project.export_profile == "zenith_high_density"


def test_scaffold_duration_math() -> None:
    """180s at controlled_chaos's average tempo lands within a bar of target."""
    project = scaffold_from_brief(FULL_BRIEF, seed=1)
    avg_tempo = (project.music.tempo_start + project.music.tempo_end) / 2
    seconds = project.duration_beats * 60.0 / avg_tempo
    bar_seconds = project.music.beats_per_bar * 60.0 / avg_tempo
    assert abs(seconds - 180.0) <= 2 * bar_seconds


def test_scaffold_falls_back_on_unknown_style() -> None:
    brief = CreativeBrief(title="X", style_hint="not_a_style")
    project = scaffold_from_brief(brief, seed=1)
    assert project.artistic_direction.mood_start == "dormant"  # organic_growth default


def test_scaffold_output_lints_clean_and_round_trips() -> None:
    project = scaffold_from_brief(FULL_BRIEF, seed=3, brief_file="b.brief.json")
    data = project.to_dict()
    assert lint_document(data) == []
    assert Project.from_dict(data) == project


def test_cli_new_from_brief_and_manifest_link(tmp_path: Path, capsys) -> None:
    brief_path = tmp_path / "glass.brief.json"
    FULL_BRIEF.save(brief_path)
    project_path = tmp_path / "glass.json"
    assert main(["new", "Glass Rain", "--brief", str(brief_path),
                 "-o", str(project_path)]) == 0
    out = capsys.readouterr().out
    assert "controlled_chaos" in out
    assert str(brief_path) in out

    midi_path = tmp_path / "glass.mid"
    assert main(["generate", str(project_path), "-o", str(midi_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    manifest = json.loads(Path(payload["files"]["manifest"]).read_text(encoding="utf-8"))
    assert manifest["brief"]["file"] == str(brief_path)
    assert len(manifest["brief"]["sha256"]) == 64


def test_cli_new_from_brief_json(tmp_path: Path, capsys) -> None:
    brief_path = tmp_path / "glass.brief.json"
    FULL_BRIEF.save(brief_path)
    project_path = tmp_path / "glass.json"

    assert main([
        "new", "Glass Rain", "--brief", str(brief_path),
        "-o", str(project_path), "--json",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "file": str(project_path),
        "style": "controlled_chaos",
        "seed": 4207,
        "scene_count": 5,
        "brief": str(brief_path),
    }
    assert Project.load(project_path).brief_file == str(brief_path)


def test_cli_lint_dispatches_to_brief(tmp_path: Path, capsys) -> None:
    brief_path = tmp_path / "b.brief.json"
    FULL_BRIEF.save(brief_path)
    assert main(["lint", str(brief_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"ok": True, "issues": [], "error_count": 0, "warning_count": 0}
