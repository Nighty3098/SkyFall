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
        controller = GraphTransformController(None, {}, plugin_dir=None)
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


class NewTransformRegistryTest(unittest.TestCase):
    def test_every_entity_type_has_a_transform(self):
        controller = GraphTransformController(None, {}, plugin_dir=None)
        for etype in (
            "Person",
            "Domain",
            "IP",
            "Email",
            "Phone",
            "MAC",
            "Username",
            "Crypto",
            "Organization",
            "Passport",
            "Photo",
            "Geolocation",
            "Custom",
        ):
            node = type("Node", (), {"entity_type": etype})()
            self.assertTrue(controller.get_transforms(node), etype)

    def test_result_accepts_evidence(self):
        from src.controllers.graph_transform_controller import TransformResult

        result = TransformResult(evidence=["https://example.com"])
        self.assertEqual(result.evidence, ["https://example.com"])

    def test_username_search_parser_accepts_evidence(self):
        from src.controllers.graph_transform_controller import _parse_username_search

        result = _parse_username_search(
            [
                {
                    "site": "Example",
                    "status": "Claimed",
                    "url_user": "https://example.com/alice",
                    "url_main": "https://example.com",
                }
            ],
            "alice",
        )
        self.assertEqual(result.children[0].title, "Example")
        self.assertEqual(result.evidence, ["https://example.com"])


class PhoneKeyWiringTest(unittest.TestCase):
    def test_reverse_lookup_passes_configured_keys(self):
        from types import SimpleNamespace

        from src.controllers.graph_transform_controller import _transform_phone_lookup

        class FakePhone:
            def __init__(self):
                self.kwargs = None

            async def reverse_lookup(self, phone, **kwargs):
                self.kwargs = kwargs
                return {"phone": phone}

        engine = FakePhone()
        settings = SimpleNamespace(
            numverify_api_key="num-key", abstractapi_api_key="abs-key"
        )
        result = asyncio.run(
            _transform_phone_lookup(
                "+12025550123",
                {"phone_search": engine, "settings": settings},
            )
        )
        self.assertEqual(engine.kwargs["numverify_key"], "num-key")
        self.assertEqual(engine.kwargs["abstractapi_key"], "abs-key")
        self.assertIn("Phone", result.content)

    def test_phone_leaks_passes_intelx_key(self):
        from types import SimpleNamespace

        from src.controllers.graph_transform_controller import _transform_phone_leaks

        class FakePhone:
            def __init__(self):
                self.kwargs = None

            async def check_leaks(self, phone, **kwargs):
                self.kwargs = kwargs
                return {"phone": phone, "findings": []}

        engine = FakePhone()
        settings = SimpleNamespace(intelligent_x_api_key="intelx-key")
        asyncio.run(
            _transform_phone_leaks(
                "+12025550123", {"phone_search": engine, "settings": settings}
            )
        )
        self.assertEqual(engine.kwargs["intelx_key"], "intelx-key")


class IdentityParserTest(unittest.TestCase):
    def test_github_user_parser(self):
        from src.controllers.graph_transform_controller import _parse_github_user

        result = _parse_github_user(
            {
                "username": "alice",
                "profile": {"login": "alice", "name": "Alice", "public_repos": 2},
                "repos": [{"full_name": "alice/project", "language": "Python"}],
            },
            "alice",
        )
        self.assertEqual(result.children[0].title, "GitHub: alice")
        self.assertEqual(result.children[1].title, "alice/project")

    def test_github_repos_parser(self):
        from src.controllers.graph_transform_controller import _parse_github_repos

        result = _parse_github_repos(
            {
                "repositories": [
                    {
                        "full_name": "acme/tool",
                        "description": "A tool",
                        "stars": 7,
                        "forks": 2,
                        "language": "Go",
                        "url": "https://github.com/acme/tool",
                    }
                ]
            },
            "acme",
        )
        self.assertEqual(result.children[0].title, "acme/tool")
        self.assertIn("Stars", result.children[0].content)

    def test_github_email_parser(self):
        from src.controllers.graph_transform_controller import _parse_github_emails

        result = _parse_github_emails(
            {
                "results": [
                    {
                        "repo": "acme/tool",
                        "path": "README.md",
                        "url": "https://github.com/acme/tool/blob/main/README.md",
                    }
                ]
            },
            "a@example.com",
        )
        self.assertEqual(result.children[0].title, "acme/tool")
        self.assertIn("a@example.com", result.children[0].content)

    def test_instagram_parser(self):
        from src.controllers.graph_transform_controller import (
            _parse_instagram_profile,
        )

        result = _parse_instagram_profile(
            {
                "username": "alice",
                "full_name": "Alice",
                "followers": 10,
                "posts": 3,
                "external_url": "https://example.com",
            },
            "alice",
        )
        self.assertEqual(result.children[0].title, "@alice")
        self.assertIn("Followers", result.children[0].content)

    def test_hibp_parser(self):
        from src.controllers.graph_transform_controller import _parse_email_hibp

        result = _parse_email_hibp(
            {
                "breaches": [
                    {
                        "name": "Example",
                        "domain": "example.com",
                        "date": "2020-01-01",
                        "records": 10,
                        "data": ["Email addresses"],
                    }
                ]
            },
            "a@example.com",
        )
        self.assertEqual(result.children[0].title, "Example")
        self.assertEqual(result.children[0].entity_type, "Organization")


class NetworkParserTest(unittest.TestCase):
    def test_http_headers_parser(self):
        from src.controllers.graph_transform_controller import _parse_domain_headers

        result = _parse_domain_headers(
            {
                "status_code": 200,
                "final_url": "https://example.com/",
                "headers": {"Server": "nginx", "X-Frame-Options": "DENY"},
            },
            "example.com",
        )
        self.assertEqual(result.children[0].title, "HTTP 200")
        self.assertIn("nginx", result.content)

    def test_waf_parser(self):
        from src.controllers.graph_transform_controller import _parse_domain_waf

        result = _parse_domain_waf(
            {
                "waf_detected": True,
                "waf_providers": ["cloudflare"],
                "server": "cloudflare",
            },
            "example.com",
        )
        self.assertEqual(result.children[0].title, "WAF: cloudflare")

    def test_hosts_parser(self):
        from src.controllers.graph_transform_controller import _parse_domain_hosts

        result = _parse_domain_hosts(
            ["www.example.com", "mail.example.com"], "example.com"
        )
        self.assertEqual(len(result.children), 2)
        self.assertEqual(result.children[0].entity_type, "Domain")

    def test_archive_check_parser(self):
        from src.controllers.graph_transform_controller import _parse_archive_check

        result = _parse_archive_check(
            {
                "wayback": {
                    "snapshot": {
                        "url": "https://web.archive.org/1",
                        "timestamp": "20240101000000",
                    }
                },
                "archive_today": {
                    "found": True,
                    "snapshot": "https://archive.ph/abc",
                    "status": 200,
                },
            },
            "example.com",
        )
        self.assertEqual(len(result.children), 2)
        self.assertIn("archive.today", result.content)

    def test_archive_save_parser(self):
        from src.controllers.graph_transform_controller import _parse_archive_save

        result = _parse_archive_save(
            {"url": "https://example.com", "archive_url": "https://web.archive.org/x"},
            "example.com",
        )
        self.assertEqual(result.children[0].title, "Wayback snapshot saved")

    def test_web_search_parser(self):
        from src.controllers.graph_transform_controller import _parse_web_search

        text = "\n1 - Example result\nURL: https://example.com\nSNIPPET: Hello world\n"
        result = _parse_web_search(text, "example")
        self.assertEqual(result.children[0].title, "Example result")
        self.assertEqual(result.children[0].evidence, ["https://example.com"])


class GeoParserTest(unittest.TestCase):
    def test_firms_parser(self):
        from src.controllers.graph_transform_controller import _parse_geo_firms

        result = _parse_geo_firms(
            {
                "count": 1,
                "source": "VIIRS",
                "fires": [
                    {
                        "latitude": 1.0,
                        "longitude": 2.0,
                        "brightness": 300,
                        "frp": 1.2,
                        "confidence": "n",
                        "date": "2024-01-01",
                        "time": "1200",
                    }
                ],
            },
            "1, 2",
        )
        self.assertEqual(result.children[0].entity_type, "Geolocation")
        self.assertIn("NASA FIRMS", result.content)

    def test_geo_report_parser(self):
        from src.controllers.graph_transform_controller import _parse_geo_report

        result = _parse_geo_report(
            {"Sun / shadow": {"Shadow ratio": 1.2}, "Fires": {"count": 0}},
            "1, 2",
        )
        self.assertEqual(len(result.children), 2)
        self.assertIn("Location report", result.content)

    def test_shadow_search_parser(self):
        from src.controllers.graph_transform_controller import _parse_geo_shadow_search

        result = _parse_geo_shadow_search(
            [
                {
                    "latitude": 1.0,
                    "longitude": 2.0,
                    "sun_altitude_deg": 30,
                    "shadow_bearing_deg": 90,
                    "error_deg": 1,
                }
            ],
            {"ratio": 1.2, "bearing": 90},
        )
        self.assertEqual(result.children[0].title, "1.0, 2.0")


class PhotoParserTest(unittest.TestCase):
    def test_metadata_parser(self):
        from src.controllers.graph_transform_controller import _parse_photo_metadata

        result = _parse_photo_metadata(
            {"File": "photo.jpg", "MIME type": "image/jpeg"}, "/tmp/photo.jpg"
        )
        self.assertEqual(result.children[0].title, "File metadata")
        self.assertIn("photo.jpg", result.content)

    def test_gps_parser(self):
        from src.controllers.graph_transform_controller import _parse_photo_gps

        result = _parse_photo_gps((1.5, 2.5), "/tmp/photo.jpg")
        self.assertEqual(result.children[0].entity_type, "Geolocation")
        self.assertIn("1.5", result.children[0].title)

    def test_stego_parser(self):
        from src.controllers.graph_transform_controller import _parse_photo_stego

        result = _parse_photo_stego({"lsb": "ok", "spectral": "ok"}, "/tmp/photo.jpg")
        self.assertEqual(len(result.children), 2)
        self.assertIn("Steganography", result.content)

    def test_faces_parser(self):
        from src.controllers.graph_transform_controller import _parse_photo_faces

        result = _parse_photo_faces(
            [
                {
                    "first_name": "Alice",
                    "last_name": "Example",
                    "vk_url": "https://vk.com/alice",
                    "similarity": 0.9,
                }
            ],
            "/tmp/photo.jpg",
        )
        self.assertEqual(result.children[0].entity_type, "Person")
        self.assertIn("Alice Example", result.children[0].title)

    def test_virustotal_parser(self):
        from src.controllers.graph_transform_controller import (
            _parse_photo_virustotal,
        )

        result = _parse_photo_virustotal(
            {
                "hash": "abc...",
                "malicious": 0,
                "suspicious": 0,
                "harmless": 10,
                "undetected": 2,
                "detected": ["Not found"],
            },
            "/tmp/photo.jpg",
        )
        self.assertEqual(result.children[0].title, "Not found")
        self.assertIn("VirusTotal", result.content)
