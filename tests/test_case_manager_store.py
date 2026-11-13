"""Integration tests between CaseManager and the unified case store."""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.case_manager import CaseManager  # noqa: E402
from src.libs.graph_lib import GraphWidget  # noqa: E402

_app = QApplication.instance() or QApplication([])


class CaseManagerStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "case"
        self.gw = GraphWidget()
        self.manager = CaseManager(graph_widget=self.gw)
        self.manager.open_case_path(self.root)

    def tearDown(self):
        self.manager.case_store.close()
        self.gw.deleteLater()
        self._tmp.cleanup()

    def test_created_case_has_unified_store(self):
        self.assertEqual(self.manager.current_case_path, self.root.resolve())
        self.assertTrue((self.root / "case.db").is_file())
        self.assertTrue((self.root / "logs" / "requests").is_dir())
        self.assertTrue((self.root / "graph" / "versions").is_dir())

    def test_capture_screenshot_links_to_note(self):
        self.gw.resize(320, 200)
        self.gw.from_dict(
            {
                "nodes": [
                    {"id": "a", "title": "Alice", "entity_type": "Person"},
                ],
                "edges": [],
            }
        )
        note = self.manager.add_note("Screenshot note")
        attachment = self.manager.capture_screenshot(
            caption="Graph", note_id=note["id"]
        )

        self.assertIsNotNone(attachment)
        self.assertEqual(attachment["note_id"], note["id"])
        self.assertEqual(attachment["kind"], "screenshot")
        self.assertTrue(Path(attachment["path"]).is_file())
        self.assertGreater(Path(attachment["path"]).stat().st_size, 0)
        self.assertEqual(len(self.manager.get_note(note["id"])["attachments"]), 1)

    def test_graph_version_save_and_restore(self):
        self.gw.from_dict(
            {
                "nodes": [
                    {"id": "a", "title": "Alice", "entity_type": "Person"},
                    {"id": "b", "title": "Bob", "entity_type": "Person"},
                ],
                "edges": [{"source": "a", "target": "b"}],
            }
        )
        version = self.manager.save_graph_version(label="two people")
        self.assertIsNotNone(version)
        self.assertTrue(version["created"])
        self.assertEqual(version["nodes"], 2)

        self.gw.from_dict(
            {
                "nodes": [{"id": "c", "title": "Carol", "entity_type": "Person"}],
                "edges": [],
            }
        )
        self.assertEqual(len(self.gw.to_dict()["nodes"]), 1)

        restored = self.manager.restore_graph_version(version["id"])
        self.assertIsNotNone(restored)
        self.assertEqual(len(self.gw.to_dict()["nodes"]), 2)
        self.assertEqual(
            sorted(node["title"] for node in self.gw.to_dict()["nodes"]),
            ["Alice", "Bob"],
        )

        # Restoring is a normal undoable graph edit.
        self.assertTrue(self.gw.undo())
        self.assertEqual(
            [node["title"] for node in self.gw.to_dict()["nodes"]], ["Carol"]
        )

        kinds = [item["kind"] for item in self.manager.case_store.list_activity()]
        self.assertIn("graph_rollback", kinds)

    def test_restore_missing_version_returns_none(self):
        self.assertIsNone(self.manager.restore_graph_version(9999))

    def test_save_graph_version_without_widget_returns_none(self):
        manager = CaseManager(graph_widget=None)
        manager.open_case_path(Path(self._tmp.name) / "other")
        try:
            self.assertIsNone(manager.save_graph_version())
            self.assertIsNotNone(
                manager.save_graph_version({"nodes": [], "edges": []}, label="empty")
            )
        finally:
            manager.case_store.close()

    def test_case_summary_combines_path_and_stats(self):
        self.manager.add_note("Summary note")
        summary = self.manager.case_summary()
        self.assertEqual(summary["name"], "case")
        self.assertEqual(Path(summary["path"]), self.root.resolve())
        self.assertEqual(summary["notes"], 1)

    def test_wrappers_delegate_to_store(self):
        note = self.manager.add_note("Delegated", "Body", tags=["tag"])
        self.assertEqual(self.manager.get_note(note["id"])["body"], "Body")
        updated = self.manager.update_note(note["id"], body="New body")
        self.assertEqual(updated["body"], "New body")

        source = Path(self._tmp.name) / "file.txt"
        source.write_text("evidence", encoding="utf-8")
        attachment = self.manager.attach_file(
            source, caption="File", note_id=note["id"]
        )
        self.assertEqual(attachment["note_id"], note["id"])

        request = self.manager.log_request("whois", "example.com")
        self.assertEqual(request["module"], "whois")

        self.assertTrue(self.manager.delete_note(note["id"]))
        self.assertIsNone(self.manager.get_note(note["id"]))


if __name__ == "__main__":
    unittest.main()
