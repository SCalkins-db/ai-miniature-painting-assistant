"""Reusable dynamic paint-pot icon renderer for the desktop GUI.

The factory loads a grayscale Citadel-style paint-pot template and luminance
mask, tints the paintable area from a paint HEX value, composites the result,
resizes it with high-quality downsampling, and caches both Pillow and Tk images.

For v2.1.8 the Citadel template is intentionally used for every manufacturer.
Additional company-specific templates can be added later without changing the
public ``PaintIconFactory.get`` API used by the GUI.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import re
import tkinter as tk
from typing import Final

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageTk


_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9A-Fa-f]{6}$")
_RESAMPLE: Final[int] = Image.Resampling.LANCZOS


class PaintIconFactory:
    """Render and cache dynamically colored paint-pot icons.

    Parameters
    ----------
    master:
        Any live Tk widget. It provides the Tcl interpreter required by
        ``ImageTk.PhotoImage``.
    palette:
        Optional GUI palette. Only ``background`` and ``border`` are used by
        the procedural fallback renderer.
    max_cache_entries:
        Maximum number of rendered Pillow images and Tk images retained in
        memory. Oldest entries are discarded first.
    """

    BASE_FILENAME: Final[str] = "base.png"
    MASK_FILENAME: Final[str] = "fill_mask.png"

    def __init__(
        self,
        master: tk.Misc,
        *,
        palette: dict[str, str] | None = None,
        max_cache_entries: int = 512,
    ) -> None:
        self.master = master
        self.palette = palette or {}
        self.max_cache_entries = max(32, int(max_cache_entries))

        self._base_master: Image.Image | None = None
        self._mask_master: Image.Image | None = None
        self._asset_signature: tuple[str, int, int] | None = None
        self._asset_paths: tuple[Path, Path] | None = None

        self._pil_cache: OrderedDict[tuple[str, int, str, tuple[str, int, int] | None], Image.Image] = OrderedDict()
        self._tk_cache: OrderedDict[tuple[str, int, str, tuple[str, int, int] | None], ImageTk.PhotoImage] = OrderedDict()

        self._load_assets()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, colour: str, *, size: int = 24, variant: str = "pot") -> ImageTk.PhotoImage:
        """Return a cached Tk image for ``colour`` and ``size``.

        ``variant`` is accepted now so callers remain stable when alternate
        icon styles are introduced later. Unknown variants currently use the
        same paint-pot template.
        """

        normalized = self._normalize_hex(colour)
        safe_size = max(12, min(int(size), 512))
        safe_variant = str(variant or "pot").strip().casefold() or "pot"
        key = (normalized, safe_size, safe_variant, self._asset_signature)

        cached = self._tk_cache.get(key)
        if cached is not None:
            self._tk_cache.move_to_end(key)
            return cached

        rendered = self._render_pillow(normalized, safe_size, safe_variant)
        photo = ImageTk.PhotoImage(rendered, master=self.master)
        self._tk_cache[key] = photo
        self._tk_cache.move_to_end(key)
        self._trim_cache(self._tk_cache)
        return photo

    def clear(self) -> None:
        """Clear rendered icon caches without unloading source assets."""

        self._pil_cache.clear()
        self._tk_cache.clear()

    def reload_assets(self) -> bool:
        """Reload template files and clear caches.

        Returns ``True`` when both production assets were found and loaded.
        """

        loaded = self._load_assets(force=True)
        self.clear()
        return loaded

    # ------------------------------------------------------------------
    # Asset discovery and loading
    # ------------------------------------------------------------------

    @classmethod
    def _candidate_roots(cls) -> list[Path]:
        module = Path(__file__).resolve()
        project_root = module.parent.parent.parent
        roots = [
            project_root / "assets" / "templates" / "citadel",
            Path.cwd() / "assets" / "templates" / "citadel",
            module.parent,
            module.parent / "assets",
            module.parent / "icons",
            module.parent / "assets" / "icons",
            module.parent.parent,
            module.parent.parent / "assets",
            module.parent.parent / "assets" / "icons",
            module.parent.parent.parent,
            module.parent.parent.parent / "assets",
            module.parent.parent.parent / "assets" / "icons",
            Path.cwd(),
            Path.cwd() / "assets",
            Path.cwd() / "assets" / "icons",
            Path.cwd() / "src" / "gui" / "assets",
            Path.cwd() / "src" / "gui" / "assets" / "icons",
        ]

        unique: list[Path] = []
        seen: set[Path] = set()
        for root in roots:
            resolved = root.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique.append(resolved)
        return unique

    @classmethod
    def _find_asset_pair(cls) -> tuple[Path, Path] | None:
        for root in cls._candidate_roots():
            base = root / cls.BASE_FILENAME
            mask = root / cls.MASK_FILENAME
            if base.is_file() and mask.is_file():
                return base, mask
        return None

    def _load_assets(self, *, force: bool = False) -> bool:
        pair = self._find_asset_pair()
        if pair is None:
            self._base_master = None
            self._mask_master = None
            self._asset_paths = None
            self._asset_signature = None
            return False

        base_path, mask_path = pair
        signature = (
            str(base_path),
            base_path.stat().st_mtime_ns,
            mask_path.stat().st_mtime_ns,
        )
        if not force and signature == self._asset_signature:
            return True

        try:
            with Image.open(base_path) as image:
                base = image.convert("RGBA")
            with Image.open(mask_path) as image:
                mask = image.convert("RGBA")
        except (OSError, ValueError):
            self._base_master = None
            self._mask_master = None
            self._asset_paths = None
            self._asset_signature = None
            return False

        if base.size != mask.size:
            mask = mask.resize(base.size, _RESAMPLE)

        # Keep both assets on their original shared canvas. Cropping them
        # independently would shift the mask relative to the artwork and cause
        # color spill around the bottle edges. Transparent padding is removed
        # only after the final composite is complete.
        self._base_master = base
        self._mask_master = mask
        self._asset_paths = pair
        self._asset_signature = signature
        return True

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_pillow(self, colour: str, size: int, variant: str) -> Image.Image:
        key = (colour, size, variant, self._asset_signature)
        cached = self._pil_cache.get(key)
        if cached is not None:
            self._pil_cache.move_to_end(key)
            return cached.copy()

        if self._base_master is None or self._mask_master is None:
            image = self._procedural_fallback(colour, size)
        else:
            image = self._render_from_assets(colour, size)

        self._pil_cache[key] = image.copy()
        self._pil_cache.move_to_end(key)
        self._trim_cache(self._pil_cache)
        return image

    def _render_from_assets(self, colour: str, size: int) -> Image.Image:
        assert self._base_master is not None
        assert self._mask_master is not None

        base = self._base_master.copy()
        mask = self._mask_master
        rgb = self._hex_to_rgb(colour)

        # The mask's luminance controls how strongly each pixel receives the
        # requested color. Its alpha preserves the silhouette and soft edges.
        mask_luma = ImageOps.grayscale(mask)
        mask_alpha = mask.getchannel("A")
        tint_alpha = ImageChops.multiply(mask_luma, mask_alpha)

        # Use the base luminance to retain highlights, shadows, and material
        # definition after tinting. Dark and light endpoints are derived from
        # the selected paint instead of hard-coded colors.
        base_luma = ImageOps.grayscale(base)
        shadow = tuple(max(0, int(channel * 0.28)) for channel in rgb)
        highlight = tuple(min(255, int(channel + (255 - channel) * 0.48)) for channel in rgb)
        tinted_rgb = ImageOps.colorize(base_luma, black=shadow, white=highlight).convert("RGBA")
        tinted_rgb.putalpha(tint_alpha)

        composited = Image.alpha_composite(base, tinted_rgb)

        # Reintroduce a restrained amount of the original grayscale highlights
        # so very dark colors still show the pot's contours at small sizes.
        highlight_mask = base_luma.point(lambda value: max(0, min(255, (value - 150) * 2)))
        highlight_mask = ImageChops.multiply(highlight_mask, base.getchannel("A"))
        highlight_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        highlight_layer.putalpha(highlight_mask.point(lambda value: int(value * 0.22)))
        composited = Image.alpha_composite(composited, highlight_layer)

        return self._fit_icon(composited, size)

    def _procedural_fallback(self, colour: str, size: int) -> Image.Image:
        """Render a compact pot when assets are missing instead of crashing."""

        scale = 4
        canvas_size = max(size * scale, 64)
        image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        rgb = self._hex_to_rgb(colour)
        outline = self._hex_to_rgb(self.palette.get("border", "#586473"))

        left = int(canvas_size * 0.20)
        right = int(canvas_size * 0.80)
        top = int(canvas_size * 0.10)
        bottom = int(canvas_size * 0.91)
        lid_bottom = int(canvas_size * 0.37)
        body_top = int(canvas_size * 0.33)
        radius = max(4, int(canvas_size * 0.09))
        width = max(2, canvas_size // 36)

        draw.rounded_rectangle((left, body_top, right, bottom), radius=radius, fill=rgb + (255,), outline=outline + (255,), width=width)
        draw.rounded_rectangle((left - width, top, right + width, lid_bottom), radius=radius, fill=(48, 53, 60, 255), outline=outline + (255,), width=width)
        draw.rectangle((left, int(canvas_size * 0.27), right, int(canvas_size * 0.34)), fill=(37, 42, 48, 255))
        draw.rounded_rectangle(
            (int(canvas_size * 0.29), int(canvas_size * 0.48), int(canvas_size * 0.71), int(canvas_size * 0.76)),
            radius=max(3, radius // 2),
            fill=(20, 23, 28, 225),
            outline=(205, 211, 218, 210),
            width=width,
        )
        draw.arc((left + width, top + width, right - width, int(canvas_size * 0.28)), 190, 350, fill=(220, 225, 232, 210), width=width)
        return image.resize((size, size), _RESAMPLE)

    @staticmethod
    def _fit_icon(image: Image.Image, size: int) -> Image.Image:
        """Fit the transparent artwork into a square without distortion."""

        alpha_bbox = image.getchannel("A").getbbox()
        if alpha_bbox is not None:
            image = image.crop(alpha_bbox)

        padding = max(1, round(size * 0.06))
        available = max(1, size - padding * 2)
        fitted = ImageOps.contain(image, (available, available), method=_RESAMPLE)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        x = (size - fitted.width) // 2
        y = (size - fitted.height) // 2
        canvas.alpha_composite(fitted, (x, y))
        return canvas

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_hex(value: str) -> str:
        text = str(value or "").strip().lstrip("#")
        if len(text) == 3:
            text = "".join(character * 2 for character in text)
        if not _HEX_RE.fullmatch(text):
            text = "777777"
        return f"#{text.upper()}"

    @staticmethod
    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        normalized = PaintIconFactory._normalize_hex(value).lstrip("#")
        return tuple(int(normalized[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]

    def _trim_cache(self, cache: OrderedDict) -> None:
        while len(cache) > self.max_cache_entries:
            cache.popitem(last=False)
