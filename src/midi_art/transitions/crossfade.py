"""Density crossfade: the outgoing texture echoes and decays into the new scene."""

from __future__ import annotations

from dataclasses import replace

from ..domain.note_event import NoteEvent, NoteRole
from .base import Transition, TransitionContext, TransitionDefinition, TransitionResult


class DensityCrossfade(Transition):
    definition = TransitionDefinition(
        name="density_crossfade",
        description="Echoes of the outgoing scene decay across the first bars of the next.",
        visual_effect="fading_echoes",
    )

    def apply(
        self,
        outgoing: list[NoteEvent],
        incoming: list[NoteEvent],
        context: TransitionContext,
    ) -> TransitionResult:
        tail_beats = context.beats_per_bar * 1.0
        fade_beats = context.beats_per_bar * 2.0
        tail = [n for n in outgoing if n.start >= context.boundary_beat - tail_beats]
        # Keep the echo sparse: sample at most ~2 notes per beat of tail.
        max_echoes = int(tail_beats * 2)
        if len(tail) > max_echoes:
            tail = context.rng.sample(tail, max_echoes)

        extra: list[NoteEvent] = []
        for note in sorted(tail, key=lambda n: n.start):
            for echo in (1, 2):
                offset = echo * fade_beats / 2
                fade = 1.0 - (echo / 3.0)
                extra.append(
                    replace(
                        note,
                        start=note.start + offset,
                        velocity=max(1, int(note.velocity * fade * 0.7)),
                        role=NoteRole.TRANSITION,
                        tags=note.tags | {"echo"},
                    )
                )
        return TransitionResult(outgoing=outgoing, incoming=incoming, extra=extra)
