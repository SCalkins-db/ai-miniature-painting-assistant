"""GUI v2 for the AI Miniature Painting Assistant."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from src.database.workflow_repository import WorkflowRepository
from src.gui.workflow_widgets import BreadcrumbBar, PaintPopup, WorkflowView


class PaintingAssistantApp(tk.Tk):
    """Desktop interface for browsing curated painting workflows."""

    WINDOW_TITLE = "AI Miniature Painting Assistant"
    WINDOW_GEOMETRY = "1180x800"
    WINDOW_MIN_WIDTH = 980
    WINDOW_MIN_HEIGHT = 650
    NO_SUBFACTION = "No Subfaction"

    PALETTE = {
        "background": "#17191D",
        "panel": "#22252A",
        "card": "#292D33",
        "field": "#2D3137",
        "text": "#F1F1F1",
        "muted": "#B8BDC5",
        "border": "#41464F",
        "accent": "#8CA6C0",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title(self.WINDOW_TITLE)
        self.geometry(self.WINDOW_GEOMETRY)
        self.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)
        self.configure(background=self.PALETTE["background"])

        self.repository = WorkflowRepository()
        self.superfaction_var = tk.StringVar()
        self.faction_var = tk.StringVar()
        self.subfaction_var = tk.StringVar()
        self.unit_var = tk.StringVar()
        self.workflow_var = tk.StringVar()
        self.workflow_title_var = tk.StringVar(value="Select a workflow to begin.")

        self.workflow_display_to_id: dict[str, str] = {}
        self.workflow_id_to_record: dict[str, dict[str, Any]] = {}

        self._configure_styles()
        self._build_layout()
        self._bind_events()
        self._load_superfactions()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        p = self.PALETTE
        style.configure("App.TFrame", background=p["background"])
        style.configure("Panel.TFrame", background=p["panel"])
        style.configure("Area.TFrame", background=p["panel"], relief="solid", borderwidth=1)
        style.configure("Card.TFrame", background=p["card"])
        style.configure("Header.TLabel", background=p["background"], foreground=p["text"], font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background=p["background"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("Breadcrumb.TLabel", background=p["background"], foreground=p["accent"], font=("Segoe UI", 11, "bold"))
        style.configure("FieldLabel.TLabel", background=p["panel"], foreground=p["muted"], font=("Segoe UI", 10, "bold"))
        style.configure("WorkflowTitle.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 15, "bold"))
        style.configure("AreaTitle.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 12, "bold"))
        style.configure("PaintName.TLabel", background=p["card"], foreground=p["text"], font=("Segoe UI", 11, "bold"))
        style.configure("Technique.TLabel", background=p["card"], foreground=p["accent"], font=("Segoe UI", 9, "bold"))
        style.configure("Purpose.TLabel", background=p["card"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("Placeholder.TLabel", background=p["panel"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("PopupTitle.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 16, "bold"))
        style.configure("PopupSubtle.TLabel", background=p["panel"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("PopupKey.TLabel", background=p["panel"], foreground=p["muted"], font=("Segoe UI", 10, "bold"))
        style.configure("PopupValue.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("AreaHeader.TButton", background=p["panel"], foreground=p["text"], font=("Segoe UI", 12, "bold"), anchor="w", padding=(12, 10), borderwidth=0)
        style.map("AreaHeader.TButton", background=[("active", p["field"])], foreground=[("active", p["text"])])
        style.configure("Dark.TCombobox", fieldbackground=p["field"], background=p["field"], foreground=p["text"], arrowcolor=p["text"], bordercolor=p["border"], padding=7)
        style.map("Dark.TCombobox", fieldbackground=[("readonly", p["field"]), ("disabled", p["panel"])], foreground=[("readonly", p["text"]), ("disabled", "#6F747C")])
        self.option_add("*TCombobox*Listbox.background", p["field"])
        self.option_add("*TCombobox*Listbox.foreground", p["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", "#101216")

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=24, style="App.TFrame")
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        ttk.Label(header, text="AI Miniature Painting Assistant", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header, text="Select an army, unit, and workflow to view the recommended painting process.", style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))
        self.breadcrumb = BreadcrumbBar(header, self.PALETTE)
        self.breadcrumb.pack(fill="x", pady=(8, 0))

        self._build_selector_panel(root)

        workflow_panel = ttk.Frame(root, padding=20, style="Panel.TFrame")
        workflow_panel.grid(row=2, column=0, sticky="nsew")
        workflow_panel.columnconfigure(0, weight=1)
        workflow_panel.rowconfigure(1, weight=1)
        ttk.Label(workflow_panel, textvariable=self.workflow_title_var, style="WorkflowTitle.TLabel").grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.workflow_view = WorkflowView(
            workflow_panel,
            palette=self.PALETTE,
            popup_callback=self._open_paint_popup,
        )
        self.workflow_view.grid(row=1, column=0, sticky="nsew")

    def _build_selector_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, padding=18, style="Panel.TFrame")
        panel.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        for column in range(5):
            panel.columnconfigure(column, weight=1)
        self.superfaction_combo = self._create_selector(panel, 0, "Superfaction", self.superfaction_var, True)
        self.faction_combo = self._create_selector(panel, 1, "Faction", self.faction_var, False)
        self.subfaction_combo = self._create_selector(panel, 2, "Subfaction", self.subfaction_var, False)
        self.unit_combo = self._create_selector(panel, 3, "Unit", self.unit_var, False)
        self.workflow_combo = self._create_selector(panel, 4, "Workflow", self.workflow_var, False)

    def _create_selector(self, parent: ttk.Frame, column: int, label: str, variable: tk.StringVar, enabled: bool) -> ttk.Combobox:
        container = ttk.Frame(parent, style="Panel.TFrame")
        container.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 7, 0 if column == 4 else 7))
        ttk.Label(container, text=label, style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 6))
        combo = ttk.Combobox(container, textvariable=variable, state="readonly" if enabled else "disabled", style="Dark.TCombobox")
        combo.pack(fill="x")
        return combo

    def _bind_events(self) -> None:
        self.superfaction_combo.bind("<<ComboboxSelected>>", self._on_superfaction_selected)
        self.faction_combo.bind("<<ComboboxSelected>>", self._on_faction_selected)
        self.subfaction_combo.bind("<<ComboboxSelected>>", self._on_subfaction_selected)
        self.unit_combo.bind("<<ComboboxSelected>>", self._on_unit_selected)
        self.workflow_combo.bind("<<ComboboxSelected>>", self._on_workflow_selected)

    def _load_superfactions(self) -> None:
        try:
            self._set_combo(self.superfaction_combo, self.repository.get_superfactions())
        except Exception as error:
            self._show_error("Unable to load superfactions.", error)

    def _on_superfaction_selected(self, _event: tk.Event) -> None:
        self._reset_after("superfaction")
        value = self.superfaction_var.get().strip()
        self._update_breadcrumb()
        if not value:
            return
        try:
            self._set_combo(self.faction_combo, self.repository.get_factions(value))
        except Exception as error:
            self._show_error(f"Unable to load factions for {value}.", error)

    def _on_faction_selected(self, _event: tk.Event) -> None:
        self._reset_after("faction")
        superfaction = self.superfaction_var.get().strip()
        faction = self.faction_var.get().strip()
        self._update_breadcrumb()
        if not superfaction or not faction:
            return
        try:
            values = self.repository.get_subfactions(superfaction, faction) or [self.NO_SUBFACTION]
            self._set_combo(self.subfaction_combo, values)
            if len(values) == 1:
                self.subfaction_var.set(values[0])
                self._load_units()
        except Exception as error:
            self._show_error(f"Unable to load subfactions for {faction}.", error)

    def _on_subfaction_selected(self, _event: tk.Event) -> None:
        self._reset_after("subfaction")
        self._update_breadcrumb()
        self._load_units()

    def _load_units(self) -> None:
        superfaction = self.superfaction_var.get().strip()
        faction = self.faction_var.get().strip()
        selected_subfaction = self.subfaction_var.get().strip()
        if not all((superfaction, faction, selected_subfaction)):
            return
        database_subfaction = "" if selected_subfaction == self.NO_SUBFACTION else selected_subfaction
        try:
            self._set_combo(self.unit_combo, self.repository.get_units(superfaction, faction, database_subfaction))
        except Exception as error:
            self._show_error(f"Unable to load units for {faction}.", error)

    def _on_unit_selected(self, _event: tk.Event) -> None:
        self._reset_after("unit")
        superfaction = self.superfaction_var.get().strip()
        faction = self.faction_var.get().strip()
        selected_subfaction = self.subfaction_var.get().strip()
        unit = self.unit_var.get().strip()
        self._update_breadcrumb()
        if not all((superfaction, faction, selected_subfaction, unit)):
            return
        database_subfaction = "" if selected_subfaction == self.NO_SUBFACTION else selected_subfaction
        try:
            workflows = self.repository.get_workflows(superfaction, faction, database_subfaction, unit)
            self.workflow_display_to_id.clear()
            self.workflow_id_to_record.clear()
            display_names: list[str] = []
            for index, workflow in enumerate(workflows, start=1):
                workflow_id = str(workflow.get("workflow_id") or "").strip()
                if not workflow_id:
                    continue
                display = self._friendly_workflow_name(workflow, index)
                base = display
                suffix = 2
                while display in self.workflow_display_to_id:
                    display = f"{base} {suffix}"
                    suffix += 1
                self.workflow_display_to_id[display] = workflow_id
                self.workflow_id_to_record[workflow_id] = workflow
                display_names.append(display)
            self._set_combo(self.workflow_combo, display_names, sort=False)
        except Exception as error:
            self._show_error(f"Unable to load workflows for {unit}.", error)

    def _on_workflow_selected(self, _event: tk.Event) -> None:
        display_name = self.workflow_var.get().strip()
        workflow_id = self.workflow_display_to_id.get(display_name)
        unit = self.unit_var.get().strip()
        self._update_breadcrumb()
        if not workflow_id:
            self.workflow_title_var.set("Select a workflow to begin.")
            self.workflow_view.show_placeholder()
            return
        self.workflow_title_var.set(unit)
        try:
            self.workflow_view.display_steps(self.repository.get_workflow_steps(workflow_id))
        except Exception as error:
            self._show_error(f"Unable to load workflow steps for {display_name}.", error)

    def _open_paint_popup(self, step: dict[str, Any]) -> None:
        paint_name = str(step.get("paint_name") or "Unknown paint").strip()
        paint_id = step.get("paint_id")
        try:
            paint = self.repository.get_paint_details(paint_id=paint_id, paint_name=paint_name) or {}
            equivalents = self.repository.get_paint_equivalents(paint_id=paint_id or paint.get("paint_id"), paint_name=paint_name)
        except Exception as error:
            self._show_error("Paint details could not be loaded.", error)
            return
        paint.setdefault("paint_name", paint_name)
        paint.setdefault("paint_hex", step.get("paint_hex"))
        PaintPopup(self, paint=paint, equivalents=equivalents, palette=self.PALETTE)

    def _update_breadcrumb(self) -> None:
        parts = [self.superfaction_var.get(), self.faction_var.get()]
        subfaction = self.subfaction_var.get().strip()
        if subfaction and subfaction != self.NO_SUBFACTION:
            parts.append(subfaction)
        parts.extend([self.unit_var.get(), self.workflow_var.get()])
        self.breadcrumb.set_parts(parts)

    def _reset_after(self, level: str) -> None:
        levels = ["superfaction", "faction", "subfaction", "unit", "workflow"]
        controls = {
            "faction": (self.faction_combo, self.faction_var),
            "subfaction": (self.subfaction_combo, self.subfaction_var),
            "unit": (self.unit_combo, self.unit_var),
            "workflow": (self.workflow_combo, self.workflow_var),
        }
        current_index = levels.index(level)
        for lower_level in levels[current_index + 1 :]:
            if lower_level in controls:
                self._reset_combo(*controls[lower_level])
        self.workflow_display_to_id.clear()
        self.workflow_id_to_record.clear()
        self.workflow_title_var.set("Select a workflow to begin.")
        self.workflow_view.show_placeholder()

    @staticmethod
    def _friendly_workflow_name(workflow: dict[str, Any], fallback_index: int) -> str:
        raw = str(workflow.get("workflow_name") or workflow.get("workflow_type") or "").strip()
        if raw:
            cleaned = " ".join(raw.replace("_", " ").replace("-", " ").split())
            aliases = {
                "box art": "Box Art",
                "boxart": "Box Art",
                "display": "Display",
                "speed paint": "Speed Paint",
                "speedpaint": "Speed Paint",
                "competition": "Competition",
                "grimdark": "Grimdark",
                "tabletop": "Tabletop",
            }
            return aliases.get(cleaned.casefold(), cleaned.title())
        return f"Workflow {fallback_index}"

    @staticmethod
    def _set_combo(combo: ttk.Combobox, values: list[Any], *, sort: bool = True) -> None:
        cleaned = list(dict.fromkeys(str(value).strip() for value in values if value is not None and str(value).strip()))
        if sort:
            cleaned.sort(key=str.casefold)
        combo.configure(values=cleaned, state="readonly" if cleaned else "disabled")

    @staticmethod
    def _reset_combo(combo: ttk.Combobox, variable: tk.StringVar) -> None:
        variable.set("")
        combo.configure(values=(), state="disabled")

    @staticmethod
    def _show_error(message: str, error: Exception) -> None:
        messagebox.showerror("Application Error", f"{message}\n\n{type(error).__name__}: {error}")


def main() -> None:
    app = PaintingAssistantApp()
    app.mainloop()


if __name__ == "__main__":
    main()
