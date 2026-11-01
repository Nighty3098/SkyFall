import asyncio
import os
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow

from main import MainWindow

_app = QApplication.instance() or QApplication([])


class MainWindowShutdownTest(unittest.IsolatedAsyncioTestCase):
    async def test_close_waits_for_file_analyzer_cleanup(self):
        closed = asyncio.Event()

        class FileAnalyzer:
            async def close(self):
                await asyncio.sleep(0.01)
                closed.set()

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.fileAnalyzer = FileAnalyzer()
        window.mcpController = Mock()
        event = QCloseEvent()

        MainWindow.closeEvent(window, event)

        self.assertFalse(event.isAccepted())
        self.assertFalse(closed.is_set())
        await window._close_task

        self.assertTrue(closed.is_set())
        self.assertTrue(window._shutdown_complete)
        window.mcpController.cleanup.assert_called_once()
        window.deleteLater()
        _app.processEvents()


if __name__ == "__main__":
    unittest.main()
