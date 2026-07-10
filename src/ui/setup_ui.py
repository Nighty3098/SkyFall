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


def setup_ui(self):
    setup_navbar(self)
