"""Preview geometry: everything a preview needs, independent of any UI toolkit.

Answers the iteration questions without rendering in Zenith: is the
composition balanced, is one area too dense, are transitions visible, does
the register expand as intended, does the climax land on time?
"""

from __future__ import annotations

from dataclasses import dataclass

from ..composition.composer import Performance

# One color per MIDI channel, mirroring Zenith's channel-to-color behavior.
CHANNEL_COLORS: tuple[str, ...] = (
    "#5b8def", "#e0653a", "#3fae6a", "#c94f7c", "#8f6fd8", "#d1a23c",
    "#38b6b6", "#b8544d", "#7a9e3b", "#d16fb0", "#4f7dc9", "#c97b4f",
    "#5bbf8f", "#a05fd1", "#bfae3f", "#d14f4f",
)

INTENSITY_SAMPLES = 17
POLYPHONY_STEP_BEATS = 0.5


@dataclass(frozen=True)
class PreviewNote:
    pitch: int
    start: float
    end: float
    channel: int


@dataclass(frozen=True)
class ScenePreview:
    name: str
    start_beat: float
    end_beat: float
    intensity_points: tuple[tuple[float, float], ...]  # (absolute beat, intensity 0..1)


@dataclass(frozen=True)
class PreviewData:
    duration_beats: float
    beats_per_bar: int
    pitch_low: int
    pitch_high: int
    notes: tuple[PreviewNote, ...]
    total_notes: int
    sampled: bool
    density_per_bar: tuple[int, ...]
    peak_density_bar: int
    polyphony: tuple[tuple[float, int], ...]  # (beat, active notes) samples
    peak_polyphony: int
    peak_polyphony_beat: float
    scenes: tuple[ScenePreview, ...]


def build_preview(performance: Performance, max_notes: int = 20_000) -> PreviewData:
    """Reduce a performance to drawable preview data.

    Very large performances are deterministically thinned to ``max_notes``
    for drawing; density and polyphony are always computed from the full set.
    """
    notes = performance.notes
    beats_per_bar = performance.project.music.beats_per_bar
    duration = performance.duration_beats or max((n.end for n in notes), default=1.0)

    density = _density_per_bar(notes, beats_per_bar, duration)
    polyphony, peak, peak_beat = _polyphony_samples(notes, duration)

    sampled = len(notes) > max_notes
    drawable = notes
    if sampled:
        stride = len(notes) / max_notes
        drawable = [notes[int(i * stride)] for i in range(max_notes)]

    scenes = []
    for span in performance.scene_spans:
        scene = next(s for s in performance.project.scenes if s.name == span.name)
        span_beats = span.end_beat - span.start_beat
        points = tuple(
            (
                span.start_beat + span_beats * (i / (INTENSITY_SAMPLES - 1)),
                scene.intent.intensity_at(i / (INTENSITY_SAMPLES - 1)),
            )
            for i in range(INTENSITY_SAMPLES)
        )
        scenes.append(ScenePreview(span.name, span.start_beat, span.end_beat, points))

    return PreviewData(
        duration_beats=duration,
        beats_per_bar=beats_per_bar,
        pitch_low=min((n.pitch for n in notes), default=21),
        pitch_high=max((n.pitch for n in notes), default=108),
        notes=tuple(PreviewNote(n.pitch, n.start, n.end, n.channel) for n in drawable),
        total_notes=len(notes),
        sampled=sampled,
        density_per_bar=density,
        peak_density_bar=max(range(len(density)), key=density.__getitem__) if density else 0,
        polyphony=polyphony,
        peak_polyphony=peak,
        peak_polyphony_beat=peak_beat,
        scenes=tuple(scenes),
    )


def _density_per_bar(notes, beats_per_bar: int, duration: float) -> tuple[int, ...]:
    bars = max(1, int(duration // beats_per_bar) + (1 if duration % beats_per_bar else 0))
    counts = [0] * bars
    for note in notes:
        bar = int(note.start // beats_per_bar)
        if 0 <= bar < bars:
            counts[bar] += 1
    return tuple(counts)


def _polyphony_samples(
    notes, duration: float
) -> tuple[tuple[tuple[float, int], ...], int, float]:
    """Active-note counts on a fixed beat grid, plus the exact instantaneous peak.

    The curve is sampled for drawing; the peak is tracked event-by-event so
    it is never underreported by the sampling grid.
    """
    events: list[tuple[float, int]] = []
    for note in notes:
        events.append((note.start, 1))
        events.append((note.end, -1))
    events.sort()

    samples: list[tuple[float, int]] = []
    active = 0
    peak = 0
    peak_beat = 0.0
    index = 0
    beat = 0.0
    while beat <= duration + 1e-9:
        while index < len(events) and events[index][0] <= beat:
            active += events[index][1]
            if active > peak:
                peak = active
                peak_beat = events[index][0]
            index += 1
        samples.append((beat, active))
        beat += POLYPHONY_STEP_BEATS
    while index < len(events):
        active += events[index][1]
        if active > peak:
            peak = active
            peak_beat = events[index][0]
        index += 1
    return tuple(samples), peak, peak_beat
