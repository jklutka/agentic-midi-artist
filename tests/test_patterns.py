"""Tests for the patterns module."""

from pathlib import Path

import mido

from midi_app.patterns import create_rainbow_spread, create_spiral, create_waterfall


def test_waterfall(tmp_path: Path):
    output = tmp_path / "waterfall.mid"
    result = create_waterfall(output, num_notes=50)

    assert result.exists()
    mid = mido.MidiFile(str(result))
    note_msgs = [m for m in mid.tracks[0] if m.type == "note_on"]
    assert len(note_msgs) == 50


def test_rainbow_spread(tmp_path: Path):
    output = tmp_path / "rainbow.mid"
    result = create_rainbow_spread(output, num_waves=2, notes_per_wave=10)

    assert result.exists()
    mid = mido.MidiFile(str(result))
    note_msgs = [m for m in mid.tracks[0] if m.type == "note_on"]
    assert len(note_msgs) == 20


def test_spiral(tmp_path: Path):
    output = tmp_path / "spiral.mid"
    result = create_spiral(output, revolutions=2, notes_per_revolution=12)

    assert result.exists()
    mid = mido.MidiFile(str(result))
    note_msgs = [m for m in mid.tracks[0] if m.type == "note_on"]
    assert len(note_msgs) == 24
