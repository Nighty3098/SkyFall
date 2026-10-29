import sqlite3

import networkx as nx

from src.modules.graph_io import _telegram_layout, tg_networkx_to_skyfall
from src.modules.tg_analyzer import TgAnalyzer


def test_telegram_layout_groups_users_around_their_channel_hubs():
    graph = nx.Graph()
    graph.add_node("channel:news", node_type="channel")
    graph.add_node("channel:chat", node_type="channel")
    graph.add_node("user:alice", node_type="user")
    graph.add_node("user:bob", node_type="user")
    graph.add_node("user:carol", node_type="user")
    graph.add_node("domain:example.org", node_type="domain")
    graph.add_edge("user:alice", "channel:news", edge_type="posted", post_count=4)
    graph.add_edge("user:bob", "channel:chat", edge_type="member")
    graph.add_edge("user:alice", "user:carol", edge_type="replier")
    graph.add_edge("user:alice", "domain:example.org", edge_type="mentions")

    positions = _telegram_layout(graph)

    assert positions == _telegram_layout(graph)
    assert positions["channel:news"] != positions["channel:chat"]
    assert positions["user:alice"] != positions["user:bob"]
    assert positions["user:carol"] != positions["user:alice"]
    assert positions["domain:example.org"] != positions["user:alice"]
    # A user connected to a channel is placed in that channel's local cluster.
    assert sum(
        (positions["user:alice"][axis] - positions["channel:news"][axis]) ** 2
        for axis in (0, 1)
    ) < sum(
        (positions["user:alice"][axis] - positions["channel:chat"][axis]) ** 2
        for axis in (0, 1)
    )


def test_tg_database_graph_keeps_relevant_users_and_relationships(tmp_path):
    database = tmp_path / "telegram.db"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE channels (username TEXT, channel_id INTEGER)")
        conn.execute("INSERT INTO channels VALUES ('news', -1001)")

    analyzer = TgAnalyzer()
    analyzer.get_channels = lambda _db_path: ["news"]
    analyzer.get_all_users = lambda _db_path: {
        101: {"user_id": 101, "username": "alice"},
        202: {"user_id": 202, "username": "bob"},
        303: {"user_id": 303, "username": "unrelated"},
    }
    analyzer.get_channel_members = lambda _db_path, _channel: {
        101: {"member_type": "member"}
    }
    analyzer.get_posts = lambda *_args: [
        {"post_id": 1, "user_id": 101},
        {"post_id": 2, "user_id": 101},
        {
            "post_id": 3,
            "user_id": 101,
            "is_forwarded": True,
            "forwarded_from_id": 202,
        },
    ]
    analyzer.get_discussions = lambda *_args: [{"post_id": 1, "user_id": 202}]

    graph = analyzer.build_graph(
        str(database),
        channels=["news"],
        min_replies=1,
        log_callback=lambda _message: None,
    )

    assert "user:303" not in graph
    assert graph.nodes["user:101"]["username"] == "alice"

    channel_edge = graph["user:101"]["channel:news"]
    assert channel_edge["edge_types"] == "member|posted"
    assert channel_edge["post_count"] == 3

    interaction_edge = graph["user:101"]["user:202"]
    assert interaction_edge["edge_types"] == "replier|forwarded"
    assert interaction_edge["reply_weight"] == 1
    assert interaction_edge["forward_weight"] == 1

    skyfall_graph = tg_networkx_to_skyfall(graph)
    labels = {edge["label"] for edge in skyfall_graph["edges"]}
    assert "member · posted x3" in labels
    assert "replier · forwarded" in labels
