def setup_navbar(parent):
    parent.ui.mainStackedWidget.tabBar().hide()
    parent.ui.menuListWidget.currentRowChanged.connect(
        parent.ui.mainStackedWidget.setCurrentIndex
    )
    parent.ui.mainStackedWidget.currentChanged.connect(
        lambda idx: parent.ui.menuListWidget.setCurrentRow(idx)
    )
    tab_count = parent.ui.mainStackedWidget.count()
    tabs = [parent.ui.mainStackedWidget.tabText(i) for i in range(tab_count)]
    parent.ui.menuListWidget.addItems(tabs)
    parent.ui.menuListWidget.setCurrentRow(0)

    parent.ui.menuListWidget.setVisible(False)


def setup_view_menu(parent):
    tabs = parent.ui.mainStackedWidget
    menu = parent.ui.menuView
    menu.addSeparator()
    for i in range(tabs.count()):
        action = menu.addAction(tabs.tabText(i))
        action.triggered.connect(lambda checked, idx=i: tabs.setCurrentIndex(idx))


def setup_ui(self):
    setup_navbar(self)
    setup_view_menu(self)
