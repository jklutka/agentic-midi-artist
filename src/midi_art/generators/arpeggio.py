"""Arpeggio: broken chords cycling with the progression. Rolling motion."""

from __future__ import annotations

from typing import Any

from ..composition.harmony import build_chord, progression_for
from ..domain.note_event import NoteEvent, NoteRole
from .base import GenerationContext, GeneratorDefinition, NoteGenerator, ParamSpec, resolve_params


class ArpeggioGenerator(NoteGenerator):
    definition = GeneratorDefinition(
        name="arpeggio",
        description="Broken chords rolling up and down the current harmony.",
        category="melody",
        visual_characteristics=("diagonal_ascent", "diagonal_descent"),
        estimated_density="medium",
        params=(
            ParamSpec(
                name="max_octaves",
                type="int",
                default=3,
                description="Octave spread of the broken-chord pool; intensity can only lower it.",
                minimum=1,
                maximum=6,
            ),
        ),
    )

    def generate(self, context: GenerationContext, params: dict[str, Any]) -> list[NoteEvent]:
        p = resolve_params(self.definition, params)
        progression = progression_for(context.scale)
        notes: list[NoteEvent] = []
        bar_beats = context.beats_per_bar
        total_bars = int(context.scene_duration // bar_beats)

        for bar in range(total_bars):
            bar_start = bar * bar_beats
            settings = context.settings_at(bar_start)
            degree = progression[bar % len(progression)]
            chord = build_chord(context.root, context.scale, degree)
            octaves = max(1, min(settings.octave_span, p["max_octaves"]))
            pool = [pitch + 12 * octave for octave in range(octaves) for pitch in chord]
            ascending = pool + pool[-2:0:-1]  # up then back down, no repeated apex

            subdivision = max(2, settings.subdivision)
            step = 1.0 / subdivision
            steps = int(bar_beats * subdivision)
            for i in range(steps):
                start = bar_start + i * step
                pitch = ascending[i % len(ascending)]
                low, high = context.register_at(start)
                while pitch < low:
                    pitch += 12
                while pitch > high:
                    pitch -= 12
                notes.append(
                    NoteEvent(
                        pitch=pitch,
                        start=start,
                        duration=step * 1.5,
                        velocity=self.velocity(context, start, 0.6 if i % subdivision else 0.8),
                        role=NoteRole.MELODY,
                    )
                )
                if context.rng.random() < settings.ornament_probability:
                    notes.append(
                        NoteEvent(
                            pitch=min(127, pitch + 12),
                            start=start + step / 2,
                            duration=step * 0.75,
                            velocity=self.velocity(context, start, 0.35),
                            role=NoteRole.TEXTURE,
                        )
                    )
        return notes
