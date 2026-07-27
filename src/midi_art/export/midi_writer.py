"""MIDI serialization: the final stage, deliberately kept at the edge of the system.

Converts beat-timed :class:`NoteEvent` lists into a single-track Standard MIDI
File, applying the export profile's Zenith-safety policies (minimum note
duration, overlapping same-pitch resolution, hard note-count cap).
"""

from __future__ import annotations

from pathlib import Path

import mido

from ..domain.note_event import NoteEvent
from .zenith_profile import ZenithExportSettings

TICKS_PER_BEAT = 480


class ExportLimitError(RuntimeError):
    """Raised when a performance exceeds the profile's hard note-count cap."""


def write_midi(
    notes: list[NoteEvent],
    output_path: str | Path,
    settings: ZenithExportSettings,
    *,
    tempo_events: list[tuple[float, float]] | None = None,
    ticks_per_beat: int = TICKS_PER_BEAT,
) -> Path:
    """Serialize notes to a .mid file.

    Args:
        notes: Beat-timed note events (channels already allocated).
        output_path: Destination .mid path.
        settings: Export profile policies to enforce.
        tempo_events: (beat, bpm) tempo changes; a default is inserted at beat 0.
    """
    if len(notes) > settings.max_total_notes:
        raise ExportLimitError(
            f"{len(notes)} notes exceeds the {settings.name} profile cap of "
            f"{settings.max_total_notes}. Lower scene intensity/density or pick a "
            "higher-density export profile."
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    spans = _note_spans(notes, ticks_per_beat, settings)

    # Event priority at equal ticks: note_off(0) < tempo(1) < note_on(2),
    # so re-struck pitches are released before they re-trigger.
    events: list[tuple[int, int, mido.Message | mido.MetaMessage]] = []
    for pitch, velocity, channel, on_tick, off_tick in spans:
        events.append(
            (on_tick, 2, mido.Message("note_on", note=pitch, velocity=velocity, channel=channel))
        )
        events.append(
            (off_tick, 0, mido.Message("note_off", note=pitch, velocity=0, channel=channel))
        )

    tempo_events = list(tempo_events or [])
    if not tempo_events or tempo_events[0][0] > 0:
        tempo_events.insert(0, (0.0, 120.0))
    for beat, bpm in tempo_events:
        tick = round(beat * ticks_per_beat)
        events.append((tick, 1, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm))))

    events.sort(key=lambda e: (e[0], e[1]))

    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    current_tick = 0
    for tick, _, message in events:
        track.append(message.copy(time=tick - current_tick))
        current_tick = tick

    mid.save(str(output_path))
    return output_path


def _note_spans(
    notes: list[NoteEvent],
    ticks_per_beat: int,
    settings: ZenithExportSettings,
) -> list[tuple[int, int, int, int, int]]:
    """Convert notes to (pitch, velocity, channel, on_tick, off_tick) tuples,
    enforcing minimum duration and resolving same-pitch overlaps."""
    min_ticks = max(1, round(settings.min_note_duration_beats * ticks_per_beat))
    spans: list[tuple[int, int, int, int, int]] = []
    for note in notes:
        note = note.clamped()
        on_tick = round(note.start * ticks_per_beat)
        off_tick = max(on_tick + min_ticks, round(note.end * ticks_per_beat))
        spans.append((note.pitch, note.velocity, note.channel, on_tick, off_tick))

    if not settings.merge_overlapping_same_pitch:
        return spans

    # Two active note_ons on the same pitch+channel produce stuck notes in
    # some renderers: truncate the earlier note at the later one's start,
    # and drop exact duplicates.
    spans.sort(key=lambda s: (s[0], s[2], s[3]))
    resolved: list[tuple[int, int, int, int, int]] = []
    for span in spans:
        if resolved:
            prev = resolved[-1]
            same_voice = prev[0] == span[0] and prev[2] == span[2]
            if same_voice and span[3] <= prev[3]:
                continue  # duplicate strike at the same tick — drop it
            if same_voice and prev[4] > span[3]:
                resolved[-1] = (prev[0], prev[1], prev[2], prev[3], span[3])
        resolved.append(span)
    return resolved
