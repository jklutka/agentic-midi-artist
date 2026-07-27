"""The standard external-tool layout: one opinionated place for everything.

midi-art depends on external programs (Zenith-MIDI, FFmpeg, FluidSynth) and
assets (a SoundFont). So that any machine — and any agent working on it — can
assume where they live, they install into ONE standard per-user root:

    Windows:  %LOCALAPPDATA%\\midi-art\\        (override: MIDI_ART_HOME)
    else:     $XDG_DATA_HOME/midi-art/ or ~/.local/share/midi-art/

    <root>/zenith/       Zenith.exe, with ffmpeg.exe beside it (Zenith needs that)
    <root>/fluidsynth/   extracted FluidSynth release (…/bin/fluidsynth.exe)
    <root>/soundfonts/   *.sf2 files; `default.sf2` wins, else first alphabetically

Resolution order everywhere: explicit argument → tool env var → standard
layout → PATH. A machine using the standard layout therefore needs no
environment variables at all. `midi-art doctor` reports what resolves and
from where; `midi-art setup` downloads whatever is missing into the layout.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

TOOLS = ("zenith", "ffmpeg", "fluidsynth", "soundfont")

_FLUIDSYNTH_FALLBACK_URL = (
    "https://github.com/FluidSynth/fluidsynth/releases/download/"
    "v2.5.7/fluidsynth-v2.5.7-win10-x64-cpp11.zip"
)
_FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
_SOUNDFONT_URL = "https://github.com/mrbumpy409/GeneralUser-GS/raw/main/GeneralUser-GS.sf2"
_SOUNDFONT_NAME = "GeneralUser-GS.sf2"


# -- layout -------------------------------------------------------------------


def standard_root() -> Path:
    if env := os.environ.get("MIDI_ART_HOME"):
        return Path(env)
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        return base / "midi-art"
    base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / "midi-art"


def zenith_dir() -> Path:
    return standard_root() / "zenith"


def fluidsynth_dir() -> Path:
    return standard_root() / "fluidsynth"


def soundfont_dir() -> Path:
    return standard_root() / "soundfonts"


def _exe(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def standard_zenith() -> Path | None:
    path = zenith_dir() / "Zenith.exe"
    return path if path.exists() else None


def standard_ffmpeg() -> Path | None:
    path = zenith_dir() / _exe("ffmpeg")
    return path if path.exists() else None


def standard_fluidsynth() -> Path | None:
    if not fluidsynth_dir().exists():
        return None
    return next(iter(sorted(fluidsynth_dir().glob(f"**/{_exe('fluidsynth')}"))), None)


def standard_soundfont() -> Path | None:
    default = soundfont_dir() / "default.sf2"
    if default.exists():
        return default
    if not soundfont_dir().exists():
        return None
    return next(iter(sorted(soundfont_dir().glob("*.sf2"))), None)


# -- resolution ---------------------------------------------------------------


def _from_env(var: str) -> Path | None:
    """Resolve an env-var path; set-but-missing is an error, not a fallthrough."""
    if env := os.environ.get(var):
        path = Path(env)
        if not path.exists():
            raise FileNotFoundError(f"{var} points to a missing file: {path}")
        return path
    return None


def resolve(tool: str, explicit: str | Path | None = None) -> tuple[Path | None, str | None]:
    """Locate a tool. Returns (path, source) — source is how it was found:
    'explicit' | 'env' | 'standard' | 'path' — or (None, None) if not found.

    Raises FileNotFoundError if an explicit path or a set env var is broken.
    """
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"{tool} not found at: {path}")
        return path, "explicit"

    env_vars = {
        "zenith": "ZENITH_MIDI_PATH",
        "ffmpeg": "FFMPEG_PATH",
        "fluidsynth": "FLUIDSYNTH_PATH",
        "soundfont": "SOUNDFONT_PATH",
    }
    if found := _from_env(env_vars[tool]):
        return found, "env"

    standard = {
        "zenith": standard_zenith,
        "ffmpeg": standard_ffmpeg,
        "fluidsynth": standard_fluidsynth,
        "soundfont": standard_soundfont,
    }[tool]()
    if standard:
        return standard, "standard"

    if tool in ("ffmpeg", "fluidsynth"):
        if on_path := shutil.which(tool):
            return Path(on_path), "path"
    if tool == "ffmpeg":
        # Last resort: the ffmpeg sitting next to a env-var-located Zenith.
        if zenith := os.environ.get("ZENITH_MIDI_PATH"):
            candidate = Path(zenith).parent / _exe("ffmpeg")
            if candidate.exists():
                return candidate, "path"
    return None, None


# -- doctor -------------------------------------------------------------------

_HINTS = {
    "zenith": "run: midi-art setup --only zenith  (the visual renderer; optional for .mid/.wav)",
    "ffmpeg": "run: midi-art setup --only ffmpeg  (needed to mux audio into Zenith videos)",
    "fluidsynth": "run: midi-art setup --only fluidsynth  (needed for midi-art audio)",
    "soundfont": "run: midi-art setup --only soundfont  (needed for midi-art audio)",
}


@dataclass(frozen=True)
class ToolStatus:
    name: str
    found: bool
    path: str | None
    source: str | None  # explicit | env | standard | path
    hint: str = ""


def doctor() -> list[ToolStatus]:
    """Resolve every external tool and report where (or why not)."""
    statuses = []
    for tool in TOOLS:
        try:
            path, source = resolve(tool)
        except FileNotFoundError as exc:
            statuses.append(ToolStatus(tool, False, None, None, hint=str(exc)))
            continue
        hint = "" if path else _HINTS[tool]
        statuses.append(
            ToolStatus(tool, path is not None, str(path) if path else None, source, hint)
        )
    return statuses


# -- setup --------------------------------------------------------------------


def _download(url: str, label: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "midi-art-setup"})
    with urllib.request.urlopen(request) as response:  # noqa: S310 - fixed https URLs
        return response.read()


def _github_latest_asset(repo: str, match: str) -> str:
    """Download URL of the latest release asset whose name contains ``match``."""
    data = json.loads(_download(f"https://api.github.com/repos/{repo}/releases/latest", repo))
    for asset in data.get("assets", ()):
        if match in asset["name"]:
            return asset["browser_download_url"]
    raise RuntimeError(f"No release asset matching {match!r} in {repo}.")


def _extract_zip(payload: bytes, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(destination)


def _install_zenith() -> Path:
    url = _github_latest_asset("arduano/Zenith-MIDI", "Zenithx64.zip")
    _extract_zip(_download(url, "Zenith-MIDI"), zenith_dir())
    exe = next(iter(zenith_dir().glob("**/Zenith.exe")), None)
    if exe is None:
        raise RuntimeError("Zenith download did not contain Zenith.exe.")
    if exe.parent != zenith_dir():  # flatten a nested zip layout
        for item in exe.parent.iterdir():
            shutil.move(str(item), zenith_dir() / item.name)
        exe = zenith_dir() / "Zenith.exe"
    return exe


def _install_ffmpeg() -> Path:
    _extract_zip(_download(_FFMPEG_URL, "FFmpeg"), fluidsynth_dir().parent / "_ffmpeg_tmp")
    tmp = fluidsynth_dir().parent / "_ffmpeg_tmp"
    try:
        exe = next(iter(tmp.glob(f"**/{_exe('ffmpeg')}")), None)
        if exe is None:
            raise RuntimeError("FFmpeg download did not contain ffmpeg.")
        zenith_dir().mkdir(parents=True, exist_ok=True)
        target = zenith_dir() / _exe("ffmpeg")
        shutil.move(str(exe), target)
        return target
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _install_fluidsynth() -> Path:
    try:
        url = _github_latest_asset("FluidSynth/fluidsynth", "win10-x64-cpp11")
    except Exception:
        url = _FLUIDSYNTH_FALLBACK_URL
    _extract_zip(_download(url, "FluidSynth"), fluidsynth_dir())
    exe = standard_fluidsynth()
    if exe is None:
        raise RuntimeError("FluidSynth download did not contain fluidsynth.")
    return exe


def _install_soundfont() -> Path:
    soundfont_dir().mkdir(parents=True, exist_ok=True)
    target = soundfont_dir() / _SOUNDFONT_NAME
    target.write_bytes(_download(_SOUNDFONT_URL, "GeneralUser GS SoundFont"))
    return target


_INSTALLERS = {
    "zenith": _install_zenith,
    "ffmpeg": _install_ffmpeg,
    "fluidsynth": _install_fluidsynth,
    "soundfont": _install_soundfont,
}


def setup(only: tuple[str, ...] = TOOLS, force: bool = False) -> list[ToolStatus]:
    """Install missing tools into the standard layout. Returns final statuses.

    Skips tools that already resolve (anywhere) unless ``force``; ``only``
    restricts which tools are considered. Windows-only for zenith.
    """
    for tool in only:
        if tool not in TOOLS:
            raise ValueError(f"Unknown tool {tool!r}. Available: {', '.join(TOOLS)}")
    for tool in only:
        if tool == "zenith" and os.name != "nt":
            continue
        path, _source = resolve(tool)
        if path is not None and not force:
            continue
        _INSTALLERS[tool]()
    return [status for status in doctor() if status.name in only]
