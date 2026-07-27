"""Tests for the dense MIDI song generator."""

from pathlib import Path

import mido

from midi_app.dense_song import (
    DenseSongSegment,
    create_dense_song,
    create_segmented_dense_song,
    dense_song_preset_options,
    get_dense_song_preset,
)


def test_dense_song_is_deterministic_with_seed(tmp_path: Path):
    first = tmp_path / "dense_a.mid"
    second = tmp_path / "dense_b.mid"

    out_a = create_dense_song(first, seed=42, bars=8, density=0.8)
    out_b = create_dense_song(second, seed=42, bars=8, density=0.8)

    assert out_a.read_bytes() == out_b.read_bytes()


def test_dense_song_has_structured_density(tmp_path: Path):
    output = tmp_path / "dense.mid"
    result = create_dense_song(output, seed=7, bars=8, density=0.9)

    mid = mido.MidiFile(str(result))
    note_on_messages = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
    pitch_set = {msg.note for msg in note_on_messages}

    assert len(note_on_messages) >= 24
    assert len(pitch_set) >= 6


def test_dense_song_extreme_density_adds_more_notes(tmp_path: Path):
    moderate = tmp_path / "moderate.mid"
    extreme = tmp_path / "extreme.mid"

    moderate_result = create_dense_song(moderate, seed=9, bars=4, density=0.9)
    extreme_result = create_dense_song(extreme, seed=9, bars=4, density=15.0)

    moderate_mid = mido.MidiFile(str(moderate_result))
    extreme_mid = mido.MidiFile(str(extreme_result))

    moderate_notes = [msg for msg in moderate_mid.tracks[0] if msg.type == "note_on"]
    extreme_notes = [msg for msg in extreme_mid.tracks[0] if msg.type == "note_on"]

    assert len(extreme_notes) > len(moderate_notes)


def test_channel_color_storm_uses_many_channels(tmp_path: Path):
    output = tmp_path / "storm.mid"
    result = create_dense_song(output, seed=3, bars=4, density=1.2, preset="channel_color_storm")

    mid = mido.MidiFile(str(result))
    channels = {msg.channel for msg in mid.tracks[0] if msg.type == "note_on"}

    assert len(channels) >= 8


def test_preset_registry_exposes_recommendations():
    presets = dense_song_preset_options()
    preset = get_dense_song_preset("black_midi_wall")

    assert len(presets) == 5
    assert preset.channel_count >= 4
    assert "MidiTrail" in preset.zenith_tip


def test_ultra_dense_preset_uses_all_channels(tmp_path: Path):
    output = tmp_path / "ultra.mid"
    result = create_dense_song(output, seed=11, bars=4, density=4.0, preset="ultra_dense")

    mid = mido.MidiFile(str(result))
    channels = {msg.channel for msg in mid.tracks[0] if msg.type == "note_on"}

    assert len(channels) == 16


def test_hypnotic_wave_preset_uses_all_channels_and_many_notes(tmp_path: Path):
    output = tmp_path / "wave.mid"
    result = create_dense_song(output, seed=13, bars=4, density=5.0, preset="hypnotic_wave")

    mid = mido.MidiFile(str(result))
    note_on_messages = [msg for msg in mid.tracks[0] if msg.type == "note_on"]
    channels = {msg.channel for msg in note_on_messages}

    assert len(note_on_messages) > 120
    assert len(channels) == 16


def test_segmented_dense_song_writes_tempo_changes(tmp_path: Path):
    output = tmp_path / "segmented.mid"
    result = create_segmented_dense_song(
        output,
        [
            DenseSongSegment(bars=2, preset="dense_but_musical", density=0.8, tempo_bpm=120),
            DenseSongSegment(bars=2, preset="hypnotic_wave", density=4.0, tempo_bpm=168),
        ],
        seed=21,
    )

    mid = mido.MidiFile(str(result))
    tempo_ticks = []
    current_tick = 0
    for msg in mid.tracks[0]:
        current_tick += msg.time
        if msg.type == "set_tempo":
            tempo_ticks.append(current_tick)
    note_on_messages = [msg for msg in mid.tracks[0] if msg.type == "note_on"]

    assert len(tempo_ticks) == 2
    assert tempo_ticks[1] == 2 * 4 * 480
    assert len(note_on_messages) > 40


def test_single_segment_matches_dense_song_api(tmp_path: Path):
    dense = tmp_path / "dense.mid"
    segmented = tmp_path / "segmented_single.mid"

    dense_result = create_dense_song(dense, bars=4, density=2.0, seed=5, preset="hypnotic_wave")
    segmented_result = create_segmented_dense_song(
        segmented,
        [DenseSongSegment(bars=4, density=2.0, preset="hypnotic_wave")],
        seed=5,
    )

    assert dense_result.read_bytes() == segmented_result.read_bytes()
