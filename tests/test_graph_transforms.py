"""Unit tests for the Reddit/merged-username graph transforms."""

import asyncio
import unittest

from src.controllers.graph_transform_controller import (
    GraphTransformController,
    _parse_reddit_report,
    _transform_reddit_osint,
    _transform_username_merged,
)

REPORT = {
    "username": "alice",
    "totals": {
        "posts": 2,
        "comments": 3,
        "items": 5,
        "live": 4,
        "removed_by_mods": 1,
        "deleted_by_author": 0,
        "last_activity": "2024-01-01T00:00:00+00:00",
    },
    "score_exposure_0_100": 40,
    "timezone_guess": {"estimated_region": "Europe (UTC+0..UTC+3)"},
    "top_subreddits": [{"subreddit": "python", "items": 3}],
    "identifiers": ["email:a@b.com", "telegram:@handle", "btc:bc1qexample"],
    "external_domains": [{"domain": "example.com", "times": 2}],
    "mentioned_users": [{"user": "u/bob", "times": 1}],
    "technologies": [{"tech": "python", "times": 2}],
    "items": [],
}


class FakeNode:
    entity_type = "Username"


class FakeReddit:
    def __init__(self, report=None, error=None):
        self._report = report if report is not None else REPORT
        self._error = error

    async def full_report(self, username, **kwargs):
        if self._error:
            raise self._error
        return self._report, []


class FakeSherlock:
    async def acheck(self, username, **kwargs):
        return [
            {
                "site": "GitHub",
                "url_user": "https://github.com/alice",
                "status": "Claimed",
            },
            {
                "site": "Reddit",
                "url_user": "https://reddit.com/user/alice",
                "status": "Claimed",
            },
        ]


class FakeMaigret:
    async def search_and_report_structured(self, username):
        return "raw", [
            {
                "site": "github",
                "url_user": "https://github.com/alice",
                "status": "Claimed",
            }
        ]


class RegistryTest(unittest.TestCase):
    def test_username_has_new_transforms(self):
        controller = GraphTransformController(None, {})
        names = [t.name for t in controller.get_transforms(FakeNode())]
        self.assertIn("Reddit OSINT", names)
        self.assertIn("Sherlock + Maigret (merged)", names)


class ParseRedditTest(unittest.TestCase):
    def test_children_cover_every_category(self):
        result = _parse_reddit_report(REPORT)
        by_type = {}
        for child in result.children:
            by_type.setdefault(child.entity_type, []).append(child.title)
        self.assertIn("r/python", by_type.get("Custom", []))
        self.assertIn("a@b.com", by_type.get("Email", []))
        self.assertIn("bc1qexample", by_type.get("Crypto", []))
        self.assertIn("example.com", by_type.get("Domain", []))
        self.assertIn("u/bob", by_type.get("Username", []))
        self.assertIn("Technologies", by_type.get("Custom", []))

    def test_content_summarises_report(self):
        result = _parse_reddit_report(REPORT, errors=["archive throttled"])
        self.assertIn("Reddit OSINT: u/alice", result.content)
        self.assertIn("Timezone", result.content)
        self.assertIn("archive throttled", result.content)

    def test_empty_report(self):
        result = _parse_reddit_report({"username": "ghost"})
        self.assertEqual(result.children, [])
        self.assertIn("Reddit OSINT: u/ghost", result.content)


class TransformRedditTest(unittest.TestCase):
    def test_missing_module(self):
        result = asyncio.run(_transform_reddit_osint("alice", {}))
        self.assertIn("not available", result.content)

    def test_happy_path(self):
        result = asyncio.run(
            _transform_reddit_osint("alice", {"reddit_osint": FakeReddit()})
        )
        self.assertTrue(result.children)
        self.assertIn("Reddit OSINT", result.content)

    def test_failure_is_surfaced(self):
        module = FakeReddit(error=RuntimeError("boom"))
        result = asyncio.run(_transform_reddit_osint("alice", {"reddit_osint": module}))
        self.assertIn("Reddit OSINT failed: boom", result.content)


class TransformMergedTest(unittest.TestCase):
    def test_missing_engines(self):
        result = asyncio.run(_transform_username_merged("alice", {}))
        self.assertIn("not available", result.content)

    def test_confirmed_child_first(self):
        modules = {"username_search": FakeSherlock(), "maigret_search": FakeMaigret()}
        result = asyncio.run(_transform_username_merged("alice", modules))
        self.assertTrue(result.children)
        self.assertTrue(result.children[0].title.startswith("✅ GitHub"))
        self.assertIn("Confirmed by both engines", result.content)
        self.assertIn("Unconfirmed", result.content)


if __name__ == "__main__":
    unittest.main()
