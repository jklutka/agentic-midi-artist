"""Dense MIDI song generation with presets and optional segments."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

import mido

from .generator import create_midi

SCALE_INTERVALS: dict[str, list[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
}

PROGRESSIONS: dict[str, list[int]] = {
    "major": [0, 4, 5, 3],
    "minor": [0, 5, 3, 4],
}

CHANNEL_PROGRAMS = [
    32,
    48,
    0,
    52,
    40,
    24,
    68,
    73,
    5,
    14,
    11,
    33,
    91,
    94,
    52,
    19,
]

TICKS_PER_BEAT = 480
BEATS_PER_BAR = 4
BAR_TICKS = TICKS_PER_BEAT * BEATS_PER_BAR


@dataclass(frozen=True)
class DenseSongPreset:
    """Descriptor for a UI preset and its rendering intent."""

    key: str
    label: str
    description: str
    zenith_tip: str
    channel_count: int
    harmony_layers: int
    lead_mode: str
    ornament_rate: float
    note_length_scale: float


@dataclass(frozen=True)
class DenseSongSegment:
    """A section of a generated MIDI song."""

    bars: int = 16
    preset: str = "dense_but_musical"
    density: float = 0.75
    tempo_bpm: int = 132
    root: int = 60
    scale_type: str = "minor"


DENSE_SONG_PRESETS: dict[str, DenseSongPreset] = {
    "dense_but_musical": DenseSongPreset(
        key="dense_but_musical",
        label="Dense but musical",
        description="Structured density with a clear bass anchor and repeating motif.",
        zenith_tip="Good with the default Classic or MidiTrail+ plugin.",
        channel_count=3,
        harmony_layers=1,
        lead_mode="stable",
        ornament_rate=0.25,
        note_length_scale=1.0,
    ),
    "black_midi_wall": DenseSongPreset(
        key="black_midi_wall",
        label="Black MIDI wall",
        description="Heavy overlap, stacked harmony, and more notes per bar.",
        zenith_tip="Best with MidiTrail+ or Black-Midi-Render, using shorter screen time.",
        channel_count=4,
        harmony_layers=2,
        lead_mode="stable",
        ornament_rate=0.9,
        note_length_scale=0.55,
    ),
    "channel_color_storm": DenseSongPreset(
        key="channel_color_storm",
        label="Channel-color storm",
        description="Distributes the texture across many channels for color variation.",
        zenith_tip="Best with a plugin or palette that visibly maps MIDI channels to colors.",
        channel_count=12,
        harmony_layers=1,
        lead_mode="rotating",
        ornament_rate=0.7,
        note_length_scale=0.8,
    ),
    "hypnotic_wave": DenseSongPreset(
        key="hypnotic_wave",
        label="Hypnotic wave",
        description="Slow sweeping clusters that pulse across the keyboard in repeating waves.",
        zenith_tip="Good for long-form motion with a trail-style plugin and higher persistence.",
        channel_count=16,
        harmony_layers=3,
        lead_mode="wave",
        ornament_rate=0.88,
        note_length_scale=0.45,
    ),
    "ultra_dense": DenseSongPreset(
        key="ultra_dense",
        label="Ultra dense",
        description="All channels active, maximum overlap, and the shortest note grid.",
        zenith_tip="Use with MidiTrail+ or Black-Midi-Render if you want a wall of motion.",
        channel_count=16,
        harmony_layers=4,
        lead_mode="rotating",
        ornament_rate=0.95,
        note_length_scale=0.35,
    ),
}


def _clamp_pitch(pitch: int) -> int:
    return max(0, min(127, pitch))


def _clamp_channel(channel: int) -> int:
    return max(0, min(15, channel))


def _degree_to_pitch(root: int, scale: list[int], degree: int) -> int:
    octave, scale_degree = divmod(degree, len(scale))
    return _clamp_pitch(root + scale[scale_degree] + octave * 12)


def _build_chord(root: int, scale: list[int], degree: int) -> list[int]:
    return [
        _degree_to_pitch(root, scale, degree),
        _degree_to_pitch(root, scale, degree + 2),
        _degree_to_pitch(root, scale, degree + 4),
    ]


def _lead_motif(root: int, scale: list[int], degree: int) -> list[int]:
    pattern = [0, 2, 4, 6, 4, 2, 1, 0]
    return [_degree_to_pitch(root, scale, degree + offset) + 12 for offset in pattern]


def get_dense_song_preset(preset_key: str) -> DenseSongPreset:
    """Return a known preset or raise with a useful list of options."""

    try:
        return DENSE_SONG_PRESETS[preset_key]
    except KeyError as exc:
        allowed = ", ".join(sorted(DENSE_SONG_PRESETS))
        raise ValueError(f"Unknown preset {preset_key!r}. Available presets: {allowed}") from exc


def dense_song_preset_options() -> list[DenseSongPreset]:
    """Return presets in display order for UI controls."""

    return list(DENSE_SONG_PRESETS.values())


def _coerce_segment(segment: DenseSongSegment | dict) -> DenseSongSegment:
    if isinstance(segment, DenseSongSegment):
        return segment
    return DenseSongSegment(
        bars=int(segment.get("bars", 16)),
        preset=str(segment.get("preset", "dense_but_musical")),
        density=float(segment.get("density", 0.75)),
        tempo_bpm=int(segment.get("tempo_bpm", 132)),
        root=int(segment.get("root", 60)),
        scale_type=str(segment.get("scale_type", "minor")),
    )


def _program_messages() -> list[mido.Message]:
    return [
        mido.Message("program_change", channel=channel, program=program)
        for channel, program in enumerate(CHANNEL_PROGRAMS)
    ]


def _compose_segment_notes(
    segment: DenseSongSegment,
    rng: random.Random,
    start_tick: int,
    global_bar_offset: int,
) -> list[dict]:
    if segment.scale_type not in SCALE_INTERVALS:
        allowed = ", ".join(sorted(SCALE_INTERVALS))
        raise ValueError(f"scale_type must be one of: {allowed}")

    preset_config = get_dense_song_preset(segment.preset)
    eighth = int((TICKS_PER_BEAT // 2) * preset_config.note_length_scale)
    sixteenth = max(1, int((TICKS_PER_BEAT // 4) * preset_config.note_length_scale))
    density = max(0.0, segment.density)
    density_tier = int(density)

    scale = SCALE_INTERVALS[segment.scale_type]
    progression = PROGRESSIONS[segment.scale_type]
    total_channels = max(1, min(16, preset_config.channel_count))
    lead_channels = max(1, total_channels - 2)
    is_hypnotic_wave = preset_config.key == "hypnotic_wave"

    notes: list[dict] = []
    lead_motif_cache: dict[int, list[int]] = {}

    for bar in range(segment.bars):
        absolute_bar = global_bar_offset + bar
        bar_start = start_tick + bar * BAR_TICKS
        degree = progression[absolute_bar % len(progression)]
        chord = _build_chord(segment.root, scale, degree)
        phrase_index = absolute_bar // 4
        if phrase_index not in lead_motif_cache:
            motif = _lead_motif(segment.root, scale, degree)
            shift = rng.choice([0, 1, 2, 3])
            lead_motif_cache[phrase_index] = motif[shift:] + motif[:shift]
        motif = lead_motif_cache[phrase_index]

        bass_root = _clamp_pitch(max(24, chord[0] - 12))
        bass_fifth = _clamp_pitch(max(24, chord[2] - 12))
        bass_note = bass_root if absolute_bar % 2 == 0 else bass_fifth
        bass_duration = BAR_TICKS if absolute_bar % 4 == 3 else BAR_TICKS // 2
        notes.append(
            {
                "pitch": bass_note,
                "velocity": 86 + rng.randint(-6, 6),
                "start_tick": bar_start,
                "duration_ticks": bass_duration,
                "channel": 0,
            }
        )

        if density >= 0.4 or absolute_bar % 2 == 0:
            notes.append(
                {
                    "pitch": bass_note + 7,
                    "velocity": 62 + rng.randint(-5, 5),
                    "start_tick": bar_start + TICKS_PER_BEAT * 2,
                    "duration_ticks": TICKS_PER_BEAT,
                    "channel": 0,
                }
            )

        for beat in range(BEATS_PER_BAR):
            beat_start = bar_start + beat * TICKS_PER_BEAT
            chord_index = beat % len(chord)
            harmony_channel = 1
            if preset_config.key == "channel_color_storm":
                harmony_channel = 1 + ((absolute_bar + beat) % lead_channels)

            notes.append(
                {
                    "pitch": _clamp_pitch(chord[chord_index] + 12),
                    "velocity": 72 + (10 if beat == 0 else 0) + rng.randint(-8, 8),
                    "start_tick": beat_start,
                    "duration_ticks": eighth + (sixteenth if beat in (0, 2) else 0),
                    "channel": harmony_channel,
                }
            )

            if density > 0.25:
                notes.append(
                    {
                        "pitch": _clamp_pitch(chord[(chord_index + 1) % len(chord)] + 12),
                        "velocity": 58 + rng.randint(-6, 6),
                        "start_tick": beat_start + eighth,
                        "duration_ticks": eighth,
                        "channel": harmony_channel if preset_config.harmony_layers == 1 else 2,
                    }
                )

            if density > 0.55 or preset_config.key == "black_midi_wall":
                notes.append(
                    {
                        "pitch": _clamp_pitch(chord[(chord_index + 2) % len(chord)] + 24),
                        "velocity": 52 + rng.randint(-6, 6),
                        "start_tick": beat_start + sixteenth,
                        "duration_ticks": max(1, int(sixteenth * 0.75)),
                        "channel": 2 if total_channels > 2 else harmony_channel,
                    }
                )

            for layer in range(1, density_tier):
                channel = _clamp_channel((harmony_channel + layer) % total_channels)
                layer_pitch = _clamp_pitch(
                    chord[(chord_index + layer) % len(chord)] + 12 * (layer + 1)
                )
                notes.append(
                    {
                        "pitch": layer_pitch,
                        "velocity": 46 + rng.randint(-6, 6),
                        "start_tick": beat_start + max(1, sixteenth // (layer + 1)),
                        "duration_ticks": max(1, int((sixteenth * 0.75) / (layer + 1))),
                        "channel": channel,
                    }
                )

        lead_step = TICKS_PER_BEAT // 2
        for step, pitch in enumerate(motif):
            lead_start = bar_start + step * lead_step
            pitch_variation = rng.choice([-12, 0, 0, 12]) if density > 0.6 else 0
            if preset_config.key == "channel_color_storm":
                pitch_variation = rng.choice([-12, -12, 0, 0, 12, 12])
            if is_hypnotic_wave:
                pitch_variation = int(12 * math.sin((absolute_bar * 0.35) + (step * 0.6)))
            lead_pitch = max(48, min(96, pitch + pitch_variation))
            if (
                not is_hypnotic_wave
                and step % 2 == 1
                and density < 0.35
                and rng.random() < 0.35
            ):
                continue
            if preset_config.lead_mode == "rotating":
                lead_channel = 2 + ((absolute_bar * 8 + step) % lead_channels)
            elif is_hypnotic_wave:
                lead_channel = (absolute_bar + step) % total_channels
            else:
                lead_channel = 2 if total_channels > 2 else 1
            notes.append(
                {
                    "pitch": lead_pitch,
                    "velocity": 78 + rng.randint(-10, 10),
                    "start_tick": lead_start,
                    "duration_ticks": int(
                        (lead_step + (sixteenth if step % 4 == 0 else 0))
                        * (0.75 if is_hypnotic_wave else preset_config.note_length_scale)
                    ),
                    "channel": _clamp_channel(lead_channel),
                }
            )

            for layer in range(1, density_tier):
                if preset_config.lead_mode == "rotating":
                    extra_channel = _clamp_channel(
                        2 + ((absolute_bar * 8 + step + layer) % lead_channels)
                    )
                else:
                    extra_channel = _clamp_channel((lead_channel + layer) % total_channels)
                notes.append(
                    {
                        "pitch": _clamp_pitch(lead_pitch + 12 * layer),
                        "velocity": 68 + rng.randint(-8, 8),
                        "start_tick": lead_start + max(1, sixteenth // 2),
                        "duration_ticks": max(
                            1,
                            int(
                                (lead_step + (sixteenth if step % 4 == 0 else 0))
                                * preset_config.note_length_scale
                                * 0.5
                            ),
                        ),
                        "channel": extra_channel,
                    }
                )

        if is_hypnotic_wave:
            wave_spacing = max(30, TICKS_PER_BEAT // 8)
            wave_steps = max(16, 12 + int(density * 2))
            wave_span = 18 + min(30, int(density * 1.5))
            wave_base = segment.root + 12 + int(4 * math.sin(absolute_bar * 0.2))
            for step in range(wave_steps):
                phase = (absolute_bar * 0.45) + (step * 0.45)
                wave_pitch = _clamp_pitch(
                    wave_base
                    + int(wave_span * math.sin(phase))
                    + int(6 * math.sin(phase * 0.5))
                )
                wave_channel = (absolute_bar + step) % total_channels
                notes.append(
                    {
                        "pitch": wave_pitch,
                        "velocity": 60 + rng.randint(-10, 10),
                        "start_tick": bar_start + step * wave_spacing,
                        "duration_ticks": max(1, int(wave_spacing * 1.8)),
                        "channel": wave_channel,
                    }
                )
                if density > 1.0:
                    notes.append(
                        {
                            "pitch": _clamp_pitch(wave_pitch + 7),
                            "velocity": 48 + rng.randint(-8, 8),
                            "start_tick": bar_start + step * wave_spacing + wave_spacing // 2,
                            "duration_ticks": max(1, int(wave_spacing * 1.5)),
                            "channel": _clamp_channel(wave_channel + 1),
                        }
                    )

        if density > 0.7 or preset_config.key != "dense_but_musical":
            embellishment_steps = [0, 2, 5, 7]
            for idx, step in enumerate(embellishment_steps):
                ornament_rate = min(
                    0.98,
                    preset_config.ornament_rate + max(0.0, density - 1.0) * 0.15,
                )
                if rng.random() < (1.0 - ornament_rate):
                    continue
                embellishment_channel = _clamp_channel(
                    2 + ((absolute_bar + step + idx) % max(1, total_channels - 2))
                )
                notes.append(
                    {
                        "pitch": _clamp_pitch(motif[step] + (12 if idx % 2 == 0 else 0)),
                        "velocity": 48 + rng.randint(-6, 6),
                        "start_tick": bar_start + step * lead_step + sixteenth,
                        "duration_ticks": max(1, int(sixteenth * preset_config.note_length_scale)),
                        "channel": embellishment_channel if total_channels > 2 else 0,
                    }
                )

    return notes


def create_segmented_dense_song(
    output_path: str | Path,
    segments: list[DenseSongSegment | dict],
    *,
    seed: int | None = None,
) -> Path:
    """Create a dense MIDI song from multiple parameter segments."""

    if not segments:
        raise ValueError("At least one segment is required.")

    rng = random.Random(seed)
    coerced_segments = [_coerce_segment(segment) for segment in segments]
    notes: list[dict] = []
    timed_messages: list[tuple[int, mido.MetaMessage]] = []
    current_tick = 0
    current_bar = 0

    for index, segment in enumerate(coerced_segments):
        if segment.bars <= 0:
            raise ValueError("Segment bars must be greater than zero.")
        if index > 0:
            timed_messages.append(
                (
                    current_tick,
                    mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(segment.tempo_bpm)),
                )
            )
        notes.extend(_compose_segment_notes(segment, rng, current_tick, current_bar))
        current_tick += segment.bars * BAR_TICKS
        current_bar += segment.bars

    return create_midi(
        notes,
        output_path,
        ticks_per_beat=TICKS_PER_BEAT,
        tempo=mido.bpm2tempo(coerced_segments[0].tempo_bpm),
        start_messages=_program_messages(),
        timed_messages=timed_messages,
    )


def create_dense_song(
    output_path: str | Path,
    *,
    preset: str = "dense_but_musical",
    bars: int = 16,
    tempo_bpm: int = 132,
    root: int = 60,
    scale_type: str = "minor",
    density: float = 0.75,
    seed: int | None = None,
) -> Path:
    """Create a dense but structured MIDI song."""

    return create_segmented_dense_song(
        output_path,
        [
            DenseSongSegment(
                bars=bars,
                preset=preset,
                density=density,
                tempo_bpm=tempo_bpm,
                root=root,
                scale_type=scale_type,
            )
        ],
        seed=seed,
    )
