"""Tests for the export layer: writer policies, profiles, analysis, validation."""

from pathlib import Path

import mido
import pytest

from midi_art.analysis.metrics import analyze, beats_to_seconds
from midi_art.analysis.validation import IssueLevel, validate
from midi_art.composition.composer import compose
from midi_art.domain.note_event import NoteEvent
from midi_art.export.midi_writer import ExportLimitError, write_midi
from midi_art.export.zenith_profile import get_profile
from midi_art.presets import build_style


def test_write_midi_produces_playable_file(tmp_path: Path):
    performance = compose(build_style("organic_growth", "Export", 11))
    path = write_midi(
        performance.notes,
        tmp_path / "export.mid",
        performance.settings,
        tempo_events=performance.tempo_events,
    )
    mid = mido.MidiFile(str(path))
    ons = [m for m in mid.tracks[0] if m.type == "note_on"]
    offs = [m for m in mid.tracks[0] if m.type == "note_off"]
    tempos = [m for m in mid.tracks[0] if m.type == "set_tempo"]
    assert len(ons) == len(offs)
    assert len(ons) <= len(performance.notes)  # overlap resolution may drop duplicates
    assert len(tempos) == len(performance.tempo_events)


def test_export_is_byte_deterministic(tmp_path: Path):
    for name in ("a.mid", "b.mid"):
        performance = compose(build_style("mechanical_precision", "Bytes", 9))
        write_midi(performance.notes, tmp_path / name, performance.settings,
                   tempo_events=performance.tempo_events)
    assert (tmp_path / "a.mid").read_bytes() == (tmp_path / "b.mid").read_bytes()


def test_min_duration_is_enforced(tmp_path: Path):
    settings = get_profile("zenith_performance_safe")
    notes = [NoteEvent(pitch=60, start=0.0, duration=0.001, velocity=100)]
    path = write_midi(notes, tmp_path / "short.mid", settings)
    mid = mido.MidiFile(str(path))
    off = next(m for m in mid.tracks[0] if m.type == "note_off")
    assert off.time >= round(settings.min_note_duration_beats * 480)


def test_same_pitch_overlaps_are_truncated(tmp_path: Path):
    settings = get_profile("zenith_standard")
    notes = [
        NoteEvent(pitch=60, start=0.0, duration=4.0, velocity=100),
        NoteEvent(pitch=60, start=1.0, duration=1.0, velocity=100),
    ]
    path = write_midi(notes, tmp_path / "overlap.mid", settings)
    mid = mido.MidiFile(str(path))
    active = 0
    for message in mid.tracks[0]:
        if message.type == "note_on":
            active += 1
            assert active <= 1, "same pitch struck while still sounding"
        elif message.type == "note_off":
            active -= 1


def test_note_cap_raises(tmp_path: Path):
    settings = get_profile("zenith_performance_safe")
    notes = [
        NoteEvent(pitch=60, start=i * 0.01, duration=0.1, velocity=90)
        for i in range(settings.max_total_notes + 1)
    ]
    with pytest.raises(ExportLimitError):
        write_midi(notes, tmp_path / "cap.mid", settings)


def test_beats_to_seconds_with_tempo_change():
    tempo = [(0.0, 120.0), (4.0, 240.0)]
    assert beats_to_seconds(4.0, tempo) == pytest.approx(2.0)
    assert beats_to_seconds(8.0, tempo) == pytest.approx(3.0)


def test_analysis_report_and_validation():
    performance = compose(build_style("controlled_chaos", "Report", 21))
    report = analyze(performance)
    assert report.total_notes == len(performance.notes)
    assert report.duration_seconds > 0
    assert report.peak_polyphony >= 1
    assert 21 <= report.pitch_min <= report.pitch_max <= 108
    assert set(report.notes_by_scene) == {span.name for span in performance.scene_spans}

    issues = validate(performance, report)
    assert not [issue for issue in issues if issue.level is IssueLevel.ERROR]
