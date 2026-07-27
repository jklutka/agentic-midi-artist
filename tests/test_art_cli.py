"""Tests for the midi-art CLI: new -> generate -> manifest round trip."""

import json
from pathlib import Path

from midi_art.app.cli import main


def test_cli_new_generate_roundtrip(tmp_path: Path, capsys):
    project_path = tmp_path / "demo.json"
    assert main(["new", "Demo Piece", "--style", "organic_growth", "--seed", "5",
                 "-o", str(project_path)]) == 0
    assert project_path.exists()

    midi_path = tmp_path / "demo.mid"
    assert main(["generate", str(project_path), "-o", str(midi_path)]) == 0
    assert midi_path.exists()

    manifest = json.loads(midi_path.with_suffix(".manifest.json").read_text())
    assert manifest["project"] == "Demo Piece"
    assert manifest["seed"] == 5
    assert manifest["report"]["total_notes"] > 0
    out = capsys.readouterr().out
    assert "Notes:" in out


def test_cli_scene_preview(tmp_path: Path):
    project_path = tmp_path / "demo.json"
    main(["new", "Demo", "--style", "controlled_chaos", "-o", str(project_path)])
    midi_path = tmp_path / "scene.mid"
    assert main(["generate", str(project_path), "--scene", "Fracture",
                 "-o", str(midi_path)]) == 0
    assert midi_path.exists()


def test_cli_seed_variation_changes_output(tmp_path: Path):
    project_path = tmp_path / "demo.json"
    main(["new", "Demo", "--style", "mechanical_precision", "-o", str(project_path)])
    a, b = tmp_path / "a.mid", tmp_path / "b.mid"
    main(["generate", str(project_path), "--seed", "1", "-o", str(a)])
    main(["generate", str(project_path), "--seed", "2", "-o", str(b)])
    assert a.read_bytes() != b.read_bytes()


def test_cli_listing_commands(capsys):
    assert main(["styles"]) == 0
    assert main(["generators"]) == 0
    assert main(["transitions"]) == 0
    out = capsys.readouterr().out
    assert "organic_growth" in out
    assert "chord_wall" in out
    assert "sudden_silence" in out


def test_cli_rejects_unknown_style(capsys):
    assert main(["new", "X", "--style", "nope"]) == 1
    assert "Unknown style" in capsys.readouterr().err
