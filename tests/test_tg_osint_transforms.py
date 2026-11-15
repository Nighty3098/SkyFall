"""Tests for Telegram OSINT graph transforms."""

import asyncio
import unittest

from src.transforms.builtin import build_builtin_registry
from src.transforms.builtin_handlers import (
    _extract_tg_target,
    _transform_tg_bot_token,
    _transform_tg_id_to_username,
    _transform_tg_osint,
    _transform_tg_username_to_id,
)

BOT_TOKEN = "123456789:" + "A" * 35


class FakeTgOsint:
    def __init__(
        self,
        *,
        raw_id=123456789,
        marked_id=-1001234567890,
        username="alice",
        bot_username="alice_bot",
    ):
        self.raw_id = raw_id
        self.marked_id = marked_id
        self.username = username
        self.bot_username = bot_username
        self.calls = []
        self.proxy = None

    async def get_id_by_username(self, username, *, marked=False):
        self.calls.append(("id", username, marked))
        return self.marked_id if marked else self.raw_id

    async def get_username_by_id(self, peer_id):
        self.calls.append(("username", peer_id))
        return self.username

    async def get_username_by_bot_token(self, token):
        self.calls.append(("bot", token))
        return self.bot_username

    def set_proxy(self, proxy_url, use_proxy=True):
        self.proxy = (proxy_url, use_proxy)


class FakeProxy:
    def __init__(self, url="socks5://127.0.0.1:1080"):
        self.url = url

    def get_proxy_url(self):
        return self.url

    def get_first_proxy(self):
        return self.url


class RegistryTest(unittest.TestCase):
    def test_telegram_transforms_are_registered(self):
        registry = build_builtin_registry()

        def names(entity_type):
            return {transform.name for transform in registry[entity_type]}

        self.assertIn("Telegram User ID", names("Username"))
        self.assertIn("Telegram Lookup", names("Person"))
        self.assertIn("Telegram Lookup", names("Organization"))
        self.assertIn("Telegram Lookup", names("SocialMedia"))
        self.assertIn("Telegram Lookup", names("Custom"))
        self.assertIn("Telegram ID → Username", names("Custom"))
        self.assertIn("Check Telegram Bot Token", names("Custom"))


class DetectionTest(unittest.TestCase):
    def test_detects_all_supported_formats(self):
        self.assertEqual(_extract_tg_target("alice"), ("alice", "username"))
        self.assertEqual(
            _extract_tg_target("https://t.me/alice/42"), ("alice", "username")
        )
        self.assertEqual(_extract_tg_target("@alice"), ("alice", "username"))
        self.assertEqual(_extract_tg_target("123456789"), ("123456789", "id"))
        self.assertEqual(_extract_tg_target(BOT_TOKEN), (BOT_TOKEN, "bot_token"))

    def test_reads_telegram_node_content(self):
        content = "tg_id: user:123456789\nfirst_name: Alice\nusername: alice"
        self.assertEqual(_extract_tg_target(content), ("123456789", "id"))
        self.assertEqual(
            _extract_tg_target("first_name: Alice\nusername: alice"),
            ("alice", "username"),
        )
        self.assertEqual(
            _extract_tg_target("Profile: https://t.me/alice"),
            ("alice", "username"),
        )

    def test_rejects_unrelated_text(self):
        self.assertEqual(_extract_tg_target("Alice Example"), (None, None))
        self.assertEqual(_extract_tg_target("New Custom"), (None, None))


class UsernameTransformTest(unittest.TestCase):
    def test_resolves_raw_and_marked_ids(self):
        engine = FakeTgOsint()
        result = asyncio.run(
            _transform_tg_username_to_id("alice", {"tg_osint": engine})
        )

        self.assertEqual(
            [child.title for child in result.children],
            ["123456789", "-1001234567890"],
        )
        self.assertTrue(all(c.entity_type == "Custom" for c in result.children))
        self.assertIn("Telegram: @alice", result.content)
        self.assertEqual(result.evidence, ["https://t.me/alice"])
        self.assertEqual(
            engine.calls,
            [("id", "alice", False), ("id", "alice", True)],
        )

    def test_skips_duplicate_ids(self):
        engine = FakeTgOsint(raw_id=123456789, marked_id=123456789)
        result = asyncio.run(
            _transform_tg_username_to_id("@alice", {"tg_osint": engine})
        )
        self.assertEqual([child.title for child in result.children], ["123456789"])

    def test_missing_account(self):
        engine = FakeTgOsint(raw_id=None, marked_id=None)
        result = asyncio.run(
            _transform_tg_username_to_id("alice", {"tg_osint": engine})
        )
        self.assertFalse(result.children)
        self.assertIn("No Telegram account found", result.content)

    def test_rejects_non_username_input(self):
        engine = FakeTgOsint()
        result = asyncio.run(
            _transform_tg_username_to_id("123456789", {"tg_osint": engine})
        )
        self.assertIn("Not a Telegram username", result.content)
        self.assertEqual(engine.calls, [])


class IdTransformTest(unittest.TestCase):
    def test_resolves_id_to_username(self):
        engine = FakeTgOsint()
        result = asyncio.run(
            _transform_tg_id_to_username("-1001234567890", {"tg_osint": engine})
        )

        self.assertEqual(result.children[0].title, "@alice")
        self.assertEqual(result.children[0].entity_type, "Username")
        self.assertIn("Telegram ID: -1001234567890", result.content)
        self.assertEqual(engine.calls, [("username", "-1001234567890")])

    def test_no_public_username(self):
        engine = FakeTgOsint(username=None)
        result = asyncio.run(
            _transform_tg_id_to_username("123456789", {"tg_osint": engine})
        )
        self.assertFalse(result.children)
        self.assertIn("No public username found", result.content)


class BotTokenTransformTest(unittest.TestCase):
    def test_valid_bot_token(self):
        engine = FakeTgOsint()
        result = asyncio.run(_transform_tg_bot_token(BOT_TOKEN, {"tg_osint": engine}))

        self.assertEqual(result.children[0].title, "@alice_bot")
        self.assertEqual(result.children[0].entity_type, "Username")
        self.assertIn("Valid", result.content)
        self.assertNotIn(BOT_TOKEN, result.content)
        self.assertEqual(engine.calls, [("bot", BOT_TOKEN)])

    def test_invalid_bot_token_is_not_echoed(self):
        engine = FakeTgOsint(bot_username=None)
        result = asyncio.run(_transform_tg_bot_token(BOT_TOKEN, {"tg_osint": engine}))
        self.assertFalse(result.children)
        self.assertIn("invalid or expired", result.content)
        self.assertNotIn(BOT_TOKEN, result.content)

    def test_non_token_input_is_not_echoed(self):
        result = asyncio.run(
            _transform_tg_bot_token("secret-not-a-token", {"tg_osint": FakeTgOsint()})
        )
        self.assertIn("not a recognized Telegram bot token", result.content)
        self.assertNotIn("secret-not-a-token", result.content)


class AutoTransformTest(unittest.TestCase):
    def test_dispatches_by_input_kind(self):
        engine = FakeTgOsint()

        username_result = asyncio.run(
            _transform_tg_osint("alice", {"tg_osint": engine})
        )
        id_result = asyncio.run(_transform_tg_osint("123456789", {"tg_osint": engine}))
        bot_result = asyncio.run(_transform_tg_osint(BOT_TOKEN, {"tg_osint": engine}))

        self.assertIn("Telegram: @alice", username_result.content)
        self.assertEqual(id_result.children[0].title, "@alice")
        self.assertEqual(bot_result.children[0].title, "@alice_bot")

    def test_reads_content_from_telegram_graph_nodes(self):
        engine = FakeTgOsint()
        content = "tg_id: user:123456789\nusername: alice"
        result = asyncio.run(_transform_tg_osint(content, {"tg_osint": engine}))
        self.assertEqual(result.children[0].title, "@alice")

    def test_missing_module(self):
        result = asyncio.run(_transform_tg_osint("alice", {}))
        self.assertIn("not available", result.content)

    def test_unrecognized_input(self):
        engine = FakeTgOsint()
        result = asyncio.run(_transform_tg_osint("Alice Example", {"tg_osint": engine}))
        self.assertIn("Not a Telegram username", result.content)

    def test_refreshes_proxy_before_lookup(self):
        engine = FakeTgOsint()
        asyncio.run(
            _transform_tg_osint("alice", {"tg_osint": engine, "proxy": FakeProxy()})
        )
        self.assertEqual(engine.proxy, ("socks5://127.0.0.1:1080", True))

    def test_keeps_unchanged_proxy_configuration(self):
        engine = FakeTgOsint()
        engine.config = {"proxy_list": "socks5://127.0.0.1:1080", "use_proxy": True}
        asyncio.run(
            _transform_tg_osint("alice", {"tg_osint": engine, "proxy": FakeProxy()})
        )
        self.assertIsNone(engine.proxy)

    def test_failures_are_surfaced(self):
        class BrokenTgOsint(FakeTgOsint):
            async def get_username_by_id(self, peer_id):
                raise RuntimeError("boom")

        result = asyncio.run(
            _transform_tg_osint("123456789", {"tg_osint": BrokenTgOsint()})
        )
        self.assertIn("Telegram lookup failed: boom", result.content)


if __name__ == "__main__":
    unittest.main()
