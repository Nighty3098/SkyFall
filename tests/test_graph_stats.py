"""Tests for the graph statistics panel and bridge summary."""

import os
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QWidget  # noqa: E402

from src.controllers.graph_stats_controller import GraphStatsController  # noqa: E402
from src.graph_bridge import GraphBridgeServer  # noqa: E402
from src.libs.graph_lib import GraphWidget, NodeItem  # noqa: E402

_app = QApplication.instance() or QApplication([])

ROOT = Path(__file__).resolve().parents[1]


class _FakeStatsUi(QWidget):
    """The subset of ``form.ui`` widgets the statistics controller writes to."""

    def __init__(self):
        super().__init__()
        for name in ("graphStatsSummary", "graphStatsMeta"):
            setattr(self, name, QLabel(self))
        for name in ("graphStatsEntityList", "graphStatsRelationshipList"):
            setattr(self, name, QListWidget(self))


class GraphStatsControllerTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.gw._status_timer.stop()
        self.ui = _FakeStatsUi()
        self.controller = GraphStatsController(self.ui, self.gw)

    def _add(self, x, title, etype="Person", evidence=None):
        node = self.gw.add_node(QPointF(x, 0), etype)
        node.title = title
        node.evidence = list(evidence or [])
        return node

    def test_empty_graph(self):
        stats = self.controller.refresh()
        self.assertEqual(stats["total_nodes"], 0)
        self.assertEqual(stats["total_edges"], 0)
        self.assertEqual(stats["entity_types"], {})
        self.assertEqual(stats["relationship_types"], {})
        self.assertEqual(self.ui.graphStatsEntityList.count(), 1)

    def test_counts_entities_relationships_and_evidence(self):
        alice = self._add(0, "Alice", "Person", ["/tmp/a.png"])
        domain = self._add(220, "alice.dev", "Domain")
        self._add(440, "bob", "Person")
        self.gw.add_edge(alice, domain, source_port="right", target_port="left")

        stats = self.controller.refresh()

        self.assertEqual(stats["total_nodes"], 3)
        self.assertEqual(stats["total_edges"], 1)
        self.assertEqual(stats["entity_types"], {"Person": 2, "Domain": 1})
        self.assertEqual(stats["relationship_types"], {"associated_with": 1})
        self.assertEqual(stats["evidence"], 1)
        self.assertEqual(stats["isolated_nodes"], 1)
        self.assertEqual(
            self.ui.graphStatsSummary.text(), "3 nodes \u00b7 1 edges \u00b7 1 evidence"
        )

        first = self.ui.graphStatsEntityList.item(0)
        self.assertIn("Person", first.text())
        self.assertIn("2", first.text())
        self.assertIn("67%", first.text())

    def test_visible_and_selected_counts(self):
        first = self._add(0, "Alice")
        second = self._add(220, "Bob")
        first.setSelected(True)
        second.setVisible(False)

        stats = self.controller.refresh()

        self.assertEqual(stats["selected_nodes"], 1)
        self.assertEqual(stats["visible_nodes"], 1)
        self.assertIn("1 of 2 visible", self.ui.graphStatsMeta.text())


class FormUiStatsWidgetsTest(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(ROOT / "resources" / "form.ui").getroot()

    def _widget(self, name):
        return self.root.find(f".//widget[@name='{name}']")

    def test_statistics_panel_is_built_from_native_widgets(self):
        panel = self._widget("graphStatsPanel")
        self.assertIsNotNone(panel)
        self.assertEqual(panel.get("class"), "QGroupBox")

        expected = {
            "graphStatsSummary": "QLabel",
            "graphStatsMeta": "QLabel",
            "graphStatsEntitiesCaption": "QLabel",
            "graphStatsRelationshipsCaption": "QLabel",
            "graphStatsEntityList": "QListWidget",
            "graphStatsRelationshipList": "QListWidget",
        }
        for name, class_name in expected.items():
            widget = self._widget(name)
            self.assertIsNotNone(widget, name)
            self.assertEqual(widget.get("class"), class_name)

    def test_no_custom_statistics_widget_is_registered(self):
        custom = {item.findtext("class") for item in self.root.iter("customwidget")}
        self.assertNotIn("GraphStatsPanel", custom)


class GraphBridgeSummaryTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.gw._status_timer.stop()
        self.server = GraphBridgeServer()
        self.server._graph_widget = self.gw
        self.server._node_item_cls = NodeItem

    def _add(self, x, title, etype="Person"):
        node = self.gw.add_node(QPointF(x, 0), etype)
        node.title = title
        return node

    def test_summary_includes_relationship_and_visibility_stats(self):
        first = self._add(0, "Alice")
        second = self._add(220, "alice.dev", "Domain")
        first.evidence.append("/tmp/evidence.png")
        self.gw.add_edge(first, second)

        summary = self.server._graph_summary()

        self.assertEqual(summary["total_nodes"], 2)
        self.assertEqual(summary["total_edges"], 1)
        self.assertEqual(summary["entity_types"], {"Person": 1, "Domain": 1})
        self.assertEqual(summary["relationship_types"], {"associated_with": 1})
        self.assertEqual(summary["total_evidence"], 1)
        self.assertEqual(summary["visible_nodes"], 2)
        self.assertEqual(summary["isolated_nodes"], 0)


if __name__ == "__main__":
    unittest.main()
