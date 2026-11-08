"""Regression tests for graph status text staying out of the layout."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QStatusBar

from src.libs.graph_lib import GraphWidget


class GraphStatusLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_status_message_does_not_create_status_bar_or_label(self):
        window = QMainWindow()
        graph = GraphWidget()
        window.setCentralWidget(graph)

        graph.status_message("Layout applied")

        self.assertIsNone(window.findChild(QStatusBar))
        self.assertIsNone(window.findChild(QLabel, "graphStatusLabel"))
        self.assertIsNone(graph._update_summary())
