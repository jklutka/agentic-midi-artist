"""Standard tool layout: resolution precedence, doctor, and setup."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from midi_art import toolchain
from midi_art.app.cli import main

EXE = ".exe" if os.name == "nt" else ""


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def _standard_fluidsynth() -> Path:
    return _touch(toolchain.fluidsynth_dir() / "bin" / f"fluidsynth{EXE}")


def test_standard_root_respects_midi_art_home(tmp_path, monkeypatch):
    monkeypatch.setenv("MIDI_ART_HOME", str(tmp_path / "custom"))
    assert toolchain.standard_root() == tmp_path / "custom"


def test_resolve_missing_everywhere(monkeypatch):
    monkeypatch.setattr(toolchain.shutil, "which", lambda _name: None)
    assert toolchain.resolve("fluidsynth") == (None, None)


def test_resolve_standard_beats_path(monkeypatch):
    standard = _standard_fluidsynth()
    monkeypatch.setattr(toolchain.shutil, "which", lambda _name: "C:/elsewhere/fluidsynth.exe")
    assert toolchain.resolve("fluidsynth") == (standard, "standard")


def test_resolve_env_beats_standard(tmp_path, monkeypatch):
    _standard_fluidsynth()
    env_exe = _touch(tmp_path / "custom-fluidsynth.exe")
    monkeypatch.setenv("FLUIDSYNTH_PATH", str(env_exe))
    assert toolchain.resolve("fluidsynth") == (env_exe, "env")


def test_resolve_explicit_beats_env(tmp_path, monkeypatch):
    env_exe = _touch(tmp_path / "env-fluidsynth.exe")
    monkeypatch.setenv("FLUIDSYNTH_PATH", str(env_exe))
    explicit = _touch(tmp_path / "explicit-fluidsynth.exe")
    assert toolchain.resolve("fluidsynth", explicit) == (explicit, "explicit")


def test_resolve_broken_env_raises(monkeypatch):
    monkeypatch.setenv("FLUIDSYNTH_PATH", "C:/nope/fluidsynth.exe")
    with pytest.raises(FileNotFoundError, match="FLUIDSYNTH_PATH"):
        toolchain.resolve("fluidsynth")


def test_soundfont_default_wins():
    _touch(toolchain.soundfont_dir() / "aaa-first.sf2")
    assert toolchain.resolve("soundfont")[0] == toolchain.soundfont_dir() / "aaa-first.sf2"
    default = _touch(toolchain.soundfont_dir() / "default.sf2")
    assert toolchain.resolve("soundfont") == (default, "standard")


def test_standard_zenith_and_ffmpeg():
    assert toolchain.resolve("zenith") == (None, None)
    zenith = _touch(toolchain.zenith_dir() / "Zenith.exe")
    ffmpeg = _touch(toolchain.zenith_dir() / f"ffmpeg{EXE}")
    assert toolchain.resolve("zenith") == (zenith, "standard")
    assert toolchain.resolve("ffmpeg") == (ffmpeg, "standard")


def test_doctor_reports_found_and_missing(monkeypatch):
    monkeypatch.setattr(toolchain.shutil, "which", lambda _name: None)
    _standard_fluidsynth()
    statuses = {status.name: status for status in toolchain.doctor()}
    assert set(statuses) == set(toolchain.TOOLS)
    assert statuses["fluidsynth"].found and statuses["fluidsynth"].source == "standard"
    assert not statuses["soundfont"].found
    assert "setup --only soundfont" in statuses["soundfont"].hint


def test_setup_skips_present_installs_missing(monkeypatch):
    monkeypatch.setattr(toolchain.shutil, "which", lambda _name: None)
    _standard_fluidsynth()
    installed = []
    for tool in toolchain.TOOLS:
        def _fake(tool=tool):
            installed.append(tool)
            if tool == "soundfont":
                return _touch(toolchain.soundfont_dir() / "default.sf2")
            if tool == "zenith":
                return _touch(toolchain.zenith_dir() / "Zenith.exe")
            if tool == "ffmpeg":
                return _touch(toolchain.zenith_dir() / f"ffmpeg{EXE}")
            return _standard_fluidsynth()
        monkeypatch.setitem(toolchain._INSTALLERS, tool, _fake)

    statuses = toolchain.setup(only=("fluidsynth", "soundfont"))
    assert installed == ["soundfont"]  # fluidsynth already resolved
    assert all(status.found for status in statuses)


def test_setup_force_reinstalls(monkeypatch):
    _standard_fluidsynth()
    installed = []
    monkeypatch.setitem(
        toolchain._INSTALLERS, "fluidsynth",
        lambda: installed.append("fluidsynth") or _standard_fluidsynth(),
    )
    toolchain.setup(only=("fluidsynth",), force=True)
    assert installed == ["fluidsynth"]


def test_setup_unknown_tool_raises():
    with pytest.raises(ValueError, match="Unknown tool"):
        toolchain.setup(only=("winamp",))


def test_cli_doctor_json(monkeypatch, capsys):
    monkeypatch.setattr(toolchain.shutil, "which", lambda _name: None)
    assert main(["doctor", "--json"]) == 1  # empty layout -> missing tools
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["root"] == str(toolchain.standard_root())
    assert {tool["name"] for tool in payload["tools"]} == set(toolchain.TOOLS)

    _standard_fluidsynth()
    _touch(toolchain.soundfont_dir() / "default.sf2")
    _touch(toolchain.zenith_dir() / "Zenith.exe")
    _touch(toolchain.zenith_dir() / f"ffmpeg{EXE}")
    assert main(["doctor", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_cli_setup_only_json(monkeypatch, capsys):
    monkeypatch.setattr(toolchain.shutil, "which", lambda _name: None)
    monkeypatch.setitem(
        toolchain._INSTALLERS, "soundfont",
        lambda: _touch(toolchain.soundfont_dir() / "default.sf2"),
    )
    assert main(["setup", "--only", "soundfont", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert [tool["name"] for tool in payload["tools"]] == ["soundfont"]
