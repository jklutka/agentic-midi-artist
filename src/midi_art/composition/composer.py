"""The composer: turns a Project into a Performance.

Pipeline: scenes → layers → generators → transitions → channel allocation.
MIDI serialization is deliberately *not* here — see ``midi_art.export``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

from ..domain.layer import Layer
from ..domain.note_event import NoteEvent
from ..domain.project import Project
from ..domain.scene import Scene
from ..export.track_allocator import allocate_channels
from ..export.zenith_profile import ZenithExportSettings, get_profile
from ..generators import GenerationContext, get_generator
from ..transitions import TransitionContext, get_transition
from .harmony import root_pitch


@dataclass
class SceneSpan:
    name: str
    start_beat: float
    end_beat: float


@dataclass
class Performance:
    """A fully composed performance, ready for analysis and export."""

    project: Project
    notes: list[NoteEvent]
    tempo_events: list[tuple[float, float]]
    scene_spans: list[SceneSpan]
    layers_by_id: dict[str, Layer]
    settings: ZenithExportSettings
    warnings: list[str] = field(default_factory=list)

    @property
    def duration_beats(self) -> float:
        return self.scene_spans[-1].end_beat if self.scene_spans else 0.0


def compose(project: Project, *, scene_name: str | None = None) -> Performance:
    """Compose a project (or a single scene, for fast preview iteration).

    Deterministic: the same project file and seed always produce the same
    performance. Each layer draws from its own RNG stream keyed by
    ``seed:scene:layer`` so editing one layer never reshuffles the others.
    """
    scenes = list(project.scenes)
    if scene_name is not None:
        scenes = [scene for scene in scenes if scene.name == scene_name]
        if not scenes:
            available = ", ".join(s.name for s in project.scenes)
            raise ValueError(f"No scene named {scene_name!r}. Scenes: {available}")
    if not scenes:
        raise ValueError("Project has no scenes to compose.")

    settings = get_profile(project.export_profile)
    root = root_pitch(project.music.root, project.music.octave)
    beats_per_bar = project.music.beats_per_bar
    total_beats = sum(scene.duration_beats(beats_per_bar) for scene in scenes)

    warnings: list[str] = []
    layers_by_id: dict[str, Layer] = {}
    scene_spans: list[SceneSpan] = []
    scene_notes: list[list[NoteEvent]] = []
    tempo_events: list[tuple[float, float]] = []

    cursor = 0.0
    for scene_index, scene in enumerate(scenes):
        duration = scene.duration_beats(beats_per_bar)
        scene_spans.append(SceneSpan(scene.name, cursor, cursor + duration))
        tempo_events.append((cursor, _tempo_at(project, cursor, total_beats)))

        notes: list[NoteEvent] = []
        for layer in scene.layers:
            layer_id = f"{scene.name}/{layer.name}"
            layers_by_id[layer_id] = layer
            rng = random.Random(f"{project.seed}:{scene_index}:{scene.name}:{layer.name}")
            context = GenerationContext(
                rng=rng,
                scene_duration=duration,
                beats_per_bar=beats_per_bar,
                root=root,
                scale=project.music.scale,
                layer=layer,
                intent_intensity_at=lambda beat, s=scene, d=duration: s.intent.intensity_at(
                    beat / d if d else 0.0
                ),
                intent_register_at=lambda beat, s=scene, d=duration: s.intent.register_at(
                    beat / d if d else 0.0
                ),
                order=scene.intent.order,
                harmonic_stability=scene.intent.harmonic_stability,
                automation=scene.automation + layer.automation,
            )
            generator = get_generator(layer.generator.generator)
            generated = generator.generate(context, dict(layer.generator.params))
            for note in generated:
                velocity = max(1, min(127, int(note.velocity * layer.gain)))
                notes.append(
                    replace(
                        note,
                        start=note.start + cursor,
                        velocity=velocity,
                        layer_id=layer_id,
                    ).clamped()
                )
        if not notes:
            warnings.append(f"Scene {scene.name!r} produced no notes.")
        scene_notes.append(notes)
        cursor += duration

    _apply_transitions(scenes, scene_notes, scene_spans, project, root, warnings)

    all_notes = sorted(
        (note for notes in scene_notes for note in notes),
        key=lambda n: (n.start, n.pitch, n.channel),
    )
    all_notes = allocate_channels(all_notes, layers_by_id, settings)

    return Performance(
        project=project,
        notes=all_notes,
        tempo_events=tempo_events,
        scene_spans=scene_spans,
        layers_by_id=layers_by_id,
        settings=settings,
        warnings=warnings,
    )


def _tempo_at(project: Project, beat: float, total_beats: float) -> float:
    start = project.music.tempo_start
    end = project.music.tempo_end
    if end is None or total_beats <= 0:
        return start
    return start + (end - start) * (beat / total_beats)


def _apply_transitions(
    scenes: list[Scene],
    scene_notes: list[list[NoteEvent]],
    scene_spans: list[SceneSpan],
    project: Project,
    root: int,
    warnings: list[str],
) -> None:
    """Apply each scene's transition_out at its boundary with the next scene."""
    for index in range(len(scenes) - 1):
        name = scenes[index].transition_out
        if not name:
            continue
        transition = get_transition(name)
        rng = random.Random(f"{project.seed}:transition:{index}:{name}")
        context = TransitionContext(
            boundary_beat=scene_spans[index].end_beat,
            beats_per_bar=project.music.beats_per_bar,
            root=root,
            scale=project.music.scale,
            rng=rng,
            outgoing_scene=scenes[index],
            incoming_scene=scenes[index + 1],
        )
        result = transition.apply(scene_notes[index], scene_notes[index + 1], context)
        scene_notes[index] = result.outgoing
        scene_notes[index + 1] = result.incoming + [note.clamped() for note in result.extra]
