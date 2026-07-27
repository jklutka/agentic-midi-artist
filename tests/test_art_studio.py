"""Smoke tests for the desktop studio (skipped where no display is available)."""

import gc
import tkinter as tk

import pytest

from midi_art.domain.project import Project
from midi_art.presets import build_style


def make_studio(tmp_path):
    from midi_art.app.desktop import StudioApp

    project_path = tmp_path / "studio.json"
    build_style("controlled_chaos", "Studio Test", 3).save(project_path)
    # Collect Tk Variables left from a previously destroyed root: their
    # deferred cleanup can corrupt the next Tcl interpreter's init.
    gc.collect()
    try:
        return StudioApp(str(project_path))
    except tk.TclError:
        gc.collect()
        try:
            return StudioApp(str(project_path))  # one retry for transient Tcl init flakes
        except tk.TclError as exc:  # headless environment
            pytest.skip(f"Tk unavailable: {exc}")


def test_studio_loads_project_and_populates_timeline(tmp_path):
    app = make_studio(tmp_path)
    try:
        assert app.project is not None
        assert len(app.timeline.get_children()) == len(app.project.scenes)
        assert app.scene_name_var.get() == app.project.scenes[0].name
        assert len(app.layer_tree.get_children()) == len(app.project.scenes[0].layers)
    finally:
        app.root.destroy()


def test_studio_scene_edits_apply_to_project(tmp_path):
    app = make_studio(tmp_path)
    try:
        app.scene_name_var.set("Renamed")
        app.intensity_end_var.set(0.9)
        app._apply_scene()
        scene = app.project.scenes[0]
        assert scene.name == "Renamed"
        assert scene.intent.intensity_end == 0.9
    finally:
        app.root.destroy()


def test_studio_add_move_remove_scene(tmp_path):
    app = make_studio(tmp_path)
    try:
        original = len(app.project.scenes)
        app._add_scene()
        assert len(app.project.scenes) == original + 1
        assert app.scene_index == original
        app._move_scene(-1)
        assert app.scene_index == original - 1
        app._remove_scene()
        assert len(app.project.scenes) == original
    finally:
        app.root.destroy()


def test_studio_save_round_trips(tmp_path):
    app = make_studio(tmp_path)
    try:
        app.seed_var.set("777")
        app.project_path = tmp_path / "saved.json"
        app._save()
        loaded = Project.load(app.project_path)
        assert loaded.seed == 777
        assert loaded == app.project
    finally:
        app.root.destroy()
