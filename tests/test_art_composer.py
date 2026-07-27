"""Tests for the composer: determinism, scenes, transitions, allocation."""

import pytest

from midi_art.composition.composer import compose
from midi_art.presets import STYLES, build_style


def test_compose_is_deterministic():
    a = compose(build_style("organic_growth", "Det", 42))
    b = compose(build_style("organic_growth", "Det", 42))
    assert a.notes == b.notes
    assert a.tempo_events == b.tempo_events


def test_different_seeds_differ():
    a = compose(build_style("organic_growth", "Det", 1))
    b = compose(build_style("organic_growth", "Det", 2))
    assert a.notes != b.notes


@pytest.mark.parametrize("style", sorted(STYLES))
def test_all_styles_compose(style: str):
    performance = compose(build_style(style, "Full", 7))
    assert len(performance.notes) > 500
    assert performance.duration_beats > 0
    assert not performance.warnings
    channels = {note.channel for note in performance.notes}
    assert channels <= set(range(16))
    for note in performance.notes:
        assert note.start < performance.duration_beats + 8  # transitions may spill slightly


def test_scene_preview_composes_only_that_scene():
    project = build_style("controlled_chaos", "Preview", 3)
    scene = project.scenes[2]
    performance = compose(project, scene_name=scene.name)
    assert len(performance.scene_spans) == 1
    expected = scene.duration_bars * project.music.beats_per_bar
    assert performance.duration_beats == expected
    assert all(note.start < expected + 1e-6 for note in performance.notes)


def test_unknown_scene_raises():
    project = build_style("organic_growth", "X", 1)
    with pytest.raises(ValueError, match="No scene named"):
        compose(project, scene_name="Nope")


def test_tempo_ramp_spans_scenes():
    performance = compose(build_style("controlled_chaos", "Tempo", 1))
    bpms = [bpm for _, bpm in performance.tempo_events]
    assert len(bpms) == 5
    assert bpms[0] == performance.project.music.tempo_start
    assert bpms == sorted(bpms)  # tempo_end > tempo_start in this style


def test_transition_notes_use_reserved_channel():
    performance = compose(build_style("mechanical_precision", "Trans", 5))
    transition_notes = [note for note in performance.notes if note.layer_id == ""]
    assert transition_notes, "expected transition-generated notes"
    assert {note.channel for note in transition_notes} == {15}
