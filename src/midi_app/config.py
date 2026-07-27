"""Configuration for Zenith-MIDI paths and render settings."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ZenithConfig:
    """Configuration for Zenith-MIDI integration."""

    zenith_exe: Path | None = None
    ffmpeg_path: Path | None = None
    output_dir: Path = field(default_factory=lambda: Path("renders"))
    midi_output_dir: Path = field(default_factory=lambda: Path("output"))

    # Render settings
    width: int = 1920
    height: int = 1080
    fps: int = 60

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.midi_output_dir.mkdir(parents=True, exist_ok=True)
