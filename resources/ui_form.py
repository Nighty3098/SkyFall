# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
    QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMenuBar, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QSpinBox, QSplitter, QTabWidget,
    QVBoxLayout, QWidget)

from src.libs.graph_lib import GraphWidget
from src.libs.graph_panel import EntityPalette
from src.ui.drop_widget import DropWidget

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1244, 795)
        self.actionNew_case = QAction(MainWindow)
        self.actionNew_case.setObjectName(u"actionNew_case")
        self.actionOpen_case = QAction(MainWindow)
        self.actionOpen_case.setObjectName(u"actionOpen_case")
        self.actionExit = QAction(MainWindow)
        self.actionExit.setObjectName(u"actionExit")
        self.actionAbout = QAction(MainWindow)
        self.actionAbout.setObjectName(u"actionAbout")
        self.actionOpenGitHub = QAction(MainWindow)
        self.actionOpenGitHub.setObjectName(u"actionOpenGitHub")
        self.actionToggleNavigation = QAction(MainWindow)
        self.actionToggleNavigation.setObjectName(u"actionToggleNavigation")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_10 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_10.setSpacing(0)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(-1, 0, -1, -1)
        self.menuListWidget = QListWidget(self.centralwidget)
        self.menuListWidget.setObjectName(u"menuListWidget")
        self.menuListWidget.setMinimumSize(QSize(150, 0))
        self.menuListWidget.setMaximumSize(QSize(150, 16777215))
        self.menuListWidget.setStyleSheet(u"padding: 4px;")

        self.horizontalLayout_6.addWidget(self.menuListWidget)

        self.mainStackedWidget = QTabWidget(self.centralwidget)
        self.mainStackedWidget.setObjectName(u"mainStackedWidget")
        self.mainStackedWidget.setTabPosition(QTabWidget.TabPosition.North)
        self.mainStackedWidget.setTabBarAutoHide(True)
        self.mainTab = QWidget()
        self.mainTab.setObjectName(u"mainTab")
        self.horizontalLayout_7 = QHBoxLayout(self.mainTab)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.verticalLayout_21 = QVBoxLayout()
        self.verticalLayout_21.setObjectName(u"verticalLayout_21")
        self.verticalLayout_21.setContentsMargins(-1, -1, -1, 0)
        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_21.addItem(self.verticalSpacer_5)

        self.winTitle = QLabel(self.mainTab)
        self.winTitle.setObjectName(u"winTitle")
        font = QFont()
        font.setBold(True)
        font.setItalic(False)
        self.winTitle.setFont(font)
        self.winTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_21.addWidget(self.winTitle)

        self.mainTabSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_21.addItem(self.mainTabSpacer)


        self.horizontalLayout_7.addLayout(self.verticalLayout_21)

        self.mainStackedWidget.addTab(self.mainTab, "")
        self.telegramDownloaderTab = QWidget()
        self.telegramDownloaderTab.setObjectName(u"telegramDownloaderTab")
        self.horizontalLayout_3 = QHBoxLayout(self.telegramDownloaderTab)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.downloaderSplitter = QSplitter(self.telegramDownloaderTab)
        self.downloaderSplitter.setObjectName(u"downloaderSplitter")
        self.downloaderSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.downloaderSettingsSection = QWidget(self.downloaderSplitter)
        self.downloaderSettingsSection.setObjectName(u"downloaderSettingsSection")
        self.verticalLayout_5 = QVBoxLayout(self.downloaderSettingsSection)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.telegramUsernameEdit = QLineEdit(self.downloaderSettingsSection)
        self.telegramUsernameEdit.setObjectName(u"telegramUsernameEdit")

        self.verticalLayout_5.addWidget(self.telegramUsernameEdit)

        self.telegramAccountInfo = QLineEdit(self.downloaderSettingsSection)
        self.telegramAccountInfo.setObjectName(u"telegramAccountInfo")
        self.telegramAccountInfo.setReadOnly(True)

        self.verticalLayout_5.addWidget(self.telegramAccountInfo)

        self.telegramUseProxyCheck = QCheckBox(self.downloaderSettingsSection)
        self.telegramUseProxyCheck.setObjectName(u"telegramUseProxyCheck")

        self.verticalLayout_5.addWidget(self.telegramUseProxyCheck)

        self.groupBox_2 = QGroupBox(self.downloaderSettingsSection)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_8 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_3 = QLabel(self.groupBox_2)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.label_4 = QLabel(self.groupBox_2)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)

        self.label_2 = QLabel(self.groupBox_2)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(self.groupBox_2)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.telegramBaseDelay = QDoubleSpinBox(self.groupBox_2)
        self.telegramBaseDelay.setObjectName(u"telegramBaseDelay")

        self.gridLayout.addWidget(self.telegramBaseDelay, 0, 1, 1, 1)

        self.telegramMaxReq = QSpinBox(self.groupBox_2)
        self.telegramMaxReq.setObjectName(u"telegramMaxReq")

        self.gridLayout.addWidget(self.telegramMaxReq, 1, 1, 1, 1)

        self.telegrammembersDelay = QDoubleSpinBox(self.groupBox_2)
        self.telegrammembersDelay.setObjectName(u"telegrammembersDelay")

        self.gridLayout.addWidget(self.telegrammembersDelay, 2, 1, 1, 1)

        self.telegramPause = QDoubleSpinBox(self.groupBox_2)
        self.telegramPause.setObjectName(u"telegramPause")

        self.gridLayout.addWidget(self.telegramPause, 3, 1, 1, 1)


        self.verticalLayout_8.addLayout(self.gridLayout)


        self.verticalLayout_5.addWidget(self.groupBox_2)

        self.groupBox = QGroupBox(self.downloaderSettingsSection)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_7 = QVBoxLayout(self.groupBox)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.telegramDownloadMediaCheck = QCheckBox(self.groupBox)
        self.telegramDownloadMediaCheck.setObjectName(u"telegramDownloadMediaCheck")

        self.verticalLayout_7.addWidget(self.telegramDownloadMediaCheck)

        self.telegramCollectMembersCheck = QCheckBox(self.groupBox)
        self.telegramCollectMembersCheck.setObjectName(u"telegramCollectMembersCheck")

        self.verticalLayout_7.addWidget(self.telegramCollectMembersCheck)

        self.telegramCollectLinksCheck = QCheckBox(self.groupBox)
        self.telegramCollectLinksCheck.setObjectName(u"telegramCollectLinksCheck")

        self.verticalLayout_7.addWidget(self.telegramCollectLinksCheck)

        self.telegramMultiAccCheck = QCheckBox(self.groupBox)
        self.telegramMultiAccCheck.setObjectName(u"telegramMultiAccCheck")

        self.verticalLayout_7.addWidget(self.telegramMultiAccCheck)


        self.verticalLayout_5.addWidget(self.groupBox)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_3)

        self.telegramDownloadStart = QPushButton(self.downloaderSettingsSection)
        self.telegramDownloadStart.setObjectName(u"telegramDownloadStart")

        self.verticalLayout_5.addWidget(self.telegramDownloadStart)

        self.telegramDownloadProgress = QProgressBar(self.downloaderSettingsSection)
        self.telegramDownloadProgress.setObjectName(u"telegramDownloadProgress")
        self.telegramDownloadProgress.setValue(0)

        self.verticalLayout_5.addWidget(self.telegramDownloadProgress)

        self.telegramDownloadAvatarsBtn = QPushButton(self.downloaderSettingsSection)
        self.telegramDownloadAvatarsBtn.setObjectName(u"telegramDownloadAvatarsBtn")

        self.verticalLayout_5.addWidget(self.telegramDownloadAvatarsBtn)

        self.downloaderSplitter.addWidget(self.downloaderSettingsSection)
        self.downloaderDebugSection = QWidget(self.downloaderSplitter)
        self.downloaderDebugSection.setObjectName(u"downloaderDebugSection")
        self.verticalLayout_6 = QVBoxLayout(self.downloaderDebugSection)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.telegramDownloaderDebug = QPlainTextEdit(self.downloaderDebugSection)
        self.telegramDownloaderDebug.setObjectName(u"telegramDownloaderDebug")
        self.telegramDownloaderDebug.setReadOnly(True)

        self.verticalLayout_6.addWidget(self.telegramDownloaderDebug)

        self.downloaderSplitter.addWidget(self.downloaderDebugSection)

        self.horizontalLayout_3.addWidget(self.downloaderSplitter)

        self.mainStackedWidget.addTab(self.telegramDownloaderTab, "")
        self.telegramAnalyzerTab = QWidget()
        self.telegramAnalyzerTab.setObjectName(u"telegramAnalyzerTab")
        self.verticalLayout_9 = QVBoxLayout(self.telegramAnalyzerTab)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.analyzerSplitter = QSplitter(self.telegramAnalyzerTab)
        self.analyzerSplitter.setObjectName(u"analyzerSplitter")
        self.analyzerSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.analyzerSettingsSection = QWidget(self.analyzerSplitter)
        self.analyzerSettingsSection.setObjectName(u"analyzerSettingsSection")
        self.verticalLayout_17 = QVBoxLayout(self.analyzerSettingsSection)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.telegramAnalyzerLoadChannelsButton = QPushButton(self.analyzerSettingsSection)
        self.telegramAnalyzerLoadChannelsButton.setObjectName(u"telegramAnalyzerLoadChannelsButton")

        self.verticalLayout_17.addWidget(self.telegramAnalyzerLoadChannelsButton)

        self.telegramChannelsList = QListWidget(self.analyzerSettingsSection)
        QListWidgetItem(self.telegramChannelsList)
        self.telegramChannelsList.setObjectName(u"telegramChannelsList")

        self.verticalLayout_17.addWidget(self.telegramChannelsList)

        self.groupBox_3 = QGroupBox(self.analyzerSettingsSection)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_10 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.label_5 = QLabel(self.groupBox_3)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_3.addWidget(self.label_5, 0, 0, 1, 1)

        self.includeLinksCheck = QCheckBox(self.groupBox_3)
        self.includeLinksCheck.setObjectName(u"includeLinksCheck")

        self.gridLayout_3.addWidget(self.includeLinksCheck, 5, 0, 1, 1)

        self.label_7 = QLabel(self.groupBox_3)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_3.addWidget(self.label_7, 4, 0, 1, 1)

        self.telegramAnalyzerEndDate = QDateTimeEdit(self.groupBox_3)
        self.telegramAnalyzerEndDate.setObjectName(u"telegramAnalyzerEndDate")

        self.gridLayout_3.addWidget(self.telegramAnalyzerEndDate, 4, 1, 1, 1)

        self.label_6 = QLabel(self.groupBox_3)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_3.addWidget(self.label_6, 3, 0, 1, 1)

        self.telegramAnalyzerMinReplies = QSpinBox(self.groupBox_3)
        self.telegramAnalyzerMinReplies.setObjectName(u"telegramAnalyzerMinReplies")

        self.gridLayout_3.addWidget(self.telegramAnalyzerMinReplies, 0, 1, 1, 1)

        self.telegramAnalyzerStartDate = QDateTimeEdit(self.groupBox_3)
        self.telegramAnalyzerStartDate.setObjectName(u"telegramAnalyzerStartDate")

        self.gridLayout_3.addWidget(self.telegramAnalyzerStartDate, 3, 1, 1, 1)

        self.includeForwardingCheck = QCheckBox(self.groupBox_3)
        self.includeForwardingCheck.setObjectName(u"includeForwardingCheck")
        self.includeForwardingCheck.setChecked(True)

        self.gridLayout_3.addWidget(self.includeForwardingCheck, 6, 0, 1, 1)


        self.verticalLayout_10.addLayout(self.gridLayout_3)


        self.verticalLayout_17.addWidget(self.groupBox_3)

        self.groupBox_4 = QGroupBox(self.analyzerSettingsSection)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.verticalLayout_11 = QVBoxLayout(self.groupBox_4)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.gridLayout_4 = QGridLayout()
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(-1, -1, -1, 0)
        self.telegramAnalyzerHTMLCheck = QCheckBox(self.groupBox_4)
        self.telegramAnalyzerHTMLCheck.setObjectName(u"telegramAnalyzerHTMLCheck")

        self.gridLayout_4.addWidget(self.telegramAnalyzerHTMLCheck, 1, 1, 1, 1)

        self.telegramAnalyzerCSVCheck = QCheckBox(self.groupBox_4)
        self.telegramAnalyzerCSVCheck.setObjectName(u"telegramAnalyzerCSVCheck")

        self.gridLayout_4.addWidget(self.telegramAnalyzerCSVCheck, 0, 1, 1, 1)

        self.telegramAnalyzerObsidianCheck = QCheckBox(self.groupBox_4)
        self.telegramAnalyzerObsidianCheck.setObjectName(u"telegramAnalyzerObsidianCheck")

        self.gridLayout_4.addWidget(self.telegramAnalyzerObsidianCheck, 2, 1, 1, 1)

        self.telegramAnalyzerPNGCheck = QCheckBox(self.groupBox_4)
        self.telegramAnalyzerPNGCheck.setObjectName(u"telegramAnalyzerPNGCheck")

        self.gridLayout_4.addWidget(self.telegramAnalyzerPNGCheck, 2, 0, 1, 1)

        self.telegramAnalyzerGraphMLCheck = QCheckBox(self.groupBox_4)
        self.telegramAnalyzerGraphMLCheck.setObjectName(u"telegramAnalyzerGraphMLCheck")

        self.gridLayout_4.addWidget(self.telegramAnalyzerGraphMLCheck, 0, 0, 1, 1)

        self.telegramAnalyzerJSONCheck = QCheckBox(self.groupBox_4)
        self.telegramAnalyzerJSONCheck.setObjectName(u"telegramAnalyzerJSONCheck")

        self.gridLayout_4.addWidget(self.telegramAnalyzerJSONCheck, 1, 0, 1, 1)

        self.checkBox_7 = QCheckBox(self.groupBox_4)
        self.checkBox_7.setObjectName(u"checkBox_7")

        self.gridLayout_4.addWidget(self.checkBox_7, 3, 0, 1, 1)

        self.checkBox_8 = QCheckBox(self.groupBox_4)
        self.checkBox_8.setObjectName(u"checkBox_8")

        self.gridLayout_4.addWidget(self.checkBox_8, 3, 1, 1, 1)


        self.verticalLayout_11.addLayout(self.gridLayout_4)


        self.verticalLayout_17.addWidget(self.groupBox_4)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_17.addItem(self.verticalSpacer_4)

        self.runTelegramAnalyzerBtn = QPushButton(self.analyzerSettingsSection)
        self.runTelegramAnalyzerBtn.setObjectName(u"runTelegramAnalyzerBtn")

        self.verticalLayout_17.addWidget(self.runTelegramAnalyzerBtn)

        self.telegramAnalyzerProgress = QProgressBar(self.analyzerSettingsSection)
        self.telegramAnalyzerProgress.setObjectName(u"telegramAnalyzerProgress")
        self.telegramAnalyzerProgress.setValue(24)

        self.verticalLayout_17.addWidget(self.telegramAnalyzerProgress)

        self.analyzerSplitter.addWidget(self.analyzerSettingsSection)
        self.analyzerDebugSection = QWidget(self.analyzerSplitter)
        self.analyzerDebugSection.setObjectName(u"analyzerDebugSection")
        self.verticalLayout_18 = QVBoxLayout(self.analyzerDebugSection)
        self.verticalLayout_18.setObjectName(u"verticalLayout_18")
        self.verticalLayout_18.setContentsMargins(0, 0, 0, 0)
        self.telegramAnalyzerDebug = QPlainTextEdit(self.analyzerDebugSection)
        self.telegramAnalyzerDebug.setObjectName(u"telegramAnalyzerDebug")
        self.telegramAnalyzerDebug.setReadOnly(True)

        self.verticalLayout_18.addWidget(self.telegramAnalyzerDebug)

        self.analyzerSplitter.addWidget(self.analyzerDebugSection)

        self.verticalLayout_9.addWidget(self.analyzerSplitter)

        self.mainStackedWidget.addTab(self.telegramAnalyzerTab, "")
        self.usernameSearchTab = QWidget()
        self.usernameSearchTab.setObjectName(u"usernameSearchTab")
        self.gridLayout_8 = QGridLayout(self.usernameSearchTab)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.usernameScriptDebug = QPlainTextEdit(self.usernameSearchTab)
        self.usernameScriptDebug.setObjectName(u"usernameScriptDebug")

        self.gridLayout_8.addWidget(self.usernameScriptDebug, 2, 0, 1, 1)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(-1, -1, -1, 0)
        self.usernameEdit = QLineEdit(self.usernameSearchTab)
        self.usernameEdit.setObjectName(u"usernameEdit")

        self.horizontalLayout_8.addWidget(self.usernameEdit)

        self.searchUsernameButton = QPushButton(self.usernameSearchTab)
        self.searchUsernameButton.setObjectName(u"searchUsernameButton")
        self.searchUsernameButton.setMinimumSize(QSize(200, 0))

        self.horizontalLayout_8.addWidget(self.searchUsernameButton)


        self.gridLayout_8.addLayout(self.horizontalLayout_8, 0, 0, 1, 2)

        self.usernameSearchProgress = QProgressBar(self.usernameSearchTab)
        self.usernameSearchProgress.setObjectName(u"usernameSearchProgress")
        self.usernameSearchProgress.setValue(0)

        self.gridLayout_8.addWidget(self.usernameSearchProgress, 3, 0, 1, 2)

        self.maigretDebug = QPlainTextEdit(self.usernameSearchTab)
        self.maigretDebug.setObjectName(u"maigretDebug")

        self.gridLayout_8.addWidget(self.maigretDebug, 2, 1, 1, 1)

        self.mainStackedWidget.addTab(self.usernameSearchTab, "")
        self.mailToolsTab = QWidget()
        self.mailToolsTab.setObjectName(u"mailToolsTab")
        self.horizontalLayout_4 = QHBoxLayout(self.mailToolsTab)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.mailSplitter = QSplitter(self.mailToolsTab)
        self.mailSplitter.setObjectName(u"mailSplitter")
        self.mailSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.mailSettingsSection = QWidget(self.mailSplitter)
        self.mailSettingsSection.setObjectName(u"mailSettingsSection")
        self.verticalLayout_19 = QVBoxLayout(self.mailSettingsSection)
        self.verticalLayout_19.setObjectName(u"verticalLayout_19")
        self.verticalLayout_19.setContentsMargins(0, 0, 0, 0)
        self.mailEdit = QLineEdit(self.mailSettingsSection)
        self.mailEdit.setObjectName(u"mailEdit")

        self.verticalLayout_19.addWidget(self.mailEdit)

        self.startMailSearchButton = QPushButton(self.mailSettingsSection)
        self.startMailSearchButton.setObjectName(u"startMailSearchButton")

        self.verticalLayout_19.addWidget(self.startMailSearchButton)

        self.startHibpCheckButton = QPushButton(self.mailSettingsSection)
        self.startHibpCheckButton.setObjectName(u"startHibpCheckButton")

        self.verticalLayout_19.addWidget(self.startHibpCheckButton)

        self.verticalSpacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_19.addItem(self.verticalSpacer_6)

        self.mailSplitter.addWidget(self.mailSettingsSection)
        self.mailDebugSection = QWidget(self.mailSplitter)
        self.mailDebugSection.setObjectName(u"mailDebugSection")
        self.verticalLayout_20 = QVBoxLayout(self.mailDebugSection)
        self.verticalLayout_20.setObjectName(u"verticalLayout_20")
        self.verticalLayout_20.setContentsMargins(0, 0, 0, 0)
        self.mailDebugSplitter = QSplitter(self.mailDebugSection)
        self.mailDebugSplitter.setObjectName(u"mailDebugSplitter")
        self.mailDebugSplitter.setOrientation(Qt.Orientation.Vertical)
        self.mailSearchDebug = QPlainTextEdit(self.mailDebugSplitter)
        self.mailSearchDebug.setObjectName(u"mailSearchDebug")
        self.mailDebugSplitter.addWidget(self.mailSearchDebug)
        self.hibpDebug = QPlainTextEdit(self.mailDebugSplitter)
        self.hibpDebug.setObjectName(u"hibpDebug")
        self.mailDebugSplitter.addWidget(self.hibpDebug)

        self.verticalLayout_20.addWidget(self.mailDebugSplitter)

        self.mailSplitter.addWidget(self.mailDebugSection)

        self.horizontalLayout_4.addWidget(self.mailSplitter)

        self.mainStackedWidget.addTab(self.mailToolsTab, "")
        self.dorkingTab = QWidget()
        self.dorkingTab.setObjectName(u"dorkingTab")
        self.verticalLayout_12 = QVBoxLayout(self.dorkingTab)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.gridLayout_5 = QGridLayout()
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.dorkCustomEditLayout = QHBoxLayout()
        self.dorkCustomEditLayout.setObjectName(u"dorkCustomEditLayout")
        self.customDorkEdit = QLineEdit(self.dorkingTab)
        self.customDorkEdit.setObjectName(u"customDorkEdit")

        self.dorkCustomEditLayout.addWidget(self.customDorkEdit)

        self.dorkItButton = QPushButton(self.dorkingTab)
        self.dorkItButton.setObjectName(u"dorkItButton")
        self.dorkItButton.setMinimumSize(QSize(200, 0))

        self.dorkCustomEditLayout.addWidget(self.dorkItButton)


        self.gridLayout_5.addLayout(self.dorkCustomEditLayout, 3, 0, 1, 3)

        self.splitter = QSplitter(self.dorkingTab)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.categorySection = QWidget(self.splitter)
        self.categorySection.setObjectName(u"categorySection")
        self.verticalLayout_14 = QVBoxLayout(self.categorySection)
        self.verticalLayout_14.setSpacing(6)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.verticalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.dorksCategoryList = QListWidget(self.categorySection)
        self.dorksCategoryList.setObjectName(u"dorksCategoryList")

        self.verticalLayout_14.addWidget(self.dorksCategoryList)

        self.dorksCategorySearchEdit = QLineEdit(self.categorySection)
        self.dorksCategorySearchEdit.setObjectName(u"dorksCategorySearchEdit")

        self.verticalLayout_14.addWidget(self.dorksCategorySearchEdit)

        self.splitter.addWidget(self.categorySection)
        self.dorksSection = QWidget(self.splitter)
        self.dorksSection.setObjectName(u"dorksSection")
        self.verticalLayout_15 = QVBoxLayout(self.dorksSection)
        self.verticalLayout_15.setSpacing(6)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.dorksList = QListWidget(self.dorksSection)
        self.dorksList.setObjectName(u"dorksList")
        self.dorksList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.verticalLayout_15.addWidget(self.dorksList)

        self.dorksListSearchEdit = QLineEdit(self.dorksSection)
        self.dorksListSearchEdit.setObjectName(u"dorksListSearchEdit")

        self.verticalLayout_15.addWidget(self.dorksListSearchEdit)

        self.splitter.addWidget(self.dorksSection)
        self.resultSection = QWidget(self.splitter)
        self.resultSection.setObjectName(u"resultSection")
        self.verticalLayout_16 = QVBoxLayout(self.resultSection)
        self.verticalLayout_16.setSpacing(6)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.dorksResult = QPlainTextEdit(self.resultSection)
        self.dorksResult.setObjectName(u"dorksResult")

        self.verticalLayout_16.addWidget(self.dorksResult)

        self.dorksResultSearchEdit = QLineEdit(self.resultSection)
        self.dorksResultSearchEdit.setObjectName(u"dorksResultSearchEdit")

        self.verticalLayout_16.addWidget(self.dorksResultSearchEdit)

        self.splitter.addWidget(self.resultSection)

        self.gridLayout_5.addWidget(self.splitter, 0, 0, 1, 3)

        self.groupBox_5 = QGroupBox(self.dorkingTab)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.groupBox_5.setMaximumSize(QSize(16777215, 80))
        self.horizontalLayout_5 = QHBoxLayout(self.groupBox_5)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.useSearxngCheck = QCheckBox(self.groupBox_5)
        self.useSearxngCheck.setObjectName(u"useSearxngCheck")

        self.horizontalLayout_5.addWidget(self.useSearxngCheck)

        self.useCustomDorkCheck = QCheckBox(self.groupBox_5)
        self.useCustomDorkCheck.setObjectName(u"useCustomDorkCheck")

        self.horizontalLayout_5.addWidget(self.useCustomDorkCheck)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_3)


        self.gridLayout_5.addWidget(self.groupBox_5, 1, 0, 1, 3)


        self.verticalLayout_12.addLayout(self.gridLayout_5)

        self.mainStackedWidget.addTab(self.dorkingTab, "")
        self.webAnalyzerTab = QWidget()
        self.webAnalyzerTab.setObjectName(u"webAnalyzerTab")
        self.gridLayout_2 = QGridLayout(self.webAnalyzerTab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.serverLocationDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverLocationDebug.setObjectName(u"serverLocationDebug")

        self.gridLayout_2.addWidget(self.serverLocationDebug, 6, 3, 1, 1)

        self.domainSubdomainsCheck = QCheckBox(self.webAnalyzerTab)
        self.domainSubdomainsCheck.setObjectName(u"domainSubdomainsCheck")
        self.domainSubdomainsCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainSubdomainsCheck, 3, 1, 1, 1)

        self.serverRobotsDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverRobotsDebug.setObjectName(u"serverRobotsDebug")

        self.gridLayout_2.addWidget(self.serverRobotsDebug, 8, 2, 1, 1)

        self.serverTlsDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverTlsDebug.setObjectName(u"serverTlsDebug")

        self.gridLayout_2.addWidget(self.serverTlsDebug, 6, 1, 1, 1)

        self.serverWafDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverWafDebug.setObjectName(u"serverWafDebug")

        self.gridLayout_2.addWidget(self.serverWafDebug, 8, 1, 1, 1)

        self.cookiesDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.cookiesDebug.setObjectName(u"cookiesDebug")

        self.gridLayout_2.addWidget(self.cookiesDebug, 10, 2, 1, 1)

        self.domainLocationCheck = QCheckBox(self.webAnalyzerTab)
        self.domainLocationCheck.setObjectName(u"domainLocationCheck")
        self.domainLocationCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainLocationCheck, 5, 3, 1, 1)

        self.securityTxtDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.securityTxtDebug.setObjectName(u"securityTxtDebug")

        self.gridLayout_2.addWidget(self.securityTxtDebug, 10, 1, 1, 1)

        self.domainDNSCheck = QCheckBox(self.webAnalyzerTab)
        self.domainDNSCheck.setObjectName(u"domainDNSCheck")
        self.domainDNSCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainDNSCheck, 3, 2, 1, 1)

        self.serverSubdomainsDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverSubdomainsDebug.setObjectName(u"serverSubdomainsDebug")

        self.gridLayout_2.addWidget(self.serverSubdomainsDebug, 4, 1, 1, 1)

        self.domainHeadersCheck = QCheckBox(self.webAnalyzerTab)
        self.domainHeadersCheck.setObjectName(u"domainHeadersCheck")
        self.domainHeadersCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainHeadersCheck, 7, 1, 1, 1)

        self.domainNmapCheck = QCheckBox(self.webAnalyzerTab)
        self.domainNmapCheck.setObjectName(u"domainNmapCheck")
        self.domainNmapCheck.setChecked(False)

        self.gridLayout_2.addWidget(self.domainNmapCheck, 3, 3, 1, 1)

        self.socialTagsDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.socialTagsDebug.setObjectName(u"socialTagsDebug")

        self.gridLayout_2.addWidget(self.socialTagsDebug, 10, 3, 1, 1)

        self.domainMalwareCheck = QCheckBox(self.webAnalyzerTab)
        self.domainMalwareCheck.setObjectName(u"domainMalwareCheck")
        self.domainMalwareCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainMalwareCheck, 7, 3, 1, 1)

        self.serverNmapDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverNmapDebug.setObjectName(u"serverNmapDebug")

        self.gridLayout_2.addWidget(self.serverNmapDebug, 4, 3, 1, 1)

        self.domainWhoisCheck = QCheckBox(self.webAnalyzerTab)
        self.domainWhoisCheck.setObjectName(u"domainWhoisCheck")
        self.domainWhoisCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainWhoisCheck, 5, 2, 1, 1)

        self.securityTxtCheck = QCheckBox(self.webAnalyzerTab)
        self.securityTxtCheck.setObjectName(u"securityTxtCheck")
        self.securityTxtCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.securityTxtCheck, 9, 1, 1, 1)

        self.domainSSLCheck = QCheckBox(self.webAnalyzerTab)
        self.domainSSLCheck.setObjectName(u"domainSSLCheck")
        self.domainSSLCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainSSLCheck, 5, 1, 1, 1)

        self.serverDnsAnalyzeDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverDnsAnalyzeDebug.setObjectName(u"serverDnsAnalyzeDebug")

        self.gridLayout_2.addWidget(self.serverDnsAnalyzeDebug, 4, 2, 1, 1)

        self.serverWhoisDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverWhoisDebug.setObjectName(u"serverWhoisDebug")

        self.gridLayout_2.addWidget(self.serverWhoisDebug, 6, 2, 1, 1)

        self.serverMalwareDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverMalwareDebug.setObjectName(u"serverMalwareDebug")

        self.gridLayout_2.addWidget(self.serverMalwareDebug, 8, 3, 1, 1)

        self.socialTagsCheck = QCheckBox(self.webAnalyzerTab)
        self.socialTagsCheck.setObjectName(u"socialTagsCheck")
        self.socialTagsCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.socialTagsCheck, 9, 3, 1, 1)

        self.cookiesCheck = QCheckBox(self.webAnalyzerTab)
        self.cookiesCheck.setObjectName(u"cookiesCheck")
        self.cookiesCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.cookiesCheck, 9, 2, 1, 1)

        self.domainRobotsCheck = QCheckBox(self.webAnalyzerTab)
        self.domainRobotsCheck.setObjectName(u"domainRobotsCheck")
        self.domainRobotsCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainRobotsCheck, 7, 2, 1, 1)

        self.certTrCheck = QCheckBox(self.webAnalyzerTab)
        self.certTrCheck.setObjectName(u"certTrCheck")

        self.gridLayout_2.addWidget(self.certTrCheck, 3, 4, 1, 1)

        self.certTrDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.certTrDebug.setObjectName(u"certTrDebug")

        self.gridLayout_2.addWidget(self.certTrDebug, 4, 4, 1, 1)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(-1, 0, -1, -1)
        self.serverUrlEdit = QLineEdit(self.webAnalyzerTab)
        self.serverUrlEdit.setObjectName(u"serverUrlEdit")

        self.horizontalLayout_9.addWidget(self.serverUrlEdit)

        self.runUrlScanButton = QPushButton(self.webAnalyzerTab)
        self.runUrlScanButton.setObjectName(u"runUrlScanButton")
        self.runUrlScanButton.setMinimumSize(QSize(200, 0))

        self.horizontalLayout_9.addWidget(self.runUrlScanButton)


        self.gridLayout_2.addLayout(self.horizontalLayout_9, 0, 1, 1, 4)

        self.domainProgress = QProgressBar(self.webAnalyzerTab)
        self.domainProgress.setObjectName(u"domainProgress")
        self.domainProgress.setValue(0)

        self.gridLayout_2.addWidget(self.domainProgress, 11, 1, 1, 4)

        self.domainsOnIpDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.domainsOnIpDebug.setObjectName(u"domainsOnIpDebug")

        self.gridLayout_2.addWidget(self.domainsOnIpDebug, 6, 4, 1, 1)

        self.domainsOnIpCheck = QCheckBox(self.webAnalyzerTab)
        self.domainsOnIpCheck.setObjectName(u"domainsOnIpCheck")

        self.gridLayout_2.addWidget(self.domainsOnIpCheck, 5, 4, 1, 1)

        self.mainStackedWidget.addTab(self.webAnalyzerTab, "")
        self.metadataTab = QWidget()
        self.metadataTab.setObjectName(u"metadataTab")
        self.gridLayout_7 = QGridLayout(self.metadataTab)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.metadataDebug = QPlainTextEdit(self.metadataTab)
        self.metadataDebug.setObjectName(u"metadataDebug")

        self.gridLayout_7.addWidget(self.metadataDebug, 1, 1, 3, 1)

        self.stringsFileDebug = QPlainTextEdit(self.metadataTab)
        self.stringsFileDebug.setObjectName(u"stringsFileDebug")

        self.gridLayout_7.addWidget(self.stringsFileDebug, 1, 3, 3, 1)

        self.fileVirustotalCheck = QCheckBox(self.metadataTab)
        self.fileVirustotalCheck.setObjectName(u"fileVirustotalCheck")
        self.fileVirustotalCheck.setChecked(True)

        self.gridLayout_7.addWidget(self.fileVirustotalCheck, 0, 2, 1, 1)

        self.virustotalFileDebug = QPlainTextEdit(self.metadataTab)
        self.virustotalFileDebug.setObjectName(u"virustotalFileDebug")

        self.gridLayout_7.addWidget(self.virustotalFileDebug, 1, 2, 3, 1)

        self.fileMetadataCheck = QCheckBox(self.metadataTab)
        self.fileMetadataCheck.setObjectName(u"fileMetadataCheck")
        self.fileMetadataCheck.setChecked(True)

        self.gridLayout_7.addWidget(self.fileMetadataCheck, 0, 1, 1, 1)

        self.getMetadataButton = QPushButton(self.metadataTab)
        self.getMetadataButton.setObjectName(u"getMetadataButton")
        self.getMetadataButton.setMaximumSize(QSize(400, 16777215))

        self.gridLayout_7.addWidget(self.getMetadataButton, 2, 0, 1, 1)

        self.fileStringsCheck = QCheckBox(self.metadataTab)
        self.fileStringsCheck.setObjectName(u"fileStringsCheck")
        self.fileStringsCheck.setChecked(True)

        self.gridLayout_7.addWidget(self.fileStringsCheck, 0, 3, 1, 1)

        self.metadataFileDropWidget = DropWidget(self.metadataTab)
        self.metadataFileDropWidget.setObjectName(u"metadataFileDropWidget")
        self.metadataFileDropWidget.setMinimumSize(QSize(300, 0))
        self.metadataFileDropWidget.setMaximumSize(QSize(300, 16777215))
        self.verticalLayout = QVBoxLayout(self.metadataFileDropWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.metadataStatusLabel = QLabel(self.metadataFileDropWidget)
        self.metadataStatusLabel.setObjectName(u"metadataStatusLabel")
        font1 = QFont()
        font1.setPointSize(30)
        font1.setBold(True)
        font1.setItalic(True)
        self.metadataStatusLabel.setFont(font1)
        self.metadataStatusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.metadataStatusLabel.setWordWrap(True)

        self.verticalLayout.addWidget(self.metadataStatusLabel)


        self.gridLayout_7.addWidget(self.metadataFileDropWidget, 0, 0, 2, 1)

        self.cleanMetadataButton = QPushButton(self.metadataTab)
        self.cleanMetadataButton.setObjectName(u"cleanMetadataButton")

        self.gridLayout_7.addWidget(self.cleanMetadataButton, 3, 0, 1, 1)

        self.metadataMapView = QWebEngineView(self.metadataTab)
        self.metadataMapView.setObjectName(u"metadataMapView")
        self.metadataMapView.setMinimumSize(QSize(400, 0))
        self.metadataMapView.setMaximumSize(QSize(400, 16777215))
        self.metadataMapView.setVisible(False)
        self.metadataMapView.setStyleSheet(u"")
        self.metadataMapView.setUrl(QUrl(u"about:blank"))

        self.gridLayout_7.addWidget(self.metadataMapView, 0, 4, 4, 1)

        self.mainStackedWidget.addTab(self.metadataTab, "")
        self.githubTab = QWidget()
        self.githubTab.setObjectName(u"githubTab")
        self.githubHorizontalLayout = QHBoxLayout(self.githubTab)
        self.githubHorizontalLayout.setObjectName(u"githubHorizontalLayout")
        self.githubSplitter = QSplitter(self.githubTab)
        self.githubSplitter.setObjectName(u"githubSplitter")
        self.githubSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.githubSettingsSection = QWidget(self.githubSplitter)
        self.githubSettingsSection.setObjectName(u"githubSettingsSection")
        self.githubSettingsLayout = QVBoxLayout(self.githubSettingsSection)
        self.githubSettingsLayout.setObjectName(u"githubSettingsLayout")
        self.githubSettingsLayout.setContentsMargins(0, 0, 0, 0)
        self.githubUserEdit = QLineEdit(self.githubSettingsSection)
        self.githubUserEdit.setObjectName(u"githubUserEdit")

        self.githubSettingsLayout.addWidget(self.githubUserEdit)

        self.githubUserSearchBtn = QPushButton(self.githubSettingsSection)
        self.githubUserSearchBtn.setObjectName(u"githubUserSearchBtn")

        self.githubSettingsLayout.addWidget(self.githubUserSearchBtn)

        self.githubRepoEdit = QLineEdit(self.githubSettingsSection)
        self.githubRepoEdit.setObjectName(u"githubRepoEdit")

        self.githubSettingsLayout.addWidget(self.githubRepoEdit)

        self.githubRepoSearchBtn = QPushButton(self.githubSettingsSection)
        self.githubRepoSearchBtn.setObjectName(u"githubRepoSearchBtn")

        self.githubSettingsLayout.addWidget(self.githubRepoSearchBtn)

        self.githubEmailEdit = QLineEdit(self.githubSettingsSection)
        self.githubEmailEdit.setObjectName(u"githubEmailEdit")

        self.githubSettingsLayout.addWidget(self.githubEmailEdit)

        self.githubEmailSearchBtn = QPushButton(self.githubSettingsSection)
        self.githubEmailSearchBtn.setObjectName(u"githubEmailSearchBtn")

        self.githubSettingsLayout.addWidget(self.githubEmailSearchBtn)

        self.githubCommitEdit = QLineEdit(self.githubSettingsSection)
        self.githubCommitEdit.setObjectName(u"githubCommitEdit")

        self.githubSettingsLayout.addWidget(self.githubCommitEdit)

        self.githubCommitSearchBtn = QPushButton(self.githubSettingsSection)
        self.githubCommitSearchBtn.setObjectName(u"githubCommitSearchBtn")

        self.githubSettingsLayout.addWidget(self.githubCommitSearchBtn)

        self.githubSecretEdit = QLineEdit(self.githubSettingsSection)
        self.githubSecretEdit.setObjectName(u"githubSecretEdit")

        self.githubSettingsLayout.addWidget(self.githubSecretEdit)

        self.githubSecretSearchBtn = QPushButton(self.githubSettingsSection)
        self.githubSecretSearchBtn.setObjectName(u"githubSecretSearchBtn")

        self.githubSettingsLayout.addWidget(self.githubSecretSearchBtn)

        self.githubDorkGroup = QGroupBox(self.githubSettingsSection)
        self.githubDorkGroup.setObjectName(u"githubDorkGroup")
        self.githubDorkLayout = QVBoxLayout(self.githubDorkGroup)
        self.githubDorkLayout.setObjectName(u"githubDorkLayout")
        self.githubDorkEdit = QLineEdit(self.githubDorkGroup)
        self.githubDorkEdit.setObjectName(u"githubDorkEdit")

        self.githubDorkLayout.addWidget(self.githubDorkEdit)

        self.githubDorkTypeLayout = QHBoxLayout()
        self.githubDorkTypeLayout.setObjectName(u"githubDorkTypeLayout")
        self.githubDorkCodeCheck = QCheckBox(self.githubDorkGroup)
        self.githubDorkCodeCheck.setObjectName(u"githubDorkCodeCheck")
        self.githubDorkCodeCheck.setChecked(True)

        self.githubDorkTypeLayout.addWidget(self.githubDorkCodeCheck)

        self.githubDorkCommitsCheck = QCheckBox(self.githubDorkGroup)
        self.githubDorkCommitsCheck.setObjectName(u"githubDorkCommitsCheck")

        self.githubDorkTypeLayout.addWidget(self.githubDorkCommitsCheck)

        self.githubDorkIssuesCheck = QCheckBox(self.githubDorkGroup)
        self.githubDorkIssuesCheck.setObjectName(u"githubDorkIssuesCheck")

        self.githubDorkTypeLayout.addWidget(self.githubDorkIssuesCheck)

        self.githubDorkReposCheck = QCheckBox(self.githubDorkGroup)
        self.githubDorkReposCheck.setObjectName(u"githubDorkReposCheck")

        self.githubDorkTypeLayout.addWidget(self.githubDorkReposCheck)

        self.githubDorkUsersCheck = QCheckBox(self.githubDorkGroup)
        self.githubDorkUsersCheck.setObjectName(u"githubDorkUsersCheck")

        self.githubDorkTypeLayout.addWidget(self.githubDorkUsersCheck)


        self.githubDorkLayout.addLayout(self.githubDorkTypeLayout)

        self.githubDorkSearchBtn = QPushButton(self.githubDorkGroup)
        self.githubDorkSearchBtn.setObjectName(u"githubDorkSearchBtn")

        self.githubDorkLayout.addWidget(self.githubDorkSearchBtn)


        self.githubSettingsLayout.addWidget(self.githubDorkGroup)

        self.githubVerticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.githubSettingsLayout.addItem(self.githubVerticalSpacer)

        self.githubProgress = QProgressBar(self.githubSettingsSection)
        self.githubProgress.setObjectName(u"githubProgress")
        self.githubProgress.setValue(0)

        self.githubSettingsLayout.addWidget(self.githubProgress)

        self.githubSplitter.addWidget(self.githubSettingsSection)
        self.githubDebugSection = QWidget(self.githubSplitter)
        self.githubDebugSection.setObjectName(u"githubDebugSection")
        self.githubDebugLayout = QVBoxLayout(self.githubDebugSection)
        self.githubDebugLayout.setObjectName(u"githubDebugLayout")
        self.githubDebugLayout.setContentsMargins(0, 0, 0, 0)
        self.githubDebug = QPlainTextEdit(self.githubDebugSection)
        self.githubDebug.setObjectName(u"githubDebug")
        self.githubDebug.setReadOnly(True)

        self.githubDebugLayout.addWidget(self.githubDebug)

        self.githubSplitter.addWidget(self.githubDebugSection)

        self.githubHorizontalLayout.addWidget(self.githubSplitter)

        self.mainStackedWidget.addTab(self.githubTab, "")
        self.phoneTab = QWidget()
        self.phoneTab.setObjectName(u"phoneTab")
        self.phoneHorizontalLayout = QHBoxLayout(self.phoneTab)
        self.phoneHorizontalLayout.setObjectName(u"phoneHorizontalLayout")
        self.phoneSplitter = QSplitter(self.phoneTab)
        self.phoneSplitter.setObjectName(u"phoneSplitter")
        self.phoneSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.phoneSettingsSection = QWidget(self.phoneSplitter)
        self.phoneSettingsSection.setObjectName(u"phoneSettingsSection")
        self.phoneSettingsLayout = QVBoxLayout(self.phoneSettingsSection)
        self.phoneSettingsLayout.setObjectName(u"phoneSettingsLayout")
        self.phoneSettingsLayout.setContentsMargins(0, 0, 0, 0)
        self.phoneNumberEdit = QLineEdit(self.phoneSettingsSection)
        self.phoneNumberEdit.setObjectName(u"phoneNumberEdit")

        self.phoneSettingsLayout.addWidget(self.phoneNumberEdit)

        self.phoneRegionEdit = QLineEdit(self.phoneSettingsSection)
        self.phoneRegionEdit.setObjectName(u"phoneRegionEdit")

        self.phoneSettingsLayout.addWidget(self.phoneRegionEdit)

        self.phoneParseBtn = QPushButton(self.phoneSettingsSection)
        self.phoneParseBtn.setObjectName(u"phoneParseBtn")

        self.phoneSettingsLayout.addWidget(self.phoneParseBtn)

        self.phoneLookupBtn = QPushButton(self.phoneSettingsSection)
        self.phoneLookupBtn.setObjectName(u"phoneLookupBtn")

        self.phoneSettingsLayout.addWidget(self.phoneLookupBtn)

        self.phoneLeakBtn = QPushButton(self.phoneSettingsSection)
        self.phoneLeakBtn.setObjectName(u"phoneLeakBtn")

        self.phoneSettingsLayout.addWidget(self.phoneLeakBtn)

        self.phone7telBtn = QPushButton(self.phoneSettingsSection)
        self.phone7telBtn.setObjectName(u"phone7telBtn")

        self.phoneSettingsLayout.addWidget(self.phone7telBtn)

        self.phoneVerticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.phoneSettingsLayout.addItem(self.phoneVerticalSpacer)

        self.phoneProgress = QProgressBar(self.phoneSettingsSection)
        self.phoneProgress.setObjectName(u"phoneProgress")
        self.phoneProgress.setValue(0)

        self.phoneSettingsLayout.addWidget(self.phoneProgress)

        self.phoneSplitter.addWidget(self.phoneSettingsSection)
        self.phoneDebugSection = QWidget(self.phoneSplitter)
        self.phoneDebugSection.setObjectName(u"phoneDebugSection")
        self.phoneDebugLayout = QVBoxLayout(self.phoneDebugSection)
        self.phoneDebugLayout.setObjectName(u"phoneDebugLayout")
        self.phoneDebugLayout.setContentsMargins(0, 0, 0, 0)
        self.phoneDebug = QPlainTextEdit(self.phoneDebugSection)
        self.phoneDebug.setObjectName(u"phoneDebug")
        self.phoneDebug.setReadOnly(True)

        self.phoneDebugLayout.addWidget(self.phoneDebug)

        self.phoneSplitter.addWidget(self.phoneDebugSection)

        self.phoneHorizontalLayout.addWidget(self.phoneSplitter)

        self.mainStackedWidget.addTab(self.phoneTab, "")
        self.macAddrTab = QWidget()
        self.macAddrTab.setObjectName(u"macAddrTab")
        self.gridLayout_9 = QGridLayout(self.macAddrTab)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.checkMacAddrButton = QPushButton(self.macAddrTab)
        self.checkMacAddrButton.setObjectName(u"checkMacAddrButton")
        self.checkMacAddrButton.setMinimumSize(QSize(150, 0))

        self.gridLayout_9.addWidget(self.checkMacAddrButton, 0, 2, 1, 1)

        self.macAddrEdit = QLineEdit(self.macAddrTab)
        self.macAddrEdit.setObjectName(u"macAddrEdit")

        self.gridLayout_9.addWidget(self.macAddrEdit, 0, 0, 1, 1)

        self.macSplitter = QSplitter(self.macAddrTab)
        self.macSplitter.setObjectName(u"macSplitter")
        self.macSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.macAddrLocationDebug = QPlainTextEdit(self.macSplitter)
        self.macAddrLocationDebug.setObjectName(u"macAddrLocationDebug")
        self.macSplitter.addWidget(self.macAddrLocationDebug)
        self.macLocationMapView = QWebEngineView(self.macSplitter)
        self.macLocationMapView.setObjectName(u"macLocationMapView")
        self.macLocationMapView.setMinimumSize(QSize(300, 0))
        self.macLocationMapView.setVisible(False)
        self.macLocationMapView.setStyleSheet(u"border-radius: 15px;")
        self.macLocationMapView.setUrl(QUrl(u"about:blank"))
        self.macSplitter.addWidget(self.macLocationMapView)

        self.gridLayout_9.addWidget(self.macSplitter, 1, 0, 1, 3)

        self.mainStackedWidget.addTab(self.macAddrTab, "")
        self.blockchainTab = QWidget()
        self.blockchainTab.setObjectName(u"blockchainTab")
        self.bcHorizontalLayout = QHBoxLayout(self.blockchainTab)
        self.bcHorizontalLayout.setObjectName(u"bcHorizontalLayout")
        self.bcSplitter = QSplitter(self.blockchainTab)
        self.bcSplitter.setObjectName(u"bcSplitter")
        self.bcSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.bcSettingsSection = QWidget(self.bcSplitter)
        self.bcSettingsSection.setObjectName(u"bcSettingsSection")
        self.bcSettingsLayout = QVBoxLayout(self.bcSettingsSection)
        self.bcSettingsLayout.setObjectName(u"bcSettingsLayout")
        self.bcSettingsLayout.setContentsMargins(0, 0, 0, 0)
        self.bcNetworkCombo = QComboBox(self.bcSettingsSection)
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.addItem("")
        self.bcNetworkCombo.setObjectName(u"bcNetworkCombo")

        self.bcSettingsLayout.addWidget(self.bcNetworkCombo)

        self.bcCoinCombo = QComboBox(self.bcSettingsSection)
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.addItem("")
        self.bcCoinCombo.setObjectName(u"bcCoinCombo")

        self.bcSettingsLayout.addWidget(self.bcCoinCombo)

        self.bcDateEdit = QLineEdit(self.bcSettingsSection)
        self.bcDateEdit.setObjectName(u"bcDateEdit")

        self.bcSettingsLayout.addWidget(self.bcDateEdit)

        self.bcTimeEdit = QLineEdit(self.bcSettingsSection)
        self.bcTimeEdit.setObjectName(u"bcTimeEdit")

        self.bcSettingsLayout.addWidget(self.bcTimeEdit)

        self.bcTimeRangeCombo = QComboBox(self.bcSettingsSection)
        self.bcTimeRangeCombo.addItem("")
        self.bcTimeRangeCombo.addItem("")
        self.bcTimeRangeCombo.addItem("")
        self.bcTimeRangeCombo.addItem("")
        self.bcTimeRangeCombo.addItem("")
        self.bcTimeRangeCombo.setObjectName(u"bcTimeRangeCombo")

        self.bcSettingsLayout.addWidget(self.bcTimeRangeCombo)

        self.bcAmountEdit = QLineEdit(self.bcSettingsSection)
        self.bcAmountEdit.setObjectName(u"bcAmountEdit")

        self.bcSettingsLayout.addWidget(self.bcAmountEdit)

        self.bcToleranceSpin = QDoubleSpinBox(self.bcSettingsSection)
        self.bcToleranceSpin.setObjectName(u"bcToleranceSpin")
        self.bcToleranceSpin.setDecimals(2)
        self.bcToleranceSpin.setMaximum(1.000000000000000)
        self.bcToleranceSpin.setSingleStep(0.010000000000000)
        self.bcToleranceSpin.setValue(0.010000000000000)

        self.bcSettingsLayout.addWidget(self.bcToleranceSpin)

        self.bcMemoEdit = QLineEdit(self.bcSettingsSection)
        self.bcMemoEdit.setObjectName(u"bcMemoEdit")

        self.bcSettingsLayout.addWidget(self.bcMemoEdit)

        self.bcSearchButton = QPushButton(self.bcSettingsSection)
        self.bcSearchButton.setObjectName(u"bcSearchButton")

        self.bcSettingsLayout.addWidget(self.bcSearchButton)

        self.bcVerticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.bcSettingsLayout.addItem(self.bcVerticalSpacer)

        self.bcProgressBar = QProgressBar(self.bcSettingsSection)
        self.bcProgressBar.setObjectName(u"bcProgressBar")
        self.bcProgressBar.setValue(0)

        self.bcSettingsLayout.addWidget(self.bcProgressBar)

        self.bcSplitter.addWidget(self.bcSettingsSection)
        self.bcDebugSection = QWidget(self.bcSplitter)
        self.bcDebugSection.setObjectName(u"bcDebugSection")
        self.bcDebugLayout = QVBoxLayout(self.bcDebugSection)
        self.bcDebugLayout.setObjectName(u"bcDebugLayout")
        self.bcDebugLayout.setContentsMargins(0, 0, 0, 0)
        self.bcDebug = QPlainTextEdit(self.bcDebugSection)
        self.bcDebug.setObjectName(u"bcDebug")
        self.bcDebug.setReadOnly(True)

        self.bcDebugLayout.addWidget(self.bcDebug)

        self.bcSplitter.addWidget(self.bcDebugSection)

        self.bcHorizontalLayout.addWidget(self.bcSplitter)

        self.mainStackedWidget.addTab(self.blockchainTab, "")
        self.steganographyTab = QWidget()
        self.steganographyTab.setObjectName(u"steganographyTab")
        self.steganographyLayout = QHBoxLayout(self.steganographyTab)
        self.steganographyLayout.setObjectName(u"steganographyLayout")
        self.steganographyLayout.setContentsMargins(9, 9, 9, 9)
        self.steganographySplitter = QSplitter(self.steganographyTab)
        self.steganographySplitter.setObjectName(u"steganographySplitter")
        self.steganographySplitter.setOrientation(Qt.Orientation.Horizontal)
        self.steganoFileDrop = DropWidget(self.steganographySplitter)
        self.steganoFileDrop.setObjectName(u"steganoFileDrop")
        self.verticalLayout_2 = QVBoxLayout(self.steganoFileDrop)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_8 = QLabel(self.steganoFileDrop)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setMinimumSize(QSize(200, 0))
        font2 = QFont()
        font2.setPointSize(30)
        self.label_8.setFont(font2)
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_2.addWidget(self.label_8)

        self.steganographySplitter.addWidget(self.steganoFileDrop)
        self.LSBDebug = QPlainTextEdit(self.steganographySplitter)
        self.LSBDebug.setObjectName(u"LSBDebug")
        self.steganographySplitter.addWidget(self.LSBDebug)
        self.spectralAnalysisDebug = QPlainTextEdit(self.steganographySplitter)
        self.spectralAnalysisDebug.setObjectName(u"spectralAnalysisDebug")
        self.steganographySplitter.addWidget(self.spectralAnalysisDebug)
        self.EOIDebug = QPlainTextEdit(self.steganographySplitter)
        self.EOIDebug.setObjectName(u"EOIDebug")
        self.steganographySplitter.addWidget(self.EOIDebug)
        self.tailDataDetectionDebug = QPlainTextEdit(self.steganographySplitter)
        self.tailDataDetectionDebug.setObjectName(u"tailDataDetectionDebug")
        self.steganographySplitter.addWidget(self.tailDataDetectionDebug)

        self.steganographyLayout.addWidget(self.steganographySplitter)

        self.mainStackedWidget.addTab(self.steganographyTab, "")
        self.s4facesTab = QWidget()
        self.s4facesTab.setObjectName(u"s4facesTab")
        self.gridLayout_10 = QGridLayout(self.s4facesTab)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.s4fFileDropWidget = DropWidget(self.s4facesTab)
        self.s4fFileDropWidget.setObjectName(u"s4fFileDropWidget")
        self.verticalLayout_24 = QVBoxLayout(self.s4fFileDropWidget)
        self.verticalLayout_24.setObjectName(u"verticalLayout_24")
        self.label_9 = QLabel(self.s4fFileDropWidget)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setMinimumSize(QSize(300, 0))
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_24.addWidget(self.label_9)


        self.gridLayout_10.addWidget(self.s4fFileDropWidget, 2, 0, 1, 1)

        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.runS4FButton = QPushButton(self.s4facesTab)
        self.runS4FButton.setObjectName(u"runS4FButton")
        self.runS4FButton.setMinimumSize(QSize(150, 0))

        self.horizontalLayout_11.addWidget(self.runS4FButton)


        self.gridLayout_10.addLayout(self.horizontalLayout_11, 3, 0, 1, 1)

        self.s4fResultsScrollArea = QScrollArea(self.s4facesTab)
        self.s4fResultsScrollArea.setObjectName(u"s4fResultsScrollArea")
        self.s4fResultsScrollArea.setWidgetResizable(True)
        self.s4fResultsContainer = QWidget()
        self.s4fResultsContainer.setObjectName(u"s4fResultsContainer")
        self.s4fResultsContainer.setGeometry(QRect(0, 0, 98, 28))
        self.verticalLayout_26 = QVBoxLayout(self.s4fResultsContainer)
        self.verticalLayout_26.setObjectName(u"verticalLayout_26")
        self.s4fResultsLayout = QVBoxLayout()
        self.s4fResultsLayout.setObjectName(u"s4fResultsLayout")

        self.verticalLayout_26.addLayout(self.s4fResultsLayout)

        self.s4fResultsScrollArea.setWidget(self.s4fResultsContainer)

        self.gridLayout_10.addWidget(self.s4fResultsScrollArea, 1, 1, 3, 1)

        self.s4fSearchEdit = QLineEdit(self.s4facesTab)
        self.s4fSearchEdit.setObjectName(u"s4fSearchEdit")

        self.gridLayout_10.addWidget(self.s4fSearchEdit, 0, 1, 1, 1)

        self.s4fTargetLabel = QLabel(self.s4facesTab)
        self.s4fTargetLabel.setObjectName(u"s4fTargetLabel")

        self.gridLayout_10.addWidget(self.s4fTargetLabel, 0, 0, 2, 1)

        self.mainStackedWidget.addTab(self.s4facesTab, "")
        self.graphTab = QWidget()
        self.graphTab.setObjectName(u"graphTab")
        self.graphMainLayout = QVBoxLayout(self.graphTab)
        self.graphMainLayout.setObjectName(u"graphMainLayout")
        self.graphMainLayout.setContentsMargins(0, 0, 0, 0)
        self.graphSplitter = QSplitter(self.graphTab)
        self.graphSplitter.setObjectName(u"graphSplitter")
        self.graphSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.entityPanel = QWidget(self.graphSplitter)
        self.entityPanel.setObjectName(u"entityPanel")
        self.entityLayout = QVBoxLayout(self.entityPanel)
        self.entityLayout.setObjectName(u"entityLayout")
        self.entityLayout.setContentsMargins(-1, -1, 9, -1)
        self.entitySearchEdit = QLineEdit(self.entityPanel)
        self.entitySearchEdit.setObjectName(u"entitySearchEdit")

        self.entityLayout.addWidget(self.entitySearchEdit)

        self.entityPalette = EntityPalette(self.entityPanel)
        self.entityPalette.setObjectName(u"entityPalette")
        self.entityPalette.setMinimumSize(QSize(200, 0))
        self.verticalLayout_23 = QVBoxLayout(self.entityPalette)
        self.verticalLayout_23.setObjectName(u"verticalLayout_23")

        self.entityLayout.addWidget(self.entityPalette)

        self.graphSplitter.addWidget(self.entityPanel)
        self.graphCenterPanel = QWidget(self.graphSplitter)
        self.graphCenterPanel.setObjectName(u"graphCenterPanel")
        self.graphCenterLayout = QVBoxLayout(self.graphCenterPanel)
        self.graphCenterLayout.setObjectName(u"graphCenterLayout")
        self.graphButtonLayout = QHBoxLayout()
        self.graphButtonLayout.setObjectName(u"graphButtonLayout")
        self.exportGraphButton = QPushButton(self.graphCenterPanel)
        self.exportGraphButton.setObjectName(u"exportGraphButton")

        self.graphButtonLayout.addWidget(self.exportGraphButton)

        self.importGraphButton = QPushButton(self.graphCenterPanel)
        self.importGraphButton.setObjectName(u"importGraphButton")

        self.graphButtonLayout.addWidget(self.importGraphButton)

        self.graphClearButton = QPushButton(self.graphCenterPanel)
        self.graphClearButton.setObjectName(u"graphClearButton")

        self.graphButtonLayout.addWidget(self.graphClearButton)

        self.graphLayoutCombo = QComboBox(self.graphCenterPanel)
        self.graphLayoutCombo.setObjectName(u"graphLayoutCombo")
        self.graphLayoutCombo.setMinimumSize(QSize(160, 0))

        self.graphButtonLayout.addWidget(self.graphLayoutCombo)

        self.graphAutoLayoutButton = QPushButton(self.graphCenterPanel)
        self.graphAutoLayoutButton.setObjectName(u"graphAutoLayoutButton")

        self.graphButtonLayout.addWidget(self.graphAutoLayoutButton)


        self.graphCenterLayout.addLayout(self.graphButtonLayout)

        self.graphSearchLayout = QHBoxLayout()
        self.graphSearchLayout.setObjectName(u"graphSearchLayout")
        self.graphSearchEdit = QLineEdit(self.graphCenterPanel)
        self.graphSearchEdit.setObjectName(u"graphSearchEdit")
        self.graphSearchEdit.setClearButtonEnabled(True)

        self.graphSearchLayout.addWidget(self.graphSearchEdit)

        self.graphClearFilterButton = QPushButton(self.graphCenterPanel)
        self.graphClearFilterButton.setObjectName(u"graphClearFilterButton")
        self.graphClearFilterButton.setMinimumSize(QSize(150, 0))

        self.graphSearchLayout.addWidget(self.graphClearFilterButton)

        self.graphFilterCombo = QComboBox(self.graphCenterPanel)
        self.graphFilterCombo.setObjectName(u"graphFilterCombo")
        self.graphFilterCombo.setMinimumSize(QSize(150, 0))

        self.graphSearchLayout.addWidget(self.graphFilterCombo)


        self.graphCenterLayout.addLayout(self.graphSearchLayout)

        self.graphWidget = GraphWidget(self.graphCenterPanel)
        self.graphWidget.setObjectName(u"graphWidget")

        self.graphCenterLayout.addWidget(self.graphWidget)

        self.graphSplitter.addWidget(self.graphCenterPanel)
        self.verticalWidget = QWidget(self.graphSplitter)
        self.verticalWidget.setObjectName(u"verticalWidget")
        self.verticalWidget.setMinimumSize(QSize(0, 0))
        self.verticalWidget.setMaximumSize(QSize(16777215, 16777215))
        self.verticalLayout_13 = QVBoxLayout(self.verticalWidget)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(9, 9, 9, 9)
        self.nodeTitleEdit = QLineEdit(self.verticalWidget)
        self.nodeTitleEdit.setObjectName(u"nodeTitleEdit")

        self.verticalLayout_13.addWidget(self.nodeTitleEdit)

        self.nodeTypeCombo = QComboBox(self.verticalWidget)
        self.nodeTypeCombo.setObjectName(u"nodeTypeCombo")

        self.verticalLayout_13.addWidget(self.nodeTypeCombo)

        self.nodeContentEdit = QPlainTextEdit(self.verticalWidget)
        self.nodeContentEdit.setObjectName(u"nodeContentEdit")
        self.nodeContentEdit.setMinimumSize(QSize(250, 60))

        self.verticalLayout_13.addWidget(self.nodeContentEdit)

        self.nodeEvidenceList = QListWidget(self.verticalWidget)
        self.nodeEvidenceList.setObjectName(u"nodeEvidenceList")

        self.verticalLayout_13.addWidget(self.nodeEvidenceList)

        self.nodeEvidenceBtnLayout = QHBoxLayout()
        self.nodeEvidenceBtnLayout.setObjectName(u"nodeEvidenceBtnLayout")
        self.nodeEvidenceBtnLayout.setContentsMargins(0, 0, 0, 0)
        self.nodeEvidenceAddFileBtn = QPushButton(self.verticalWidget)
        self.nodeEvidenceAddFileBtn.setObjectName(u"nodeEvidenceAddFileBtn")

        self.nodeEvidenceBtnLayout.addWidget(self.nodeEvidenceAddFileBtn)

        self.nodeEvidenceAddUrlBtn = QPushButton(self.verticalWidget)
        self.nodeEvidenceAddUrlBtn.setObjectName(u"nodeEvidenceAddUrlBtn")

        self.nodeEvidenceBtnLayout.addWidget(self.nodeEvidenceAddUrlBtn)

        self.nodeEvidenceRemoveBtn = QPushButton(self.verticalWidget)
        self.nodeEvidenceRemoveBtn.setObjectName(u"nodeEvidenceRemoveBtn")

        self.nodeEvidenceBtnLayout.addWidget(self.nodeEvidenceRemoveBtn)


        self.verticalLayout_13.addLayout(self.nodeEvidenceBtnLayout)

        self.graphSplitter.addWidget(self.verticalWidget)

        self.graphMainLayout.addWidget(self.graphSplitter)

        self.mainStackedWidget.addTab(self.graphTab, "")
        self.reportTab = QWidget()
        self.reportTab.setObjectName(u"reportTab")
        self.gridLayout_6 = QGridLayout(self.reportTab)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.aiReportLangEdit = QLineEdit(self.reportTab)
        self.aiReportLangEdit.setObjectName(u"aiReportLangEdit")

        self.gridLayout_6.addWidget(self.aiReportLangEdit, 1, 0, 1, 1)

        self.ollamaModelsSelector = QComboBox(self.reportTab)
        self.ollamaModelsSelector.setObjectName(u"ollamaModelsSelector")
        self.ollamaModelsSelector.setMinimumSize(QSize(150, 0))

        self.gridLayout_6.addWidget(self.ollamaModelsSelector, 1, 1, 1, 1)

        self.updateOllamaListButton = QPushButton(self.reportTab)
        self.updateOllamaListButton.setObjectName(u"updateOllamaListButton")
        self.updateOllamaListButton.setMinimumSize(QSize(150, 0))

        self.gridLayout_6.addWidget(self.updateOllamaListButton, 1, 2, 1, 1)

        self.aiReportDebug = QPlainTextEdit(self.reportTab)
        self.aiReportDebug.setObjectName(u"aiReportDebug")

        self.gridLayout_6.addWidget(self.aiReportDebug, 0, 0, 1, 3)

        self.generateReportButton = QPushButton(self.reportTab)
        self.generateReportButton.setObjectName(u"generateReportButton")

        self.gridLayout_6.addWidget(self.generateReportButton, 2, 0, 1, 3)

        self.saveReportButton = QPushButton(self.reportTab)
        self.saveReportButton.setObjectName(u"saveReportButton")

        self.gridLayout_6.addWidget(self.saveReportButton, 3, 0, 1, 3)

        self.mainStackedWidget.addTab(self.reportTab, "")
        self.settingsTab = QWidget()
        self.settingsTab.setObjectName(u"settingsTab")
        self.horizontalLayout = QHBoxLayout(self.settingsTab)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)

        self.pathToStorageEdit = QLineEdit(self.settingsTab)
        self.pathToStorageEdit.setObjectName(u"pathToStorageEdit")
        self.pathToStorageEdit.setMinimumSize(QSize(500, 0))

        self.verticalLayout_4.addWidget(self.pathToStorageEdit)

        self.tgApiKeyEdit = QLineEdit(self.settingsTab)
        self.tgApiKeyEdit.setObjectName(u"tgApiKeyEdit")

        self.verticalLayout_4.addWidget(self.tgApiKeyEdit)

        self.telegramApiHashEdit = QLineEdit(self.settingsTab)
        self.telegramApiHashEdit.setObjectName(u"telegramApiHashEdit")

        self.verticalLayout_4.addWidget(self.telegramApiHashEdit)

        self.telegramPhoneEdit = QLineEdit(self.settingsTab)
        self.telegramPhoneEdit.setObjectName(u"telegramPhoneEdit")

        self.verticalLayout_4.addWidget(self.telegramPhoneEdit)

        self.intelligentXApiKeyEdit = QLineEdit(self.settingsTab)
        self.intelligentXApiKeyEdit.setObjectName(u"intelligentXApiKeyEdit")

        self.verticalLayout_4.addWidget(self.intelligentXApiKeyEdit)

        self.hibpApiKeyEdit = QLineEdit(self.settingsTab)
        self.hibpApiKeyEdit.setObjectName(u"hibpApiKeyEdit")

        self.verticalLayout_4.addWidget(self.hibpApiKeyEdit)

        self.virustotalApiKeyEdit = QLineEdit(self.settingsTab)
        self.virustotalApiKeyEdit.setObjectName(u"virustotalApiKeyEdit")

        self.verticalLayout_4.addWidget(self.virustotalApiKeyEdit)

        self.googleSafeApiKeyEdit = QLineEdit(self.settingsTab)
        self.googleSafeApiKeyEdit.setObjectName(u"googleSafeApiKeyEdit")

        self.verticalLayout_4.addWidget(self.googleSafeApiKeyEdit)

        self.ipinfoApiKeyEdit = QLineEdit(self.settingsTab)
        self.ipinfoApiKeyEdit.setObjectName(u"ipinfoApiKeyEdit")

        self.verticalLayout_4.addWidget(self.ipinfoApiKeyEdit)

        self.githubTokenEdit = QLineEdit(self.settingsTab)
        self.githubTokenEdit.setObjectName(u"githubTokenEdit")

        self.verticalLayout_4.addWidget(self.githubTokenEdit)

        self.numverifyApiKeyEdit = QLineEdit(self.settingsTab)
        self.numverifyApiKeyEdit.setObjectName(u"numverifyApiKeyEdit")

        self.verticalLayout_4.addWidget(self.numverifyApiKeyEdit)

        self.abstractapiApiKeyEdit = QLineEdit(self.settingsTab)
        self.abstractapiApiKeyEdit.setObjectName(u"abstractapiApiKeyEdit")

        self.verticalLayout_4.addWidget(self.abstractapiApiKeyEdit)

        self.trongridApiKeyEdit = QLineEdit(self.settingsTab)
        self.trongridApiKeyEdit.setObjectName(u"trongridApiKeyEdit")

        self.verticalLayout_4.addWidget(self.trongridApiKeyEdit)

        self.etherscanApiKeyEdit = QLineEdit(self.settingsTab)
        self.etherscanApiKeyEdit.setObjectName(u"etherscanApiKeyEdit")

        self.verticalLayout_4.addWidget(self.etherscanApiKeyEdit)

        self.bscscanApiKeyEdit = QLineEdit(self.settingsTab)
        self.bscscanApiKeyEdit.setObjectName(u"bscscanApiKeyEdit")

        self.verticalLayout_4.addWidget(self.bscscanApiKeyEdit)

        self.tonapiApiKeyEdit = QLineEdit(self.settingsTab)
        self.tonapiApiKeyEdit.setObjectName(u"tonapiApiKeyEdit")

        self.verticalLayout_4.addWidget(self.tonapiApiKeyEdit)

        self.heliusApiKeyEdit = QLineEdit(self.settingsTab)
        self.heliusApiKeyEdit.setObjectName(u"heliusApiKeyEdit")

        self.verticalLayout_4.addWidget(self.heliusApiKeyEdit)

        self.lightThemeCheck = QCheckBox(self.settingsTab)
        self.lightThemeCheck.setObjectName(u"lightThemeCheck")

        self.verticalLayout_4.addWidget(self.lightThemeCheck)

        self.framelessCheck = QCheckBox(self.settingsTab)
        self.framelessCheck.setObjectName(u"framelessCheck")

        self.verticalLayout_4.addWidget(self.framelessCheck)

        self.groupBox_6 = QGroupBox(self.settingsTab)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.groupBox_6.setMinimumSize(QSize(0, 0))
        self.groupBox_6.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalLayout_22 = QVBoxLayout(self.groupBox_6)
        self.verticalLayout_22.setObjectName(u"verticalLayout_22")
        self.mcpStatusLabel = QLabel(self.groupBox_6)
        self.mcpStatusLabel.setObjectName(u"mcpStatusLabel")
        self.mcpStatusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_22.addWidget(self.mcpStatusLabel)

        self.mcpToggleButton = QPushButton(self.groupBox_6)
        self.mcpToggleButton.setObjectName(u"mcpToggleButton")

        self.verticalLayout_22.addWidget(self.mcpToggleButton)


        self.verticalLayout_4.addWidget(self.groupBox_6)

        self.pushButton = QPushButton(self.settingsTab)
        self.pushButton.setObjectName(u"pushButton")

        self.verticalLayout_4.addWidget(self.pushButton)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_2)


        self.horizontalLayout.addLayout(self.verticalLayout_4)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.mainStackedWidget.addTab(self.settingsTab, "")
        self.proxyTab = QWidget()
        self.proxyTab.setObjectName(u"proxyTab")
        self.verticalLayout_3 = QVBoxLayout(self.proxyTab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.proxyListEdit = QPlainTextEdit(self.proxyTab)
        self.proxyListEdit.setObjectName(u"proxyListEdit")

        self.horizontalLayout_2.addWidget(self.proxyListEdit)


        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.saveProxiesButton = QPushButton(self.proxyTab)
        self.saveProxiesButton.setObjectName(u"saveProxiesButton")

        self.verticalLayout_3.addWidget(self.saveProxiesButton)

        self.mainStackedWidget.addTab(self.proxyTab, "")

        self.horizontalLayout_6.addWidget(self.mainStackedWidget)


        self.horizontalLayout_10.addLayout(self.horizontalLayout_6)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 1244, 22))
        self.menuFile = QMenu(self.menuBar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuView = QMenu(self.menuBar)
        self.menuView.setObjectName(u"menuView")
        self.menuHelp = QMenu(self.menuBar)
        self.menuHelp.setObjectName(u"menuHelp")
        self.menu_SkyFall = QMenu(self.menuBar)
        self.menu_SkyFall.setObjectName(u"menu_SkyFall")
        self.menu_SkyFall.setTearOffEnabled(True)
        MainWindow.setMenuBar(self.menuBar)

        self.menuBar.addAction(self.menu_SkyFall.menuAction())
        self.menuBar.addAction(self.menuFile.menuAction())
        self.menuBar.addAction(self.menuView.menuAction())
        self.menuBar.addAction(self.menuHelp.menuAction())
        self.menuFile.addAction(self.actionNew_case)
        self.menuFile.addAction(self.actionOpen_case)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExit)
        self.menuView.addAction(self.actionToggleNavigation)
        self.menuHelp.addAction(self.actionAbout)
        self.menuHelp.addAction(self.actionOpenGitHub)

        self.retranslateUi(MainWindow)

        self.mainStackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionNew_case.setText(QCoreApplication.translate("MainWindow", u"New case", None))
        self.actionOpen_case.setText(QCoreApplication.translate("MainWindow", u"Open case", None))
        self.actionExit.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.actionAbout.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.actionOpenGitHub.setText(QCoreApplication.translate("MainWindow", u"Open GitHub", None))
        self.actionToggleNavigation.setText(QCoreApplication.translate("MainWindow", u"Toggle Navigation", None))
        self.winTitle.setText(QCoreApplication.translate("MainWindow", u"SkyFall", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.mainTab), QCoreApplication.translate("MainWindow", u"SKYFALL", None))
        self.telegramUsernameEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Username", None))
        self.telegramAccountInfo.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Account (auto after download)", None))
        self.telegramUseProxyCheck.setText(QCoreApplication.translate("MainWindow", u"Use Proxy", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Safety Delays", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Member Delay(S)", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Pause(S)", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Max Requests", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Base Delay(S)", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"Collection Options", None))
        self.telegramDownloadMediaCheck.setText(QCoreApplication.translate("MainWindow", u"Download Media", None))
        self.telegramCollectMembersCheck.setText(QCoreApplication.translate("MainWindow", u"Collect Members", None))
        self.telegramCollectLinksCheck.setText(QCoreApplication.translate("MainWindow", u"Collect Links", None))
        self.telegramMultiAccCheck.setText(QCoreApplication.translate("MainWindow", u"Multi-Acc Mode", None))
        self.telegramDownloadStart.setText(QCoreApplication.translate("MainWindow", u"Run", None))
        self.telegramDownloadAvatarsBtn.setText(QCoreApplication.translate("MainWindow", u"Download Avatars", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.telegramDownloaderTab), QCoreApplication.translate("MainWindow", u"TELEGRAM DOWNLOADER", None))
        self.telegramAnalyzerLoadChannelsButton.setText(QCoreApplication.translate("MainWindow", u"Load Channels", None))

        __sortingEnabled = self.telegramChannelsList.isSortingEnabled()
        self.telegramChannelsList.setSortingEnabled(False)
        ___qlistwidgetitem = self.telegramChannelsList.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("MainWindow", u"All Channels", None))
        self.telegramChannelsList.setSortingEnabled(__sortingEnabled)

        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Graph Parameters", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Min replies", None))
        self.includeLinksCheck.setText(QCoreApplication.translate("MainWindow", u"Include Links", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"End", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.includeForwardingCheck.setText(QCoreApplication.translate("MainWindow", u"Include Forwarding", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("MainWindow", u"Output Formats", None))
        self.telegramAnalyzerHTMLCheck.setText(QCoreApplication.translate("MainWindow", u"HTML", None))
        self.telegramAnalyzerCSVCheck.setText(QCoreApplication.translate("MainWindow", u"CSV", None))
        self.telegramAnalyzerObsidianCheck.setText(QCoreApplication.translate("MainWindow", u"Obsidian", None))
        self.telegramAnalyzerPNGCheck.setText(QCoreApplication.translate("MainWindow", u"PNG", None))
        self.telegramAnalyzerGraphMLCheck.setText(QCoreApplication.translate("MainWindow", u"GraphML", None))
        self.telegramAnalyzerJSONCheck.setText(QCoreApplication.translate("MainWindow", u"JSON", None))
        self.checkBox_7.setText(QCoreApplication.translate("MainWindow", u"CheckBox", None))
        self.checkBox_8.setText(QCoreApplication.translate("MainWindow", u"CheckBox", None))
        self.runTelegramAnalyzerBtn.setText(QCoreApplication.translate("MainWindow", u"Run", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.telegramAnalyzerTab), QCoreApplication.translate("MainWindow", u"TELEGRAM ANALYZER", None))
        self.usernameScriptDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Script", None))
        self.usernameEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Username", None))
        self.searchUsernameButton.setText(QCoreApplication.translate("MainWindow", u"Search", None))
        self.maigretDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Maigret", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.usernameSearchTab), QCoreApplication.translate("MainWindow", u"USERNAME", None))
        self.mailEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Mail", None))
        self.startMailSearchButton.setText(QCoreApplication.translate("MainWindow", u"IntelX Search", None))
        self.startHibpCheckButton.setText(QCoreApplication.translate("MainWindow", u"HIBP Check", None))
        self.mailSearchDebug.setPlainText("")
        self.mailSearchDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"INTELX", None))
        self.hibpDebug.setPlainText("")
        self.hibpDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"HIBP", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.mailToolsTab), QCoreApplication.translate("MainWindow", u"MAIL", None))
        self.customDorkEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Custom Dork", None))
        self.dorkItButton.setText(QCoreApplication.translate("MainWindow", u"Dork", None))
        self.dorksCategorySearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Category Search", None))
        self.dorksListSearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Dork Search", None))
        self.dorksResultSearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Result Search", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.useSearxngCheck.setText(QCoreApplication.translate("MainWindow", u"Use SearXNG", None))
        self.useCustomDorkCheck.setText(QCoreApplication.translate("MainWindow", u"Cusom Dork", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.dorkingTab), QCoreApplication.translate("MainWindow", u"DORKING", None))
        self.serverLocationDebug.setPlaceholderText("")
        self.domainSubdomainsCheck.setText(QCoreApplication.translate("MainWindow", u"Subdomains Dorking", None))
        self.serverRobotsDebug.setPlaceholderText("")
        self.serverTlsDebug.setPlaceholderText("")
        self.serverWafDebug.setPlaceholderText("")
        self.domainLocationCheck.setText(QCoreApplication.translate("MainWindow", u"Server Location", None))
        self.domainDNSCheck.setText(QCoreApplication.translate("MainWindow", u"DNS", None))
        self.serverSubdomainsDebug.setDocumentTitle("")
        self.serverSubdomainsDebug.setPlainText("")
        self.serverSubdomainsDebug.setPlaceholderText("")
        self.domainHeadersCheck.setText(QCoreApplication.translate("MainWindow", u"Headers", None))
        self.domainNmapCheck.setText(QCoreApplication.translate("MainWindow", u"Open Ports", None))
        self.domainMalwareCheck.setText(QCoreApplication.translate("MainWindow", u"Malware", None))
        self.serverNmapDebug.setPlaceholderText("")
        self.domainWhoisCheck.setText(QCoreApplication.translate("MainWindow", u"Whois", None))
        self.securityTxtCheck.setText(QCoreApplication.translate("MainWindow", u"Security.txt", None))
        self.domainSSLCheck.setText(QCoreApplication.translate("MainWindow", u"SSL / TLS", None))
        self.serverDnsAnalyzeDebug.setPlaceholderText("")
        self.serverWhoisDebug.setPlaceholderText("")
        self.serverMalwareDebug.setPlaceholderText("")
        self.socialTagsCheck.setText(QCoreApplication.translate("MainWindow", u"Social Tags", None))
        self.cookiesCheck.setText(QCoreApplication.translate("MainWindow", u"Cookies", None))
        self.domainRobotsCheck.setText(QCoreApplication.translate("MainWindow", u"Robots", None))
        self.certTrCheck.setText(QCoreApplication.translate("MainWindow", u"Certificate Transparency ", None))
        self.serverUrlEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"URL", None))
        self.runUrlScanButton.setText(QCoreApplication.translate("MainWindow", u"Scan", None))
        self.domainsOnIpDebug.setPlaceholderText("")
        self.domainsOnIpCheck.setText(QCoreApplication.translate("MainWindow", u"Find domains on IP", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.webAnalyzerTab), QCoreApplication.translate("MainWindow", u"WEB", None))
        self.metadataDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"METADATA", None))
        self.stringsFileDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"STRINGS", None))
        self.fileVirustotalCheck.setText(QCoreApplication.translate("MainWindow", u"Check", None))
        self.virustotalFileDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"VIRUSTOTAL", None))
        self.fileMetadataCheck.setText(QCoreApplication.translate("MainWindow", u"Check", None))
        self.getMetadataButton.setText(QCoreApplication.translate("MainWindow", u"Analyze", None))
        self.fileStringsCheck.setText(QCoreApplication.translate("MainWindow", u"Check", None))
        self.metadataStatusLabel.setText(QCoreApplication.translate("MainWindow", u"DROP", None))
        self.cleanMetadataButton.setText(QCoreApplication.translate("MainWindow", u"Clean Metadata", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.metadataTab), QCoreApplication.translate("MainWindow", u"FILE ANALYZE", None))
        self.githubUserEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"GitHub Username", None))
        self.githubUserSearchBtn.setText(QCoreApplication.translate("MainWindow", u"User Info", None))
        self.githubRepoEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search Repositories", None))
        self.githubRepoSearchBtn.setText(QCoreApplication.translate("MainWindow", u"Search Repos", None))
        self.githubEmailEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Email search (org/domain/repo)", None))
        self.githubEmailSearchBtn.setText(QCoreApplication.translate("MainWindow", u"Search Emails", None))
        self.githubCommitEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Commit search (user/repo)", None))
        self.githubCommitSearchBtn.setText(QCoreApplication.translate("MainWindow", u"Search Commits", None))
        self.githubSecretEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Secret scan (org/repo)", None))
        self.githubSecretSearchBtn.setText(QCoreApplication.translate("MainWindow", u"Scan Secrets", None))
        self.githubDorkGroup.setTitle(QCoreApplication.translate("MainWindow", u"GitHub Dorking", None))
        self.githubDorkEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Dork query", None))
        self.githubDorkCodeCheck.setText(QCoreApplication.translate("MainWindow", u"Code", None))
        self.githubDorkCommitsCheck.setText(QCoreApplication.translate("MainWindow", u"Commits", None))
        self.githubDorkIssuesCheck.setText(QCoreApplication.translate("MainWindow", u"Issues", None))
        self.githubDorkReposCheck.setText(QCoreApplication.translate("MainWindow", u"Repos", None))
        self.githubDorkUsersCheck.setText(QCoreApplication.translate("MainWindow", u"Users", None))
        self.githubDorkSearchBtn.setText(QCoreApplication.translate("MainWindow", u"Dork", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.githubTab), QCoreApplication.translate("MainWindow", u"GITHUB", None))
        self.phoneNumberEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Phone number (+1234567890)", None))
        self.phoneRegionEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Region code (US, RU, DE... optional)", None))
        self.phoneParseBtn.setText(QCoreApplication.translate("MainWindow", u"Parse / Validate", None))
        self.phoneLookupBtn.setText(QCoreApplication.translate("MainWindow", u"Reverse Lookup", None))
        self.phoneLeakBtn.setText(QCoreApplication.translate("MainWindow", u"Check Leaks", None))
        self.phone7telBtn.setText(QCoreApplication.translate("MainWindow", u"7tel.ru Search", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.phoneTab), QCoreApplication.translate("MainWindow", u"PHONE", None))
        self.checkMacAddrButton.setText(QCoreApplication.translate("MainWindow", u"Check", None))
        self.macAddrEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Mac Addr", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.macAddrTab), QCoreApplication.translate("MainWindow", u"MAC ADDR", None))
        self.bcNetworkCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"TRON", None))
        self.bcNetworkCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"TON", None))
        self.bcNetworkCombo.setItemText(2, QCoreApplication.translate("MainWindow", u"ETH", None))
        self.bcNetworkCombo.setItemText(3, QCoreApplication.translate("MainWindow", u"BSC", None))
        self.bcNetworkCombo.setItemText(4, QCoreApplication.translate("MainWindow", u"BASE", None))
        self.bcNetworkCombo.setItemText(5, QCoreApplication.translate("MainWindow", u"SOL", None))
        self.bcNetworkCombo.setItemText(6, QCoreApplication.translate("MainWindow", u"BTC", None))
        self.bcNetworkCombo.setItemText(7, QCoreApplication.translate("MainWindow", u"LTC", None))
        self.bcNetworkCombo.setItemText(8, QCoreApplication.translate("MainWindow", u"DOGE", None))
        self.bcNetworkCombo.setItemText(9, QCoreApplication.translate("MainWindow", u"BCH", None))

        self.bcCoinCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"USDT", None))
        self.bcCoinCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"USDC", None))
        self.bcCoinCombo.setItemText(2, QCoreApplication.translate("MainWindow", u"BTC", None))
        self.bcCoinCombo.setItemText(3, QCoreApplication.translate("MainWindow", u"ETH", None))
        self.bcCoinCombo.setItemText(4, QCoreApplication.translate("MainWindow", u"TON", None))
        self.bcCoinCombo.setItemText(5, QCoreApplication.translate("MainWindow", u"SOL", None))
        self.bcCoinCombo.setItemText(6, QCoreApplication.translate("MainWindow", u"BNB", None))
        self.bcCoinCombo.setItemText(7, QCoreApplication.translate("MainWindow", u"LTC", None))
        self.bcCoinCombo.setItemText(8, QCoreApplication.translate("MainWindow", u"DOGE", None))
        self.bcCoinCombo.setItemText(9, QCoreApplication.translate("MainWindow", u"BCH", None))
        self.bcCoinCombo.setItemText(10, QCoreApplication.translate("MainWindow", u"NOT", None))
        self.bcCoinCombo.setItemText(11, QCoreApplication.translate("MainWindow", u"RAY", None))
        self.bcCoinCombo.setItemText(12, QCoreApplication.translate("MainWindow", u"JUP", None))

        self.bcDateEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Date DD.MM.YYYY or range DD.MM.YYYY-DD.MM.YYYY", None))
        self.bcTimeEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Time HH:MM (UTC)", None))
        self.bcTimeRangeCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"exact", None))
        self.bcTimeRangeCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"\u00b11min", None))
        self.bcTimeRangeCombo.setItemText(2, QCoreApplication.translate("MainWindow", u"\u00b15min", None))
        self.bcTimeRangeCombo.setItemText(3, QCoreApplication.translate("MainWindow", u"\u00b115min", None))
        self.bcTimeRangeCombo.setItemText(4, QCoreApplication.translate("MainWindow", u"custom", None))

        self.bcAmountEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Amount or range (e.g. 800 or 500-800)", None))
        self.bcMemoEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Memo (optional)", None))
        self.bcSearchButton.setText(QCoreApplication.translate("MainWindow", u"Search", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.blockchainTab), QCoreApplication.translate("MainWindow", u"BLOCKCHAIN", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"DROP", None))
        self.LSBDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"LSB", None))
        self.spectralAnalysisDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Spectral Analysis", None))
        self.EOIDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"EOI/EOD", None))
        self.tailDataDetectionDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Tail Data Detection", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.steganographyTab), QCoreApplication.translate("MainWindow", u"STEGANOGRAPHY", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"DROP", None))
        self.runS4FButton.setText(QCoreApplication.translate("MainWindow", u"Run", None))
        self.s4fSearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search", None))
        self.s4fTargetLabel.setText("")
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.s4facesTab), QCoreApplication.translate("MainWindow", u"SEARCH4FACES", None))
        self.entitySearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search", None))
        self.exportGraphButton.setText(QCoreApplication.translate("MainWindow", u"Export To JSON", None))
        self.importGraphButton.setText(QCoreApplication.translate("MainWindow", u"Import From JSON", None))
        self.graphClearButton.setText(QCoreApplication.translate("MainWindow", u"Clear All", None))
        self.graphAutoLayoutButton.setText(QCoreApplication.translate("MainWindow", u"Auto Layout", None))
        self.graphSearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search nodes...", None))
        self.graphClearFilterButton.setText(QCoreApplication.translate("MainWindow", u"Clear", None))
        self.nodeTitleEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Title", None))
        self.nodeContentEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Content", None))
        self.nodeEvidenceAddFileBtn.setText(QCoreApplication.translate("MainWindow", u"Add File", None))
        self.nodeEvidenceAddUrlBtn.setText(QCoreApplication.translate("MainWindow", u"Add URL", None))
        self.nodeEvidenceRemoveBtn.setText(QCoreApplication.translate("MainWindow", u"Remove", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.graphTab), QCoreApplication.translate("MainWindow", u"GRAPH", None))
        self.aiReportLangEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Lang", None))
        self.updateOllamaListButton.setText(QCoreApplication.translate("MainWindow", u"Update", None))
        self.aiReportDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"REPORT", None))
        self.generateReportButton.setText(QCoreApplication.translate("MainWindow", u"Generate Report", None))
        self.saveReportButton.setText(QCoreApplication.translate("MainWindow", u"Save Report", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.reportTab), QCoreApplication.translate("MainWindow", u"AI REPORT", None))
        self.pathToStorageEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Path to folder", None))
        self.tgApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram API KEY", None))
        self.telegramApiHashEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram API HASH", None))
        self.telegramPhoneEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram Phone Number", None))
        self.intelligentXApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"IntelligentX API KEY", None))
        self.hibpApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"HIBP API KEY", None))
        self.virustotalApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Virustotal", None))
        self.googleSafeApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Google Safe API KEY", None))
        self.ipinfoApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"IpInfo", None))
        self.githubTokenEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"GitHub Token split by ;", None))
        self.numverifyApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"NumVerify API Key", None))
        self.abstractapiApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"AbstractAPI API Key", None))
        self.trongridApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"TronGrid API Key", None))
        self.etherscanApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Etherscan API Key", None))
        self.bscscanApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"BscScan API Key", None))
        self.tonapiApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"TON API Key", None))
        self.heliusApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Helius API Key", None))
        self.lightThemeCheck.setText(QCoreApplication.translate("MainWindow", u"Light Theme", None))
        self.framelessCheck.setText(QCoreApplication.translate("MainWindow", u"Frameless Window", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("MainWindow", u"MCP Server", None))
        self.mcpStatusLabel.setText(QCoreApplication.translate("MainWindow", u"Stopped", None))
        self.mcpToggleButton.setText(QCoreApplication.translate("MainWindow", u"Start MCP Server", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.settingsTab), QCoreApplication.translate("MainWindow", u"SETTINGS", None))
        self.saveProxiesButton.setText(QCoreApplication.translate("MainWindow", u"Save Proxies", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.proxyTab), QCoreApplication.translate("MainWindow", u"PROXY", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuView.setTitle(QCoreApplication.translate("MainWindow", u"View", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
        self.menu_SkyFall.setTitle(QCoreApplication.translate("MainWindow", u" SkyFall", None))
    # retranslateUi

