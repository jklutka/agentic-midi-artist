"""Wave: sinusoidal pitch sweeps. Hypnotic rolling motion across the keyboard."""

from __future__ import annotations

import math
from typing import Any

from ..composition.harmony import snap_to_scale
from ..domain.note_event import NoteEvent, NoteRole
from .base import GenerationContext, GeneratorDefinition, NoteGenerator, ParamSpec, resolve_params


class WaveGenerator(NoteGenerator):
    definition = GeneratorDefinition(
        name="wave",
        description="Sine-shaped pitch sweeps — long, hypnotic rolling motion.",
        category="visual_motion",
        visual_characteristics=("wave", "curtain"),
        estimated_density="high",
        supports_symmetry=True,
        params=(
            ParamSpec(
                name="wavelength_bars",
                type="float",
                default=2.0,
                description="Bars per full sine cycle — longer means slower rolling motion.",
                minimum=0.25,
                maximum=32.0,
            ),
            ParamSpec(
                name="strands",
                type="int",
                default=1,
                description="Parallel phase-shifted waves woven together.",
                minimum=1,
                maximum=6,
            ),
        ),
    )

    def generate(self, context: GenerationContext, params: dict[str, Any]) -> list[NoteEvent]:
        p = resolve_params(self.definition, params)
        wavelength_bars = p["wavelength_bars"]
        strands = p["strands"]
        notes: list[NoteEvent] = []
        bar_beats = context.beats_per_bar
        wavelength_beats = max(1.0, wavelength_bars * bar_beats)

        beat = 0.0
        while beat < context.scene_duration:
            settings = context.settings_at(beat)
            step = max(1.0 / max(2, settings.subdivision * 2), 0.0625)
            low, high = context.register_at(beat)
            center = (low + high) / 2
            amplitude = (high - low) / 2

            for strand in range(max(1, strands)):
                phase = (beat / wavelength_beats) * math.tau + strand * (math.tau / max(1, strands))
                pitch = int(center + amplitude * math.sin(phase) + 4 * math.sin(phase * 0.5))
                if context.harmonic_stability > 0.5:
                    pitch = snap_to_scale(pitch, context.root, context.scale)
                notes.append(
                    NoteEvent(
                        pitch=max(0, min(127, pitch)),
                        start=beat,
                        duration=step * 1.8,
                        velocity=self.velocity(context, beat, 0.5 + 0.2 * math.sin(phase)),
                        role=NoteRole.VISUAL_EFFECT,
                    )
                )
            beat += step
        return notes
