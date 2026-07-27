"""MIDI file generation and Zenith-MIDI rendering integration."""

from .dense_song import (
    DENSE_SONG_PRESETS,
    DenseSongPreset,
    DenseSongSegment,
    create_dense_song,
    create_segmented_dense_song,
    dense_song_preset_options,
    get_dense_song_preset,
)
from .generator import create_chord_progression, create_midi, create_scale

__all__ = [
    "DENSE_SONG_PRESETS",
    "DenseSongSegment",
    "DenseSongPreset",
    "create_chord_progression",
    "create_dense_song",
    "create_segmented_dense_song",
    "create_midi",
    "create_scale",
    "dense_song_preset_options",
    "get_dense_song_preset",
]
