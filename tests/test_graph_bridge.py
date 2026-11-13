"""Tests for the graph bridge's agent-facing node/edge semantics."""

import os
import socket
import struct
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src import graph_bridge  # noqa: E402
from src.graph_bridge import GraphBridgeServer  # noqa: E402
from src.libs.graph_lib import EdgeItem, GraphWidget, NodeItem  # noqa: E402

_app = QApplication.instance() or QApplication([])


class GraphBridgeServerTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.server = GraphBridgeServer()
        self.server._graph_widget = self.gw
        self.server._node_item_cls = NodeItem

    def tearDown(self):
        self.server.stop()

    def _nodes(self):
        return [i for i in self.gw._scene.items() if isinstance(i, NodeItem)]

    def _edges(self):
        return [i for i in self.gw._scene.items() if isinstance(i, EdgeItem)]

    def test_add_node_creates_and_places(self):
        res = self.server._add_node({"title": "example.com", "entity_type": "domain"})
        self.assertTrue(res["created"])
        self.assertEqual(res["entity_type"], "Domain")
        self.assertEqual(len(self._nodes()), 1)

    def test_add_node_rejects_unknown_type(self):
        res = self.server._add_node({"title": "x", "entity_type": "nanobot"})
        self.assertIn("error", res)
        self.assertIn("Person", res["valid_entity_types"])
        self.assertEqual(len(self._nodes()), 0)

    def test_add_node_requires_title(self):
        self.assertIn("error", self.server._add_node({"title": "  "}))

    def test_add_node_accepts_maltego_style_types(self):
        cases = {
            "url": "URL",
            "asn": "ASN",
            "cidr": "Netblock",
            "port": "Port",
            "tls_cert": "Certificate",
            "sha256": "Hash",
            "social_media": "SocialMedia",
            "file": "Document",
            "dns_server": "Nameserver",
        }
        for index, (raw, expected) in enumerate(cases.items()):
            res = self.server._add_node({"title": f"value-{index}", "entity_type": raw})
            self.assertEqual(res.get("entity_type"), expected, raw)

    def test_add_edge_accepts_new_relationship_vocabulary(self):
        a = self.server._add_node({"title": "a.example", "entity_type": "Domain"})
        b = self.server._add_node({"title": "b.example", "entity_type": "Domain"})
        res = self.server._add_edge(
            {
                "source_id": a["node_id"],
                "target_id": b["node_id"],
                "relationship": "subdomain",
            }
        )
        self.assertTrue(res["created"])
        self.assertEqual(res["relationship"], "subdomain_of")
        self.assertTrue(res["relationship_known"])

    def test_add_node_deduplicates_and_merges(self):
        first = self.server._add_node({"title": "alice", "entity_type": "Username"})
        second = self.server._add_node(
            {"title": "alice", "entity_type": "Username", "content": "found on X"}
        )
        self.assertFalse(second["created"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(first["node_id"], second["node_id"])
        self.assertEqual(len(self._nodes()), 1)
        self.assertIn("found on X", self._nodes()[0].content)

    def test_add_node_allow_duplicate(self):
        self.server._add_node({"title": "alice", "entity_type": "Username"})
        self.server._add_node(
            {
                "title": "alice",
                "entity_type": "Username",
                "allow_duplicate": True,
            }
        )
        self.assertEqual(len(self._nodes()), 2)

    def test_anchored_nodes_do_not_overlap(self):
        anchor = self.server._add_node({"title": "alice", "entity_type": "Username"})
        for i in range(6):
            self.server._add_node(
                {
                    "title": f"site{i}.com",
                    "entity_type": "Domain",
                    "anchor_id": anchor["node_id"],
                }
            )
        nodes = self._nodes()
        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                separated = (
                    abs(a.pos().x() - b.pos().x()) >= a._width
                    or abs(a.pos().y() - b.pos().y()) >= a._height
                )
                self.assertTrue(separated)

    def test_add_edge_auto_ports_and_dedupe(self):
        a = self.server._add_node({"title": "a.com", "entity_type": "Domain"})
        b = self.server._add_node({"title": "b.com", "entity_type": "Domain"})
        res = self.server._add_edge(
            {
                "source_id": a["node_id"],
                "target_id": b["node_id"],
                "relationship": "owns",
            }
        )
        self.assertTrue(res["created"])
        self.assertIn(res["source_port"], {"left", "right", "top", "bottom"})
        dup = self.server._add_edge(
            {
                "source_id": b["node_id"],
                "target_id": a["node_id"],
                "relationship": "resolved_to",
            }
        )
        self.assertFalse(dup["created"])
        self.assertTrue(dup["duplicate"])
        self.assertEqual(len(self._edges()), 1)

    def test_add_edge_rejects_self_loop(self):
        a = self.server._add_node({"title": "a.com", "entity_type": "Domain"})
        res = self.server._add_edge(
            {"source_id": a["node_id"], "target_id": a["node_id"]}
        )
        self.assertIn("error", res)
        self.assertEqual(len(self._edges()), 0)

    def test_build_maps_refs(self):
        res = self.server._build(
            {
                "nodes": [
                    {"ref": "p", "title": "@alice", "entity_type": "Username"},
                    {
                        "ref": "e",
                        "title": "a@b.com",
                        "entity_type": "Email",
                        "anchor": "p",
                    },
                ],
                "edges": [
                    {"source": "p", "target": "e", "relationship": "registered_at"}
                ],
            }
        )
        self.assertEqual(len(res["node_ids"]), 2)
        self.assertEqual(len(res["nodes"]), 2)
        self.assertEqual(len(res["edges"]), 1)
        self.assertTrue(res["edges"][0]["created"])

    def test_receive_exactly_reads_fragmented_header_and_body(self):
        payload = b'{"action":"test"}'

        class FragmentedSocket:
            def __init__(self, data):
                self.data = data

            def gettimeout(self):
                return None

            def settimeout(self, timeout):
                pass

            def recv(self, size):
                result, self.data = self.data[:1], self.data[1:]
                return result

        frame = struct.pack("!I", len(payload)) + payload
        self.assertEqual(
            graph_bridge._recv_msg(FragmentedSocket(frame)), {"action": "test"}
        )

    def test_receive_rejects_oversized_frame_before_body_read(self):
        class HeaderOnlySocket:
            def __init__(self):
                self.reads = 0

            def gettimeout(self):
                return None

            def settimeout(self, timeout):
                pass

            def recv(self, size):
                self.reads += 1
                return struct.pack("!I", graph_bridge.MAX_FRAME_SIZE + 1)

        sock = HeaderOnlySocket()
        with self.assertRaises(ValueError):
            graph_bridge._recv_msg(sock)
        self.assertEqual(sock.reads, 1)

    def test_invocation_timeout_cancels_queued_mutation(self):
        class Signal:
            def emit(self, invocation):
                self.invocation = invocation

        class Worker:
            execute = Signal()

        self.server._worker = Worker()
        called = []
        with mock.patch.object(graph_bridge, "MAIN_THREAD_INVOKE_TIMEOUT", 0.01):
            result = self.server._invoke_on_main(lambda: called.append(True))
        self.assertEqual(
            result, {"error": "Graph bridge main-thread invocation timed out"}
        )
        self.server._worker.execute.invocation.execute()
        self.assertEqual(called, [])

    def test_stop_closes_idle_clients_and_joins_workers(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.close()
        clients = []
        overflow_client = None
        with (
            mock.patch.object(graph_bridge, "GRAPH_BRIDGE_PORT", port),
            mock.patch.object(graph_bridge, "MAX_CLIENTS", 1),
            mock.patch.object(graph_bridge, "CLIENT_READ_TIMEOUT", 5),
        ):
            self.server.start(self.gw, NodeItem, "test-token")
            client = socket.create_connection(("127.0.0.1", port))
            clients.append(client)
            deadline = time.monotonic() + 1
            while not self.server._clients and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(len(self.server._clients), 1)
            overflow_client = socket.create_connection(("127.0.0.1", port))
            overflow_client.settimeout(1)
            self.assertEqual(overflow_client.recv(1), b"")
            client_threads = list(self.server._clients.values())
            self.server.stop()
            self.assertEqual(self.server._clients, {})
            self.assertFalse(any(thread.is_alive() for thread in client_threads))
        for client in clients:
            client.close()
        if overflow_client is not None:
            overflow_client.close()

    def test_idle_client_read_deadline_releases_worker(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.close()
        with (
            mock.patch.object(graph_bridge, "GRAPH_BRIDGE_PORT", port),
            mock.patch.object(graph_bridge, "CLIENT_READ_TIMEOUT", 0.1),
        ):
            self.server.start(self.gw, NodeItem, "test-token")
            client = socket.create_connection(("127.0.0.1", port))
            client.settimeout(1)
            deadline = time.monotonic() + 1
            while not self.server._clients and time.monotonic() < deadline:
                time.sleep(0.01)
            while self.server._clients and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(self.server._clients, {})
            self.assertEqual(client.recv(1), b"")
            client.close()


if __name__ == "__main__":
    unittest.main()
