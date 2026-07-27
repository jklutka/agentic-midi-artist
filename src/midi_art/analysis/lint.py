"""Document lint: validate a project JSON *before* composing.

``from_dict`` is deliberately lenient (unknown keys ignored, out-of-range
values clamped downstream), which is safe for loading but silent for
authoring. This walker checks the raw document against the declarative
schema and reports every problem at once, with paths and did-you-mean
suggestions — the tight feedback loop ``midi-art lint`` exposes.
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any

from ..domain.brief import BRIEF_FORMAT_VERSION
from ..domain.project import FORMAT_VERSION
from ..domain.schema import BRIEF_SCHEMA, PROJECT_SCHEMA, FieldSpec, enum_values
from .validation import Issue, IssueLevel

_MAX_CHANNELS = 16


def lint_document(data: Any) -> list[Issue]:
    """Lint a raw project document. Returns all issues, worst first."""
    if not isinstance(data, dict):
        return [Issue(IssueLevel.ERROR, "Project document must be a JSON object.")]
    issues: list[Issue] = []
    _walk(PROJECT_SCHEMA, data, "", issues)
    _check_format_version(data, issues)
    _check_project_shape(data, issues)
    order = {IssueLevel.ERROR: 0, IssueLevel.WARNING: 1, IssueLevel.INFO: 2}
    issues.sort(key=lambda issue: order[issue.level])
    return issues


def lint_brief_document(data: Any) -> list[Issue]:
    """Lint a raw creative-brief document."""
    if not isinstance(data, dict):
        return [Issue(IssueLevel.ERROR, "Brief document must be a JSON object.")]
    issues: list[Issue] = []
    _walk(BRIEF_SCHEMA, data, "", issues)
    version = data.get("brief_format_version", 1)
    if isinstance(version, int) and version > BRIEF_FORMAT_VERSION:
        issues.append(Issue(
            IssueLevel.ERROR,
            f"Brief format {version} is newer than supported {BRIEF_FORMAT_VERSION}.",
            path="brief_format_version",
        ))
    style = data.get("style_hint")
    if isinstance(style, str) and style:
        styles = list(enum_values("styles"))
        if style not in styles:
            issues.append(Issue(
                IssueLevel.WARNING,
                f"Unknown style_hint {style!r} — scaffolding falls back to a default."
                f"{_suggest(style, styles)} Available: {', '.join(styles)}.",
                path="style_hint",
            ))
    order = {IssueLevel.ERROR: 0, IssueLevel.WARNING: 1, IssueLevel.INFO: 2}
    issues.sort(key=lambda issue: order[issue.level])
    return issues


def _suggest(word: str, options: list[str]) -> str:
    matches = get_close_matches(str(word), options, n=1)
    return f" Did you mean {matches[0]!r}?" if matches else ""


def _walk(specs: tuple[FieldSpec, ...], data: dict[str, Any], prefix: str,
          issues: list[Issue]) -> None:
    index = {spec.key: spec for spec in specs}
    for key in data:
        if key not in index:
            issues.append(Issue(
                IssueLevel.WARNING,
                f"Unknown key {key!r} is silently ignored.{_suggest(key, list(index))}",
                path=f"{prefix}{key}",
            ))
    for spec in specs:
        path = f"{prefix}{spec.key}"
        if spec.key not in data:
            if spec.required:
                issues.append(Issue(
                    IssueLevel.ERROR, f"Missing required key {spec.key!r}.", path=path
                ))
            continue
        _check_value(spec, data[spec.key], path, issues)


def _check_value(spec: FieldSpec, value: Any, path: str, issues: list[Issue]) -> None:
    if value is None:
        if not spec.nullable:
            issues.append(Issue(IssueLevel.ERROR, "Value must not be null.", path=path))
        return

    if spec.type == "array":
        if not isinstance(value, list):
            issues.append(Issue(IssueLevel.ERROR, "Expected a JSON array.", path=path))
            return
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                issues.append(Issue(
                    IssueLevel.ERROR, "Expected a JSON object.", path=f"{path}[{i}]"
                ))
                continue
            _walk(spec.children, item, f"{path}[{i}].", issues)
        return

    if spec.type == "object":
        if not isinstance(value, dict):
            issues.append(Issue(IssueLevel.ERROR, "Expected a JSON object.", path=path))
            return
        if not spec.free_form:
            _walk(spec.children, value, f"{path}.", issues)
        if spec.key == "generator":
            _lint_generator_params(value, path, issues)
        return

    if spec.type == "list[str]":
        if not isinstance(value, list):
            issues.append(Issue(IssueLevel.ERROR, "Expected a JSON array of strings.", path=path))
        elif any(not isinstance(item, str) for item in value):
            issues.append(Issue(IssueLevel.WARNING, "All items should be strings.", path=path))
        return

    if spec.type in ("int", "float"):
        _check_number(spec, value, path, issues)
        return

    # str-typed leaf
    if not isinstance(value, str):
        level = IssueLevel.ERROR if spec.enum else IssueLevel.WARNING
        issues.append(Issue(level, f"Expected a string, got {type(value).__name__}.", path=path))
        return
    if spec.enum:
        allowed = list(enum_values(spec.enum))
        if value not in allowed:
            level = IssueLevel.WARNING if spec.enum_warn else IssueLevel.ERROR
            consequence = "it is silently ignored" if spec.enum_warn else "compose will fail"
            issues.append(Issue(
                level,
                f"Unknown value {value!r} — {consequence}.{_suggest(value, allowed)} "
                f"Allowed: {', '.join(allowed)}.",
                path=path,
            ))


def _check_number(spec: FieldSpec, value: Any, path: str, issues: list[Issue]) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                issues.append(Issue(
                    IssueLevel.ERROR, f"Expected a number, got {value!r}.", path=path
                ))
                return
            issues.append(Issue(
                IssueLevel.WARNING, f"Number written as a string: {value!r}.", path=path
            ))
        else:
            issues.append(Issue(
                IssueLevel.ERROR, f"Expected a number, got {type(value).__name__}.", path=path
            ))
            return
    if spec.type == "int" and isinstance(value, float) and not float(value).is_integer():
        issues.append(Issue(
            IssueLevel.WARNING, f"Expected an integer; {value} will be truncated.", path=path
        ))
    low, high = spec.minimum, spec.maximum
    if (low is not None and value < low) or (high is not None and value > high):
        bounds = f"{low:g}..{high:g}" if low is not None and high is not None else (
            f">= {low:g}" if low is not None else f"<= {high:g}"
        )
        issues.append(Issue(
            IssueLevel.WARNING,
            f"Value {value} is outside {bounds} and will be clamped or misbehave.",
            path=path,
        ))


def _lint_generator_params(generator: dict[str, Any], path: str, issues: list[Issue]) -> None:
    from ..generators import GENERATORS

    gtype = generator.get("type")
    params = generator.get("params", {})
    if gtype not in GENERATORS or not isinstance(params, dict):
        return  # the type/object errors are already reported
    specs = {spec.name: spec for spec in GENERATORS[gtype].definition.params}
    for key, value in params.items():
        param_path = f"{path}.params.{key}"
        if key not in specs:
            known = f" {gtype!r} accepts: {', '.join(specs)}." if specs else (
                f" {gtype!r} accepts no params."
            )
            issues.append(Issue(
                IssueLevel.WARNING,
                f"Unknown param {key!r} is silently ignored.{_suggest(key, list(specs))}{known}",
                path=param_path,
            ))
            continue
        spec = specs[key]
        if spec.choices and value not in spec.choices:
            issues.append(Issue(
                IssueLevel.WARNING,
                f"Value {value!r} is not one of {'|'.join(spec.choices)}; "
                f"behavior falls back to a default branch.{_suggest(value, list(spec.choices))}",
                path=param_path,
            ))
            continue
        if spec.type in ("int", "float"):
            _check_number(
                FieldSpec(key, spec.type, minimum=spec.minimum, maximum=spec.maximum),
                value, param_path, issues,
            )


def _check_format_version(data: dict[str, Any], issues: list[Issue]) -> None:
    version = data.get("format_version", 1)
    if isinstance(version, int) and version > FORMAT_VERSION:
        issues.append(Issue(
            IssueLevel.ERROR,
            f"Project format {version} is newer than supported {FORMAT_VERSION}.",
            path="format_version",
        ))


def _check_project_shape(data: dict[str, Any], issues: list[Issue]) -> None:
    scenes = data.get("scenes")
    if not isinstance(scenes, list):
        return
    if not scenes:
        issues.append(Issue(
            IssueLevel.WARNING, "Project has no scenes — it will compose zero notes.",
            path="scenes",
        ))
        return

    names = [
        s.get("name") for s in scenes
        if isinstance(s, dict) and isinstance(s.get("name"), str)
    ]
    for name in sorted({n for n in names if names.count(n) > 1}):
        issues.append(Issue(
            IssueLevel.WARNING,
            f"Duplicate scene name {name!r} — '--scene' selection is ambiguous.",
            path="scenes",
        ))

    color_groups: set[str] = set()
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        layers = scene.get("layers")
        if layers == []:
            issues.append(Issue(
                IssueLevel.INFO,
                "Scene has no layers — it renders as silence (transitions aside).",
                path=f"scenes[{i}].layers",
            ))
        if isinstance(layers, list):
            for layer in layers:
                if isinstance(layer, dict) and isinstance(layer.get("color_group"), str):
                    color_groups.add(layer["color_group"])
    if len(color_groups) > _MAX_CHANNELS:
        issues.append(Issue(
            IssueLevel.INFO,
            f"{len(color_groups)} distinct color groups exceed {_MAX_CHANNELS} MIDI channels; "
            "groups will share channels (and colors).",
        ))

    music = data.get("music")
    if isinstance(music, dict) and music.get("tempo_end") is not None:
        if music.get("tempo_end") == music.get("tempo_start", 120.0):
            issues.append(Issue(
                IssueLevel.INFO,
                "tempo_end equals tempo_start — the tempo ramp does nothing.",
                path="music.tempo_end",
            ))
