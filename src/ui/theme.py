"""Central theme system.

The whole application stylesheet is generated from a single template
(``resources/style.template.qss``) plus a semantic colour palette.  Both the
dark and the light theme therefore share the exact same structure and only
differ in colour tokens, which keeps them from drifting apart.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

from loguru import logger

RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "resources"
STYLE_TEMPLATE = RESOURCES_DIR / "style.template.qss"

# Common typography / geometry tokens shared by every palette.
BASE_TOKENS = {
    "font_size": "10pt",
    "font_size_small": "9pt",
    "font_size_drop": "50px",
    "font_size_win_title": "120px",
    "radius": "10px",
    "radius_sm": "5px",
}

DARK = {
    **BASE_TOKENS,
    "bg": "#0A0A0A",
    "graph_bg": "#0A0A0A",
    "surface": "#161616",
    "surface_hover": "#262626",
    "border": "#333333",
    "border_hover": "#888888",
    "border_focus": "#C1C1C1",
    "text": "#C1C1C1",
    "text_muted": "#888888",
    "text_disabled": "#555555",
    "accent": "#C1C1C1",
    "accent_hover": "#D6D6D6",
    "accent_pressed": "#A8A8A8",
    "on_accent": "#0A0A0A",
    "danger": "#E5484D",
    "danger_hover": "#F2555A",
    "on_danger": "#0A0A0A",
    "scrollbar": "#333333",
    "scrollbar_hover": "#888888",
    # Progress bars draw their percentage text over the filled chunk, so the
    # chunk has to stay mid-tone: light enough to be visible against the
    # track, dark enough for the (light) text to remain readable on top.
    "progress_chunk": "#4F4F4F",
}

LIGHT = {
    **BASE_TOKENS,
    "bg": "#F5F5F5",
    "graph_bg": "#F5F5F5",
    "surface": "#E8E8E8",
    "surface_hover": "#D0D0D0",
    "border": "#BDBDBD",
    "border_hover": "#888888",
    "border_focus": "#3A3A3A",
    "text": "#3A3A3A",
    "text_muted": "#6E6E6E",
    "text_disabled": "#9A9A9A",
    "accent": "#3A3A3A",
    "accent_hover": "#4E4E4E",
    "accent_pressed": "#2A2A2A",
    "on_accent": "#F5F5F5",
    "danger": "#C0392B",
    "danger_hover": "#D64534",
    "on_danger": "#FFFFFF",
    "scrollbar": "#BDBDBD",
    "scrollbar_hover": "#888888",
    "progress_chunk": "#A6A6A6",
}

PALETTES = {"dark": DARK, "light": LIGHT}


def get_palette(theme: str = "dark") -> dict[str, str]:
    """Return the colour palette for ``theme`` (falls back to dark)."""
    return PALETTES.get(theme, DARK)


def current_theme(app=None) -> str:
    """Detect which theme is currently applied to the application.

    Widgets that build their own stylesheet (dialogs, graphics items) can use
    this plus :func:`get_palette` instead of hard-coding colours, so they never
    drift away from ``style.template.qss``.
    """
    if app is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
    sheet = app.styleSheet() if app is not None else ""
    if not sheet:
        return "dark"
    return "dark" if DARK["bg"] in sheet else "light"


def dialog_palette(theme: str | None = None) -> dict[str, str]:
    """Palette values used by the hand-rolled dialogs in ``graph_lib``.

    Returns a flat dict of already-resolved colours so a stylesheet can be
    composed with a single ``.format(**palette)`` call instead of the hex
    literals that used to be duplicated across several modules.
    """
    pal = get_palette(theme) if theme else get_palette(current_theme())
    return {
        "bg": pal["bg"],
        "surface": pal["surface"],
        "surface_hover": pal["surface_hover"],
        "border": pal["border"],
        "border_hover": pal["border_hover"],
        "text": pal["text"],
        "text_muted": pal["text_muted"],
        "accent": pal["accent"],
        "on_accent": pal["on_accent"],
        "radius": pal["radius"],
    }


def build_stylesheet(theme: str = "dark", font_size: int = 10) -> str:
    """Render the QSS template for the requested theme."""
    template = Template(STYLE_TEMPLATE.read_text(encoding="utf-8"))
    size = f"{max(8, min(24, int(font_size)))}pt"
    palette = {
        **get_palette(theme),
        "font_size": size,
        "font_size_small": size,
        "font_size_drop": size,
        "font_size_win_title": "120px",
    }
    return template.safe_substitute(palette)


def current_font_size(app=None) -> int:
    if app is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
    if app is None:
        return 10
    try:
        return max(8, min(24, int(app.property("fontSizePt") or 10)))
    except (TypeError, ValueError):
        return 10


def apply_theme(theme: str = "dark", app=None, font_size: int = 10) -> None:
    """Apply ``theme`` to the running :class:`QApplication`."""
    if app is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
    if app is None:
        logger.warning("Cannot apply theme: no QApplication instance")
        return
    try:
        size = max(8, min(24, int(font_size)))
        app.setProperty("fontSizePt", size)
        app.setStyleSheet(build_stylesheet(theme, size))
    except FileNotFoundError:
        logger.warning(f"{STYLE_TEMPLATE} not found, using default theme")
