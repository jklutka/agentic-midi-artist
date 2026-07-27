"""Full-keyboard sweep: a glissando racing across the range into the boundary."""

from __future__ import annotations

from ..composition.harmony import snap_to_scale
from ..domain.note_event import NoteEvent, NoteRole
from .base import Transition, TransitionContext, TransitionDefinition, TransitionResult


class KeyboardSweep(Transition):
    definition = TransitionDefinition(
        name="keyboard_sweep",
        description="A glissando races across the full keyboard, arriving exactly on the boundary.",
        visual_effect="glissando_streak",
    )

    def apply(
        self,
        outgoing: list[NoteEvent],
        incoming: list[NoteEvent],
        context: TransitionContext,
    ) -> TransitionResult:
        sweep_beats = context.beats_per_bar / 2
        low, high = 21, 108
        steps = 44
        rising = context.rng.random() < 0.5
        extra: list[NoteEvent] = []
        for i in range(steps):
            t = i / (steps - 1)
            pitch = int(low + (high - low) * (t if rising else 1.0 - t))
            pitch = snap_to_scale(pitch, context.root, context.scale)
            extra.append(
                NoteEvent(
                    pitch=pitch,
                    start=context.boundary_beat - sweep_beats + t * sweep_beats,
                    duration=sweep_beats / steps * 2.5,
                    velocity=int(70 + 50 * t),
                    role=NoteRole.TRANSITION,
                    tags=frozenset({"sweep"}),
                )
            )
        return TransitionResult(outgoing=outgoing, incoming=incoming, extra=extra)
