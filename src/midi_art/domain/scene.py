"""Scenes: the main unit of artistic composition."""

from __future__ import annotations

from dataclasses import dataclass, field

from .automation import AutomationCurve, CurveType, shape
from .layer import Layer


@dataclass(frozen=True)
class SceneIntent:
    """Artistic controls for a scene, all expressed as ranges over its duration.

    Values in [0, 1] read as sliders:
    - intensity: sparse/calm .. saturated/extreme
    - order: chaotic .. geometric
    - harmonic_stability: dissonant .. stable
    """

    intensity_start: float = 0.2
    intensity_end: float = 0.4
    intensity_curve: CurveType = CurveType.LINEAR
    register_center: int = 64
    register_span_start: int = 24
    register_span_end: int = 36
    order: float = 0.7
    harmonic_stability: float = 0.8

    def intensity_at(self, progress: float) -> float:
        t = shape(progress, self.intensity_curve)
        return self.intensity_start + (self.intensity_end - self.intensity_start) * t

    def register_at(self, progress: float) -> tuple[int, int]:
        """Return the (low, high) pitch bounds at scene progress in [0, 1]."""
        span = self.register_span_start + (
            self.register_span_end - self.register_span_start
        ) * max(0.0, min(1.0, progress))
        low = int(self.register_center - span / 2)
        high = int(self.register_center + span / 2)
        return max(21, low), min(108, high)


@dataclass(frozen=True)
class Scene:
    """A visually and musically distinct section of the performance."""

    name: str
    duration_bars: int
    intent: SceneIntent = field(default_factory=SceneIntent)
    layers: tuple[Layer, ...] = ()
    transition_out: str | None = None
    automation: tuple[AutomationCurve, ...] = ()

    def duration_beats(self, beats_per_bar: int) -> float:
        return float(self.duration_bars * beats_per_bar)
