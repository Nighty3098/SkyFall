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
    compute_hierarchical_layout,
    compute_layout,
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


class HierarchicalLayoutTest(unittest.TestCase):
    def _chain(self, length):
        nodes = [{"id": f"n{i}"} for i in range(length)]
        edges = [{"source": f"n{i}", "target": f"n{i + 1}"} for i in range(length - 1)]
        return nodes, edges

    def test_root_is_placed_at_top(self):
        nodes, edges = self._chain(4)
        positions = compute_hierarchical_layout(nodes, edges).positions
        ys = {nid: y for nid, (_, y) in positions.items()}
        self.assertEqual(min(ys, key=ys.get), "n0")
        self.assertLess(ys["n0"], ys["n3"])

    def test_levels_have_even_vertical_spacing(self):
        nodes, edges = self._chain(5)
        positions = compute_hierarchical_layout(nodes, edges).positions
        ys = sorted({round(y, 6) for _, y in positions.values()})
        gaps = {round(b - a, 6) for a, b in zip(ys, ys[1:])}
        self.assertEqual(len(gaps), 1)

    def test_siblings_do_not_overlap(self):
        nodes = [
            {"id": "root"},
            {"id": "a"},
            {"id": "b"},
            {"id": "c"},
        ]
        edges = [
            {"source": "root", "target": "a"},
            {"source": "root", "target": "b"},
            {"source": "root", "target": "c"},
        ]
        positions = compute_hierarchical_layout(nodes, edges).positions
        xs = sorted(positions[nid][0] for nid in ("a", "b", "c"))
        self.assertGreaterEqual(xs[1] - xs[0], NODE_WIDTH)
        self.assertGreaterEqual(xs[2] - xs[1], NODE_WIDTH)


class LayoutAlgorithmTest(unittest.TestCase):
    ALGORITHMS = (
        "spring",
        "kamada_kawai",
        "shell",
        "spectral",
        "circular",
        "hierarchical",
    )

    def _graph(self, count):
        nodes = [{"id": f"n{i}"} for i in range(count)]
        edges = [{"source": f"n{i}", "target": f"n{i + 1}"} for i in range(count - 1)]
        return nodes, edges

    def test_every_algorithm_places_all_nodes(self):
        nodes, edges = self._graph(12)
        for algorithm in self.ALGORITHMS:
            with self.subTest(algorithm=algorithm):
                positions = compute_layout(nodes, edges, algorithm=algorithm).positions
                self.assertEqual(set(positions), {n["id"] for n in nodes})

    def test_non_hierarchical_span_is_bounded(self):
        nodes, edges = self._graph(12)
        for algorithm in self.ALGORITHMS:
            if algorithm == "hierarchical":
                continue
            with self.subTest(algorithm=algorithm):
                positions = compute_layout(nodes, edges, algorithm=algorithm).positions
                xs = [x for x, _ in positions.values()]
                ys = [y for _, y in positions.values()]
                span = max(max(xs) - min(xs), max(ys) - min(ys))
                # Roughly four node-widths for a 12 node graph.
                self.assertLess(span, NODE_WIDTH * 8)

    def test_repeated_layout_does_not_drift(self):
        nodes, edges = self._graph(10)
        first = compute_layout(nodes, edges, algorithm="spring").positions
        second = compute_layout(nodes, edges, algorithm="spring").positions
        for nid in first:
            self.assertAlmostEqual(first[nid][0], second[nid][0], places=4)
            self.assertAlmostEqual(first[nid][1], second[nid][1], places=4)


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
