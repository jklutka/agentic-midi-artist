"""Tests for the preview model, SVG renderer, and preview CLI command."""

import json
from pathlib import Path

from midi_art.analysis.metrics import analyze
from midi_art.app.cli import main
from midi_art.composition.composer import compose
from midi_art.presets import build_style
from midi_art.preview import build_preview, render_html, render_svg


def make_performance(seed: int = 11):
    return compose(build_style("organic_growth", "Preview", seed))


def test_preview_data_matches_performance():
    performance = make_performance()
    data = build_preview(performance)

    assert data.total_notes == len(performance.notes)
    assert data.duration_beats == performance.duration_beats
    assert len(data.scenes) == len(performance.scene_spans)
    assert data.peak_polyphony == analyze(performance).peak_polyphony
    bars = performance.duration_beats / performance.project.music.beats_per_bar
    assert len(data.density_per_bar) == int(bars)
    assert sum(data.density_per_bar) == data.total_notes


def test_preview_sampling_caps_drawable_notes():
    performance = make_performance()
    data = build_preview(performance, max_notes=100)
    assert data.sampled
    assert len(data.notes) == 100
    assert data.total_notes == len(performance.notes)  # metrics stay exact


def test_intensity_points_follow_scene_intent():
    performance = make_performance()
    data = build_preview(performance)
    scene = performance.project.scenes[0]
    points = data.scenes[0].intensity_points
    assert points[0][1] == scene.intent.intensity_at(0.0)
    assert points[-1][1] == scene.intent.intensity_at(1.0)


def test_render_svg_and_html():
    data = build_preview(make_performance(), max_notes=500)
    svg = render_svg(data)
    assert svg.startswith("<svg")
    assert svg.count("<rect") > 100

    html_page = render_html("Title", [("seed 11", data, "report body", ["[INFO] note"])])
    assert "<!doctype html>" in html_page
    assert "report body" in html_page
    assert "[INFO] note" in html_page


def test_cli_preview_writes_html(tmp_path: Path):
    project_path = tmp_path / "p.json"
    main(["new", "Prev", "--style", "controlled_chaos", "-o", str(project_path)])
    out = tmp_path / "prev.html"
    assert main(["preview", str(project_path), "-o", str(out)]) == 0
    assert "<svg" in out.read_text(encoding="utf-8")


def test_cli_preview_variation_comparison(tmp_path: Path):
    project_path = tmp_path / "p.json"
    main(["new", "Prev", "--style", "mechanical_precision", "-o", str(project_path)])
    out = tmp_path / "compare.html"
    assert main(["preview", str(project_path), "--seeds", "1,2,3", "-o", str(out)]) == 0
    page = out.read_text(encoding="utf-8")
    for seed in (1, 2, 3):
        assert f"seed {seed}" in page
    assert page.count("<svg") == 3


def test_cli_preview_scene_only(tmp_path: Path):
    project_path = tmp_path / "p.json"
    main(["new", "Prev", "--style", "organic_growth", "-o", str(project_path)])
    project = json.loads(project_path.read_text(encoding="utf-8"))
    scene_name = project["scenes"][1]["name"]
    out = tmp_path / "scene.html"
    assert main(["preview", str(project_path), "--scene", scene_name, "-o", str(out)]) == 0
    assert scene_name in out.read_text(encoding="utf-8")
