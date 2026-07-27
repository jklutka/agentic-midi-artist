"""The persistent project model: a durable, versionable artifact.

Projects serialize to plain JSON so they can be edited, duplicated, diffed,
and regenerated. Together with the seed, a project file fully reproduces a
performance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .automation import AutomationCurve, CurveType
from .layer import GeneratorConfig, Layer, LayerRole
from .scene import Scene, SceneIntent

FORMAT_VERSION = 1


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    """Read a required key, failing with a ValueError the CLI can present."""
    try:
        return data[key]
    except KeyError:
        raise ValueError(f"{where} is missing required key {key!r}.") from None


@dataclass(frozen=True)
class ArtisticDirection:
    """The creative brief: what the audience should see and feel."""

    theme: str = ""
    mood_start: str = ""
    mood_middle: str = ""
    mood_end: str = ""
    visual_focus: tuple[str, ...] = ()


@dataclass(frozen=True)
class MusicalSettings:
    root: str = "C"
    octave: int = 4
    scale: str = "minor"
    tempo_start: float = 120.0
    tempo_end: float | None = None
    beats_per_bar: int = 4


@dataclass(frozen=True)
class Project:
    name: str
    seed: int = 0
    artistic_direction: ArtisticDirection = field(default_factory=ArtisticDirection)
    music: MusicalSettings = field(default_factory=MusicalSettings)
    scenes: tuple[Scene, ...] = ()
    export_profile: str = "zenith_standard"
    brief_file: str | None = None  # path of the creative brief this project realizes

    @property
    def duration_beats(self) -> float:
        return sum(scene.duration_beats(self.music.beats_per_bar) for scene in self.scenes)

    # -- persistence ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": FORMAT_VERSION,
            "name": self.name,
            "seed": self.seed,
            "export_profile": self.export_profile,
            "brief": self.brief_file,
            "artistic_direction": {
                "theme": self.artistic_direction.theme,
                "mood": {
                    "start": self.artistic_direction.mood_start,
                    "middle": self.artistic_direction.mood_middle,
                    "end": self.artistic_direction.mood_end,
                },
                "visual_focus": list(self.artistic_direction.visual_focus),
            },
            "music": {
                "root": self.music.root,
                "octave": self.music.octave,
                "scale": self.music.scale,
                "tempo_start": self.music.tempo_start,
                "tempo_end": self.music.tempo_end,
                "beats_per_bar": self.music.beats_per_bar,
            },
            "scenes": [_scene_to_dict(scene) for scene in self.scenes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Project:
        direction = data.get("artistic_direction", {})
        mood = direction.get("mood", {})
        music = data.get("music", {})
        return cls(
            name=_require(data, "name", "project"),
            seed=int(data.get("seed", 0)),
            export_profile=str(data.get("export_profile", "zenith_standard")),
            brief_file=data.get("brief"),
            artistic_direction=ArtisticDirection(
                theme=direction.get("theme", ""),
                mood_start=mood.get("start", ""),
                mood_middle=mood.get("middle", ""),
                mood_end=mood.get("end", ""),
                visual_focus=tuple(direction.get("visual_focus", ())),
            ),
            music=MusicalSettings(
                root=music.get("root", "C"),
                octave=int(music.get("octave", 4)),
                scale=music.get("scale", "minor"),
                tempo_start=float(music.get("tempo_start", 120.0)),
                tempo_end=(
                    float(music["tempo_end"]) if music.get("tempo_end") is not None else None
                ),
                beats_per_bar=int(music.get("beats_per_bar", 4)),
            ),
            scenes=tuple(_scene_from_dict(scene) for scene in data.get("scenes", ())),
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> Project:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        version = data.get("format_version", 1)
        if version > FORMAT_VERSION:
            raise ValueError(f"Project format {version} is newer than supported {FORMAT_VERSION}.")
        return cls.from_dict(data)


def _curve_to_dict(curve: AutomationCurve) -> dict[str, Any]:
    return {
        "target": curve.target,
        "start_value": curve.start_value,
        "end_value": curve.end_value,
        "curve": curve.curve.value,
        "start_beat": curve.start_beat,
        "end_beat": curve.end_beat,
    }


def _curve_from_dict(data: dict[str, Any]) -> AutomationCurve:
    return AutomationCurve(
        target=_require(data, "target", "automation curve"),
        start_value=float(_require(data, "start_value", "automation curve")),
        end_value=float(_require(data, "end_value", "automation curve")),
        curve=CurveType(data.get("curve", "linear")),
        start_beat=float(data.get("start_beat", 0.0)),
        end_beat=float(data.get("end_beat", 0.0)),
    )


def _layer_to_dict(layer: Layer) -> dict[str, Any]:
    return {
        "name": layer.name,
        "role": layer.role.value,
        "generator": {
            "type": layer.generator.generator,
            "params": dict(layer.generator.params),
        },
        "color_group": layer.color_group,
        "gain": layer.gain,
        "automation": [_curve_to_dict(curve) for curve in layer.automation],
    }


def _layer_from_dict(data: dict[str, Any]) -> Layer:
    generator = data.get("generator", {})
    return Layer(
        name=_require(data, "name", "layer"),
        role=LayerRole(data.get("role", "texture")),
        generator=GeneratorConfig(
            generator=generator.get("type", "pulse"),
            params=dict(generator.get("params", {})),
        ),
        color_group=data.get("color_group", "default"),
        gain=float(data.get("gain", 1.0)),
        automation=tuple(_curve_from_dict(curve) for curve in data.get("automation", ())),
    )


def _scene_to_dict(scene: Scene) -> dict[str, Any]:
    intent = scene.intent
    return {
        "name": scene.name,
        "duration_bars": scene.duration_bars,
        "intent": {
            "intensity_start": intent.intensity_start,
            "intensity_end": intent.intensity_end,
            "intensity_curve": intent.intensity_curve.value,
            "register_center": intent.register_center,
            "register_span_start": intent.register_span_start,
            "register_span_end": intent.register_span_end,
            "order": intent.order,
            "harmonic_stability": intent.harmonic_stability,
        },
        "layers": [_layer_to_dict(layer) for layer in scene.layers],
        "transition_out": scene.transition_out,
        "automation": [_curve_to_dict(curve) for curve in scene.automation],
    }


def _scene_from_dict(data: dict[str, Any]) -> Scene:
    intent = data.get("intent", {})
    return Scene(
        name=_require(data, "name", "scene"),
        duration_bars=int(_require(data, "duration_bars", "scene")),
        intent=SceneIntent(
            intensity_start=float(intent.get("intensity_start", 0.2)),
            intensity_end=float(intent.get("intensity_end", 0.4)),
            intensity_curve=CurveType(intent.get("intensity_curve", "linear")),
            register_center=int(intent.get("register_center", 64)),
            register_span_start=int(intent.get("register_span_start", 24)),
            register_span_end=int(intent.get("register_span_end", 36)),
            order=float(intent.get("order", 0.7)),
            harmonic_stability=float(intent.get("harmonic_stability", 0.8)),
        ),
        layers=tuple(_layer_from_dict(layer) for layer in data.get("layers", ())),
        transition_out=data.get("transition_out"),
        automation=tuple(_curve_from_dict(curve) for curve in data.get("automation", ())),
    )
