"""Agentic MIDI Artist Studio: the desktop interface for composing performances
(launched via ``midi-art studio`` or ``midi-art-studio``).

Organized around creative decisions, per the four work areas: project
(wizard, style browser), timeline (scene blocks), scene editor (intent +
layer inspector), and preview/analysis (piano roll, density, polyphony,
warnings, export). Advanced mode reveals expert parameters.
"""

from __future__ import annotations

import json
import random as _random
import threading
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..analysis.metrics import analyze
from ..analysis.validation import IssueLevel, validate
from ..composition.composer import Performance, compose
from ..domain.automation import CurveType
from ..domain.layer import GeneratorConfig, Layer, LayerRole
from ..domain.project import Project
from ..domain.scene import Scene, SceneIntent
from ..export.midi_writer import write_midi
from ..export.zenith_profile import PROFILES
from ..generators import GENERATORS
from ..presets import STYLES, build_style
from ..preview import CHANNEL_COLORS, PreviewData, build_preview
from ..transitions import TRANSITIONS

BG = "#101216"
PANEL = "#171a20"
FIELD = "#0e1116"
TEXT = "#d5dbe3"
MUTED = "#9aa4b2"
ACCENT = "#e8c15a"
GRID = "#262b33"

NO_TRANSITION = "(none)"


class StudioApp:
    def __init__(self, project_path: str | None = None) -> None:
        self.root = tk.Tk()
        self.root.title("Agentic MIDI Artist Studio")
        self.root.geometry("1360x860")
        self.root.minsize(1100, 700)
        self.root.configure(bg=BG)

        self.project: Project | None = None
        self.project_path: Path | None = None
        self.scene_index: int | None = None
        self.performance: Performance | None = None

        self._build_styles()
        self._build_layout()

        if project_path:
            self._open_project(Path(project_path))
        else:
            self._new_project_dialog(initial=True)

    # -- styling --------------------------------------------------------------

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("App.TLabel", background=PANEL, foreground=TEXT,
                        font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("Bar.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=PANEL, foreground="#f3f4f6",
                        font=("Segoe UI", 11, "bold"))
        style.configure("App.TEntry", fieldbackground=FIELD, foreground=TEXT)
        style.configure("App.TSpinbox", fieldbackground=FIELD, foreground=TEXT,
                        arrowsize=12)
        style.configure("App.TCombobox", fieldbackground=FIELD, foreground=TEXT)
        style.configure("Accent.TButton", background="#7c9bff", foreground="#0b1020",
                        font=("Segoe UI", 10, "bold"), padding=(12, 6))
        style.map("Accent.TButton",
                  background=[("active", "#93adff"), ("pressed", "#6784ef")])
        style.configure("App.TCheckbutton", background=PANEL, foreground=TEXT)
        style.configure("Horizontal.TScale", background=PANEL)

    # -- layout ---------------------------------------------------------------

    def _build_layout(self) -> None:
        bar = ttk.Frame(self.root, style="App.TFrame", padding=(12, 10))
        bar.pack(fill="x")
        for label, command in (
            ("New", self._new_project_dialog),
            ("Open", self._open_dialog),
            ("Save", self._save),
            ("Save As", self._save_as),
        ):
            ttk.Button(bar, text=label, command=command).pack(side="left", padx=(0, 6))

        ttk.Label(bar, text="Seed", style="Bar.TLabel").pack(side="left", padx=(18, 4))
        self.seed_var = tk.StringVar(value="0")
        ttk.Entry(bar, textvariable=self.seed_var, width=10, style="App.TEntry").pack(
            side="left")
        ttk.Button(bar, text="Reroll", command=self._reroll_seed).pack(side="left", padx=6)

        self.advanced_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Advanced", variable=self.advanced_var,
                        style="App.TCheckbutton",
                        command=self._toggle_advanced).pack(side="left", padx=18)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(bar, textvariable=self.status_var, style="Bar.TLabel").pack(
            side="right")

        body = ttk.Frame(self.root, style="App.TFrame", padding=(12, 0, 12, 12))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="App.TFrame")
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        self._build_timeline_panel(left)
        self._build_scene_editor(left)

        right = ttk.Frame(body, style="App.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=1)
        self._build_preview_panel(right)
        self._build_report_panel(right)

    def _build_timeline_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        panel.pack(fill="x")
        ttk.Label(panel, text="Timeline", style="Title.TLabel").pack(anchor="w")

        self.timeline = ttk.Treeview(
            panel, columns=("bars", "intensity", "transition"), show="tree headings",
            height=7, selectmode="browse")
        self.timeline.heading("#0", text="Scene")
        self.timeline.column("#0", width=150)
        for column, title, width in (("bars", "Bars", 46),
                                     ("intensity", "Intensity", 74),
                                     ("transition", "Transition", 120)):
            self.timeline.heading(column, text=title)
            self.timeline.column(column, width=width, anchor="center")
        self.timeline.pack(fill="x", pady=(8, 8))
        self.timeline.bind("<<TreeviewSelect>>", self._on_scene_selected)

        buttons = ttk.Frame(panel, style="Panel.TFrame")
        buttons.pack(fill="x")
        for index, (label, command) in enumerate((
            ("Add", self._add_scene),
            ("Remove", self._remove_scene),
            ("Up", lambda: self._move_scene(-1)),
            ("Down", lambda: self._move_scene(1)),
        )):
            buttons.columnconfigure(index, weight=1)
            ttk.Button(buttons, text=label, command=command).grid(
                row=0, column=index, sticky="ew", padx=2)

    def _build_scene_editor(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        panel.pack(fill="both", expand=True, pady=(12, 0))
        ttk.Label(panel, text="Scene", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        panel.columnconfigure(1, weight=1)

        self.scene_name_var = tk.StringVar()
        self.scene_bars_var = tk.IntVar(value=16)
        self.transition_var = tk.StringVar(value=NO_TRANSITION)
        self.intensity_start_var = tk.DoubleVar(value=0.2)
        self.intensity_end_var = tk.DoubleVar(value=0.5)
        self.curve_var = tk.StringVar(value=CurveType.LINEAR.value)
        self.order_var = tk.DoubleVar(value=0.7)
        self.stability_var = tk.DoubleVar(value=0.8)
        self.register_center_var = tk.IntVar(value=64)
        self.register_start_var = tk.IntVar(value=24)
        self.register_end_var = tk.IntVar(value=36)

        row = 1
        row = self._grid_entry(panel, row, "Name", self.scene_name_var)
        row = self._grid_spin(panel, row, "Bars", self.scene_bars_var, 1, 256)
        row = self._grid_combo(panel, row, "Transition out", self.transition_var,
                               [NO_TRANSITION, *sorted(TRANSITIONS)])
        row = self._grid_scale(panel, row, "Intensity start", self.intensity_start_var)
        row = self._grid_scale(panel, row, "Intensity end", self.intensity_end_var)
        row = self._grid_combo(panel, row, "Intensity curve", self.curve_var,
                               [curve.value for curve in CurveType])

        self.advanced_frame = ttk.Frame(panel, style="Panel.TFrame")
        self.advanced_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.advanced_frame.columnconfigure(1, weight=1)
        adv_row = 0
        adv_row = self._grid_scale(self.advanced_frame, adv_row, "Order",
                                   self.order_var)
        adv_row = self._grid_scale(self.advanced_frame, adv_row, "Harmonic stability",
                                   self.stability_var)
        adv_row = self._grid_spin(self.advanced_frame, adv_row, "Register center",
                                  self.register_center_var, 21, 108)
        adv_row = self._grid_spin(self.advanced_frame, adv_row, "Span start",
                                  self.register_start_var, 4, 87)
        adv_row = self._grid_spin(self.advanced_frame, adv_row, "Span end",
                                  self.register_end_var, 4, 87)
        self.advanced_frame.grid_remove()
        row += 1

        ttk.Label(panel, text="Layers", style="Title.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 4))
        row += 1
        self.layer_tree = ttk.Treeview(
            panel, columns=("role", "generator", "color", "gain"), show="tree headings",
            height=5, selectmode="browse")
        self.layer_tree.heading("#0", text="Layer")
        self.layer_tree.column("#0", width=110)
        for column, title, width in (("role", "Role", 90), ("generator", "Generator", 90),
                                     ("color", "Color", 70), ("gain", "Gain", 46)):
            self.layer_tree.heading(column, text=title)
            self.layer_tree.column(column, width=width, anchor="center")
        self.layer_tree.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1

        layer_buttons = ttk.Frame(panel, style="Panel.TFrame")
        layer_buttons.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 8))
        for index, (label, command) in enumerate((
            ("Add", self._add_layer),
            ("Edit", self._edit_layer),
            ("Remove", self._remove_layer),
        )):
            layer_buttons.columnconfigure(index, weight=1)
            ttk.Button(layer_buttons, text=label, command=command).grid(
                row=0, column=index, sticky="ew", padx=2)
        row += 1

        actions = ttk.Frame(panel, style="Panel.TFrame")
        actions.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Button(actions, text="Apply Scene", command=self._apply_scene).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(actions, text="Preview Scene", command=self._preview_scene).grid(
            row=0, column=1, sticky="ew", padx=(4, 0))

    def _build_preview_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        header = ttk.Frame(panel, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(header, text="Preview", style="Title.TLabel").pack(side="left")
        self.profile_var = tk.StringVar(value="zenith_standard")
        self.profile_combo = ttk.Combobox(
            header, textvariable=self.profile_var, values=sorted(PROFILES),
            state="readonly", width=24)
        self.profile_combo.pack(side="right", padx=(6, 0))
        self.profile_combo.pack_forget()  # advanced-only
        ttk.Button(header, text="Export MIDI", style="Accent.TButton",
                   command=self._export_midi).pack(side="right", padx=(6, 0))
        ttk.Button(header, text="Preview Performance",
                   command=self._preview_full).pack(side="right")

        self.canvas = tk.Canvas(panel, bg=FIELD, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")

    def _build_report_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        panel.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        ttk.Label(panel, text="Analysis", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        self.report_text = tk.Text(panel, height=8, bg=FIELD, fg=TEXT, bd=0,
                                   font=("Consolas", 9), state="disabled", wrap="word")
        self.report_text.grid(row=1, column=0, sticky="nsew")

    # -- small grid helpers ----------------------------------------------------

    def _grid_entry(self, parent, row: int, label: str, variable) -> int:
        ttk.Label(parent, text=label, style="App.TLabel").grid(
            row=row, column=0, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=variable, style="App.TEntry").grid(
            row=row, column=1, sticky="ew", padx=(10, 0), pady=3)
        return row + 1

    def _grid_spin(self, parent, row: int, label: str, variable, low: int,
                   high: int) -> int:
        ttk.Label(parent, text=label, style="App.TLabel").grid(
            row=row, column=0, sticky="w", pady=3)
        ttk.Spinbox(parent, from_=low, to=high, textvariable=variable, width=8,
                    style="App.TSpinbox").grid(row=row, column=1, sticky="w",
                                               padx=(10, 0), pady=3)
        return row + 1

    def _grid_combo(self, parent, row: int, label: str, variable, values) -> int:
        ttk.Label(parent, text=label, style="App.TLabel").grid(
            row=row, column=0, sticky="w", pady=3)
        ttk.Combobox(parent, textvariable=variable, values=list(values),
                     state="readonly", width=18).grid(row=row, column=1, sticky="w",
                                                      padx=(10, 0), pady=3)
        return row + 1

    def _grid_scale(self, parent, row: int, label: str, variable) -> int:
        ttk.Label(parent, text=label, style="App.TLabel").grid(
            row=row, column=0, sticky="w", pady=3)
        holder = ttk.Frame(parent, style="Panel.TFrame")
        holder.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=3)
        holder.columnconfigure(0, weight=1)
        ttk.Scale(holder, from_=0.0, to=1.0, variable=variable).grid(
            row=0, column=0, sticky="ew")
        value_label = ttk.Label(holder, style="Muted.TLabel", width=5)
        value_label.grid(row=0, column=1, padx=(6, 0))

        def refresh(*_: object) -> None:
            value_label.configure(text=f"{variable.get():.2f}")

        variable.trace_add("write", refresh)
        refresh()
        return row + 1

    # -- project lifecycle -------------------------------------------------------

    def _new_project_dialog(self, initial: bool = False) -> None:
        dialog = NewProjectDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.result:
            name, style, seed = dialog.result
            self._set_project(build_style(style, name, seed), path=None)
        elif initial and self.project is None:
            self._set_project(build_style("organic_growth", "Untitled Performance", 4207),
                              path=None)

    def _open_dialog(self) -> None:
        path = filedialog.askopenfilename(
            title="Open project", filetypes=[("midi-art projects", "*.json")])
        if path:
            self._open_project(Path(path))

    def _open_project(self, path: Path) -> None:
        try:
            project = Project.load(path)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showerror("Agentic MIDI Artist Studio", f"Could not open project:\n{exc}")
            return
        self._set_project(project, path)

    def _set_project(self, project: Project, path: Path | None) -> None:
        self.project = project
        self.project_path = path
        self.performance = None
        self.seed_var.set(str(project.seed))
        self.profile_var.set(project.export_profile)
        self.scene_index = 0 if project.scenes else None
        self._refresh_timeline()
        self._load_scene_editor()
        self.root.title(f"Agentic MIDI Artist Studio — {project.name}")
        self.status_var.set(f"Loaded {project.name!r} ({len(project.scenes)} scenes).")

    def _save(self) -> None:
        if self.project_path is None:
            self._save_as()
            return
        self._sync_project_settings()
        assert self.project is not None
        self.project.save(self.project_path)
        self.status_var.set(f"Saved {self.project_path}")

    def _save_as(self) -> None:
        if self.project is None:
            return
        path = filedialog.asksaveasfilename(
            title="Save project", defaultextension=".json",
            filetypes=[("midi-art projects", "*.json")],
            initialfile=f"{_slug(self.project.name)}.json")
        if path:
            self.project_path = Path(path)
            self._save()

    def _sync_project_settings(self) -> None:
        if self.project is None:
            return
        seed = _parse_int(self.seed_var.get(), self.project.seed)
        self.project = replace(self.project, seed=seed,
                               export_profile=self.profile_var.get())

    def _reroll_seed(self) -> None:
        self.seed_var.set(str(_random.randint(1, 999_999)))
        self.status_var.set("New seed rolled — preview or export to hear the variation.")

    def _toggle_advanced(self) -> None:
        if self.advanced_var.get():
            self.advanced_frame.grid()
            self.profile_combo.pack(side="right", padx=(6, 0))
        else:
            self.advanced_frame.grid_remove()
            self.profile_combo.pack_forget()

    # -- timeline -----------------------------------------------------------------

    def _refresh_timeline(self) -> None:
        self.timeline.delete(*self.timeline.get_children())
        if self.project is None:
            return
        for index, scene in enumerate(self.project.scenes):
            intent = scene.intent
            self.timeline.insert(
                "", "end", iid=str(index), text=scene.name,
                values=(scene.duration_bars,
                        f"{intent.intensity_start:.2f}→{intent.intensity_end:.2f}",
                        scene.transition_out or ""))
        if self.scene_index is not None and self.project.scenes:
            self.scene_index = min(self.scene_index, len(self.project.scenes) - 1)
            self.timeline.selection_set(str(self.scene_index))

    def _on_scene_selected(self, _event: object) -> None:
        selection = self.timeline.selection()
        if selection:
            self.scene_index = int(selection[0])
            self._load_scene_editor()

    def _selected_scene(self) -> Scene | None:
        if self.project is None or self.scene_index is None:
            return None
        if not 0 <= self.scene_index < len(self.project.scenes):
            return None
        return self.project.scenes[self.scene_index]

    def _replace_scene(self, index: int, scene: Scene | None) -> None:
        """Replace (or delete, when scene is None) the scene at index."""
        assert self.project is not None
        scenes = list(self.project.scenes)
        if scene is None:
            scenes.pop(index)
        else:
            scenes[index] = scene
        self.project = replace(self.project, scenes=tuple(scenes))
        self._refresh_timeline()

    def _add_scene(self) -> None:
        if self.project is None:
            return
        scenes = list(self.project.scenes)
        scenes.append(Scene(
            name=f"Scene {len(scenes) + 1}",
            duration_bars=16,
            intent=SceneIntent(),
            layers=(Layer("voice", LayerRole.MELODY, GeneratorConfig("arpeggio")),),
        ))
        self.project = replace(self.project, scenes=tuple(scenes))
        self.scene_index = len(scenes) - 1
        self._refresh_timeline()
        self._load_scene_editor()

    def _remove_scene(self) -> None:
        scene = self._selected_scene()
        if scene is None or self.project is None:
            return
        if len(self.project.scenes) == 1:
            messagebox.showwarning(
                "Agentic MIDI Artist Studio", "A performance needs at least one scene."
            )
            return
        assert self.scene_index is not None
        self._replace_scene(self.scene_index, None)
        self.scene_index = max(0, self.scene_index - 1)
        self._refresh_timeline()
        self._load_scene_editor()

    def _move_scene(self, direction: int) -> None:
        if self.project is None or self.scene_index is None:
            return
        scenes = list(self.project.scenes)
        target = self.scene_index + direction
        if not 0 <= target < len(scenes):
            return
        scenes[self.scene_index], scenes[target] = scenes[target], scenes[self.scene_index]
        self.project = replace(self.project, scenes=tuple(scenes))
        self.scene_index = target
        self._refresh_timeline()

    # -- scene editor ---------------------------------------------------------------

    def _load_scene_editor(self) -> None:
        scene = self._selected_scene()
        if scene is None:
            return
        intent = scene.intent
        self.scene_name_var.set(scene.name)
        self.scene_bars_var.set(scene.duration_bars)
        self.transition_var.set(scene.transition_out or NO_TRANSITION)
        self.intensity_start_var.set(intent.intensity_start)
        self.intensity_end_var.set(intent.intensity_end)
        self.curve_var.set(intent.intensity_curve.value)
        self.order_var.set(intent.order)
        self.stability_var.set(intent.harmonic_stability)
        self.register_center_var.set(intent.register_center)
        self.register_start_var.set(intent.register_span_start)
        self.register_end_var.set(intent.register_span_end)
        self._refresh_layers(scene)

    def _refresh_layers(self, scene: Scene) -> None:
        self.layer_tree.delete(*self.layer_tree.get_children())
        for index, layer in enumerate(scene.layers):
            self.layer_tree.insert(
                "", "end", iid=str(index), text=layer.name,
                values=(layer.role.value, layer.generator.generator,
                        layer.color_group, f"{layer.gain:.2f}"))

    def _scene_from_editor(self, base: Scene) -> Scene:
        transition = self.transition_var.get()
        return replace(
            base,
            name=self.scene_name_var.get().strip() or base.name,
            duration_bars=max(1, _parse_int(str(self.scene_bars_var.get()), 16)),
            transition_out=None if transition == NO_TRANSITION else transition,
            intent=replace(
                base.intent,
                intensity_start=round(self.intensity_start_var.get(), 3),
                intensity_end=round(self.intensity_end_var.get(), 3),
                intensity_curve=CurveType(self.curve_var.get()),
                order=round(self.order_var.get(), 3),
                harmonic_stability=round(self.stability_var.get(), 3),
                register_center=self.register_center_var.get(),
                register_span_start=self.register_start_var.get(),
                register_span_end=self.register_end_var.get(),
            ),
        )

    def _apply_scene(self) -> None:
        scene = self._selected_scene()
        if scene is None or self.scene_index is None:
            return
        self._replace_scene(self.scene_index, self._scene_from_editor(scene))
        self.status_var.set(f"Applied scene {self.scene_name_var.get()!r}.")

    # -- layers ------------------------------------------------------------------------

    def _selected_layer_index(self) -> int | None:
        selection = self.layer_tree.selection()
        return int(selection[0]) if selection else None

    def _add_layer(self) -> None:
        scene = self._selected_scene()
        if scene is None or self.scene_index is None:
            return
        dialog = LayerDialog(self.root, advanced=self.advanced_var.get())
        self.root.wait_window(dialog)
        if dialog.result:
            layers = (*scene.layers, dialog.result)
            self._replace_scene(self.scene_index, replace(scene, layers=layers))
            self._refresh_layers(self._selected_scene())

    def _edit_layer(self) -> None:
        scene = self._selected_scene()
        layer_index = self._selected_layer_index()
        if scene is None or self.scene_index is None or layer_index is None:
            return
        dialog = LayerDialog(self.root, layer=scene.layers[layer_index],
                             advanced=self.advanced_var.get())
        self.root.wait_window(dialog)
        if dialog.result:
            layers = list(scene.layers)
            layers[layer_index] = dialog.result
            self._replace_scene(self.scene_index, replace(scene, layers=tuple(layers)))
            self._refresh_layers(self._selected_scene())

    def _remove_layer(self) -> None:
        scene = self._selected_scene()
        layer_index = self._selected_layer_index()
        if scene is None or self.scene_index is None or layer_index is None:
            return
        layers = tuple(layer for i, layer in enumerate(scene.layers) if i != layer_index)
        self._replace_scene(self.scene_index, replace(scene, layers=layers))
        self._refresh_layers(self._selected_scene())

    # -- preview & export -----------------------------------------------------------------

    def _preview_full(self) -> None:
        self._run_preview(scene_name=None)

    def _preview_scene(self) -> None:
        scene = self._selected_scene()
        if scene is not None:
            self._apply_scene()
            self._run_preview(scene_name=self.scene_name_var.get().strip() or scene.name)

    def _run_preview(self, scene_name: str | None) -> None:
        if self.project is None:
            return
        self._sync_project_settings()
        project = self.project
        self.status_var.set("Composing preview...")

        def work() -> None:
            try:
                performance = compose(project, scene_name=scene_name)
                report = analyze(performance)
                issues = validate(performance, report)
                data = build_preview(performance, max_notes=6000)
            except Exception as exc:  # pragma: no cover - UI error path
                message = str(exc)
                self.root.after(0, lambda: self._preview_failed(message))
                return
            self.root.after(0, lambda: self._preview_done(performance, data, report, issues))

        threading.Thread(target=work, daemon=True).start()

    def _preview_failed(self, message: str) -> None:
        self.status_var.set("Preview failed.")
        messagebox.showerror("Agentic MIDI Artist Studio", message)

    def _preview_done(self, performance, data: PreviewData, report, issues) -> None:
        self.performance = performance
        self._draw_preview(data)
        text = report.format_text()
        if issues:
            text += "\n\n" + "\n".join(str(issue) for issue in issues)
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", text)
        self.report_text.configure(state="disabled")
        self.status_var.set(
            f"Previewed {data.total_notes:,} notes across {len(data.scenes)} scene(s).")

    def _draw_preview(self, data: PreviewData) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 400)
        height = max(canvas.winfo_height(), 300)
        roll_height = int(height * 0.68)
        strip_height = int(height * 0.13)
        beats = max(data.duration_beats, 1e-9)
        pitch_span = 108 - 21

        def x(beat: float) -> float:
            return (beat / beats) * width

        def y(pitch: int) -> float:
            return roll_height * (1.0 - (pitch - 21) / pitch_span)

        for pitch in range(24, 108, 12):
            canvas.create_line(0, y(pitch), width, y(pitch), fill=GRID)
        note_height = max(2, roll_height // pitch_span)
        for note in data.notes:
            color = CHANNEL_COLORS[note.channel % len(CHANNEL_COLORS)]
            canvas.create_rectangle(
                x(note.start), y(note.pitch) - note_height / 2,
                max(x(note.end), x(note.start) + 1), y(note.pitch) + note_height / 2,
                fill=color, width=0)
        for scene in data.scenes:
            left = x(scene.start_beat)
            canvas.create_line(left, 0, left, roll_height, fill=MUTED, dash=(3, 4))
            canvas.create_text(left + 5, 10, text=scene.name, fill=MUTED,
                               anchor="w", font=("Segoe UI", 9))

        # Density strip with intensity curve.
        density_top = roll_height + 8
        peak = max(data.density_per_bar) if data.density_per_bar else 1
        for bar, count in enumerate(data.density_per_bar):
            if not count:
                continue
            left = x(bar * data.beats_per_bar)
            right = max(x((bar + 1) * data.beats_per_bar) - 1, left + 1)
            h = (count / peak) * strip_height
            fill = ACCENT if bar == data.peak_density_bar else "#55606e"
            canvas.create_rectangle(left, density_top + strip_height - h, right,
                                    density_top + strip_height, fill=fill, width=0)
        curve_points = []
        for scene in data.scenes:
            for beat, intensity in scene.intensity_points:
                curve_points += [x(beat), density_top + strip_height * (1 - intensity)]
        if len(curve_points) >= 4:
            canvas.create_line(*curve_points, fill=ACCENT, width=2)

        # Polyphony graph.
        poly_top = density_top + strip_height + 8
        poly_height = height - poly_top - 2
        poly_peak = max(data.peak_polyphony, 1)
        points = [0, poly_top + poly_height]
        for beat, active in data.polyphony:
            points += [x(beat), poly_top + poly_height * (1 - active / poly_peak)]
        points += [width, poly_top + poly_height]
        canvas.create_polygon(*points, fill="#2c4f7c", outline="#3d6fae")
        canvas.create_text(4, poly_top + 2, anchor="nw", fill=MUTED,
                           text=f"polyphony (peak {data.peak_polyphony})",
                           font=("Segoe UI", 8))

    def _export_midi(self) -> None:
        if self.project is None:
            return
        self._sync_project_settings()
        project = self.project
        self.status_var.set("Composing performance...")

        def work() -> None:
            try:
                performance = compose(project)
                report = analyze(performance)
                issues = validate(performance, report)
                errors = [issue for issue in issues if issue.level is IssueLevel.ERROR]
                if errors:
                    raise RuntimeError("\n".join(str(issue) for issue in errors))
                midi_path = Path("output") / f"{_slug(project.name)}.mid"
                write_midi(performance.notes, midi_path, performance.settings,
                           tempo_events=performance.tempo_events)
                manifest_path = midi_path.with_suffix(".manifest.json")
                manifest_path.write_text(json.dumps({
                    "project": project.name,
                    "midi_file": str(midi_path),
                    "seed": project.seed,
                    "export_profile": performance.settings.name,
                    "report": report.to_dict(),
                }, indent=2), encoding="utf-8")
            except Exception as exc:  # pragma: no cover - UI error path
                error_message = str(exc)
                self.root.after(0, lambda: self._preview_failed(error_message))
                return
            message = f"Exported {report.total_notes:,} notes to {midi_path}"
            self.root.after(0, lambda: self.status_var.set(message))

        threading.Thread(target=work, daemon=True).start()

    def run(self) -> None:
        self.root.mainloop()


class NewProjectDialog(tk.Toplevel):
    """Project wizard: name, style browser with descriptions, seed."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title("New performance")
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.result: tuple[str, str, int] | None = None
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, style="Panel.TFrame", padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Name", style="App.TLabel").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value="Untitled Performance")
        ttk.Entry(frame, textvariable=self.name_var, width=36, style="App.TEntry").grid(
            row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Label(frame, text="Style", style="App.TLabel").grid(row=1, column=0, sticky="w")
        self.style_var = tk.StringVar(value=sorted(STYLES)[0])
        combo = ttk.Combobox(frame, textvariable=self.style_var, values=sorted(STYLES),
                             state="readonly")
        combo.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)
        combo.bind("<<ComboboxSelected>>", self._refresh_description)

        self.description_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.description_var, style="Muted.TLabel",
                  wraplength=300, justify="left").grid(row=2, column=1, sticky="w",
                                                       padx=(10, 0))
        self._refresh_description()

        ttk.Label(frame, text="Seed", style="App.TLabel").grid(row=3, column=0, sticky="w")
        self.seed_var = tk.StringVar(value=str(_random.randint(1, 999_999)))
        ttk.Entry(frame, textvariable=self.seed_var, width=12, style="App.TEntry").grid(
            row=3, column=1, sticky="w", padx=(10, 0), pady=4)

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="Create", style="Accent.TButton",
                   command=self._create).pack(side="right")

    def _refresh_description(self, *_: object) -> None:
        definition = STYLES.get(self.style_var.get())
        self.description_var.set(definition.description if definition else "")

    def _create(self) -> None:
        seed = _parse_int(self.seed_var.get(), 4207)
        self.result = (self.name_var.get().strip() or "Untitled Performance",
                       self.style_var.get(), seed)
        self.destroy()


class LayerDialog(tk.Toplevel):
    """Layer inspector: role, generator (with description), color group, gain."""

    def __init__(self, parent: tk.Misc, layer: Layer | None = None,
                 advanced: bool = False) -> None:
        super().__init__(parent)
        self.title("Layer" if layer else "New layer")
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.result: Layer | None = None
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, style="Panel.TFrame", padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        self.name_var = tk.StringVar(value=layer.name if layer else "layer")
        self.role_var = tk.StringVar(value=layer.role.value if layer else "melody")
        self.generator_var = tk.StringVar(
            value=layer.generator.generator if layer else "arpeggio")
        self.color_var = tk.StringVar(value=layer.color_group if layer else "default")
        self.gain_var = tk.DoubleVar(value=layer.gain if layer else 1.0)
        params = dict(layer.generator.params) if layer else {}
        self.params_var = tk.StringVar(value=json.dumps(params) if params else "{}")

        row = 0
        ttk.Label(frame, text="Name", style="App.TLabel").grid(row=row, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.name_var, style="App.TEntry").grid(
            row=row, column=1, sticky="ew", padx=(10, 0), pady=3)
        row += 1

        ttk.Label(frame, text="Role", style="App.TLabel").grid(row=row, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=self.role_var,
                     values=[role.value for role in LayerRole],
                     state="readonly").grid(row=row, column=1, sticky="ew",
                                            padx=(10, 0), pady=3)
        row += 1

        ttk.Label(frame, text="Generator", style="App.TLabel").grid(
            row=row, column=0, sticky="w")
        combo = ttk.Combobox(frame, textvariable=self.generator_var,
                             values=sorted(GENERATORS), state="readonly")
        combo.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=3)
        combo.bind("<<ComboboxSelected>>", self._refresh_description)
        row += 1

        self.description_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.description_var, style="Muted.TLabel",
                  wraplength=320, justify="left").grid(row=row, column=1, sticky="w",
                                                       padx=(10, 0))
        self._refresh_description()
        row += 1

        ttk.Label(frame, text="Color group", style="App.TLabel").grid(
            row=row, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.color_var, style="App.TEntry").grid(
            row=row, column=1, sticky="ew", padx=(10, 0), pady=3)
        row += 1

        ttk.Label(frame, text="Gain", style="App.TLabel").grid(row=row, column=0, sticky="w")
        ttk.Scale(frame, from_=0.1, to=1.5, variable=self.gain_var).grid(
            row=row, column=1, sticky="ew", padx=(10, 0), pady=3)
        row += 1

        if advanced:
            ttk.Label(frame, text="Params (JSON)", style="App.TLabel").grid(
                row=row, column=0, sticky="w")
            ttk.Entry(frame, textvariable=self.params_var, style="App.TEntry").grid(
                row=row, column=1, sticky="ew", padx=(10, 0), pady=3)
            row += 1

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="OK", style="Accent.TButton",
                   command=self._accept).pack(side="right")

    def _refresh_description(self, *_: object) -> None:
        generator = GENERATORS.get(self.generator_var.get())
        if generator:
            d = generator.definition
            visuals = ", ".join(d.visual_characteristics)
            self.description_var.set(f"{d.description}\nvisuals: {visuals}")

    def _accept(self) -> None:
        try:
            params = json.loads(self.params_var.get() or "{}")
            if not isinstance(params, dict):
                raise ValueError("Params must be a JSON object.")
        except (json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror(
                "Agentic MIDI Artist Studio", f"Invalid params: {exc}", parent=self
            )
            return
        self.result = Layer(
            name=self.name_var.get().strip() or "layer",
            role=LayerRole(self.role_var.get()),
            generator=GeneratorConfig(self.generator_var.get(), params),
            color_group=self.color_var.get().strip() or "default",
            gain=round(self.gain_var.get(), 2),
        )
        self.destroy()


def _parse_int(text: str, default: int) -> int:
    try:
        return int(text.strip())
    except (ValueError, AttributeError):
        return default


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-") or "performance"


def run_studio(project_path: str | None = None) -> None:
    StudioApp(project_path).run()


def main() -> None:
    import sys

    run_studio(sys.argv[1] if len(sys.argv) > 1 else None)


if __name__ == "__main__":
    main()
