"""Chord wall: stacked chords across octaves. Vertical impact walls in Zenith."""

from __future__ import annotations

from typing import Any

from ..composition.harmony import build_chord, progression_for
from ..domain.note_event import NoteEvent, NoteRole
from .base import GenerationContext, GeneratorDefinition, NoteGenerator, ParamSpec, resolve_params


class ChordWallGenerator(NoteGenerator):
    definition = GeneratorDefinition(
        name="chord_wall",
        description="Chords stacked across octaves striking on bar lines — vertical walls.",
        category="accent",
        visual_characteristics=("vertical_wall", "pulse"),
        estimated_density="high",
        params=(
            ParamSpec(
                name="sustain_beats",
                type="float",
                default=0.0,
                description="Hold each wall chord this many beats (0 = intensity-driven length).",
                minimum=0.0,
                maximum=16.0,
            ),
        ),
    )

    def generate(self, context: GenerationContext, params: dict[str, Any]) -> list[NoteEvent]:
        p = resolve_params(self.definition, params)
        progression = progression_for(context.scale)
        sustain = p["sustain_beats"]
        notes: list[NoteEvent] = []
        bar_beats = context.beats_per_bar
        total_bars = int(context.scene_duration // bar_beats)

        for bar in range(total_bars):
            bar_start = bar * bar_beats
            settings = context.settings_at(bar_start)
            intensity = context.intensity_at(bar_start)
            degree = progression[bar % len(progression)]
            chord = build_chord(context.root, context.scale, degree)
            low, high = context.register_at(bar_start)

            hits = [bar_start]
            if intensity > 0.55:
                hits.append(bar_start + bar_beats / 2)
            if intensity > 0.85:
                hits.extend([bar_start + bar_beats / 4, bar_start + 3 * bar_beats / 4])

            for hit in hits:
                duration = sustain if sustain > 0 else max(0.2, settings.note_length_beats)
                base = chord[0] - 24
                pitch = base
                while pitch <= high:
                    for offset in [p - chord[0] for p in chord]:
                        wall_pitch = pitch + offset
                        if low - 12 <= wall_pitch <= high:
                            notes.append(
                                NoteEvent(
                                    pitch=wall_pitch,
                                    start=hit,
                                    duration=duration,
                                    velocity=self.velocity(
                                        context, hit, 0.9 if hit == bar_start else 0.6
                                    ),
                                    role=NoteRole.ACCENT,
                                )
                            )
                    pitch += 12
        return notes
