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
    QSpacerItem, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1200, 647)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.mainTabsWidget = QTabWidget(self.centralwidget)
        self.mainTabsWidget.setObjectName(u"mainTabsWidget")
        self.mainTab = QWidget()
        self.mainTab.setObjectName(u"mainTab")
        self.mainTabLayout = QVBoxLayout(self.mainTab)
        self.mainTabLayout.setObjectName(u"mainTabLayout")
        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.mainTabLayout.addItem(self.verticalSpacer_5)

        self.appIconLabel = QLabel(self.mainTab)
        self.appIconLabel.setObjectName(u"appIconLabel")
        self.appIconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mainTabLayout.addWidget(self.appIconLabel)

        self.winTitle = QLabel(self.mainTab)
        self.winTitle.setObjectName(u"winTitle")
        self.winTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mainTabLayout.addWidget(self.winTitle)

        self.mainTabSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.mainTabLayout.addItem(self.mainTabSpacer)

        self.mainTabsWidget.addTab(self.mainTab, "")
        self.telegram_tools_tab = QWidget()
        self.telegram_tools_tab.setObjectName(u"telegram_tools_tab")
        self.verticalLayout_2 = QVBoxLayout(self.telegram_tools_tab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.tabWidget = QTabWidget(self.telegram_tools_tab)
        self.tabWidget.setObjectName(u"tabWidget")
        self.telegram_downloader_tab = QWidget()
        self.telegram_downloader_tab.setObjectName(u"telegram_downloader_tab")
        self.horizontalLayout_3 = QHBoxLayout(self.telegram_downloader_tab)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.telegramUsernameEdit = QLineEdit(self.telegram_downloader_tab)
        self.telegramUsernameEdit.setObjectName(u"telegramUsernameEdit")

        self.verticalLayout_5.addWidget(self.telegramUsernameEdit)

        self.telegramUseProxyCheck = QCheckBox(self.telegram_downloader_tab)
        self.telegramUseProxyCheck.setObjectName(u"telegramUseProxyCheck")

        self.verticalLayout_5.addWidget(self.telegramUseProxyCheck)

        self.groupBox_2 = QGroupBox(self.telegram_downloader_tab)
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

        self.groupBox = QGroupBox(self.telegram_downloader_tab)
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

        self.telegramDownloadStart = QPushButton(self.telegram_downloader_tab)
        self.telegramDownloadStart.setObjectName(u"telegramDownloadStart")

        self.verticalLayout_5.addWidget(self.telegramDownloadStart)

        self.telegramDownloadProgress = QProgressBar(self.telegram_downloader_tab)
        self.telegramDownloadProgress.setObjectName(u"telegramDownloadProgress")
        self.telegramDownloadProgress.setValue(24)

        self.verticalLayout_5.addWidget(self.telegramDownloadProgress)


        self.horizontalLayout_3.addLayout(self.verticalLayout_5)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, -1, -1, -1)
        self.telegramDownloaderDebug = QPlainTextEdit(self.telegram_downloader_tab)
        self.telegramDownloaderDebug.setObjectName(u"telegramDownloaderDebug")
        self.telegramDownloaderDebug.setReadOnly(True)

        self.verticalLayout_6.addWidget(self.telegramDownloaderDebug)


        self.horizontalLayout_3.addLayout(self.verticalLayout_6)

        self.tabWidget.addTab(self.telegram_downloader_tab, "")
        self.telegram_analyzer_tab = QWidget()
        self.telegram_analyzer_tab.setObjectName(u"telegram_analyzer_tab")
        self.verticalLayout_9 = QVBoxLayout(self.telegram_analyzer_tab)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.telegramAnalyzerLoadChannelsButton = QPushButton(self.telegram_analyzer_tab)
        self.telegramAnalyzerLoadChannelsButton.setObjectName(u"telegramAnalyzerLoadChannelsButton")

        self.gridLayout_2.addWidget(self.telegramAnalyzerLoadChannelsButton, 0, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.telegram_analyzer_tab)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_10 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.label_6 = QLabel(self.groupBox_3)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_3.addWidget(self.label_6, 3, 0, 1, 1)

        self.label_5 = QLabel(self.groupBox_3)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_3.addWidget(self.label_5, 0, 0, 1, 1)

        self.label_7 = QLabel(self.groupBox_3)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_3.addWidget(self.label_7, 4, 0, 1, 1)

        self.telegramAnalyzerStartDate = QDateTimeEdit(self.groupBox_3)
        self.telegramAnalyzerStartDate.setObjectName(u"telegramAnalyzerStartDate")

        self.gridLayout_3.addWidget(self.telegramAnalyzerStartDate, 3, 1, 1, 1)

        self.telegramAnalyzerMinReplies = QSpinBox(self.groupBox_3)
        self.telegramAnalyzerMinReplies.setObjectName(u"telegramAnalyzerMinReplies")

        self.gridLayout_3.addWidget(self.telegramAnalyzerMinReplies, 0, 1, 1, 1)

        self.telegramAnalyzerEndDate = QDateTimeEdit(self.groupBox_3)
        self.telegramAnalyzerEndDate.setObjectName(u"telegramAnalyzerEndDate")

        self.gridLayout_3.addWidget(self.telegramAnalyzerEndDate, 4, 1, 1, 1)

        self.includeForwardingCheck = QCheckBox(self.groupBox_3)
        self.includeForwardingCheck.setObjectName(u"includeForwardingCheck")

        self.gridLayout_3.addWidget(self.includeForwardingCheck, 1, 0, 1, 2)

        self.includeLinksCheck = QCheckBox(self.groupBox_3)
        self.includeLinksCheck.setObjectName(u"includeLinksCheck")

        self.gridLayout_3.addWidget(self.includeLinksCheck, 2, 0, 1, 2)


        self.verticalLayout_10.addLayout(self.gridLayout_3)


        self.gridLayout_2.addWidget(self.groupBox_3, 2, 0, 1, 1)

        self.telegramAnalyzerDebug = QPlainTextEdit(self.telegram_analyzer_tab)
        self.telegramAnalyzerDebug.setObjectName(u"telegramAnalyzerDebug")
        self.telegramAnalyzerDebug.setReadOnly(True)

        self.gridLayout_2.addWidget(self.telegramAnalyzerDebug, 0, 1, 7, 1)

        self.telegramAnalyzerProgress = QProgressBar(self.telegram_analyzer_tab)
        self.telegramAnalyzerProgress.setObjectName(u"telegramAnalyzerProgress")
        self.telegramAnalyzerProgress.setValue(24)

        self.gridLayout_2.addWidget(self.telegramAnalyzerProgress, 6, 0, 1, 1)

        self.telegramChannelsList = QListWidget(self.telegram_analyzer_tab)
        QListWidgetItem(self.telegramChannelsList)
        self.telegramChannelsList.setObjectName(u"telegramChannelsList")

        self.gridLayout_2.addWidget(self.telegramChannelsList, 1, 0, 1, 1)

        self.groupBox_4 = QGroupBox(self.telegram_analyzer_tab)
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


        self.gridLayout_2.addWidget(self.groupBox_4, 3, 0, 1, 1)

        self.runTelegramAnalyzerBtn = QPushButton(self.telegram_analyzer_tab)
        self.runTelegramAnalyzerBtn.setObjectName(u"runTelegramAnalyzerBtn")

        self.gridLayout_2.addWidget(self.runTelegramAnalyzerBtn, 5, 0, 1, 1)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_4, 4, 0, 1, 1)


        self.verticalLayout_9.addLayout(self.gridLayout_2)

        self.tabWidget.addTab(self.telegram_analyzer_tab, "")

        self.verticalLayout_2.addWidget(self.tabWidget)

        self.mainTabsWidget.addTab(self.telegram_tools_tab, "")
        self.mail_tools_tab = QWidget()
        self.mail_tools_tab.setObjectName(u"mail_tools_tab")
        self.mainTabsWidget.addTab(self.mail_tools_tab, "")
        self.dorkingTab = QWidget()
        self.dorkingTab.setObjectName(u"dorkingTab")
        self.verticalLayout_12 = QVBoxLayout(self.dorkingTab)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.gridLayout_5 = QGridLayout()
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.label_9 = QLabel(self.dorkingTab)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout_5.addWidget(self.label_9, 0, 1, 1, 1)

        self.label_8 = QLabel(self.dorkingTab)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout_5.addWidget(self.label_8, 0, 0, 1, 1)

        self.dorksResult = QPlainTextEdit(self.dorkingTab)
        self.dorksResult.setObjectName(u"dorksResult")

        self.gridLayout_5.addWidget(self.dorksResult, 1, 2, 1, 1)

        self.dorksList = QListWidget(self.dorkingTab)
        self.dorksList.setObjectName(u"dorksList")

        self.gridLayout_5.addWidget(self.dorksList, 1, 1, 1, 1)

        self.dorksCategoryList = QListWidget(self.dorkingTab)
        QListWidgetItem(self.dorksCategoryList)
        QListWidgetItem(self.dorksCategoryList)
        QListWidgetItem(self.dorksCategoryList)
        self.dorksCategoryList.setObjectName(u"dorksCategoryList")

        self.gridLayout_5.addWidget(self.dorksCategoryList, 1, 0, 1, 1)

        self.dorkItButton = QPushButton(self.dorkingTab)
        self.dorkItButton.setObjectName(u"dorkItButton")

        self.gridLayout_5.addWidget(self.dorkItButton, 2, 2, 1, 1)

        self.label_10 = QLabel(self.dorkingTab)
        self.label_10.setObjectName(u"label_10")

        self.gridLayout_5.addWidget(self.label_10, 0, 2, 1, 1)

        self.customDorkEdit = QLineEdit(self.dorkingTab)
        self.customDorkEdit.setObjectName(u"customDorkEdit")

        self.gridLayout_5.addWidget(self.customDorkEdit, 2, 0, 1, 2)


        self.verticalLayout_12.addLayout(self.gridLayout_5)

        self.mainTabsWidget.addTab(self.dorkingTab, "")
        self.proxy_tab = QWidget()
        self.proxy_tab.setObjectName(u"proxy_tab")
        self.verticalLayout_3 = QVBoxLayout(self.proxy_tab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.proxyListEdit = QPlainTextEdit(self.proxy_tab)
        self.proxyListEdit.setObjectName(u"proxyListEdit")

        self.horizontalLayout_2.addWidget(self.proxyListEdit)


        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.saveProxiesButton = QPushButton(self.proxy_tab)
        self.saveProxiesButton.setObjectName(u"saveProxiesButton")

        self.verticalLayout_3.addWidget(self.saveProxiesButton)

        self.mainTabsWidget.addTab(self.proxy_tab, "")
        self.global_serrings_tab = QWidget()
        self.global_serrings_tab.setObjectName(u"global_serrings_tab")
        self.horizontalLayout = QHBoxLayout(self.global_serrings_tab)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)

        self.pathToStorageEdit = QLineEdit(self.global_serrings_tab)
        self.pathToStorageEdit.setObjectName(u"pathToStorageEdit")

        self.verticalLayout_4.addWidget(self.pathToStorageEdit)

        self.tgApiKeyEdit = QLineEdit(self.global_serrings_tab)
        self.tgApiKeyEdit.setObjectName(u"tgApiKeyEdit")

        self.verticalLayout_4.addWidget(self.tgApiKeyEdit)

        self.telegramApiHashEdit = QLineEdit(self.global_serrings_tab)
        self.telegramApiHashEdit.setObjectName(u"telegramApiHashEdit")

        self.verticalLayout_4.addWidget(self.telegramApiHashEdit)

        self.telegramPhoneEdit = QLineEdit(self.global_serrings_tab)
        self.telegramPhoneEdit.setObjectName(u"telegramPhoneEdit")

        self.verticalLayout_4.addWidget(self.telegramPhoneEdit)

        self.intelligentXApiKeyEdit = QLineEdit(self.global_serrings_tab)
        self.intelligentXApiKeyEdit.setObjectName(u"intelligentXApiKeyEdit")

        self.verticalLayout_4.addWidget(self.intelligentXApiKeyEdit)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_2)


        self.horizontalLayout.addLayout(self.verticalLayout_4)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.mainTabsWidget.addTab(self.global_serrings_tab, "")

        self.verticalLayout.addWidget(self.mainTabsWidget)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.mainTabsWidget.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.appIconLabel.setStyleSheet(QCoreApplication.translate("MainWindow", u"color: #82aaff;", None))
        self.winTitle.setText(QCoreApplication.translate("MainWindow", u"SkyFall", None))
        self.mainTabsWidget.setTabText(self.mainTabsWidget.indexOf(self.mainTab), QCoreApplication.translate("MainWindow", u"SKYFALL", None))
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
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Graph Parameters", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Min replies", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"End", None))
        self.includeForwardingCheck.setText(QCoreApplication.translate("MainWindow", u"Include Forwarding", None))
        self.includeLinksCheck.setText(QCoreApplication.translate("MainWindow", u"Include Links", None))

        __sortingEnabled = self.telegramChannelsList.isSortingEnabled()
        self.telegramChannelsList.setSortingEnabled(False)
        ___qlistwidgetitem = self.telegramChannelsList.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("MainWindow", u"All Channels", None))
        self.telegramChannelsList.setSortingEnabled(__sortingEnabled)

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
        self.mainTabsWidget.setTabText(self.mainTabsWidget.indexOf(self.telegram_tools_tab), QCoreApplication.translate("MainWindow", u"TELEGRAM", None))
        self.mainTabsWidget.setTabText(self.mainTabsWidget.indexOf(self.mail_tools_tab), QCoreApplication.translate("MainWindow", u"MAIL", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Dorks", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Category", None))

        __sortingEnabled1 = self.dorksCategoryList.isSortingEnabled()
        self.dorksCategoryList.setSortingEnabled(False)
        ___qlistwidgetitem1 = self.dorksCategoryList.item(0)
        ___qlistwidgetitem1.setText(QCoreApplication.translate("MainWindow", u"ADMIN PANELS", None))
        ___qlistwidgetitem2 = self.dorksCategoryList.item(1)
        ___qlistwidgetitem2.setText(QCoreApplication.translate("MainWindow", u".ENV", None))
        ___qlistwidgetitem3 = self.dorksCategoryList.item(2)
        ___qlistwidgetitem3.setText(QCoreApplication.translate("MainWindow", u"DB", None))
        self.dorksCategoryList.setSortingEnabled(__sortingEnabled1)

        self.dorkItButton.setText(QCoreApplication.translate("MainWindow", u"Dork", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Result", None))
        self.customDorkEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Custom Dork", None))
        self.mainTabsWidget.setTabText(self.mainTabsWidget.indexOf(self.dorkingTab), QCoreApplication.translate("MainWindow", u"DORKING", None))
        self.saveProxiesButton.setText(QCoreApplication.translate("MainWindow", u"Save Proxies", None))
        self.mainTabsWidget.setTabText(self.mainTabsWidget.indexOf(self.proxy_tab), QCoreApplication.translate("MainWindow", u"PROXY", None))
        self.pathToStorageEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Path to folder", None))
        self.tgApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram API KEY", None))
        self.telegramApiHashEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram API HASH", None))
        self.telegramPhoneEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Telegram Phone Number", None))
        self.intelligentXApiKeyEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"IntelligentX API KEY", None))
        self.mainTabsWidget.setTabText(self.mainTabsWidget.indexOf(self.global_serrings_tab), QCoreApplication.translate("MainWindow", u"SETTINGS", None))
    # retranslateUi

