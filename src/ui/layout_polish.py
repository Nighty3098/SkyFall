"""Small, centralised visual polish applied to the loaded form.

Keeping this logic in one place lets every tab share the same hierarchy
(one primary action, consistent padding) without having to duplicate the
tweaks across the 3000-line form.ui file.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
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

# Unified spacing/margins
PAGE_MARGINS = (11, 11, 11, 11)
PAGE_SPACING = 6
INNER_MARGINS = (8, 8, 8, 8)
INNER_SPACING = 6

# Skip normalizing these special containers/wrappers
_SKIP_NORMALIZE_NAMES = {
    "settingsTabScrollContainer",
    "settingsTabScrollContents",
}


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
    _invalidate_widget(ui.graphTab)


def _normalize_layout(layout, *, is_page: bool = False):
    if layout is None:
        return
    if is_page:
        layout.setContentsMargins(*PAGE_MARGINS)
        layout.setSpacing(PAGE_SPACING)
    else:
        layout.setContentsMargins(*INNER_MARGINS)
        layout.setSpacing(INNER_SPACING)


def _should_skip_widget(widget: QWidget) -> bool:
    name = widget.objectName() or ""
    if name in _SKIP_NORMALIZE_NAMES:
        return True
    # Also skip if inside scroll wrapper containers
    parent = widget.parent()
    while parent is not None:
        pname = parent.objectName() or ""
        if pname in _SKIP_NORMALIZE_NAMES:
            return True
        parent = parent.parent()
    return False


def _harmonize_ui(ui):
    """Apply unified padding/spacing across all tabs and nested containers."""
    from PySide6.QtWidgets import QFrame, QStackedWidget

    stacked: QStackedWidget | None = getattr(ui, "mainStackedWidget", None)
    if stacked is not None:
        for i in range(stacked.count()):
            page = stacked.widget(i)
            if page is None:
                continue
            if _should_skip_widget(page):
                continue
            pl = page.layout()
            if pl is not None:
                _normalize_layout(pl, is_page=True)
            # Normalize inner containers
            for child in page.findChildren(QWidget):
                if _should_skip_widget(child):
                    continue
                if isinstance(child, QGroupBox) or isinstance(child, QFrame):
                    cl = child.layout()
                    if cl is not None:
                        _normalize_layout(cl)
                if isinstance(child, QSplitter):
                    for j in range(child.count()):
                        pane = child.widget(j)
                        if pane is not None and not _should_skip_widget(pane):
                            playout = pane.layout()
                            if playout is not None:
                                _normalize_layout(playout)
            # Also normalize any direct child layouts not caught
            for child in page.children():
                if isinstance(child, QWidget) and not _should_skip_widget(child):
                    cl = child.layout()
                    if cl is not None:
                        # treat as inner unless it's the page layout
                        pass


def _wrap_page_in_scroll_area(host, column_index=1):
    """Move the entire settings page (all columns) into a vertical scroll area."""
    outer = host.layout()
    if outer is None:
        return

    contents = QWidget()
    contents.setObjectName(f"{host.objectName()}ScrollContents")
    column_layout = QVBoxLayout(contents)
    column_layout.setContentsMargins(0, 0, 0, 0)

    while outer.count():
        moved = outer.takeAt(0)
        if moved.widget() is not None:
            column_layout.addWidget(moved.widget())
        elif moved.spacerItem() is not None:
            column_layout.addItem(moved.spacerItem())
        elif moved.layout() is not None:
            col = QVBoxLayout()
            col.setContentsMargins(0, 0, 0, 0)
            while moved.layout().count():
                im = moved.layout().takeAt(0)
                if im.widget():
                    col.addWidget(im.widget())
                elif im.spacerItem():
                    col.addItem(im.spacerItem())
                elif im.layout():
                    sub = QVBoxLayout()
                    while im.layout().count():
                        iim = im.layout().takeAt(0)
                        if iim.widget():
                            sub.addWidget(iim.widget())
                        elif iim.spacerItem():
                            sub.addItem(iim.spacerItem())
                    col.addLayout(sub)
            column_layout.addLayout(col)

    # Wrap contents in a width-limiting container (400px max)
    container = QWidget()
    container.setObjectName(f"{host.objectName()}ScrollContainer")
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(contents)
    container.setMaximumWidth(400)

    scroll = QScrollArea(host)
    scroll.setObjectName(f"{host.objectName()}ScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    scroll.setWidget(container)
    outer_wrap = QVBoxLayout(host)
    outer_wrap.setContentsMargins(0, 0, 0, 0)
    outer_wrap.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    outer_wrap.addWidget(scroll)
    _invalidate_widget(host)
    host.updateGeometry()


def polish_ui(parent):
    _tune_section_layouts(parent.ui)
    _mark_primary_buttons(parent.ui)
    _tune_responsive_widgets(parent.ui)
    _harmonize_ui(parent.ui)
    _wrap_page_in_scroll_area(parent.ui.settingsTab)
