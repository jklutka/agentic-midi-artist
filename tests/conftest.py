"""Shared fixtures: isolate tests from the machine's real tool installs."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_toolchain(tmp_path, monkeypatch):
    """Point the standard tool layout at an empty temp dir and clear tool env vars.

    Without this, tests would pass or fail depending on whether the machine
    has Zenith/FluidSynth/a SoundFont installed in the standard location.
    """
    monkeypatch.setenv("MIDI_ART_HOME", str(tmp_path / "midi-art-home"))
    for var in ("ZENITH_MIDI_PATH", "FFMPEG_PATH", "FLUIDSYNTH_PATH", "SOUNDFONT_PATH"):
        monkeypatch.delenv(var, raising=False)
