"""Sudden silence: cut the outgoing scene early so the incoming scene lands in a void."""

from __future__ import annotations

from dataclasses import replace

from ..domain.note_event import NoteEvent
from .base import Transition, TransitionContext, TransitionDefinition, TransitionResult


class SuddenSilence(Transition):
    definition = TransitionDefinition(
        name="sudden_silence",
        description="Cuts the last half bar dead — the next scene strikes out of a void.",
        visual_effect="void",
    )

    def apply(
        self,
        outgoing: list[NoteEvent],
        incoming: list[NoteEvent],
        context: TransitionContext,
    ) -> TransitionResult:
        cut_beat = context.boundary_beat - context.beats_per_bar / 2
        kept: list[NoteEvent] = []
        for note in outgoing:
            if note.start >= cut_beat:
                continue
            if note.end > cut_beat:
                note = replace(note, duration=max(0.05, cut_beat - note.start))
            kept.append(note)
        return TransitionResult(outgoing=kept, incoming=incoming, extra=[])
