"""Declarative spec of the project JSON document shape.

This is the single source of truth for what a project file may contain:
``midi-art describe`` renders it as the authoring contract and
``midi-art lint`` walks it against raw documents. It describes the *JSON*
shape (which differs from the dataclasses in two places: mood nests under
``artistic_direction.mood`` and the generator name lives at
``layers[].generator.type``).

A drift-guard test asserts the paths here exactly match ``Project.to_dict``
output — add a model field without a schema entry and pytest fails.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldSpec:
    """One node of the document tree.

    ``enum`` names an entry in ``enum_values``; violations are lint ERRORs
    unless ``enum_warn`` is set (used where unknown values are silently
    ignored rather than fatal). ``minimum``/``maximum`` are advisory ranges —
    values outside them are clamped at compose time, so lint warns only.
    """

    key: str
    type: str  # "str" | "int" | "float" | "bool" | "list[str]" | "object" | "array"
    required: bool = False
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    enum: str | None = None
    enum_warn: bool = False
    nullable: bool = False
    description: str = ""
    children: tuple["FieldSpec", ...] = ()
    free_form: bool = False  # object with unvalidated keys (e.g. generator params)


def enum_values(name: str) -> tuple[str, ...]:
    """Resolve a named enum source from the live registries (lazy imports)."""
    if name == "scales":
        from ..composition.harmony import SCALES

        return tuple(sorted(SCALES))
    if name == "roots":
        from ..composition.harmony import NOTE_NAMES

        return tuple(sorted(NOTE_NAMES))
    if name == "generators":
        from ..generators import GENERATORS

        return tuple(sorted(GENERATORS))
    if name == "transitions":
        from ..transitions import TRANSITIONS

        return tuple(sorted(TRANSITIONS))
    if name == "profiles":
        from ..export.zenith_profile import PROFILES

        return tuple(sorted(PROFILES))
    if name == "styles":
        from ..presets import STYLES

        return tuple(sorted(STYLES))
    if name == "curves":
        from .automation import CurveType

        return tuple(curve.value for curve in CurveType)
    if name == "roles":
        from .layer import LayerRole

        return tuple(role.value for role in LayerRole)
    if name == "automation_targets":
        from .automation import AUTOMATION_TARGETS

        return tuple(AUTOMATION_TARGETS)
    raise ValueError(f"Unknown enum source {name!r}.")


_AUTOMATION_CHILDREN = (
    FieldSpec(
        "target", "str", required=True, enum="automation_targets", enum_warn=True,
        description="What the curve drives; unknown targets are silently ignored.",
    ),
    FieldSpec("start_value", "float", required=True, description="Value at start_beat."),
    FieldSpec("end_value", "float", required=True, description="Value at end_beat."),
    FieldSpec("curve", "str", default="linear", enum="curves", description="Ramp shape."),
    FieldSpec("start_beat", "float", default=0.0, minimum=0,
              description="Scene-relative start beat."),
    FieldSpec("end_beat", "float", default=0.0, minimum=0,
              description="Scene-relative end beat (0 = instant at start_beat)."),
)

_LAYER_CHILDREN = (
    FieldSpec("name", "str", required=True, description="Layer name, unique within the scene."),
    FieldSpec("role", "str", default="texture", enum="roles",
              description="The layer's artistic purpose."),
    FieldSpec(
        "generator", "object", required=True,
        description="Which note-generator plugin drives this layer.",
        children=(
            FieldSpec("type", "str", required=True, enum="generators",
                      description="Generator plugin name."),
            FieldSpec("params", "object", free_form=True,
                      description="Expert params — validated against the generator's specs."),
        ),
    ),
    FieldSpec("color_group", "str", default="default",
              description="Free label; groups map to MIDI channels (= Zenith colors)."),
    FieldSpec("gain", "float", default=1.0, minimum=0, maximum=2,
              description="Velocity multiplier for the layer."),
    FieldSpec("automation", "array", children=_AUTOMATION_CHILDREN,
              description="Layer-level curves; override scene automation."),
)

_SCENE_CHILDREN = (
    FieldSpec("name", "str", required=True, description="Scene name, unique in the timeline."),
    FieldSpec("duration_bars", "int", required=True, minimum=1, maximum=256,
              description="Scene length in bars."),
    FieldSpec(
        "intent", "object", description="Artistic controls, all ramping over the scene.",
        children=(
            FieldSpec("intensity_start", "float", default=0.2, minimum=0, maximum=1,
                      description="Opening intensity: sparse/calm .. saturated/extreme."),
            FieldSpec("intensity_end", "float", default=0.4, minimum=0, maximum=1,
                      description="Closing intensity."),
            FieldSpec("intensity_curve", "str", default="linear", enum="curves",
                      description="Shape of the intensity ramp."),
            FieldSpec("register_center", "int", default=64, minimum=21, maximum=108,
                      description="MIDI pitch at the middle of the register."),
            FieldSpec("register_span_start", "int", default=24, minimum=1, maximum=88,
                      description="Register width in semitones at scene start."),
            FieldSpec("register_span_end", "int", default=36, minimum=1, maximum=88,
                      description="Register width at scene end."),
            FieldSpec("order", "float", default=0.7, minimum=0, maximum=1,
                      description="0 = chaotic, 1 = grid-tight geometry."),
            FieldSpec("harmonic_stability", "float", default=0.8, minimum=0, maximum=1,
                      description="0 = chromatic/dissonant, 1 = strictly in key."),
        ),
    ),
    FieldSpec("layers", "array", children=_LAYER_CHILDREN,
              description="Independent voices composed together."),
    FieldSpec("transition_out", "str", nullable=True, enum="transitions",
              description="Boundary effect into the next scene (null = hard cut)."),
    FieldSpec("automation", "array", children=_AUTOMATION_CHILDREN,
              description="Scene-level curves applied to every layer."),
)

PROJECT_SCHEMA: tuple[FieldSpec, ...] = (
    FieldSpec("format_version", "int", default=1, description="Project file format version."),
    FieldSpec("name", "str", required=True, description="Performance name."),
    FieldSpec("seed", "int", default=0,
              description="Master seed — same file + seed is byte-identical MIDI."),
    FieldSpec("export_profile", "str", default="zenith_standard", enum="profiles",
              description="Zenith export policy (density caps, overlap handling)."),
    FieldSpec("brief", "str", nullable=True,
              description="Path of the creative brief this project realizes."),
    FieldSpec(
        "artistic_direction", "object",
        description="Descriptive creative intent — never read by the composer.",
        children=(
            FieldSpec("theme", "str", default="", description="One-line theme."),
            FieldSpec(
                "mood", "object", description="Mood arc over the performance.",
                children=(
                    FieldSpec("start", "str", default="", description="Opening mood."),
                    FieldSpec("middle", "str", default="", description="Middle mood."),
                    FieldSpec("end", "str", default="", description="Closing mood."),
                ),
            ),
            FieldSpec("visual_focus", "list[str]", description="Visual priorities."),
        ),
    ),
    FieldSpec(
        "music", "object", description="Global musical settings.",
        children=(
            FieldSpec("root", "str", default="C", enum="roots",
                      description="Key root note name (case-sensitive)."),
            FieldSpec("octave", "int", default=4, minimum=0, maximum=8,
                      description="Octave of the root (C4 = MIDI 60)."),
            FieldSpec("scale", "str", default="minor", enum="scales", description="Scale name."),
            FieldSpec("tempo_start", "float", default=120.0, minimum=20, maximum=400,
                      description="Opening tempo in BPM."),
            FieldSpec("tempo_end", "float", nullable=True, minimum=20, maximum=400,
                      description="Closing tempo (null = constant tempo)."),
            FieldSpec("beats_per_bar", "int", default=4, minimum=1, maximum=16,
                      description="Time signature numerator."),
        ),
    ),
    FieldSpec("scenes", "array", children=_SCENE_CHILDREN,
              description="The performance timeline, played in order."),
)


BRIEF_SCHEMA: tuple[FieldSpec, ...] = (
    FieldSpec("brief_format_version", "int", default=1,
              description="Brief file format version."),
    FieldSpec("title", "str", required=True, description="Working title."),
    FieldSpec("logline", "str", default="",
              description="One sentence: what the audience should feel."),
    FieldSpec("mood_arc", "list[str]",
              description="Ordered moods, e.g. stillness → rupture → aftermath."),
    FieldSpec("energy_shape", "str", default="",
              description="Prose shape of the energy: 'slow build, cliff-edge drop'."),
    FieldSpec("duration_seconds", "float", nullable=True, minimum=10, maximum=3600,
              description="Target length of the piece."),
    FieldSpec("tempo_feel", "str", default="",
              description="Tempo in feelings or numbers: 'glacial', 'relentless ~150'."),
    FieldSpec("imagery", "list[str]",
              description="Visual references: 'rain on glass', 'collapsing tower'."),
    FieldSpec("palette", "list[str]",
              description="Color vocabulary hints for layer color groups."),
    FieldSpec("must_have_moments", "list[str]",
              description="Non-negotiable beats: 'total silence before the climax'."),
    FieldSpec("avoid", "list[str]", description="What the piece must NOT do."),
    FieldSpec("style_hint", "str", default="",
              description="Optional style preset to scaffold from."),
    FieldSpec("notes", "str", default="", description="Anything else."),
)


def schema_paths(specs: tuple[FieldSpec, ...] = PROJECT_SCHEMA, prefix: str = "") -> set[str]:
    """Dotted paths of every declared field; array elements are ``key[]``."""
    paths: set[str] = set()
    for spec in specs:
        path = f"{prefix}{spec.key}"
        paths.add(path)
        if spec.type == "array":
            paths |= schema_paths(spec.children, f"{path}[].")
        elif spec.children:
            paths |= schema_paths(spec.children, f"{path}.")
    return paths


def field_index(specs: tuple[FieldSpec, ...]) -> dict[str, FieldSpec]:
    return {spec.key: spec for spec in specs}
