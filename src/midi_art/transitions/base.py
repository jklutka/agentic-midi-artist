"""Transition plugin interface: scenes should not simply stop and start.

A transition may modify the outgoing scene's notes, modify the incoming
scene's notes, and/or contribute entirely new notes of its own. All note
starts are absolute performance beats.
"""

from __future__ import annotations

import abc
import random
from dataclasses import dataclass

from ..domain.note_event import NoteEvent
from ..domain.scene import Scene


@dataclass
class TransitionContext:
    boundary_beat: float
    beats_per_bar: int
    root: int
    scale: str
    rng: random.Random
    outgoing_scene: Scene
    incoming_scene: Scene


@dataclass
class TransitionResult:
    outgoing: list[NoteEvent]
    incoming: list[NoteEvent]
    extra: list[NoteEvent]


@dataclass(frozen=True)
class TransitionDefinition:
    """Metadata that lets the app present a transition as an artistic tool."""

    name: str
    description: str
    visual_effect: str = ""


class Transition(abc.ABC):
    definition: TransitionDefinition

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def description(self) -> str:
        return self.definition.description

    @abc.abstractmethod
    def apply(
        self,
        outgoing: list[NoteEvent],
        incoming: list[NoteEvent],
        context: TransitionContext,
    ) -> TransitionResult:
        raise NotImplementedError
