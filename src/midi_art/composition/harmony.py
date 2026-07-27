"""Harmony helpers: scales, chords, and pitch math shared by all generators."""

from __future__ import annotations

NOTE_NAMES: dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}

SCALES: dict[str, list[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
    "chromatic": list(range(12)),
}

PROGRESSIONS: dict[str, list[int]] = {
    "major": [0, 4, 5, 3],
    "minor": [0, 5, 3, 4],
}
DEFAULT_PROGRESSION = [0, 5, 3, 4]


def root_pitch(root: str, octave: int) -> int:
    """MIDI pitch for a note name and octave (C4 = 60)."""
    try:
        semitone = NOTE_NAMES[root]
    except KeyError as exc:
        allowed = ", ".join(sorted(NOTE_NAMES))
        raise ValueError(f"Unknown root {root!r}. Use one of: {allowed}") from exc
    return semitone + 12 * (octave + 1)


def scale_intervals(scale: str) -> list[int]:
    try:
        return SCALES[scale]
    except KeyError as exc:
        allowed = ", ".join(sorted(SCALES))
        raise ValueError(f"Unknown scale {scale!r}. Use one of: {allowed}") from exc


def progression_for(scale: str) -> list[int]:
    return PROGRESSIONS.get(scale, DEFAULT_PROGRESSION)


def degree_to_pitch(root: int, scale: str, degree: int) -> int:
    intervals = scale_intervals(scale)
    octave, step = divmod(degree, len(intervals))
    return max(0, min(127, root + intervals[step] + 12 * octave))


def build_chord(root: int, scale: str, degree: int, size: int = 3) -> list[int]:
    return [degree_to_pitch(root, scale, degree + 2 * i) for i in range(size)]


def snap_to_scale(pitch: int, root: int, scale: str) -> int:
    """Move a pitch to the nearest scale tone (preferring downward on ties)."""
    intervals = scale_intervals(scale)
    pitch_class = (pitch - root) % 12
    best = min(intervals, key=lambda i: (min((pitch_class - i) % 12, (i - pitch_class) % 12), i))
    delta_down = (pitch_class - best) % 12
    delta_up = (best - pitch_class) % 12
    snapped = pitch - delta_down if delta_down <= delta_up else pitch + delta_up
    return max(0, min(127, snapped))
