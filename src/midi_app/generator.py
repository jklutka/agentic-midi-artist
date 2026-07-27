"""MIDI file generation utilities using the Mido library."""

from pathlib import Path

import mido


def create_midi(
    notes: list[dict],
    output_path: str | Path,
    ticks_per_beat: int = 480,
    tempo: int = 500000,
    start_messages: list[mido.Message | mido.MetaMessage] | None = None,
    timed_messages: list[tuple[int, mido.Message | mido.MetaMessage]] | None = None,
) -> Path:
    """Create a MIDI file from a list of note events.

    Args:
        notes: List of note dicts with keys: pitch, velocity, start_tick, duration_ticks, channel.
        output_path: Where to save the .mid file.
        ticks_per_beat: Resolution of the MIDI file.
        tempo: Microseconds per beat (500000 = 120 BPM).

    Returns:
        Path to the created MIDI file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    for message in start_messages or []:
        track.append(message.copy(time=0))

    # Convert note list to sorted on/off events
    events = []
    for note in notes:
        pitch = note["pitch"]
        velocity = note.get("velocity", 100)
        channel = note.get("channel", 0)
        start = note["start_tick"]
        end = start + note["duration_ticks"]

        events.append(
            (
                start,
                2,
                mido.Message("note_on", note=pitch, velocity=velocity, channel=channel),
            )
        )
        events.append(
            (
                end,
                0,
                mido.Message("note_off", note=pitch, velocity=0, channel=channel),
            )
        )

    for tick, message in timed_messages or []:
        events.append((tick, 1, message.copy(time=0)))

    events.sort(key=lambda e: (e[0], e[1]))

    current_tick = 0
    for tick, _, message in events:
        delta = tick - current_tick
        track.append(message.copy(time=delta))
        current_tick = tick

    mid.save(str(output_path))
    return output_path


def create_scale(
    output_path: str | Path,
    root: int = 60,
    scale_type: str = "major",
    tempo_bpm: int = 120,
    note_duration_beats: float = 0.5,
) -> Path:
    """Create a MIDI file containing a musical scale.

    Args:
        output_path: Where to save the .mid file.
        root: MIDI note number for the root (60 = middle C).
        scale_type: 'major' or 'minor'.
        tempo_bpm: Tempo in beats per minute.
        note_duration_beats: Duration of each note in beats.

    Returns:
        Path to the created MIDI file.
    """
    intervals = {
        "major": [0, 2, 4, 5, 7, 9, 11, 12],
        "minor": [0, 2, 3, 5, 7, 8, 10, 12],
        "chromatic": list(range(13)),
    }

    ticks_per_beat = 480
    tempo = mido.bpm2tempo(tempo_bpm)
    duration_ticks = int(note_duration_beats * ticks_per_beat)

    notes = []
    for i, interval in enumerate(intervals[scale_type]):
        notes.append({
            "pitch": root + interval,
            "velocity": 100,
            "start_tick": i * duration_ticks,
            "duration_ticks": duration_ticks,
            "channel": 0,
        })

    return create_midi(notes, output_path, ticks_per_beat=ticks_per_beat, tempo=tempo)


def create_chord_progression(
    output_path: str | Path,
    chords: list[list[int]],
    tempo_bpm: int = 120,
    beats_per_chord: int = 4,
) -> Path:
    """Create a MIDI file with a chord progression.

    Args:
        output_path: Where to save the .mid file.
        chords: List of chords, each chord is a list of MIDI note numbers.
        tempo_bpm: Tempo in beats per minute.
        beats_per_chord: How many beats each chord lasts.

    Returns:
        Path to the created MIDI file.
    """
    ticks_per_beat = 480
    tempo = mido.bpm2tempo(tempo_bpm)
    chord_duration = beats_per_chord * ticks_per_beat

    notes = []
    for chord_idx, chord in enumerate(chords):
        start = chord_idx * chord_duration
        for pitch in chord:
            notes.append({
                "pitch": pitch,
                "velocity": 90,
                "start_tick": start,
                "duration_ticks": chord_duration,
                "channel": 0,
            })

    return create_midi(notes, output_path, ticks_per_beat=ticks_per_beat, tempo=tempo)
