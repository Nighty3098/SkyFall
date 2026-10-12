"""Unit tests for :mod:`src.modules.reddit_osint`.

The tests never touch the network: an ``httpx.MockTransport`` stands in for the
Arctic Shift and PullPush archives, so the concurrency, pagination, retry and
merge logic can be exercised deterministically.
"""

import asyncio
import unittest

import httpx

from src.modules.reddit_osint import (
    RedditArchiveError,
    RedditOsint,
    analyze,
    build_search_url,
    detect_technologies,
    extract_signals,
    guess_timezone,
    normalize_username,
    status_of,
)

ARCTIC = "https://arctic.test"
PULLPUSH = "https://pullpush.test"


async def _no_sleep(*_args, **_kwargs):
    return None


def make_osint(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    params = {
        "arctic": ARCTIC,
        "pullpush": PULLPUSH,
        "transport": transport,
        "sleeper": _no_sleep,
        "delay": 0.0,
        "max_attempts": 1,
    }
    params.update(kwargs)
    return RedditOsint(**params)


def post(rid, ts, text="hello world", sub="python", **extra):
    row = {
        "id": rid,
        "created_utc": ts,
        "subreddit": sub,
        "selftext": text,
        "title": text[:20],
        "author": "alice",
        "score": 1,
    }
    row.update(extra)
    return row


def comment(rid, ts, text="a comment", sub="python", **extra):
    row = {
        "id": rid,
        "created_utc": ts,
        "subreddit": sub,
        "body": text,
        "author": "alice",
        "score": 1,
    }
    row.update(extra)
    return row


class PureHelpersTest(unittest.TestCase):
    def test_normalize_username(self):
        self.assertEqual(normalize_username("u/Alice"), "Alice")
        self.assertEqual(normalize_username("/u/Bob/"), "Bob")
        self.assertEqual(normalize_username("@carol"), "carol")
        self.assertEqual(normalize_username("  dave  "), "dave")
        self.assertEqual(normalize_username(None), "")

    def test_status_of(self):
        self.assertEqual(status_of({"selftext": "hi"}, "posts"), "live")
        self.assertEqual(status_of({"selftext": "[removed]"}, "posts"), "removed")
        self.assertEqual(
            status_of({"selftext": "x", "removed_by_category": "moderator"}, "posts"),
            "removed",
        )
        self.assertEqual(status_of({"selftext": "[deleted]"}, "posts"), "deleted")
        self.assertEqual(status_of({"body": "[deleted]"}, "comments"), "deleted")
        self.assertEqual(status_of({"body": "ok"}, "comments"), "live")

    def test_extract_signals(self):
        text = (
            "mail me at a.b@example.com or t.me/myhandle, +1 (555) 123-4567 "
            "wallet 0x" + "a" * 40 + " see https://evil.example.com/x "
            "cc u/otheruser"
        )
        signals = dict((tag, val) for tag, val in extract_signals(text))
        tags = {tag for tag, _ in extract_signals(text)}
        self.assertIn("email", tags)
        self.assertIn("eth", tags)
        self.assertIn("telegram", tags)
        self.assertIn("phone", tags)
        self.assertIn("domain", tags)
        self.assertIn("mention", tags)
        self.assertEqual(signals["email"], "a.b@example.com")
        self.assertEqual(signals["telegram"], "@myhandle")
        self.assertEqual(signals["mention"], "u/otheruser")
        self.assertIn("evil.example.com", (signals["domain"]))
        # btc address must be recognised as a distinct tag
        btc = extract_signals("bc1" + "q" * 40)
        self.assertTrue(any(tag == "btc" for tag, _ in btc))

    def test_detect_technologies(self):
        found = detect_technologies("I write Python and use Docker on Kubernetes")
        self.assertIn("python", found)
        self.assertIn("docker", found)
        self.assertIn("kubernetes", found)
        self.assertNotIn("rust", found)

    def test_guess_timezone(self):
        hours = [3] * 24
        for i in range(8, 14):
            hours[i] = 0
        start, region = guess_timezone(hours)
        self.assertEqual(start, 8)
        self.assertTrue(region.startswith("Americas"))
        # flat distribution is reported as unknown
        self.assertEqual(guess_timezone([0] * 24)[1], "Unknown / distributed")
        self.assertEqual(guess_timezone([])[1], "Unknown / distributed")

    def test_build_search_url_arctic(self):
        url = build_search_url(
            "arctic", "posts", author="alice", keywords="secret", arctic=ARCTIC
        )
        self.assertIn("/api/posts/search", url)
        self.assertIn("author=alice", url)
        self.assertIn("query=secret", url)
        comments = build_search_url(
            "arctic", "comments", author="alice", keywords="secret", arctic=ARCTIC
        )
        self.assertIn("body=secret", comments)

    def test_build_search_url_pullpush(self):
        url = build_search_url(
            "pullpush", "comments", author="alice", keywords="secret", pullpush=PULLPUSH
        )
        self.assertIn("/reddit/search/comment/", url)
        self.assertIn("q=secret", url)
        submission = build_search_url(
            "pullpush", "posts", author="alice", pullpush=PULLPUSH
        )
        self.assertIn("/reddit/search/submission/", submission)

    def test_build_search_url_requires_target(self):
        with self.assertRaises(ValueError):
            build_search_url("arctic", "posts", arctic=ARCTIC)


class AnalyzeTest(unittest.TestCase):
    def _report(self):
        posts = [
            post("p1", 1000, "email me bob@example.com", sub="python"),
            post("p2", 2000, "[removed]", sub="python"),
        ]
        comments = [
            comment("c1", 1100, "i use docker", sub="devops"),
            comment("c2", 1200, "[deleted]", sub="devops"),
        ]
        return analyze("alice", {"posts": posts, "comments": comments})

    def test_totals_and_status(self):
        report = self._report()
        totals = report["totals"]
        self.assertEqual(totals["posts"], 2)
        self.assertEqual(totals["comments"], 2)
        self.assertEqual(totals["items"], 4)
        self.assertEqual(totals["live"], 2)
        self.assertEqual(totals["removed_by_mods"], 1)
        self.assertEqual(totals["deleted_by_author"], 1)
        self.assertEqual(totals["deleted_pct"], 50.0)
        self.assertEqual(len(report["deleted_removed_items"]), 2)

    def test_identifiers_and_score(self):
        report = self._report()
        self.assertGreater(report["score_exposure_0_100"], 0)
        self.assertTrue(any("email" in ident for ident in report["identifiers"]))

    def test_activity_histograms(self):
        report = self._report()
        self.assertEqual(len(report["activity_by_hour_utc"]), 24)
        self.assertEqual(sum(report["activity_by_weekday"].values()), 4)
        self.assertEqual(sum(report["activity_by_month"].values()), 4)

    def test_top_subreddits_and_tech(self):
        report = self._report()
        subs = {
            entry["subreddit"]: entry["items"] for entry in report["top_subreddits"]
        }
        self.assertEqual(subs, {"python": 2, "devops": 2})
        techs = {entry["tech"] for entry in report["technologies"]}
        self.assertIn("docker", techs)


class CollectTest(unittest.TestCase):
    def test_collect_merges_and_dedupes(self):
        def handler(request):
            path = request.url.path
            if path == "/api/posts/search":
                data = [post("a1", 100), post("dup", 50)]
            elif path == "/api/comments/search":
                data = [comment("ac1", 150)]
            elif path == "/reddit/search/submission/":
                data = [post("dup", 50), post("b1", 200)]
            elif path == "/reddit/search/comment/":
                data = [comment("bc1", 250)]
            else:
                return httpx.Response(404)
            return httpx.Response(200, json={"data": data})

        osint = make_osint(handler)
        items, errors = asyncio.run(osint.collect("alice"))
        self.assertEqual(errors, [])
        self.assertEqual([row["id"] for row in items["posts"]], ["dup", "a1", "b1"])
        self.assertEqual([row["id"] for row in items["comments"]], ["ac1", "bc1"])

    def test_collect_records_source_errors(self):
        def handler(request):
            if request.url.path == "/api/posts/search":
                return httpx.Response(500, text="boom")
            return httpx.Response(200, json={"data": []})

        osint = make_osint(handler)
        items, errors = asyncio.run(osint.collect("alice"))
        self.assertTrue(any("posts" in message for message in errors))
        self.assertEqual(items["posts"], [])


class PaginationTest(unittest.TestCase):
    def test_fetch_all_paginates_with_cursor(self):
        calls = []

        def handler(request):
            params = dict(request.url.params)
            after = int(params.get("after", 0))
            calls.append(after)
            if after == 0:
                data = [post("a", 100), post("b", 90)]
            elif after == 91:
                data = [post("c", 80)]
            else:
                data = []
            return httpx.Response(200, json={"data": data})

        osint = make_osint(handler)
        rows = asyncio.run(osint.fetch_all("arctic", "posts", "alice", limit=2))
        self.assertEqual([row["id"] for row in rows], ["a", "b", "c"])
        self.assertEqual(calls, [0, 91])

    def test_fetch_all_stops_on_empty_page(self):
        def handler(request):
            return httpx.Response(200, json={"data": []})

        osint = make_osint(handler)
        rows = asyncio.run(osint.fetch_all("arctic", "posts", "alice"))
        self.assertEqual(rows, [])


class RetryTest(unittest.TestCase):
    def test_retries_on_throttle_then_succeeds(self):
        state = {"n": 0}

        def handler(request):
            state["n"] += 1
            if state["n"] == 1:
                return httpx.Response(429, text="slow down")
            return httpx.Response(200, json={"data": [post("a", 1)]})

        osint = make_osint(handler, max_attempts=3)
        rows = asyncio.run(osint.fetch_all("arctic", "posts", "alice"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(state["n"], 2)

    def test_raises_after_retries_exhausted(self):
        def handler(request):
            return httpx.Response(503, text="unavailable")

        osint = make_osint(handler, max_attempts=2)
        with self.assertRaises(RedditArchiveError):
            asyncio.run(osint.fetch_all("arctic", "posts", "alice"))


class FullReportTest(unittest.TestCase):
    def test_full_report_without_credentials(self):
        def handler(request):
            path = request.url.path
            if path == "/api/posts/search":
                data = [post("p1", 1000, "hi bob@example.com")]
            elif path == "/api/comments/search":
                data = [comment("c1", 1100)]
            elif path == "/api/users/search":
                return httpx.Response(
                    200, json={"data": [{"_meta": {"total_karma": 42}}]}
                )
            else:
                data = []
            return httpx.Response(200, json={"data": data})

        osint = make_osint(handler)
        report, errors = asyncio.run(osint.full_report("alice"))
        self.assertEqual(errors, [])
        self.assertEqual(report["username"], "alice")
        self.assertEqual(report["totals"]["items"], 2)
        self.assertEqual(report["archive_meta"], {"total_karma": 42})
        self.assertIsNone(report["live_profile"])

    def test_live_profile_with_oauth(self):
        def handler(request):
            if request.url.path == "/api/v1/access_token":
                return httpx.Response(200, json={"access_token": "tok"})
            if request.url.path == "/user/alice/about":
                return httpx.Response(
                    200, json={"data": {"name": "alice", "link_karma": 7}}
                )
            return httpx.Response(200, json={"data": []})

        osint = make_osint(handler, client_id="id", client_secret="secret")
        live = asyncio.run(osint.fetch_live_profile("alice"))
        self.assertEqual(live, {"name": "alice", "link_karma": 7})

    def test_live_profile_without_credentials(self):
        def handler(request):  # pragma: no cover - must not be called
            raise AssertionError("no request expected")

        osint = make_osint(handler)
        self.assertIsNone(asyncio.run(osint.fetch_live_profile("alice")))


class RenderTest(unittest.TestCase):
    def test_render_report_sections(self):
        report = analyze(
            "alice",
            {"posts": [post("p1", 1000, "bob@example.com")], "comments": []},
        )
        osint = make_osint(lambda request: httpx.Response(200, json={"data": []}))
        full = osint.render_report(report)
        self.assertIn("Reddit OSINT: u/alice", full)
        self.assertIn("Exposure", full)
        self.assertIn("Identifiers", full)
        partial = osint.render_report(report, sections=["posts"])
        self.assertIn("Reddit OSINT: u/alice", partial)
        self.assertNotIn("Exposure", partial)
        self.assertIn("Posts", partial)

    def test_render_search(self):
        rows = [
            {
                "status": "live",
                "title": "hello",
                "subreddit": "python",
                "utc": "2024-01-01T00:00:00+00:00",
                "score": 3,
                "url": "https://reddit.com/x",
            }
        ]
        text = RedditOsint.render_search(rows, keywords="hello", author="alice")
        self.assertIn("Archive search", text)
        self.assertIn("hello", text)
        empty = RedditOsint.render_search([], keywords="x")
        self.assertIn("No matching items", empty)


if __name__ == "__main__":
    unittest.main()
