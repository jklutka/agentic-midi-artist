"""Compact visual summary: judge the shape of a performance without looking.

Answers "does this match the creative brief?" in a couple of hundred tokens:
the per-scene energy arc, register evolution, peaks with scene attribution,
and silent stretches. The cheap inner loop next to the PNG preview.
"""

from __future__ import annotations

from typing import Any

from ..composition.composer import Performance
from .metrics import PerformanceReport

GAP_THRESHOLD_BARS = 2


def build_visual_summary(performance: Performance, report: PerformanceReport) -> dict[str, Any]:
    beats_per_bar = performance.project.music.beats_per_bar
    notes = sorted(performance.notes, key=lambda n: n.start)
    intents = {scene.name: scene.intent for scene in performance.project.scenes}

    scenes: list[dict[str, Any]] = []
    scene_density: list[float] = []
    peak_density = {"bar": 0, "notes": 0, "scene": ""}
    peak_polyphony = {"value": 0, "beat": 0.0, "scene": ""}

    for span in performance.scene_spans:
        span_notes = [n for n in notes if span.start_beat <= n.start < span.end_beat]
        bars = max(1, round((span.end_beat - span.start_beat) / beats_per_bar))
        counts = [0] * bars
        for note in span_notes:
            bar = int((note.start - span.start_beat) // beats_per_bar)
            if 0 <= bar < bars:
                counts[bar] += 1
        avg = len(span_notes) / bars
        scene_density.append(avg)

        local_peak_bar = max(range(bars), key=counts.__getitem__)
        if counts[local_peak_bar] > peak_density["notes"]:
            peak_density = {
                "bar": int(span.start_beat // beats_per_bar) + local_peak_bar,
                "notes": counts[local_peak_bar],
                "scene": span.name,
            }

        poly_peak, poly_beat = _peak_polyphony(span_notes)
        if poly_peak > peak_polyphony["value"]:
            peak_polyphony = {"value": poly_peak, "beat": round(poly_beat, 1),
                              "scene": span.name}

        intent = intents.get(span.name)
        scenes.append({
            "name": span.name,
            "bars": bars,
            "notes": len(span_notes),
            "notes_per_bar": {"min": min(counts), "avg": round(avg, 1), "max": max(counts)},
            "register": (
                [min(n.pitch for n in span_notes), max(n.pitch for n in span_notes)]
                if span_notes else None
            ),
            "peak_polyphony": poly_peak,
            "intensity": (
                [intent.intensity_start, intent.intensity_end] if intent else None
            ),
        })

    top = max(scene_density) if scene_density else 1.0
    density_arc = [round(d / top, 2) if top else 0.0 for d in scene_density]

    return {
        "scenes": scenes,
        "density_arc": density_arc,
        "peak_density": peak_density,
        "peak_polyphony": peak_polyphony,
        "gaps": _gaps(notes, performance, beats_per_bar),
        "register_evolution": " → ".join(
            f"{s['register'][0]}..{s['register'][1]}" if s["register"] else "silent"
            for s in scenes
        ),
    }


def format_summary_text(summary: dict[str, Any]) -> str:
    lines = ["Visual summary:"]
    for scene in summary["scenes"]:
        npb = scene["notes_per_bar"]
        register = (
            f"{scene['register'][0]}..{scene['register'][1]}" if scene["register"] else "silent"
        )
        intensity = (
            f"{scene['intensity'][0]:.2f}→{scene['intensity'][1]:.2f}"
            if scene["intensity"] else "?"
        )
        lines.append(
            f"  {scene['name']:<18} {scene['bars']:>3} bars {scene['notes']:>7,} notes  "
            f"n/bar {npb['min']}/{npb['avg']}/{npb['max']}  reg {register}  "
            f"poly {scene['peak_polyphony']}  int {intensity}"
        )
    lines.append(f"Energy arc:      {', '.join(f'{v:.2f}' for v in summary['density_arc'])}")
    pd = summary["peak_density"]
    lines.append(f"Peak density:    bar {pd['bar']} ({pd['notes']} notes) in {pd['scene']}")
    pp = summary["peak_polyphony"]
    lines.append(f"Peak polyphony:  {pp['value']} at beat {pp['beat']} in {pp['scene']}")
    if summary["gaps"]:
        gaps = "; ".join(
            f"beat {g['start_beat']:g} for {g['beats']:g} beats ({g['scene']})"
            for g in summary["gaps"]
        )
        lines.append(f"Silent gaps:     {gaps}")
    else:
        lines.append("Silent gaps:     none")
    lines.append(f"Register arc:    {summary['register_evolution']}")
    return "\n".join(lines)


def _peak_polyphony(notes: list) -> tuple[int, float]:
    events: list[tuple[float, int]] = []
    for note in notes:
        events.append((note.start, 1))
        events.append((note.end, -1))
    events.sort()
    active = peak = 0
    peak_beat = 0.0
    for beat, delta in events:
        active += delta
        if active > peak:
            peak = active
            peak_beat = beat
    return peak, peak_beat


def _gaps(notes: list, performance: Performance, beats_per_bar: int) -> list[dict[str, Any]]:
    """Silent stretches longer than GAP_THRESHOLD_BARS, with scene attribution."""
    threshold = GAP_THRESHOLD_BARS * beats_per_bar
    gaps: list[dict[str, Any]] = []

    def scene_at(beat: float) -> str:
        for span in performance.scene_spans:
            if span.start_beat <= beat < span.end_beat:
                return span.name
        return performance.scene_spans[-1].name if performance.scene_spans else ""

    cursor = 0.0
    for note in notes:
        if note.start - cursor > threshold:
            gaps.append({
                "start_beat": round(cursor, 1),
                "beats": round(note.start - cursor, 1),
                "scene": scene_at(cursor),
            })
        cursor = max(cursor, note.end)
    if performance.duration_beats - cursor > threshold:
        gaps.append({
            "start_beat": round(cursor, 1),
            "beats": round(performance.duration_beats - cursor, 1),
            "scene": scene_at(cursor),
        })
    return gaps
