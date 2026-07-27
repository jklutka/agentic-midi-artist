"""Integration with the Zenith-MIDI renderer."""

import subprocess
from pathlib import Path

# Default Zenith-MIDI install location — update this or set via environment variable
DEFAULT_ZENITH_PATH = Path.home() / "Zenith-MIDI" / "Zenith.exe"


def find_zenith_exe(zenith_path: str | Path | None = None) -> Path:
    """Locate the Zenith-MIDI executable.

    Args:
        zenith_path: Explicit path to Zenith.exe. Falls back to DEFAULT_ZENITH_PATH.

    Returns:
        Path to the Zenith executable.

    Raises:
        FileNotFoundError: If the executable is not found.
    """
    import os

    if zenith_path:
        path = Path(zenith_path)
    elif env_path := os.environ.get("ZENITH_MIDI_PATH"):
        path = Path(env_path)
    else:
        # The standard midi-art tool layout (see midi_art.toolchain), then legacy default.
        local = Path(os.environ.get("MIDI_ART_HOME",
                                    Path(os.environ.get("LOCALAPPDATA", Path.home()))
                                    / "midi-art"))
        standard = local / "zenith" / "Zenith.exe"
        path = standard if standard.exists() else DEFAULT_ZENITH_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"Zenith-MIDI not found at: {path}\n"
            "Download from: https://github.com/arduano/Zenith-MIDI/releases\n"
            "Set the ZENITH_MIDI_PATH environment variable or pass zenith_path explicitly."
        )

    return path


def launch_zenith_preview(
    midi_file: str | Path,
    zenith_path: str | Path | None = None,
) -> subprocess.Popen:
    """Launch Zenith-MIDI in preview mode to visualize a MIDI file.

    Args:
        midi_file: Path to the .mid file to preview.
        zenith_path: Optional explicit path to Zenith.exe.

    Returns:
        The subprocess.Popen handle for the launched process.
    """
    exe = find_zenith_exe(zenith_path)
    midi_file = Path(midi_file).resolve()

    if not midi_file.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_file}")

    proc = subprocess.Popen(
        [str(exe), str(midi_file)],
        cwd=str(exe.parent),
    )
    return proc


def render_video(
    midi_file: str | Path,
    output_video: str | Path,
    zenith_path: str | Path | None = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 60,
) -> Path:
    """Render a MIDI file to video using Zenith-MIDI (requires FFmpeg next to Zenith.exe).

    Note: Zenith-MIDI's CLI rendering support is limited. This launches Zenith
    with the MIDI file — you may need to configure render settings via the GUI
    and use this as a starting point.

    Args:
        midi_file: Path to the .mid file to render.
        output_video: Desired output video path.
        zenith_path: Optional explicit path to Zenith.exe.
        width: Video width in pixels.
        height: Video height in pixels.
        fps: Frames per second.

    Returns:
        Path to the output video file.
    """
    exe = find_zenith_exe(zenith_path)
    midi_file = Path(midi_file).resolve()
    output_video = Path(output_video).resolve()
    output_video.parent.mkdir(parents=True, exist_ok=True)

    if not midi_file.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_file}")

    # Zenith-MIDI is primarily GUI-driven. Launch it with the file for manual rendering.
    # For automated pipelines, consider using the preview + screen capture approach.
    proc = subprocess.Popen(
        [str(exe), str(midi_file)],
        cwd=str(exe.parent),
    )
    proc.wait()

    return output_video
