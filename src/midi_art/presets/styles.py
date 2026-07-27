"""Style presets: complete project templates with a dramatic arc.

Each style chooses scenes, layers, generators, transitions, curves, and an
export profile — a whole performance the user can regenerate, reseed, and
edit scene by scene.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..domain.automation import CurveType
from ..domain.layer import GeneratorConfig, Layer, LayerRole
from ..domain.project import ArtisticDirection, MusicalSettings, Project
from ..domain.scene import Scene, SceneIntent


@dataclass(frozen=True)
class StyleDefinition:
    name: str
    description: str
    build: Callable[[str, int], Project]


def _layer(name: str, role: LayerRole, generator: str, color: str,
           gain: float = 1.0, **params) -> Layer:
    return Layer(
        name=name,
        role=role,
        generator=GeneratorConfig(generator=generator, params=params),
        color_group=color,
        gain=gain,
    )


def _mechanical_precision(name: str, seed: int) -> Project:
    """Quantized grids, high symmetry, abrupt transitions, consistent velocity."""
    bass = _layer("grid", LayerRole.BASS, "pulse", "steel", max_subdivision=8)
    arp = _layer("machinery", LayerRole.MELODY, "arpeggio", "copper", max_octaves=2)
    walls = _layer("stamp", LayerRole.ACCENT, "chord_wall", "warning")
    mirror = _layer("lattice", LayerRole.VISUAL_MOTION, "mirror", "chrome", gain=0.85)
    return Project(
        name=name,
        seed=seed,
        artistic_direction=ArtisticDirection(
            theme="mechanical_precision",
            mood_start="controlled",
            mood_middle="relentless",
            mood_end="overdriven",
            visual_focus=("symmetry", "vertical_note_walls", "repeating_structures"),
        ),
        music=MusicalSettings(root="E", scale="minor", tempo_start=124, tempo_end=152),
        export_profile="zenith_standard",
        scenes=(
            Scene("Initialization", 16,
                  SceneIntent(0.08, 0.2, CurveType.STEP, 52, 14, 20, order=0.98,
                              harmonic_stability=0.95),
                  layers=(bass,), transition_out="chord_wall_impact"),
            Scene("Assembly", 24,
                  SceneIntent(0.25, 0.45, CurveType.LINEAR, 60, 24, 30, order=0.95,
                              harmonic_stability=0.9),
                  layers=(bass, arp), transition_out="sudden_silence"),
            Scene("Production", 32,
                  SceneIntent(0.45, 0.7, CurveType.LINEAR, 64, 30, 42, order=0.92,
                              harmonic_stability=0.85),
                  layers=(bass, arp, mirror), transition_out="chord_wall_impact"),
            Scene("Overdrive", 24,
                  SceneIntent(0.7, 0.98, CurveType.EASE_IN, 66, 42, 66, order=0.85,
                              harmonic_stability=0.75),
                  layers=(bass, arp, mirror, walls), transition_out="sudden_silence"),
            Scene("Shutdown", 8,
                  SceneIntent(0.35, 0.05, CurveType.EASE_OUT, 48, 24, 12, order=0.98,
                              harmonic_stability=0.95),
                  layers=(bass,)),
        ),
    )


def _organic_growth(name: str, seed: int) -> Project:
    """Curved density growth, expanding register, smooth crossfaded transitions."""
    seedling = _layer("seedling", LayerRole.MELODY, "arpeggio", "moss", max_octaves=3)
    waves = _layer("canopy", LayerRole.VISUAL_MOTION, "wave", "leaf",
                   wavelength_bars=4.0, strands=2)
    rain = _layer("rain", LayerRole.TEXTURE, "cloud", "mist", gain=0.8, density_scale=0.6)
    roots = _layer("roots", LayerRole.BASS, "pulse", "bark", max_subdivision=2)
    bloom = _layer("bloom", LayerRole.VISUAL_MOTION, "cascade", "petal",
                   direction="up", runs_per_bar=1)
    return Project(
        name=name,
        seed=seed,
        artistic_direction=ArtisticDirection(
            theme="organic_growth",
            mood_start="dormant",
            mood_middle="flourishing",
            mood_end="radiant",
            visual_focus=("expanding_register", "waves", "gradual_density"),
        ),
        music=MusicalSettings(root="D", scale="dorian", tempo_start=96, tempo_end=126),
        export_profile="zenith_standard",
        scenes=(
            Scene("Germination", 16,
                  SceneIntent(0.05, 0.18, CurveType.EASE_IN, 60, 10, 18, order=0.7,
                              harmonic_stability=0.95),
                  layers=(roots, seedling), transition_out="density_crossfade"),
            Scene("Growth", 32,
                  SceneIntent(0.18, 0.45, CurveType.EASE_IN_OUT, 62, 20, 40, order=0.65,
                              harmonic_stability=0.9),
                  layers=(roots, seedling, waves), transition_out="density_crossfade"),
            Scene("Canopy", 32,
                  SceneIntent(0.45, 0.72, CurveType.EASE_IN_OUT, 64, 40, 60, order=0.6,
                              harmonic_stability=0.85),
                  layers=(roots, seedling, waves, rain), transition_out="keyboard_sweep"),
            Scene("Full Bloom", 24,
                  SceneIntent(0.72, 0.95, CurveType.EASE_OUT, 66, 60, 84, order=0.55,
                              harmonic_stability=0.8),
                  layers=(roots, seedling, waves, rain, bloom),
                  transition_out="density_crossfade"),
            Scene("Seed Fall", 16,
                  SceneIntent(0.5, 0.08, CurveType.EASE_OUT, 60, 48, 14, order=0.7,
                              harmonic_stability=0.95),
                  layers=(seedling, rain)),
        ),
    )


def _controlled_chaos(name: str, seed: int) -> Project:
    """Stable opening, rising chromatic corruption, huge late-stage note clouds."""
    anchor = _layer("anchor", LayerRole.BASS, "pulse", "ember", max_subdivision=4)
    theme = _layer("theme", LayerRole.MELODY, "mirror", "flame", gain=0.95)
    storm = _layer("storm", LayerRole.TEXTURE, "cloud", "ash", density_scale=1.4)
    surge = _layer("surge", LayerRole.VISUAL_MOTION, "cascade", "spark",
                   direction="alternate", runs_per_bar=2)
    slabs = _layer("slabs", LayerRole.ACCENT, "chord_wall", "core")
    return Project(
        name=name,
        seed=seed,
        artistic_direction=ArtisticDirection(
            theme="controlled_chaos",
            mood_start="stable",
            mood_middle="unraveling",
            mood_end="catastrophic",
            visual_focus=("high_density_climax", "fragmentation", "note_clouds"),
        ),
        music=MusicalSettings(root="A", scale="harmonic_minor", tempo_start=132,
                              tempo_end=176),
        export_profile="zenith_high_density",
        scenes=(
            Scene("Order", 16,
                  SceneIntent(0.1, 0.25, CurveType.LINEAR, 57, 20, 26, order=0.9,
                              harmonic_stability=0.95),
                  layers=(anchor, theme), transition_out="density_crossfade"),
            Scene("Hairline Cracks", 24,
                  SceneIntent(0.25, 0.5, CurveType.EASE_IN, 60, 26, 44, order=0.7,
                              harmonic_stability=0.75),
                  layers=(anchor, theme, storm), transition_out="keyboard_sweep"),
            Scene("Fracture", 24,
                  SceneIntent(0.5, 0.8, CurveType.EASE_IN, 64, 44, 66, order=0.45,
                              harmonic_stability=0.5),
                  layers=(anchor, theme, storm, surge), transition_out="sudden_silence"),
            Scene("Collapse", 20,
                  SceneIntent(0.85, 1.0, CurveType.EXPONENTIAL, 64, 66, 87, order=0.25,
                              harmonic_stability=0.3),
                  layers=(anchor, storm, surge, slabs), transition_out="chord_wall_impact"),
            Scene("Aftermath", 12,
                  SceneIntent(0.2, 0.04, CurveType.EASE_OUT, 52, 30, 10, order=0.8,
                              harmonic_stability=0.9),
                  layers=(theme,)),
        ),
    )


STYLES: dict[str, StyleDefinition] = {
    "mechanical_precision": StyleDefinition(
        name="mechanical_precision",
        description="Quantized grids, hard symmetry, abrupt transitions — a machine at work.",
        build=_mechanical_precision,
    ),
    "organic_growth": StyleDefinition(
        name="organic_growth",
        description="Curved density growth and an expanding register — something alive.",
        build=_organic_growth,
    ),
    "controlled_chaos": StyleDefinition(
        name="controlled_chaos",
        description="Stability corrupted by chromatic storms into a saturated collapse.",
        build=_controlled_chaos,
    ),
}


def style_names() -> list[str]:
    return sorted(STYLES)


def build_style(style: str, name: str, seed: int) -> Project:
    try:
        definition = STYLES[style]
    except KeyError as exc:
        allowed = ", ".join(style_names())
        raise ValueError(f"Unknown style {style!r}. Available: {allowed}") from exc
    return definition.build(name, seed)
