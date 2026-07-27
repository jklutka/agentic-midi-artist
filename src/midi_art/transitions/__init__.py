"""Transition plugin registry."""

from __future__ import annotations

from .base import Transition, TransitionContext, TransitionDefinition, TransitionResult
from .chord_impact import ChordWallImpact
from .crossfade import DensityCrossfade
from .silence import SuddenSilence
from .sweep import KeyboardSweep

TRANSITIONS: dict[str, Transition] = {
    transition.name: transition
    for transition in (
        DensityCrossfade(),
        SuddenSilence(),
        KeyboardSweep(),
        ChordWallImpact(),
    )
}


def get_transition(name: str) -> Transition:
    try:
        return TRANSITIONS[name]
    except KeyError as exc:
        allowed = ", ".join(sorted(TRANSITIONS))
        raise ValueError(f"Unknown transition {name!r}. Available: {allowed}") from exc


__all__ = [
    "TRANSITIONS",
    "Transition",
    "TransitionContext",
    "TransitionDefinition",
    "TransitionResult",
    "get_transition",
]
