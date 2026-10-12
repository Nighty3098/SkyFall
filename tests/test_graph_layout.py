"""Tests for graph placement helpers and entity/relationship normalisation."""

import unittest

from src.libs.graph_lib import (
    auto_ports,
    normalize_entity_type,
    normalize_relationship,
)
from src.modules.graph_layout import (
    NODE_HEIGHT,
    NODE_WIDTH,
    child_arc_positions,
    find_free_slot,
    graph_centroid,
    rects_overlap,
)


class FindFreeSlotTest(unittest.TestCase):
    def test_avoids_occupied_rectangles(self):
        occupied = [(0, 0, NODE_WIDTH, NODE_HEIGHT)]
        pos = find_free_slot(occupied, anchor=(NODE_WIDTH / 2, NODE_HEIGHT / 2))
        rect = (pos[0], pos[1], NODE_WIDTH, NODE_HEIGHT)
        self.assertFalse(rects_overlap(rect, occupied[0], padding=8))

    def test_stays_near_the_anchor(self):
        pos = find_free_slot([], anchor=(1000.0, -500.0), radius=240.0)
        cx = pos[0] + NODE_WIDTH / 2
        cy = pos[1] + NODE_HEIGHT / 2
        self.assertLess(abs(cx - 1000.0), 240.0 + NODE_WIDTH)
        self.assertLess(abs(cy + 500.0), 240.0 + NODE_HEIGHT)

    def test_pushes_out_when_ring_is_full(self):
        anchor = (0.0, 0.0)
        occupied = []
        positions = []
        for _ in range(10):
            pos = find_free_slot(occupied, anchor=anchor)
            rect = (pos[0], pos[1], NODE_WIDTH, NODE_HEIGHT)
            for other in occupied:
                self.assertFalse(rects_overlap(rect, other, padding=8))
            occupied.append(rect)
            positions.append(rect)
        self.assertEqual(len({(round(x), round(y)) for x, y, _, _ in positions}), 10)


class ChildArcTest(unittest.TestCase):
    def test_single_child_is_placed_above_parent(self):
        ((x, y),) = child_arc_positions((0, 0), 1)
        self.assertLess(y, 0)

    def test_count_matches(self):
        self.assertEqual(len(child_arc_positions((0, 0), 5)), 5)

    def test_children_are_spread_out(self):
        positions = child_arc_positions((0, 0), 4)
        self.assertEqual(len({(round(x), round(y)) for x, y in positions}), 4)
        ys = [y for _, y in positions]
        self.assertGreater(max(ys) - min(ys), NODE_HEIGHT)


class CentroidTest(unittest.TestCase):
    def test_centroid_of_empty_is_origin(self):
        self.assertEqual(graph_centroid([]), (0.0, 0.0))

    def test_centroid_of_rectangles(self):
        cx, cy = graph_centroid([(0, 0, 100, 100), (100, 100, 100, 100)])
        self.assertEqual((cx, cy), (100.0, 100.0))


class NormalizeEntityTypeTest(unittest.TestCase):
    def test_canonical_and_case_insensitive(self):
        self.assertEqual(normalize_entity_type("domain"), "Domain")
        self.assertEqual(normalize_entity_type("  Username "), "Username")

    def test_aliases(self):
        self.assertEqual(normalize_entity_type("handle"), "Username")
        self.assertEqual(normalize_entity_type("wallet"), "Crypto")
        self.assertEqual(normalize_entity_type("location"), "Geolocation")

    def test_unknown_returns_empty(self):
        self.assertEqual(normalize_entity_type("nanobot"), "")
        self.assertEqual(normalize_entity_type(None), "")


class NormalizeRelationshipTest(unittest.TestCase):
    def test_canonical_values(self):
        self.assertEqual(normalize_relationship("owns"), "owns")
        self.assertEqual(normalize_relationship("Resolved-To"), "resolved_to")

    def test_aliases(self):
        self.assertEqual(normalize_relationship("employed_by"), "works_at")
        self.assertEqual(normalize_relationship("lives in"), "located_at")

    def test_unknown_is_kept(self):
        self.assertEqual(normalize_relationship("paid_for"), "paid_for")

    def test_empty_defaults_to_associated(self):
        self.assertEqual(normalize_relationship(""), "associated_with")
        self.assertEqual(normalize_relationship(None), "associated_with")


class _FakeNode:
    def __init__(self, x, y, w=NODE_WIDTH, h=NODE_HEIGHT):
        self._x = x
        self._y = y
        self._width = w
        self._height = h

    def scenePos(self):  # noqa: N802 - mirrors the Qt API
        from PySide6.QtCore import QPointF

        return QPointF(self._x, self._y)


class AutoPortsTest(unittest.TestCase):
    def test_horizontal_neighbours(self):
        left = _FakeNode(0, 0)
        right = _FakeNode(600, 0)
        self.assertEqual(auto_ports(left, right), ("right", "left"))
        self.assertEqual(auto_ports(right, left), ("left", "right"))

    def test_vertical_neighbours(self):
        top = _FakeNode(0, 0)
        bottom = _FakeNode(0, 600)
        self.assertEqual(auto_ports(top, bottom), ("bottom", "top"))
        self.assertEqual(auto_ports(bottom, top), ("top", "bottom"))


if __name__ == "__main__":
    unittest.main()
