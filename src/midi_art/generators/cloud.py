"""Note cloud: scattered points of light. Chaotic texture that scales with intensity."""

from __future__ import annotations

from typing import Any

from ..composition.harmony import snap_to_scale
from ..domain.note_event import NoteEvent, NoteRole
from .base import GenerationContext, GeneratorDefinition, NoteGenerator, ParamSpec, resolve_params


class CloudGenerator(NoteGenerator):
    definition = GeneratorDefinition(
        name="cloud",
        description="Scattered note constellations — chaotic sparkle that grows with intensity.",
        category="texture",
        visual_characteristics=("rain", "explosion"),
        estimated_density="variable",
        supports_harmony=True,
        params=(
            ParamSpec(
                name="density_scale",
                type="float",
                default=1.0,
                description="Multiplier on the intensity-driven note count.",
                minimum=0.0,
                maximum=4.0,
            ),
        ),
    )

    def generate(self, context: GenerationContext, params: dict[str, Any]) -> list[NoteEvent]:
        density_scale = resolve_params(self.definition, params)["density_scale"]
        notes: list[NoteEvent] = []
        beat = 0.0
        while beat < context.scene_duration:
            settings = context.settings_at(beat)
            count = max(0, int(settings.notes_per_beat * density_scale))
            low, high = context.register_at(beat)
            for _ in range(count):
                start = beat + context.rng.random()
                pitch = context.rng.randint(low, high)
                # Stable scenes keep the cloud in key; unstable ones go chromatic.
                if context.rng.random() < context.harmonic_stability:
                    pitch = snap_to_scale(pitch, context.root, context.scale)
                length = settings.note_length_beats * context.rng.uniform(0.4, 1.2)
                notes.append(
                    NoteEvent(
                        pitch=pitch,
                        start=min(start, context.scene_duration - 0.05),
                        duration=max(0.08, length),
                        velocity=self.velocity(context, beat, context.rng.uniform(0.25, 0.7)),
                        role=NoteRole.TEXTURE,
                    )
                )
            beat += 1.0
        return notes
