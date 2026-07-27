"""Tests for the MIDI generator module."""

from pathlib import Path

import mido

from midi_app.generator import create_chord_progression, create_midi, create_scale


def test_create_midi_produces_file(tmp_path: Path):
    notes = [
        {"pitch": 60, "velocity": 100, "start_tick": 0, "duration_ticks": 480, "channel": 0},
        {"pitch": 64, "velocity": 100, "start_tick": 480, "duration_ticks": 480, "channel": 0},
    ]
    output = tmp_path / "test.mid"
    result = create_midi(notes, output)

    assert result.exists()
    mid = mido.MidiFile(str(result))
    assert len(mid.tracks) == 1


def test_create_scale_major(tmp_path: Path):
    output = tmp_path / "scale.mid"
    result = create_scale(output, root=60, scale_type="major")

    assert result.exists()
    mid = mido.MidiFile(str(result))
    # Major scale has 8 notes (including octave) = 16 note events (on + off)
    note_msgs = [m for m in mid.tracks[0] if m.type in ("note_on", "note_off")]
    assert len(note_msgs) == 16


def test_create_chord_progression(tmp_path: Path):
    chords = [[60, 64, 67], [65, 69, 72]]
    output = tmp_path / "chords.mid"
    result = create_chord_progression(output, chords=chords)

    assert result.exists()
    mid = mido.MidiFile(str(result))
    note_msgs = [m for m in mid.tracks[0] if m.type in ("note_on", "note_off")]
    # 2 chords × 3 notes × 2 events = 12
    assert len(note_msgs) == 12


def test_create_midi_supports_start_messages(tmp_path: Path):
    notes = [{"pitch": 60, "velocity": 100, "start_tick": 0, "duration_ticks": 480, "channel": 0}]
    output = tmp_path / "program.mid"
    result = create_midi(
        notes,
        output,
        start_messages=[mido.Message("program_change", channel=0, program=12)],
    )

    mid = mido.MidiFile(str(result))
    assert mid.tracks[0][1].type == "program_change"
    assert mid.tracks[0][1].program == 12


def test_create_midi_supports_timed_messages(tmp_path: Path):
    notes = [{"pitch": 60, "velocity": 100, "start_tick": 0, "duration_ticks": 960, "channel": 0}]
    output = tmp_path / "tempo_change.mid"
    result = create_midi(
        notes,
        output,
        timed_messages=[(480, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(180)))],
    )

    mid = mido.MidiFile(str(result))
    tempo_messages = [message for message in mid.tracks[0] if message.type == "set_tempo"]

    assert len(tempo_messages) == 2
    assert tempo_messages[1].time == 480
