"""Document lint: every check has a positive and a negative case."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from midi_art.analysis.lint import lint_document
from midi_art.analysis.validation import IssueLevel
from midi_art.domain.project import Project
from midi_art.presets import STYLES, build_style

PROJECT_FILE = Path(__file__).parent.parent / "projects" / "collapse.json"


@pytest.fixture()
def document() -> dict:
    return json.loads(PROJECT_FILE.read_text(encoding="utf-8"))


def _messages(issues, level=None):
    return [issue.message for issue in issues if level is None or issue.level is level]


def _paths(issues, level=None):
    return [issue.path for issue in issues if level is None or issue.level is level]


def test_committed_project_lints_clean(document) -> None:
    assert lint_document(document) == []


def test_all_style_presets_lint_clean() -> None:
    for style in STYLES:
        data = build_style(style, "Test", seed=1).to_dict()
        assert lint_document(data) == [], style


def test_non_object_document() -> None:
    issues = lint_document([1, 2, 3])
    assert issues[0].level is IssueLevel.ERROR


def test_missing_required_key_is_error(document) -> None:
    del document["name"]
    issues = lint_document(document)
    assert "name" in _paths(issues, IssueLevel.ERROR)


def test_unknown_key_warns_with_suggestion(document) -> None:
    document["scenes"][0]["intent"]["intensity_strat"] = 0.5
    issues = lint_document(document)
    warning = next(i for i in issues if "intensity_strat" in i.path)
    assert warning.level is IssueLevel.WARNING
    assert "intensity_start" in warning.message  # did-you-mean


def test_bad_enum_is_error_with_suggestion(document) -> None:
    document["music"]["scale"] = "minr"
    issues = lint_document(document)
    error = next(i for i in issues if i.path == "music.scale")
    assert error.level is IssueLevel.ERROR
    assert "minor" in error.message


def test_bad_transition_is_error(document) -> None:
    document["scenes"][0]["transition_out"] = "fade"
    issues = lint_document(document)
    assert "scenes[0].transition_out" in _paths(issues, IssueLevel.ERROR)


def test_out_of_range_value_warns(document) -> None:
    document["scenes"][0]["intent"]["intensity_start"] = 5.0
    issues = lint_document(document)
    warning = next(i for i in issues if i.path == "scenes[0].intent.intensity_start")
    assert warning.level is IssueLevel.WARNING


def test_unknown_generator_param_warns_with_suggestion(document) -> None:
    layer = document["scenes"][1]["layers"][2]
    assert layer["generator"]["type"] == "cloud"
    layer["generator"]["params"] = {"density_scal": 2.0}
    issues = lint_document(document)
    warning = next(i for i in issues if "density_scal" in i.path)
    assert warning.level is IssueLevel.WARNING
    assert "density_scale" in warning.message


def test_param_choices_warn(document) -> None:
    layer = document["scenes"][2]["layers"][3]
    assert layer["generator"]["type"] == "cascade"
    layer["generator"]["params"]["direction"] = "sideways"
    issues = lint_document(document)
    warning = next(i for i in issues if i.path.endswith("params.direction"))
    assert warning.level is IssueLevel.WARNING


def test_unknown_automation_target_warns(document) -> None:
    document["scenes"][0]["automation"] = [
        {"target": "volume", "start_value": 0.0, "end_value": 1.0}
    ]
    issues = lint_document(document)
    warning = next(i for i in issues if i.path == "scenes[0].automation[0].target")
    assert warning.level is IssueLevel.WARNING  # ignored, not fatal


def test_explicit_null_is_error(document) -> None:
    document["seed"] = None
    issues = lint_document(document)
    assert "seed" in _paths(issues, IssueLevel.ERROR)


def test_nullable_fields_accept_null(document) -> None:
    document["music"]["tempo_end"] = None
    document["scenes"][0]["transition_out"] = None
    assert lint_document(document) == []


def test_newer_format_version_is_error(document) -> None:
    document["format_version"] = 99
    issues = lint_document(document)
    assert "format_version" in _paths(issues, IssueLevel.ERROR)


def test_empty_scenes_warns(document) -> None:
    document["scenes"] = []
    issues = lint_document(document)
    assert "scenes" in _paths(issues, IssueLevel.WARNING)


def test_duplicate_scene_names_warn(document) -> None:
    document["scenes"][1]["name"] = document["scenes"][0]["name"]
    issues = lint_document(document)
    assert any("Duplicate scene name" in m for m in _messages(issues, IssueLevel.WARNING))


def test_layerless_scene_is_info(document) -> None:
    document["scenes"][0]["layers"] = []
    issues = lint_document(document)
    assert "scenes[0].layers" in _paths(issues, IssueLevel.INFO)


def test_pointless_tempo_ramp_is_info(document) -> None:
    document["music"]["tempo_end"] = document["music"]["tempo_start"]
    issues = lint_document(document)
    assert "music.tempo_end" in _paths(issues, IssueLevel.INFO)


def test_number_as_string_warns(document) -> None:
    document["scenes"][0]["intent"]["order"] = "0.9"
    issues = lint_document(document)
    warning = next(i for i in issues if i.path == "scenes[0].intent.order")
    assert warning.level is IssueLevel.WARNING


def test_issues_sorted_worst_first(document) -> None:
    document["music"]["scale"] = "minr"  # error
    document["scenes"][0]["intent"]["intensity_start"] = 5.0  # warning
    document["scenes"][0]["layers"] = []  # info
    issues = lint_document(document)
    levels = [issue.level for issue in issues]
    assert levels == sorted(
        levels, key=lambda lv: {IssueLevel.ERROR: 0, IssueLevel.WARNING: 1, IssueLevel.INFO: 2}[lv]
    )


def test_missing_required_key_raises_value_error_not_key_error(document) -> None:
    broken = copy.deepcopy(document)
    del broken["scenes"][0]["duration_bars"]
    with pytest.raises(ValueError, match="duration_bars"):
        Project.from_dict(broken)
