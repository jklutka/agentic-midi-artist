"""Chord-wall impact: a full-range chord strike exactly on the scene boundary."""

from __future__ import annotations

from ..composition.harmony import build_chord
from ..domain.note_event import NoteEvent, NoteRole
from .base import Transition, TransitionContext, TransitionDefinition, TransitionResult


class ChordWallImpact(Transition):
    definition = TransitionDefinition(
        name="chord_wall_impact",
        description="A tonic chord stacked across the whole keyboard lands on the downbeat.",
        visual_effect="full_range_wall",
    )

    def apply(
        self,
        outgoing: list[NoteEvent],
        incoming: list[NoteEvent],
        context: TransitionContext,
    ) -> TransitionResult:
        chord = build_chord(context.root, context.scale, 0)
        offsets = [pitch - chord[0] for pitch in chord]
        extra: list[NoteEvent] = []
        base = chord[0] % 12 + 24
        pitch = base
        while pitch <= 108:
            for offset in offsets:
                if 21 <= pitch + offset <= 108:
                    extra.append(
                        NoteEvent(
                            pitch=pitch + offset,
                            start=context.boundary_beat,
                            duration=context.beats_per_bar / 2,
                            velocity=118,
                            role=NoteRole.TRANSITION,
                            tags=frozenset({"impact"}),
                        )
                    )
            pitch += 12
        return TransitionResult(outgoing=outgoing, incoming=incoming, extra=extra)
