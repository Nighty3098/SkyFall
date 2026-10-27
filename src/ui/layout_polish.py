"""Small, centralised visual polish applied to the loaded form.

Keeping this logic in one place lets every tab share the same hierarchy
(one primary action, consistent padding) without having to duplicate the
tweaks across the 3000-line form.ui file.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
)

# Left-hand settings pane of a tab; only used to normalise its padding.
SETTINGS_SECTIONS = (
    "downloaderSettingsSection",
    "analyzerSettingsSection",
    "mailSettingsSection",
    "socialSettingsSection",
    "leaksSettingsSection",
    "geoSettingsSection",
    "archiveSettingsSection",
    "githubSettingsSection",
    "phoneSettingsSection",
    "bcSettingsSection",
)

# The main call-to-action of every tab gets the accent style.
PRIMARY_BUTTONS = (
    "telegramDownloadStart",
    "runTelegramAnalyzerBtn",
    "searchUsernameButton",
    "startMailSearchButton",
    "socialSearchButton",
    "leakSearchAllButton",
    "geoFullReportButton",
    "archiveCheckButton",
    "dorkItButton",
    "runUrlScanButton",
    "getMetadataButton",
    "githubUserSearchBtn",
    "phoneLookupBtn",
    "checkMacAddrButton",
    "bcSearchButton",
    "runS4FButton",
    "downloadFromLinkButton",
    "generateReportButton",
    "pushButton",
    "saveProxiesButton",
)

# Fixed minimum widths that are larger than they need to be.
COMPACT_MIN_WIDTHS = {
    "graphLayoutCombo": 110,
    "graphFilterCombo": 110,
    "graphClearFilterButton": 90,
    "entityPalette": 160,
    "nodeContentEdit": 180,
}

SETTINGS_MARGINS = (12, 12, 12, 12)
SETTINGS_SPACING = 8


def _repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _tune_section_layouts(ui):
    for name in SETTINGS_SECTIONS:
        section = getattr(ui, name, None)
        if section is None:
            continue
        layout = section.layout()
        if layout is None:
            continue
        layout.setContentsMargins(*SETTINGS_MARGINS)
        layout.setSpacing(SETTINGS_SPACING)


def _mark_primary_buttons(ui):
    for name in PRIMARY_BUTTONS:
        button = getattr(ui, name, None)
        if button is None:
            continue
        button.setProperty("accent", True)
        _repolish(button)


def _invalidate_layout(layout):
    layout.invalidate()
    for i in range(layout.count()):
        item = layout.itemAt(i)
        sub = item.layout()
        if sub is not None:
            _invalidate_layout(sub)
        elif item.widget() is not None:
            _invalidate_widget(item.widget())


def _invalidate_widget(widget, seen=None):
    if seen is None:
        seen = set()
    if id(widget) in seen:
        return
    seen.add(id(widget))
    layout = widget.layout()
    if layout is not None:
        _invalidate_layout(layout)
    for child in widget.children():
        if isinstance(child, QWidget):
            _invalidate_widget(child, seen)


def _tune_responsive_widgets(ui):
    """Set compact minimum widths and refresh the graph layout."""
    for name, width in COMPACT_MIN_WIDTHS.items():
        widget = getattr(ui, name, None)
        if widget is not None:
            widget.setMinimumWidth(width)
        _invalidate_widget(ui.graphTab)


def polish_ui(parent):
    _tune_section_layouts(parent.ui)
    _mark_primary_buttons(parent.ui)
    _tune_responsive_widgets(parent.ui)
