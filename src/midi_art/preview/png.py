"""PNG preview renderer: a raster image an AI agent (or human) can look at.

Draws the same three panels as the SVG/HTML preview — piano roll with
labeled scene boundaries, density-per-bar with the intensity curve, and the
polyphony graph — from the same toolkit-independent ``PreviewData``.
Requires Pillow (the only optional heavyweight dependency).
"""

from __future__ import annotations

from pathlib import Path

from .model import CHANNEL_COLORS, PreviewData

BG = "#101216"
PANEL = "#171a20"
GRID = "#262b33"
TEXT = "#9aa4b2"
ACCENT = "#e8c15a"
POLY_FILL = "#3d6fae"
PITCH_LOW, PITCH_HIGH = 21, 108


def render_png(
    data: PreviewData,
    path: str | Path,
    *,
    width: int = 1600,
    height: int = 900,
    title: str = "",
) -> Path:
    """Render the preview to a PNG file and return its path."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:  # pragma: no cover - exercised only without Pillow
        raise RuntimeError(
            "PNG preview requires Pillow — install it with: pip install pillow"
        ) from None

    try:
        font = ImageFont.load_default(size=14)
        small = ImageFont.load_default(size=11)
    except TypeError:  # older Pillow without sizable default font
        font = small = ImageFont.load_default()

    margin = 14
    title_height = 28
    gap = 18
    label_height = 16
    usable = height - title_height - 2 * margin - 2 * gap - 2 * label_height
    roll_height = int(usable * 0.68)
    strip_height = (usable - roll_height) // 2
    left, right = margin, width - margin
    span_x = right - left

    roll_top = margin + title_height
    density_top = roll_top + roll_height + gap + label_height
    poly_top = density_top + strip_height + gap + label_height

    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    beats = max(data.duration_beats, 1e-9)

    def x(beat: float) -> float:
        return left + (beat / beats) * span_x

    def pitch_y(pitch: float) -> float:
        t = (pitch - PITCH_LOW) / (PITCH_HIGH - PITCH_LOW)
        return roll_top + (1.0 - t) * roll_height

    if title:
        # Pillow's default bitmap font lacks some punctuation glyphs.
        draw.text((left, margin), title.replace("—", "-"), fill=TEXT, font=font)
    if data.sampled:
        note_info = f"{data.total_notes:,} notes (drawing {len(data.notes):,})"
    else:
        note_info = f"{data.total_notes:,} notes"
    draw.text((right - draw.textlength(note_info, font=small), margin + 4),
              note_info, fill=TEXT, font=small)

    # --- piano roll ---------------------------------------------------------
    draw.rectangle((left, roll_top, right, roll_top + roll_height), fill=PANEL)
    for c_pitch in range(PITCH_LOW + (12 - PITCH_LOW % 12) % 12, PITCH_HIGH + 1, 12):
        y = pitch_y(c_pitch)
        draw.line((left, y, right, y), fill=GRID)
        draw.text((left + 3, y - 13), f"C{c_pitch // 12 - 1}", fill=GRID, font=small)

    note_height = max(2, int(roll_height / (PITCH_HIGH - PITCH_LOW + 1)))
    for note in data.notes:
        x0 = x(note.start)
        x1 = max(x(note.end), x0 + 1.5)
        y = pitch_y(note.pitch)
        color = CHANNEL_COLORS[note.channel % len(CHANNEL_COLORS)]
        draw.rectangle((x0, y - note_height / 2, x1, y + note_height / 2), fill=color)

    for scene in data.scenes:
        boundary = x(scene.start_beat)
        if scene.start_beat > 0:
            draw.line((boundary, roll_top, boundary, roll_top + roll_height), fill=TEXT)
        bar = int(scene.start_beat // data.beats_per_bar) + 1
        draw.text((boundary + 4, roll_top + 3), f"{scene.name} (bar {bar})",
                  fill=TEXT, font=font)

    # --- density per bar + intensity curve ----------------------------------
    draw.text((left, density_top - label_height),
              "density per bar (yellow line = scene intensity)", fill=TEXT, font=small)
    draw.rectangle((left, density_top, right, density_top + strip_height), fill=PANEL)
    if data.density_per_bar:
        top_count = max(max(data.density_per_bar), 1)
        bar_width = span_x / len(data.density_per_bar)
        for i, count in enumerate(data.density_per_bar):
            if not count:
                continue
            bar_height = (count / top_count) * (strip_height - 2)
            x0 = left + i * bar_width
            fill = ACCENT if i == data.peak_density_bar else POLY_FILL
            draw.rectangle(
                (x0 + 0.5, density_top + strip_height - bar_height,
                 x0 + max(bar_width - 0.5, 1.0), density_top + strip_height),
                fill=fill,
            )
    for scene in data.scenes:
        points = [
            (x(beat), density_top + (1.0 - value) * strip_height)
            for beat, value in scene.intensity_points
        ]
        if len(points) > 1:
            draw.line(points, fill=ACCENT, width=2)

    # --- polyphony ----------------------------------------------------------
    draw.text((left, poly_top - label_height),
              f"polyphony (peak {data.peak_polyphony})", fill=TEXT, font=small)
    draw.rectangle((left, poly_top, right, poly_top + strip_height), fill=PANEL)
    if data.polyphony:
        top_poly = max(data.peak_polyphony, 1)
        polygon = [(left, poly_top + strip_height)]
        polygon += [
            (x(beat), poly_top + (1.0 - active / top_poly) * strip_height)
            for beat, active in data.polyphony
        ]
        polygon.append((x(data.polyphony[-1][0]), poly_top + strip_height))
        draw.polygon(polygon, fill=POLY_FILL)
        peak_x = x(data.peak_polyphony_beat)
        draw.line((peak_x, poly_top, peak_x, poly_top + strip_height), fill=ACCENT)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path
