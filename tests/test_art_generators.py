"""Tests for generator plugins: bounds, determinism, intensity response."""

import random

import pytest

from midi_art.domain.layer import GeneratorConfig, Layer, LayerRole
from midi_art.domain.scene import SceneIntent
from midi_art.generators import GENERATORS, GenerationContext, get_generator


def make_context(seed: int = 1, intensity: float = 0.5, duration: float = 16.0):
    intent = SceneIntent(
        intensity_start=intensity,
        intensity_end=intensity,
        register_center=64,
        register_span_start=36,
        register_span_end=36,
    )
    layer = Layer("test", LayerRole.TEXTURE, GeneratorConfig("pulse"))
    return GenerationContext(
        rng=random.Random(seed),
        scene_duration=duration,
        beats_per_bar=4,
        root=57,
        scale="minor",
        layer=layer,
        intent_intensity_at=lambda beat: intent.intensity_at(beat / duration),
        intent_register_at=lambda beat: intent.register_at(beat / duration),
        order=0.8,
        harmonic_stability=0.9,
    )


@pytest.mark.parametrize("name", sorted(GENERATORS))
def test_generators_stay_within_scene_and_midi_bounds(name: str):
    generator = get_generator(name)
    notes = generator.generate(make_context(), {})
    assert notes, f"{name} produced no notes at moderate intensity"
    for note in notes:
        assert 0 <= note.pitch <= 127
        assert 1 <= note.velocity <= 127
        assert note.start >= 0
        assert note.start < 16.0 + 1e-6
        assert note.duration > 0


@pytest.mark.parametrize("name", sorted(GENERATORS))
def test_generators_are_deterministic(name: str):
    generator = get_generator(name)
    first = generator.generate(make_context(seed=7), {})
    second = generator.generate(make_context(seed=7), {})
    assert first == second


def test_cloud_density_scales_with_intensity():
    cloud = get_generator("cloud")
    sparse = cloud.generate(make_context(intensity=0.15), {})
    dense = cloud.generate(make_context(intensity=0.95), {})
    assert len(dense) > len(sparse) * 2


def test_mirror_produces_symmetric_pairs():
    mirror = get_generator("mirror")
    notes = mirror.generate(make_context(), {})
    mirrored = [note for note in notes if "mirror" in note.tags]
    assert mirrored, "mirror generator produced no reflected notes"


def test_unknown_generator_raises():
    with pytest.raises(ValueError, match="Unknown generator"):
        get_generator("does_not_exist")
