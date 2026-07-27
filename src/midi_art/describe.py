"""The authoring contract: everything needed to write a project file.

``midi-art describe --json`` emits this as one compact JSON object so an
agent (or any tool) can learn the full vocabulary — schema, generators with
param specs, transitions, styles, profiles, scales — in a single read,
without ever opening the source.
"""

from __future__ import annotations

from typing import Any

from . import __version__
from .composition.harmony import PROGRESSIONS, SCALES
from .domain.brief import BRIEF_FORMAT_VERSION
from .domain.project import FORMAT_VERSION
from .domain.schema import BRIEF_SCHEMA, PROJECT_SCHEMA, FieldSpec, enum_values
from .export.zenith_profile import PROFILES
from .generators import GENERATORS, ParamSpec
from .presets import STYLES
from .transitions import TRANSITIONS

QUIRKS = (
    "mood nests as artistic_direction.mood.{start,middle,end}",
    "the layer generator name lives at layers[].generator.type",
    "artistic_direction is descriptive only — the composer never reads it",
    "values outside declared ranges are clamped silently at compose time; lint warns",
    "unknown JSON keys and generator params are ignored at load time; lint reports them",
    "color_group labels are free-form; groups map to MIDI channels (= Zenith colors) "
    "in order of first appearance, channel 15 is reserved for transition notes",
)

WORKFLOW = (
    "midi-art describe --json            # this contract",
    'midi-art new "Title" --style <s> [--brief <b.json>] -o projects/x.json --json',
    "midi-art lint projects/x.json --json      # after every edit",
    "midi-art generate projects/x.json --json  # .mid + manifest",
    "midi-art report projects/x.json --json    # metrics + visual summary, no MIDI",
    "midi-art preview projects/x.json --format png   # look at the piano roll",
    "midi-art audio output/x.mid [--video render.mp4]  # .wav via FluidSynth, mux into video",
    "midi-art doctor --json / midi-art setup    # check / install the external toolchain",
)


def _range_text(minimum: float | None, maximum: float | None) -> str:
    if minimum is None and maximum is None:
        return ""
    low = f"{minimum:g}" if minimum is not None else ""
    high = f"{maximum:g}" if maximum is not None else ""
    return f" {low}..{high}"


def _field_text(spec: FieldSpec) -> str:
    parts = spec.type
    if spec.enum:
        parts += f" enum:{spec.enum}"
    parts += _range_text(spec.minimum, spec.maximum)
    if spec.required:
        parts += " required"
    elif spec.default is not None:
        parts += f" ={spec.default!r}" if isinstance(spec.default, str) else f" ={spec.default}"
    if spec.nullable:
        parts += " nullable"
    if spec.description:
        parts += f" — {spec.description}"
    return parts


def _schema_tree(specs: tuple[FieldSpec, ...]) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for spec in specs:
        if spec.type == "array" and spec.children:
            tree[spec.key + "[]"] = _schema_tree(spec.children)
        elif spec.children:
            tree[spec.key] = _schema_tree(spec.children)
        else:
            tree[spec.key] = _field_text(spec)
    return tree


def _param_text(spec: ParamSpec) -> str:
    parts = spec.type
    if spec.choices:
        parts += " one of " + "|".join(spec.choices)
    parts += _range_text(spec.minimum, spec.maximum)
    parts += f" ={spec.default!r}" if isinstance(spec.default, str) else f" ={spec.default}"
    if spec.description:
        parts += f" — {spec.description}"
    return parts


def build_contract() -> dict[str, Any]:
    generators = {}
    for name, generator in sorted(GENERATORS.items()):
        d = generator.definition
        entry: dict[str, Any] = {
            "description": d.description,
            "category": d.category,
            "density": d.estimated_density,
            "visuals": list(d.visual_characteristics),
            "params": {p.name: _param_text(p) for p in d.params},
        }
        if d.supports_symmetry:
            entry["supports_symmetry"] = True
        generators[name] = entry

    scales = {
        name: {
            "intervals": intervals,
            "progression": "dedicated" if name in PROGRESSIONS else "default (minor-like)",
        }
        for name, intervals in sorted(SCALES.items())
    }

    profiles = {
        name: {
            "description": profile.description,
            "max_total_notes": profile.max_total_notes,
            "max_notes_per_second": profile.max_notes_per_second,
            "max_polyphony": profile.max_polyphony,
            "min_note_duration_beats": profile.min_note_duration_beats,
        }
        for name, profile in sorted(PROFILES.items())
    }

    return {
        "product": "Agentic MIDI Artist",
        "tool": "midi-art",
        "version": __version__,
        "project_format_version": FORMAT_VERSION,
        "brief_format_version": BRIEF_FORMAT_VERSION,
        "workflow": list(WORKFLOW),
        "quirks": list(QUIRKS),
        "project_schema": _schema_tree(PROJECT_SCHEMA),
        "brief_schema": _schema_tree(BRIEF_SCHEMA),
        "enums": {
            name: list(enum_values(name))
            for name in ("roots", "curves", "roles", "automation_targets")
        },
        "generators": generators,
        "transitions": {
            name: {"description": t.description, "visual_effect": t.definition.visual_effect}
            for name, t in sorted(TRANSITIONS.items())
        },
        "styles": {name: s.description for name, s in sorted(STYLES.items())},
        "profiles": profiles,
        "scales": scales,
    }


def format_contract_text(contract: dict[str, Any]) -> str:
    """Human-readable outline of the contract."""
    lines: list[str] = [f"midi-art {contract['version']} authoring contract", ""]

    lines.append("Workflow:")
    lines.extend(f"  {step}" for step in contract["workflow"])

    lines.extend(["", "Quirks:"])
    lines.extend(f"  - {quirk}" for quirk in contract["quirks"])

    lines.extend(["", "Project schema:"])

    def _walk(tree: dict[str, Any], indent: int) -> None:
        for key, value in tree.items():
            if isinstance(value, dict):
                lines.append(f"{'  ' * indent}{key}:")
                _walk(value, indent + 1)
            else:
                lines.append(f"{'  ' * indent}{key}: {value}")

    _walk(contract["project_schema"], 1)

    lines.extend(["", "Creative brief schema (.brief.json):"])
    _walk(contract["brief_schema"], 1)

    lines.extend(["", "Generators:"])
    for name, info in contract["generators"].items():
        lines.append(f"  {name} [{info['category']}] density={info['density']}")
        lines.append(f"    {info['description']}")
        for pname, ptext in info["params"].items():
            lines.append(f"    param {pname}: {ptext}")

    lines.extend(["", "Transitions:"])
    for name, info in contract["transitions"].items():
        lines.append(f"  {name:20} {info['description']}")

    lines.extend(["", "Styles:"])
    for name, description in contract["styles"].items():
        lines.append(f"  {name:24} {description}")

    lines.extend(["", "Export profiles:"])
    for name, info in contract["profiles"].items():
        lines.append(f"  {name:26} {info['description']}")

    lines.extend(["", "Scales:"])
    for name, info in contract["scales"].items():
        lines.append(f"  {name:18} intervals={info['intervals']} progression={info['progression']}")

    for enum_name, values in contract["enums"].items():
        lines.append(f"\n{enum_name}: {', '.join(values)}")

    return "\n".join(lines)
