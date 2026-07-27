"""Mirror: a scale walk reflected around the register center. Visible symmetry."""

from __future__ import annotations

from typing import Any

from ..composition.harmony import snap_to_scale
from ..domain.note_event import NoteEvent, NoteRole
from .base import GenerationContext, GeneratorDefinition, NoteGenerator


class MirrorGenerator(NoteGenerator):
    definition = GeneratorDefinition(
        name="mirror",
        description="A melodic walk and its reflection around the register center.",
        category="visual_motion",
        visual_characteristics=("mirror", "diagonal_ascent", "diagonal_descent"),
        estimated_density="medium",
        supports_symmetry=True,
    )

    def generate(self, context: GenerationContext, params: dict[str, Any]) -> list[NoteEvent]:
        notes: list[NoteEvent] = []
        pitch_offset = 0
        beat = 0.0
        while beat < context.scene_duration:
            settings = context.settings_at(beat)
            step = 1.0 / max(2, settings.subdivision)
            low, high = context.register_at(beat)
            center = (low + high) // 2
            half_span = max(4, (high - low) // 2)

            # Ordered scenes walk smoothly; chaotic ones leap.
            max_leap = 1 + int((1.0 - context.order) * 6)
            pitch_offset += context.rng.randint(-max_leap, max_leap)
            pitch_offset = max(-half_span, min(half_span, pitch_offset))

            upper = snap_to_scale(center + pitch_offset, context.root, context.scale)
            lower = snap_to_scale(center - pitch_offset, context.root, context.scale)
            duration = max(step * 1.5, settings.note_length_beats * 0.6)
            velocity = self.velocity(context, beat, 0.6)
            notes.append(
                NoteEvent(pitch=upper, start=beat, duration=duration, velocity=velocity,
                          role=NoteRole.MELODY)
            )
            if upper != lower:
                notes.append(
                    NoteEvent(pitch=lower, start=beat, duration=duration, velocity=velocity,
                              role=NoteRole.VISUAL_EFFECT, tags=frozenset({"mirror"}))
                )
            beat += step
        return notes
