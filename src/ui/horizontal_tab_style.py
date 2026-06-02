from PySide6.QtWidgets import QProxyStyle, QStyle, QStyleOptionTab
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QTabBar

class HorizontalTabStyle(QProxyStyle):
    def drawControl(self, element, option, painter, widget=None):
        if element == QStyle.CE_TabBarTabLabel:
            if isinstance(option, QStyleOptionTab):
                option.shape = QTabBar.Shape.RoundedNorth
        super().drawControl(element, option, painter, widget)

    def sizeFromContents(self, sizeType, option, size, widget=None):
        size = super().sizeFromContents(sizeType, option, size, widget)
        if sizeType == QStyle.CT_TabBarTab:
            if isinstance(option, QStyleOptionTab):
                return QSize(size.height(), size.width())
        return size
