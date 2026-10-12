"""Unit tests for the Reddit and merged-username MCP tools.

The archive engines are replaced with in-memory fakes so the suite stays
network free.
"""

import asyncio
import json
import unittest
from unittest.mock import patch

import src.skyfall_mcp_server as mcp_mod

EXPECTED_TOOL_COUNT = 89

NEW_TOOLS = [
    "skyfall_username_merged",
    "skyfall_reddit_report",
    "skyfall_reddit_posts",
    "skyfall_reddit_comments",
    "skyfall_reddit_removed",
    "skyfall_reddit_identifiers",
    "skyfall_reddit_activity",
    "skyfall_reddit_affiliations",
    "skyfall_reddit_archive_search",
]


class FakeReddit:
    def __init__(self, **kwargs):
        pass

    async def full_report(self, username, **kwargs):
        report = {
            "username": username,
            "items": [
                {"id": "1", "kind": "posts", "title": "hello"},
                {"id": "2", "kind": "comments", "text": "hi"},
            ],
            "totals": {"posts": 1, "comments": 1},
            "identifiers": ["email:a@b.com"],
            "top_subreddits": [{"subreddit": "python", "items": 1}],
        }
        return report, ["archive slow"]

    async def search_archive(self, **kwargs):
        return [{"id": "1", "title": "hit", "status": "live"}]


class McpToolRegistryTest(unittest.TestCase):
    def test_tool_count(self):
        tools = asyncio.run(mcp_mod.mcp.list_tools())
        self.assertEqual(len(tools), EXPECTED_TOOL_COUNT)

    def test_new_tools_registered(self):
        names = {t.name for t in asyncio.run(mcp_mod.mcp.list_tools())}
        for name in NEW_TOOLS:
            self.assertIn(name, names)


class RedditToolTest(unittest.TestCase):
    def setUp(self):
        mcp_mod._REDDIT_CACHE.clear()

    def tearDown(self):
        mcp_mod._REDDIT_CACHE.clear()

    def test_report_drops_raw_items(self):
        with patch("src.modules.reddit_osint.RedditOsint", FakeReddit):
            out = asyncio.run(mcp_mod.skyfall_reddit_report("alice"))
        data = json.loads(out)
        self.assertEqual(data["username"], "alice")
        self.assertNotIn("items", data)
        self.assertEqual(data["errors"], ["archive slow"])

    def test_posts_filter(self):
        with patch("src.modules.reddit_osint.RedditOsint", FakeReddit):
            out = asyncio.run(mcp_mod.skyfall_reddit_posts("alice"))
        data = json.loads(out)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["posts"][0]["id"], "1")

    def test_identifiers(self):
        with patch("src.modules.reddit_osint.RedditOsint", FakeReddit):
            out = asyncio.run(mcp_mod.skyfall_reddit_identifiers("alice"))
        data = json.loads(out)
        self.assertEqual(data["identifiers"], ["email:a@b.com"])

    def test_archive_search(self):
        with patch("src.modules.reddit_osint.RedditOsint", FakeReddit):
            out = asyncio.run(mcp_mod.skyfall_reddit_archive_search("python"))
        data = json.loads(out)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["title"], "hit")

    def test_cache_reuses_report(self):
        calls = {"n": 0}

        class CountingReddit(FakeReddit):
            async def full_report(self, username, **kwargs):
                calls["n"] += 1
                return await super().full_report(username, **kwargs)

        with patch("src.modules.reddit_osint.RedditOsint", CountingReddit):
            asyncio.run(mcp_mod.skyfall_reddit_report("alice"))
            asyncio.run(mcp_mod.skyfall_reddit_activity("alice"))
        self.assertEqual(calls["n"], 1)


class MergedUsernameToolTest(unittest.TestCase):
    def test_merges_both_engines(self):
        from src.modules.username_search import UsernameSearch as RealSherlock

        class Sherlock:
            Status = RealSherlock.Status

            async def acheck(self, username):
                return [
                    {
                        "site": "GitHub",
                        "url_user": "https://github.com/alice",
                        "status": self.Status.CLAIMED,
                    }
                ]

        class Maigret:
            async def search_and_report_structured(self, username):
                return "", [
                    {
                        "site": "GitHub",
                        "url_user": "https://github.com/alice",
                        "status": "Claimed",
                    }
                ]

        with (
            patch("src.modules.username_search.UsernameSearch", Sherlock),
            patch("src.modules.maigret_search.MaigretSearch", Maigret),
        ):
            out = asyncio.run(mcp_mod.skyfall_username_merged("alice"))
        data = json.loads(out)
        self.assertEqual(data["confirmed_count"], 1)
        self.assertEqual(data["confirmed"][0]["site"], "GitHub")


if __name__ == "__main__":
    unittest.main()
