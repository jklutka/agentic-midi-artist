"""Generator plugin interface.

Generators are artistic tools: each publishes metadata describing what it
looks like in Zenith, and produces scene-relative :class:`NoteEvent` lists
from a :class:`GenerationContext`. They never touch MIDI directly.
"""

from __future__ import annotations

import abc
import random
from dataclasses import dataclass
from typing import Any

from ..composition.controls import GeneratorSettings, map_intensity
from ..domain.automation import AutomationCurve, resolve
from ..domain.layer import Layer
from ..domain.note_event import NoteEvent


@dataclass(frozen=True)
class ParamSpec:
    """Declares one expert parameter of a generator: schema, default, and meaning.

    Bounds and choices are advisory (lint warns); ``resolve_params`` only
    coerces types so out-of-range values behave exactly as they always have.
    """

    name: str
    type: str  # "int" | "float" | "str"
    default: Any
    description: str
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] | None = None


@dataclass(frozen=True)
class GeneratorDefinition:
    """Metadata that lets the app present a generator as an artistic tool."""

    name: str
    description: str
    category: str
    visual_characteristics: tuple[str, ...]
    estimated_density: str
    supports_harmony: bool = True
    supports_symmetry: bool = False
    params: tuple[ParamSpec, ...] = ()


_COERCERS = {"int": int, "float": float, "str": str}


def resolve_params(definition: GeneratorDefinition, params: dict[str, Any]) -> dict[str, Any]:
    """Coerce and default ``params`` against the definition's specs.

    Unknown keys are ignored here (lint reports them); coercion matches the
    int()/float()/str() casts generators historically applied inline.
    """
    return {
        spec.name: _COERCERS[spec.type](params.get(spec.name, spec.default))
        for spec in definition.params
    }


@dataclass
class GenerationContext:
    """Everything a generator may consult. Starts are scene-relative beats."""

    rng: random.Random
    scene_duration: float
    beats_per_bar: int
    root: int
    scale: str
    layer: Layer
    intent_intensity_at: Any  # Callable[[float], float], beat -> intensity
    intent_register_at: Any  # Callable[[float], tuple[int, int]], beat -> (low, high)
    order: float
    harmonic_stability: float
    automation: tuple[AutomationCurve, ...] = ()

    def intensity_at(self, beat: float) -> float:
        base = self.intent_intensity_at(beat)
        return max(0.0, min(1.0, resolve(self.automation, "intensity", beat, base)))

    def register_at(self, beat: float) -> tuple[int, int]:
        low, high = self.intent_register_at(beat)
        center = resolve(self.automation, "register_center", beat, (low + high) / 2)
        span = resolve(self.automation, "register_span", beat, high - low)
        low = int(center - span / 2)
        high = int(max(low + 1, center + span / 2))
        return max(0, low), min(127, high)

    def settings_at(self, beat: float) -> GeneratorSettings:
        return map_intensity(self.intensity_at(beat))

    def value(self, target: str, beat: float, default: float) -> float:
        return resolve(self.automation, target, beat, default)


class NoteGenerator(abc.ABC):
    """Base class for note-generator plugins."""

    definition: GeneratorDefinition

    @abc.abstractmethod
    def generate(self, context: GenerationContext, params: dict[str, Any]) -> list[NoteEvent]:
        """Produce scene-relative note events. Must be pure given context.rng."""
        raise NotImplementedError

    @staticmethod
    def velocity(context: GenerationContext, beat: float, emphasis: float = 0.5) -> int:
        settings = context.settings_at(beat)
        spread = settings.velocity_max - settings.velocity_min
        jitter = context.rng.randint(-4, 4)
        return max(1, min(127, int(settings.velocity_min + spread * emphasis) + jitter))
