from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QListWidgetItem, QSplitter, QWidget

from src.utils import get_current_ip
from src.ui.layout_polish import polish_ui

# Logical grouping of the tabs shown in the navigation sidebar.  Tabs are
# matched by their title so the grouping keeps working when new tabs are
# inserted into form.ui.
NAV_GROUPS = [
    ("Home", ["SKYFALL"]),
    ("Telegram", ["TELEGRAM DOWNLOADER", "TELEGRAM ANALYZER"]),
    (
        "Social",
        [
            "USERNAME",
            "MAIL",
            "REDDIT",
            "SOCIAL",
        ],
    ),
    (
        "Identity",
        [
            "SEARCH4FACES",
            "PHONE",
            "GEO",
            "LEAKS",
            "ARCHIVE",
        ],
    ),
    (
        "Web & Infrastructure",
        [
            "DORKING",
            "WEB",
            "GITHUB",
            "MAC ADDR",
            "WIFI",
            "OPEN CAMERAS",
        ],
    ),
    (
        "Blockchain",
        [
            "BLOCKCHAIN",
        ],
    ),
    (
        "File analyze",
        [
            "STEGANOGRAPHY",
            "FILE ANALYZE",
        ],
    ),
    ("Workspace", ["DOWNLOADER", "GRAPH", "AI REPORT"]),
    ("System", ["SETTINGS", "PROXY"]),
]


def setup_navbar(parent):
    tabs = parent.ui.mainStackedWidget
    nav = parent.ui.menuListWidget
    tabs.tabBar().hide()

    # Build title -> index map from the live tab widget.
    title_to_index = {tabs.tabText(i): i for i in range(tabs.count())}

    tab_to_row = {}
    row_to_tab = {}
    grouped = set()

    for group_title, titles in NAV_GROUPS:
        present = [title_to_index[t] for t in titles if t in title_to_index]
        if not present:
            continue

        header = QListWidgetItem(group_title.upper())
        header.setFlags(Qt.ItemFlag.NoItemFlags)
        header.setSizeHint(QSize(0, 28))
        nav.addItem(header)

        for idx in present:
            item = QListWidgetItem(tabs.tabText(idx))
            item.setData(Qt.ItemDataRole.UserRole, idx)
            nav.addItem(item)
            row = nav.count() - 1
            row_to_tab[row] = idx
            tab_to_row[idx] = row
            grouped.add(idx)

    # Any tab not listed above still gets a row so it can never disappear.
    leftover = [i for i in range(tabs.count()) if i not in grouped]
    if leftover:
        header = QListWidgetItem("OTHER")
        header.setFlags(Qt.ItemFlag.NoItemFlags)
        header.setSizeHint(QSize(0, 28))
        nav.addItem(header)
        for idx in leftover:
            item = QListWidgetItem(tabs.tabText(idx))
            item.setData(Qt.ItemDataRole.UserRole, idx)
            nav.addItem(item)
            row = nav.count() - 1
            row_to_tab[row] = idx
            tab_to_row[idx] = row

    def on_row_changed(row):
        idx = row_to_tab.get(row)
        if idx is not None and tabs.currentIndex() != idx:
            tabs.setCurrentIndex(idx)

    def on_tab_changed(idx):
        row = tab_to_row.get(idx)
        if row is not None and nav.currentRow() != row:
            nav.setCurrentRow(row)

    nav.currentRowChanged.connect(on_row_changed)
    tabs.currentChanged.connect(on_tab_changed)

    nav.setVisible(True)
    # Always open on the first tab (the SkyFall home screen) instead of
    # whatever tab happened to be selected in Qt Designer.
    tabs.setCurrentIndex(0)
    nav.setCurrentRow(tab_to_row.get(0, 0))


def setup_navigation_action(parent):
    action = parent.ui.actionToggleNavigation
    nav = parent.ui.menuListWidget
    action.setCheckable(True)
    action.setChecked(not nav.isHidden())
    action.toggled.connect(nav.setVisible)


def setup_view_menu(parent):
    tabs = parent.ui.mainStackedWidget
    menu = parent.ui.menuView
    menu.addSeparator()
    for i in range(tabs.count()):
        action = menu.addAction(tabs.tabText(i))
        action.triggered.connect(lambda checked, idx=i: tabs.setCurrentIndex(idx))


def setup_source_code_link(parent):
    label = getattr(parent.ui, "sourceCodeLinkLabel", None)
    if label is None:
        return
    label.setCursor(Qt.CursorShape.PointingHandCursor)
    label.installEventFilter(parent)


def normalize_splitters(parent, outer=12, gap=8, spacing=8):
    splitters = parent.findChildren(QSplitter)
    nested = {n for s in splitters for n in s.findChildren(QSplitter)}

    for s in splitters:
        s.setHandleWidth(gap)
        s.setChildrenCollapsible(False)
        for i in range(s.count()):
            lay = s.widget(i).layout()
            if lay:
                lay.setContentsMargins(0, 0, 0, 0)
                lay.setSpacing(spacing)
        if s not in nested:
            play = s.parentWidget().layout()
            if play:
                play.setContentsMargins(outer, outer, outer, outer)
                play.setSpacing(spacing)

def setup_home_tab(parent):
    label = getattr(parent.ui, "currentIpLabel", None)
    if label is None:
        return
    label.setText(f"Current IP: {get_current_ip()}")

def setup_ui(self):
    setup_navbar(self)
    setup_view_menu(self)
    setup_navigation_action(self)
    setup_source_code_link(self)
    polish_ui(self)
    normalize_splitters(self)
    setup_home_tab(self)
