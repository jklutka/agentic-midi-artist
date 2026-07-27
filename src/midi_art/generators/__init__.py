"""Generator plugin registry."""

from __future__ import annotations

from .arpeggio import ArpeggioGenerator
from .base import GenerationContext, GeneratorDefinition, NoteGenerator, ParamSpec, resolve_params
from .cascade import CascadeGenerator
from .chord_wall import ChordWallGenerator
from .cloud import CloudGenerator
from .mirror import MirrorGenerator
from .pulse import PulseGenerator
from .wave import WaveGenerator

GENERATORS: dict[str, NoteGenerator] = {
    generator.definition.name: generator
    for generator in (
        PulseGenerator(),
        ArpeggioGenerator(),
        CascadeGenerator(),
        ChordWallGenerator(),
        CloudGenerator(),
        WaveGenerator(),
        MirrorGenerator(),
    )
}


def get_generator(name: str) -> NoteGenerator:
    try:
        return GENERATORS[name]
    except KeyError as exc:
        allowed = ", ".join(sorted(GENERATORS))
        raise ValueError(f"Unknown generator {name!r}. Available: {allowed}") from exc


__all__ = [
    "GENERATORS",
    "GenerationContext",
    "GeneratorDefinition",
    "NoteGenerator",
    "ParamSpec",
    "get_generator",
    "resolve_params",
]
