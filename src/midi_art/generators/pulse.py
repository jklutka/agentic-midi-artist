"""Pulse grid: a steady rhythmic anchor. Reads as regular beams in Zenith."""

from __future__ import annotations

from typing import Any

from ..composition.harmony import build_chord, progression_for
from ..domain.note_event import NoteEvent, NoteRole
from .base import GenerationContext, GeneratorDefinition, NoteGenerator, ParamSpec, resolve_params


class PulseGenerator(NoteGenerator):
    definition = GeneratorDefinition(
        name="pulse",
        description="Steady root/fifth pulses on a subdivision grid — the rhythmic anchor.",
        category="rhythm",
        visual_characteristics=("horizontal_beam", "pulse"),
        estimated_density="low",
        params=(
            ParamSpec(
                name="max_subdivision",
                type="int",
                default=4,
                description="Upper bound on pulses per beat; intensity can only lower it.",
                minimum=1,
                maximum=16,
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
            degree = progression[bar % len(progression)]
            chord = build_chord(context.root, context.scale, degree)
            bass_root = max(24, chord[0] - 24)
            bass_fifth = max(24, chord[2] - 24)

            settings = context.settings_at(bar_start)
            subdivision = max(1, min(p["max_subdivision"], settings.subdivision))
            step = bar_beats / (bar_beats * subdivision)
            steps = bar_beats * subdivision
            for i in range(steps):
                start = bar_start + i * step
                on_beat = i % subdivision == 0
                # Chaotic scenes drop pulses; ordered scenes keep the grid intact.
                if not on_beat and context.rng.random() > context.order:
                    continue
                pitch = bass_root if (bar + (i // subdivision)) % 2 == 0 else bass_fifth
                notes.append(
                    NoteEvent(
                        pitch=pitch if on_beat else pitch + 12,
                        start=start,
                        duration=min(step * 0.9, settings.note_length_beats),
                        velocity=self.velocity(context, start, 0.75 if on_beat else 0.4),
                        role=NoteRole.BASS if on_beat else NoteRole.RHYTHM,
                    )
                )
        return notes
