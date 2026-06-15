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
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QDateTimeEdit, QDoubleSpinBox,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QSplitter, QTabWidget,
    QVBoxLayout, QWidget)

from src.ui.drop_widget import DropWidget

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1023, 839)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_22 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_22.setSpacing(0)
        self.verticalLayout_22.setObjectName(u"verticalLayout_22")
        self.verticalLayout_22.setContentsMargins(6, 6, 6, 6)
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(-1, 0, -1, -1)
        self.menuListWidget = QListWidget(self.centralwidget)
        self.menuListWidget.setObjectName(u"menuListWidget")
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

        self.appIconLabel = QLabel(self.mainTab)
        self.appIconLabel.setObjectName(u"appIconLabel")
        self.appIconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_21.addWidget(self.appIconLabel)

        self.winTitle = QLabel(self.mainTab)
        self.winTitle.setObjectName(u"winTitle")
        font = QFont()
        font.setBold(True)
        font.setItalic(True)
        self.winTitle.setFont(font)
        self.winTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_21.addWidget(self.winTitle)

        self.mainTabSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_21.addItem(self.mainTabSpacer)


        self.horizontalLayout_7.addLayout(self.verticalLayout_21)

        self.horizontalSpacer_4 = QSpacerItem(150, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_4)

        self.mainStackedWidget.addTab(self.mainTab, "")
        self.telegramToolsTab = QWidget()
        self.telegramToolsTab.setObjectName(u"telegramToolsTab")
        self.verticalLayout_2 = QVBoxLayout(self.telegramToolsTab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(self.telegramToolsTab)
        self.tabWidget.setObjectName(u"tabWidget")
        self.telegram_downloader_tab = QWidget()
        self.telegram_downloader_tab.setObjectName(u"telegram_downloader_tab")
        self.horizontalLayout_3 = QHBoxLayout(self.telegram_downloader_tab)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.downloaderSplitter = QSplitter(self.telegram_downloader_tab)
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

        self.tabWidget.addTab(self.telegram_downloader_tab, "")
        self.telegram_analyzer_tab = QWidget()
        self.telegram_analyzer_tab.setObjectName(u"telegram_analyzer_tab")
        self.verticalLayout_9 = QVBoxLayout(self.telegram_analyzer_tab)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.analyzerSplitter = QSplitter(self.telegram_analyzer_tab)
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

        self.tabWidget.addTab(self.telegram_analyzer_tab, "")

        self.verticalLayout_2.addWidget(self.tabWidget)

        self.mainStackedWidget.addTab(self.telegramToolsTab, "")
        self.usernameSearchTab = QWidget()
        self.usernameSearchTab.setObjectName(u"usernameSearchTab")
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

        self.verticalSpacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_19.addItem(self.verticalSpacer_6)

        self.mailSplitter.addWidget(self.mailSettingsSection)
        self.mailDebugSection = QWidget(self.mailSplitter)
        self.mailDebugSection.setObjectName(u"mailDebugSection")
        self.verticalLayout_20 = QVBoxLayout(self.mailDebugSection)
        self.verticalLayout_20.setObjectName(u"verticalLayout_20")
        self.verticalLayout_20.setContentsMargins(0, 0, 0, 0)
        self.mailSearchDebug = QPlainTextEdit(self.mailDebugSection)
        self.mailSearchDebug.setObjectName(u"mailSearchDebug")

        self.verticalLayout_20.addWidget(self.mailSearchDebug)

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
        self.useCustomDorkCheck = QCheckBox(self.groupBox_5)
        self.useCustomDorkCheck.setObjectName(u"useCustomDorkCheck")

        self.horizontalLayout_5.addWidget(self.useCustomDorkCheck)

        self.useSearxngCheck = QCheckBox(self.groupBox_5)
        self.useSearxngCheck.setObjectName(u"useSearxngCheck")

        self.horizontalLayout_5.addWidget(self.useSearxngCheck)

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

        self.gridLayout_2.addWidget(self.serverLocationDebug, 5, 3, 1, 1)

        self.domainDNSCheck = QCheckBox(self.webAnalyzerTab)
        self.domainDNSCheck.setObjectName(u"domainDNSCheck")
        self.domainDNSCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainDNSCheck, 2, 2, 1, 1)

        self.serverTlsDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverTlsDebug.setObjectName(u"serverTlsDebug")

        self.gridLayout_2.addWidget(self.serverTlsDebug, 5, 1, 1, 1)

        self.serverDnsAnalyzeDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverDnsAnalyzeDebug.setObjectName(u"serverDnsAnalyzeDebug")

        self.gridLayout_2.addWidget(self.serverDnsAnalyzeDebug, 3, 2, 1, 1)

        self.domainRobotsCheck = QCheckBox(self.webAnalyzerTab)
        self.domainRobotsCheck.setObjectName(u"domainRobotsCheck")
        self.domainRobotsCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainRobotsCheck, 6, 2, 1, 1)

        self.serverRobotsDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverRobotsDebug.setObjectName(u"serverRobotsDebug")

        self.gridLayout_2.addWidget(self.serverRobotsDebug, 7, 2, 1, 1)

        self.domainLocationCheck = QCheckBox(self.webAnalyzerTab)
        self.domainLocationCheck.setObjectName(u"domainLocationCheck")
        self.domainLocationCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainLocationCheck, 4, 3, 1, 1)

        self.serverUrlEdit = QLineEdit(self.webAnalyzerTab)
        self.serverUrlEdit.setObjectName(u"serverUrlEdit")

        self.gridLayout_2.addWidget(self.serverUrlEdit, 0, 1, 1, 3)

        self.domainNmapCheck = QCheckBox(self.webAnalyzerTab)
        self.domainNmapCheck.setObjectName(u"domainNmapCheck")
        self.domainNmapCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainNmapCheck, 2, 3, 1, 1)

        self.domainHeadersCheck = QCheckBox(self.webAnalyzerTab)
        self.domainHeadersCheck.setObjectName(u"domainHeadersCheck")
        self.domainHeadersCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainHeadersCheck, 6, 1, 1, 1)

        self.serverNmapDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverNmapDebug.setObjectName(u"serverNmapDebug")

        self.gridLayout_2.addWidget(self.serverNmapDebug, 3, 3, 1, 1)

        self.domainSubdomainsCheck = QCheckBox(self.webAnalyzerTab)
        self.domainSubdomainsCheck.setObjectName(u"domainSubdomainsCheck")
        self.domainSubdomainsCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainSubdomainsCheck, 2, 1, 1, 1)

        self.serverSubdomainsDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverSubdomainsDebug.setObjectName(u"serverSubdomainsDebug")

        self.gridLayout_2.addWidget(self.serverSubdomainsDebug, 3, 1, 1, 1)

        self.runUrlScanButton = QPushButton(self.webAnalyzerTab)
        self.runUrlScanButton.setObjectName(u"runUrlScanButton")

        self.gridLayout_2.addWidget(self.runUrlScanButton, 1, 1, 1, 3)

        self.domainSSLCheck = QCheckBox(self.webAnalyzerTab)
        self.domainSSLCheck.setObjectName(u"domainSSLCheck")
        self.domainSSLCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainSSLCheck, 4, 1, 1, 1)

        self.serverWafDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverWafDebug.setObjectName(u"serverWafDebug")

        self.gridLayout_2.addWidget(self.serverWafDebug, 7, 1, 1, 1)

        self.serverMalwareDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverMalwareDebug.setObjectName(u"serverMalwareDebug")

        self.gridLayout_2.addWidget(self.serverMalwareDebug, 7, 3, 1, 1)

        self.domainProgress = QProgressBar(self.webAnalyzerTab)
        self.domainProgress.setObjectName(u"domainProgress")
        self.domainProgress.setValue(0)

        self.gridLayout_2.addWidget(self.domainProgress, 8, 1, 1, 3)

        self.serverWhoisDebug = QPlainTextEdit(self.webAnalyzerTab)
        self.serverWhoisDebug.setObjectName(u"serverWhoisDebug")

        self.gridLayout_2.addWidget(self.serverWhoisDebug, 5, 2, 1, 1)

        self.domainMalwareCheck = QCheckBox(self.webAnalyzerTab)
        self.domainMalwareCheck.setObjectName(u"domainMalwareCheck")
        self.domainMalwareCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainMalwareCheck, 6, 3, 1, 1)

        self.domainWhoisCheck = QCheckBox(self.webAnalyzerTab)
        self.domainWhoisCheck.setObjectName(u"domainWhoisCheck")
        self.domainWhoisCheck.setChecked(True)

        self.gridLayout_2.addWidget(self.domainWhoisCheck, 4, 2, 1, 1)

        self.mainStackedWidget.addTab(self.webAnalyzerTab, "")
        self.metadataTab = QWidget()
        self.metadataTab.setObjectName(u"metadataTab")
        self.gridLayout_7 = QGridLayout(self.metadataTab)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.metadataFilePath = QLabel(self.metadataTab)
        self.metadataFilePath.setObjectName(u"metadataFilePath")
        self.metadataFilePath.setMaximumSize(QSize(400, 30))
        self.metadataFilePath.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout_7.addWidget(self.metadataFilePath, 1, 0, 1, 1)

        self.stringsFileDebug = QPlainTextEdit(self.metadataTab)
        self.stringsFileDebug.setObjectName(u"stringsFileDebug")

        self.gridLayout_7.addWidget(self.stringsFileDebug, 0, 3, 3, 1)

        self.metadataDebug = QPlainTextEdit(self.metadataTab)
        self.metadataDebug.setObjectName(u"metadataDebug")

        self.gridLayout_7.addWidget(self.metadataDebug, 0, 1, 3, 1)

        self.metadataFileDropWidget = DropWidget(self.metadataTab)
        self.metadataFileDropWidget.setObjectName(u"metadataFileDropWidget")
        self.metadataFileDropWidget.setMinimumSize(QSize(400, 0))
        self.metadataFileDropWidget.setMaximumSize(QSize(400, 16777215))
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


        self.gridLayout_7.addWidget(self.metadataFileDropWidget, 0, 0, 1, 1)

        self.getMetadataButton = QPushButton(self.metadataTab)
        self.getMetadataButton.setObjectName(u"getMetadataButton")
        self.getMetadataButton.setMaximumSize(QSize(400, 16777215))

        self.gridLayout_7.addWidget(self.getMetadataButton, 2, 0, 1, 1)

        self.virustotalFileDebug = QPlainTextEdit(self.metadataTab)
        self.virustotalFileDebug.setObjectName(u"virustotalFileDebug")

        self.gridLayout_7.addWidget(self.virustotalFileDebug, 0, 2, 3, 1)

        self.mainStackedWidget.addTab(self.metadataTab, "")
        self.graphTab = QWidget()
        self.graphTab.setObjectName(u"graphTab")
        self.verticalLayout_13 = QVBoxLayout(self.graphTab)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.gridLayout_6 = QGridLayout()
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.exportGraphButton = QPushButton(self.graphTab)
        self.exportGraphButton.setObjectName(u"exportGraphButton")

        self.gridLayout_6.addWidget(self.exportGraphButton, 1, 0, 1, 1)

        self.importGraphButton = QPushButton(self.graphTab)
        self.importGraphButton.setObjectName(u"importGraphButton")

        self.gridLayout_6.addWidget(self.importGraphButton, 1, 1, 1, 1)

        self.widget = QWidget(self.graphTab)
        self.widget.setObjectName(u"widget")

        self.gridLayout_6.addWidget(self.widget, 0, 0, 1, 1)


        self.verticalLayout_13.addLayout(self.gridLayout_6)

        self.mainStackedWidget.addTab(self.graphTab, "")
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

        self.virustotalApiKeyEdit = QLineEdit(self.settingsTab)
        self.virustotalApiKeyEdit.setObjectName(u"virustotalApiKeyEdit")

        self.verticalLayout_4.addWidget(self.virustotalApiKeyEdit)

        self.ipinfoApiKeyEdit = QLineEdit(self.settingsTab)
        self.ipinfoApiKeyEdit.setObjectName(u"ipinfoApiKeyEdit")

        self.verticalLayout_4.addWidget(self.ipinfoApiKeyEdit)

        self.lightThemeCheck = QCheckBox(self.settingsTab)
        self.lightThemeCheck.setObjectName(u"lightThemeCheck")

        self.verticalLayout_4.addWidget(self.lightThemeCheck)

        self.pushButton = QPushButton(self.settingsTab)
        self.pushButton.setObjectName(u"pushButton")

        self.verticalLayout_4.addWidget(self.pushButton)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_2)


        self.horizontalLayout.addLayout(self.verticalLayout_4)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.mainStackedWidget.addTab(self.settingsTab, "")

        self.horizontalLayout_6.addWidget(self.mainStackedWidget)


        self.verticalLayout_22.addLayout(self.horizontalLayout_6)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.mainStackedWidget.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.appIconLabel.setStyleSheet(QCoreApplication.translate("MainWindow", u"color: #82aaff;", None))
        self.winTitle.setText(QCoreApplication.translate("MainWindow", u"SkyFall", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.mainTab), QCoreApplication.translate("MainWindow", u"SKYFALL", None))
        self.telegramUsernameEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Username", None))
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
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.telegram_downloader_tab), QCoreApplication.translate("MainWindow", u"DOWNLOADER", None))
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
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.telegram_analyzer_tab), QCoreApplication.translate("MainWindow", u"ANALYZER", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.telegramToolsTab), QCoreApplication.translate("MainWindow", u"TELEGRAM", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.usernameSearchTab), QCoreApplication.translate("MainWindow", u"USERNAME", None))
        self.mailEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Mail", None))
        self.startMailSearchButton.setText(QCoreApplication.translate("MainWindow", u"Search", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.mailToolsTab), QCoreApplication.translate("MainWindow", u"MAIL", None))
        self.customDorkEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Custom Dork", None))
        self.dorkItButton.setText(QCoreApplication.translate("MainWindow", u"Dork", None))
        self.dorksCategorySearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Category Search", None))
        self.dorksListSearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Dork Search", None))
        self.dorksResultSearchEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Result Search", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.useCustomDorkCheck.setText(QCoreApplication.translate("MainWindow", u"Cusom Dork", None))
        self.useSearxngCheck.setText(QCoreApplication.translate("MainWindow", u"Use SearXNG", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.dorkingTab), QCoreApplication.translate("MainWindow", u"DORKING", None))
        self.serverLocationDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"SERVER LOCATION", None))
        self.domainDNSCheck.setText(QCoreApplication.translate("MainWindow", u"DNS", None))
        self.serverTlsDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"TLS", None))
        self.serverDnsAnalyzeDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"DNS", None))
        self.domainRobotsCheck.setText(QCoreApplication.translate("MainWindow", u"Robots", None))
        self.serverRobotsDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"ROBOTS", None))
        self.domainLocationCheck.setText(QCoreApplication.translate("MainWindow", u"Server Location", None))
        self.serverUrlEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"URL", None))
        self.domainNmapCheck.setText(QCoreApplication.translate("MainWindow", u"Open Ports", None))
        self.domainHeadersCheck.setText(QCoreApplication.translate("MainWindow", u"Headers", None))
        self.serverNmapDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"OPEN PORTS", None))
        self.domainSubdomainsCheck.setText(QCoreApplication.translate("MainWindow", u"Subdomains Dorking", None))
        self.serverSubdomainsDebug.setDocumentTitle("")
        self.serverSubdomainsDebug.setPlainText("")
        self.serverSubdomainsDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"SUBDOMAIN DORKING", None))
        self.runUrlScanButton.setText(QCoreApplication.translate("MainWindow", u"Scan", None))
        self.domainSSLCheck.setText(QCoreApplication.translate("MainWindow", u"SSL / TLS", None))
        self.serverWafDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"HEADERS", None))
        self.serverMalwareDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"MALWARE", None))
        self.serverWhoisDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"WHOIS", None))
        self.domainMalwareCheck.setText(QCoreApplication.translate("MainWindow", u"Malware", None))
        self.domainWhoisCheck.setText(QCoreApplication.translate("MainWindow", u"Whois", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.webAnalyzerTab), QCoreApplication.translate("MainWindow", u"WEB", None))
        self.metadataFilePath.setText(QCoreApplication.translate("MainWindow", u"File", None))
        self.stringsFileDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"STRINGS", None))
        self.metadataDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"METADATA", None))
        self.metadataStatusLabel.setText(QCoreApplication.translate("MainWindow", u"DROP", None))
        self.getMetadataButton.setText(QCoreApplication.translate("MainWindow", u"Analyze", None))
        self.virustotalFileDebug.setPlaceholderText(QCoreApplication.translate("MainWindow", u"VIRUSTOTAL", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.metadataTab), QCoreApplication.translate("MainWindow", u"FILE INFO", None))
        self.exportGraphButton.setText(QCoreApplication.translate("MainWindow", u"Export from DB", None))
        self.importGraphButton.setText(QCoreApplication.translate("MainWindow", u"Import to DB", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.graphTab), QCoreApplication.translate("MainWindow", u"GRAPH", None))
        self.saveProxiesButton.setText(QCoreApplication.translate("MainWindow", u"Save Proxies", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.proxyTab), QCoreApplication.translate("MainWindow", u"PROXY", None))
        self.pathToStorageEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Path to folder", None))
        self.tgApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram API KEY", None))
        self.telegramApiHashEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram API HASH", None))
        self.telegramPhoneEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram Phone Number", None))
        self.intelligentXApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"IntelligentX API KEY", None))
        self.virustotalApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Virustotal", None))
        self.ipinfoApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"IpInfo", None))
        self.lightThemeCheck.setText(QCoreApplication.translate("MainWindow", u"Light Theme", None))
        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.mainStackedWidget.setTabText(self.mainStackedWidget.indexOf(self.settingsTab), QCoreApplication.translate("MainWindow", u"SETTINGS", None))
    # retranslateUi

