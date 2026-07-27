"""Scale cascade: runs sweeping across the register. Strong diagonals in Zenith."""

from __future__ import annotations

from typing import Any

from ..composition.harmony import snap_to_scale
from ..domain.note_event import NoteEvent, NoteRole
from .base import GenerationContext, GeneratorDefinition, NoteGenerator, ParamSpec, resolve_params


class CascadeGenerator(NoteGenerator):
    definition = GeneratorDefinition(
        name="cascade",
        description="Scale runs sweeping the full register — bold diagonal lines.",
        category="visual_motion",
        visual_characteristics=("diagonal_ascent", "diagonal_descent", "rain"),
        estimated_density="medium",
        params=(
            ParamSpec(
                name="direction",
                type="str",
                default="alternate",
                description="Run direction; 'alternate' flips every run.",
                choices=("up", "down", "alternate"),
            ),
            ParamSpec(
                name="runs_per_bar",
                type="int",
                default=1,
                description="Number of full-register runs packed into each bar.",
                minimum=1,
                maximum=8,
            ),
        ),
    )

    def generate(self, context: GenerationContext, params: dict[str, Any]) -> list[NoteEvent]:
        p = resolve_params(self.definition, params)
        direction = p["direction"]
        runs_per_bar = p["runs_per_bar"]
        notes: list[NoteEvent] = []
        bar_beats = context.beats_per_bar
        total_bars = int(context.scene_duration // bar_beats)

        for bar in range(total_bars):
            bar_start = bar * bar_beats
            settings = context.settings_at(bar_start)
            low, high = context.register_at(bar_start)
            span = max(12, high - low)
            steps = max(6, int(settings.notes_per_beat * bar_beats / max(1, runs_per_bar)))
            steps = min(steps, span * 2)

            for run in range(max(1, runs_per_bar)):
                descending = direction == "down" or (
                    direction == "alternate" and (bar + run) % 2 == 1
                )
                run_start = bar_start + run * (bar_beats / max(1, runs_per_bar))
                run_length = bar_beats / max(1, runs_per_bar)
                step_beats = run_length / steps
                for i in range(steps):
                    t = i / max(1, steps - 1)
                    pitch = int(low + span * (1.0 - t if descending else t))
                    pitch = snap_to_scale(pitch, context.root, context.scale)
                    start = run_start + i * step_beats
                    notes.append(
                        NoteEvent(
                            pitch=pitch,
                            start=start,
                            duration=max(step_beats * 1.8, settings.note_length_beats * 0.5),
                            velocity=self.velocity(context, start, 0.45 + 0.4 * t),
                            role=NoteRole.VISUAL_EFFECT,
                        )
                    )
        return notes
