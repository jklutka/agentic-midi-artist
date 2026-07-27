"""Artistic controls: expressive sliders mapped to technical parameters.

Users think in intensity, order, and stability; generators consume note
rates, velocity ranges, and probabilities. This module is the single place
that translation lives.
"""

from __future__ import annotations

from dataclasses import dataclass


def interpolate(low: float, high: float, t: float) -> float:
    t = max(0.0, min(1.0, t))
    return low + (high - low) * t


@dataclass(frozen=True)
class GeneratorSettings:
    """Technical parameters derived from a single intensity value in [0, 1]."""

    notes_per_beat: float
    polyphony: int
    velocity_min: int
    velocity_max: int
    octave_span: int
    ornament_probability: float
    note_length_beats: float
    subdivision: int


def map_intensity(value: float) -> GeneratorSettings:
    """Translate one artistic intensity slider into generator parameters.

    Density grows quadratically so the top of the slider feels dramatic,
    while note lengths shrink to keep extreme sections readable in Zenith.
    """
    value = max(0.0, min(1.0, value))
    return GeneratorSettings(
        notes_per_beat=interpolate(0.5, 48.0, value**2),
        polyphony=int(interpolate(2, 200, value)),
        velocity_min=int(interpolate(40, 82, value)),
        velocity_max=int(interpolate(72, 127, value)),
        octave_span=int(interpolate(1, 6, value)),
        ornament_probability=interpolate(0.05, 0.65, value),
        note_length_beats=interpolate(1.0, 0.14, value),
        subdivision=_subdivision_for(value),
    )


def _subdivision_for(value: float) -> int:
    if value < 0.2:
        return 1
    if value < 0.45:
        return 2
    if value < 0.7:
        return 4
    if value < 0.9:
        return 8
    return 16
