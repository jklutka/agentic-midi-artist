"""Minimal Tkinter UI for dense MIDI generation."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .dense_song import (
    DenseSongSegment,
    create_segmented_dense_song,
    dense_song_preset_options,
)


class DenseSongApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Dense MIDI Generator")
        self.root.geometry("1080x720")
        self.root.minsize(920, 640)
        self.root.configure(bg="#111317")
        self._suspend_preset_defaults = False

        self._build_styles()
        self._build_layout()

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background="#111317")
        style.configure("Panel.TFrame", background="#171b21")
        style.configure(
            "App.TLabel",
            background="#111317",
            foreground="#e5e7eb",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Title.TLabel",
            background="#111317",
            foreground="#f9fafb",
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#111317",
            foreground="#9ca3af",
            font=("Segoe UI", 10),
        )
        style.configure(
            "PanelTitle.TLabel",
            background="#171b21",
            foreground="#f3f4f6",
            font=("Segoe UI", 11, "bold"),
        )
        style.configure("App.TEntry", fieldbackground="#0f1318", foreground="#f3f4f6")
        style.configure("App.TCombobox", fieldbackground="#0f1318", foreground="#f3f4f6")
        style.configure("App.TSpinbox", fieldbackground="#0f1318", foreground="#f3f4f6")
        style.configure(
            "Accent.TButton",
            background="#7c9bff",
            foreground="#0b1020",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 8),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#93adff"), ("pressed", "#6784ef")],
        )

    def _build_layout(self) -> None:
        root = ttk.Frame(self.root, style="App.TFrame", padding=20)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="App.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Dense MIDI Generator", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text=(
                "Create a structured, high-density MIDI file with a bass anchor, "
                "repeating motif, and arpeggiated fill."
            ),
            style="Subtitle.TLabel",
            wraplength=640,
        ).pack(anchor="w", pady=(6, 0))

        body = ttk.Frame(root, style="App.TFrame")
        body.pack(fill="both", expand=True, pady=(18, 0))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)

        controls = ttk.Frame(body, style="Panel.TFrame", padding=16)
        controls.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Song Settings", style="PanelTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        self.output_var = tk.StringVar(value=str(Path("output") / "dense_song.mid"))
        self.preset_var = tk.StringVar()
        self.bars_var = tk.IntVar(value=16)
        self.tempo_var = tk.IntVar(value=132)
        self.root_var = tk.IntVar(value=60)
        self.mode_var = tk.StringVar(value="minor")
        self.density_var = tk.StringVar(value="0.78")
        self.seed_var = tk.StringVar(value="")
        self.preset_options = dense_song_preset_options()
        self.preset_by_label = {preset.label: preset for preset in self.preset_options}
        self.preset_var.set(self.preset_options[0].label)

        row = 1
        row = self._add_entry(controls, row, "Output", self.output_var, browse=True)
        row = self._add_combobox(controls, row, "Preset", self.preset_var, self._preset_labels())
        row = self._add_spinbox(controls, row, "Bars", self.bars_var, 4, 128, 4)
        row = self._add_spinbox(controls, row, "Tempo", self.tempo_var, 60, 220, 1)
        row = self._add_spinbox(controls, row, "Root MIDI", self.root_var, 24, 84, 1)
        row = self._add_combobox(controls, row, "Mode", self.mode_var, ("minor", "major"))
        row = self._add_density_input(controls, row)
        row = self._add_entry(controls, row, "Seed", self.seed_var)
        row = self._add_segment_editor(controls, row)

        action_row = ttk.Frame(controls, style="Panel.TFrame")
        action_row.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        action_row.columnconfigure(0, weight=1)
        self.generate_button = ttk.Button(
            action_row,
            text="Generate MIDI",
            style="Accent.TButton",
            command=self._generate_async,
        )
        self.generate_button.grid(row=0, column=0, sticky="ew")

        info = ttk.Frame(body, style="Panel.TFrame", padding=16)
        info.grid(row=0, column=1, sticky="nsew")
        info.columnconfigure(0, weight=1)

        ttk.Label(info, text="Preset", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.preset_description_var = tk.StringVar()
        self.zenith_tip_var = tk.StringVar()
        self.control_tip_var = tk.StringVar()
        ttk.Label(
            info,
            textvariable=self.preset_description_var,
            style="App.TLabel",
            wraplength=220,
            justify="left",
        ).grid(row=1, column=0, sticky="nw", pady=(10, 0))

        ttk.Label(info, text="Zenith use", style="PanelTitle.TLabel").grid(
            row=2, column=0, sticky="w", pady=(24, 0)
        )
        ttk.Label(
            info,
            textvariable=self.zenith_tip_var,
            style="App.TLabel",
            wraplength=220,
            justify="left",
        ).grid(row=3, column=0, sticky="nw", pady=(10, 0))

        ttk.Label(info, text="Control", style="PanelTitle.TLabel").grid(
            row=4, column=0, sticky="w", pady=(24, 0)
        )
        ttk.Label(
            info,
            textvariable=self.control_tip_var,
            style="App.TLabel",
            wraplength=220,
            justify="left",
        ).grid(row=5, column=0, sticky="nw", pady=(10, 0))

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(info, text="Status", style="PanelTitle.TLabel").grid(
            row=6, column=0, sticky="w", pady=(24, 0)
        )
        ttk.Label(
            info,
            textvariable=self.status_var,
            style="App.TLabel",
            wraplength=220,
            justify="left",
        ).grid(row=7, column=0, sticky="nw", pady=(10, 0))

        self.preset_var.trace_add("write", self._apply_selected_preset)
        self._apply_selected_preset()
        self._add_segment()

    def _add_entry(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.Variable,
        browse: bool = False,
    ) -> int:
        ttk.Label(
            parent,
            text=label,
            style="App.TLabel",
        ).grid(row=row, column=0, sticky="w", pady=6)
        entry = ttk.Entry(parent, textvariable=variable, style="App.TEntry")
        entry.grid(row=row, column=1, sticky="ew", padx=(12, 12), pady=6)
        if browse:
            ttk.Button(
                parent,
                text="Browse",
                command=self._browse_output,
            ).grid(row=row, column=2, sticky="e", pady=6)
        else:
            ttk.Label(
                parent,
                text="",
                style="App.TLabel",
            ).grid(row=row, column=2, sticky="e", pady=6)
        return row + 1

    def _add_spinbox(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.IntVar,
        minimum: int,
        maximum: int,
        increment: int,
    ) -> int:
        ttk.Label(
            parent,
            text=label,
            style="App.TLabel",
        ).grid(row=row, column=0, sticky="w", pady=6)
        spin = ttk.Spinbox(
            parent,
            from_=minimum,
            to=maximum,
            increment=increment,
            textvariable=variable,
            width=12,
            style="App.TSpinbox",
        )
        spin.grid(row=row, column=1, sticky="w", padx=(12, 12), pady=6)
        ttk.Label(parent, text="", style="App.TLabel").grid(row=row, column=2, sticky="e", pady=6)
        return row + 1

    def _add_combobox(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
    ) -> int:
        ttk.Label(
            parent,
            text=label,
            style="App.TLabel",
        ).grid(row=row, column=0, sticky="w", pady=6)
        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            values=values,
            state="readonly",
            width=14,
        )
        combo.grid(row=row, column=1, sticky="w", padx=(12, 12), pady=6)
        if label == "Preset":
            combo.bind("<<ComboboxSelected>>", lambda _event: self._apply_selected_preset())
        ttk.Label(parent, text="", style="App.TLabel").grid(row=row, column=2, sticky="e", pady=6)
        return row + 1

    def _add_density_input(self, parent: ttk.Frame, row: int) -> int:
        ttk.Label(
            parent,
            text="Density",
            style="App.TLabel",
        ).grid(row=row, column=0, sticky="w", pady=6)
        entry = ttk.Entry(parent, textvariable=self.density_var, style="App.TEntry")
        entry.grid(row=row, column=1, sticky="ew", padx=(12, 12), pady=6)
        ttk.Label(
            parent,
            text="Any non-negative number",
            style="App.TLabel",
        ).grid(row=row, column=2, sticky="e", pady=6)
        return row + 1

    def _preset_labels(self) -> tuple[str, ...]:
        return tuple(preset.label for preset in self.preset_options)

    def _apply_selected_preset(self, *_: object) -> None:
        preset = self.preset_by_label.get(self.preset_var.get(), self.preset_options[0])

        self.preset_description_var.set(preset.description)
        self.zenith_tip_var.set(preset.zenith_tip)
        self.control_tip_var.set(
            f"This preset spreads notes across {preset.channel_count} channels. "
            "Values above 1.00 push into extreme overlap, and values above 3.00 can get wild."
        )
        if self._suspend_preset_defaults:
            return

        if preset.key == "dense_but_musical":
            values = {"bars": 16, "tempo": 132, "root": 60, "mode": "minor", "density": 0.85}
        elif preset.key == "black_midi_wall":
            values = {"bars": 24, "tempo": 160, "root": 60, "mode": "minor", "density": 2.4}
        elif preset.key == "channel_color_storm":
            values = {"bars": 20, "tempo": 150, "root": 60, "mode": "major", "density": 3.2}
        elif preset.key == "hypnotic_wave":
            values = {"bars": 32, "tempo": 144, "root": 60, "mode": "minor", "density": 8.0}
        else:
            values = {"bars": 20, "tempo": 176, "root": 60, "mode": "minor", "density": 6.0}

        self.bars_var.set(values["bars"])
        self.tempo_var.set(values["tempo"])
        self.root_var.set(values["root"])
        self.mode_var.set(values["mode"])
        self.density_var.set(values["density"])

    def _add_segment_editor(self, parent: ttk.Frame, row: int) -> int:
        ttk.Label(parent, text="Segments", style="PanelTitle.TLabel").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(16, 8)
        )

        columns = ("bars", "preset", "density", "tempo", "mode", "root")
        self.segment_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=7,
            selectmode="browse",
        )
        headings = {
            "bars": "Bars",
            "preset": "Preset",
            "density": "Density",
            "tempo": "Tempo",
            "mode": "Mode",
            "root": "Root",
        }
        widths = {"bars": 56, "preset": 150, "density": 84, "tempo": 70, "mode": 70, "root": 56}
        for column in columns:
            self.segment_tree.heading(column, text=headings[column])
            self.segment_tree.column(column, width=widths[column], stretch=column == "preset")
        self.segment_tree.grid(row=row + 1, column=0, columnspan=3, sticky="nsew", pady=(0, 8))
        self.segment_tree.bind("<<TreeviewSelect>>", self._on_segment_selected)

        buttons = ttk.Frame(parent, style="Panel.TFrame")
        buttons.grid(row=row + 2, column=0, columnspan=3, sticky="ew")
        for index in range(6):
            buttons.columnconfigure(index, weight=1)
        ttk.Button(buttons, text="Add", command=self._add_segment).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ttk.Button(buttons, text="Update", command=self._update_segment).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ttk.Button(buttons, text="Remove", command=self._remove_segment).grid(
            row=0, column=2, sticky="ew", padx=4
        )
        ttk.Button(buttons, text="Up", command=lambda: self._move_segment(-1)).grid(
            row=0, column=3, sticky="ew", padx=4
        )
        ttk.Button(buttons, text="Down", command=lambda: self._move_segment(1)).grid(
            row=0, column=4, sticky="ew", padx=4
        )
        ttk.Button(buttons, text="Wave Arc", command=self._load_wave_arc).grid(
            row=0, column=5, sticky="ew", padx=(4, 0)
        )
        return row + 3

    def _current_segment_values(self) -> tuple[str, str, str, str, str, str]:
        return (
            str(int(self.bars_var.get())),
            self.preset_var.get(),
            str(float(self.density_var.get().strip() or "0")),
            str(int(self.tempo_var.get())),
            self.mode_var.get(),
            str(int(self.root_var.get())),
        )

    def _add_segment(self) -> None:
        self.segment_tree.insert("", "end", values=self._current_segment_values())

    def _update_segment(self) -> None:
        selected = self.segment_tree.selection()
        if not selected:
            self._add_segment()
            return
        self.segment_tree.item(selected[0], values=self._current_segment_values())

    def _remove_segment(self) -> None:
        for item in self.segment_tree.selection():
            self.segment_tree.delete(item)

    def _move_segment(self, direction: int) -> None:
        selected = self.segment_tree.selection()
        if not selected:
            return
        item = selected[0]
        index = self.segment_tree.index(item)
        new_index = max(0, min(len(self.segment_tree.get_children()) - 1, index + direction))
        self.segment_tree.move(item, "", new_index)
        self.segment_tree.selection_set(item)

    def _load_wave_arc(self) -> None:
        for item in self.segment_tree.get_children():
            self.segment_tree.delete(item)
        rows = [
            (8, "Dense but musical", 0.9, 128, "minor", 60),
            (12, "Hypnotic wave", 4.0, 138, "minor", 60),
            (16, "Hypnotic wave", 12.0, 148, "minor", 60),
            (8, "Ultra dense", 18.0, 168, "minor", 60),
            (8, "Hypnotic wave", 5.0, 132, "minor", 57),
        ]
        for row in rows:
            self.segment_tree.insert("", "end", values=tuple(str(value) for value in row))

    def _on_segment_selected(self, _event: tk.Event) -> None:
        selected = self.segment_tree.selection()
        if not selected:
            return
        bars, preset, density, tempo, mode, root = self.segment_tree.item(selected[0], "values")
        self._suspend_preset_defaults = True
        try:
            self.preset_var.set(preset)
            self._apply_selected_preset()
            self.bars_var.set(int(bars))
            self.density_var.set(density)
            self.tempo_var.set(int(tempo))
            self.mode_var.set(mode)
            self.root_var.set(int(root))
        finally:
            self._suspend_preset_defaults = False

    def _segments_from_table(self) -> list[DenseSongSegment]:
        segments: list[DenseSongSegment] = []
        for item in self.segment_tree.get_children():
            bars, preset_label, density, tempo, mode, root = self.segment_tree.item(item, "values")
            preset = self.preset_by_label[preset_label]
            segments.append(
                DenseSongSegment(
                    bars=int(bars),
                    preset=preset.key,
                    density=float(density),
                    tempo_bpm=int(tempo),
                    root=int(root),
                    scale_type=mode,
                )
            )
        if not segments:
            preset = self.preset_by_label[self.preset_var.get()]
            segments.append(
                DenseSongSegment(
                    bars=int(self.bars_var.get()),
                    preset=preset.key,
                    density=float(self.density_var.get().strip() or "0"),
                    tempo_bpm=int(self.tempo_var.get()),
                    root=int(self.root_var.get()),
                    scale_type=self.mode_var.get(),
                )
            )
        return segments

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save MIDI file",
            defaultextension=".mid",
            filetypes=[("MIDI files", "*.mid"), ("All files", "*.*")],
            initialfile=Path(self.output_var.get()).name,
        )
        if path:
            self.output_var.set(path)

    def _generate_async(self) -> None:
        self.generate_button.configure(state="disabled")
        self.status_var.set("Generating...")
        threading.Thread(target=self._generate, daemon=True).start()

    def _generate(self) -> None:
        try:
            seed_text = self.seed_var.get().strip()
            seed = int(seed_text) if seed_text else None
            output = create_segmented_dense_song(
                self.output_var.get(),
                self._segments_from_table(),
                seed=seed,
            )
        except Exception as exc:  # pragma: no cover - UI error path
            error_message = str(exc)

            def report_error() -> None:
                self.status_var.set("Generation failed.")
                self.generate_button.configure(state="normal")
                messagebox.showerror("Dense MIDI Generator", error_message)

            self.root.after(0, report_error)
            return

        def finish() -> None:
            self.status_var.set(f"Created {output}")
            self.generate_button.configure(state="normal")

        self.root.after(0, finish)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    DenseSongApp().run()


if __name__ == "__main__":
    main()
