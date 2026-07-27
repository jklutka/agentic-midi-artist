---
name: compose-midi-art
description: Compose a Zenith-MIDI visual performance with Agentic MIDI Artist from the user's creative direction — interview, brief, scaffold, sculpt, lint, generate, judge the PNG, iterate. Use when the user wants a MIDI piece, song, or visual performance made.
---

Follow [docs/COMPOSING.md](../../../docs/COMPOSING.md) — it is the complete,
tool-neutral process guide (interview checklist, brief format, imagery→generator
judgment table, iteration discipline).

Ground rules from [AGENTS.md](../../../AGENTS.md): get the authoring contract from
`midi-art describe --json` (never read `src/`), run `midi-art lint <file> --json`
after every project edit, prefer `--json` on all commands, judge results with
`midi-art report --json` (the `visual` block) and `midi-art preview --format png`,
and never open `*-preview.html`.
