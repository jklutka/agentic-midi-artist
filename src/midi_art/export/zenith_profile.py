"""Zenith export profiles: named policies tuned for the renderer, not generic MIDI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ZenithExportSettings:
    """Policy for turning a performance into a Zenith-friendly .mid file.

    Limits are the runaway-generation guard: exceeding ``max_total_notes``
    aborts the export; softer limits surface as validation warnings.
    """

    name: str
    channel_strategy: str = "by_color_group"
    color_group_mapping: dict[str, int] = field(default_factory=dict)
    min_note_duration_beats: float = 0.03
    merge_overlapping_same_pitch: bool = True
    max_total_notes: int = 500_000
    max_notes_per_second: float = 3_000.0
    max_polyphony: int = 400
    description: str = ""


PROFILES: dict[str, ZenithExportSettings] = {
    "zenith_standard": ZenithExportSettings(
        name="zenith_standard",
        description="Safe default — up to 500k notes, 3k notes/s guideline.",
    ),
    "zenith_high_density": ZenithExportSettings(
        name="zenith_high_density",
        min_note_duration_beats=0.02,
        max_total_notes=1_500_000,
        max_notes_per_second=8_000.0,
        max_polyphony=800,
        description="Dense showpieces — up to 1.5M notes, 8k notes/s guideline.",
    ),
    "zenith_extreme_density": ZenithExportSettings(
        name="zenith_extreme_density",
        min_note_duration_beats=0.01,
        max_total_notes=5_000_000,
        max_notes_per_second=30_000.0,
        max_polyphony=4_000,
        description="Black-MIDI territory — up to 5M notes; expect heavy render times.",
    ),
    "zenith_performance_safe": ZenithExportSettings(
        name="zenith_performance_safe",
        min_note_duration_beats=0.05,
        max_total_notes=120_000,
        max_notes_per_second=800.0,
        max_polyphony=128,
        description="Conservative caps for weak GPUs or live playback — 120k notes max.",
    ),
}


def get_profile(name: str) -> ZenithExportSettings:
    try:
        return PROFILES[name]
    except KeyError as exc:
        allowed = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown export profile {name!r}. Available: {allowed}") from exc
