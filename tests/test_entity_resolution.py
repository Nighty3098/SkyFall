"""Tests for identifier normalisation, duplicate matching and graph merging."""

import unittest

from src.modules.entity_resolution import (
    EntityRecord,
    auto_merge_graph_dict,
    build_profile,
    compare_profiles,
    extract_identifiers,
    find_duplicate_groups,
    find_duplicate_groups_from_graph,
    merge_graph_dict,
    normalize_phone,
    normalize_text,
)


def _record(node_id, title, entity_type="Custom", content="", evidence=None):
    return EntityRecord(
        id=node_id,
        title=title,
        entity_type=entity_type,
        content=content,
        evidence=list(evidence or []),
    )


class NormalizationTest(unittest.TestCase):
    def test_phone_formats_collapse_to_one_value(self):
        values = [
            "+7 (999) 123-45-67",
            "8 999 123 45 67",
            "89991234567",
            "+79991234567",
        ]
        normalized = {normalize_phone(value) for value in values}
        self.assertEqual(len(normalized), 1)

    def test_cyrillic_names_transliterate(self):
        self.assertEqual(
            normalize_text("Иван Петров"),
            normalize_text("Ivan Petrov"),
        )

    def test_extracts_labelled_identifiers_without_contamination(self):
        text = (
            "Email: User@Example.com\n"
            "Phone: +7 (999) 123-45-67\n"
            "Username: @alice\n"
            "Domain: example.com\n"
            "URL: https://example.com/path\n"
            "IP: 8.8.8.8\n"
            "MAC: AA:BB:CC:DD:EE:FF\n"
            "Telegram: @bob"
        )
        found = extract_identifiers(text)
        self.assertIn("email:user@example.com", found)
        self.assertIn("phone:+79991234567", found)
        self.assertIn("username:alice", found)
        self.assertIn("domain:example.com", found)
        self.assertIn("url:example.com/path", found)
        self.assertIn("ip:8.8.8.8", found)
        self.assertIn("mac:aa:bb:cc:dd:ee:ff", found)
        self.assertIn("username:bob", found)
        self.assertNotIn("email:phone", found)

    def test_url_path_is_not_mistaken_for_a_phone_number(self):
        found = extract_identifiers("https://example.com/1234567890")
        self.assertFalse(any(item.startswith("phone:") for item in found))

    def test_cyrillic_field_names_are_recognised(self):
        found = extract_identifiers("Телефон: 8 999 123 45 67\nПочта: user@example.com")
        self.assertIn("phone:+79991234567", found)
        self.assertIn("email:user@example.com", found)


class MatchingTest(unittest.TestCase):
    def _match(self, left, right, entity_type="Custom"):
        return compare_profiles(
            build_profile(_record("a", left, entity_type)),
            build_profile(_record("b", right, entity_type)),
        )

    def test_email_case_and_whitespace_are_duplicates(self):
        match = self._match(" User@Example.com ", "user@example.com", "Email")
        self.assertIsNotNone(match)
        self.assertTrue(match.auto)

    def test_phone_formatting_is_a_duplicate(self):
        match = self._match("+7 (999) 123-45-67", "8 999 123 45 67", "Phone")
        self.assertIsNotNone(match)
        self.assertTrue(match.auto)

    def test_different_emails_are_never_merged(self):
        self.assertIsNone(self._match("a@example.com", "b@example.com", "Email"))

    def test_person_word_order_is_automatically_merged(self):
        match = self._match("Ivan Petrov", "Petrov Ivan", "Person")
        self.assertIsNotNone(match)
        self.assertTrue(match.auto)

    def test_name_variants_need_review(self):
        groups = find_duplicate_groups(
            [
                _record("a", "J. Smith", "Person"),
                _record("b", "John Smith", "Person"),
            ],
            include_review=True,
        )
        self.assertEqual(len(groups), 1)
        self.assertFalse(groups[0].auto)

    def test_unrelated_names_are_not_grouped(self):
        self.assertIsNone(self._match("John Smith", "Jane Doe", "Person"))

    def test_different_entity_types_do_not_match(self):
        self.assertIsNone(
            compare_profiles(
                build_profile(_record("a", "alice", "Username")),
                build_profile(_record("b", "alice", "Person")),
            )
        )

    def test_graph_groups_use_edge_degree_for_the_primary(self):
        graph = {
            "nodes": [
                {"id": "a", "title": "user@example.com", "entity_type": "Email"},
                {"id": "b", "title": "USER@example.com", "entity_type": "Email"},
                {"id": "c", "title": "target", "entity_type": "Custom"},
            ],
            "edges": [{"source": "b", "target": "c"}],
        }
        groups = find_duplicate_groups_from_graph(graph, include_review=False)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].primary_id, "b")


class MergeGraphTest(unittest.TestCase):
    def _duplicate_graph(self):
        return {
            "nodes": [
                {
                    "id": "a",
                    "title": "User@Example.com",
                    "entity_type": "Email",
                    "content": "source: profile A",
                    "evidence": ["https://example.com/a"],
                },
                {
                    "id": "b",
                    "title": "user@example.com",
                    "entity_type": "Email",
                    "content": "source: profile B",
                    "evidence": ["https://example.com/b"],
                },
                {
                    "id": "c",
                    "title": "Alice",
                    "entity_type": "Person",
                },
                {
                    "id": "d",
                    "title": "Bob",
                    "entity_type": "Person",
                },
            ],
            "edges": [
                {"source": "a", "target": "c", "relationship_type": "owns"},
                {"source": "b", "target": "d", "relationship_type": "owns"},
                {"source": "a", "target": "b", "relationship_type": "aliases"},
            ],
        }

    def test_auto_merge_preserves_evidence_aliases_and_edges(self):
        merged, reports = auto_merge_graph_dict(self._duplicate_graph())
        self.assertEqual(len(reports), 1)
        emails = [node for node in merged["nodes"] if node["entity_type"] == "Email"]
        self.assertEqual(len(emails), 1)
        survivor = emails[0]
        self.assertEqual(
            set(survivor["evidence"]),
            {"https://example.com/a", "https://example.com/b"},
        )
        self.assertIn("User@Example.com", survivor["aliases"])
        self.assertIn("user@example.com", survivor["aliases"])
        self.assertTrue(survivor["metadata"]["merged_from"])
        self.assertEqual(len(survivor["metadata"]["resolution"]["node_ids"]), 2)
        self.assertIn("profile A", survivor["content"])
        self.assertIn("profile B", survivor["content"])

        targets = {
            edge["target"]
            for edge in merged["edges"]
            if edge["source"] == survivor["id"]
        }
        self.assertEqual(targets, {"c", "d"})
        # The edge between the two duplicates must become a dropped self-loop.
        self.assertFalse(
            any(edge["source"] == edge["target"] for edge in merged["edges"])
        )

    def test_manual_merge_of_unrelated_records(self):
        graph = {
            "nodes": [
                {"id": "a", "title": "one", "entity_type": "Custom"},
                {"id": "b", "title": "two", "entity_type": "Custom"},
            ],
            "edges": [],
        }
        merged, reports = merge_graph_dict(graph, [["a", "b"]])
        self.assertEqual(len(merged["nodes"]), 1)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["reasons"], ["manual selection"])

    def test_input_graph_is_not_mutated(self):
        graph = self._duplicate_graph()
        before = len(graph["nodes"])
        auto_merge_graph_dict(graph)
        self.assertEqual(len(graph["nodes"]), before)


if __name__ == "__main__":
    unittest.main()
