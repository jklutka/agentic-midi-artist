"""Performance metrics: every generated performance produces a report."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from ..composition.composer import Performance


@dataclass(frozen=True)
class PerformanceReport:
    total_notes: int
    duration_beats: float
    duration_seconds: float
    avg_notes_per_second: float
    max_notes_per_second: int
    avg_polyphony: float
    peak_polyphony: int
    pitch_min: int
    pitch_max: int
    avg_note_duration_beats: float
    channel_count: int
    notes_by_role: dict[str, int]
    notes_by_scene: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_notes": self.total_notes,
            "duration_beats": round(self.duration_beats, 3),
            "duration_seconds": round(self.duration_seconds, 2),
            "avg_notes_per_second": round(self.avg_notes_per_second, 2),
            "max_notes_per_second": self.max_notes_per_second,
            "avg_polyphony": round(self.avg_polyphony, 2),
            "peak_polyphony": self.peak_polyphony,
            "pitch_range": [self.pitch_min, self.pitch_max],
            "avg_note_duration_beats": round(self.avg_note_duration_beats, 4),
            "channel_count": self.channel_count,
            "notes_by_role": self.notes_by_role,
            "notes_by_scene": self.notes_by_scene,
        }

    def format_text(self) -> str:
        lines = [
            f"Notes:            {self.total_notes:,}",
            f"Duration:         {self.duration_seconds:.1f}s ({self.duration_beats:.0f} beats)",
            f"Notes/sec:        avg {self.avg_notes_per_second:.1f}, "
            f"max {self.max_notes_per_second}",
            f"Polyphony:        avg {self.avg_polyphony:.1f}, peak {self.peak_polyphony}",
            f"Pitch range:      {self.pitch_min}..{self.pitch_max}",
            f"Avg note length:  {self.avg_note_duration_beats:.3f} beats",
            f"Channels used:    {self.channel_count}",
        ]
        if self.notes_by_scene:
            lines.append("Scene note counts:")
            for scene, count in self.notes_by_scene.items():
                lines.append(f"  {scene}: {count:,}")
        return "\n".join(lines)


def beats_to_seconds(beat: float, tempo_events: list[tuple[float, float]]) -> float:
    """Convert a beat position to seconds through a stepwise tempo map."""
    events = sorted(tempo_events) or [(0.0, 120.0)]
    if events[0][0] > 0:
        events.insert(0, (0.0, 120.0))
    seconds = 0.0
    for (start, bpm), nxt in zip(events, events[1:] + [(float("inf"), 0.0)]):
        if beat <= start:
            break
        segment_end = min(beat, nxt[0])
        seconds += (segment_end - start) * 60.0 / bpm
    return seconds


def analyze(performance: Performance) -> PerformanceReport:
    notes = performance.notes
    tempo = performance.tempo_events
    duration_beats = performance.duration_beats or max((n.end for n in notes), default=0.0)
    duration_seconds = beats_to_seconds(duration_beats, tempo)

    if not notes:
        return PerformanceReport(
            total_notes=0, duration_beats=duration_beats, duration_seconds=duration_seconds,
            avg_notes_per_second=0.0, max_notes_per_second=0, avg_polyphony=0.0,
            peak_polyphony=0, pitch_min=0, pitch_max=0, avg_note_duration_beats=0.0,
            channel_count=0, notes_by_role={}, notes_by_scene={},
        )

    starts_seconds = [beats_to_seconds(note.start, tempo) for note in notes]
    per_second = Counter(int(s) for s in starts_seconds)
    max_per_second = max(per_second.values())

    peak, avg_polyphony = _polyphony(notes, duration_beats)

    notes_by_scene: dict[str, int] = {}
    for span in performance.scene_spans:
        notes_by_scene[span.name] = sum(
            1 for note in notes if span.start_beat <= note.start < span.end_beat
        )

    return PerformanceReport(
        total_notes=len(notes),
        duration_beats=duration_beats,
        duration_seconds=duration_seconds,
        avg_notes_per_second=len(notes) / duration_seconds if duration_seconds else 0.0,
        max_notes_per_second=max_per_second,
        avg_polyphony=avg_polyphony,
        peak_polyphony=peak,
        pitch_min=min(note.pitch for note in notes),
        pitch_max=max(note.pitch for note in notes),
        avg_note_duration_beats=sum(note.duration for note in notes) / len(notes),
        channel_count=len({note.channel for note in notes}),
        notes_by_role=dict(Counter(note.role.value for note in notes)),
        notes_by_scene=notes_by_scene,
    )


def _polyphony(notes: list, duration_beats: float) -> tuple[int, float]:
    """Peak and time-weighted average concurrent notes, via an event sweep."""
    events: list[tuple[float, int]] = []
    for note in notes:
        events.append((note.start, 1))
        events.append((note.end, -1))
    events.sort()

    active = 0
    peak = 0
    weighted = 0.0
    last_beat = 0.0
    for beat, delta in events:
        weighted += active * (beat - last_beat)
        active += delta
        peak = max(peak, active)
        last_beat = beat
    total = max(duration_beats, last_beat, 1e-9)
    return peak, weighted / total
