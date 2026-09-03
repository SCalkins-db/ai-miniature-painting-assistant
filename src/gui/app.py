"""Full desktop-shell redesign for the AI Miniature Painting Assistant."""

from __future__ import annotations
from pathlib import Path
import tkinter as tk

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from src.database.workflow_repository import WorkflowRepository
from src.gui.workflow_widgets import (
    ChromeTabStrip,
    CollapseRail,
    DetailsPane,
    DocumentTab,
    PaintBrowser,
    PaintDocument,
    WorkflowDocument,
    InventoryDocument,
    WorkspaceHost,
    display_text,
    record_value,
)


class PaintingAssistantApp(tk.Tk):
    WINDOW_TITLE = "AI Miniature Painting Assistant"
    WINDOW_GEOMETRY = "1500x930"
    WINDOW_MIN_WIDTH = 1050
    WINDOW_MIN_HEIGHT = 680
    SELECT = "[Select]"
    ALL_COMPANIES = "[All Companies]"
    VERSION = "v2.1.8"

    PALETTE = {
        "background": "#11161D",
        "panel": "#19212B",
        "card": "#202A35",
        "field": "#1B2530",
        "tab": "#1A2430",
        "section": "#1D2732",
        "text": "#F3F6FA",
        "muted": "#B7C0CB",
        "border": "#3A4653",
        "accent": "#2F7FE5",
        "green": "#44C05A",
        "danger": "#D64242",
    }

    def __init__(self) -> None:
        super().__init__()

        print(icon_path)

        icon_path = Path(__file__).resolve().parents[2] / "assets" / "icons" / "master_icon.png"

        self.app_icon = tk.PhotoImage(file=str(icon_path))
        self.iconphoto(True, self.app_icon)

        self.title(self.WINDOW_TITLE)
        self.geometry(self.WINDOW_GEOMETRY)

        self.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)
        self.configure(bg=self.PALETTE["background"])

        self.repository = WorkflowRepository()
        self._paint_cache: list[dict[str, Any]] = []
        self._documents: dict[str, dict[str, Any]] = {}
        self._document_widgets: dict[str, ttk.Frame] = {}
        self._tabs: list[DocumentTab] = []
        self._active_key = "workflow:home"
        self._left_visible = True
        self._right_visible = True
        self._workflow_display_to_id: dict[str, str] = {}
        self._workflow_records: dict[str, dict[str, Any]] = {}
        self._implicit_subfaction = ""

        self.superfaction_var = tk.StringVar(value=self.SELECT)
        self.faction_var = tk.StringVar(value=self.SELECT)
        self.subfaction_var = tk.StringVar(value=self.SELECT)
        self.unit_var = tk.StringVar(value=self.SELECT)
        self.workflow_var = tk.StringVar(value=self.SELECT)
        self.status_left = tk.StringVar(value="Loading paints…")
        self.status_right = tk.StringVar(value="●  Ready")

        self._configure_styles()
        self._build_shell()
        self._bind_workflow_events()
        self._create_home_document()
        self._load_superfactions()
        self._load_paint_cache_async()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        p = self.PALETTE
        for name, background in (
            ("App.TFrame", p["background"]),
            ("Panel.TFrame", p["panel"]),
            ("Card.TFrame", p["card"]),
            ("Section.TFrame", p["section"]),
            ("MatchRow.TFrame", p["section"]),
            ("WorkflowRow.TFrame", p["card"]),
            ("Rail.TFrame", p["background"]),
        ):
            style.configure(name, background=background)

        style.configure("PaneTitle.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 12, "bold"))
        style.configure("ToolbarLabel.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("FilterLabel.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=p["panel"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("SearchIcon.TLabel", background=p["panel"], foreground=p["muted"], font=("Segoe UI", 14))
        style.configure("DocumentTitle.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 20, "bold"))
        style.configure("SectionTitle.TLabel", background=p["section"], foreground=p["text"], font=("Segoe UI", 13, "bold"))
        style.configure("SectionSubtle.TLabel", background=p["section"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("CardText.TLabel", background=p["card"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("Counter.TLabel", background="#111820", foreground=p["text"], relief="solid", borderwidth=1, font=("Segoe UI", 10))
        style.configure("Chip.TLabel", background=p["field"], foreground=p["text"], relief="solid", borderwidth=1, padding=(10, 4), font=("Segoe UI", 10))
        style.configure("DetailKey.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("DetailValue.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("MatchName.TLabel", background=p["section"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("MatchMeta.TLabel", background=p["section"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("MatchPercent.TLabel", background=p["section"], foreground=p["text"], font=("Segoe UI", 10))
        style.configure("WorkflowPaint.TLabel", background=p["card"], foreground=p["text"], font=("Segoe UI", 12, "bold"))
        style.configure("WorkflowTechnique.TLabel", background=p["card"], foreground="#9EC5FF", font=("Segoe UI", 10))
        style.configure("WorkflowDescription.TLabel", background=p["card"], foreground=p["muted"], font=("Segoe UI", 10))
        style.configure("EmptyTitle.TLabel", background=p["panel"], foreground=p["text"], font=("Segoe UI", 17, "bold"))
        style.configure("Rail.TLabel", background=p["background"], foreground=p["muted"], font=("Segoe UI", 8))

        style.configure("Dark.TCombobox", fieldbackground=p["field"], background=p["field"], foreground=p["text"], arrowcolor=p["text"], bordercolor=p["field"], lightcolor=p["field"], darkcolor=p["field"], relief="flat", padding=(9, 7), arrowsize=13)
        style.map("Dark.TCombobox", fieldbackground=[("readonly", p["field"]), ("disabled", p["background"])], background=[("readonly", p["field"]), ("active", p["field"])], foreground=[("readonly", p["text"]), ("disabled", "#68727E")], arrowcolor=[("readonly", p["text"]), ("active", p["text"])])
        style.configure("Dark.TEntry", fieldbackground=p["field"], foreground=p["text"], insertcolor=p["text"], bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"], relief="flat", padding=8)
        style.configure("Toolbar.TButton", background=p["field"], foreground=p["text"], padding=(14, 8), borderwidth=1, bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"], relief="flat", font=("Segoe UI", 10, "bold"))
        style.configure("Secondary.TButton", background=p["field"], foreground=p["text"], padding=(10, 6), borderwidth=1, bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"], relief="flat", font=("Segoe UI", 10))
        style.configure("Tiny.TButton", background=p["field"], foreground=p["text"], padding=(4, 2), borderwidth=1, bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"], relief="flat", font=("Segoe UI", 10, "bold"))
        style.configure("TinyBlue.TButton", background=p["field"], foreground=p["text"], padding=(5, 3), borderwidth=1, bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"], relief="flat", font=("Segoe UI", 11, "bold"))
        style.configure("Rail.TButton", background=p["background"], foreground=p["muted"], borderwidth=0, relief="flat", font=("Segoe UI", 20, "bold"))
        style.configure("WorkflowSection.TButton", background=p["section"], foreground=p["text"], anchor="w", padding=(10, 8), borderwidth=0, font=("Segoe UI", 12, "bold"))
        style.map("Toolbar.TButton", background=[("active", p["card"]), ("pressed", p["background"])])
        style.map("Secondary.TButton", background=[("active", p["card"])])
        style.map("Tiny.TButton", background=[("active", p["card"])])
        style.map("TinyBlue.TButton", background=[("active", p["card"]), ("pressed", p["background"])])
        style.map("WorkflowSection.TButton", background=[("active", p["field"])])

        style.configure("SearchField.TFrame", background=p["field"], borderwidth=1, relief="solid")
        style.configure("Search.TEntry", fieldbackground=p["field"], foreground=p["text"], insertcolor=p["text"], borderwidth=0, relief="flat", padding=(8, 5, 30, 5))
        style.configure("SearchInside.TLabel", background=p["field"], foreground=p["muted"], font=("Segoe UI", 12))
        style.configure("Paint.Treeview", background=p["panel"], fieldbackground=p["panel"], foreground=p["text"], rowheight=27, bordercolor=p["border"], font=("Segoe UI", 10))
        style.configure("Paint.Treeview.Heading", background=p["field"], foreground=p["text"], relief="flat", font=("Segoe UI", 10))
        style.map("Paint.Treeview.Heading", background=[("active", p["card"]), ("pressed", p["card"])], foreground=[("active", p["text"]), ("pressed", p["text"])])
        # Remove the unused tree-expander indentation so paint swatches sit flush
        # against the left edge of their fixed-width column.
        style.layout(
            "Paint.Treeview.Item",
            [("Treeitem.padding", {"sticky": "nswe", "children": [
                ("Treeitem.image", {"side": "left", "sticky": "w"}),
                ("Treeitem.text", {"sticky": "nswe"}),
            ]})],
        )
        style.map("Paint.Treeview", background=[("selected", "#294A70")], foreground=[("selected", "#FFFFFF")])
        style.configure("Shell.TPanedwindow", background=p["background"])
        style.configure("Dark.TSeparator", background=p["border"], bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"])
        style.configure("StatusReady.TLabel", background=p["panel"], foreground=p["green"], font=("Segoe UI", 10))
        style.configure("StatusError.TLabel", background=p["panel"], foreground=p["danger"], font=("Segoe UI", 10))
        style.configure("StatusLoading.TLabel", background=p["panel"], foreground="#D9A441", font=("Segoe UI", 10))
        style.configure("Vertical.TScrollbar", background="#343E49", troughcolor=p["background"], bordercolor=p["background"], arrowcolor=p["muted"], darkcolor="#343E49", lightcolor="#343E49")
        style.configure("Horizontal.TScrollbar", background="#343E49", troughcolor=p["background"], bordercolor=p["background"], arrowcolor=p["muted"], darkcolor="#343E49", lightcolor="#343E49")
        style.map("Vertical.TScrollbar", background=[("active", "#4B5663")])
        style.map("Horizontal.TScrollbar", background=[("active", "#4B5663")])

        self.option_add("*TCombobox*Listbox.background", p["field"])
        self.option_add("*TCombobox*Listbox.foreground", p["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", p["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    def _build_shell(self) -> None:
        shell = ttk.Frame(self, style="App.TFrame")
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        self.tab_strip = ChromeTabStrip(
            shell,
            palette=self.PALETTE,
            on_select=self._select_tab,
            on_close=self._close_tab,
            on_new=self._new_tab,
        )
        self.tab_strip.grid(row=0, column=0, sticky="ew")
        self._build_toolbar(shell)

        # The three working regions now live in a real horizontal paned window.
        # Dragging either sash resizes the workflow canvas while preserving the
        # overall application size.
        self.content_row = tk.PanedWindow(
            shell,
            orient=tk.HORIZONTAL,
            bg=self.PALETTE["border"],
            sashwidth=6,
            sashrelief="flat",
            bd=0,
            opaqueresize=False,
        )
        self.content_row.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)

        self.left_slot = ttk.Frame(self.content_row, style="App.TFrame", width=320)
        self.center_holder = ttk.Frame(self.content_row, style="Panel.TFrame")
        self.right_slot = ttk.Frame(self.content_row, style="App.TFrame", width=310)

        self.content_row.add(self.left_slot, minsize=26, width=320, stretch="never")
        self.content_row.add(self.center_holder, minsize=460, stretch="always")
        self.content_row.add(self.right_slot, minsize=26, width=310, stretch="never")

        self.left_slot.columnconfigure(0, weight=1)
        self.left_slot.rowconfigure(0, weight=1)
        self.right_slot.columnconfigure(0, weight=1)
        self.right_slot.rowconfigure(0, weight=1)

        self.left_holder = ttk.Frame(self.left_slot, style="Panel.TFrame")
        self.left_holder.grid(row=0, column=0, sticky="nsew")
        self.left_holder.columnconfigure(0, weight=1)
        self.left_holder.rowconfigure(0, weight=1)
        self.left_rail = CollapseRail(self.left_slot, text="", command=self._toggle_left, side="left", compact=True)

        self.center_holder.columnconfigure(0, weight=1)
        self.center_holder.rowconfigure(0, weight=1)
        self.workspace = WorkspaceHost(self.center_holder, palette=self.PALETTE)
        self.workspace.grid(row=0, column=0, sticky="nsew")

        self.right_holder = ttk.Frame(self.right_slot, style="Panel.TFrame")
        self.right_holder.grid(row=0, column=0, sticky="nsew")
        self.right_holder.columnconfigure(0, weight=1)
        self.right_holder.rowconfigure(0, weight=1)
        self.right_rail = CollapseRail(self.right_slot, text="", command=self._toggle_right, side="right", compact=True)

        self.paint_browser = PaintBrowser(
            self.left_holder,
            palette=self.PALETTE,
            on_select=self._preview_paint,
            on_open=self._open_paint_document,
            on_filters_changed=lambda: None,
            on_collapse=self._toggle_left,
        )
        self.paint_browser.grid(row=0, column=0, sticky="nsew")
        self.details_pane = DetailsPane(self.right_holder, palette=self.PALETTE, on_collapse=self._toggle_right)
        self.details_pane.grid(row=0, column=0, sticky="nsew")

        self._left_width = 320
        self._right_width = 310
        self.content_row.bind("<ButtonRelease-1>", self._remember_pane_widths, add="+")
        self.after_idle(self._restore_default_sashes)
        self._build_status_bar(shell)

    def _restore_default_sashes(self) -> None:
        self.update_idletasks()
        total = max(self.content_row.winfo_width(), 900)
        try:
            self.content_row.sash_place(0, self._left_width, 0)
            self.content_row.sash_place(1, max(self._left_width + 460, total - self._right_width), 0)
        except tk.TclError:
            pass

    def _remember_pane_widths(self, _event: tk.Event | None = None) -> None:
        if not self._left_visible or not self._right_visible:
            return
        try:
            first = self.content_row.sash_coord(0)[0]
            second = self.content_row.sash_coord(1)[0]
            total = self.content_row.winfo_width()
            self._left_width = max(220, first)
            self._right_width = max(220, total - second)
        except tk.TclError:
            pass

    def _build_toolbar(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, style="Panel.TFrame", padding=(14, 10))
        toolbar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 0))
        toolbar.columnconfigure(10, weight=1)
        self.superfaction_combo = self._toolbar_selector(toolbar, 0, "Superfaction", self.superfaction_var, 12, True)
        self.faction_combo = self._toolbar_selector(toolbar, 2, "Faction", self.faction_var, 24, False)
        self.subfaction_combo = self._toolbar_selector(toolbar, 4, "Subfaction", self.subfaction_var, 14, False)
        self.unit_combo = self._toolbar_selector(toolbar, 6, "Unit", self.unit_var, 32, False)
        self.workflow_combo = self._toolbar_selector(toolbar, 8, "Workflow", self.workflow_var, 15, False)
        ttk.Button(toolbar, text="↶  Reset", style="Toolbar.TButton", command=self._reset_workflow_filters).grid(row=0, column=11, padx=(12, 6))
        ttk.Button(toolbar, text="🎨  Browse Paints", style="Toolbar.TButton", command=self._show_left).grid(row=0, column=12, padx=6)
        ttk.Button(toolbar, text="▣  Inventory", style="Toolbar.TButton", command=self._open_inventory_document).grid(row=0, column=13, padx=(6, 0))

    def _toolbar_selector(self, parent: ttk.Frame, column: int, label: str, variable: tk.StringVar, width: int, enabled: bool) -> ttk.Combobox:
        ttk.Label(parent, text=label, style="ToolbarLabel.TLabel").grid(row=0, column=column, padx=(0 if column == 0 else 10, 5))
        combo = ttk.Combobox(parent, textvariable=variable, width=width, state="readonly" if enabled else "disabled", style="Dark.TCombobox")
        combo.grid(row=0, column=column + 1)
        return combo

    def _build_status_bar(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent, style="Panel.TFrame", padding=(12, 7))
        bar.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        bar.columnconfigure(1, weight=1)
        ttk.Label(bar, textvariable=self.status_left, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(bar, text=self.VERSION, style="Muted.TLabel").grid(row=0, column=2, padx=(10, 16))
        self.status_indicator = ttk.Label(bar, textvariable=self.status_right, style="StatusReady.TLabel")
        self.status_indicator.grid(row=0, column=3, sticky="e")

    def _toggle_left(self) -> None:
        if self._left_visible:
            self._remember_pane_widths()
            self._left_visible = False
            self.left_holder.grid_remove()
            self.left_rail.grid(row=0, column=0, sticky="nsew")
            self.content_row.paneconfigure(self.left_slot, minsize=26, width=26, stretch="never")
            self.after_idle(lambda: self.content_row.sash_place(0, 26, 0))
        else:
            self._left_visible = True
            self.left_rail.grid_remove()
            self.left_holder.grid(row=0, column=0, sticky="nsew")
            self.content_row.paneconfigure(self.left_slot, minsize=220, width=self._left_width, stretch="never")
            self.after_idle(lambda: self.content_row.sash_place(0, self._left_width, 0))

    def _toggle_right(self) -> None:
        if self._right_visible:
            self._remember_pane_widths()
            self._right_visible = False
            self.right_holder.grid_remove()
            self.right_rail.grid(row=0, column=0, sticky="nsew")
            self.content_row.paneconfigure(self.right_slot, minsize=26, width=26, stretch="never")
            self.after_idle(lambda: self.content_row.sash_place(1, max(80, self.content_row.winfo_width() - 26), 0))
        else:
            self._right_visible = True
            self.right_rail.grid_remove()
            self.right_holder.grid(row=0, column=0, sticky="nsew")
            self.content_row.paneconfigure(self.right_slot, minsize=220, width=self._right_width, stretch="never")
            self.after_idle(lambda: self.content_row.sash_place(1, max(80, self.content_row.winfo_width() - self._right_width), 0))

    def _show_left(self) -> None:
        if not self._left_visible:
            self._toggle_left()
        self.paint_browser.search_entry.focus_set()

    # ------------------------------------------------------------------
    # Paint cache and documents
    # ------------------------------------------------------------------

    def _set_status(self, state: str, text: str) -> None:
        self.status_right.set(f"●  {text}")
        style = {"ready": "StatusReady.TLabel", "loading": "StatusLoading.TLabel", "error": "StatusError.TLabel"}.get(state, "Muted.TLabel")
        if hasattr(self, "status_indicator"):
            self.status_indicator.configure(style=style)

    def _load_paint_cache_async(self) -> None:
        self.status_right.set("●  Loading")
        self._set_status("loading", "Loading")
        def worker() -> None:
            try:
                paints = self.repository.search_paints(limit=100000)
                companies = sorted({str(p.get("company") or p.get("brand") or "").strip() for p in paints if str(p.get("company") or p.get("brand") or "").strip()}, key=str.casefold)
                lines = sorted({str(p.get("product_line") or "").strip() for p in paints if str(p.get("product_line") or "").strip()}, key=str.casefold)
                for paint in paints:
                    raw_type = str(paint.get("paint_type") or "").strip()
                    if raw_type.casefold() == "acrylic paint":
                        paint["paint_type"] = "Acrylic Paint"
                types = sorted({str(p.get("paint_type") or "").strip() for p in paints if str(p.get("paint_type") or "").strip()}, key=str.casefold)
                self.after(0, lambda: self._paint_cache_loaded(paints, companies, lines, types))
            except Exception as exc:
                self.after(0, lambda: self._show_error("Unable to load the paint browser.", exc))
        threading.Thread(target=worker, daemon=True).start()

    def _paint_cache_loaded(self, paints: list[dict[str, Any]], companies: list[str], lines: list[str], types: list[str]) -> None:
        self._paint_cache = paints
        self.paint_browser.set_filter_values(companies, lines, types)
        self.paint_browser.set_paints(paints)
        self.status_left.set(f"Paints Loaded: {len(paints):,}")
        self._set_status("ready", "Ready")

    def _preview_paint(self, paint: dict[str, Any]) -> None:
        self.details_pane.show_paint(paint, [], [])
        def worker() -> None:
            try:
                details = self.repository.get_paint_details(
                    paint_id=paint.get("paint_id"),
                    paint_name=paint.get("paint_name"),
                ) or dict(paint)
                equivalents = self.repository.get_paint_equivalents(
                    paint_id=details.get("paint_id"),
                    paint_name=details.get("paint_name"),
                )
                near_matches = self.repository.get_near_matches(
                    paint_id=details.get("paint_id"),
                    paint_name=details.get("paint_name"),
                    limit=12,
                )
                self.after(
                    0,
                    lambda: self.details_pane.show_paint(
                        details,
                        equivalents,
                        near_matches,
                    ),
                )
            except Exception as exc:
                self.after(0, lambda: self._show_error("Unable to load paint details.", exc))
        threading.Thread(target=worker, daemon=True).start()

    def _open_paint_document(self, paint: dict[str, Any]) -> None:
        paint_id = str(paint.get("paint_id") or paint.get("paint_name") or "paint")
        key = f"paint:{paint_id}"
        title = display_text(paint.get("paint_name"), "Paint")
        widget = self._document_widgets.get(key)
        try:
            widget_alive = widget is not None and bool(widget.winfo_exists())
        except tk.TclError:
            widget_alive = False
        if key not in self._documents or not widget_alive:
            self._documents[key] = {"kind": "paint", "paint": paint}
            if not any(tab.key == key for tab in self._tabs):
                self._tabs.append(DocumentTab(key=key, title=title, kind="paint", colour=str(paint.get("hex") or "#777777")))
            widget = PaintDocument(self.workspace, palette=self.PALETTE, on_open_paint=self._open_paint_document, on_set_owned=self._set_owned, on_set_wishlist=self._set_wishlist)
            self._document_widgets[key] = widget
        self._active_key = key
        self._refresh_tabs()
        self._load_paint_document(key, paint)

    def _load_paint_document(self, key: str, paint: dict[str, Any]) -> None:
        self._set_status("loading", "Loading")
        self.details_pane.show_paint(paint, [], [])
        widget = self._document_widgets.get(key)
        if widget is None or not widget.winfo_exists():
            widget = PaintDocument(self.workspace, palette=self.PALETTE, on_open_paint=self._open_paint_document, on_set_owned=self._set_owned, on_set_wishlist=self._set_wishlist)
            self._document_widgets[key] = widget
        self.workspace.show(widget)
        def worker() -> None:
            try:
                details = self.repository.get_paint_details(paint_id=paint.get("paint_id"), paint_name=paint.get("paint_name")) or dict(paint)
                equivalents = self.repository.get_paint_equivalents(paint_id=details.get("paint_id"), paint_name=details.get("paint_name"))
                near = self.repository.get_near_matches(paint_id=details.get("paint_id"), paint_name=details.get("paint_name"), limit=18)
                self.after(0, lambda: self._paint_document_loaded(key, details, equivalents, near))
            except Exception as exc:
                self.after(0, lambda: self._show_error("Unable to load paint details.", exc))
        threading.Thread(target=worker, daemon=True).start()

    def _paint_document_loaded(self, key: str, paint: dict[str, Any], equivalents: list[dict[str, Any]], near: list[dict[str, Any]]) -> None:
        widget = self._document_widgets.get(key)
        if isinstance(widget, PaintDocument):
            widget.show_paint(paint, equivalents, near)
        self._documents[key]["paint"] = paint
        if key == self._active_key:
            self.details_pane.show_paint(paint, equivalents, near)
        self._set_status("ready", "Ready")

    def _set_owned(self, paint: dict[str, Any], quantity: int) -> None:
        try:
            self.repository.set_inventory_quantity(paint_id=paint.get("paint_id"), paint_name=paint.get("paint_name"), quantity=quantity)
            paint["quantity"] = quantity
            self.paint_browser.apply_local_filters()
        except Exception as exc:
            self._show_error("Unable to update owned quantity.", exc)

    def _set_wishlist(self, paint: dict[str, Any], quantity: int) -> None:
        try:
            self.repository.set_wishlist_quantity(paint_id=paint.get("paint_id"), paint_name=paint.get("paint_name"), quantity=quantity)
            paint["wishlist_quantity"] = quantity
        except Exception as exc:
            self._show_error("Unable to update wishlist quantity.", exc)

    def _open_inventory_document(self) -> None:
        key = "inventory:owned"
        widget = self._document_widgets.get(key)
        if widget is None or not bool(widget.winfo_exists()):
            self._documents[key] = {"kind": "inventory"}
            if not any(tab.key == key for tab in self._tabs):
                self._tabs.append(DocumentTab(key=key, title="Inventory", kind="inventory", colour="#4AA36B"))
            widget = InventoryDocument(self.workspace, palette=self.PALETTE, on_open_paint=self._open_paint_document, on_set_owned=self._set_owned, on_set_wishlist=self._set_wishlist)
            self._document_widgets[key] = widget
        self._active_key = key
        self._refresh_tabs()
        self.workspace.show(widget)
        self.details_pane.show_message("")
        self._set_status("loading", "Loading")
        try:
            paints = [dict(p) for p in self.repository.get_inventory_paints()]
            assert isinstance(widget, InventoryDocument)
            widget.show_inventory(paints)
            self._set_status("ready", "Ready")
        except Exception as exc:
            self._show_error("Unable to load inventory.", exc)

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    def _create_home_document(self) -> None:
        key = "workflow:home"
        self._documents[key] = {"kind": "workflow", "title": "Workflow Explorer"}
        self._tabs.append(DocumentTab(key=key, title="Workflow Explorer", kind="workflow", colour="#6D7B89", closable=False))
        widget = WorkflowDocument(self.workspace, palette=self.PALETTE, on_open_paint=self._open_paint_document)
        widget.show_placeholder()
        self._document_widgets[key] = widget
        self.workspace.show(widget)
        self._refresh_tabs()

    def _refresh_tabs(self) -> None:
        self.tab_strip.set_tabs(self._tabs, self._active_key)

    def _select_tab(self, key: str) -> None:
        if key not in self._documents:
            return
        self._active_key = key
        self._refresh_tabs()
        widget = self._document_widgets.get(key)
        if widget is None or not widget.winfo_exists():
            document = self._documents[key]
            if document["kind"] == "inventory":
                self._open_inventory_document()
                return
            if document["kind"] == "paint":
                self._open_paint_document(document["paint"])
                return
            widget = WorkflowDocument(self.workspace, palette=self.PALETTE, on_open_paint=self._open_paint_from_step)
            self._document_widgets[key] = widget
            if document.get("steps") is not None:
                widget.show_workflow(document.get("title") or document.get("workflow", {}).get("workflow_name") or "Workflow", document.get("steps", []))
            else:
                widget.show_placeholder()
        self.workspace.show(widget)
        document = self._documents[key]
        if document["kind"] == "paint":
            self.details_pane.show_paint(document["paint"], [])
        elif document["kind"] == "workflow" and document.get("workflow"):
            steps = document.get("steps", [])
            self.details_pane.show_workflow(document["workflow"], len(steps))
        elif document["kind"] == "inventory":
            self._open_inventory_document()
            return
        else:
            self.details_pane.show_message("Select a workflow or paint to view details.")

    def _close_tab(self, key: str) -> None:
        tab = next((item for item in self._tabs if item.key == key), None)
        if not tab or not tab.closable:
            return
        index = self._tabs.index(tab)
        self._tabs.remove(tab)
        widget = self._document_widgets.pop(key, None)
        if widget:
            if getattr(self.workspace, "current", None) is widget:
                self.workspace.current = None
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self._documents.pop(key, None)
        if self._active_key == key:
            replacement = self._tabs[max(0, index - 1)]
            self._select_tab(replacement.key)
        else:
            self._refresh_tabs()

    def _new_tab(self) -> None:
        """Keep the reserved tab control honest until multi-document creation ships."""
        self._set_status("ready", "New tab support is planned")

    # ------------------------------------------------------------------
    # Workflow selectors and workspace
    # ------------------------------------------------------------------

    def _bind_workflow_events(self) -> None:
        self.superfaction_combo.bind("<<ComboboxSelected>>", self._on_superfaction)
        self.faction_combo.bind("<<ComboboxSelected>>", self._on_faction)
        self.subfaction_combo.bind("<<ComboboxSelected>>", self._on_subfaction)
        self.unit_combo.bind("<<ComboboxSelected>>", self._on_unit)
        self.workflow_combo.bind("<<ComboboxSelected>>", self._on_workflow)

    def _set_combo(self, combo: ttk.Combobox, variable: tk.StringVar, values: list[str], enabled: bool = True) -> None:
        cleaned = sorted({str(v).strip() for v in values if str(v).strip()}, key=str.casefold)
        combo.configure(values=[self.SELECT, *cleaned], state="readonly" if enabled and cleaned else "disabled")
        # Faction and Unit names vary dramatically in length. Size these two
        # controls from the actual populated values so names are not clipped.
        if combo is getattr(self, "faction_combo", None):
            combo.configure(width=max(24, min(42, max([len(v) for v in cleaned] or [24]) + 2)))
        elif combo is getattr(self, "unit_combo", None):
            combo.configure(width=max(32, min(48, max([len(v) for v in cleaned] or [32]) + 2)))
        variable.set(self.SELECT)

    def _reset_lower(self, *items: tuple[ttk.Combobox, tk.StringVar]) -> None:
        for combo, variable in items:
            combo.configure(values=[self.SELECT], state="disabled")
            variable.set(self.SELECT)

    def _load_superfactions(self) -> None:
        try:
            self._set_combo(self.superfaction_combo, self.superfaction_var, self.repository.get_superfactions())
        except Exception as exc:
            self._show_error("Unable to load superfactions.", exc)

    def _on_superfaction(self, _event: tk.Event) -> None:
        value = self.superfaction_var.get()
        self._reset_lower((self.faction_combo, self.faction_var), (self.subfaction_combo, self.subfaction_var), (self.unit_combo, self.unit_var), (self.workflow_combo, self.workflow_var))
        if value == self.SELECT:
            return
        try:
            self._set_combo(self.faction_combo, self.faction_var, self.repository.get_factions(value))
        except Exception as exc:
            self._show_error("Unable to load factions.", exc)

    def _on_faction(self, _event: tk.Event) -> None:
        superfaction, faction = self.superfaction_var.get(), self.faction_var.get()
        self._reset_lower((self.subfaction_combo, self.subfaction_var), (self.unit_combo, self.unit_var), (self.workflow_combo, self.workflow_var))
        if self.SELECT in (superfaction, faction):
            return
        try:
            values = [str(value).strip() for value in self.repository.get_subfactions(superfaction, faction) if str(value).strip()]
            self._implicit_subfaction = ""
            if values:
                self._set_combo(self.subfaction_combo, self.subfaction_var, values)
            else:
                # Preserve the original pre-v2 path behavior for factions with no
                # explicit subfaction value: use an empty database value and load units.
                self.subfaction_combo.configure(values=[self.SELECT], state="disabled")
                self.subfaction_var.set(self.SELECT)
                self._load_units_for_selection(superfaction, faction, "")
        except Exception as exc:
            self._show_error("Unable to load subfactions.", exc)

    def _load_units_for_selection(self, superfaction: str, faction: str, subfaction: str) -> None:
        self._reset_lower((self.unit_combo, self.unit_var), (self.workflow_combo, self.workflow_var))
        try:
            self._set_combo(self.unit_combo, self.unit_var, self.repository.get_units(superfaction, faction, subfaction))
        except Exception as exc:
            self._show_error("Unable to load units.", exc)

    def _on_subfaction(self, _event: tk.Event) -> None:
        superfaction, faction, subfaction = self.superfaction_var.get(), self.faction_var.get(), self.subfaction_var.get()
        if self.SELECT in (superfaction, faction, subfaction):
            return
        self._load_units_for_selection(superfaction, faction, subfaction)

    def _on_unit(self, _event: tk.Event) -> None:
        self._reset_lower((self.workflow_combo, self.workflow_var))
        superfaction, faction, subfaction, unit = self.superfaction_var.get(), self.faction_var.get(), self.subfaction_var.get(), self.unit_var.get()
        if self.SELECT in (superfaction, faction, unit):
            return
        db_sub = self._implicit_subfaction if subfaction in (self.SELECT, "No Subfaction") else subfaction
        try:
            records = self.repository.get_workflows(superfaction, faction, db_sub, unit)
            self._workflow_display_to_id.clear()
            self._workflow_records.clear()
            displays: list[str] = []
            for record in records:
                data = dict(record) if not isinstance(record, dict) and hasattr(record, "keys") else record
                workflow_id = str(record_value(data, "workflow_id", "Workflow_ID"))
                raw_name = str(record_value(data, "workflow_name", "Workflow_Name", "workflow_type", "Workflow_Type", default=workflow_id)).strip()
                upper_name = raw_name.upper()
                looks_like_identifier = ("_" in raw_name and raw_name == upper_name) or upper_name.startswith(("CHAOS_", "IMPERIUM_", "XENOS_"))
                name = "Box Art" if looks_like_identifier or not raw_name else raw_name
                label = name if name not in displays else f"{name} ({len(displays) + 1})"
                displays.append(label)
                self._workflow_display_to_id[label] = workflow_id
                self._workflow_records[workflow_id] = dict(data) if isinstance(data, dict) else {"workflow_id": workflow_id, "workflow_name": name}
            self._set_combo(self.workflow_combo, self.workflow_var, displays)
        except Exception as exc:
            self._show_error("Unable to load workflows.", exc)

    def _on_workflow(self, _event: tk.Event) -> None:
        label = self.workflow_var.get()
        if label == self.SELECT:
            return
        workflow_id = self._workflow_display_to_id.get(label, label)
        try:
            steps_raw = self.repository.get_workflow_steps(workflow_id)
            steps = [dict(step) if not isinstance(step, dict) and hasattr(step, "keys") else dict(step) for step in steps_raw]
            workflow = self._workflow_records.get(workflow_id) or self.repository.get_workflow(workflow_id) or {"workflow_id": workflow_id, "workflow_name": label}
            key = f"workflow:{workflow_id}"
            widget = self._document_widgets.get(key)
            if widget is None or not bool(widget.winfo_exists()):
                self._documents[key] = {"kind": "workflow", "workflow": workflow, "steps": steps}
                unit_title = self.unit_var.get() if self.unit_var.get() != self.SELECT else label
                if not any(tab.key == key for tab in self._tabs):
                    self._tabs.append(DocumentTab(key=key, title=unit_title, kind="workflow", colour="#6C8FB8"))
                widget = WorkflowDocument(self.workspace, palette=self.PALETTE, on_open_paint=self._open_paint_from_step)
                self._document_widgets[key] = widget
            self._documents[key] = {"kind": "workflow", "workflow": workflow, "steps": steps}
            self._active_key = key
            assert isinstance(widget, WorkflowDocument)
            widget.show_workflow(label, steps)
            self.workspace.show(widget)
            self.details_pane.show_workflow(workflow, len(steps))
            self._refresh_tabs()
        except Exception as exc:
            self._show_error("Unable to load workflow steps.", exc)

    def _open_paint_from_step(self, step: dict[str, Any]) -> None:
        paint = None
        paint_id = step.get("paint_id") or step.get("Paint_ID")
        paint_name = step.get("paint_name") or step.get("Paint_Name")
        try:
            paint = self.repository.get_paint_details(paint_id=paint_id, paint_name=paint_name)
        except Exception:
            paint = None
        if paint:
            self.details_pane.show_paint(paint)
            self._set_status("ready", "Ready")

    def _reset_workflow_filters(self) -> None:
        self.superfaction_var.set(self.SELECT)
        self._reset_lower((self.faction_combo, self.faction_var), (self.subfaction_combo, self.subfaction_var), (self.unit_combo, self.unit_var), (self.workflow_combo, self.workflow_var))
        self._workflow_display_to_id.clear()
        self._workflow_records.clear()
        self._implicit_subfaction = ""
        self._select_tab("workflow:home")
        home = self._document_widgets["workflow:home"]
        assert isinstance(home, WorkflowDocument)
        home.show_placeholder()
        self.details_pane.show_message("Select a paint or workflow to view details.")

    # ------------------------------------------------------------------

    def _show_error(self, message: str, error: Exception) -> None:
        self._set_status("error", "Error")
        messagebox.showerror("Application Error", f"{message}\n\n{type(error).__name__}: {error}")


def main() -> None:
    app = PaintingAssistantApp()
    app.mainloop()


if __name__ == "__main__":
    main()
