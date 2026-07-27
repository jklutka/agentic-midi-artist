"""Automation: parameters that change over time turn patterns into performances."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

# The only targets GenerationContext consumes; curves naming anything else
# are silently ignored (lint warns about them).
AUTOMATION_TARGETS: dict[str, str] = {
    "intensity": "overrides the scene intensity ramp (0..1)",
    "register_center": "overrides the register midpoint (MIDI pitch)",
    "register_span": "overrides the register width (semitones)",
}


class CurveType(str, Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    STEP = "step"
    OSCILLATING = "oscillating"


def shape(t: float, curve: CurveType) -> float:
    """Map linear progress ``t`` in [0, 1] through a curve shape."""
    t = max(0.0, min(1.0, t))
    if curve is CurveType.LINEAR:
        return t
    if curve is CurveType.EASE_IN:
        return t * t
    if curve is CurveType.EASE_OUT:
        return 1.0 - (1.0 - t) ** 2
    if curve is CurveType.EASE_IN_OUT:
        return t * t * (3.0 - 2.0 * t)
    if curve is CurveType.EXPONENTIAL:
        return (math.exp(4.0 * t) - 1.0) / (math.exp(4.0) - 1.0)
    if curve is CurveType.LOGARITHMIC:
        return math.log1p(9.0 * t) / math.log(10.0)
    if curve is CurveType.STEP:
        return 0.0 if t < 1.0 else 1.0
    if curve is CurveType.OSCILLATING:
        return t + 0.12 * math.sin(t * math.tau * 3.0) * (1.0 - t)
    raise ValueError(f"Unknown curve type: {curve}")


@dataclass(frozen=True)
class AutomationCurve:
    """A value ramp for a named target over a beat range (scene-relative)."""

    target: str
    start_value: float
    end_value: float
    curve: CurveType = CurveType.LINEAR
    start_beat: float = 0.0
    end_beat: float = 0.0

    def value_at(self, beat: float) -> float:
        span = self.end_beat - self.start_beat
        if span <= 0:
            return self.end_value if beat >= self.start_beat else self.start_value
        t = shape((beat - self.start_beat) / span, self.curve)
        return self.start_value + (self.end_value - self.start_value) * t


def resolve(
    curves: Iterable[AutomationCurve],
    target: str,
    beat: float,
    default: float,
) -> float:
    """Evaluate the last matching curve for ``target`` at ``beat``.

    Later curves win, so layer automation can be appended after scene
    automation to override it.
    """
    value = default
    for curve in curves:
        if curve.target == target:
            value = curve.value_at(beat)
    return value
