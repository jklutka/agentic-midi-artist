"""Validation: catch technical problems before the file reaches Zenith."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..composition.composer import Performance
from .metrics import PerformanceReport


class IssueLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Issue:
    level: IssueLevel
    message: str
    path: str = ""

    def __str__(self) -> str:
        location = f" (at {self.path})" if self.path else ""
        return f"[{self.level.value.upper()}] {self.message}{location}"


def validate(performance: Performance, report: PerformanceReport) -> list[Issue]:
    settings = performance.settings
    issues: list[Issue] = []

    for warning in performance.warnings:
        issues.append(Issue(IssueLevel.WARNING, warning))

    if report.total_notes == 0:
        issues.append(Issue(IssueLevel.ERROR, "Performance contains no notes."))
        return issues

    if report.total_notes > settings.max_total_notes:
        issues.append(
            Issue(
                IssueLevel.ERROR,
                f"{report.total_notes:,} notes exceeds the {settings.name} cap of "
                f"{settings.max_total_notes:,}; export will refuse this file.",
            )
        )
    if report.max_notes_per_second > settings.max_notes_per_second:
        issues.append(
            Issue(
                IssueLevel.WARNING,
                f"Peak density {report.max_notes_per_second}/s exceeds the profile's "
                f"{settings.max_notes_per_second:.0f}/s guideline — Zenith may stutter.",
            )
        )
    if report.peak_polyphony > settings.max_polyphony:
        issues.append(
            Issue(
                IssueLevel.WARNING,
                f"Peak polyphony {report.peak_polyphony} exceeds the profile's "
                f"{settings.max_polyphony} guideline.",
            )
        )

    off_piano = sum(1 for note in performance.notes if not 21 <= note.pitch <= 108)
    if off_piano:
        issues.append(
            Issue(
                IssueLevel.WARNING,
                f"{off_piano:,} notes fall outside the 88-key piano range (21..108) "
                "and will render off the visible keyboard.",
            )
        )

    short = sum(
        1
        for note in performance.notes
        if note.duration < settings.min_note_duration_beats
    )
    if short:
        issues.append(
            Issue(
                IssueLevel.INFO,
                f"{short:,} notes are shorter than the profile minimum and will be "
                "extended at export.",
            )
        )

    overlaps = _same_pitch_overlaps(performance)
    if overlaps:
        issues.append(
            Issue(
                IssueLevel.INFO,
                f"{overlaps:,} same-pitch overlaps (stuck-note risk) will be resolved "
                "at export by truncation.",
            )
        )

    quiet = _longest_gap_beats(performance)
    if quiet > performance.project.music.beats_per_bar * 4:
        issues.append(
            Issue(
                IssueLevel.WARNING,
                f"Longest visually inactive stretch is {quiet:.0f} beats — confirm the "
                "silence is intentional.",
            )
        )
    return issues


def _same_pitch_overlaps(performance: Performance) -> int:
    last_end: dict[tuple[int, int], float] = {}
    count = 0
    for note in sorted(performance.notes, key=lambda n: n.start):
        key = (note.pitch, note.channel)
        if key in last_end and note.start < last_end[key]:
            count += 1
        last_end[key] = max(last_end.get(key, 0.0), note.end)
    return count


def _longest_gap_beats(performance: Performance) -> float:
    longest = 0.0
    cursor = 0.0
    for note in performance.notes:  # already sorted by start
        if note.start > cursor:
            longest = max(longest, note.start - cursor)
        cursor = max(cursor, note.end)
    longest = max(longest, performance.duration_beats - cursor)
    return longest
