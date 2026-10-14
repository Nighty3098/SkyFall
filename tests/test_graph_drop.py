"""Tests for dropping graph files onto the canvas / graph tab."""

import json
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QDragEnterEvent, QDropEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from src.libs.graph_lib import (  # noqa: E402
    EdgeItem,
    GraphDropFilter,
    GraphWidget,
    NodeItem,
)

_app = QApplication.instance() or QApplication([])

_GRAPH_DOC = {
    "nodes": [
        {"id": "1", "title": "alpha.com", "entity_type": "Domain", "x": 0, "y": 0},
        {"id": "2", "title": "carol", "entity_type": "Person", "x": 300, "y": 0},
    ],
    "edges": [{"source": "1", "target": "2"}],
}


class GraphFileDropTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.tmp = tempfile.TemporaryDirectory()
        self.json_path = os.path.join(self.tmp.name, "graph.json")
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(_GRAPH_DOC, f)
        self.txt_path = os.path.join(self.tmp.name, "notes.txt")
        with open(self.txt_path, "w", encoding="utf-8") as f:
            f.write("hello")

    def tearDown(self):
        self.tmp.cleanup()

    def _nodes(self):
        return [i for i in self.gw._scene.items() if isinstance(i, NodeItem)]

    def _edges(self):
        return [i for i in self.gw._scene.items() if isinstance(i, EdgeItem)]

    def _mime_for(self, path):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        return mime

    def _drag_enter(self, mime):
        event = QDragEnterEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        event.setAccepted(False)
        self.gw.dragEnterEvent(event)
        return event

    def _drop(self, mime, target=None):
        event = QDropEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        (target or self.gw).dropEvent(event)
        return event

    def test_detects_supported_file(self):
        mime = self._mime_for(self.json_path)
        self.assertEqual(self.gw._dropped_graph_file(mime), self.json_path)

    def test_ignores_unsupported_file(self):
        mime = self._mime_for(self.txt_path)
        self.assertIsNone(self.gw._dropped_graph_file(mime))

    def test_ignores_text_only_mime(self):
        mime = QMimeData()
        mime.setText("not a file")
        self.assertIsNone(self.gw._dropped_graph_file(mime))

    def test_load_graph_path_populates_scene(self):
        self.assertTrue(self.gw.load_graph_path(self.json_path))
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(len(self._edges()), 1)

    def test_load_graph_path_reports_failure(self):
        bad = os.path.join(self.tmp.name, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("{not json")
        self.assertFalse(self.gw.load_graph_path(bad))
        self.assertEqual(len(self._nodes()), 0)

    def test_drop_event_loads_file(self):
        mime = self._mime_for(self.json_path)
        event = self._drop(mime)
        self.assertTrue(event.isAccepted())
        self.assertEqual(len(self._nodes()), 2)

    def test_drag_enter_accepts_supported_file(self):
        mime = self._mime_for(self.json_path)
        self.assertTrue(self._drag_enter(mime).isAccepted())

    def test_drag_enter_rejects_unsupported_file(self):
        mime = self._mime_for(self.txt_path)
        self.assertFalse(self._drag_enter(mime).isAccepted())

    def test_drop_filter_loads_supported_file(self):
        host = QWidget()
        filt = GraphDropFilter(self.gw, host)
        mime = self._mime_for(self.json_path)
        event = QDropEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.assertTrue(filt.eventFilter(host, event))
        self.assertEqual(len(self._nodes()), 2)

    def test_drop_filter_ignores_other_drags(self):
        host = QWidget()
        filt = GraphDropFilter(self.gw, host)
        mime = QMimeData()
        mime.setText("Domain")
        event = QDropEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.assertFalse(filt.eventFilter(host, event))
        self.assertEqual(len(self._nodes()), 0)


if __name__ == "__main__":
    unittest.main()
