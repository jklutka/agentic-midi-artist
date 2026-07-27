"""The core event model: a note with musical *and* visual intent."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum


class NoteRole(str, Enum):
    """Why a note exists. Roles drive channel allocation, analysis, and editing."""

    MELODY = "melody"
    HARMONY = "harmony"
    RHYTHM = "rhythm"
    BASS = "bass"
    TEXTURE = "texture"
    VISUAL_EFFECT = "visual_effect"
    TRANSITION = "transition"
    ACCENT = "accent"


@dataclass(frozen=True)
class NoteEvent:
    """A single note, timed in beats from the start of the performance.

    Timing stays in float beats until export; the MIDI writer owns the
    beats-to-ticks conversion.
    """

    pitch: int
    start: float
    duration: float
    velocity: int
    channel: int = 0
    layer_id: str = ""
    role: NoteRole = NoteRole.TEXTURE
    tags: frozenset[str] = field(default_factory=frozenset)

    @property
    def end(self) -> float:
        return self.start + self.duration

    def clamped(self) -> NoteEvent:
        """Return a copy with pitch/velocity forced into valid MIDI ranges."""
        pitch = max(0, min(127, self.pitch))
        velocity = max(1, min(127, self.velocity))
        duration = max(1e-4, self.duration)
        if (pitch, velocity, duration) == (self.pitch, self.velocity, self.duration):
            return self
        return replace(self, pitch=pitch, velocity=velocity, duration=duration)
