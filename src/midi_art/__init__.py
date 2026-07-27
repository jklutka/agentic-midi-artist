"""Agentic MIDI Artist (``midi-art``): an agent-first generative performance
composer for visually dramatic MIDI art.

The creative object is a *performance* — its structure, pacing, geometry,
tension, and climax. The ``.mid`` file is the final serialization stage,
designed specifically for rendering in Zenith-MIDI.

Layering:

- ``domain``       — the composition model (Project, Scene, Layer, NoteEvent)
- ``composition``  — harmony, artistic-control mapping, and the composer
- ``generators``   — note-generator plugins
- ``transitions``  — scene-boundary transition plugins
- ``analysis``     — performance metrics and validation
- ``export``       — Zenith-aware MIDI serialization
- ``presets``      — style presets that configure the whole engine
- ``app``          — the command-line interface
"""

from importlib import metadata as _metadata

from .composition.composer import Performance, compose
from .domain.automation import AutomationCurve, CurveType
from .domain.layer import GeneratorConfig, Layer, LayerRole
from .domain.note_event import NoteEvent, NoteRole
from .domain.project import ArtisticDirection, MusicalSettings, Project
from .domain.scene import Scene, SceneIntent

try:
    __version__ = _metadata.version("agentic-midi-artist")
except _metadata.PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0"

__all__ = [
    "ArtisticDirection",
    "AutomationCurve",
    "CurveType",
    "GeneratorConfig",
    "Layer",
    "LayerRole",
    "MusicalSettings",
    "NoteEvent",
    "NoteRole",
    "Performance",
    "Project",
    "Scene",
    "SceneIntent",
    "compose",
]
