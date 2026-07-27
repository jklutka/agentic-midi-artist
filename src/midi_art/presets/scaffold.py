"""Scaffold a project from a creative brief: the deterministic, mechanical part.

Code handles what has one right answer — style selection, duration math,
copying the brief's language into the artistic direction. Everything
creative (generator choices per imagery, intensity curves, transitions,
color groups) is left to whoever sculpts the scaffold; see
docs/COMPOSING.md.
"""

from __future__ import annotations

from dataclasses import replace

from ..domain.brief import CreativeBrief
from ..domain.project import ArtisticDirection, Project
from .styles import STYLES, build_style

DEFAULT_STYLE = "organic_growth"


def scaffold_from_brief(
    brief: CreativeBrief,
    seed: int,
    *,
    name: str | None = None,
    brief_file: str | None = None,
) -> Project:
    """Build a starting project from a brief. Deterministic and lint-clean."""
    style = brief.style_hint if brief.style_hint in STYLES else DEFAULT_STYLE
    project = build_style(style, name or brief.title, seed)

    if brief.duration_seconds:
        project = _scale_duration(project, brief.duration_seconds)

    mood_start, mood_middle, mood_end = _mood_triplet(brief.mood_arc)
    direction = ArtisticDirection(
        theme=brief.logline or project.artistic_direction.theme,
        mood_start=mood_start or project.artistic_direction.mood_start,
        mood_middle=mood_middle or project.artistic_direction.mood_middle,
        mood_end=mood_end or project.artistic_direction.mood_end,
        visual_focus=brief.imagery or project.artistic_direction.visual_focus,
    )
    return replace(project, artistic_direction=direction, brief_file=brief_file)


def _mood_triplet(mood_arc: tuple[str, ...]) -> tuple[str, str, str]:
    if not mood_arc:
        return "", "", ""
    if len(mood_arc) == 1:
        return mood_arc[0], "", mood_arc[0]
    middle = ", ".join(mood_arc[1:-1])
    return mood_arc[0], middle, mood_arc[-1]


def _scale_duration(project: Project, target_seconds: float) -> Project:
    """Proportionally rescale scene lengths to hit the target duration."""
    music = project.music
    avg_tempo = (music.tempo_start + (music.tempo_end or music.tempo_start)) / 2
    target_beats = target_seconds * avg_tempo / 60.0
    current_beats = project.duration_beats
    if current_beats <= 0:
        return project
    factor = target_beats / current_beats
    scenes = tuple(
        replace(scene, duration_bars=max(1, round(scene.duration_bars * factor)))
        for scene in project.scenes
    )
    return replace(project, scenes=scenes)
