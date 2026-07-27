"""Agentic MIDI Artist (``midi-art``) command line interface.

Workflow:

    midi-art styles                      # browse style presets
    midi-art new "Collapse" --style controlled_chaos -o collapse.json
    midi-art generate collapse.json      # full performance -> .mid + manifest
    midi-art generate collapse.json --scene Fracture   # fast single-scene preview
    midi-art generate collapse.json --seed 7 --suffix var-b   # a variation
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__, toolchain
from ..analysis.lint import lint_brief_document, lint_document
from ..analysis.metrics import analyze
from ..analysis.summary import build_visual_summary, format_summary_text
from ..analysis.validation import IssueLevel, validate
from ..composition.composer import compose
from ..domain.brief import CreativeBrief, is_brief_document
from ..domain.project import Project
from ..export import audio
from ..export.midi_writer import write_midi
from ..export.zenith_profile import PROFILES
from ..generators import GENERATORS
from ..presets import STYLES, build_style, scaffold_from_brief
from ..preview import build_preview, render_html, render_png
from ..transitions import TRANSITIONS


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _emit(args: argparse.Namespace, payload: dict, human) -> None:
    """Print one compact JSON object with --json, else the human output."""
    if getattr(args, "json", False):
        print(json.dumps(payload, separators=(",", ":")))
    else:
        human()


def _issue_dict(issue) -> dict:
    return {"level": issue.level.value, "message": issue.message, "path": issue.path}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="midi-art",
        description=(
            "Agentic MIDI Artist — an agent-first generative performance composer "
            "for visually dramatic MIDI art."
        ),
    )
    sub = parser.add_subparsers(required=True)

    p_styles = sub.add_parser("styles", help="List style presets.")
    p_styles.set_defaults(handler=_cmd_styles)

    p_generators = sub.add_parser("generators", help="List note generators.")
    p_generators.set_defaults(handler=_cmd_generators)

    p_transitions = sub.add_parser("transitions", help="List transition types.")
    p_transitions.set_defaults(handler=_cmd_transitions)

    p_profiles = sub.add_parser("profiles", help="List Zenith export profiles.")
    p_profiles.set_defaults(handler=_cmd_profiles)

    p_describe = sub.add_parser(
        "describe", help="Print the complete authoring contract (schema, plugins, enums)."
    )
    p_describe.add_argument("--json", action="store_true",
                            help="Emit one compact JSON object.")
    p_describe.set_defaults(handler=_cmd_describe)

    p_new = sub.add_parser("new", help="Create a project file from a style preset.")
    p_new.add_argument("name", help="Performance name.")
    p_new.add_argument("--style", default="organic_growth", help="Style preset to start from.")
    p_new.add_argument("--brief", help="Creative brief (.brief.json) to scaffold from; "
                                       "its style_hint and duration take over from --style.")
    p_new.add_argument("--seed", type=int, default=4207, help="Random seed.")
    p_new.add_argument("-o", "--output", help="Project file path (default: <name>.json).")
    p_new.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    p_new.set_defaults(handler=_cmd_new)

    p_gen = sub.add_parser("generate", help="Compose a project and export MIDI + manifest.")
    p_gen.add_argument("project", help="Path to a project .json file.")
    p_gen.add_argument("-o", "--output", help="Output .mid path (default: output/<name>.mid).")
    p_gen.add_argument("--seed", type=int, help="Override the project seed (variation).")
    p_gen.add_argument("--scene", help="Compose only this scene — a fast preview.")
    p_gen.add_argument("--profile", help="Override the export profile.")
    p_gen.add_argument("--suffix", help="Filename suffix for variations (e.g. 'var-b').")
    p_gen.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    p_gen.set_defaults(handler=_cmd_generate)

    p_lint = sub.add_parser(
        "lint", help="Validate a project (or creative brief) document before composing."
    )
    p_lint.add_argument("project", help="Path to a project .json or .brief.json file.")
    p_lint.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    p_lint.set_defaults(handler=_cmd_lint)

    p_audio = sub.add_parser(
        "audio",
        help="Render a .mid to audio via FluidSynth, optionally muxed into a Zenith video.",
    )
    p_audio.add_argument("midi", help="Path to the .mid file to render.")
    p_audio.add_argument("-o", "--output",
                         help="Output .wav path (default: next to the .mid).")
    p_audio.add_argument("--soundfont",
                         help="Path to a .sf2 SoundFont (default: SOUNDFONT_PATH env var).")
    p_audio.add_argument("--video",
                         help="Zenith-rendered video to mux the audio into "
                              "(writes <video>-audio.<ext>).")
    p_audio.add_argument("--gain", type=float, default=audio.DEFAULT_GAIN,
                         help="Synth gain 0..10; keep low for dense pieces "
                              f"(default: {audio.DEFAULT_GAIN}).")
    p_audio.add_argument("--polyphony", type=int, default=audio.DEFAULT_POLYPHONY,
                         help=f"Max simultaneous voices (default: {audio.DEFAULT_POLYPHONY}).")
    p_audio.add_argument("--sample-rate", type=int, default=audio.DEFAULT_SAMPLE_RATE,
                         help=f"Sample rate in Hz (default: {audio.DEFAULT_SAMPLE_RATE}).")
    p_audio.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    p_audio.set_defaults(handler=_cmd_audio)

    p_report = sub.add_parser("report", help="Analyze a project without writing MIDI.")
    p_report.add_argument("project", help="Path to a project .json file.")
    p_report.add_argument("--scene", help="Analyze only this scene.")
    p_report.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    p_report.set_defaults(handler=_cmd_report)

    p_prev = sub.add_parser(
        "preview", help="Render an HTML preview (piano roll, density, polyphony)."
    )
    p_prev.add_argument("project", help="Path to a project .json file.")
    p_prev.add_argument("-o", "--output", help="Output .html path.")
    p_prev.add_argument("--scene", help="Preview only this scene.")
    p_prev.add_argument(
        "--seeds", help="Comma-separated seeds to compare as variations (e.g. 1,2,3)."
    )
    p_prev.add_argument(
        "--format", choices=("html", "png", "both"), default="html", dest="fmt",
        help="Output format: html (default), png (one image per seed), or both.",
    )
    p_prev.add_argument("--open", action="store_true", dest="open_browser",
                        help="Open the preview in the default browser.")
    p_prev.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    p_prev.set_defaults(handler=_cmd_preview)

    p_doctor = sub.add_parser(
        "doctor", help="Check the external toolchain (Zenith, FFmpeg, FluidSynth, SoundFont)."
    )
    p_doctor.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    p_doctor.set_defaults(handler=_cmd_doctor)

    p_setup = sub.add_parser(
        "setup", help="Install missing external tools into the standard layout."
    )
    p_setup.add_argument(
        "--only", help=f"Comma-separated subset to install ({','.join(toolchain.TOOLS)})."
    )
    p_setup.add_argument("--force", action="store_true",
                         help="Reinstall even if the tool already resolves.")
    p_setup.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    p_setup.set_defaults(handler=_cmd_setup)

    p_studio = sub.add_parser("studio", help="Launch the desktop studio (GUI).")
    p_studio.add_argument("project", nargs="?", help="Optional project file to open.")
    p_studio.set_defaults(handler=_cmd_studio)

    return parser


def _cmd_styles(_args: argparse.Namespace) -> int:
    for definition in STYLES.values():
        print(f"{definition.name:24} {definition.description}")
    return 0


def _cmd_generators(_args: argparse.Namespace) -> int:
    for generator in GENERATORS.values():
        d = generator.definition
        visuals = ", ".join(d.visual_characteristics)
        print(f"{d.name:12} [{d.category}] density={d.estimated_density}")
        print(f"{'':12} {d.description}")
        print(f"{'':12} visuals: {visuals}")
    return 0


def _cmd_transitions(_args: argparse.Namespace) -> int:
    for transition in TRANSITIONS.values():
        print(f"{transition.name:20} {transition.description}")
    return 0


def _cmd_profiles(_args: argparse.Namespace) -> int:
    for profile in PROFILES.values():
        print(f"{profile.name:26} {profile.description}")
    return 0


def _cmd_describe(args: argparse.Namespace) -> int:
    from ..describe import build_contract, format_contract_text

    contract = build_contract()
    if args.json:
        print(json.dumps(contract, separators=(",", ":")))
    else:
        print(format_contract_text(contract))
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    if args.brief:
        brief = CreativeBrief.load(args.brief)
        project = scaffold_from_brief(
            brief, args.seed, name=args.name, brief_file=str(Path(args.brief))
        )
        style = brief.style_hint if brief.style_hint in STYLES else "organic_growth"
    else:
        style = args.style
        project = build_style(style, args.name, args.seed)
    path = Path(args.output) if args.output else Path(_slug(args.name) + ".json")
    project.save(path)

    def _human() -> None:
        print(f"Created project: {path}")
        print(f"  style: {style}, seed: {args.seed}, scenes: {len(project.scenes)}")
        if args.brief:
            print(f"  brief: {args.brief}")
        print(f"Next: midi-art generate {path}")

    _emit(args, {
        "ok": True,
        "file": str(path),
        "style": style,
        "seed": args.seed,
        "scene_count": len(project.scenes),
        "brief": args.brief,
    }, _human)
    return 0


def _lint_file(path: str | Path) -> list:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if is_brief_document(data):
        return lint_brief_document(data)
    return lint_document(data)


def _load_project(args: argparse.Namespace) -> tuple[Project, list]:
    """Load a project, aborting with the lint errors if the document is broken.

    Returns the project plus the non-fatal lint issues so commands can show
    them alongside the post-compose validation issues.
    """
    lint_issues = _lint_file(args.project)
    errors = [issue for issue in lint_issues if issue.level is IssueLevel.ERROR]
    if errors:
        detail = "; ".join(str(issue) for issue in errors[:3])
        raise ValueError(
            f"Project document has {len(errors)} lint error(s): {detail} "
            f"— run: midi-art lint {args.project}"
        )
    project = Project.load(args.project)
    if getattr(args, "seed", None) is not None:
        project = replace(project, seed=args.seed)
    if getattr(args, "profile", None):
        if args.profile not in PROFILES:
            allowed = ", ".join(sorted(PROFILES))
            raise ValueError(f"Unknown export profile {args.profile!r}. Available: {allowed}")
        project = replace(project, export_profile=args.profile)
    return project, lint_issues


def _cmd_lint(args: argparse.Namespace) -> int:
    issues = _lint_file(args.project)
    errors = [issue for issue in issues if issue.level is IssueLevel.ERROR]

    def _human() -> None:
        for issue in issues:
            print(str(issue))
        if not issues:
            print("OK — no issues.")

    _emit(args, {
        "ok": not errors,
        "issues": [_issue_dict(issue) for issue in issues],
        "error_count": len(errors),
        "warning_count": sum(1 for i in issues if i.level is IssueLevel.WARNING),
    }, _human)
    return 1 if errors else 0


def _cmd_generate(args: argparse.Namespace) -> int:
    project, lint_issues = _load_project(args)
    performance = compose(project, scene_name=args.scene)
    report = analyze(performance)
    issues = validate(performance, report) + lint_issues

    stem = _slug(project.name)
    if args.scene:
        stem += f"-scene-{_slug(args.scene)}"
    if args.suffix:
        stem += f"-{args.suffix}"
    midi_path = Path(args.output) if args.output else Path("output") / f"{stem}.mid"

    errors = [issue for issue in issues if issue.level is IssueLevel.ERROR]
    payload = {
        "ok": not errors,
        "project": project.name,
        "project_file": str(Path(args.project)),
        "seed": project.seed,
        "profile": performance.settings.name,
        "scene": args.scene,
        "report": report.to_dict(),
        "issues": [_issue_dict(issue) for issue in issues],
        "aborted": bool(errors),
        "files": {},
    }
    if errors:
        def _human_abort() -> None:
            _print_summary(performance, report, issues)

        _emit(args, payload, _human_abort)
        print("\nExport aborted due to errors above.", file=sys.stderr)
        return 1

    write_midi(
        performance.notes,
        midi_path,
        performance.settings,
        tempo_events=performance.tempo_events,
    )
    manifest_path = midi_path.with_suffix(".manifest.json")
    manifest = {
        "manifest_version": 2,
        "project": project.name,
        "project_file": str(Path(args.project)),
        "project_sha256": hashlib.sha256(Path(args.project).read_bytes()).hexdigest(),
        "midi_file": str(midi_path),
        "scene": args.scene,
        "seed": project.seed,
        "export_profile": performance.settings.name,
        "tool_version": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "report": report.to_dict(),
        "issues": [_issue_dict(issue) for issue in issues],
        "brief": _manifest_brief(project),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    payload["files"] = {"midi": str(midi_path), "manifest": str(manifest_path)}

    def _human() -> None:
        _print_summary(performance, report, issues)
        print(f"\nWrote: {midi_path}")
        print(f"Manifest: {manifest_path}")

    _emit(args, payload, _human)
    return 0


def _manifest_brief(project: Project) -> dict | None:
    """Reference to the creative brief behind this project, if it has one."""
    brief_file = getattr(project, "brief_file", None)
    if not brief_file:
        return None
    entry: dict = {"file": brief_file}
    path = Path(brief_file)
    if path.exists():
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return entry


def _cmd_audio(args: argparse.Namespace) -> int:
    wav_path = audio.render_wav(
        args.midi,
        wav_file=args.output,
        soundfont=args.soundfont,
        sample_rate=args.sample_rate,
        gain=args.gain,
        polyphony=args.polyphony,
    )
    muxed = audio.mux_audio(args.video, wav_path) if args.video else None

    def _human() -> None:
        print(f"Wrote audio: {wav_path}")
        if muxed:
            print(f"Wrote video with audio: {muxed}")

    _emit(args, {
        "ok": True,
        "files": {"wav": str(wav_path), "video": str(muxed) if muxed else None},
    }, _human)
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    project, _ = _load_project(args)
    seeds = [project.seed]
    if args.seeds:
        seeds = [int(seed.strip()) for seed in args.seeds.split(",") if seed.strip()]

    sections = []
    for seed in seeds:
        variation = replace(project, seed=seed)
        performance = compose(variation, scene_name=args.scene)
        report = analyze(performance)
        issues = validate(performance, report)
        heading = f"seed {seed}" + (f" — scene {args.scene}" if args.scene else "")
        sections.append(
            (heading, build_preview(performance), report.format_text(),
             [str(issue) for issue in issues])
        )

    stem = _slug(project.name)
    if args.scene:
        stem += f"-scene-{_slug(args.scene)}"

    files: list[Path] = []
    if args.fmt in ("html", "both"):
        path = Path(args.output) if args.output else Path("output") / f"{stem}-preview.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        title = f"Agentic MIDI Artist — {project.name}"
        path.write_text(render_html(title, sections), encoding="utf-8")
        files.append(path)
    if args.fmt in ("png", "both"):
        for seed, (heading, data, _report, _issues) in zip(seeds, sections):
            png_path = _png_path(args, stem, seed, multi=len(seeds) > 1)
            files.append(render_png(data, png_path, title=f"{project.name} — {heading}"))

    def _human() -> None:
        for written in files:
            print(f"Wrote preview: {written}")
        if len(sections) > 1:
            print(f"Comparing {len(sections)} variations: {', '.join(str(s) for s in seeds)}")

    _emit(args, {"ok": True, "files": [str(f) for f in files], "seeds": seeds}, _human)
    if args.open_browser and files:
        import webbrowser

        webbrowser.open(files[0].resolve().as_uri())
    return 0


def _png_path(args: argparse.Namespace, stem: str, seed: int, multi: bool) -> Path:
    if args.output:
        base = Path(args.output)
        if args.fmt == "both" or base.suffix.lower() != ".png":
            base = base.with_suffix(".png")
        if multi:
            base = base.with_name(f"{base.stem}-seed-{seed}.png")
        return base
    name = f"{stem}-seed-{seed}-preview.png" if multi else f"{stem}-preview.png"
    return Path("output") / name


def _tool_payload(statuses) -> dict:
    return {
        "ok": all(status.found for status in statuses),
        "root": str(toolchain.standard_root()),
        "tools": [
            {"name": s.name, "found": s.found, "path": s.path, "source": s.source,
             "hint": s.hint}
            for s in statuses
        ],
    }


def _print_tool_statuses(statuses) -> None:
    print(f"Standard tool root: {toolchain.standard_root()}")
    for status in statuses:
        if status.found:
            print(f"  {status.name:12} OK       {status.path} ({status.source})")
        else:
            print(f"  {status.name:12} MISSING  {status.hint}")


def _cmd_doctor(args: argparse.Namespace) -> int:
    statuses = toolchain.doctor()
    payload = _tool_payload(statuses)
    _emit(args, payload, lambda: _print_tool_statuses(statuses))
    return 0 if payload["ok"] else 1


def _cmd_setup(args: argparse.Namespace) -> int:
    only = tuple(
        part.strip() for part in args.only.split(",") if part.strip()
    ) if args.only else toolchain.TOOLS
    statuses = toolchain.setup(only=only, force=args.force)
    payload = _tool_payload(statuses)
    _emit(args, payload, lambda: _print_tool_statuses(statuses))
    return 0 if payload["ok"] else 1


def _cmd_studio(args: argparse.Namespace) -> int:
    from .desktop import run_studio

    run_studio(args.project)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    project, lint_issues = _load_project(args)
    performance = compose(project, scene_name=args.scene)
    report = analyze(performance)
    issues = validate(performance, report) + lint_issues
    visual = build_visual_summary(performance, report)

    def _human() -> None:
        _print_summary(performance, report, issues)
        print()
        print(format_summary_text(visual))

    _emit(args, {
        "ok": True,
        "project": project.name,
        "seed": project.seed,
        "profile": performance.settings.name,
        "scene": args.scene,
        "report": report.to_dict(),
        "visual": visual,
        "issues": [_issue_dict(issue) for issue in issues],
    }, _human)
    return 0


def _print_summary(performance, report, issues) -> int:
    is_preview = len(performance.scene_spans) == 1 and len(performance.project.scenes) > 1
    scope = " — scene preview" if is_preview else ""
    print(f"{performance.project.name}{scope}")
    print(f"Profile: {performance.settings.name}, seed: {performance.project.seed}")
    print()
    print(report.format_text())
    if issues:
        print()
        for issue in issues:
            print(str(issue))
    return 0


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-") or "performance"


if __name__ == "__main__":
    raise SystemExit(main())
