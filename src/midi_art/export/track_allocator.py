"""Channel allocation: color groups become MIDI channels, which Zenith maps to colors."""

from __future__ import annotations

from dataclasses import replace

from ..domain.layer import Layer
from ..domain.note_event import NoteEvent
from .zenith_profile import ZenithExportSettings

TRANSITION_CHANNEL = 15


def allocate_channels(
    notes: list[NoteEvent],
    layers_by_id: dict[str, Layer],
    settings: ZenithExportSettings,
) -> list[NoteEvent]:
    """Assign each note a channel from its layer's color group.

    Explicit mappings in the profile win; remaining color groups get the next
    free channel in order of first appearance, wrapping past 16 groups.
    Transition notes (no layer) share a reserved channel so boundary effects
    read as their own color.
    """
    mapping = dict(settings.color_group_mapping)
    used = set(mapping.values())
    next_channel = 0

    def channel_for(group: str) -> int:
        nonlocal next_channel
        if group in mapping:
            return mapping[group]
        while next_channel in used and next_channel < 16:
            next_channel += 1
        channel = next_channel % 16
        mapping[group] = channel
        used.add(channel)
        next_channel += 1
        return channel

    allocated: list[NoteEvent] = []
    for note in notes:
        layer = layers_by_id.get(note.layer_id)
        if layer is None:
            channel = TRANSITION_CHANNEL
        else:
            channel = channel_for(layer.color_group)
        allocated.append(replace(note, channel=channel) if note.channel != channel else note)
    return allocated
