# AGENTS.md

Guidance for AI agents (and new contributors) working on **Agentic MIDI Artist** (this
repository; CLI: `midi-art`). Updated 2026-07 after the agent-first workflow release. This
file is the canonical agent guide for any CLI-capable agent (Claude Code, OpenAI Codex, …).
Claude Code and Codex also discover the repository-scoped `compose-midi-art` skill from
their native skill directories; both thin wrappers route to the same tool-neutral guide.

## Composing (agent workflow)

If the task is *making a performance for a user* — not changing source — this section is
all you need; everything below it is contributor material.

1. `midi-art describe --json` — the complete authoring contract (project schema, brief
   schema, generators with param specs, transitions, styles, profiles, scales, quirks).
   **Never read `src/` to discover parameters.**
2. Interview the user about creative direction, then save it as
   `projects/<slug>.brief.json` and scaffold:
   `midi-art new "<Title>" --brief projects/<slug>.brief.json -o projects/<slug>.json --json`.
   The interview questions and imagery→generator judgment live in
   [docs/COMPOSING.md](docs/COMPOSING.md) — read it before composing.
3. Edit the project JSON, then `midi-art lint projects/<slug>.json --json` after **every**
   edit — typos in keys/params are silently ignored at load time; only lint catches them.
4. `midi-art generate projects/<slug>.json --json` → `.mid` + manifest. Iterate cheaply:
   `midi-art report ... --json` (its `visual` block is the shape of the piece) and
   single scenes via `--scene <Name>`.
5. `midi-art preview projects/<slug>.json --format png` and **look at the image** to judge
   the piece against the brief. Compare variations with `--seeds 1,2,3 --format png`.
6. Optional delivery extras: `midi-art audio output/<slug>.mid [--video render.mp4] --json`
   renders the (otherwise silent) .mid to .wav via FluidSynth and can mux it into the
   Zenith video. Before using it, `midi-art doctor --json` tells you whether the external
   toolchain resolves; `midi-art setup --json` installs anything missing into the standard
   layout (`%LOCALAPPDATA%\midi-art\`) — after that, no env vars or flags are needed.
   Setup downloads roughly 40–100 MB, so tell the user before running it.

Hard token rules: prefer `--json` wherever supported; never open `*-preview.html`
(megabytes of inline SVG); generated artifacts land in `output/`, projects and briefs in
`projects/`.

## What this project is

**Agentic MIDI Artist** (CLI: `midi-art`) is a generative performance composer: it turns an
editable JSON *project file*
(scenes, layers, artistic intent) into a `.mid` file deliberately designed for the
[Zenith-MIDI](https://github.com/arduano/Zenith-MIDI) visual renderer. The product framing is
"what should the audience see and feel", not "what notes should be generated" — see
`README.md` for the user-facing story.

The repo contains two packages under `src/`:

- **`midi_art/`** — the primary package (the refactor target architecture). All new work
  goes here.
- **`midi_app/`** — the legacy procedural generator (dense-song Tkinter UI, pattern demos,
  Zenith launcher). Kept working during migration; do not extend it except for bug fixes.

## Environment

- **Platform:** Windows. Zenith integration is Windows-specific; the composer itself is portable.
- **Python:** 3.14 in `.venv/` (project requires >= 3.10). Runtime deps: `mido`, `pillow`.
- **External tools (optional):** Zenith-MIDI, FFmpeg, FluidSynth, and a SoundFont live in
  the **standard layout** `%LOCALAPPDATA%\midi-art\` (`zenith/`, `fluidsynth/`,
  `soundfonts/`; override root with `MIDI_ART_HOME`). Discovery order everywhere:
  explicit flag → env var (`ZENITH_MIDI_PATH`/`FFMPEG_PATH`/`FLUIDSYNTH_PATH`/
  `SOUNDFONT_PATH`) → standard layout → PATH, implemented once in
  [src/midi_art/toolchain.py](src/midi_art/toolchain.py). `midi-art doctor` reports what
  resolves; `midi-art setup` downloads what's missing into the layout. **On a standard
  machine, assume the layout — no env vars needed.** Composition, linting, reports, PNG
  previews, MIDI export, and tests do not need these tools (tests isolate via the
  `MIDI_ART_HOME` fixture in `tests/conftest.py` — keep that pattern for new tool tests).

## Setup, launch, and test

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

```powershell
# Primary workflow (the midi-art console script)
midi-art describe [--json]                                 # the full authoring contract
midi-art styles | generators | transitions | profiles      # registry listings
midi-art new "Name" --style controlled_chaos -o proj.json [--json] # scaffold from a style
midi-art new "Name" --brief b.brief.json -o proj.json [--json]     # scaffold from a brief
midi-art lint proj.json [--json]                           # document lint (also lints briefs)
midi-art generate proj.json [--json]                       # compose -> output/*.mid + manifest
midi-art generate proj.json --scene Fracture               # fast single-scene preview
midi-art generate proj.json --seed 7 --suffix var-b        # variation
midi-art report proj.json [--json]                         # metrics + visual summary, no MIDI
midi-art preview proj.json [--seeds 1,2,3] [--format html|png|both] [--open]
midi-art audio out.mid [--video r.mp4] [--json]            # .wav via FluidSynth (+ mux)
midi-art doctor [--json]                                   # check the external toolchain
midi-art setup [--only t1,t2] [--force] [--json]           # install tools into the layout
midi-art studio [proj.json]                                # desktop GUI (also: midi-art-studio)

# Legacy
midi-dense-ui                          # old Tkinter dense-song UI
python examples/generate_demos.py      # old pattern demos
```

```powershell
.venv\Scripts\python.exe -m pytest          # ~130 tests, all passing, <20s; studio tests
                                            # auto-skip if Tk has no display
.venv\Scripts\python.exe -m ruff check .    # lint (E/F/I/W, line length 100) — currently clean
```

No CI, no type checker, setuptools via `pyproject.toml`. Runtime deps: `mido` and `pillow`.
Example project committed at `projects/collapse.json`.

## Architecture of `midi_art`

The core principle: **creative intent → composition structure → note generation → MIDI
serialization** are separate stages, and the MIDI writer is the last of them, not the center.

```
Project (JSON) ──> compose() ──> Performance (NoteEvents + tempo map + spans)
                     │                      │
        generators per layer          analyze() -> PerformanceReport
        transitions per boundary      validate() -> Issues
        channel allocation                  │
                                      write_midi() -> .mid  (+ manifest via CLI)
```

- [domain/](src/midi_art/domain/) — the composition model, no MIDI knowledge.
  - `note_event.py`: `NoteEvent` (frozen dataclass, **beat-timed floats**, plus `role`,
    `layer_id`, `tags`) and `NoteRole` (melody/bass/…/visual_effect/transition). Ticks exist
    only inside the MIDI writer.
  - `automation.py`: `CurveType` + `AutomationCurve` with `value_at(beat)`; `resolve()` picks
    the last matching curve so layer automation overrides scene automation.
  - `scene.py`: `Scene` + `SceneIntent` — the artistic controls (intensity ramp with curve,
    register center/span expansion, `order` chaos↔geometry, `harmonic_stability`).
  - `layer.py`: `Layer` (role, `GeneratorConfig`, `color_group`, gain, automation).
  - `project.py`: `Project`, `MusicalSettings`, `ArtisticDirection`, and all JSON
    (de)serialization (`save`/`load`, `format_version` guard, `brief_file` link).
    Serialization is manual to_dict/from_dict — keep it in sync when adding fields;
    the schema drift test enforces this (see `schema.py`).
  - `schema.py`: **the declarative spec of the JSON document shape** (`FieldSpec` trees
    `PROJECT_SCHEMA`/`BRIEF_SCHEMA`, `enum_values` resolving live registries). Single
    source of truth consumed by both `midi-art describe` and `midi-art lint`. A drift
    test (`tests/test_art_describe.py`) asserts its paths exactly match `to_dict()`
    output — **new model fields require a schema entry or pytest fails**.
  - `brief.py`: `CreativeBrief` — the user's creative direction in the user's language
    (mood arc, imagery, energy shape; deliberately no project vocabulary). Same
    persistence pattern as `Project` (`brief_format_version` guard).
- [composition/](src/midi_art/composition/) —
  - `harmony.py`: note names, scales, progressions, `snap_to_scale`, chord building.
  - `controls.py`: **the one place** artistic sliders map to technical parameters
    (`map_intensity(value) -> GeneratorSettings`).
  - `composer.py`: `compose(project, scene_name=None) -> Performance`. Iterates scenes,
    builds a `GenerationContext` per layer, offsets scene-relative notes to absolute beats,
    applies transitions at boundaries, allocates channels. `scene_name` composes a single
    scene for fast preview.
- [generators/](src/midi_art/generators/) — plugin system. `base.py` has `NoteGenerator`
  (abstract), `GeneratorDefinition` (artistic metadata **including `params: tuple[ParamSpec]`
  — every expert param is declared there: type, default, range/choices, artistic meaning**),
  `resolve_params` (the only way generators read params), and `GenerationContext` (rng,
  intensity/register lookups, automation). Registry in `__init__.py` (`GENERATORS`,
  `get_generator`). Seven plugins: pulse, arpeggio, cascade, chord_wall, cloud, wave, mirror.
  Generators emit **scene-relative** starts and channel 0; the allocator sets real channels.
  Never read params with `params.get(...)` inline — declare a `ParamSpec` so describe/lint
  see it.
- [transitions/](src/midi_art/transitions/) — plugin system mirroring generators.
  `Transition.apply(outgoing, incoming, ctx) -> TransitionResult` may modify either scene's
  notes and/or add new ones. Metadata lives in `TransitionDefinition` (`definition` classvar;
  `name`/`description` are delegating properties). Four plugins: density_crossfade,
  sudden_silence, keyboard_sweep, chord_wall_impact. Registry `TRANSITIONS`.
- [analysis/](src/midi_art/analysis/) — `metrics.analyze()` produces `PerformanceReport`
  (density, polyphony via event sweep, per-scene counts, beats↔seconds through the tempo
  map); `validation.validate()` returns leveled `Issue`s (now with a `path` field) on the
  composed performance. `lint.py` validates the raw *document* pre-compose against
  `domain/schema.py` (unknown keys, enums with did-you-mean, ranges, generator params,
  automation targets) — `lint_document` / `lint_brief_document`. `summary.py` builds the
  compact visual summary (`report --json`'s `visual` block). Errors abort CLI export.
- [export/](src/midi_art/export/) — `zenith_profile.py` holds `ZenithExportSettings` and the
  four named profiles with runaway-generation caps; `track_allocator.py` maps layer
  `color_group`s to channels (transition notes get reserved channel 15);
  `midi_writer.py` is the **only** module that touches mido for output — enforces min note
  duration, resolves same-pitch overlaps, raises `ExportLimitError` over the hard cap.
  `audio.py` renders a `.mid` to `.wav` via external FluidSynth and muxes it into Zenith
  videos via FFmpeg (`midi-art audio`) — pure subprocess orchestration with env-var
  discovery (`FLUIDSYNTH_PATH`, `SOUNDFONT_PATH`, `FFMPEG_PATH`/Zenith folder), no
  Python audio deps.
- [preview/](src/midi_art/preview/) — Phase 6 iteration tools. `model.py` reduces a
  `Performance` to toolkit-independent drawable data (`build_preview`): piano-roll notes
  (deterministically thinned above `max_notes`, while density/polyphony stay exact),
  density-per-bar, sampled polyphony curve with the *exact* event-sweep peak, per-scene
  intensity points, and the channel color palette (`CHANNEL_COLORS`). `svg.py` renders that
  to a self-contained dark-theme HTML page (`render_html`); `png.py` renders the same
  `PreviewData` to a raster image via Pillow (`render_png`, lazy import) — the format an AI
  agent can actually look at (`midi-art preview --format png`, one image per seed).
- [presets/styles.py](src/midi_art/presets/styles.py) — three style presets, each a complete
  5-scene `Project` with an arc (intro → escalation → climax → resolution).
  `presets/scaffold.py` — `scaffold_from_brief`: the deterministic brief→project mechanics
  (style selection, duration rescaling, mood/imagery copy). Creative sculpting is agent
  judgment, documented in [docs/COMPOSING.md](docs/COMPOSING.md).
- [describe.py](src/midi_art/describe.py) — `build_contract()`: the one-read authoring
  contract behind `midi-art describe`, assembled from `domain/schema.py` and the live
  registries. New registry entries and ParamSpecs appear there automatically.
- [app/cli.py](src/midi_art/app/cli.py) — argparse CLI (`midi-art`), returns exit codes.
  `--json` on lint/generate/report/preview emits exactly one compact JSON object to stdout
  (errors become `{"ok": false, "error": ...}`). Writes a v2 `.manifest.json` (seed,
  profile, report, issues, project sha256, tool version, brief link) beside every exported
  `.mid`.
- [app/desktop.py](src/midi_art/app/desktop.py) — Phase 7: `midi-art studio` /
  `midi-art-studio`, a Tkinter app (`StudioApp`) organized around the four work areas:
  project (wizard + style browser), timeline (scene Treeview with add/remove/reorder),
  scene editor (intent sliders, transition picker, layer inspector via `LayerDialog` with
  generator descriptions), and preview/analysis (canvas piano roll + density + polyphony,
  report text, async compose/export on worker threads with `root.after` callbacks).
  The Advanced toggle reveals order/stability/register controls, export profile, and raw
  generator params (JSON). Domain objects are frozen — all edits go through
  `dataclasses.replace` + `_replace_scene`.

## Invariants to preserve

- **Determinism is a contract.** Same project file + seed ⇒ byte-identical MIDI
  (tests assert it). Each layer uses `random.Random(f"{seed}:{scene_index}:{scene}:{layer}")`
  so editing one layer never reshuffles others; transitions have their own streams. Never
  use the global `random` module or unseeded RNGs in generators/transitions.
- **NoteEvents are beat-timed.** Only `export/midi_writer.py` converts to ticks (480/beat).
- **Generators/transitions never write MIDI** and never pick channels; the allocator does.
- **`composition/controls.py` is the only artistic→technical mapping point.** Don't scatter
  intensity math into generators.
- **Serialization round-trip**: `Project.from_dict(project.to_dict()) == project` (tested).
  New model fields need defaults + to_dict/from_dict updates **+ a `FieldSpec` in
  `domain/schema.py`** — the drift test fails otherwise. Same contract for `CreativeBrief`.
- **Generator params are declared, not improvised**: every param a generator reads must have
  a `ParamSpec` in its `GeneratorDefinition` and be read via `resolve_params`. That is what
  makes it visible to `describe` and checkable by `lint`.
- **`from_dict` stays lenient; `lint` is the strict layer.** Never make loading reject
  unknown keys — the studio and old files depend on leniency; put authoring checks in
  `analysis/lint.py` instead.
- **Runaway-generation guards stay on**: profile caps in export, validation before export in
  the CLI.
- Registries (`GENERATORS`, `TRANSITIONS`, `STYLES`, `PROFILES`) are the extension points —
  new plugins register there and become CLI-, describe-, and lint-visible automatically.
- `GeneratorSettings.polyphony` and `ornament_probability` are computed but currently only
  partially consumed (arpeggio uses ornaments) — reserved; don't document them as active
  controls.
- Non-major/minor scales intentionally share `DEFAULT_PROGRESSION` (documented in
  `describe` output as "default (minor-like)") — changing that would reshuffle existing
  projects' harmony, so treat it as a deliberate constraint, not a bug.
- Run `pytest` and `ruff check .` before considering a change done; both are currently clean.
- Generated artifacts go to `output/` (gitignored, including manifests); project files live
  in `projects/`.

## Refactor status (against the 7-phase plan)

Done: Phase 1 (NoteEvent, centralized writer, seeds, validation, tests), Phase 2 (project/
scene/layer models + JSON persistence + per-scene generation + channel allocation), Phase 3
(artistic controls with expert params via `GeneratorConfig.params`), most of Phase 4
(automation curves, intensity/register ramps, tempo ramp, 4 transitions), most of Phase 5
(export profiles, overlap handling, caps, manifest, analysis), Phase 6 (HTML + canvas
piano-roll/density/polyphony previews, scene-only preview, multi-seed variation comparison,
warnings surfaced in both CLI and studio), Phase 7 (the `midi-art studio` desktop app with
basic/advanced modes).

Remaining: composition grammar (§18), visual-gesture vocabulary as first-class commands
(§9), named variation presets beyond seed override (§16 — "more structured", "stronger
symmetry", etc.), automation of more targets (tempo inside scenes, generator probability),
studio niceties (undo, automation curve editing, drag-reorder timeline), and
migrating/retiring the legacy `midi_app` package.

Known test-infra quirk: creating several Tk roots in one pytest process can transiently
fail Tcl init (`tcl_findLibrary`) when destroyed roots' `Variable`s are garbage-collected
mid-init; `tests/test_art_studio.py::make_studio` guards with `gc.collect()` + one retry.
Keep that pattern for new studio tests.

## Legacy `midi_app` notes

Unchanged from before the refactor: `generator.py` (note-dict → .mid funnel), `patterns.py`,
`dense_song.py` (seeded, byte-determinism tested), `ui.py` (Tkinter, ~500-line class),
`zenith.py` (`launch_zenith_preview` — still the way to open any `.mid` in Zenith),
`config.py` (dead code). Known legacy issues (unseeded `random` in patterns, misleading
`render_video()`, duplicated constants) are documented in git history; fix only if touched.
