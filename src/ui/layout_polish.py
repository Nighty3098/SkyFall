"""Small, centralised visual polish applied to the loaded form.

Keeping this logic in one place lets every tab share the same hierarchy
(one primary action, consistent padding) without having to duplicate the
tweaks across the 3000-line form.ui file.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

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

# Widgets that live on a single, very wide toolbar row.  Their text-based
# minimum width used to decide the minimum size of the *whole* window
# (~1460px), which does not fit common laptop screens.  Letting them shrink
# means the row only elides once the window is genuinely too narrow.
SHRINKABLE_BUTTONS = (
    "exportGraphButton",
    "importGraphButton",
    "graphClearButton",
    "graphAutoLayoutButton",
    "exportGraphImageButton",
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
    """Shrink the few fixed-size widgets that dictate the window minimum."""
    for name in SHRINKABLE_BUTTONS:
        widget = getattr(ui, name, None)
        if widget is not None:
            widget.setMinimumWidth(1)
    for name, width in COMPACT_MIN_WIDTHS.items():
        widget = getattr(ui, name, None)
        if widget is not None:
            widget.setMinimumWidth(width)
    # The size hints above are cached by the (sub)layouts that own the widgets
    # and are only recomputed after the pending LayoutRequest is delivered.
    # Drop those caches now so the window's minimum size is correct on the
    # very first show.
    _invalidate_widget(ui.graphTab)


def _wrap_page_in_scroll_area(host, column_index=1):
    """Move a page's single tall column of fields into a vertical scroll area.

    Without this the SETTINGS page (two dozen stacked fields) reports a
    ~1110px minimum height, which forces the whole main window to be taller
    than most screens.  Inside a scroll area the page collapses to a normal
    minimum and simply scrolls when the window is short.
    """
    outer = host.layout()
    if outer is None:
        return

    moved = outer.takeAt(column_index)
    column = moved.layout() if moved is not None else None
    if column is None:
        if moved is not None:
            outer.insertItem(column_index, moved)
        return

    scroll = QScrollArea(host)
    scroll.setObjectName(f"{host.objectName()}ScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    contents = QWidget()
    contents.setObjectName(f"{host.objectName()}ScrollContents")
    column_layout = QVBoxLayout(contents)
    column_layout.setContentsMargins(0, 0, 0, 0)
    while column.count():
        item = column.takeAt(0)
        if item.widget() is not None:
            column_layout.addWidget(item.widget())
        elif item.spacerItem() is not None:
            column_layout.addItem(item.spacerItem())
    column.deleteLater()

    scroll.setWidget(contents)
    outer.insertWidget(column_index, scroll)
    _invalidate_widget(host)
    host.updateGeometry()


def polish_ui(parent):
    _tune_section_layouts(parent.ui)
    _mark_primary_buttons(parent.ui)
    _tune_responsive_widgets(parent.ui)
    _wrap_page_in_scroll_area(parent.ui.settingsTab)
