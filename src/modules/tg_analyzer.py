import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from loguru import logger
from networkx.readwrite import json_graph

from src.ui.output_formatter import divider, kv, line, section, title

try:
    from pyvis.network import Network

    PYVIS_AVAILABLE = True
except ImportError:
    Network = None
    PYVIS_AVAILABLE = False


class TgAnalyzer:
    def __init__(self):
        logger.debug("Init: TgAnalyzer")
        self._conn = None

    def _get_connection(self, db_path):
        original = db_path
        if os.path.isdir(db_path):
            db_path = os.path.join(db_path, "SkyFall_TG.db")
            logger.debug("_get_connection: {} is a dir, resolved to {}", original, db_path)
        logger.debug("_get_connection: connecting to {}", db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_table_columns(self, conn, table_name):
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

    @staticmethod
    def _safe_get(row, key, default=None):
        return row[key] if key in row.keys() else default

    def get_channels(self, db_path):
        logger.debug("get_channels: db_path={}", db_path)
        conn = self._get_connection(db_path)
        channels = []
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='channels'"
            )
            table_exists = cursor.fetchone()
            if not table_exists:
                logger.warning("get_channels: 'channels' table does not exist in DB")
                conn.close()
                return []
            cursor.execute("SELECT COUNT(*) FROM channels")
            count = cursor.fetchone()[0]
            logger.debug("get_channels: total rows in channels table: {}", count)
            cursor.execute("SELECT username FROM channels WHERE username IS NOT NULL")
            rows = cursor.fetchall()
            logger.debug("get_channels: rows with non-null username: {}", len(rows))
            for r in rows:
                logger.debug("get_channels: found channel username='{}'", r[0])
            channels = [row[0] for row in rows]
        except sqlite3.OperationalError as e:
            logger.warning("Could not query channels table: {}", e)
        finally:
            conn.close()
        result = sorted(set(channels))
        logger.debug("get_channels: returning {} unique channels", len(result))
        return result

    def get_channel_id(self, db_path, channel_username):
        conn = self._get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT channel_id FROM channels WHERE username = ?",
                (channel_username,),
            )
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.OperationalError:
            return None
        finally:
            conn.close()

    def get_channel_members(self, db_path, channel):
        conn = self._get_connection(db_path)
        members = {}
        try:
            cursor = conn.cursor()
            query = """
                SELECT m.user_id, m.date, m.status, m.joined_at, m.member_type,
                       u.username, u.first_name, u.last_name, u.phone, u.bot, u.verified, u.premium
                FROM members m
                LEFT JOIN users u ON m.user_id = u.user_id
                JOIN channels c ON m.channel_id = c.channel_id
                WHERE c.username = ?
            """
            cursor.execute(query, (channel,))
            for row in cursor.fetchall():
                user_id = row[0]
                info = {
                    "user_id": user_id,
                    "member_date": row[1],
                    "member_status": row[2],
                    "member_joined_at": row[3],
                    "member_type": row[4],
                    "username": row[5] or "",
                    "first_name": row[6] or "",
                    "last_name": row[7] or "",
                    "phone": row[8] or "",
                    "bot": row[9] or False,
                    "verified": row[10] or False,
                    "premium": row[11] or False,
                }
                members[user_id] = info
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not query members: {e}")
        finally:
            conn.close()
        return members

    def get_posts(self, db_path, channel, start_date=None, end_date=None):
        conn = self._get_connection(db_path)
        posts = []
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT channel_id FROM channels WHERE username = ?",
                (channel,),
            )
            ch_row = cursor.fetchone()
            channel_id_from_channels = dict(ch_row)["channel_id"] if ch_row else None
            cursor.execute("SELECT COUNT(*) FROM posts")
            total_posts = cursor.fetchone()[0]
            cursor.execute(
                "SELECT DISTINCT channel_id FROM posts LIMIT 20"
            )
            post_channel_ids = [r[0] for r in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) FROM posts WHERE date IS NULL")
            null_dates = cursor.fetchone()[0]
            logger.debug(
                "get_posts: channel='{}', channel_id={}, total_posts_in_db={}, null_dates={}, post_channel_ids={}",
                channel, channel_id_from_channels, total_posts, null_dates, post_channel_ids,
            )
            query = """
                SELECT p.* FROM posts p
                JOIN channels c ON p.channel_id = c.channel_id
                WHERE c.username = ?
            """
            params = [channel]
            if start_date:
                query += " AND (p.date IS NULL OR p.date >= ?)"
                params.append(start_date)
            if end_date:
                query += " AND (p.date IS NULL OR p.date <= ?)"
                params.append(end_date)
            cursor.execute(query, params)
            for row in cursor.fetchall():
                posts.append(dict(row))
            logger.debug("get_posts: query returned {} posts", len(posts))
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not query posts: {e}")
        finally:
            conn.close()
        return posts

    def get_discussions(self, db_path, channel, start_date=None, end_date=None):
        conn = self._get_connection(db_path)
        discussions = []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM discussions")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT DISTINCT channel_id FROM discussions LIMIT 20")
            disc_channel_ids = [r[0] for r in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) FROM discussions WHERE date IS NULL")
            null_dates = cursor.fetchone()[0]
            logger.debug(
                "get_discussions: channel='{}', total_discussions_in_db={}, null_dates={}, disc_channel_ids={}",
                channel, total, null_dates, disc_channel_ids,
            )
            query = """
                SELECT d.* FROM discussions d
                JOIN channels c ON d.channel_id = c.channel_id
                WHERE c.username = ?
            """
            params = [channel]
            if start_date:
                query += " AND (d.date IS NULL OR d.date >= ?)"
                params.append(start_date)
            if end_date:
                query += " AND (d.date IS NULL OR d.date <= ?)"
                params.append(end_date)
            cursor.execute(query, params)
            for row in cursor.fetchall():
                discussions.append(dict(row))
            logger.debug("get_discussions: query returned {} discussions", len(discussions))
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not query discussions: {e}")
        finally:
            conn.close()
        return discussions

    def get_links(self, db_path, channel, start_date=None, end_date=None):
        conn = self._get_connection(db_path)
        links = []
        try:
            cursor = conn.cursor()
            query = """
                SELECT l.* FROM links l
                JOIN channels c ON l.channel_id = c.channel_id
                WHERE c.username = ?
            """
            params = [channel]
            if start_date:
                query += " AND (l.date IS NULL OR l.date >= ?)"
                params.append(start_date)
            if end_date:
                query += " AND (l.date IS NULL OR l.date <= ?)"
                params.append(end_date)
            cursor.execute(query, params)
            for row in cursor.fetchall():
                links.append(dict(row))
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not query links: {e}")
        finally:
            conn.close()
        return links

    def get_all_users(self, db_path):
        conn = self._get_connection(db_path)
        users = {}
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            for row in cursor.fetchall():
                users[row["user_id"]] = dict(row)
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not query users table: {e}")
        finally:
            conn.close()
        return users

    def get_cross_channel_members(self, db_path, channels, min_shared=2):
        conn = self._get_connection(db_path)
        cross_channel = defaultdict(set)
        try:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(channels))
            query = f"""
                SELECT c1.username as ch1, c2.username as ch2, m1.user_id
                FROM members m1
                JOIN channels c1 ON m1.channel_id = c1.channel_id
                JOIN members m2 ON m1.user_id = m2.user_id
                JOIN channels c2 ON m2.channel_id = c2.channel_id
                WHERE c1.username IN ({placeholders}) AND c2.username IN ({placeholders})
                AND c1.username < c2.username
            """
            cursor.execute(query, channels + channels)
            for row in cursor.fetchall():
                ch1, ch2, user_id = row
                cross_channel[(ch1, ch2)].add(user_id)
            for key in list(cross_channel.keys()):
                if len(cross_channel[key]) < min_shared:
                    del cross_channel[key]
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not query cross-channel members: {e}")
        finally:
            conn.close()
        return cross_channel

    @staticmethod
    def _make_user_label(info):
        return (
            info.get("username")
            or f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
            or f"User {info.get('user_id', '')}"
        )

    @staticmethod
    def _get_user_attrs(info):
        return {
            "node_type": "user",
            "label": info.get("username")
            or f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
            or f"User {info.get('user_id', '')}",
            "username": info.get("username", ""),
            "first_name": info.get("first_name", ""),
            "last_name": info.get("last_name", ""),
            "phone": info.get("phone", ""),
            "bot": info.get("bot", False),
            "verified": info.get("verified", False),
            "premium": info.get("premium", False),
            "scam": info.get("scam", False),
            "fake": info.get("fake", False),
            "deleted": info.get("deleted", False),
            "business_work_hours": info.get("business_work_hours"),
            "business_location": info.get("business_location"),
            "business_greeting_message": info.get("business_greeting_message"),
            "business_away_message": info.get("business_away_message"),
            "business_intro": info.get("business_intro"),
            "birthday_day": info.get("birthday_day"),
            "birthday_month": info.get("birthday_month"),
            "birthday_year": info.get("birthday_year"),
            "avatar_path": info.get("avatar_path"),
        }

    def _ensure_user_node(self, graph, user_id, all_users):
        node_id = f"user:{user_id}"
        if node_id not in graph:
            info = all_users.get(user_id, {})
            graph.add_node(node_id, **self._get_user_attrs(info))
        return node_id

    def build_graph(
        self,
        db_path,
        channels=None,
        min_replies=2,
        include_forwarded=True,
        include_links=False,
        start_date=None,
        end_date=None,
        include_cross_channel=False,
        include_discussion_replies=True,
        log_callback=print,
    ):
        return self._build_graph_impl(
            db_path,
            channels,
            min_replies,
            include_forwarded,
            include_links,
            start_date,
            end_date,
            include_cross_channel,
            include_discussion_replies,
            log_callback,
        )

    def _build_graph_impl(
        self,
        db_path,
        channels=None,
        min_replies=2,
        include_forwarded=True,
        include_links=False,
        start_date=None,
        end_date=None,
        include_cross_channel=False,
        include_discussion_replies=True,
        log_callback=print,
    ):
        graph = nx.Graph()

        all_channels = self.get_channels(db_path)
        if channels is None:
            channels = all_channels
        else:
            channels = [ch for ch in channels if ch in all_channels]

        log_callback(f"Channels to process: {channels}")

        all_users = self.get_all_users(db_path)

        user_nodes_batch = []
        for user_id, info in all_users.items():
            user_nodes_batch.append((f"user:{user_id}", self._get_user_attrs(info)))
        graph.add_nodes_from(user_nodes_batch)

        channel_id_map = {}
        try:
            db_file = db_path if not os.path.isdir(db_path) else os.path.join(db_path, "SkyFall_TG.db")
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT username, channel_id FROM channels")
            for row in cursor.fetchall():
                if row["username"]:
                    channel_id_map[row["username"]] = row["channel_id"]
                channel_id_map[str(row["channel_id"])] = row["channel_id"]
            conn.close()
        except sqlite3.OperationalError:
            pass

        for channel in channels:
            numeric_id = channel_id_map.get(channel)
            channel_node = f"channel:{channel}"
            graph.add_node(
                channel_node, node_type="channel", label=channel, numeric_id=numeric_id
            )

            posts = self.get_posts(db_path, channel, start_date, end_date)
            discussions = self.get_discussions(db_path, channel, start_date, end_date)
            log_callback(
                f"Channel '{channel}': {len(posts)} posts, {len(discussions)} discussions (filtered)"
            )

            members = self.get_channel_members(db_path, channel)
            log_callback(f"Channel '{channel}': {len(members)} members found")

            member_edges_batch = []
            for user_id, minfo in members.items():
                if user_id is None:
                    continue
                if (
                    isinstance(user_id, int)
                    and user_id < 0
                    and str(user_id).startswith("-100")
                ):
                    continue
                if str(user_id) == str(numeric_id):
                    continue
                user_node = self._ensure_user_node(graph, user_id, all_users)
                target_node = channel_node
                if target_node is None:
                    continue
                member_edges_batch.append(
                    (
                        user_node,
                        target_node,
                        {
                            "edge_type": "member",
                            "member_type": minfo.get("member_type", "member"),
                            "joined_at": minfo.get("member_joined_at"),
                            "member_date": minfo.get("member_date"),
                        },
                    )
                )
            graph.add_edges_from(member_edges_batch)

            post_author = {}
            reply_counter = defaultdict(lambda: defaultdict(int))
            forward_counter = defaultdict(lambda: defaultdict(int))
            forward_users_to_add = set()
            if numeric_id:
                forward_users_to_add.add(numeric_id)

            for p in posts:
                post_id = p.get("post_id")
                user_id = p.get("user_id")
                if post_id:
                    if user_id:
                        post_author[post_id] = user_id
                    elif numeric_id:
                        post_author[post_id] = numeric_id
                if (
                    include_forwarded
                    and p.get("is_forwarded")
                    and p.get("forwarded_from_id")
                    and user_id
                ):
                    src = p["forwarded_from_id"]
                    dst = user_id
                    if src in all_users and src != dst:
                        forward_counter[src][dst] += 1
                        forward_users_to_add.add(src)
                        forward_users_to_add.add(dst)

            for d in discussions:
                d_user_id = d.get("user_id")
                if not d_user_id:
                    continue
                if (
                    isinstance(d_user_id, int)
                    and d_user_id < 0
                    and str(d_user_id).startswith("-100")
                ):
                    continue
                post_id = d.get("post_id")
                if post_id in post_author:
                    author = post_author[post_id]
                    if author != d_user_id:
                        reply_counter[author][d_user_id] += 1

            replier_users = set()
            for u1, reps in reply_counter.items():
                for u2, cnt in reps.items():
                    if cnt >= min_replies:
                        replier_users.add(u1)
                        replier_users.add(u2)

            all_needed_users = forward_users_to_add | replier_users
            for uid in all_needed_users:
                if uid:
                    if isinstance(uid, int) and uid < 0 and str(uid).startswith("-100"):
                        continue
                    if str(uid) == str(numeric_id):
                        continue
                    self._ensure_user_node(graph, uid, all_users)

            discussion_reply_pairs = defaultdict(int)
            if include_discussion_replies:
                discussion_authors = {}
                for d in discussions:
                    msg_id = d.get("message_id")
                    user_id = d.get("user_id")
                    if msg_id and user_id:
                        discussion_authors[msg_id] = user_id

                for d in discussions:
                    reply_to = d.get("reply_to_message_id")
                    if reply_to and reply_to in discussion_authors:
                        author = d.get("user_id")
                        target_author = discussion_authors[reply_to]
                        if author and target_author and author != target_author:
                            if (
                                isinstance(author, int)
                                and author < 0
                                and str(author).startswith("-100")
                            ):
                                continue
                            if (
                                isinstance(target_author, int)
                                and target_author < 0
                                and str(target_author).startswith("-100")
                            ):
                                continue
                            if (
                                str(author) not in channel_id_map.values()
                                and str(target_author) not in channel_id_map.values()
                            ):
                                discussion_reply_pairs[(author, target_author)] += 1
                                replier_users.add(author)
                                replier_users.add(target_author)

            all_needed_users = forward_users_to_add | replier_users
            for uid in all_needed_users:
                if uid:
                    if isinstance(uid, int) and uid < 0 and str(uid).startswith("-100"):
                        continue
                    if str(uid) == str(numeric_id):
                        continue
                    self._ensure_user_node(graph, uid, all_users)

            edge_batch = []
            for u1, reps in reply_counter.items():
                for u2, cnt in reps.items():
                    if cnt >= min_replies:
                        if str(u1) == str(numeric_id):
                            edge_nodes = (channel_node, f"user:{u2}")
                            if graph.has_edge(*edge_nodes):
                                old = graph.get_edge_data(*edge_nodes)
                                old["reply_weight"] = old.get("reply_weight", 0) + cnt
                                old["is_channel_reply"] = True
                            else:
                                edge_batch.append(
                                    (*edge_nodes, {
                                        "edge_type": "replier",
                                        "weight": cnt,
                                        "is_channel_reply": True,
                                    })
                                )
                        elif str(u2) == str(numeric_id):
                            edge_nodes = (channel_node, f"user:{u1}")
                            if graph.has_edge(*edge_nodes):
                                old = graph.get_edge_data(*edge_nodes)
                                old["reply_weight"] = old.get("reply_weight", 0) + cnt
                                old["is_channel_reply"] = True
                            else:
                                edge_batch.append(
                                    (*edge_nodes, {
                                        "edge_type": "replier",
                                        "weight": cnt,
                                        "is_channel_reply": True,
                                    })
                                )
                        else:
                            edge_batch.append(
                                (
                                    f"user:{u1}",
                                    f"user:{u2}",
                                    {"edge_type": "replier", "weight": cnt},
                                )
                            )

            if include_forwarded:
                for src, tgts in forward_counter.items():
                    for dst, cnt in tgts.items():
                        if str(src) == str(numeric_id):
                            edge_batch.append(
                                (
                                    channel_node,
                                    f"user:{dst}",
                                    {
                                        "edge_type": "forwarded",
                                        "weight": cnt,
                                        "is_channel_forward": True,
                                    },
                                )
                            )
                        elif str(dst) == str(numeric_id):
                            edge_batch.append(
                                (
                                    channel_node,
                                    f"user:{src}",
                                    {
                                        "edge_type": "forwarded",
                                        "weight": cnt,
                                        "is_channel_forward": True,
                                    },
                                )
                            )
                        else:
                            edge_batch.append(
                                (
                                    f"user:{src}",
                                    f"user:{dst}",
                                    {"edge_type": "forwarded", "weight_forward": cnt},
                                )
                            )

            for (u1, u2), cnt in discussion_reply_pairs.items():
                if cnt >= min_replies:
                    edge_batch.append(
                        (
                            f"user:{u1}",
                            f"user:{u2}",
                            {"edge_type": "discussion_reply", "weight": cnt},
                        )
                    )

            graph.add_edges_from(edge_batch)

            if include_links:
                links = self.get_links(db_path, channel, start_date, end_date)
                log_callback(f"Channel '{channel}': {len(links)} links found")

                from urllib.parse import urlparse

                user_domains = defaultdict(set)
                for link in links:
                    url = link.get("url")
                    if not url:
                        continue
                    parsed = urlparse(url)
                    domain = parsed.netloc or parsed.path.split("/")[0]
                    post_id = link.get("post_id")
                    if post_id and post_id in post_author:
                        user_id = post_author[post_id]
                        user_domains[user_id].add(domain)

                link_edges_batch = []
                for user_id, domains in user_domains.items():
                    if (
                        isinstance(user_id, int)
                        and user_id < 0
                        and str(user_id).startswith("-100")
                    ):
                        continue
                    user_node = self._ensure_user_node(graph, user_id, all_users)
                    for domain in domains:
                        domain_node = f"domain:{domain}"
                        if domain_node not in graph:
                            graph.add_node(
                                domain_node, node_type="domain", label=domain
                            )
                        link_edges_batch.append(
                            (user_node, domain_node, {"edge_type": "mentions"})
                        )
                graph.add_edges_from(link_edges_batch)

        if len(channels) > 1 and include_cross_channel:
            cross_channel_edges = self.get_cross_channel_members(db_path, channels)
            for (ch1, ch2), shared_users in cross_channel_edges.items():
                if shared_users:
                    ch1_node = f"channel:{ch1}"
                    ch2_node = f"channel:{ch2}"
                    if graph.has_node(ch1_node) and graph.has_node(ch2_node):
                        graph.add_edge(
                            ch1_node,
                            ch2_node,
                            edge_type="shared_members",
                            weight=len(shared_users),
                            shared_users=list(shared_users)[:10],
                        )

        # debug: count edge types
        edge_types = defaultdict(int)
        for _, _, d in graph.edges(data=True):
            edge_types[d.get("edge_type", "unknown")] += 1
        user2user = 0
        channel2user = 0
        for u, v, d in graph.edges(data=True):
            if d.get("edge_type") in ("replier", "forwarded", "discussion_reply"):
                if u.startswith("user:") and v.startswith("user:"):
                    user2user += 1
                else:
                    channel2user += 1
        logger.debug(
            "_build_graph_impl: edges total={} member={} replier={} forwarded={} discussion_reply={} user2user={} channel2user={}",
            graph.number_of_edges(),
            edge_types.get("member", 0),
            edge_types.get("replier", 0),
            edge_types.get("forwarded", 0),
            edge_types.get("discussion_reply", 0),
            user2user,
            channel2user,
        )

        return graph

    def print_graph_stats(self, graph, log_callback=print):
        log_callback("\n" + divider("=", 50))
        log_callback(title("Graph Statistics"))
        log_callback(divider("=", 50))
        log_callback(kv("Total nodes", graph.number_of_nodes()))
        log_callback(kv("Total edges", graph.number_of_edges()))

        node_types = defaultdict(int)
        for n, d in graph.nodes(data=True):
            node_types[d.get("node_type", "unknown")] += 1
        log_callback("\n" + section("Node types"))
        for t, cnt in node_types.items():
            log_callback(line(f"{t}: {cnt}"))

        edge_types = defaultdict(int)
        for u, v, d in graph.edges(data=True):
            edge_types[d.get("edge_type", "unknown")] += 1
        log_callback("\n" + section("Edge types"))
        for t, cnt in edge_types.items():
            log_callback(line(f"{t}: {cnt}"))

        user_nodes = [
            n for n, d in graph.nodes(data=True) if d.get("node_type") == "user"
        ]
        if user_nodes:
            degrees = [d for n, d in graph.degree(user_nodes)]
            if degrees:
                log_callback(
                    "\n" + line(f"User node degree: min={min(degrees)}, max={max(degrees)}, avg={sum(degrees) / len(degrees):.2f}")
                )
            bot_count = sum(
                1
                for n, d in graph.nodes(data=True)
                if d.get("node_type") == "user" and d.get("bot")
            )
            verified_count = sum(
                1
                for n, d in graph.nodes(data=True)
                if d.get("node_type") == "user" and d.get("verified")
            )
            premium_count = sum(
                1
                for n, d in graph.nodes(data=True)
                if d.get("node_type") == "user" and d.get("premium")
            )
            log_callback(line(f"Bots: {bot_count}"))
            log_callback(line(f"Verified: {verified_count}"))
            log_callback(line(f"Premium: {premium_count}"))

    def export_graph(
        self,
        graph,
        output_path,
        formats=None,
        log_callback=print,
        db_path=None,
        channels=None,
        min_replies=2,
        include_forwarded=True,
        include_discussion_replies=True,
        start_date=None,
        end_date=None,
    ):
        if formats is None:
            formats = ["graphml"]
        base = os.path.join(output_path, "graph")

        def clean_attrs(attrs):
            if attrs is None:
                return {}
            return {k: ("" if v is None else v) for k, v in attrs.items()}

        graph_clean = nx.Graph()
        graph_clean.graph.update(clean_attrs(graph.graph))
        for node, attrs in graph.nodes(data=True):
            graph_clean.add_node(node, **clean_attrs(attrs))
        for u, v, attrs in graph.edges(data=True):
            graph_clean.add_edge(u, v, **clean_attrs(attrs))

        if "graphml" in formats:
            try:
                nx.write_graphml(graph_clean, base + ".graphml")
                log_callback(f"GraphML saved to {base}.graphml")
            except Exception as e:
                log_callback(f"GraphML save error: {e}")

        if "gexf" in formats:
            try:
                nx.write_gexf(graph_clean, base + ".gexf")
                log_callback(f"GEXF saved to {base}.gexf")
            except Exception as e:
                log_callback(f"GEXF save error: {e}")

        if "json" in formats:
            try:
                json_data = json_graph.node_link_data(graph_clean)
                with open(base + ".json", "w") as f:
                    json.dump(json_data, f, indent=2)
                log_callback(f"JSON (node-link) saved to {base}.json")
            except Exception as e:
                log_callback(f"JSON save error: {e}")

        if "csv-nodes" in formats:
            import csv

            with open(base + "_nodes.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                attr_keys = set()
                for n, d in graph_clean.nodes(data=True):
                    attr_keys.update(d.keys())
                attr_keys = sorted(attr_keys)
                writer.writerow(["id"] + attr_keys)
                for n, d in graph_clean.nodes(data=True):
                    row = [n] + [d.get(k, "") for k in attr_keys]
                    writer.writerow(row)
            log_callback(f"CSV nodes saved to {base}_nodes.csv")

        if "csv-edges" in formats:
            import csv

            with open(base + "_edges.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                attr_keys = set()
                for u, v, d in graph_clean.edges(data=True):
                    attr_keys.update(d.keys())
                attr_keys = sorted(attr_keys)
                writer.writerow(["source", "target"] + attr_keys)
                for u, v, d in graph_clean.edges(data=True):
                    row = [u, v] + [d.get(k, "") for k in attr_keys]
                    writer.writerow(row)
            log_callback(f"CSV edges saved to {base}_edges.csv")

        if "html" in formats:
            self.visualize_interactive(
                graph_clean, output_path, log_callback=log_callback
            )

        if "obsidian" in formats and db_path:
            self.export_to_obsidian(
                db_path,
                output_path,
                channels=channels,
                min_replies=min_replies,
                include_forwarded=include_forwarded,
                include_discussion_replies=include_discussion_replies,
                start_date=start_date,
                end_date=end_date,
                log_callback=log_callback,
            )

    def export_to_obsidian(
        self,
        db_path,
        output_path,
        channels=None,
        min_replies=2,
        include_forwarded=True,
        include_discussion_replies=True,
        start_date=None,
        end_date=None,
        log_callback=print,
    ):
        import json as json_module
        import re

        def sanitize_filename(name):
            name = re.sub(r'[<>:"/\\|?*]', "_", name)
            return name.strip()

        def get_safe_link_name(info):
            if info.get("username"):
                return info["username"]
            name = f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
            if name:
                return sanitize_filename(name)
            return f"User_{info.get('user_id', 'unknown')}"

        def parse_json_field(data):
            if not data:
                return None
            try:
                return json_module.loads(data)
            except Exception:
                return data

        def format_user_markdown(info, connections, channel_username):
            lines = []
            lines.append(f"# {get_safe_link_name(info)}\n")
            lines.append("## Basic Info")
            lines.append(f"- **User ID**: {info.get('user_id', 'N/A')}")
            username = info.get("username")
            lines.append(
                f"- **Username**: @{username}" if username else "- **Username**: N/A"
            )
            first_name = info.get("first_name")
            if first_name:
                lines.append(f"- **First Name**: {first_name}")
            last_name = info.get("last_name")
            if last_name:
                lines.append(f"- **Last Name**: {last_name}")
            phone = info.get("phone")
            if phone:
                lines.append(f"- **Phone**: {phone}")
            status = info.get("status")
            if status:
                lines.append(f"- **Status**: {status}")
            was_online = info.get("was_online")
            if was_online:
                lines.append(f"- **Last Seen**: {was_online}")
            about = info.get("about")
            if about:
                lines.append(f"- **Bio**: {about}")

            flags = []
            for flag in (
                "bot",
                "verified",
                "premium",
                "scam",
                "fake",
                "deleted",
                "restricted",
            ):
                if info.get(flag):
                    flags.append(flag.capitalize())
            if flags:
                lines.append(f"- **Flags**: {', '.join(flags)}")

            lang_code = info.get("lang_code")
            if lang_code:
                lines.append(f"- **Language**: {lang_code}")

            birthday_d = info.get("birthday_day")
            birthday_m = info.get("birthday_month")
            birthday_y = info.get("birthday_year")
            if birthday_d and birthday_m:
                month_names = [
                    "",
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ]
                bday_str = f"{birthday_d} {month_names[birthday_m]}"
                if birthday_y:
                    bday_str += f" {birthday_y}"
                lines.append(f"- **Birthday**: {bday_str}")

            biz_location = parse_json_field(info.get("business_location"))
            if biz_location:
                addr = biz_location.get("address") or ""
                geo = biz_location.get("geo") or {}
                lat = geo.get("lat") or ""
                lng = geo.get("long") or ""
                if lat and lng:
                    addr += f" ({lat}, {lng})" if addr else f"Geo: {lat}, {lng}"
                if addr:
                    lines.append(f"- **Business Location**: {addr}")

            biz_hours = parse_json_field(info.get("business_work_hours"))
            if biz_hours:
                tz = biz_hours.get("timezone_id")
                if tz:
                    lines.append(f"- **Business Hours**: Timezone: {tz}")

            lines.append("")
            lines.append("## Channels")
            lines.append(f"- Member of: [[{channel_username}]]\n")

            if connections:
                lines.append("## Connections")
                other_users = [
                    c for c in connections if c.get("user_id") != info.get("user_id")
                ]
                if other_users:
                    lines.append("Interacts with:")
                    for conn in other_users[:20]:
                        lines.append(f"- [[{get_safe_link_name(conn)}]]")
                    if len(other_users) > 20:
                        lines.append(f"- _... and {len(other_users) - 20} more_")
                lines.append("")

            avatar_paths = info.get("avatar_paths")
            if avatar_paths:
                lines.append("## Media")
                paths = (
                    avatar_paths.split("|") if "|" in avatar_paths else [avatar_paths]
                )
                for p in paths[:5]:
                    if p:
                        lines.append(f"![avatar]({p})")
                lines.append("")

            return "\n".join(lines)

        def format_channel_markdown(
            channel_info, members, posts_count, discussions_count
        ):
            lines = []
            title = (
                channel_info.get("title")
                or channel_info.get("username")
                or "Unknown Channel"
            )
            lines.append(f"# {title}\n")
            lines.append("## Channel Info")
            lines.append(f"- **Channel ID**: {channel_info.get('channel_id', 'N/A')}")
            username = channel_info.get("username")
            if username:
                lines.append(f"- **Username**: @{username}")
            access_hash = channel_info.get("access_hash")
            if access_hash:
                lines.append(f"- **Access Hash**: {access_hash}")
            created_at = channel_info.get("created_at")
            if created_at:
                lines.append(f"- **Created**: {created_at}")
            lines.append(f"- **Members**: {len(members)}")
            lines.append(f"- **Posts**: {posts_count}")
            lines.append(f"- **Discussions**: {discussions_count}")
            lines.append("")
            lines.append("## Members")
            for m in members[:50]:
                lines.append(f"- [[{get_safe_link_name(m)}]]")
            if len(members) > 50:
                lines.append(f"- _... and {len(members) - 50} more members_")
            lines.append("")
            return "\n".join(lines)

        try:
            log_callback("Starting Obsidian export...")
            graph_dir = os.path.join(output_path, "GRAPH")
            os.makedirs(graph_dir, exist_ok=True)

            all_channels = self.get_channels(db_path)
            if channels is None:
                channels = all_channels
            else:
                channels = [ch for ch in channels if ch in all_channels]

            db_file = db_path if not os.path.isdir(db_path) else os.path.join(db_path, "SkyFall_TG.db")
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row

            for channel in channels:
                channel_dir = os.path.join(graph_dir, sanitize_filename(channel))
                os.makedirs(channel_dir, exist_ok=True)

                cursor = conn.cursor()
                cursor.execute("SELECT * FROM channels WHERE username = ?", (channel,))
                chan_row = cursor.fetchone()
                channel_info = dict(chan_row) if chan_row else {}

                members = []
                cursor.execute(
                    """SELECT u.* FROM members m
                       LEFT JOIN users u ON m.user_id = u.user_id
                       JOIN channels c ON m.channel_id = c.channel_id
                       WHERE c.username = ?""",
                    (channel,),
                )
                for row in cursor.fetchall():
                    members.append(dict(row))

                cursor.execute(
                    "SELECT COUNT(*) FROM posts p JOIN channels c ON p.channel_id = c.channel_id WHERE c.username = ?",
                    (channel,),
                )
                posts_count = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COUNT(*) FROM discussions d JOIN channels c ON d.channel_id = c.channel_id WHERE c.username = ?",
                    (channel,),
                )
                discussions_count = cursor.fetchone()[0] or 0

                channel_md = format_channel_markdown(
                    channel_info, members, posts_count, discussions_count
                )
                with open(
                    os.path.join(channel_dir, f"{channel}.md"), "w", encoding="utf-8"
                ) as f:
                    f.write(channel_md)
                log_callback(f"Created: {os.path.join(channel_dir, f'{channel}.md')}")

                member_dict = {m.get("user_id"): m for m in members if m.get("user_id")}
                posts = self.get_posts(db_path, channel, start_date, end_date)
                discussions = self.get_discussions(
                    db_path, channel, start_date, end_date
                )

                post_author = {}
                reply_counter = defaultdict(lambda: defaultdict(int))
                discussion_reply_pairs = defaultdict(int)
                discussion_authors = {}
                forward_counter = defaultdict(lambda: defaultdict(int))

                for p in posts:
                    post_id = p.get("post_id")
                    user_id = p.get("user_id")
                    if post_id and user_id:
                        post_author[post_id] = user_id
                    if (
                        include_forwarded
                        and p.get("is_forwarded")
                        and p.get("forwarded_from_id")
                        and user_id
                    ):
                        src = p["forwarded_from_id"]
                        dst = user_id
                        if src != dst:
                            forward_counter[src][dst] += 1

                for d in discussions:
                    msg_id = d.get("message_id")
                    user_id = d.get("user_id")
                    if msg_id and user_id:
                        discussion_authors[msg_id] = user_id
                    post_id = d.get("post_id")
                    if post_id in post_author:
                        author = post_author[post_id]
                        if author != user_id:
                            reply_counter[author][user_id] += 1

                if include_discussion_replies:
                    for d in discussions:
                        reply_to = d.get("reply_to_message_id")
                        if reply_to and reply_to in discussion_authors:
                            author = d.get("user_id")
                            target_author = discussion_authors[reply_to]
                            if author and target_author and author != target_author:
                                discussion_reply_pairs[(author, target_author)] += 1

                all_users = self.get_all_users(db_path)

                connections_by_user = defaultdict(set)
                for u1, reps in reply_counter.items():
                    for u2, cnt in reps.items():
                        if cnt >= min_replies:
                            connections_by_user[u1].add(u2)
                            connections_by_user[u2].add(u1)
                for (u1, u2), cnt in discussion_reply_pairs.items():
                    if cnt >= min_replies:
                        connections_by_user[u1].add(u2)
                        connections_by_user[u2].add(u1)
                if include_forwarded:
                    for src, tgts in forward_counter.items():
                        for dst, cnt in tgts.items():
                            if cnt >= min_replies:
                                connections_by_user[src].add(dst)
                                connections_by_user[dst].add(src)

                for member in members:
                    link_name = get_safe_link_name(member)
                    user_id = member.get("user_id")
                    connected_user_ids = connections_by_user.get(user_id, set())

                    connections = []
                    for uid in connected_user_ids:
                        if uid in member_dict:
                            connections.append(member_dict[uid])
                        elif uid in all_users:
                            connections.append(all_users[uid])

                    user_md = format_user_markdown(member, connections, channel)
                    with open(
                        os.path.join(channel_dir, f"{link_name}.md"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        f.write(user_md)
                    log_callback(
                        f"Created: {os.path.join(channel_dir, f'{link_name}.md')}"
                    )

            conn.close()
            log_callback(f"Obsidian export completed! Files saved to: {graph_dir}")
            return True
        except Exception as e:
            log_callback(f"Error exporting to Obsidian: {e}")
            import traceback

            traceback.print_exc()
            return False

    def visualize_interactive(self, graph, output_path, log_callback=print):
        if not PYVIS_AVAILABLE or Network is None:
            log_callback("pyvis not installed, skipping HTML export.")
            return

        net = Network(
            height="100vh",
            width="100%",
            bgcolor="#011627",
            cdn_resources="in_line",
        )

        physics_options = {
            "physics": {
                "enabled": True,
                "solver": "repulsion",
                "repulsion": {
                    "nodeDistance": 250,
                    "centralGravity": 0.5,
                    "springLength": 300,
                    "springConstant": 0.05,
                    "damping": 0.09,
                },
                "stabilization": {
                    "enabled": True,
                    "iterations": 200,
                    "updateInterval": 25,
                },
            },
            "interaction": {
                "dragNodes": True,
                "dragView": True,
                "zoomView": True,
                "hoverConnectedEdges": True,
            },
        }
        net.set_options(json.dumps(physics_options))

        node_info = {}

        for node, attrs in graph.nodes(data=True):
            node_type = attrs.get("node_type", "unknown")
            label = attrs.get("label", str(node))

            if node_type == "user":
                avatar_url = None
                avatar_path = attrs.get("avatar_path")
                if avatar_path and os.path.isfile(avatar_path):
                    try:
                        with open(avatar_path, "rb") as f:
                            import base64
                            b64 = base64.b64encode(f.read()).decode()
                            ext = os.path.splitext(avatar_path)[1].lstrip(".") or "jpg"
                            avatar_url = f"data:image/{ext};base64,{b64}"
                    except Exception:
                        pass
                info = {
                    "type": "user",
                    "user_id": node.split(":")[1] if ":" in node else node,
                    "username": attrs.get("username", ""),
                    "first_name": attrs.get("first_name", ""),
                    "last_name": attrs.get("last_name", ""),
                    "phone": attrs.get("phone", ""),
                    "bot": attrs.get("bot", False),
                    "verified": attrs.get("verified", False),
                    "premium": attrs.get("premium", False),
                    "scam": attrs.get("scam", False),
                    "fake": attrs.get("fake", False),
                    "deleted": attrs.get("deleted", False),
                    "business_work_hours": attrs.get("business_work_hours"),
                    "business_location": attrs.get("business_location"),
                    "business_greeting_message": attrs.get("business_greeting_message"),
                    "business_away_message": attrs.get("business_away_message"),
                    "business_intro": attrs.get("business_intro"),
                    "birthday_day": attrs.get("birthday_day"),
                    "birthday_month": attrs.get("birthday_month"),
                    "birthday_year": attrs.get("birthday_year"),
                    "avatar_url": avatar_url,
                }
            elif node_type == "channel":
                channel_name = node.split(":")[1] if ":" in node else node
                info = {
                    "type": "channel",
                    "channel_id": attrs.get("numeric_id") or channel_name,
                    "name": label,
                }
            elif node_type == "domain":
                info = {"type": "domain", "domain": label}
            elif node_type == "discussion_chat":
                info = {"type": "discussion_chat", "name": label}
            else:
                info = {"type": "unknown", "label": label}

            node_info[node] = info

            if node_type == "channel":
                size, color = 50, "#7caf7c"
            elif node_type == "user":
                color = "#e74c3c" if attrs.get("bot", False) else "#82aaff"
                size = 15 + 5 * (
                    bool(attrs.get("bot", False)) or bool(attrs.get("verified", False))
                )
            elif node_type == "domain":
                size, color = 20, "#bdc1c6"
            elif node_type == "discussion_chat":
                size, color = 40, "#f39c12"
            else:
                size, color = 10, "#12293C"

            net.add_node(
                node,
                label=label,
                size=size,
                color=color,
                font={"color": "#bdc1c6", "strokeWidth": 0},
            )

        message_counts = []
        for src, dst, attrs in graph.edges(data=True):
            edge_type = attrs.get("edge_type", "")
            if edge_type in ("replier", "forwarded", "discussion_reply"):
                src_is_user = src.startswith("user:")
                dst_is_user = dst.startswith("user:")
                if src_is_user and dst_is_user:
                    weight = attrs.get("weight_forward", attrs.get("weight", 0))
                    message_counts.append(weight)
            elif edge_type == "member" and attrs.get("is_channel_reply"):
                message_counts.append(attrs.get("reply_weight", 0))
        max_message_count = max(message_counts) if message_counts else 0

        for src, dst, attrs in graph.edges(data=True):
            edge_type = attrs.get("edge_type", "unknown")
            is_channel_edge = attrs.get("is_channel_reply") or attrs.get(
                "is_channel_forward"
            )
            dashes = False
            if edge_type == "member":
                if attrs.get("is_channel_reply"):
                    rw = attrs.get("reply_weight", 0)
                    pct = rw / max_message_count if max_message_count > 0 else 0
                    color = "#5dade2" if pct < 0.2 else "#f7dc6f" if pct < 0.5 else "#ff7675"
                    width = 1
                else:
                    color, width = "#6c7a89", 1
            elif edge_type in ("replier", "forwarded", "discussion_reply"):
                if edge_type == "forwarded":
                    weight = attrs.get("weight_forward", attrs.get("weight", 0))
                else:
                    weight = attrs.get("weight", 0)
                src_is_user = src.startswith("user:")
                dst_is_user = dst.startswith("user:")
                if src_is_user and dst_is_user:
                    pct = weight / max_message_count if max_message_count > 0 else 0
                    if pct < 0.2:
                        color = "#5dade2"
                    elif pct < 0.5:
                        color = "#f7dc6f"
                    else:
                        color = "#ff7675"
                elif is_channel_edge:
                    color = "#ff7675"
                else:
                    if edge_type == "replier":
                        color = "#58d68d"
                    elif edge_type == "forwarded":
                        color = "#bb8fce"
                    else:
                        color = "#f0b27a"
                width = 1
            else:
                color, width = "#6c7a89", 1

            if dashes:
                net.add_edge(src, dst, color=color, width=width, dashes=[5, 5])
            else:
                net.add_edge(src, dst, color=color, width=width)

        html_file = os.path.join(output_path, "graph.html")
        net.write_html(html_file, notebook=False)

        with open(html_file, encoding="utf-8") as f:
            html_content = f.read()

        node_info_json = json.dumps(node_info, ensure_ascii=False)

        sidebar_html = """
        <div id="info-sidebar" class="sidebar" style="display: none;">
            <div class="sidebar-header">
                <h3 class="sidebar-title">Node Info</h3>
                <button id="close-sidebar" class="close-btn" aria-label="Close">✕</button>
            </div>
            <div id="sidebar-content" class="sidebar-content"></div>
        </div>
        """

        style_css = """
        <style>
            html, body { margin: 0; padding: 0; width: 100vw; height: 100vh; overflow: hidden; background-color: #011627; font-family: "Courier New", monospace; font-size: 10pt; }
            #mynetwork { position: absolute; top: 0; left: 0; padding: 0px; margin: 0px; width: 100vw; height: 100vh; border: none; background-color: #011627 !important; }
            .vis-network { background-color: #011627 !important; }
            .vis-network canvas { background-color: #011627; }
            .card { background-color: transparent; padding: 0px; margin: 0px; }
            .sidebar { position: fixed; top: 24px; right: 24px; width: 360px; max-height: calc(100vh - 48px); background: #011627; border: 1px solid #12293C; border-radius: 10px; box-shadow: 0 0 15px rgba(0,0,0,0.5); color: #bdc1c6; z-index: 1000; overflow-y: auto; padding: 20px; transition: opacity 0.25s ease, transform 0.2s ease; font-family: "Courier New", monospace; font-size: 10pt; scrollbar-width: thin; scrollbar-color: #82aaff #011627; }
            .sidebar::-webkit-scrollbar { width: 6px; }
            .sidebar::-webkit-scrollbar-track { background: #011627; }
            .sidebar::-webkit-scrollbar-thumb { background: #12293C; border-radius: 10px; }
            .sidebar::-webkit-scrollbar-thumb:hover { background: #82aaff; }
            .sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid #12293C; }
            .sidebar-title { margin: 0; font-size: 10pt; font-weight: bold; color: #7caf7c; }
            .close-btn { background: transparent; border: 0px solid #82aaff; color: #bdc1c6; font-size: 18px; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; line-height: 1; padding: 0; }
            .close-btn:hover { color: #82aaff; }
            .sidebar-content { font-size: 10pt; line-height: 1.5; }
            .field-row { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; padding: 8px 10px; background-color: #12293C; border: 0px solid #82aaff; border-radius: 10px; }
            .field-label { color: #82aaff; font-size: 10pt; font-weight: bold; }
            .field-value { color: #bdc1c6; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: right; font-family: "Courier New", monospace; font-size: 10pt; }
            .copy-btn { background-color: #12293C; border: 0px solid #82aaff; color: #bdc1c6; border-radius: 10px; padding: 10px 18px; font-size: 10pt; cursor: pointer; transition: background 0.2s; margin-top: 16px; width: 100%; text-align: center; font-family: "Courier New", monospace; }
            .copy-btn:hover { background-color: #82aaff; color: #011627; }
            .copy-btn:active { transform: scale(0.98); }
        </style>
        """

        script = f"""
        <script type="text/javascript">
        var nodeInfo = {node_info_json};
        var currentNodeId = null;

        function formatBirthday(day, month, year) {{
            if (!day || !month) return null;
            var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            var dateStr = day + ' ' + months[month - 1];
            if (year) dateStr += ' ' + year;
            return dateStr;
        }}

        function formatBusinessInfo(data) {{
            if (!data) return null;
            try {{ var obj = JSON.parse(data); if (obj.timezone_id) return 'Timezone: ' + obj.timezone_id; if (obj.address) return obj.address; if (obj.geo && obj.geo.lat) return obj.geo.lat + ', ' + obj.geo.long; return JSON.stringify(obj); }} catch(e) {{ return data; }}
        }}

        function formatBusinessMessage(data) {{
            if (!data) return null;
            try {{ var obj = JSON.parse(data); if (obj.title && obj.message) return obj.title + ': ' + obj.message; if (obj.title) return obj.title; return obj.message || data; }} catch(e) {{ return data; }}
        }}

        function closeSidebar() {{ document.getElementById('info-sidebar').style.display = 'none'; }}

        function showNodeInfo(nodeId) {{
            var info = nodeInfo[nodeId];
            if (!info) return;
            var contentDiv = document.getElementById('sidebar-content');
            var html = '';
            var typeLabel = info.type === 'user' ? 'USER' : info.type === 'channel' ? 'CHANNEL' : info.type === 'domain' ? 'DOMAIN' : info.type === 'discussion_chat' ? 'DISCUSSION CHAT' : 'NODE';
            html += '<div style="margin-bottom: 12px; font-weight: bold; color: #82aaff; font-size: 10pt;">' + typeLabel + '</div>';
            if (info.avatar_url) {{
                html += '<div style="text-align: center; margin-bottom: 16px;"><img src="' + info.avatar_url + '" style="width: 80px; height: 80px; border-radius: 50%; border: 2px solid #82aaff; object-fit: cover;" alt="avatar"></div>';
            }}
            var fields = [];
            if (info.type === 'user') {{
                fields = [
                    ['User ID', info.user_id], ['Username', info.username ? '@' + info.username : null],
                    ['First Name', info.first_name], ['Last Name', info.last_name],
                    ['Phone', info.phone], ['Bot', info.bot ? 'Yes' : 'No'],
                    ['Verified', info.verified ? 'Yes' : 'No'], ['Premium', info.premium ? 'Yes' : 'No'],
                    ['Scam', info.scam ? 'Yes' : null], ['Fake', info.fake ? 'Yes' : null],
                    ['Deleted', info.deleted ? 'Yes' : null],
                    ['Birthday', formatBirthday(info.birthday_day, info.birthday_month, info.birthday_year)],
                    ['Business Hours', formatBusinessInfo(info.business_work_hours)],
                    ['Business Location', formatBusinessInfo(info.business_location)],
                    ['Greeting Message', formatBusinessMessage(info.business_greeting_message)],
                    ['Away Message', formatBusinessMessage(info.business_away_message)],
                    ['Business Intro', formatBusinessMessage(info.business_intro)]
                ];
            }} else if (info.type === 'channel') {{
                fields = [['Channel ID', info.channel_id], ['Name', info.name]];
            }} else if (info.type === 'domain') {{
                fields = [['Domain', info.domain]];
            }} else if (info.type === 'discussion_chat') {{
                fields = [['Name', info.name]];
            }} else {{
                fields = [['Node ID', nodeId], ['Label', info.label]];
            }}
            for (var i = 0; i < fields.length; i++) {{
                var key = fields[i][0], val = fields[i][1];
                if (val !== null && val !== '' && val !== undefined) {{
                    html += '<div class="field-row"><span class="field-label">' + key + ':</span><span class="field-value" title="' + val + '">' + val + '</span></div>';
                }}
            }}
            html += '<button class="copy-btn" onclick="copyAll()">Copy All Info</button>';
            contentDiv.innerHTML = html;
            currentNodeId = nodeId;
            document.getElementById('info-sidebar').style.display = 'block';
        }}

        function copyAll() {{ if (currentNodeId) navigator.clipboard.writeText(JSON.stringify(nodeInfo[currentNodeId], null, 2)); }}

        document.addEventListener('click', function(e) {{
            var sidebar = document.getElementById('info-sidebar');
            if (sidebar.style.display === 'block' && !sidebar.contains(e.target) && !e.target.closest('.vis-network canvas')) closeSidebar();
        }});
        document.getElementById('close-sidebar').addEventListener('click', closeSidebar);
        network.on('click', function(params) {{ if (params.nodes.length > 0) showNodeInfo(params.nodes[0]); }});
        network.on('dragStart', function() {{ closeSidebar(); }});
        network.on('zoom', function() {{ closeSidebar(); }});
        </script>
        """

        combined = style_css + sidebar_html + script
        html_content = html_content.replace("</body>", combined + "\n</body>")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        log_callback(f"Interactive HTML saved to {html_file}")

    def visualize_graph(self, graph, output_path, layout="spring"):
        if graph.number_of_nodes() == 0:
            logger.warning("Graph is empty, skipping PNG export.")
            return

        plt.style.use("dark_background")
        plt.figure(figsize=(16, 12), facecolor="black")

        if layout == "spring":
            pos = nx.spring_layout(graph, k=2, iterations=50)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(graph)
        else:
            pos = nx.spring_layout(graph, k=2, iterations=50)

        channel_nodes = [
            n for n, d in graph.nodes(data=True) if d.get("node_type") == "channel"
        ]
        user_nodes = [
            n for n, d in graph.nodes(data=True) if d.get("node_type") == "user"
        ]
        domain_nodes = [
            n for n, d in graph.nodes(data=True) if d.get("node_type") == "domain"
        ]
        discussion_nodes = [
            n
            for n, d in graph.nodes(data=True)
            if d.get("node_type") == "discussion_chat"
        ]

        if channel_nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=channel_nodes,
                node_color="#3c8c3c",
                node_size=800,
                label="Channels",
            )
        if user_nodes:
            bot_nodes = [n for n in user_nodes if graph.nodes[n].get("bot", False)]
            normal_nodes = [
                n for n in user_nodes if not graph.nodes[n].get("bot", False)
            ]
            if normal_nodes:
                nx.draw_networkx_nodes(
                    graph,
                    pos,
                    nodelist=normal_nodes,
                    node_color="#7caf7c",
                    node_size=300,
                    label="Users",
                )
            if bot_nodes:
                nx.draw_networkx_nodes(
                    graph,
                    pos,
                    nodelist=bot_nodes,
                    node_color="#e74c3c",
                    node_size=250,
                    label="Bots",
                )
        if domain_nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=domain_nodes,
                node_color="#e6b800",
                node_size=200,
                label="Domains",
            )
        if discussion_nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=discussion_nodes,
                node_color="#f39c12",
                node_size=400,
                label="Discussion Chats",
            )

        member_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == "member"
        ]
        replier_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == "replier"
        ]
        forwarded_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == "forwarded"
        ]
        mention_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == "mentions"
        ]
        discussion_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == "discussion_reply"
        ]
        linked_edges = [
            (u, v)
            for u, v, d in graph.edges(data=True)
            if d.get("edge_type") == "linked_chat"
        ]

        if member_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=member_edges,
                edge_color="#4a4a4a",
                width=1,
                alpha=0.6,
            )
        if replier_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=replier_edges,
                edge_color="#7caf7c",
                width=1,
                alpha=0.7,
                label="Replies",
            )
        if forwarded_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=forwarded_edges,
                edge_color="#9b59b6",
                width=1,
                alpha=0.6,
                label="Forwards",
            )
        if mention_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=mention_edges,
                edge_color="#f1c40f",
                width=1,
                alpha=0.5,
                style="dashed",
                label="Mentions",
            )
        if discussion_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=discussion_edges,
                edge_color="#e67e22",
                width=1,
                alpha=0.6,
                style="dashed",
                label="Discussion Replies",
            )
        if linked_edges:
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=linked_edges,
                edge_color="#f39c12",
                width=1,
                alpha=0.8,
                style="dashed",
                label="Linked Chat",
            )

        labels = {n: d.get("label", n) for n, d in graph.nodes(data=True)}
        nx.draw_networkx_labels(
            graph,
            pos,
            labels,
            font_size=8,
            font_family="Courier New",
            font_color="#7caf7c",
        )

        plt.title(
            "Telegram Channel Interaction Graph",
            color="#7caf7c",
            fontfamily="Courier New",
        )
        plt.legend(facecolor="black", edgecolor="#3c8c3c", labelcolor="#7caf7c")
        plt.axis("off")
        plt.tight_layout()

        png_file = os.path.join(output_path, "graph.png")
        plt.savefig(png_file, dpi=150, bbox_inches="tight", facecolor="black")
        plt.close()
        logger.info(f"PNG exported to {png_file}")

    def run_analysis(self, params, log_callback=print, progress_callback=None):
        db_path = params.get("db_path")
        channels = params.get("channels")
        min_replies = params.get("min_replies", 2)
        include_forwarded = params.get("include_forwarded", True)
        include_links = params.get("include_links", False)
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        formats = params.get("formats", ["graphml", "png"])

        logger.debug(
            "run_analysis: params={}",
            {k: v for k, v in params.items() if k not in ("formats",)},
        )
        logger.debug("run_analysis: db_path={}, channels={}", db_path, channels)
        if os.path.isdir(db_path):
            resolved = os.path.join(db_path, "SkyFall_TG.db")
            logger.debug("run_analysis: resolved dir to db file: {}", resolved)

        if os.path.isdir(db_path):
            output_dir = db_path
        else:
            output_dir = os.path.dirname(db_path) or "."
        Path(output_dir).mkdir(exist_ok=True)
        logger.debug("run_analysis: output_dir='{}'", output_dir)

        if progress_callback:
            progress_callback(5)

        log_callback("Building graph...")
        graph = self.build_graph(
            db_path=db_path,
            channels=channels,
            min_replies=min_replies,
            include_forwarded=include_forwarded,
            include_links=include_links,
            start_date=start_date,
            end_date=end_date,
            log_callback=log_callback,
        )

        if progress_callback:
            progress_callback(50)

        self.print_graph_stats(graph, log_callback=log_callback)

        if progress_callback:
            progress_callback(70)

        export_formats = [f for f in formats if f != "png"]
        if export_formats:
            self.export_graph(
                graph,
                output_dir,
                export_formats,
                log_callback=log_callback,
                db_path=db_path,
                channels=channels,
                min_replies=min_replies,
                include_forwarded=include_forwarded,
                include_discussion_replies=True,
                start_date=start_date,
                end_date=end_date,
            )

        if progress_callback:
            progress_callback(90)

        if "png" in formats:
            self.visualize_graph(graph, output_dir)

        if progress_callback:
            progress_callback(100)

        log_callback("Analysis completed!")
