"""The creative brief: the user's direction in the user's language.

A brief captures what the performance should *feel* like — mood arc,
imagery, energy shape, must-have moments — without any project-JSON
vocabulary (no scales, generators, or intensities). It is elicited in
conversation, saved beside the project, and survives regenerations: the
manifest links every exported .mid back to the brief that motivated it.

``midi-art new "Title" --brief x.brief.json`` scaffolds a project from a
brief deterministically; sculpting the scaffold into the brief's vision
(generator choices, intensity curves, transitions) is creative judgment,
not code — see docs/COMPOSING.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .project import _require

BRIEF_FORMAT_VERSION = 1


@dataclass(frozen=True)
class CreativeBrief:
    title: str
    logline: str = ""  # one sentence: what the audience should feel
    mood_arc: tuple[str, ...] = ()  # ordered, e.g. ("stillness", "rupture", "aftermath")
    energy_shape: str = ""  # prose: "slow build, cliff-edge drop, long decay"
    duration_seconds: float | None = None
    tempo_feel: str = ""  # "glacial", "relentless ~150"
    imagery: tuple[str, ...] = ()  # visual references: "rain on glass"
    palette: tuple[str, ...] = ()  # color-group vocabulary hints: "ember", "ash"
    must_have_moments: tuple[str, ...] = ()  # "total silence right before the climax"
    avoid: tuple[str, ...] = ()
    style_hint: str = ""  # optional style preset to start from
    notes: str = ""

    # -- persistence ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief_format_version": BRIEF_FORMAT_VERSION,
            "title": self.title,
            "logline": self.logline,
            "mood_arc": list(self.mood_arc),
            "energy_shape": self.energy_shape,
            "duration_seconds": self.duration_seconds,
            "tempo_feel": self.tempo_feel,
            "imagery": list(self.imagery),
            "palette": list(self.palette),
            "must_have_moments": list(self.must_have_moments),
            "avoid": list(self.avoid),
            "style_hint": self.style_hint,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CreativeBrief:
        return cls(
            title=_require(data, "title", "brief"),
            logline=str(data.get("logline", "")),
            mood_arc=tuple(data.get("mood_arc", ())),
            energy_shape=str(data.get("energy_shape", "")),
            duration_seconds=(
                float(data["duration_seconds"])
                if data.get("duration_seconds") is not None else None
            ),
            tempo_feel=str(data.get("tempo_feel", "")),
            imagery=tuple(data.get("imagery", ())),
            palette=tuple(data.get("palette", ())),
            must_have_moments=tuple(data.get("must_have_moments", ())),
            avoid=tuple(data.get("avoid", ())),
            style_hint=str(data.get("style_hint", "")),
            notes=str(data.get("notes", "")),
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> CreativeBrief:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        version = data.get("brief_format_version", 1)
        if version > BRIEF_FORMAT_VERSION:
            raise ValueError(
                f"Brief format {version} is newer than supported {BRIEF_FORMAT_VERSION}."
            )
        return cls.from_dict(data)


def is_brief_document(data: Any) -> bool:
    """A brief file is recognized by its version key (projects use format_version)."""
    return isinstance(data, dict) and "brief_format_version" in data
