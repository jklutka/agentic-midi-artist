"""SVG/HTML preview renderer: a self-contained page, no dependencies, no server.

Layout per figure (top to bottom): piano roll with scene boundaries, a
density-per-bar strip with the intensity curve overlaid, and a polyphony
graph with its peak marked.
"""

from __future__ import annotations

import html

from .model import CHANNEL_COLORS, PreviewData

WIDTH = 1100
ROLL_HEIGHT = 380
DENSITY_HEIGHT = 70
POLY_HEIGHT = 70
GAP = 26
MARGIN = 8
PITCH_LOW, PITCH_HIGH = 21, 108

BG = "#101216"
PANEL = "#171a20"
GRID = "#262b33"
TEXT = "#9aa4b2"
ACCENT = "#e8c15a"
POLY_FILL = "#3d6fae"


def render_svg(data: PreviewData) -> str:
    height = MARGIN + ROLL_HEIGHT + GAP + DENSITY_HEIGHT + GAP + POLY_HEIGHT + MARGIN
    beats = max(data.duration_beats, 1e-9)

    def x(beat: float) -> float:
        return MARGIN + (beat / beats) * (WIDTH - 2 * MARGIN)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" style="background:{BG}">'
    ]

    parts += _piano_roll(data, x, MARGIN)
    density_top = MARGIN + ROLL_HEIGHT + GAP
    parts += _density_strip(data, x, density_top)
    poly_top = density_top + DENSITY_HEIGHT + GAP
    parts += _polyphony_graph(data, x, poly_top)

    parts.append("</svg>")
    return "".join(parts)


def _piano_roll(data: PreviewData, x, top: float) -> list[str]:
    parts = [f'<rect x="{MARGIN}" y="{top}" width="{WIDTH - 2 * MARGIN}" '
             f'height="{ROLL_HEIGHT}" fill="{PANEL}"/>']
    span = PITCH_HIGH - PITCH_LOW

    def y(pitch: float) -> float:
        return top + ROLL_HEIGHT * (1.0 - (pitch - PITCH_LOW) / span)

    # Octave gridlines on the Cs.
    for pitch in range(24, PITCH_HIGH, 12):
        parts.append(
            f'<line x1="{MARGIN}" y1="{y(pitch):.1f}" x2="{WIDTH - MARGIN}" '
            f'y2="{y(pitch):.1f}" stroke="{GRID}" stroke-width="1"/>'
        )

    note_height = max(1.6, ROLL_HEIGHT / span)
    for note in data.notes:
        left = x(note.start)
        width = max(1.0, x(note.end) - left)
        color = CHANNEL_COLORS[note.channel % len(CHANNEL_COLORS)]
        parts.append(
            f'<rect x="{left:.1f}" y="{y(note.pitch) - note_height / 2:.1f}" '
            f'width="{width:.1f}" height="{note_height:.1f}" fill="{color}" '
            f'fill-opacity="0.85"/>'
        )

    for scene in data.scenes:
        left = x(scene.start_beat)
        parts.append(
            f'<line x1="{left:.1f}" y1="{top}" x2="{left:.1f}" y2="{top + ROLL_HEIGHT}" '
            f'stroke="{TEXT}" stroke-width="1" stroke-dasharray="4 4" stroke-opacity="0.6"/>'
        )
        parts.append(
            f'<text x="{left + 5:.1f}" y="{top + 14}" fill="{TEXT}" '
            f'font-family="Segoe UI, sans-serif" font-size="12">{html.escape(scene.name)}</text>'
        )
    if data.sampled:
        parts.append(
            f'<text x="{WIDTH - MARGIN - 4}" y="{top + 14}" fill="{TEXT}" text-anchor="end" '
            f'font-family="Segoe UI, sans-serif" font-size="11">'
            f'showing {len(data.notes):,} of {data.total_notes:,} notes</text>'
        )
    return parts


def _density_strip(data: PreviewData, x, top: float) -> list[str]:
    parts = [
        f'<rect x="{MARGIN}" y="{top}" width="{WIDTH - 2 * MARGIN}" '
        f'height="{DENSITY_HEIGHT}" fill="{PANEL}"/>',
        _label(MARGIN + 4, top - 6, "density per bar / intensity curve"),
    ]
    peak = max(data.density_per_bar) if data.density_per_bar else 1
    bar_beats = data.beats_per_bar
    for bar, count in enumerate(data.density_per_bar):
        if count == 0:
            continue
        left = x(bar * bar_beats)
        width = max(1.0, x((bar + 1) * bar_beats) - left - 0.5)
        h = (count / peak) * (DENSITY_HEIGHT - 4)
        color = ACCENT if bar == data.peak_density_bar else "#55606e"
        parts.append(
            f'<rect x="{left:.1f}" y="{top + DENSITY_HEIGHT - h:.1f}" width="{width:.1f}" '
            f'height="{h:.1f}" fill="{color}" fill-opacity="0.9"/>'
        )

    points = []
    for scene in data.scenes:
        for beat, intensity in scene.intensity_points:
            points.append(f"{x(beat):.1f},{top + DENSITY_HEIGHT * (1 - intensity):.1f}")
    if points:
        parts.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{ACCENT}" '
            f'stroke-width="1.6" stroke-opacity="0.9"/>'
        )
    return parts


def _polyphony_graph(data: PreviewData, x, top: float) -> list[str]:
    parts = [
        f'<rect x="{MARGIN}" y="{top}" width="{WIDTH - 2 * MARGIN}" '
        f'height="{POLY_HEIGHT}" fill="{PANEL}"/>',
        _label(MARGIN + 4, top - 6, f"polyphony (peak {data.peak_polyphony})"),
    ]
    peak = max(data.peak_polyphony, 1)
    points = [f"{x(0):.1f},{top + POLY_HEIGHT:.1f}"]
    for beat, active in data.polyphony:
        points.append(f"{x(beat):.1f},{top + POLY_HEIGHT * (1 - active / peak):.1f}")
    points.append(f"{x(data.duration_beats):.1f},{top + POLY_HEIGHT:.1f}")
    parts.append(
        f'<polygon points="{" ".join(points)}" fill="{POLY_FILL}" fill-opacity="0.55" '
        f'stroke="{POLY_FILL}" stroke-width="1"/>'
    )
    peak_x = x(data.peak_polyphony_beat)
    parts.append(
        f'<line x1="{peak_x:.1f}" y1="{top}" x2="{peak_x:.1f}" y2="{top + POLY_HEIGHT}" '
        f'stroke="{ACCENT}" stroke-width="1" stroke-dasharray="2 3"/>'
    )
    return parts


def _label(x_pos: float, y_pos: float, text: str) -> str:
    return (
        f'<text x="{x_pos}" y="{y_pos}" fill="{TEXT}" '
        f'font-family="Segoe UI, sans-serif" font-size="11">{html.escape(text)}</text>'
    )


def render_html(
    title: str,
    sections: list[tuple[str, PreviewData, str, list[str]]],
) -> str:
    """Build a standalone preview page.

    Each section is (heading, preview data, report text, issue strings) —
    multiple sections give side-by-side variation comparison.
    """
    body: list[str] = [f"<h1>{html.escape(title)}</h1>"]
    for heading, data, report_text, issues in sections:
        body.append(f"<section><h2>{html.escape(heading)}</h2>")
        body.append(render_svg(data))
        body.append(f"<pre>{html.escape(report_text)}</pre>")
        if issues:
            body.append("<ul>")
            body.extend(f"<li>{html.escape(issue)}</li>" for issue in issues)
            body.append("</ul>")
        body.append("</section>")

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        f"body{{background:{BG};color:#d5dbe3;font-family:'Segoe UI',sans-serif;"
        "margin:24px}}"
        "h1{font-size:20px}h2{font-size:15px;color:#b8c1cc;margin:28px 0 8px}"
        f"pre{{background:{PANEL};padding:12px;font-size:12px;line-height:1.5}}"
        f"ul{{background:{PANEL};padding:12px 12px 12px 32px;font-size:12px}}"
        "svg{max-width:100%;height:auto}"
        "</style></head><body>"
        + "".join(body)
        + "</body></html>"
    )
