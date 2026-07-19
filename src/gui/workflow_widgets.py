"""Reusable Tkinter widgets for workflow presentation."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Iterable


Palette = dict[str, str]


def normalize_hex(value: Any, fallback: str = "#777777") -> str:
    """Return a Tk-compatible six-digit hex colour."""
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    if not text.startswith("#"):
        text = f"#{text}"
    if len(text) == 4:
        text = "#" + "".join(character * 2 for character in text[1:])
    if len(text) != 7:
        return fallback
    try:
        int(text[1:], 16)
    except ValueError:
        return fallback
    return text.upper()


def _is_light_colour(hex_colour: str) -> bool:
    colour = normalize_hex(hex_colour)
    red = int(colour[1:3], 16)
    green = int(colour[3:5], 16)
    blue = int(colour[5:7], 16)
    luminance = (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)
    return luminance >= 190


def _rounded_rectangle(
    canvas: tk.Canvas,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int,
    **kwargs: Any,
) -> int:
    radius = max(1, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class PaintSwatch(tk.Canvas):
    """Reusable rounded paint swatch used throughout the application."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        colour: Any,
        palette: Palette,
        width: int = 52,
        height: int = 28,
        radius: int = 5,
        background: str | None = None,
        command: Callable[[], None] | None = None,
    ) -> None:
        self._width = width
        self._height = height
        self._radius = radius
        self._palette = palette
        self._colour = normalize_hex(colour)
        self._command = command
        self._hovered = False
        super().__init__(
            parent,
            width=width,
            height=height,
            background=background or palette["card"],
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2" if command else "arrow",
        )
        self._draw()
        if command:
            self.bind("<Button-1>", lambda _event: command())
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)

    @property
    def colour(self) -> str:
        return self._colour

    def set_colour(self, colour: Any) -> None:
        self._colour = normalize_hex(colour)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        border = "#272A30" if _is_light_colour(self._colour) else self._palette["border"]
        if self._hovered:
            border = self._palette["accent"]
        _rounded_rectangle(
            self,
            1,
            1,
            self._width - 1,
            self._height - 1,
            self._radius,
            fill=self._colour,
            outline=border,
            width=2 if _is_light_colour(self._colour) or self._hovered else 1,
        )

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._draw()


class BreadcrumbBar(ttk.Frame):
    """Compact breadcrumb showing the current workflow selection path."""

    def __init__(self, parent: tk.Misc, palette: Palette) -> None:
        super().__init__(parent, style="App.TFrame")
        self._palette = palette
        self._parts: list[str] = []
        self._label = ttk.Label(self, style="Breadcrumb.TLabel")
        self._label.pack(anchor="w", fill="x")
        self.set_parts([])

    def set_parts(self, parts: Iterable[str]) -> None:
        self._parts = [str(part).strip() for part in parts if str(part).strip()]
        self._label.configure(
            text="  >  ".join(self._parts) if self._parts else "Select a workflow to begin"
        )


class ChromeTabStrip(tk.Canvas):
    """Chrome-style touching tabs with paint swatches and close controls."""

    TAB_HEIGHT = 42
    TAB_MIN_WIDTH = 150
    TAB_MAX_WIDTH = 235
    PLUS_WIDTH = 42
    TAB_OVERLAP = 16

    def __init__(
        self,
        parent: tk.Misc,
        *,
        palette: Palette,
        on_activate: Callable[[str], None],
        on_close: Callable[[str], None],
        on_add: Callable[[], None],
    ) -> None:
        super().__init__(
            parent,
            height=self.TAB_HEIGHT,
            background=palette["background"],
            highlightthickness=0,
            borderwidth=0,
        )
        self._palette = palette
        self._on_activate = on_activate
        self._on_close = on_close
        self._on_add = on_add
        self._tabs: list[dict[str, Any]] = []
        self._active_key: str | None = None
        self._hit_areas: list[tuple[int, int, str, str]] = []
        self._hover: tuple[str, str] | None = None
        self.bind("<Button-1>", self._handle_click)
        self.bind("<Motion>", self._handle_motion)
        self.bind("<Leave>", self._handle_leave)
        self.bind("<Configure>", lambda _event: self.redraw())

    def set_tabs(self, tabs: list[dict[str, Any]], active_key: str | None) -> None:
        self._tabs = tabs
        self._active_key = active_key
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        self._hit_areas.clear()
        p = self._palette
        available = max(self.winfo_width(), 500) - self.PLUS_WIDTH - 8
        count = max(len(self._tabs), 1)
        usable = available + max(0, count - 1) * self.TAB_OVERLAP
        tab_width = min(self.TAB_MAX_WIDTH, max(self.TAB_MIN_WIDTH, usable // count))

        positions: list[tuple[dict[str, Any], int]] = []
        x = 0
        for tab in self._tabs:
            positions.append((tab, x))
            x += tab_width - self.TAB_OVERLAP

        # Chrome draws the active tab above its neighbours.
        inactive = [item for item in positions if str(item[0]["key"]) != self._active_key]
        active = [item for item in positions if str(item[0]["key"]) == self._active_key]
        for tab, tab_x in [*inactive, *active]:
            self._draw_tab(tab, tab_x, tab_width)

        plus_x = max(8, x + 5)
        plus_hover = self._hover == ("+", "add")
        self.create_oval(
            plus_x,
            7,
            plus_x + 30,
            37,
            fill=p["field"] if plus_hover else p["card"],
            outline=p["border"],
            width=1,
        )
        self.create_text(plus_x + 15, 22, text="+", fill=p["text"], font=("Segoe UI", 15))
        self._hit_areas.append((plus_x, plus_x + 30, "+", "add"))

    def _draw_tab(self, tab: dict[str, Any], x: int, width: int) -> None:
        p = self._palette
        key = str(tab["key"])
        active = key == self._active_key
        top = 2 if active else 6
        bottom = self.TAB_HEIGHT + 2 if active else self.TAB_HEIGHT - 1
        fill = p["panel"] if active else p["card"]
        if self._hover == (key, "tab") and not active:
            fill = p["field"]

        # Close to Chromium's current tab profile: shallow shoulders, rounded crown,
        # and overlapping lower wings so adjacent tabs physically touch.
        points = [
            x, bottom,
            x + 8, bottom - 1,
            x + 13, bottom - 5,
            x + 18, top + 9,
            x + 23, top + 4,
            x + 31, top + 1,
            x + width - 31, top + 1,
            x + width - 23, top + 4,
            x + width - 18, top + 9,
            x + width - 13, bottom - 5,
            x + width - 8, bottom - 1,
            x + width, bottom,
        ]
        self.create_polygon(
            points,
            smooth=True,
            splinesteps=30,
            fill=fill,
            outline=p["border"],
            width=1,
        )
        if active:
            self.create_line(x + 8, bottom - 1, x + width - 8, bottom - 1, fill=p["panel"], width=4)

        colour = normalize_hex(tab.get("colour"))
        border = "#272A30" if _is_light_colour(colour) else p["border"]
        self.create_oval(x + 24, top + 13, x + 38, top + 27, fill=colour, outline=border, width=1)

        name = str(tab.get("name") or "Unknown paint")
        max_chars = max(10, int((width - 86) / 7.1))
        label = name if len(name) <= max_chars else name[: max_chars - 1] + "…"
        self.create_text(
            x + 46,
            top + 20,
            text=label,
            anchor="w",
            fill=p["text"],
            font=("Segoe UI", 10),
        )

        close_x = x + width - 27
        close_hover = self._hover == (key, "close")
        if close_hover:
            self.create_oval(close_x - 8, top + 12, close_x + 8, top + 28, fill="#4A4F57", outline="")
        self.create_text(
            close_x,
            top + 20,
            text="×",
            fill=p["text"] if close_hover else p["muted"],
            font=("Segoe UI", 9),
        )

        self._hit_areas.append((x + 5, x + width - 5, key, "tab"))
        self._hit_areas.append((close_x - 12, close_x + 12, key, "close"))

    def _hit_test(self, x: int) -> tuple[str, str] | None:
        for left, right, key, action in reversed(self._hit_areas):
            if left <= x <= right:
                return key, action
        return None

    def _handle_click(self, event: tk.Event) -> None:
        hit = self._hit_test(event.x)
        if not hit:
            return
        key, action = hit
        if action == "close":
            self._on_close(key)
        elif action == "add":
            self._on_add()
        else:
            self._on_activate(key)

    def _handle_motion(self, event: tk.Event) -> None:
        hit = self._hit_test(event.x)
        if hit != self._hover:
            self._hover = hit
            self.configure(cursor="hand2" if hit else "arrow")
            self.redraw()

    def _handle_leave(self, _event: tk.Event) -> None:
        self._hover = None
        self.configure(cursor="arrow")
        self.redraw()


class PaintSearchDialog(tk.Toplevel):
    """Cascading brand/type/name paint search dialog."""

    ALL_BRANDS = "All Brands"
    ALL_TYPES = "All Paint Types"

    def __init__(
        self,
        parent: tk.Misc,
        *,
        palette: Palette,
        repository: Any,
        on_open: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._repository = repository
        self._on_open = on_open
        self.title("Browse Paints")
        self.configure(background=palette["panel"])
        self.resizable(False, False)
        self.minsize(470, 310)
        self.transient(parent.winfo_toplevel())

        self.brand_var = tk.StringVar(value=self.ALL_BRANDS)
        self.type_var = tk.StringVar(value=self.ALL_TYPES)
        self.paint_var = tk.StringVar()
        self._paint_lookup: dict[str, dict[str, Any]] = {}

        outer = ttk.Frame(self, padding=24, style="Panel.TFrame")
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="Browse Paints", style="PopupTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text="Filter the paint library, then open the selected paint in the inspector.",
            style="PopupSubtle.TLabel",
            wraplength=410,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 18))

        self.brand_combo = self._combo(outer, 2, "Brand", self.brand_var)
        self.type_combo = self._combo(outer, 3, "Paint Type", self.type_var)
        self.paint_combo = self._combo(outer, 4, "Paint Name", self.paint_var)

        buttons = ttk.Frame(outer, style="Panel.TFrame")
        buttons.grid(row=5, column=0, sticky="e", pady=(22, 0))
        ttk.Button(buttons, text="Cancel", style="Secondary.TButton", command=self.destroy).pack(side="left", padx=(0, 8))
        self.open_button = ttk.Button(buttons, text="Open Paint", style="Primary.TButton", command=self._open_selected)
        self.open_button.pack(side="left")

        self.brand_combo.bind("<<ComboboxSelected>>", self._on_brand_changed)
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)
        self.paint_combo.bind("<<ComboboxSelected>>", self._on_paint_changed)
        self.bind("<Return>", lambda _event: self._open_selected())
        self.bind("<Escape>", lambda _event: self.destroy())
        self._load_brands()
        self.after_idle(self._center_on_parent)

    def _combo(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> ttk.Combobox:
        container = ttk.Frame(parent, style="Panel.TFrame")
        container.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(container, text=label, style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 6))
        combo = ttk.Combobox(container, textvariable=variable, state="readonly", style="Dark.TCombobox")
        combo.pack(fill="x")
        return combo

    def _load_brands(self) -> None:
        brands = self._repository.get_paint_brands()
        self.brand_combo.configure(values=[self.ALL_BRANDS, *brands])
        self._reload_types_and_paints()

    def _on_brand_changed(self, _event: tk.Event) -> None:
        self.type_var.set(self.ALL_TYPES)
        self.paint_var.set("")
        self._reload_types_and_paints()

    def _on_type_changed(self, _event: tk.Event) -> None:
        self.paint_var.set("")
        self._reload_paints()

    def _on_paint_changed(self, _event: tk.Event) -> None:
        self.open_button.configure(state="normal" if self.paint_var.get() in self._paint_lookup else "disabled")
        self.open_button.focus_set()

    def _reload_types_and_paints(self) -> None:
        brand = None if self.brand_var.get() == self.ALL_BRANDS else self.brand_var.get()
        types = self._repository.get_paint_types(brand=brand)
        self.type_combo.configure(values=[self.ALL_TYPES, *types])
        self._reload_paints()

    def _reload_paints(self) -> None:
        brand = None if self.brand_var.get() == self.ALL_BRANDS else self.brand_var.get()
        paint_type = None if self.type_var.get() == self.ALL_TYPES else self.type_var.get()
        paints = self._repository.search_paints(brand=brand, paint_type=paint_type)
        self._paint_lookup.clear()
        display_values: list[str] = []
        name_counts: dict[str, int] = {}
        for paint in paints:
            name = str(paint.get("paint_name") or "Unknown paint").strip()
            key = name.casefold()
            name_counts[key] = name_counts.get(key, 0) + 1
            occurrence = name_counts[key]
            display = name if occurrence == 1 else f"{name} ({occurrence})"
            self._paint_lookup[display] = paint
            display_values.append(display)
        self.paint_combo.configure(values=display_values, state="readonly" if display_values else "disabled")
        if display_values:
            # Leave selection blank so the user deliberately chooses a paint,
            # but make the control visibly usable and keep Open Paint disabled
            # until a selection is made.
            self.open_button.configure(state="disabled")
        else:
            self.paint_var.set("")
            self.open_button.configure(state="disabled")

    def _open_selected(self) -> None:
        selected = self._paint_lookup.get(self.paint_var.get())
        if not selected:
            self.bell()
            return
        self._on_open(selected)
        self.destroy()

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")


class InventoryWindow(tk.Toplevel):
    """Simple owned-paint workspace with live plus/minus quantity controls."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        palette: Palette,
        repository: Any,
        on_open_paint: Callable[[dict[str, Any]], None],
        on_destroyed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._repository = repository
        self._on_open_paint = on_open_paint
        self._on_destroyed = on_destroyed
        self.title("Paint Inventory")
        self.geometry("720x620")
        self.minsize(560, 420)
        self.configure(background=palette["background"])
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        outer = ttk.Frame(self, padding=18, style="Panel.TFrame")
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        ttk.Label(outer, text="Paint Inventory", style="PopupTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))

        host = ttk.Frame(outer, style="Panel.TFrame")
        host.grid(row=1, column=0, sticky="nsew")
        host.columnconfigure(0, weight=1)
        host.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(host, background=palette["panel"], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(host, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.rows = ttk.Frame(self.canvas, style="Panel.TFrame")
        self._window_id = self.canvas.create_window((0, 0), window=self.rows, anchor="nw")
        self.canvas.bind("<Configure>", self._resize_content)
        self.rows.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.bind("<Escape>", lambda _event: self.destroy())
        self._reload()
        self.after_idle(self._center_on_parent)

    def destroy(self) -> None:
        if self._on_destroyed:
            callback = self._on_destroyed
            self._on_destroyed = None
            callback()
        super().destroy()

    def _reload(self) -> None:
        for child in self.rows.winfo_children():
            child.destroy()
        paints = self._repository.get_inventory_paints()
        if not paints:
            ttk.Label(
                self.rows,
                text="No paints are currently recorded as owned.",
                style="Placeholder.TLabel",
            ).pack(anchor="w", padx=4, pady=4)
            return
        for paint in paints:
            self._build_row(paint)

    def _build_row(self, paint: dict[str, Any]) -> None:
        row = ttk.Frame(self.rows, padding=(12, 10), style="InspectorCard.TFrame")
        row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(1, weight=1)
        PaintSwatch(
            row,
            colour=paint.get("hex"),
            palette=self._palette,
            width=46,
            height=28,
            radius=5,
            background=self._palette["card"],
            command=lambda item=paint: self._on_open_paint(item),
        ).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
        name = str(paint.get("paint_name") or "Unknown paint")
        label = ttk.Label(row, text=name, style="InspectorValueCard.TLabel", cursor="hand2")
        label.grid(row=0, column=1, sticky="w")
        label.bind("<Button-1>", lambda _event, item=paint: self._on_open_paint(item))
        details = " • ".join(
            str(value).strip()
            for value in (paint.get("company") or paint.get("brand"), paint.get("product_line") or paint.get("paint_type"))
            if value and str(value).strip()
        )
        ttk.Label(row, text=details, style="InspectorMutedCard.TLabel").grid(row=1, column=1, sticky="w", pady=(3, 0))

        quantity_var = tk.IntVar(value=PaintInspector._inventory_number(paint))
        controls = ttk.Frame(row, style="InspectorCard.TFrame")
        controls.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))
        ttk.Button(
            controls,
            text="−",
            width=3,
            style="Secondary.TButton",
            command=lambda: self._change(paint, quantity_var, -1),
        ).pack(side="left")
        ttk.Label(controls, textvariable=quantity_var, width=4, anchor="center", style="InspectorValueCard.TLabel").pack(side="left", padx=6)
        ttk.Button(
            controls,
            text="+",
            width=3,
            style="Secondary.TButton",
            command=lambda: self._change(paint, quantity_var, 1),
        ).pack(side="left")

    def _change(self, paint: dict[str, Any], variable: tk.IntVar, delta: int) -> None:
        value = max(0, int(variable.get()) + delta)
        try:
            saved = self._repository.set_inventory_quantity(
                paint_id=paint.get("paint_id"),
                paint_name=paint.get("paint_name"),
                quantity=value,
            )
        except Exception as error:
            messagebox.showerror("Inventory Error", f"Inventory could not be updated.\n\n{error}", parent=self)
            return
        variable.set(saved)
        paint["quantity"] = saved
        if saved == 0:
            self.after_idle(self._reload)

    def _resize_content(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window_id, width=max(1, event.width))

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")


class PaintInspector(tk.Toplevel):
    """Non-modal multi-paint inspector with Chrome-like tabs."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        palette: Palette,
        repository: Any,
        on_destroyed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._repository = repository
        self._on_destroyed = on_destroyed
        self._tabs: dict[str, dict[str, Any]] = {}
        self._tab_order: list[str] = []
        self._active_key: str | None = None
        self._search_dialog: PaintSearchDialog | None = None
        self._active_scroll_canvas: tk.Canvas | None = None

        self.title("Paint Inspector")
        self.configure(background=palette["background"])
        self.geometry("820x650")
        self.minsize(650, 500)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _event: self.destroy())

        # Toplevel bindings are reached through Tk's bindtags for child widgets,
        # so the wheel scrolls the active paint canvas no matter which label,
        # swatch, button, or blank area the pointer is over. This mirrors the
        # free-scroll behavior of the main workflow view without stealing the
        # application's global mouse-wheel bindings.
        self.bind("<MouseWheel>", self._on_inspector_mousewheel, add="+")
        self.bind("<Button-4>", self._on_inspector_mousewheel, add="+")
        self.bind("<Button-5>", self._on_inspector_mousewheel, add="+")

        self.tab_strip = ChromeTabStrip(
            self,
            palette=palette,
            on_activate=self.activate_tab,
            on_close=self.close_tab,
            on_add=self.open_search,
        )
        self.tab_strip.pack(fill="x")

        self.content_host = ttk.Frame(self, padding=(18, 16, 18, 18), style="Panel.TFrame")
        self.content_host.pack(fill="both", expand=True)
        self.content_host.columnconfigure(0, weight=1)
        self.content_host.rowconfigure(0, weight=1)

        self.after_idle(self._center_on_parent)

    def destroy(self) -> None:
        if self._on_destroyed:
            callback = self._on_destroyed
            self._on_destroyed = None
            callback()
        super().destroy()

    def open_paint(self, paint: dict[str, Any], equivalents: list[dict[str, Any]] | None = None) -> None:
        key = self._paint_key(paint)
        if key in self._tabs:
            self.activate_tab(key)
            self.deiconify()
            self.lift()
            return

        paint_id = paint.get("paint_id")
        paint_name = str(paint.get("paint_name") or "Unknown paint").strip()
        if equivalents is None:
            equivalents = self._repository.get_paint_equivalents(paint_id=paint_id, paint_name=paint_name)

        frame = self._build_paint_page(paint, equivalents)
        self._tabs[key] = {
            "key": key,
            "name": paint_name,
            "colour": paint.get("hex") or paint.get("paint_hex"),
            "frame": frame,
            "scroll_canvas": getattr(frame, "scroll_canvas", None),
        }
        self._tab_order.append(key)
        self.activate_tab(key)
        self.deiconify()
        self.lift()

    def activate_tab(self, key: str) -> None:
        tab = self._tabs.get(key)
        if not tab:
            return
        for other in self._tabs.values():
            other["frame"].grid_remove()
        tab["frame"].grid(row=0, column=0, sticky="nsew")
        self._active_scroll_canvas = tab.get("scroll_canvas")
        self._active_key = key
        self._refresh_strip()
        self.title(f"Paint Inspector — {tab['name']}")

    def close_tab(self, key: str) -> None:
        tab = self._tabs.pop(key, None)
        if not tab:
            return
        tab["frame"].destroy()
        index = self._tab_order.index(key)
        self._tab_order.remove(key)
        if not self._tab_order:
            self.destroy()
            return
        if self._active_key == key:
            next_index = min(index, len(self._tab_order) - 1)
            self.activate_tab(self._tab_order[next_index])
        else:
            self._refresh_strip()

    def open_search(self) -> None:
        if self._search_dialog and self._search_dialog.winfo_exists():
            self._search_dialog.deiconify()
            self._search_dialog.lift()
            return
        self._search_dialog = PaintSearchDialog(
            self,
            palette=self._palette,
            repository=self._repository,
            on_open=self._open_from_search,
        )

    def _open_from_search(self, selected: dict[str, Any]) -> None:
        details = self._repository.get_paint_details(
            paint_id=selected.get("paint_id"),
            paint_name=selected.get("paint_name"),
        ) or selected
        self.open_paint(details)

    def _refresh_strip(self) -> None:
        tabs = [self._tabs[key] for key in self._tab_order]
        self.tab_strip.set_tabs(tabs, self._active_key)

    @staticmethod
    def _paint_key(paint: dict[str, Any]) -> str:
        paint_id = str(paint.get("paint_id") or "").strip()
        if paint_id:
            return f"id:{paint_id.casefold()}"
        name = str(paint.get("paint_name") or "Unknown paint").strip().casefold()
        company = str(paint.get("company") or paint.get("brand") or "").strip().casefold()
        return f"name:{company}:{name}"

    def _build_paint_page(
        self,
        paint: dict[str, Any],
        equivalents: list[dict[str, Any]],
    ) -> ttk.Frame:
        # The tab strip stays fixed. Everything below it lives in a dedicated
        # scrollable canvas so long equivalent/near-match lists remain usable.
        page = ttk.Frame(self.content_host, style="Panel.TFrame")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)

        scroll_canvas = tk.Canvas(
            page,
            background=self._palette["panel"],
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(page, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scroll_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        content = ttk.Frame(scroll_canvas, padding=(2, 0, 10, 8), style="Panel.TFrame")
        content.columnconfigure(0, weight=1)
        window_id = scroll_canvas.create_window((0, 0), window=content, anchor="nw")

        def refresh_scrollregion(_event: tk.Event | None = None) -> None:
            bbox = scroll_canvas.bbox("all")
            if bbox:
                scroll_canvas.configure(scrollregion=bbox)

        def resize_content(event: tk.Event) -> None:
            scroll_canvas.itemconfigure(window_id, width=max(1, event.width))
            refresh_scrollregion()

        scroll_canvas.bind("<Configure>", resize_content)
        content.bind("<Configure>", refresh_scrollregion)

        header = ttk.Frame(content, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(1, weight=1)

        PaintSwatch(
            header,
            colour=paint.get("hex") or paint.get("paint_hex"),
            palette=self._palette,
            width=86,
            height=86,
            radius=10,
            background=self._palette["panel"],
        ).grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 18))

        paint_name = str(paint.get("paint_name") or "Unknown paint")
        ttk.Label(header, text=paint_name, style="PopupTitle.TLabel").grid(row=0, column=1, sticky="sw")
        company_line = " • ".join(
            str(value).strip()
            for value in (
                paint.get("company") or paint.get("brand"),
                paint.get("product_line") or paint.get("paint_type"),
            )
            if value and str(value).strip()
        )
        ttk.Label(header, text=company_line or "Paint details", style="PopupSubtle.TLabel").grid(
            row=1, column=1, sticky="nw", pady=(4, 0)
        )

        body = ttk.Frame(content, style="Panel.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)

        inventory_card = ttk.Frame(body, padding=16, style="InspectorCard.TFrame")
        inventory_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        inventory_card.columnconfigure(1, weight=1)
        ttk.Label(inventory_card, text="Inventory", style="AreaTitleCard.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )
        ttk.Label(inventory_card, text="Owned", style="InspectorKey.TLabel").grid(row=1, column=0, sticky="w")

        quantity_var = tk.IntVar(value=self._inventory_number(paint))
        controls = ttk.Frame(inventory_card, style="InspectorCard.TFrame")
        controls.grid(row=1, column=1, sticky="w", padx=(18, 0))
        ttk.Button(
            controls, text="−", width=3, style="Secondary.TButton",
            command=lambda: self._change_inventory(paint, quantity_var, -1),
        ).pack(side="left")
        ttk.Label(
            controls, textvariable=quantity_var, style="InspectorValueCard.TLabel",
            anchor="center", width=5,
        ).pack(side="left", padx=8)
        ttk.Button(
            controls, text="+", width=3, style="Secondary.TButton",
            command=lambda: self._change_inventory(paint, quantity_var, 1),
        ).pack(side="left")

        wishlist = paint.get("wishlist")
        ttk.Label(inventory_card, text="Wishlist", style="InspectorKey.TLabel").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Label(
            inventory_card,
            text=str(wishlist) if wishlist not in (None, "") else "Not recorded",
            style="InspectorValue.TLabel",
        ).grid(row=2, column=1, sticky="w", padx=(18, 0), pady=(10, 0))

        matches_card = ttk.Frame(body, padding=16, style="InspectorCard.TFrame")
        matches_card.grid(row=1, column=0, sticky="ew")
        matches_card.columnconfigure(0, weight=1)

        ttk.Label(matches_card, text="Equivalent Paints", style="AreaTitleCard.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        row_index = 1
        if equivalents:
            for equivalent in equivalents[:12]:
                self._build_match_row(matches_card, row_index, equivalent, show_percentage=True)
                row_index += 1
        else:
            ttk.Label(
                matches_card, text="No curated equivalents were found.",
                style="InspectorMutedCard.TLabel",
            ).grid(row=row_index, column=0, sticky="w")
            row_index += 1

        ttk.Separator(matches_card, orient="horizontal").grid(
            row=row_index, column=0, sticky="ew", pady=14
        )
        row_index += 1
        ttk.Label(matches_card, text="Near Matches", style="AreaTitleCard.TLabel").grid(
            row=row_index, column=0, sticky="w", pady=(0, 10)
        )
        row_index += 1

        near_matches = self._repository.get_near_matches(
            paint_id=paint.get("paint_id"), paint_name=paint_name, limit=12,
        )
        if near_matches:
            for match in near_matches:
                self._build_match_row(matches_card, row_index, match, show_percentage=True)
                row_index += 1
        else:
            ttk.Label(
                matches_card, text="No near-color matches could be calculated.",
                style="InspectorMutedCard.TLabel",
            ).grid(row=row_index, column=0, sticky="w")

        page.scroll_canvas = scroll_canvas  # type: ignore[attr-defined]
        page.refresh_scrollregion = refresh_scrollregion  # type: ignore[attr-defined]
        page.after_idle(refresh_scrollregion)
        return page

    def _build_match_row(
        self,
        parent: ttk.Frame,
        grid_row: int,
        record: dict[str, Any],
        *,
        show_percentage: bool,
    ) -> None:
        row = ttk.Frame(parent, style="InspectorCard.TFrame")
        row.grid(row=grid_row, column=0, sticky="ew", pady=(0, 7))
        row.columnconfigure(1, weight=1)
        PaintSwatch(
            row,
            colour=record.get("hex") or record.get("paint_hex"),
            palette=self._palette,
            width=38,
            height=22,
            radius=4,
            background=self._palette["card"],
            command=lambda item=record: self._open_equivalent(item),
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        name = str(record.get("paint_name") or record.get("equivalent_paint_name") or "Unknown paint")
        company = str(record.get("company") or record.get("brand") or "").strip()
        line = str(record.get("product_line") or record.get("paint_type") or "").strip()
        details = " • ".join(part for part in (company, line) if part)
        text_frame = ttk.Frame(row, style="InspectorCard.TFrame")
        text_frame.grid(row=0, column=1, sticky="ew")
        label = ttk.Label(text_frame, text=name, style="InspectorValueCard.TLabel", cursor="hand2")
        label.pack(anchor="w")
        if details:
            ttk.Label(text_frame, text=details, style="InspectorMutedCard.TLabel").pack(anchor="w")
        label.bind("<Button-1>", lambda _event, item=record: self._open_equivalent(item))

        if show_percentage:
            percentage = self._match_percentage(record)
            ttk.Label(
                row,
                text=f"{percentage:.1f}%" if percentage is not None else "—",
                style="InspectorValueCard.TLabel",
                anchor="e",
                width=8,
            ).grid(row=0, column=2, sticky="e", padx=(12, 0))

    def _change_inventory(self, paint: dict[str, Any], variable: tk.IntVar, delta: int) -> None:
        new_value = max(0, int(variable.get()) + delta)
        try:
            saved = self._repository.set_inventory_quantity(
                paint_id=paint.get("paint_id"),
                paint_name=paint.get("paint_name"),
                quantity=new_value,
            )
        except Exception as error:
            self.bell()
            messagebox.showerror("Inventory Error", f"Inventory could not be updated.\n\n{error}", parent=self)
            return
        variable.set(saved)
        paint["quantity"] = saved

    def _open_equivalent(self, record: dict[str, Any]) -> None:
        details = self._repository.get_paint_details(
            paint_id=record.get("paint_id") or record.get("equivalent_paint_id"),
            paint_name=record.get("paint_name") or record.get("equivalent_paint_name"),
        ) or record
        self.open_paint(details)

    @staticmethod
    def _inventory_number(paint: dict[str, Any]) -> int:
        for key in ("quantity", "inventory_quantity", "owned_quantity", "inventory"):
            value = paint.get(key)
            if value is not None and str(value).strip() != "":
                try:
                    return max(0, int(float(str(value))))
                except (TypeError, ValueError):
                    pass
        return 0

    @staticmethod
    def _match_percentage(record: dict[str, Any]) -> float | None:
        for key in ("match_percentage", "similarity_percentage", "similarity", "percentage", "score"):
            value = record.get(key)
            if value is None or str(value).strip() == "":
                continue
            try:
                number = float(value)
                if 0 <= number <= 1:
                    number *= 100
                return max(0.0, min(100.0, number))
            except (TypeError, ValueError):
                continue
        return None

    def _on_inspector_mousewheel(self, event: tk.Event) -> str | None:
        canvas = self._active_scroll_canvas
        if canvas is None or not canvas.winfo_exists():
            return None
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = int(getattr(event, "delta", 0))
            if delta == 0:
                return None
            units = -max(1, abs(delta) // 120) if delta > 0 else max(1, abs(delta) // 120)
        canvas.yview_scroll(units, "units")
        return "break"

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")


class PaintStepCard(ttk.Frame):
    """One interactive workflow step with a clickable colour swatch."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        step: dict[str, Any],
        palette: Palette,
        popup_callback: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(parent, padding=(12, 10), style="Card.TFrame")
        self.columnconfigure(1, weight=1)
        self._step = step
        self._popup_callback = popup_callback

        paint_name = str(step.get("paint_name") or "Unknown paint").strip()
        technique = str(step.get("technique") or "Painting step").strip()
        purpose = str(step.get("purpose") or "").strip()
        notes = str(step.get("notes") or "").strip()
        optional = str(step.get("optional") or "").strip().casefold() in {"1", "true", "yes", "y"}

        swatch = PaintSwatch(
            self,
            colour=step.get("paint_hex") or step.get("hex"),
            palette=palette,
            width=52,
            height=28,
            radius=5,
            background=palette["card"],
            command=self._open_popup,
        )
        swatch.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 12))

        paint_label = ttk.Label(self, text=paint_name, style="PaintName.TLabel", cursor="hand2")
        paint_label.grid(row=0, column=1, sticky="w")
        paint_label.bind("<Button-1>", self._open_popup)

        technique_text = technique + ("  ·  Optional" if optional else "")
        ttk.Label(self, text=technique_text, style="Technique.TLabel").grid(row=1, column=1, sticky="w", pady=(2, 0))

        description = purpose
        if notes:
            description = f"{description}\n{notes}" if description else notes
        if description:
            ttk.Label(
                self,
                text=description,
                style="Purpose.TLabel",
                wraplength=860,
                justify="left",
            ).grid(row=2, column=1, sticky="ew", pady=(5, 0))

    def _open_popup(self, _event: tk.Event | None = None) -> None:
        self._popup_callback(self._step)


class AreaSection(ttk.Frame):
    """Collapsible model-area section containing paint-step cards."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        steps: list[dict[str, Any]],
        palette: Palette,
        popup_callback: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(parent, padding=0, style="Area.TFrame")
        self._expanded = True
        self._body = ttk.Frame(self, padding=(12, 4, 12, 12), style="Area.TFrame")
        self._toggle = ttk.Button(
            self,
            text=f"▼  {title}",
            style="AreaHeader.TButton",
            command=lambda: self.toggle(title),
        )
        self._toggle.pack(fill="x")
        self._body.pack(fill="x")

        for index, step in enumerate(steps):
            card = PaintStepCard(
                self._body,
                step=step,
                palette=palette,
                popup_callback=popup_callback,
            )
            card.pack(fill="x", pady=(0, 7 if index < len(steps) - 1 else 0))

    def toggle(self, title: str) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self._body.pack(fill="x")
            self._toggle.configure(text=f"▼  {title}")
        else:
            self._body.pack_forget()
            self._toggle.configure(text=f"▶  {title}")


class WorkflowView(ttk.Frame):
    """Scrollable workflow renderer with reliable wheel handling."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        palette: Palette,
        popup_callback: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self._palette = palette
        self._popup_callback = popup_callback
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, background=palette["panel"], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.content = ttk.Frame(self.canvas, style="Panel.TFrame")
        self._window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Enter>", self._activate_wheel)
        self.canvas.bind("<Leave>", self._deactivate_wheel)
        self.show_placeholder()

    def destroy(self) -> None:
        self._deactivate_wheel()
        super().destroy()

    def clear(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)
        self.canvas.configure(scrollregion=(0, 0, 0, 0))

    def show_placeholder(self, text: str = "Select a workflow to view its painting steps.") -> None:
        self.clear()
        ttk.Label(self.content, text=text, style="Placeholder.TLabel").pack(anchor="w", padx=8, pady=8)

    def display_steps(self, steps: list[dict[str, Any]]) -> None:
        self.clear()
        if not steps:
            self.show_placeholder("No workflow steps were found.")
            return
        grouped: dict[str, list[dict[str, Any]]] = {}
        for step in steps:
            area = str(step.get("model_area") or "General").strip() or "General"
            grouped.setdefault(area, []).append(step)
        for area, area_steps in grouped.items():
            section = AreaSection(
                self.content,
                title=area,
                steps=area_steps,
                palette=self._palette,
                popup_callback=self._popup_callback,
            )
            section.pack(fill="x", padx=(0, 4), pady=(0, 10))
        self.update_idletasks()
        self._refresh_scrollregion()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window_id, width=max(event.width, 1))
        self._refresh_scrollregion()

    def _on_content_configure(self, _event: tk.Event) -> None:
        self._refresh_scrollregion()

    def _refresh_scrollregion(self) -> None:
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def _activate_wheel(self, _event: tk.Event | None = None) -> None:
        root = self.winfo_toplevel()
        root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        root.bind_all("<Button-4>", self._on_mousewheel, add="+")
        root.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _deactivate_wheel(self, _event: tk.Event | None = None) -> None:
        root = self.winfo_toplevel()
        root.unbind_all("<MouseWheel>")
        root.unbind_all("<Button-4>")
        root.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: tk.Event) -> str:
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = int(getattr(event, "delta", 0))
            units = -max(1, abs(delta) // 120) if delta > 0 else max(1, abs(delta) // 120)
        self.canvas.yview_scroll(units, "units")
        return "break"
