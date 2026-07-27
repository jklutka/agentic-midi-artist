"""Layers: independent voices within a scene, each with a role and a generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .automation import AutomationCurve


class LayerRole(str, Enum):
    """The primary purpose of a layer — sound, visuals, or both."""

    MELODY = "melody"
    BASS = "bass"
    RHYTHM = "rhythm"
    HARMONY = "harmony"
    TEXTURE = "texture"
    VISUAL_MOTION = "visual_motion"
    ACCENT = "accent"
    TRANSITION = "transition"


@dataclass(frozen=True)
class GeneratorConfig:
    """Which generator plugin drives a layer, plus its expert-mode parameters."""

    generator: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Layer:
    name: str
    role: LayerRole
    generator: GeneratorConfig
    color_group: str = "default"
    gain: float = 1.0
    automation: tuple[AutomationCurve, ...] = ()
