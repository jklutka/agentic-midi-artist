# CLAUDE.md

This repository is **Agentic MIDI Artist** (CLI: `midi-art`) — an agent-first generative
performance composer for visually dramatic MIDI art.

Read [AGENTS.md](AGENTS.md) — it is the canonical agent guide for this repository
(its "Composing (agent workflow)" section covers making performances; the rest covers
changing source).

When composing a performance for a user, follow [docs/COMPOSING.md](docs/COMPOSING.md):
interview → brief → scaffold → sculpt → lint → generate → look at the PNG → iterate.

Quick rules: start with `midi-art describe --json` (never read `src/` to discover
parameters), prefer `--json` on every command, and never open `*-preview.html`.
