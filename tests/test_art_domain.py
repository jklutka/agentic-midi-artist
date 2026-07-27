"""Tests for the midi_art domain model: automation, note events, persistence."""

from pathlib import Path

from midi_art.domain.automation import AutomationCurve, CurveType, resolve, shape
from midi_art.domain.note_event import NoteEvent, NoteRole
from midi_art.domain.scene import SceneIntent
from midi_art.presets import build_style


def test_curve_shapes_hit_endpoints():
    for curve in CurveType:
        assert shape(0.0, curve) == 0.0
        assert abs(shape(1.0, curve) - 1.0) < 1e-9


def test_automation_curve_interpolates():
    curve = AutomationCurve("density", 0.0, 10.0, CurveType.LINEAR, 0.0, 8.0)
    assert curve.value_at(0.0) == 0.0
    assert curve.value_at(4.0) == 5.0
    assert curve.value_at(8.0) == 10.0
    assert curve.value_at(100.0) == 10.0


def test_automation_resolve_later_curves_win():
    curves = [
        AutomationCurve("intensity", 0.0, 1.0, CurveType.LINEAR, 0.0, 10.0),
        AutomationCurve("intensity", 0.5, 0.5, CurveType.LINEAR, 0.0, 10.0),
    ]
    assert resolve(curves, "intensity", 5.0, 0.0) == 0.5
    assert resolve(curves, "other", 5.0, 0.7) == 0.7


def test_note_event_clamps_to_midi_ranges():
    note = NoteEvent(pitch=200, start=0.0, duration=-1.0, velocity=300).clamped()
    assert note.pitch == 127
    assert note.velocity == 127
    assert note.duration > 0


def test_scene_intent_register_expands():
    intent = SceneIntent(register_center=64, register_span_start=12, register_span_end=48)
    low0, high0 = intent.register_at(0.0)
    low1, high1 = intent.register_at(1.0)
    assert (high1 - low1) > (high0 - low0)
    assert low1 >= 21 and high1 <= 108


def test_project_round_trips_through_json(tmp_path: Path):
    project = build_style("controlled_chaos", "Round Trip", 99)
    path = project.save(tmp_path / "proj.json")
    loaded = type(project).load(path)
    assert loaded == project


def test_note_role_values_are_stable():
    assert NoteRole("visual_effect") is NoteRole.VISUAL_EFFECT
