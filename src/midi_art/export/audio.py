"""Audio rendering: .mid -> .wav via FluidSynth, optionally muxed into a Zenith video.

The .mid this package writes is silent note data; FluidSynth plays it through a
SoundFont (.sf2) to produce audio, and FFmpeg muxes that audio into the video
Zenith rendered from the same .mid. Both start at tick 0, so no offset is needed.

Executable discovery is delegated to :mod:`midi_art.toolchain`: explicit path,
then the tool's env var (FLUIDSYNTH_PATH / FFMPEG_PATH / SOUNDFONT_PATH), then
the standard layout under ``%LOCALAPPDATA%\\midi-art``, then PATH. A machine
prepared with ``midi-art setup`` needs no configuration at all.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .. import toolchain

DEFAULT_SAMPLE_RATE = 44100
# Dense output clips easily and exhausts FluidSynth's default 256 voices,
# so default well above the analyzer's typical peak polyphony and well below 1.0 gain.
DEFAULT_GAIN = 0.5
DEFAULT_POLYPHONY = 1024


def find_fluidsynth(explicit: str | Path | None = None) -> Path:
    path, _source = toolchain.resolve("fluidsynth", explicit)
    if path is None:
        raise FileNotFoundError(
            "FluidSynth not found. Run 'midi-art setup --only fluidsynth' to install "
            "it into the standard layout, or set the FLUIDSYNTH_PATH environment variable."
        )
    return path


def find_ffmpeg(explicit: str | Path | None = None) -> Path:
    path, _source = toolchain.resolve("ffmpeg", explicit)
    if path is None:
        raise FileNotFoundError(
            "FFmpeg not found. Run 'midi-art setup --only ffmpeg' to install it next "
            "to Zenith in the standard layout, set FFMPEG_PATH, or add it to PATH."
        )
    return path


def find_soundfont(explicit: str | Path | None = None) -> Path:
    path, _source = toolchain.resolve("soundfont", explicit)
    if path is None:
        raise FileNotFoundError(
            "No SoundFont found. Run 'midi-art setup --only soundfont' to install "
            "GeneralUser GS into the standard layout, pass --soundfont, or set the "
            "SOUNDFONT_PATH environment variable."
        )
    return path


def fluidsynth_command(
    fluidsynth: Path,
    soundfont: Path,
    midi_file: Path,
    wav_file: Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    gain: float = DEFAULT_GAIN,
    polyphony: int = DEFAULT_POLYPHONY,
) -> list[str]:
    return [
        str(fluidsynth),
        "-ni",
        "-g", str(gain),
        "-r", str(sample_rate),
        "-o", f"synth.polyphony={polyphony}",
        "-F", str(wav_file),
        str(soundfont),
        str(midi_file),
    ]


def ffmpeg_mux_command(ffmpeg: Path, video_file: Path, wav_file: Path,
                       output: Path) -> list[str]:
    return [
        str(ffmpeg),
        "-y",
        "-i", str(video_file),
        "-i", str(wav_file),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output),
    ]


def render_wav(
    midi_file: str | Path,
    wav_file: str | Path | None = None,
    soundfont: str | Path | None = None,
    fluidsynth: str | Path | None = None,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    gain: float = DEFAULT_GAIN,
    polyphony: int = DEFAULT_POLYPHONY,
) -> Path:
    """Render a .mid to a .wav through a SoundFont. Returns the .wav path."""
    midi_file = Path(midi_file).resolve()
    if not midi_file.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_file}")
    wav_file = Path(wav_file).resolve() if wav_file else midi_file.with_suffix(".wav")
    wav_file.parent.mkdir(parents=True, exist_ok=True)

    command = fluidsynth_command(
        find_fluidsynth(fluidsynth), find_soundfont(soundfont), midi_file, wav_file,
        sample_rate=sample_rate, gain=gain, polyphony=polyphony,
    )
    _run(command, "FluidSynth")
    if not wav_file.exists():
        raise RuntimeError(f"FluidSynth finished but produced no file at {wav_file}")
    return wav_file


def mux_audio(
    video_file: str | Path,
    wav_file: str | Path,
    output: str | Path | None = None,
    ffmpeg: str | Path | None = None,
) -> Path:
    """Mux a .wav into a video (video stream copied, audio encoded as AAC)."""
    video_file = Path(video_file).resolve()
    wav_file = Path(wav_file).resolve()
    for path, label in ((video_file, "Video"), (wav_file, "Audio")):
        if not path.exists():
            raise FileNotFoundError(f"{label} file not found: {path}")
    if output:
        output = Path(output).resolve()
    else:
        output = video_file.with_name(f"{video_file.stem}-audio{video_file.suffix}")
    if output == video_file:
        raise ValueError("Output path must differ from the input video.")
    output.parent.mkdir(parents=True, exist_ok=True)

    _run(ffmpeg_mux_command(find_ffmpeg(ffmpeg), video_file, wav_file, output), "FFmpeg")
    return output


def _run(command: list[str], tool: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join((result.stderr or result.stdout or "").splitlines()[-8:])
        raise RuntimeError(f"{tool} failed (exit {result.returncode}):\n{tail}")
