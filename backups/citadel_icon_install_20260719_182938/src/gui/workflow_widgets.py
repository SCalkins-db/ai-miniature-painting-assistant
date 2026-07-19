"""Desktop-shell widgets for the AI Miniature Painting Assistant.

This module intentionally contains no database code.  It provides reusable,
scrollable panels for the permanent paint browser, workspace documents,
workflow sections, paint details, and Chrome-style document tabs.
"""

from __future__ import annotations

import difflib
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable, Iterable, Sequence
from PIL import Image, ImageDraw, ImageFont, ImageTk

try:
    from src.gui.icon_factory import PaintIconFactory
except (ImportError, ModuleNotFoundError):
    PaintIconFactory = None  # Added in the next v2.1.8 increment.

Palette = dict[str, str]


def normalize_hex(value: Any, fallback: str = "#777777") -> str:
    text = str(value or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return fallback
    try:
        int(text, 16)
    except ValueError:
        return fallback
    return f"#{text.upper()}"


def display_text(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def record_value(record: Any, *keys: str, default: Any = "") -> Any:
    if isinstance(record, dict):
        for key in keys:
            if key in record and record[key] is not None:
                return record[key]
    if hasattr(record, "keys"):
        available = set(record.keys())
        for key in keys:
            if key in available and record[key] is not None:
                return record[key]
    for key in keys:
        if hasattr(record, key):
            value = getattr(record, key)
            if value is not None:
                return value
    return default


class HoverWheel:
    """Route wheel events to the scrollable region currently under the pointer."""

    def __init__(self, widget: tk.Misc, vertical: Callable[[int], None], horizontal: Callable[[int], None] | None = None) -> None:
        self.widget = widget
        self.vertical = vertical
        self.horizontal = horizontal
        root = widget.winfo_toplevel()
        root.bind_all("<MouseWheel>", self._wheel, add="+")
        root.bind_all("<Shift-MouseWheel>", self._shift_wheel, add="+")
        root.bind_all("<Button-4>", self._linux_up, add="+")
        root.bind_all("<Button-5>", self._linux_down, add="+")

    @staticmethod
    def _units(event: tk.Event) -> int:
        delta = int(getattr(event, "delta", 0))
        if delta == 0:
            return 0
        return -max(1, abs(delta) // 120) if delta > 0 else max(1, abs(delta) // 120)

    def _contains_pointer(self) -> bool:
        try:
            root = self.widget.winfo_toplevel()
            pointed = root.winfo_containing(root.winfo_pointerx(), root.winfo_pointery())
            while pointed is not None:
                if pointed == self.widget:
                    return True
                pointed = pointed.master
        except tk.TclError:
            return False
        return False

    def _wheel(self, event: tk.Event) -> str | None:
        if not self._contains_pointer():
            return None
        try:
            self.vertical(self._units(event))
        except tk.TclError:
            return None
        return "break"

    def _shift_wheel(self, event: tk.Event) -> str | None:
        if not self._contains_pointer():
            return None
        try:
            (self.horizontal or self.vertical)(self._units(event))
        except tk.TclError:
            return None
        return "break"

    def _linux_up(self, _event: tk.Event) -> str | None:
        if not self._contains_pointer():
            return None
        try:
            self.vertical(-3)
        except tk.TclError:
            return None
        return "break"

    def _linux_down(self, _event: tk.Event) -> str | None:
        if not self._contains_pointer():
            return None
        try:
            self.vertical(3)
        except tk.TclError:
            return None
        return "break"


class ScrollableFrame(ttk.Frame):
    """Canvas-backed frame with independent vertical and horizontal scrolling."""

    def __init__(self, parent: tk.Misc, *, palette: Palette, style: str = "Panel.TFrame", horizontal: bool = False) -> None:
        super().__init__(parent, style=style)
        self.palette = palette
        self.horizontal_enabled = horizontal
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=palette["panel"], highlightthickness=0, borderwidth=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        if horizontal:
            self.hbar.grid(row=1, column=0, sticky="ew")
        self.content = ttk.Frame(self.canvas, style=style)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.content.bind("<Configure>", self._on_content_configure)
        self.wheel = HoverWheel(self.canvas, self._scroll_y, self._scroll_x if horizontal else None)

    def _scroll_y(self, units: int) -> None:
        self.canvas.yview_scroll(units, "units")

    def _scroll_x(self, units: int) -> None:
        self.canvas.xview_scroll(units, "units")

    def _on_canvas_configure(self, event: tk.Event) -> None:
        if not self.horizontal_enabled:
            self.canvas.itemconfigure(self.window_id, width=max(1, event.width))
        self._refresh()

    def _on_content_configure(self, _event: tk.Event) -> None:
        self._refresh()

    def _refresh(self) -> None:
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def clear(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)
        self.canvas.configure(scrollregion=(0, 0, 0, 0))


@dataclass(slots=True)
class DocumentTab:
    key: str
    title: str
    kind: str
    colour: str = "#777777"
    closable: bool = True


class ChromeTabStrip(tk.Canvas):
    """Compact anti-aliased Chrome-style pill tabs."""

    SCALE = 3
    HEIGHT = 38

    def __init__(self, parent: tk.Misc, *, palette: Palette, on_select: Callable[[str], None], on_close: Callable[[str], None], on_new: Callable[[], None]) -> None:
        super().__init__(parent, height=self.HEIGHT, bg=palette["background"], highlightthickness=0, borderwidth=0)
        self.palette = palette
        self.on_select = on_select
        self.on_close = on_close
        self.on_new = on_new
        self.tabs: list[DocumentTab] = []
        self.active_key = ""
        self._hitboxes: list[tuple[int, int, str, str]] = []
        self._offset = 0
        self._photo: ImageTk.PhotoImage | None = None
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Button-1>", self._click)
        self.bind("<Button-2>", self._middle_click)
        self.bind("<MouseWheel>", self._wheel)

    def set_tabs(self, tabs: Sequence[DocumentTab], active_key: str) -> None:
        self.tabs = list(tabs)
        self.active_key = active_key
        self.redraw()

    @staticmethod
    def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        names = ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf") if bold else ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf")
        for name in names:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def redraw(self) -> None:
        width = max(self.winfo_width(), 200)
        height = self.HEIGHT
        scale = self.SCALE
        image = Image.new("RGB", (width * scale, height * scale), self.palette["background"])
        draw = ImageDraw.Draw(image)
        font = self._font(10 * scale)
        bold_font = self._font(10 * scale, bold=True)
        close_font = self._font(18 * scale, bold=True)
        plus_font = self._font(20 * scale)
        self._hitboxes.clear()
        x = 10 - self._offset
        max_x = max(width - 38, 90)
        top, bottom, radius = 4, 34, 15
        center_y = (top + bottom) / 2
        for tab in self.tabs:
            active = tab.key == self.active_key
            active_font = bold_font if active else font
            bbox = draw.textbbox((0, 0), tab.title, font=active_font)
            text_w = max(1, bbox[2] - bbox[0]) // scale
            tab_w = max(76, min(250, text_w + (54 if tab.closable else 38)))
            if x + tab_w >= 0 and x <= max_x:
                box = (x * scale, top * scale, (x + tab_w) * scale, bottom * scale)
                fill = self.palette["panel"] if active else self.palette["tab"]
                draw.rounded_rectangle(box, radius=radius * scale, fill=fill, outline=self.palette["border"], width=scale)
                colour = normalize_hex(tab.colour)
                dot = 10
                draw.ellipse(((x + 12) * scale, (center_y - dot/2) * scale, (x + 12 + dot) * scale, (center_y + dot/2) * scale), fill=colour)
                draw.text(((x + 30) * scale, center_y * scale), tab.title, fill=self.palette["text"], font=active_font, anchor="lm")
                self._hitboxes.append((x, x + tab_w, tab.key, "tab"))
                if tab.closable:
                    close_x = x + tab_w - 17
                    draw.text((close_x * scale, center_y * scale), "×", fill=self.palette["muted"], font=close_font, anchor="mm")
                    self._hitboxes.append((x + tab_w - 34, x + tab_w, tab.key, "close"))
            x += tab_w + 4
        plus_x = min(max(10, x + 3), max_x + 3)
        draw.ellipse((plus_x * scale, 3 * scale, (plus_x + 32) * scale, 35 * scale), fill=self.palette["tab"], outline=self.palette["border"], width=scale)
        draw.text(((plus_x + 16) * scale, 19 * scale), "+", fill=self.palette["text"], font=plus_font, anchor="mm")
        self._hitboxes.append((plus_x, plus_x + 32, "", "new"))
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(image)
        self.delete("all")
        self.create_image(0, 0, image=self._photo, anchor="nw")

    def _target(self, x: int) -> tuple[str, str] | None:
        for left, right, key, action in reversed(self._hitboxes):
            if left <= x <= right:
                return key, action
        return None

    def _click(self, event: tk.Event) -> None:
        target = self._target(event.x)
        if not target:
            return
        key, action = target
        if action == "new":
            self.on_new()
        elif action == "close":
            self.on_close(key)
        else:
            self.on_select(key)

    def _middle_click(self, event: tk.Event) -> None:
        target = self._target(event.x)
        if target and target[1] == "tab":
            self.on_close(target[0])

    def _wheel(self, event: tk.Event) -> str:
        delta = -1 if int(getattr(event, "delta", 0)) > 0 else 1
        self._offset = max(0, self._offset + delta * 90)
        self.redraw()
        return "break"


class CollapseRail(tk.Canvas):
    """A true 26-pixel dark restore rail. No text, no white hover state."""
    def __init__(self, parent: tk.Misc, *, text: str, command: Callable[[], None], side: str, compact: bool = False) -> None:
        super().__init__(parent, width=26, bg="#151D26", highlightthickness=0, borderwidth=0, cursor="hand2")
        self.command = command
        self.side = side
        self.bind("<Button-1>", lambda _e: self.command())
        self.bind("<Enter>", lambda _e: self.configure(bg="#202A35"))
        self.bind("<Leave>", lambda _e: self.configure(bg="#151D26"))
        self.bind("<Configure>", self._draw)

    def _draw(self, _event: tk.Event | None = None) -> None:
        self.delete("all")
        arrow = "›" if self.side == "left" else "‹"
        self.create_text(13, max(16, self.winfo_height()//2), text=arrow, fill="#B7C0CB", font=("Segoe UI", 16, "bold"))


class PaintBrowser(ttk.Frame):
    """Permanent left-side browser with cached, forgiving live search."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        palette: Palette,
        on_select: Callable[[dict[str, Any]], None],
        on_open: Callable[[dict[str, Any]], None],
        on_filters_changed: Callable[[], None],
        on_collapse: Callable[[], None],
    ) -> None:
        super().__init__(parent, style="Panel.TFrame", padding=10)
        self.palette = palette
        self.on_select = on_select
        self.on_open = on_open
        self.on_filters_changed = on_filters_changed
        self._all_paints: list[dict[str, Any]] = []
        self._visible_paints: list[dict[str, Any]] = []
        self._search_after: str | None = None
        self._swatch_images: list[tk.PhotoImage] = []
        self.icon_factory = PaintIconFactory(self, palette=palette) if PaintIconFactory is not None else None
        self._column_visible = {"name": True, "type": True, "owned": True}

        self.company_var = tk.StringVar(value="[All Companies]")
        self.line_var = tk.StringVar(value="[All Lines]")
        self.type_var = tk.StringVar(value="[All Types]")
        self.search_var = tk.StringVar()
        self.count_var = tk.StringVar(value="0 paints")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(8, weight=1)
        self.view_mode = "details"
        heading = ttk.Frame(self, style="Panel.TFrame")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="BROWSE PAINTS", style="PaneTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(heading, text="‹", width=2, style="Tiny.TButton", command=on_collapse).grid(row=0, column=1)

        self.company_combo = self._filter_row(1, "Company", self.company_var)
        self.line_combo = self._filter_row(2, "Product Line", self.line_var)
        self.type_combo = self._filter_row(3, "Paint Type", self.type_var)

        search_frame = ttk.Frame(self, style="SearchField.TFrame", padding=(0, 0))
        search_frame.grid(row=4, column=0, sticky="ew", pady=(4, 6))
        search_frame.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, style="Search.TEntry")
        self.search_entry.grid(row=0, column=0, sticky="ew", ipady=4)
        search_icon = ttk.Label(search_frame, text="⌕", style="SearchInside.TLabel", cursor="xterm")
        search_icon.place(relx=1.0, rely=0.5, x=-9, anchor="e")

        ttk.Button(self, text="⨯  Clear Filters", style="Secondary.TButton", command=self.reset_filters).grid(row=5, column=0, sticky="w", pady=(0, 8))
        ttk.Label(self, textvariable=self.count_var, style="Muted.TLabel").grid(row=6, column=0, sticky="w", pady=(0, 5))

        column_bar = ttk.Frame(self, style="Panel.TFrame")
        column_bar.grid(row=7, column=0, sticky="ew", pady=(0, 5))
        ttk.Label(column_bar, text="Columns", style="Muted.TLabel").pack(side="left")
        self.name_column_button = ttk.Button(column_bar, text="Paint Name", style="Tiny.TButton", command=lambda: self._toggle_column("name"))
        self.name_column_button.pack(side="left", padx=(8, 4))
        self.type_column_button = ttk.Button(column_bar, text="Type", style="Tiny.TButton", command=lambda: self._toggle_column("type"))
        self.type_column_button.pack(side="left", padx=4)
        self.owned_column_button = ttk.Button(column_bar, text="Owned", style="Tiny.TButton", command=lambda: self._toggle_column("owned"))
        self.owned_column_button.pack(side="left", padx=4)

        self.tree = ttk.Treeview(self, columns=("name", "type", "owned"), show="tree headings", selectmode="browse", style="Paint.Treeview")
        self.tree.heading("#0", text="", anchor="w")
        self.tree.column("#0", width=30, minwidth=30, stretch=False, anchor="w")
        self.tree.heading("name", text="Paint Name", anchor="w")
        self.tree.heading("type", text="Type", anchor="w")
        self.tree.heading("owned", text="Owned", anchor="w")
        self.tree.column("name", width=190, minwidth=110, stretch=True, anchor="w")
        self.tree.column("type", width=75, minwidth=55, stretch=False, anchor="w")
        self.tree.column("owned", width=45, minwidth=42, stretch=False, anchor="w")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hscroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll.set, xscrollcommand=hscroll.set)
        self.tree.bind("<Button-1>", self._guard_swatch_column, add="+")
        self.tree.grid(row=8, column=0, sticky="nsew")
        scroll.grid(row=8, column=1, sticky="ns")
        hscroll.grid(row=10, column=0, sticky="ew", pady=(4,0))
        view_bar = ttk.Frame(self, style="Panel.TFrame")
        view_bar.grid(row=9, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(view_bar, text="View", style="Muted.TLabel").pack(side="left")
        ttk.Button(view_bar, text="☷", width=3, style="Tiny.TButton", command=lambda: self.set_view_mode("details")).pack(side="left", padx=(8, 4))
        ttk.Button(view_bar, text="▦", width=3, style="Tiny.TButton", command=lambda: self.set_view_mode("swatches")).pack(side="left")
        self.tree.bind("<<TreeviewSelect>>", self._selected)
        self.tree.bind("<Double-1>", self._double_click)
        HoverWheel(self.tree, lambda units: self.tree.yview_scroll(units, "units"))

        for combo in (self.company_combo, self.line_combo, self.type_combo):
            combo.bind("<<ComboboxSelected>>", lambda _e: self._filters_changed())
        self.search_var.trace_add("write", self._search_changed)

    def _filter_row(self, row: int, label: str, variable: tk.StringVar) -> ttk.Combobox:
        frame = ttk.Frame(self, style="Panel.TFrame")
        frame.grid(row=row, column=0, sticky="ew", pady=3)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=label, style="FilterLabel.TLabel", width=12, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8))
        combo = ttk.Combobox(frame, textvariable=variable, state="readonly", style="Dark.TCombobox", width=22)
        combo.grid(row=0, column=1, sticky="ew")
        return combo

    def set_filter_values(self, companies: Iterable[str], product_lines: Iterable[str], paint_types: Iterable[str]) -> None:
        self.company_combo.configure(values=["[All Companies]", *companies])
        self.line_combo.configure(values=["[All Lines]", *product_lines])
        self.type_combo.configure(values=["[All Types]", *paint_types])

    def _toggle_column(self, column: str) -> None:
        """Show or hide one Browse Paints data column without losing the swatch."""
        self._column_visible[column] = not self._column_visible[column]
        self._apply_display_columns()

    def _apply_display_columns(self) -> None:
        visible = tuple(
            column
            for column in ("name", "type", "owned")
            if self._column_visible.get(column, True)
        )
        # Keep at least Paint Name visible so the browser remains usable.
        if not visible:
            self._column_visible["name"] = True
            visible = ("name",)
        self.tree.configure(displaycolumns=visible)
        state_text = {
            "name": "Paint Name" if self._column_visible["name"] else "+ Paint Name",
            "type": "Type" if self._column_visible["type"] else "+ Type",
            "owned": "Owned" if self._column_visible["owned"] else "+ Owned",
        }
        self.name_column_button.configure(text=state_text["name"])
        self.type_column_button.configure(text=state_text["type"])
        self.owned_column_button.configure(text=state_text["owned"])

    def _guard_swatch_column(self, event: tk.Event) -> str | None:
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        if column == "#0" and region in {"heading", "separator"}:
            return "break"
        return None

    def set_paints(self, paints: list[dict[str, Any]]) -> None:
        self._all_paints = paints
        self.apply_local_filters()

    def _filters_changed(self) -> None:
        self.on_filters_changed()
        self.apply_local_filters()

    def _search_changed(self, *_args: Any) -> None:
        if self._search_after:
            self.after_cancel(self._search_after)
        self._search_after = self.after(180, self.apply_local_filters)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [token for token in text.casefold().replace("-", " ").split() if token]

    @classmethod
    def _matches(cls, record: dict[str, Any], query: str) -> bool:
        if not query.strip():
            return True
        name = str(record.get("paint_name") or "").casefold()
        company = str(record.get("company") or record.get("brand") or "").casefold()
        line = str(record.get("product_line") or "").casefold()
        haystack = f"{name} {company} {line}"
        tokens = cls._tokens(query)
        if all(token in haystack for token in tokens):
            return True
        words = haystack.split()
        return all(any(word.startswith(token) or difflib.SequenceMatcher(None, token, word).ratio() >= 0.78 for word in words) for token in tokens)

    def _swatch_image(self, colour: str, size: int = 20) -> tk.PhotoImage:
        """Return a cached paint-pot icon, with a safe legacy fallback."""
        if self.icon_factory is not None:
            return self.icon_factory.get(colour, size=size, variant="pot")
        pad = 4
        scale = 3
        image = Image.new("RGBA", ((size + pad) * scale, size * scale), self.palette["panel"])
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (pad * scale, 0, (pad + size - 1) * scale, (size - 1) * scale),
            radius=3 * scale,
            fill=normalize_hex(colour),
            outline=self.palette["border"],
            width=scale,
        )
        image = image.resize((size + pad, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def _fit_columns(self) -> None:
        import tkinter.font as tkfont
        font = tkfont.nametofont("TkDefaultFont")
        names = [display_text(p.get("paint_name"), "") for p in self._visible_paints[:500]]
        types = [display_text(p.get("paint_type"), "") for p in self._visible_paints[:500]]
        self.tree.column("name", width=max(120, min(320, max([font.measure(v) for v in names] or [120]) + 24)))
        self.tree.column("type", width=max(70, min(180, max([font.measure(v) for v in types] or [70]) + 24)))

    def apply_local_filters(self) -> None:
        company = self.company_var.get()
        line = self.line_var.get()
        paint_type = self.type_var.get()
        query = self.search_var.get()
        visible: list[dict[str, Any]] = []
        for paint in self._all_paints:
            if company != "[All Companies]" and str(paint.get("company") or paint.get("brand") or "") != company:
                continue
            if line != "[All Lines]" and str(paint.get("product_line") or "") != line:
                continue
            if paint_type != "[All Types]" and str(paint.get("paint_type") or "") != paint_type:
                continue
            if not self._matches(paint, query):
                continue
            visible.append(paint)
        self._visible_paints = visible
        self.tree.delete(*self.tree.get_children())
        self._swatch_images.clear()
        swatch_size = 22
        self.tree.column("#0", width=34, minwidth=34, stretch=False, anchor="w")
        self.tree.configure(height=max(8, self.tree.cget("height")))
        for index, paint in enumerate(visible):
            paint_name = display_text(paint.get("paint_name"), "Unknown")
            paint_type_value = display_text(paint.get("paint_type"), "")
            if paint_type_value.casefold() == "acrylic paint":
                paint_type_value = "Acrylic Paint"
            owned = "" if self.view_mode == "swatches" else int(paint.get("quantity") or 0)
            image = self._swatch_image(str(paint.get("hex") or paint.get("paint_hex") or "#777777"), swatch_size)
            self._swatch_images.append(image)
            self.tree.insert("", "end", iid=str(index), image=image, values=(paint_name, paint_type_value, owned))
        self._fit_columns()
        self.count_var.set(f"{len(visible):,} paints found")


    def set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        if mode == "swatches":
            self.tree.heading("name", text="Paint Name", anchor="w")
            self.tree.column("name", width=215, minwidth=130, stretch=True)
            self.tree.column("type", width=70, minwidth=55, stretch=False)
            self.tree.column("owned", width=0, minwidth=0, stretch=False)
        else:
            self.tree.heading("name", text="Paint Name", anchor="w")
            self.tree.column("name", width=190, minwidth=110, stretch=True, anchor="w")
            self.tree.column("type", width=75, minwidth=55, stretch=False, anchor="w")
            self.tree.column("owned", width=45, minwidth=42, stretch=False)
        self.apply_local_filters()
    def reset_filters(self) -> None:
        self.company_var.set("[All Companies]")
        self.line_var.set("[All Lines]")
        self.type_var.set("[All Types]")
        self.search_var.set("")
        self.apply_local_filters()

    def _record_for_selection(self) -> dict[str, Any] | None:
        selected = self.tree.selection()
        if not selected:
            return None
        try:
            return self._visible_paints[int(selected[0])]
        except (ValueError, IndexError):
            return None

    def _selected(self, _event: tk.Event) -> None:
        record = self._record_for_selection()
        if record:
            self.on_select(record)
            self.on_open(record)

    def _double_click(self, event: tk.Event) -> None:
        if self.tree.identify_region(event.x, event.y) == "heading":
            self._fit_columns()
            return
        record = self._record_for_selection()
        if record:
            self.on_open(record)


class DetailsPane(ScrollableFrame):
    """Independently scrollable details pane with collapsible paint sections."""

    def __init__(self, parent: tk.Misc, *, palette: Palette, on_collapse: Callable[[], None]) -> None:
        super().__init__(parent, palette=palette)
        self.content.configure(padding=14)
        self.icon_factory = PaintIconFactory(self, palette=palette) if PaintIconFactory is not None else None
        self._icon_refs: list[tk.PhotoImage] = []
        self._section_state: dict[str, bool] = {}
        header = ttk.Frame(self.content, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="DETAILS", style="PaneTitle.TLabel").pack(side="left")
        ttk.Button(header, text="›", width=2, style="Tiny.TButton", command=on_collapse).pack(side="right")
        self.body = ttk.Frame(self.content, style="Panel.TFrame")
        self.body.pack(fill="both", expand=True)
        self.show_message("")

    def _clear_body(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self._icon_refs.clear()
        self.canvas.yview_moveto(0)

    def show_message(self, text: str) -> None:
        self._clear_body()
        if text.strip():
            ttk.Label(self.body, text=text, style="Muted.TLabel", wraplength=250, justify="left").pack(anchor="w")

    def _paint_icon(self, parent: tk.Misc, paint: dict[str, Any], size: int = 24) -> ttk.Label | tk.Canvas:
        colour = normalize_hex(paint.get("hex") or paint.get("paint_hex"))
        if self.icon_factory is not None:
            image = self.icon_factory.get(colour, size=size, variant="pot")
            self._icon_refs.append(image)
            return ttk.Label(parent, image=image, style="DetailValue.TLabel")
        canvas = tk.Canvas(parent, width=size, height=size, bg=self.palette["panel"], highlightthickness=0)
        canvas.create_oval(2, 2, size - 2, size - 2, fill=colour, outline=self.palette["border"])
        return canvas

    def _section(self, title: str, *, expanded: bool = True) -> ttk.Frame:
        shell = ttk.Frame(self.body, style="Panel.TFrame")
        shell.pack(fill="x", pady=(4, 8))
        content = ttk.Frame(shell, style="Panel.TFrame")
        key = title.casefold()
        state = self._section_state.get(key, expanded)
        self._section_state[key] = state
        label = tk.StringVar(value=("▾  " if state else "▸  ") + title)

        def toggle() -> None:
            shown = self._section_state[key]
            self._section_state[key] = not shown
            label.set(("▾  " if not shown else "▸  ") + title)
            if shown:
                content.pack_forget()
            else:
                content.pack(fill="x", pady=(6, 0))
            self._refresh()

        ttk.Button(shell, textvariable=label, style="WorkflowSection.TButton", command=toggle).pack(fill="x")
        if state:
            content.pack(fill="x", pady=(6, 0))
        return content

    @staticmethod
    def _exact_matches(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        exact: list[dict[str, Any]] = []
        for item in items or []:
            try:
                if float(item.get("match_percentage") or 100) >= 99.999:
                    exact.append(item)
            except (TypeError, ValueError):
                exact.append(item)
        return exact

    @staticmethod
    def _near_matches(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        near: list[dict[str, Any]] = []
        for item in items or []:
            try:
                if float(item.get("match_percentage") or 0) < 99.999:
                    near.append(item)
            except (TypeError, ValueError):
                near.append(item)
        return near

    def _match_rows(self, parent: ttk.Frame, items: list[dict[str, Any]], empty_text: str) -> None:
        if not items:
            ttk.Label(parent, text=empty_text, style="Muted.TLabel", wraplength=225, justify="left").pack(anchor="w", pady=4)
            return
        for item in items:
            row = ttk.Frame(parent, style="Panel.TFrame")
            row.pack(fill="x", pady=5)
            self._paint_icon(row, item, 24).pack(side="left", padx=(0, 8))
            text_frame = ttk.Frame(row, style="Panel.TFrame")
            text_frame.pack(side="left", fill="x", expand=True)
            name = display_text(item.get("paint_name") or item.get("equivalent_paint_name") or item.get("name"), "Unknown paint")
            meta = " • ".join(part for part in (display_text(item.get("company") or item.get("brand"), ""), display_text(item.get("product_line"), "")) if part)
            ttk.Label(text_frame, text=name, style="DetailValue.TLabel", font=("Segoe UI", 9, "bold"), wraplength=170, justify="left").pack(anchor="w")
            if meta:
                ttk.Label(text_frame, text=meta, style="Muted.TLabel", wraplength=170, justify="left").pack(anchor="w")
            percentage = item.get("match_percentage")
            if percentage not in (None, ""):
                try:
                    shown = f"{float(percentage):.1f}%"
                except (TypeError, ValueError):
                    shown = display_text(percentage, "")
                ttk.Label(row, text=shown, style="Muted.TLabel").pack(side="right", padx=(6, 0))

    def show_paint(self, paint: dict[str, Any], equivalents: list[dict[str, Any]] | None = None, near_matches: list[dict[str, Any]] | None = None) -> None:
        self._clear_body()

        info = self._section("PAINT INFORMATION")
        title_row = ttk.Frame(info, style="Panel.TFrame")
        title_row.pack(fill="x", pady=(0, 8))
        self._paint_icon(title_row, paint, 42).pack(side="left", padx=(0, 10))
        title_text = ttk.Frame(title_row, style="Panel.TFrame")
        title_text.pack(side="left", fill="x", expand=True)
        ttk.Label(title_text, text=display_text(paint.get("paint_name"), "Unknown paint"), style="PaneTitle.TLabel", wraplength=190, justify="left").pack(anchor="w")
        company_line = " • ".join(part for part in (display_text(paint.get("company") or paint.get("brand"), ""), display_text(paint.get("product_line"), "")) if part)
        if company_line:
            ttk.Label(title_text, text=company_line, style="Muted.TLabel", wraplength=190, justify="left").pack(anchor="w")

        fields = [
            ("Full Name", paint.get("paint_name")), ("Company", paint.get("company") or paint.get("brand")),
            ("Product Line", paint.get("product_line")), ("Paint Type", paint.get("paint_type")),
            ("Finish", paint.get("finish")), ("Opacity", paint.get("opacity")),
            ("Layer Coverage", paint.get("coverage") or paint.get("layer_coverage")),
            ("SKU / Code", paint.get("sku") or paint.get("code")),
            ("Release", paint.get("release") or paint.get("release_date")), ("Notes", paint.get("notes")),
        ]
        for label, value in fields:
            if value is None or str(value).strip() in {"", "—", "-"}:
                continue
            row = ttk.Frame(info, style="Panel.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, style="DetailKey.TLabel", width=14).pack(side="left", anchor="n")
            ttk.Label(row, text=display_text(value), style="DetailValue.TLabel", wraplength=170, justify="left").pack(side="left", fill="x", expand=True, anchor="n")

        preview = self._section("COLOR PREVIEW")
        colour = normalize_hex(paint.get("hex") or paint.get("paint_hex"))
        ttk.Label(preview, text=f"HEX  {colour}", style="DetailValue.TLabel").pack(anchor="w", pady=(0, 6))
        for label, background in (("On White", "#F4F4F4"), ("On Black", "#111111")):
            ttk.Label(preview, text=label, style="Muted.TLabel").pack(anchor="w", pady=(4, 2))
            canvas = tk.Canvas(preview, height=32, bg=background, highlightthickness=1, highlightbackground=self.palette["border"])
            canvas.pack(fill="x")
            canvas.bind("<Configure>", lambda e, c=canvas, fill=colour: (c.delete("preview"), c.create_rectangle(0, 0, e.width, e.height, fill=fill, outline="", tags="preview")))

        equivalents_section = self._section(f"EQUIVALENT PAINTS  ({len(self._exact_matches(equivalents))})")
        self._match_rows(equivalents_section, self._exact_matches(equivalents), "No exact equivalents were found.")

        near = self._near_matches(near_matches)
        near_section = self._section(f"NEAR MATCHES  ({len(near)})")
        self._match_rows(near_section, near, "No near matches were found.")
        self._refresh()

    def show_workflow(self, workflow: dict[str, Any], step_count: int) -> None:
        self._clear_body()
        section = self._section("WORKFLOW INFORMATION")
        fields = [
            ("Workflow", record_value(workflow, "workflow_name", "Workflow_Name", "workflow_type", "Workflow_Type", "workflow_id", "Workflow_ID")),
            ("Superfaction", record_value(workflow, "superfaction", "Superfaction")),
            ("Faction", record_value(workflow, "faction", "Faction")),
            ("Subfaction", record_value(workflow, "subfaction", "Subfaction")),
            ("Unit", record_value(workflow, "unit", "Unit", "character", "Character")),
            ("Painter", record_value(workflow, "painter", "Painter")), ("Steps", step_count),
            ("Source", record_value(workflow, "source", "Source", "video_title", "Video_Title")),
        ]
        for label, value in fields:
            if value is None or str(value).strip() in {"", "—", "-"}:
                continue
            row = ttk.Frame(section, style="Panel.TFrame")
            row.pack(fill="x", pady=5)
            ttk.Label(row, text=label, style="DetailKey.TLabel", width=14).pack(side="left", anchor="n")
            ttk.Label(row, text=display_text(value), style="DetailValue.TLabel", wraplength=170, justify="left").pack(side="left", fill="x", expand=True, anchor="n")
        self._refresh()


class InventoryAdjuster(ttk.Frame):
    def __init__(self, parent: tk.Misc, *, label: str, value: int, on_change: Callable[[int], None]) -> None:
        super().__init__(parent, style="Section.TFrame")
        self.value = max(0, int(value))
        self.on_change = on_change
        self.var = tk.StringVar(value=str(self.value))
        ttk.Label(self, text=label, style="SectionSubtle.TLabel", width=8).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Button(self, text="−", width=2, style="Tiny.TButton", command=lambda: self._change(-1)).grid(row=0, column=1)
        ttk.Label(self, textvariable=self.var, width=3, anchor="center", style="Counter.TLabel").grid(row=0, column=2, sticky="ns")
        ttk.Button(self, text="+", width=2, style="Tiny.TButton", command=lambda: self._change(1)).grid(row=0, column=3)

    def _change(self, delta: int) -> None:
        self.value = max(0, self.value + delta)
        self.var.set(str(self.value))
        self.on_change(self.value)


class NearMatchRow(ttk.Frame):
    def __init__(self, parent: tk.Misc, *, paint: dict[str, Any], palette: Palette, on_open: Callable[[dict[str, Any]], None], on_owned: Callable[[dict[str, Any], int], None]) -> None:
        super().__init__(parent, style="Section.TFrame")
        ttk.Separator(self, orient="horizontal", style="Dark.TSeparator").grid(row=0, column=0, columnspan=4, sticky="ew")
        self.columnconfigure(1, weight=1)
        colour = normalize_hex(paint.get("hex") or paint.get("paint_hex"))
        self.icon_factory = PaintIconFactory(self, palette=palette) if PaintIconFactory is not None else None
        self._icon_image: tk.PhotoImage | None = None
        if self.icon_factory is not None:
            self._icon_image = self.icon_factory.get(colour, size=38, variant="pot")
            swatch: tk.Misc = ttk.Label(self, image=self._icon_image, style="Section.TLabel", cursor="hand2")
        else:
            fallback = tk.Canvas(self, width=38, height=38, bg=palette["section"], highlightthickness=0, cursor="hand2")
            fallback.create_oval(3, 3, 35, 35, fill=colour, outline=palette["border"])
            swatch = fallback
        swatch.grid(row=1, column=0, rowspan=2, padx=(7, 10), pady=7)
        name = ttk.Label(self, text=display_text(paint.get("paint_name"), "Unknown paint"), style="MatchName.TLabel", cursor="hand2")
        name.grid(row=1, column=1, sticky="sw", pady=(6,0))
        meta = " • ".join(part for part in (str(paint.get("company") or paint.get("brand") or "").strip(), str(paint.get("product_line") or paint.get("paint_type") or "").strip()) if part)
        ttk.Label(self, text=meta, style="MatchMeta.TLabel").grid(row=2, column=1, sticky="nw", pady=(0,6))
        ttk.Label(self, text=f"{float(paint.get('match_percentage') or 0):.1f}%", style="MatchPercent.TLabel", width=7, anchor="e").grid(row=1, column=2, rowspan=2, padx=(8, 10))
        adjuster = InventoryAdjuster(self, label="Owned", value=int(paint.get("quantity") or 0), on_change=lambda value: on_owned(paint, value))
        adjuster.grid(row=1, column=3, rowspan=2, sticky="e", padx=(0,7))
        for widget in (swatch, name): widget.bind("<Button-1>", lambda _e: on_open(paint))


class PaintDocument(ScrollableFrame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        palette: Palette,
        on_open_paint: Callable[[dict[str, Any]], None],
        on_set_owned: Callable[[dict[str, Any], int], None],
        on_set_wishlist: Callable[[dict[str, Any], int], None],
    ) -> None:
        super().__init__(parent, palette=palette)
        self.palette = palette
        self.on_open_paint = on_open_paint
        self.on_set_owned = on_set_owned
        self.on_set_wishlist = on_set_wishlist
        self.icon_factory = PaintIconFactory(self, palette=palette) if PaintIconFactory is not None else None
        self._icon_refs: list[tk.PhotoImage] = []

    def _paint_icon(self, parent: tk.Misc, paint: dict[str, Any], size: int) -> tk.Misc:
        colour = normalize_hex(paint.get("hex") or paint.get("paint_hex"))
        if self.icon_factory is not None:
            image = self.icon_factory.get(colour, size=size, variant="pot")
            self._icon_refs.append(image)
            return ttk.Label(parent, image=image, style="Panel.TLabel")
        canvas = tk.Canvas(parent, width=size, height=size, bg=self.palette["panel"], highlightthickness=0)
        canvas.create_oval(2, 2, size - 2, size - 2, fill=colour, outline=self.palette["border"])
        return canvas

    def show_paint(self, paint: dict[str, Any], equivalents: list[dict[str, Any]], near_matches: list[dict[str, Any]]) -> None:
        self.clear()
        self._icon_refs.clear()
        body = ttk.Frame(self.content, style="Panel.TFrame", padding=8)
        body.pack(fill="both", expand=True)
        header = ttk.Frame(body, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 12))
        swatch = self._paint_icon(header, paint, 84)
        swatch.pack(side="left", padx=(0, 18))
        name_meta = ttk.Frame(header, style="Panel.TFrame")
        name_meta.pack(side="left", fill="x", expand=True, anchor="n")
        ttk.Label(name_meta, text=display_text(paint.get("paint_name"), "Paint"), style="DocumentTitle.TLabel").pack(anchor="w", pady=(8, 6))
        chips = ttk.Frame(name_meta, style="Panel.TFrame")
        chips.pack(anchor="w")
        for value in (paint.get("company") or paint.get("brand"), paint.get("product_line"), paint.get("paint_type")):
            if value:
                ttk.Label(chips, text=str(value), style="Chip.TLabel").pack(side="left", padx=(0, 7))

        inventory = ttk.Frame(body, style="Section.TFrame", padding=12)
        inventory.pack(fill="x", pady=(0, 10))
        ttk.Label(inventory, text="Inventory", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 10))
        controls = ttk.Frame(inventory, style="Section.TFrame")
        controls.pack(anchor="w")
        InventoryAdjuster(controls, label="Owned", value=int(paint.get("quantity") or 0), on_change=lambda value: self.on_set_owned(paint, value)).pack(side="left", padx=(0, 28))
        InventoryAdjuster(controls, label="Wishlist", value=int(paint.get("wishlist_quantity") or paint.get("wishlist") or 0), on_change=lambda value: self.on_set_wishlist(paint, value)).pack(side="left")

        matches = ttk.Frame(body, style="Section.TFrame", padding=12)
        matches.pack(fill="both", expand=True)
        ttk.Label(matches, text="Equivalent Paints (Exact Matches)", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 8))
        exact = [item for item in equivalents if float(item.get("match_percentage") or 100) >= 99.999]
        if exact:
            for item in exact:
                NearMatchRow(matches, paint=item, palette=self.palette, on_open=self.on_open_paint, on_owned=self.on_set_owned).pack(fill="x", pady=1)
        else:
            ttk.Label(matches, text="No exact equivalents or matches were found.", style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Separator(matches, style="Dark.TSeparator").pack(fill="x", pady=10)
        ttk.Label(matches, text="Near Matches", style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 6))
        filtered = [item for item in near_matches if float(item.get("match_percentage") or 0) < 99.999]
        if not filtered:
            ttk.Label(matches, text="No near matches were found.", style="Muted.TLabel").pack(anchor="w")
        for item in filtered:
            NearMatchRow(matches, paint=item, palette=self.palette, on_open=self.on_open_paint, on_owned=self.on_set_owned).pack(fill="x", pady=1)


class InventoryDocument(ttk.Frame):
    """Sortable inventory table with direct owned and wishlist editing."""
    def __init__(self, parent: tk.Misc, *, palette: Palette, on_open_paint: Callable[[dict[str, Any]], None], on_set_owned: Callable[[dict[str, Any], int], None], on_set_wishlist: Callable[[dict[str, Any], int], None]) -> None:
        super().__init__(parent, style="Panel.TFrame", padding=10)
        self.palette = palette
        self.on_open_paint = on_open_paint
        self.on_set_owned = on_set_owned
        self.on_set_wishlist = on_set_wishlist
        self.records: list[dict[str, Any]] = []
        self.sort_column = "company"
        self.reverse = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text="Inventory", style="DocumentTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0,10))
        cols=("name","company","line","type","owned","wishlist")
        self.tree=ttk.Treeview(self, columns=cols, show="headings", style="Paint.Treeview")
        labels={"name":"Paint Name","company":"Company","line":"Product Line","type":"Paint Type","owned":"Owned","wishlist":"Wishlist"}
        for c in cols:
            self.tree.heading(c, text=labels[c], command=lambda col=c:self._sort(col))
        self.tree.column("name", width=220, stretch=True)
        self.tree.column("company", width=150)
        self.tree.column("line", width=130)
        self.tree.column("type", width=100)
        self.tree.column("owned", width=70, anchor="center")
        self.tree.column("wishlist", width=75, anchor="center")
        bar=ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hbar=ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=bar.set, xscrollcommand=hbar.set)
        self.tree.grid(row=1,column=0,sticky="nsew")
        bar.grid(row=1,column=1,sticky="ns")
        hbar.grid(row=2,column=0,sticky="ew")
        self.tree.bind("<Double-1>", self._double_click)
        HoverWheel(self.tree, lambda units:self.tree.yview_scroll(units,"units"))

    def show_inventory(self, records: list[dict[str, Any]]) -> None:
        self.records=records
        self._render()

    def _sort(self, column: str) -> None:
        self.reverse = not self.reverse if self.sort_column == column else False
        self.sort_column=column
        self._render()

    def _value(self, p: dict[str, Any], column: str) -> Any:
        return {"name":p.get("paint_name"),"company":p.get("company") or p.get("brand"),"line":p.get("product_line"),"type":p.get("paint_type"),"owned":int(p.get("quantity") or 0),"wishlist":int(p.get("wishlist_quantity") or p.get("wishlist") or 0)}[column]

    def _render(self) -> None:
        self.tree.delete(*self.tree.get_children())
        ordered=sorted(self.records,key=lambda p:str(self._value(p,self.sort_column)).casefold(),reverse=self.reverse)
        self._ordered=ordered
        for i,p in enumerate(ordered):
            self.tree.insert("","end",iid=str(i),values=tuple(self._value(p,c) for c in ("name","company","line","type","owned","wishlist")))
        self._fit_columns()

    def _fit_columns(self) -> None:
        import tkinter.font as tkfont
        font = tkfont.nametofont("TkDefaultFont")
        labels = {"name":"Paint Name","company":"Company","line":"Product Line","type":"Paint Type","owned":"Owned","wishlist":"Wishlist"}
        for column in ("name","company","line","type","owned","wishlist"):
            values = [str(self._value(p,column) or "") for p in self.records[:1000]]
            width = max(font.measure(labels[column]) + 28, max([font.measure(v) for v in values] or [60]) + 24)
            self.tree.column(column, width=min(max(width, 70), 320))

    def _double_click(self, event: tk.Event) -> None:
        if self.tree.identify_region(event.x, event.y) == "heading":
            self._fit_columns()
            return
        selected=self.tree.selection()
        if selected:
            self.on_open_paint(self._ordered[int(selected[0])])


class WorkflowStepRow(ttk.Frame):
    def __init__(self, parent: tk.Misc, *, step: dict[str, Any], palette: Palette, on_open_paint: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(parent, style="WorkflowRow.TFrame", padding=(10, 8))
        self.columnconfigure(1, weight=1)
        colour = normalize_hex(step.get("paint_hex") or step.get("hex"))
        self.icon_factory = PaintIconFactory(self, palette=palette) if PaintIconFactory is not None else None
        self._icon_image: tk.PhotoImage | None = None
        if self.icon_factory is not None:
            self._icon_image = self.icon_factory.get(colour, size=38, variant="pot")
            swatch: tk.Misc = ttk.Label(self, image=self._icon_image, style="WorkflowRow.TLabel", cursor="hand2")
        else:
            fallback = tk.Canvas(self, width=38, height=38, bg=palette["card"], highlightthickness=0, cursor="hand2")
            fallback.create_oval(3, 3, 35, 35, fill=colour, outline=palette["border"])
            swatch = fallback
        swatch.grid(row=0, column=0, rowspan=3, padx=(0, 10), sticky="n")
        paint_name = display_text(step.get("paint_name"), "Unknown paint")
        label = ttk.Label(self, text=paint_name, style="WorkflowPaint.TLabel", cursor="hand2")
        label.grid(row=0, column=1, sticky="w")
        technique = display_text(step.get("technique"), "Painting step")
        optional = str(step.get("optional") or "").casefold() in {"1", "true", "yes", "y"}
        ttk.Label(self, text=technique + ("  •  Optional" if optional else ""), style="WorkflowTechnique.TLabel").grid(row=1, column=1, sticky="w", pady=(1, 0))
        description = "\n".join(part for part in (str(step.get("purpose") or "").strip(), str(step.get("notes") or "").strip()) if part)
        if description:
            ttk.Label(self, text=description, style="WorkflowDescription.TLabel", wraplength=760, justify="left").grid(row=2, column=1, sticky="ew", pady=(4, 0))
        payload = dict(step)
        for widget in (swatch, label):
            widget.bind("<Button-1>", lambda _e, data=payload: on_open_paint(data))


class CollapsibleWorkflowSection(ttk.Frame):
    def __init__(self, parent: tk.Misc, *, title: str, steps: list[dict[str, Any]], palette: Palette, on_open_paint: Callable[[dict[str, Any]], None], expanded: bool = True) -> None:
        super().__init__(parent, style="Section.TFrame")
        self.title = title
        self.expanded = expanded
        self.header = ttk.Button(self, style="WorkflowSection.TButton", command=self.toggle)
        self.header.pack(fill="x")
        self.body = ttk.Frame(self, style="Section.TFrame", padding=(8, 4, 8, 8))
        for step in steps:
            WorkflowStepRow(self.body, step=step, palette=palette, on_open_paint=on_open_paint).pack(fill="x", pady=1)
        self._apply()

    def toggle(self) -> None:
        self.expanded = not self.expanded
        self._apply()

    def set_expanded(self, expanded: bool) -> None:
        self.expanded = expanded
        self._apply()

    def _apply(self) -> None:
        self.header.configure(text=("▼  " if self.expanded else "▶  ") + self.title)
        if self.expanded:
            self.body.pack(fill="x")
        else:
            self.body.pack_forget()


class WorkflowDocument(ScrollableFrame):
    def __init__(self, parent: tk.Misc, *, palette: Palette, on_open_paint: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(parent, palette=palette)
        self.palette = palette
        self.on_open_paint = on_open_paint
        self.sections: list[CollapsibleWorkflowSection] = []

    def show_placeholder(self, text: str = "Choose a workflow from the toolbar to begin.") -> None:
        self.clear()
        ttk.Label(self.content, text=text, style="EmptyTitle.TLabel").pack(anchor="center", pady=(100, 8))
        ttk.Label(self.content, text="The center workspace is reserved for workflow steps, paint documents, images, and tutorials.", style="Muted.TLabel", wraplength=620, justify="center").pack(anchor="center")

    def show_workflow(self, title: str, steps: list[dict[str, Any]]) -> None:
        self.clear()
        self.sections.clear()
        top = ttk.Frame(self.content, style="Panel.TFrame", padding=(8, 8, 8, 12))
        top.pack(fill="x")
        ttk.Label(top, text=title, style="DocumentTitle.TLabel").pack(side="left")
        controls = ttk.Frame(top, style="Panel.TFrame")
        controls.pack(side="right")
        ttk.Button(controls, text="Expand All", style="Secondary.TButton", command=lambda: self._set_all(True)).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Collapse All", style="Secondary.TButton", command=lambda: self._set_all(False)).pack(side="left")
        grouped: dict[str, list[dict[str, Any]]] = {}
        for step in steps:
            area = str(step.get("model_area") or step.get("Model_Area") or "General").strip() or "General"
            grouped.setdefault(area, []).append(step)
        if not grouped:
            ttk.Label(self.content, text="No workflow steps were found.", style="Muted.TLabel").pack(anchor="w", padx=12, pady=12)
            return
        for title_text, area_steps in grouped.items():
            section = CollapsibleWorkflowSection(self.content, title=title_text, steps=area_steps, palette=self.palette, on_open_paint=self.on_open_paint)
            section.pack(fill="x", padx=8, pady=(0, 8))
            self.sections.append(section)

    def _set_all(self, expanded: bool) -> None:
        for section in self.sections:
            section.set_expanded(expanded)


class WorkspaceHost(ttk.Frame):
    """Hosts one active center document while preserving a consistent shell."""

    def __init__(self, parent: tk.Misc, *, palette: Palette) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.palette = palette
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.current: ttk.Frame | None = None

    def show(self, widget: ttk.Frame) -> None:
        try:
            widget_exists = bool(widget.winfo_exists())
        except tk.TclError:
            widget_exists = False
        if not widget_exists:
            raise tk.TclError("Cannot show a destroyed workspace document.")
        if self.current is widget:
            widget.grid(row=0, column=0, sticky="nsew")
            return
        if self.current is not None:
            try:
                if self.current.winfo_exists():
                    self.current.grid_remove()
            except tk.TclError:
                pass
        self.current = widget
        widget.grid(row=0, column=0, sticky="nsew")
