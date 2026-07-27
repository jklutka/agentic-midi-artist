"""Presets: styles that configure the entire engine, not just one generator."""

from .scaffold import scaffold_from_brief
from .styles import STYLES, build_style, style_names

__all__ = ["STYLES", "build_style", "scaffold_from_brief", "style_names"]
