from PySide6.QtCore import QSize
from PySide6.QtWidgets import QProxyStyle, QStyle, QStyleOptionTab, QTabBar


class HorizontalTabStyle(QProxyStyle):
    def draw_control(self, element, option, painter, widget=None):
        if element == QStyle.CE_TabBarTabLabel:
            if isinstance(option, QStyleOptionTab):
                option.shape = QTabBar.Shape.RoundedNorth
        super().draw_control(element, option, painter, widget)

    def size_from_contents(self, size_type, option, size, widget=None):
        size = super().size_from_contents(size_type, option, size, widget)
        if size_type == QStyle.CT_TabBarTab:
            if isinstance(option, QStyleOptionTab):
                return QSize(size.height(), size.width())
        return size
