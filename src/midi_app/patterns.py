"""Patterns module: higher-level MIDI composition patterns."""

from pathlib import Path

import mido

from .generator import create_midi


def create_waterfall(
    output_path: str | Path,
    num_notes: int = 200,
    pitch_range: tuple[int, int] = (21, 108),
    tempo_bpm: int = 140,
    density: float = 1.0,
) -> Path:
    """Create a cascading waterfall of notes — visually impressive in Zenith.

    Args:
        output_path: Where to save the .mid file.
        num_notes: Total number of notes to generate.
        pitch_range: (low, high) MIDI note range.
        tempo_bpm: Tempo in beats per minute.
        density: Note density multiplier (higher = more overlapping notes).

    Returns:
        Path to the created MIDI file.
    """
    import random

    ticks_per_beat = 480
    tempo = mido.bpm2tempo(tempo_bpm)
    spacing = int(ticks_per_beat / (4 * density))

    notes = []
    low, high = pitch_range
    for i in range(num_notes):
        notes.append({
            "pitch": random.randint(low, high),
            "velocity": random.randint(60, 127),
            "start_tick": i * spacing,
            "duration_ticks": random.randint(ticks_per_beat // 4, ticks_per_beat * 2),
            "channel": 0,
        })

    return create_midi(notes, output_path, ticks_per_beat=ticks_per_beat, tempo=tempo)


def create_rainbow_spread(
    output_path: str | Path,
    num_waves: int = 8,
    notes_per_wave: int = 50,
    tempo_bpm: int = 160,
) -> Path:
    """Create spreading wave patterns across the keyboard — looks great with color mapping.

    Args:
        output_path: Where to save the .mid file.
        num_waves: Number of wave passes.
        notes_per_wave: Notes in each wave.
        tempo_bpm: Tempo in beats per minute.

    Returns:
        Path to the created MIDI file.
    """
    import math

    ticks_per_beat = 480
    tempo = mido.bpm2tempo(tempo_bpm)

    notes = []
    center = 64
    tick = 0
    spacing = ticks_per_beat // 8

    for wave in range(num_waves):
        direction = 1 if wave % 2 == 0 else -1
        for i in range(notes_per_wave):
            spread = int(30 * math.sin(i / notes_per_wave * math.pi))
            pitch = center + (direction * spread * i // notes_per_wave)
            pitch = max(21, min(108, pitch))

            notes.append({
                "pitch": pitch,
                "velocity": 100,
                "start_tick": tick,
                "duration_ticks": ticks_per_beat,
                "channel": wave % 16,
            })
            tick += spacing

    return create_midi(notes, output_path, ticks_per_beat=ticks_per_beat, tempo=tempo)


def create_spiral(
    output_path: str | Path,
    revolutions: int = 4,
    notes_per_revolution: int = 48,
    tempo_bpm: int = 180,
) -> Path:
    """Create a spiral pattern that expands outward from middle C.

    Args:
        output_path: Where to save the .mid file.
        revolutions: Number of spiral rotations.
        notes_per_revolution: Notes per full rotation.
        tempo_bpm: Tempo in beats per minute.

    Returns:
        Path to the created MIDI file.
    """
    import math

    ticks_per_beat = 480
    tempo = mido.bpm2tempo(tempo_bpm)
    spacing = ticks_per_beat // 6

    notes = []
    total_notes = revolutions * notes_per_revolution

    for i in range(total_notes):
        angle = (i / notes_per_revolution) * 2 * math.pi
        radius = (i / total_notes) * 40
        pitch = int(64 + radius * math.sin(angle))
        pitch = max(21, min(108, pitch))

        notes.append({
            "pitch": pitch,
            "velocity": int(80 + 40 * (i / total_notes)),
            "start_tick": i * spacing,
            "duration_ticks": ticks_per_beat // 2,
            "channel": (i // notes_per_revolution) % 16,
        })

    return create_midi(notes, output_path, ticks_per_beat=ticks_per_beat, tempo=tempo)
