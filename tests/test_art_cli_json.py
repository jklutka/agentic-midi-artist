"""--json output: every command emits one parseable object; human mode is stable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from midi_art.app.cli import main

PROJECT_FILE = str(Path(__file__).parent.parent / "projects" / "collapse.json")


def _run_json(capsys, argv: list[str]) -> tuple[int, dict]:
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_describe_json(capsys) -> None:
    code, payload = _run_json(capsys, ["describe", "--json"])
    assert code == 0
    assert payload["tool"] == "midi-art"
    assert "project_schema" in payload
    assert "wavelength_bars" in payload["generators"]["wave"]["params"]


def test_new_json(tmp_path: Path, capsys) -> None:
    project_path = tmp_path / "new.json"
    code, payload = _run_json(
        capsys,
        [
            "new", "New Piece", "--style", "mechanical_precision", "--seed", "12",
            "-o", str(project_path), "--json",
        ],
    )
    assert code == 0
    assert payload == {
        "ok": True,
        "file": str(project_path),
        "style": "mechanical_precision",
        "seed": 12,
        "scene_count": 5,
        "brief": None,
    }
    assert project_path.exists()


def test_new_json_error(capsys) -> None:
    code, payload = _run_json(
        capsys, ["new", "Broken", "--style", "not-a-style", "--json"]
    )
    assert code == 1
    assert payload["ok"] is False
    assert "Unknown style" in payload["error"]


def test_lint_json_clean(capsys) -> None:
    code, payload = _run_json(capsys, ["lint", PROJECT_FILE, "--json"])
    assert code == 0
    assert payload == {"ok": True, "issues": [], "error_count": 0, "warning_count": 0}


def test_lint_json_broken(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad.json"
    data = json.loads(Path(PROJECT_FILE).read_text(encoding="utf-8"))
    data["music"]["scale"] = "minr"
    bad.write_text(json.dumps(data), encoding="utf-8")
    code, payload = _run_json(capsys, ["lint", str(bad), "--json"])
    assert code == 1
    assert payload["ok"] is False
    assert payload["error_count"] == 1
    assert payload["issues"][0]["path"] == "music.scale"


def test_generate_json(tmp_path: Path, capsys) -> None:
    midi_path = tmp_path / "out.mid"
    code, payload = _run_json(
        capsys, ["generate", PROJECT_FILE, "-o", str(midi_path), "--json"]
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["report"]["total_notes"] > 0
    assert Path(payload["files"]["midi"]).exists()
    manifest = json.loads(Path(payload["files"]["manifest"]).read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 2
    assert len(manifest["project_sha256"]) == 64
    assert manifest["tool_version"]
    assert manifest["created_utc"]
    assert manifest["brief"] is None
    assert isinstance(manifest["issues"], list)
    # v1 keys survive unchanged
    assert manifest["project"] == "Collapse of the Machine"
    assert manifest["seed"] == 82217


def test_report_json(capsys) -> None:
    code, payload = _run_json(capsys, ["report", PROJECT_FILE, "--json"])
    assert code == 0
    assert payload["ok"] is True
    assert payload["report"]["total_notes"] > 0
    assert payload["profile"] == "zenith_high_density"


def test_preview_json(tmp_path: Path, capsys) -> None:
    out = tmp_path / "p.html"
    code, payload = _run_json(
        capsys, ["preview", PROJECT_FILE, "-o", str(out), "--json"]
    )
    assert code == 0
    assert payload["files"] == [str(out)]
    assert payload["seeds"] == [82217]


def test_error_becomes_json_object(capsys) -> None:
    code, payload = _run_json(capsys, ["report", "no-such-file.json", "--json"])
    assert code == 1
    assert payload["ok"] is False
    assert payload["error"]


def test_lint_error_aborts_generate_with_pointer(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad.json"
    data = json.loads(Path(PROJECT_FILE).read_text(encoding="utf-8"))
    data["scenes"][0]["transition_out"] = "fade"
    bad.write_text(json.dumps(data), encoding="utf-8")
    assert main(["generate", str(bad)]) == 1
    err = capsys.readouterr().err
    assert "lint" in err


@pytest.mark.parametrize("argv,expected", [
    (["report", PROJECT_FILE], "Notes:"),
    (["lint", PROJECT_FILE], "OK — no issues."),
])
def test_human_mode_unchanged(capsys, argv, expected) -> None:
    assert main(argv) == 0
    assert expected in capsys.readouterr().out
