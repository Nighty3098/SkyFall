"""Tests for the SQLite-backed unified case store."""

import tempfile
import unittest
from pathlib import Path

from src.modules.case_store import CaseStore


class CaseStoreTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "case"
        self.store = CaseStore(self.root)

    def tearDown(self):
        self.store.close()
        self._tmp.cleanup()


class NotesTest(CaseStoreTestBase):
    def test_create_read_update_and_delete_note(self):
        note = self.store.create_note(
            "First lead", "Body about **Alice**", tags=["alice", "lead", "alice"]
        )
        self.assertTrue(note["id"])
        self.assertEqual(note["title"], "First lead")
        self.assertEqual(note["tags"], ["alice", "lead"])

        fetched = self.store.get_note(note["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["body"], "Body about **Alice**")
        self.assertEqual(fetched["attachments"], [])

        updated = self.store.update_note(note["id"], body="Updated body")
        self.assertEqual(updated["body"], "Updated body")
        self.assertEqual(updated["title"], "First lead")

        self.assertTrue(self.store.delete_note(note["id"]))
        self.assertIsNone(self.store.get_note(note["id"]))
        self.assertFalse(self.store.delete_note("missing"))

    def test_empty_title_and_string_tags(self):
        note = self.store.create_note("   ", tags="one; two, one")
        self.assertEqual(note["title"], "Untitled note")
        self.assertEqual(note["tags"], ["one", "two"])

    def test_list_notes_includes_attachment_count(self):
        note = self.store.create_note("With evidence")
        self.store.add_screenshot(b"png-bytes", note_id=note["id"])
        listed = self.store.list_notes()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["attachment_count"], 1)

    def test_search_matches_notes_requests_and_attachments(self):
        self.store.create_note("Target profile", "Located in Berlin")
        self.store.log_request("whois", "example.com", response_body="Registrar ACME")
        self.store.add_screenshot(b"data", caption="Berlin map", filename="berlin.png")

        results = self.store.search("Berlin")
        self.assertEqual(len(results["notes"]), 1)
        self.assertEqual(len(results["attachments"]), 1)

        by_body = self.store.search("Registrar")
        self.assertEqual(len(by_body["requests"]), 1)


class AttachmentsTest(CaseStoreTestBase):
    def test_screenshot_is_copied_and_linked_to_note(self):
        note = self.store.create_note("Screenshot owner")
        attachment = self.store.add_screenshot(
            b"fake-png", caption="Graph view", note_id=note["id"], filename="graph.png"
        )
        self.assertEqual(attachment["kind"], "screenshot")
        self.assertEqual(attachment["note_id"], note["id"])
        self.assertEqual(attachment["mime"], "image/png")
        self.assertEqual(attachment["caption"], "Graph view")
        self.assertTrue(Path(attachment["path"]).is_file())
        self.assertEqual(Path(attachment["path"]).parent, self.root / "screenshots")
        self.assertEqual(Path(attachment["path"]).read_bytes(), b"fake-png")

        fetched = self.store.get_note(note["id"])
        self.assertEqual(len(fetched["attachments"]), 1)

    def test_screenshot_generates_png_name_when_missing_suffix(self):
        attachment = self.store.add_screenshot(b"x", filename="capture")
        self.assertTrue(attachment["original_name"].endswith(".png"))

    def test_duplicate_filename_does_not_overwrite(self):
        first = self.store.add_screenshot(b"one", filename="same.png")
        second = self.store.add_screenshot(b"two", filename="same.png")
        self.assertNotEqual(first["path"], second["path"])
        self.assertEqual(Path(first["path"]).read_bytes(), b"one")
        self.assertEqual(Path(second["path"]).read_bytes(), b"two")

    def test_attachment_copy_and_reference_modes(self):
        source = Path(self._tmp.name) / "evidence.txt"
        source.write_text("evidence", encoding="utf-8")

        copied = self.store.add_attachment(source, caption="copied")
        self.assertIsNotNone(copied)
        self.assertNotEqual(Path(copied["path"]), source)
        self.assertEqual(Path(copied["path"]).read_bytes(), b"evidence")

        referenced = self.store.add_attachment(source, copy=False)
        self.assertEqual(Path(referenced["path"]), source.resolve())

        self.assertIsNone(self.store.add_attachment(self.root / "missing.txt"))

    def test_list_and_delete_attachments(self):
        note = self.store.create_note("Owner")
        screenshot = self.store.add_screenshot(b"x", note_id=note["id"])
        source = Path(self._tmp.name) / "file.pdf"
        source.write_bytes(b"%PDF")
        file_attachment = self.store.add_attachment(source)

        self.assertEqual(len(self.store.list_attachments(note_id=note["id"])), 1)
        self.assertEqual(len(self.store.list_attachments(kind="screenshot")), 1)
        self.assertEqual(len(self.store.list_attachments()), 2)

        copied_path = Path(file_attachment["path"])
        self.assertTrue(copied_path.exists())
        self.assertTrue(
            self.store.delete_attachment(file_attachment["id"], delete_file=True)
        )
        self.assertFalse(copied_path.exists())
        self.assertIsNone(self.store.get_attachment(file_attachment["id"]))

        # Detaching is not the same as deleting the note.
        self.assertTrue(self.store.delete_note(note["id"]))
        orphan = self.store.get_attachment(screenshot["id"])
        self.assertIsNotNone(orphan)
        self.assertIsNone(orphan["note_id"])


class RequestLogTest(CaseStoreTestBase):
    def test_log_request_writes_database_row_and_raw_file(self):
        entry = self.store.log_request(
            "shodan",
            "example.com",
            method="GET",
            url="https://api.shodan.io/shodan/host/search?q=example.com",
            status_code=200,
            duration_ms=42.5,
            request_headers={"Authorization": "secret"},
            request_body={"query": "example.com"},
            response_headers={"Content-Type": "application/json"},
            response_body={"matches": []},
        )
        self.assertEqual(entry["module"], "shodan")
        self.assertEqual(entry["target"], "example.com")
        self.assertEqual(entry["status_code"], 200)
        self.assertIn("Authorization", entry["request_headers"])

        raw_path = Path(entry["raw_path"])
        self.assertTrue(raw_path.is_file())
        self.assertEqual(raw_path.parent, self.root / "logs" / "requests")
        raw = raw_path.read_text(encoding="utf-8")
        self.assertIn("SkyFall raw request log", raw)
        self.assertIn("=== request body ===", raw)
        self.assertIn("example.com", raw)

        fetched = self.store.get_request(entry["id"])
        self.assertEqual(
            fetched["url"], "https://api.shodan.io/shodan/host/search?q=example.com"
        )

    def test_save_raw_can_be_disabled(self):
        entry = self.store.log_request("dns", "example.com", save_raw=False)
        self.assertEqual(entry["raw_path"], "")
        self.assertEqual(list((self.root / "logs" / "requests").iterdir()), [])

    def test_list_requests_filters_by_module_and_target(self):
        self.store.log_request("shodan", "a.com")
        self.store.log_request("whois", "a.com")
        self.store.log_request("shodan", "b.com")

        self.assertEqual(len(self.store.list_requests()), 3)
        self.assertEqual(len(self.store.list_requests(module="shodan")), 2)
        self.assertEqual(len(self.store.list_requests(target="a.com")), 2)
        self.assertEqual(
            len(self.store.list_requests(module="whois", target="a.com")), 1
        )

    def test_large_bodies_are_clipped_in_database(self):
        store = CaseStore(self.root, max_inline=10)
        entry = store.log_request("module", "target", response_body="x" * 100)
        self.assertIn("truncated", entry["response_body"])
        self.assertLess(len(entry["response_body"]), 100)

    def test_log_response_adapter_reads_requests_like_objects(self):
        class Request:
            method = "POST"
            headers = {"X-Test": "1"}
            body = "payload"

        class Response:
            request = Request()
            url = "https://example.com/api"
            status_code = 201
            headers = {"Content-Type": "text/plain"}
            text = "created"

        entry = self.store.log_response(
            "module", "example.com", Response(), duration_ms=1.0
        )
        self.assertEqual(entry["method"], "POST")
        self.assertEqual(entry["status_code"], 201)
        self.assertIn("created", entry["response_body"])


def _snapshot(nodes=None, edges=None, **extra):
    payload = {"nodes": list(nodes or []), "edges": list(edges or [])}
    payload.update(extra)
    return payload


def _node(node_id, title="Node", **extra):
    node = {"id": node_id, "title": title, "content": "", "entity_type": "Custom"}
    node.update(extra)
    return node


class GraphVersionTest(CaseStoreTestBase):
    def test_save_and_load_snapshot(self):
        snapshot = _snapshot([_node("a"), _node("b")], [{"source": "a", "target": "b"}])
        saved = self.store.save_graph_version(
            snapshot, label="initial", action="manual"
        )
        self.assertTrue(saved["created"])
        self.assertEqual(saved["nodes"], 2)
        self.assertEqual(saved["edges"], 1)
        self.assertEqual(saved["label"], "initial")

        loaded = self.store.get_graph_version(saved["id"])
        self.assertEqual(loaded["snapshot"], snapshot)
        self.assertEqual(loaded["action"], "manual")

    def test_content_dedupe_ignores_positions_but_not_content(self):
        first = self.store.save_graph_version(_snapshot([_node("a", x=1, y=2)]))
        moved = self.store.save_graph_version(_snapshot([_node("a", x=90, y=40)]))
        self.assertFalse(moved["created"])
        self.assertEqual(moved["id"], first["id"])

        changed = self.store.save_graph_version(
            _snapshot([_node("a", title="Renamed")])
        )
        self.assertTrue(changed["created"])
        self.assertNotEqual(changed["id"], first["id"])

    def test_dedupe_can_be_disabled(self):
        snapshot = _snapshot([_node("a")])
        first = self.store.save_graph_version(snapshot, dedupe=False)
        second = self.store.save_graph_version(snapshot, dedupe=False)
        self.assertTrue(first["created"])
        self.assertTrue(second["created"])
        self.assertNotEqual(first["id"], second["id"])

    def test_versions_are_listed_newest_first_and_keep_parents(self):
        parent = self.store.save_graph_version(_snapshot([_node("a")]))
        child = self.store.save_graph_version(
            _snapshot([_node("a"), _node("b")]),
            action="transform",
            parent_id=parent["id"],
        )
        versions = self.store.list_graph_versions()
        self.assertEqual([item["id"] for item in versions], [child["id"], parent["id"]])
        self.assertNotIn("snapshot", versions[0])
        self.assertEqual(child["parent_id"], parent["id"])

        with_snapshots = self.store.list_graph_versions(include_snapshot=True)
        self.assertIn("snapshot", with_snapshots[0])

    def test_latest_graph_version(self):
        self.assertIsNone(self.store.latest_graph_version())
        first = self.store.save_graph_version(_snapshot([_node("a")]))
        self.store.save_graph_version(_snapshot([_node("b")]))
        latest = self.store.latest_graph_version(include_snapshot=False)
        self.assertNotEqual(latest["id"], first["id"])
        self.assertNotIn("snapshot", latest)
        self.assertIn(
            "snapshot", self.store.latest_graph_version(include_snapshot=True)
        )

    def test_prune_keeps_most_recent_versions(self):
        for index in range(6):
            self.store.save_graph_version(_snapshot([_node(str(index))]), dedupe=False)
        self.assertEqual(len(self.store.list_graph_versions()), 6)

        pruned = self.store.prune_graph_versions(keep=3)
        self.assertEqual(pruned, 3)
        remaining = self.store.list_graph_versions()
        self.assertEqual(len(remaining), 3)
        self.assertEqual(len(self.store.list_graph_versions(include_snapshot=True)), 3)

    def test_save_graph_version_prunes_automatically(self):
        for index in range(5):
            self.store.save_graph_version(
                _snapshot([_node(str(index))]), dedupe=False, keep=2
            )
        self.assertEqual(len(self.store.list_graph_versions()), 2)

    def test_delete_graph_version(self):
        saved = self.store.save_graph_version(_snapshot([_node("a")]))
        self.assertTrue(self.store.delete_graph_version(saved["id"]))
        self.assertFalse(self.store.delete_graph_version(saved["id"]))
        self.assertIsNone(self.store.get_graph_version(saved["id"]))

    def test_invalid_snapshot_type_is_rejected(self):
        with self.assertRaises(TypeError):
            self.store.save_graph_version([])


class ActivityAndStatsTest(CaseStoreTestBase):
    def test_activity_records_operations(self):
        note = self.store.create_note("Audit me")
        kinds = [item["kind"] for item in self.store.list_activity()]
        self.assertIn("note_created", kinds)
        self.store.delete_note(note["id"])
        kinds = [item["kind"] for item in self.store.list_activity()]
        self.assertIn("note_deleted", kinds)

    def test_stats_counts_every_collection(self):
        note = self.store.create_note("Stats")
        self.store.add_screenshot(b"shot", note_id=note["id"])
        self.store.log_request("whois", "example.com")
        self.store.save_graph_version(_snapshot([_node("a")]))

        stats = self.store.stats()
        self.assertEqual(stats["root"], str(self.root.resolve()))
        self.assertEqual(stats["notes"], 1)
        self.assertEqual(stats["attachments"], 1)
        self.assertEqual(stats["screenshots"], 1)
        self.assertEqual(stats["requests"], 1)
        self.assertEqual(stats["graph_versions"], 1)
        self.assertGreaterEqual(stats["activity"], 3)

    def test_export_note_writes_markdown_with_tags_and_attachments(self):
        note = self.store.create_note("Export note", "Body text", tags=["alpha"])
        screenshot = self.store.add_screenshot(b"x", caption="Map", note_id=note["id"])
        path = Path(self.store.export_note(note["id"]))
        self.assertTrue(path.is_file())
        content = path.read_text(encoding="utf-8")
        self.assertIn("# Export note", content)
        self.assertIn("Tags: alpha", content)
        self.assertIn("Body text", content)
        self.assertIn(screenshot["path"], content)
        self.assertIsNone(self.store.export_note("missing"))

    def test_meta_schema_is_created(self):
        with self.store._connect() as conn:
            keys = {
                row["key"] for row in conn.execute("SELECT key FROM meta").fetchall()
            }
        self.assertIn("created_at", keys)
        self.assertIn("schema_version", keys)

    def test_database_file_lives_in_case_root(self):
        self.assertTrue((self.root / "case.db").is_file())
        self.assertEqual(self.store.db_path, self.root / "case.db")
        for directory in (
            "notes",
            "evidence",
            "screenshots",
            "logs/requests",
            "graph/versions",
        ):
            self.assertTrue((self.root / directory).is_dir(), directory)

    def test_reopening_store_preserves_data(self):
        note = self.store.create_note("Persistent")
        self.store.close()
        reopened = CaseStore(self.root)
        try:
            self.assertIsNotNone(reopened.get_note(note["id"]))
            self.assertEqual(reopened.stats()["notes"], 1)
        finally:
            reopened.close()


if __name__ == "__main__":
    unittest.main()
