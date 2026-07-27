# Composing with Agentic MIDI Artist — the creative process guide

Tool-neutral guidance for anyone (AI agent or human) turning a user's creative
direction into a finished performance. The mechanics live in the CLI; this
document is the judgment layer on top.

## The loop at a glance

```text
interview → brief → scaffold → sculpt → lint → generate → look → change ONE thing → repeat
```

Token/efficiency rules if you are an AI agent:

- `midi-art describe --json` is the entire authoring contract. Never read `src/`
  to discover fields, params, scales, or styles.
- Prefer `--json` on every command; never open `*-preview.html` (megabytes of SVG).
- Iterate on single scenes (`--scene <Name>`) before full regenerations.
- Outputs land in `output/`; projects and briefs live in `projects/`.

## 1. Interview the user

Ask only what shapes the piece. Five questions cover most performances:

1. **Mood arc** — how should it feel at the start, the middle, the end?
   ("calm → unraveling → catastrophic")
2. **Duration** — roughly how long? (seconds or "a few minutes")
3. **One image** — what should the audience *see* in their mind?
   ("rain on glass", "a machine tearing itself apart")
4. **One must-have moment** — the beat they'd be sad to lose.
   ("total silence right before the climax")
5. **What to avoid** — the fastest way to learn taste.
   ("nothing cheerful", "no long empty stretches")

Optionally: tempo feel, a color palette, a style preset they like
(`midi-art styles`). Don't interrogate — two or three answers plus sensible
defaults beat a ten-question form. Confirm your synthesis in one sentence
("So: a slow glassy build that shatters at ~2:30 and decays — right?") before writing.

## 2. Save the brief

Persist the answers as `projects/<slug>.brief.json` (schema: `describe --json`
→ `brief_schema`). The brief is the user's language — moods and imagery, never
scales or generator names. It survives sessions; regenerations trace back to it
through the manifest.

## 3. Scaffold

```powershell
midi-art new "Title" --brief projects/<slug>.brief.json -o projects/<slug>.json --json
```

Deterministic mechanics: picks the style skeleton (`style_hint` or
`organic_growth`), rescales scene lengths to `duration_seconds`, copies
mood/logline/imagery into `artistic_direction`, links the brief. The scaffold
is a competent default — your job is to make it *this* piece.

## 4. Sculpt — where the judgment lives

Edit the project JSON directly. Run `midi-art lint <file> --json` after every
edit; fix errors immediately, read warnings carefully (they are silent behavior
changes, not style nits).

**Imagery → generator vocabulary** (combine 2–4 layers per scene):

| The user says…                        | Reach for |
|---------------------------------------|-----------|
| rain, drizzle, static, sparkle, stars | `cloud` (scale `density_scale`), short notes |
| waterfall, run, sweep, avalanche      | `cascade` (`direction`, `runs_per_bar`) |
| waves, breathing, tide, hypnotic      | `wave` (`wavelength_bars` long, `strands` 2–3) |
| impact, slam, tower, wall, chord hits | `chord_wall` (+ `chord_wall_impact` transition) |
| heartbeat, engine, march, pulse       | `pulse` (`max_subdivision` low = calm, high = driving) |
| melody, theme, voice, song            | `arpeggio` or `mirror` |
| symmetry, reflection, kaleidoscope    | `mirror` (`supports_symmetry`) |

**Energy shape → scene intents.** The intensity ramps are the piece's
silhouette — draw the user's energy-shape prose with them:

- "slow build" → rising `intensity_start/end` across scenes, `ease_in` curves
- "cliff-edge drop" → high `intensity_end`, then a scene starting near 0 —
  or a `sudden_silence` transition
- "explosive" → `exponential` curve into a `chord_wall_impact`
- "long decay" → final scene `ease_out`, shrinking `register_span`, one layer

Register is the visual canvas: widen `register_span_*` toward climaxes (66+
fills the screen), narrow it for intimacy. `order` sets grid vs. chaos;
`harmonic_stability` sets consonance vs. dissonance — drop both as things
fall apart, restore them for resolution.

**Must-have moments** become scenes or transitions, not afterthoughts: place
them at exact bars by adjusting `duration_bars`, and name scenes after the
moment ("The Silence", "Shatter") so previews read like the story.

**Palette** words become `color_group` labels. Same group = same Zenith color;
give each visual role its own group and reuse groups across scenes for
continuity (≤16 total).

**Tempo feel**: set `tempo_start`/`tempo_end` (accelerating = rising urgency).
Check the profile fits the density ambition (`midi-art profiles`).

## 5. Generate and judge

```powershell
midi-art generate projects/<slug>.json --json     # .mid + manifest
midi-art report projects/<slug>.json --json       # metrics + "visual" block, no MIDI
midi-art preview projects/<slug>.json --format png
```

Cheap check first: the report's `visual` block. Does `density_arc` match the
energy shape? Peaks in the right scene? Unintended `gaps`? Register arc
expanding when it should?

Then **look at the PNG** and judge it against the brief like an art director:
Does the roll *look like the image the user named*? Is the climax visually
saturated? Do scene boundaries read as events? Name the ONE biggest mismatch,
change the ONE setting that fixes it, regenerate. Small deterministic steps —
never shotgun five edits between looks.

Not sure between readings? Compare dice: `--seeds 1,2,3 --format png` (same
structure, different randomness). Iterate a single scene with
`generate --scene <Name>` before re-running the whole piece.

## 6. Deliver

Ship the `.mid` (plus manifest — it records seed, profile, project hash, and
the brief, so any result is reproducible). Offer one or two seed variations.
The user renders in Zenith-MIDI; density warnings from `generate` predict
render performance, so respect them.

If the user wants sound, not just visuals: `midi-art audio output/<slug>.mid
[--video render.mp4] --json` renders the .wav via FluidSynth and can mux it
into the Zenith video. Check the toolchain first with `midi-art doctor --json`;
if something is missing, `midi-art setup --json` installs it into the standard
layout (`%LOCALAPPDATA%\midi-art\`) — downloads ~40–100 MB, so tell the user
before running it. A toolchain failure is environment setup, not your
composition — report it and continue delivering the .mid.

## Failure modes to avoid

- **Writing project JSON from memory.** The contract is `describe --json`; typos
  are silently ignored without `lint`.
- **Encoding the brief in project vocabulary.** "harmonic_minor at intensity
  0.7" belongs in the project; "menacing" belongs in the brief.
- **Wall-to-wall maximalism.** Contrast sells the climax: the loudest scene only
  works next to a quiet one, and silence is a legitimate scene.
- **Iterating blind.** Every change deserves at least the `visual` block; every
  few changes deserve the PNG.
- **Fighting the seed.** If structure is right but the dice feel wrong, change
  the seed, not the design.
