"""The authoring contract: describe output and schema drift guards."""

from __future__ import annotations

from typing import Any

from midi_art.describe import build_contract, format_contract_text
from midi_art.domain.automation import AUTOMATION_TARGETS, AutomationCurve, CurveType
from midi_art.domain.layer import GeneratorConfig, Layer, LayerRole
from midi_art.domain.project import ArtisticDirection, MusicalSettings, Project
from midi_art.domain.scene import Scene, SceneIntent
from midi_art.domain.schema import PROJECT_SCHEMA, enum_values, schema_paths
from midi_art.export.zenith_profile import PROFILES
from midi_art.generators import GENERATORS, resolve_params
from midi_art.presets import STYLES
from midi_art.transitions import TRANSITIONS


def _max_project() -> Project:
    """A project exercising every serializable field."""
    curve = AutomationCurve(
        target="intensity", start_value=0.1, end_value=0.9,
        curve=CurveType.EASE_IN, start_beat=0.0, end_beat=8.0,
    )
    layer = Layer(
        name="layer", role=LayerRole.MELODY,
        generator=GeneratorConfig(generator="pulse", params={"max_subdivision": 2}),
        color_group="ember", gain=0.9, automation=(curve,),
    )
    scene = Scene(
        name="scene", duration_bars=4, intent=SceneIntent(),
        layers=(layer,), transition_out="sudden_silence", automation=(curve,),
    )
    return Project(
        name="Max",
        seed=7,
        artistic_direction=ArtisticDirection(
            theme="t", mood_start="a", mood_middle="b", mood_end="c", visual_focus=("x",)
        ),
        music=MusicalSettings(tempo_end=140.0),
        scenes=(scene,),
        export_profile="zenith_standard",
        brief_file="projects/max.brief.json",
    )


def _document_paths(data: Any, prefix: str = "") -> set[str]:
    """Dotted key paths of a JSON document; list elements become ``key[]``.

    Free-form dicts (generator params) are treated as leaves, matching the
    schema's ``free_form`` marker.
    """
    paths: set[str] = set()
    if not isinstance(data, dict):
        return paths
    for key, value in data.items():
        path = f"{prefix}{key}"
        paths.add(path)
        if path.endswith("generator.params"):
            continue  # free-form
        if isinstance(value, dict):
            paths |= _document_paths(value, f"{path}.")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for item in value:
                paths |= _document_paths(item, f"{path}[].")
    return paths


def test_schema_matches_serialization() -> None:
    """Drift guard: every to_dict path is declared, and vice versa."""
    document = _max_project().to_dict()
    assert _document_paths(document) == schema_paths(PROJECT_SCHEMA)


def test_enum_sources_resolve_and_are_nonempty() -> None:
    for name in ("scales", "roots", "generators", "transitions", "profiles",
                 "styles", "curves", "roles", "automation_targets"):
        assert enum_values(name), name


def test_schema_enums_reference_known_sources() -> None:
    def _walk(specs):
        for spec in specs:
            if spec.enum:
                enum_values(spec.enum)
            _walk(spec.children)

    _walk(PROJECT_SCHEMA)


def test_contract_covers_all_registries() -> None:
    contract = build_contract()
    assert any("midi-art new" in step and "--json" in step for step in contract["workflow"])
    assert set(contract["generators"]) == set(GENERATORS)
    assert set(contract["transitions"]) == set(TRANSITIONS)
    assert set(contract["styles"]) == set(STYLES)
    assert set(contract["profiles"]) == set(PROFILES)
    assert set(contract["enums"]["automation_targets"]) == set(AUTOMATION_TARGETS)
    for info in contract["profiles"].values():
        assert info["description"]
    for info in contract["transitions"].values():
        assert info["description"]


def test_resolve_params_defaults_and_coercion() -> None:
    wave = GENERATORS["wave"].definition
    resolved = resolve_params(wave, {})
    assert resolved == {"wavelength_bars": 2.0, "strands": 1}
    resolved = resolve_params(wave, {"wavelength_bars": "3", "strands": 2.0, "typo": 9})
    assert resolved == {"wavelength_bars": 3.0, "strands": 2}
    assert "typo" not in resolved


def test_param_specs_are_well_formed() -> None:
    for generator in GENERATORS.values():
        for spec in generator.definition.params:
            assert spec.type in {"int", "float", "str"}
            assert spec.description
            # The default must survive its own coercion.
            assert resolve_params(generator.definition, {})[spec.name] is not None


def test_contract_text_renders() -> None:
    text = format_contract_text(build_contract())
    assert "Project schema:" in text
    assert "wavelength_bars" in text
    assert "zenith_high_density" in text
