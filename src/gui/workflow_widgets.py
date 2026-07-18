"""Reusable Tkinter widgets for workflow presentation."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
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


class PaintPopup(tk.Toplevel):
    """Paint details dialog with inventory and equivalent-paint information."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        paint: dict[str, Any],
        equivalents: list[dict[str, Any]],
        palette: Palette,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        paint_name = str(paint.get("paint_name") or "Paint Information")
        self.title(paint_name)
        self.configure(background=palette["panel"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.minsize(560, 430)

        outer = ttk.Frame(self, padding=20, style="Panel.TFrame")
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)

        swatch_colour = normalize_hex(paint.get("hex") or paint.get("paint_hex"))
        swatch = tk.Canvas(
            outer,
            width=82,
            height=82,
            background=palette["panel"],
            highlightthickness=0,
        )
        swatch.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 18))
        swatch.create_rectangle(
            3,
            3,
            79,
            79,
            fill=swatch_colour,
            outline=palette["border"],
            width=2,
        )

        ttk.Label(outer, text=paint_name, style="PopupTitle.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        company_line = " · ".join(
            str(value).strip()
            for value in (
                paint.get("company"),
                paint.get("brand"),
                paint.get("product_line"),
            )
            if value and str(value).strip()
        )
        if company_line:
            ttk.Label(outer, text=company_line, style="PopupSubtle.TLabel").grid(
                row=1, column=1, sticky="nw", pady=(4, 0)
            )

        fields = [
            ("Paint ID", paint.get("paint_id")),
            ("Paint Type", paint.get("paint_type")),
            ("Status", paint.get("status")),
            ("Inventory", self._inventory_text(paint)),
            ("Wishlist", paint.get("wishlist")),
            ("Source", paint.get("source")),
            ("Notes", paint.get("notes")),
        ]

        row = 2
        for key, value in fields:
            if value is None or str(value).strip() == "":
                continue
            ttk.Label(outer, text=key, style="PopupKey.TLabel").grid(
                row=row, column=0, sticky="nw", pady=(10, 0)
            )
            ttk.Label(
                outer,
                text=str(value),
                style="PopupValue.TLabel",
                wraplength=360,
                justify="left",
            ).grid(row=row, column=1, sticky="nw", pady=(10, 0))
            row += 1

        ttk.Separator(outer, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=16
        )
        row += 1
        ttk.Label(
            outer,
            text="Equivalent and near-match paints",
            style="AreaTitle.TLabel",
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        if equivalents:
            for equivalent in equivalents[:15]:
                name = str(
                    equivalent.get("paint_name")
                    or equivalent.get("equivalent_paint_name")
                    or equivalent.get("name")
                    or "Unknown paint"
                ).strip()
                company = str(equivalent.get("company") or "").strip()
                relation = str(
                    equivalent.get("relation_type")
                    or equivalent.get("match_type")
                    or equivalent.get("equivalence_type")
                    or ""
                ).strip()
                line = " — ".join(part for part in (name, company, relation) if part)
                ttk.Label(
                    outer,
                    text=f"• {line}",
                    style="PopupValue.TLabel",
                    wraplength=490,
                    justify="left",
                ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(5, 0))
                row += 1
        else:
            ttk.Label(
                outer,
                text="No curated equivalents or near-color matches were found.",
                style="PopupSubtle.TLabel",
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
            row += 1

        ttk.Button(outer, text="Close", command=self.destroy).grid(
            row=row, column=1, sticky="e", pady=(20, 0)
        )
        self.bind("<Escape>", lambda _event: self.destroy())
        self.after_idle(self._center_on_parent)

    @staticmethod
    def _inventory_text(paint: dict[str, Any]) -> str | None:
        for key in ("quantity", "inventory_quantity", "owned_quantity", "inventory"):
            value = paint.get(key)
            if value is not None and str(value).strip() != "":
                return str(value)
        return None

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
        super().__init__(parent, padding=(10, 9), style="Card.TFrame")
        self.columnconfigure(1, weight=1)
        self._step = step
        self._popup_callback = popup_callback

        paint_name = str(step.get("paint_name") or "Unknown paint").strip()
        technique = str(step.get("technique") or "Painting step").strip()
        purpose = str(step.get("purpose") or "").strip()
        notes = str(step.get("notes") or "").strip()
        optional = str(step.get("optional") or "").strip().casefold() in {
            "1",
            "true",
            "yes",
            "y",
        }

        swatch = tk.Canvas(
            self,
            width=52,
            height=28,
            background=palette["card"],
            cursor="hand2",
            highlightthickness=0,
        )
        swatch.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 12))
        swatch.create_rectangle(
            1,
            1,
            51,
            27,
            fill=normalize_hex(step.get("paint_hex") or step.get("hex")),
            outline=palette["border"],
            width=1,
        )

        paint_label = ttk.Label(
            self,
            text=paint_name,
            style="PaintName.TLabel",
            cursor="hand2",
        )
        paint_label.grid(row=0, column=1, sticky="w")

        technique_text = technique + ("  ·  Optional" if optional else "")
        ttk.Label(self, text=technique_text, style="Technique.TLabel").grid(
            row=1, column=1, sticky="w", pady=(2, 0)
        )

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

        for widget in (swatch, paint_label):
            widget.bind("<Button-1>", self._open_popup)

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

        self.canvas = tk.Canvas(
            self,
            background=palette["panel"],
            highlightthickness=0,
            borderwidth=0,
        )
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
        ttk.Label(self.content, text=text, style="Placeholder.TLabel").pack(
            anchor="w", padx=8, pady=8
        )

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
