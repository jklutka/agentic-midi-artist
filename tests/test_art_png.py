"""PNG preview and visual summary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from midi_art.analysis.metrics import analyze
from midi_art.analysis.summary import build_visual_summary, format_summary_text
from midi_art.app.cli import main
from midi_art.composition.composer import compose
from midi_art.domain.project import Project
from midi_art.preview import build_preview

PROJECT_FILE = Path(__file__).parent.parent / "projects" / "collapse.json"


@pytest.fixture(scope="module")
def performance():
    return compose(Project.load(PROJECT_FILE))


def test_render_png_smoke(tmp_path: Path, performance) -> None:
    pytest.importorskip("PIL")
    from midi_art.preview import render_png

    path = render_png(build_preview(performance), tmp_path / "preview.png", title="test")
    assert path.exists()
    assert path.stat().st_size > 10_000


def test_cli_preview_png_and_both(tmp_path: Path, capsys) -> None:
    pytest.importorskip("PIL")
    out = tmp_path / "p.png"
    assert main(["preview", str(PROJECT_FILE), "-o", str(out),
                 "--format", "png", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["files"] == [str(out)]
    assert out.exists()

    both = tmp_path / "q.html"
    assert main(["preview", str(PROJECT_FILE), "-o", str(both),
                 "--format", "both", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert str(both) in payload["files"]
    assert str(both.with_suffix(".png")) in payload["files"]


def test_cli_preview_png_multi_seed(tmp_path: Path, capsys) -> None:
    pytest.importorskip("PIL")
    out = tmp_path / "v.png"
    assert main(["preview", str(PROJECT_FILE), "-o", str(out), "--seeds", "1,2",
                 "--format", "png", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["files"]) == 2
    for file in payload["files"]:
        assert "-seed-" in file
        assert Path(file).exists()


def test_visual_summary_shape(performance) -> None:
    summary = build_visual_summary(performance, analyze(performance))
    assert [s["name"] for s in summary["scenes"]] == [
        "Order", "Hairline Cracks", "Fracture", "Collapse", "Aftermath"
    ]
    assert len(summary["density_arc"]) == 5
    assert max(summary["density_arc"]) == 1.0
    assert summary["peak_density"]["scene"] == "Collapse"
    assert summary["peak_polyphony"]["value"] > 0
    assert "→" in summary["register_evolution"]
    for scene in summary["scenes"]:
        assert scene["notes"] > 0
        assert scene["register"] is not None
        assert scene["intensity"] is not None


def test_visual_summary_finds_gaps() -> None:
    """A tiny project with one silent scene reports the gap with attribution."""
    data = json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    data["scenes"] = [
        data["scenes"][0],
        {"name": "Void", "duration_bars": 8,
         "intent": data["scenes"][0]["intent"], "layers": [],
         "transition_out": None, "automation": []},
    ]
    data["scenes"][0]["transition_out"] = None
    performance = compose(Project.from_dict(data))
    summary = build_visual_summary(performance, analyze(performance))
    assert any(gap["scene"] == "Void" for gap in summary["gaps"])


def test_summary_text_renders(performance) -> None:
    text = format_summary_text(build_visual_summary(performance, analyze(performance)))
    assert "Energy arc:" in text
    assert "Register arc:" in text
    assert "Collapse" in text


def test_report_json_includes_visual(capsys) -> None:
    assert main(["report", str(PROJECT_FILE), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "visual" in payload
    assert payload["visual"]["peak_density"]["scene"] == "Collapse"
