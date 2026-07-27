"""Tests for audio rendering: FluidSynth/FFmpeg discovery, commands, CLI wiring."""

from pathlib import Path

import pytest

from midi_art.app.cli import main
from midi_art.export import audio


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def test_fluidsynth_command_shape(tmp_path: Path):
    command = audio.fluidsynth_command(
        Path("fluidsynth"), tmp_path / "font.sf2", tmp_path / "in.mid",
        tmp_path / "out.wav", sample_rate=48000, gain=0.4, polyphony=512,
    )
    assert command[0] == "fluidsynth"
    assert "-ni" in command
    assert command[command.index("-g") + 1] == "0.4"
    assert command[command.index("-r") + 1] == "48000"
    assert command[command.index("-o") + 1] == "synth.polyphony=512"
    assert command[command.index("-F") + 1] == str(tmp_path / "out.wav")
    # fluidsynth expects: [options] soundfont midifile
    assert command[-2:] == [str(tmp_path / "font.sf2"), str(tmp_path / "in.mid")]


def test_ffmpeg_mux_command_copies_video_and_encodes_audio(tmp_path: Path):
    command = audio.ffmpeg_mux_command(
        Path("ffmpeg"), tmp_path / "v.mp4", tmp_path / "a.wav", tmp_path / "out.mp4"
    )
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[command.index("-c:a") + 1] == "aac"
    assert "-shortest" in command
    assert command[-1] == str(tmp_path / "out.mp4")


def test_find_soundfont_env_var(tmp_path: Path, monkeypatch):
    font = _touch(tmp_path / "font.sf2")
    monkeypatch.setenv("SOUNDFONT_PATH", str(font))
    assert audio.find_soundfont() == font


def test_find_soundfont_missing_raises(monkeypatch):
    monkeypatch.delenv("SOUNDFONT_PATH", raising=False)
    with pytest.raises(FileNotFoundError, match="SOUNDFONT_PATH"):
        audio.find_soundfont()


def test_find_ffmpeg_falls_back_to_zenith_folder(tmp_path: Path, monkeypatch):
    from midi_art import toolchain

    zenith = _touch(tmp_path / "zenith" / "Zenith.exe")
    ffmpeg = _touch(tmp_path / "zenith" / toolchain._exe("ffmpeg"))
    monkeypatch.setenv("ZENITH_MIDI_PATH", str(zenith))
    monkeypatch.setattr(toolchain.shutil, "which", lambda _name: None)
    assert audio.find_ffmpeg() == ffmpeg


def test_render_wav_missing_midi_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="MIDI file not found"):
        audio.render_wav(tmp_path / "nope.mid")


def test_mux_output_defaults_next_to_video(tmp_path: Path, monkeypatch):
    video = _touch(tmp_path / "render.mp4")
    wav = _touch(tmp_path / "render.wav")
    monkeypatch.setattr(audio, "find_ffmpeg", lambda explicit=None: Path("ffmpeg"))
    calls = []
    monkeypatch.setattr(audio, "_run", lambda command, tool: calls.append(command))
    output = audio.mux_audio(video, wav)
    assert output == tmp_path / "render-audio.mp4"
    assert calls and calls[0][-1] == str(output)


def test_cli_audio_renders_and_muxes(tmp_path: Path, monkeypatch, capsys):
    midi = _touch(tmp_path / "piece.mid")
    font = _touch(tmp_path / "font.sf2")
    video = _touch(tmp_path / "piece.mp4")
    monkeypatch.setattr(audio, "find_fluidsynth", lambda explicit=None: Path("fluidsynth"))
    monkeypatch.setattr(audio, "find_ffmpeg", lambda explicit=None: Path("ffmpeg"))

    def fake_run(command, tool):
        if tool == "FluidSynth":
            _touch(Path(command[command.index("-F") + 1]))

    monkeypatch.setattr(audio, "_run", fake_run)
    assert main(["audio", str(midi), "--soundfont", str(font),
                 "--video", str(video)]) == 0
    out = capsys.readouterr().out
    assert str(tmp_path / "piece.wav") in out
    assert str(tmp_path / "piece-audio.mp4") in out


def test_cli_audio_json(tmp_path: Path, monkeypatch, capsys):
    import json

    midi = _touch(tmp_path / "piece.mid")
    font = _touch(tmp_path / "font.sf2")
    monkeypatch.setattr(audio, "find_fluidsynth", lambda explicit=None: Path("fluidsynth"))

    def fake_run(command, tool):
        if tool == "FluidSynth":
            _touch(Path(command[command.index("-F") + 1]))

    monkeypatch.setattr(audio, "_run", fake_run)
    assert main(["audio", str(midi), "--soundfont", str(font), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["files"]["wav"] == str(tmp_path / "piece.wav")
    assert payload["files"]["video"] is None


def test_cli_audio_without_soundfont_errors(tmp_path: Path, monkeypatch, capsys):
    midi = _touch(tmp_path / "piece.mid")
    monkeypatch.delenv("SOUNDFONT_PATH", raising=False)
    monkeypatch.setattr(audio, "find_fluidsynth", lambda explicit=None: Path("fluidsynth"))
    assert main(["audio", str(midi)]) == 1
    assert "SOUNDFONT_PATH" in capsys.readouterr().err
