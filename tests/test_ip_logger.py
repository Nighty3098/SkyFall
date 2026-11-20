import asyncio
import json
import re
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aiohttp import ClientSession

from src.controllers.ip_logger_controller import IpLoggerController
from src.modules.ip_logger import IpLogger, inject_tracker, parse_proxy_header
from src.modules.ip_logger_forwarder import _proxy_header
from src.modules.ip_logger_privilege import (
    linux_command,
    macos_script,
    needs_elevation,
    windows_forwarder,
)


class FakeGeo:
    api_key = ""

    async def lookup(self, ip):
        return {
            "status": "CLEAN",
            "city": "Testville",
            "country": "Testland",
            "lat": 10.5,
            "lon": 20.5,
        }


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class TemplateDiscoveryTest(unittest.TestCase):
    def test_discovers_html_from_both_folders_and_selects_a_site(self):
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            builtin = Path(first)
            user = Path(second)
            (builtin / "site.html").write_text("<html></html>", encoding="utf-8")
            (builtin / "ignored.txt").write_text("nope", encoding="utf-8")
            (builtin / "other.HTM").write_text("<html></html>", encoding="utf-8")
            (user / "site.html").write_text("<html>user</html>", encoding="utf-8")

            logger = IpLogger(geo=FakeGeo(), template_dirs=[builtin, user])
            labels = [item.label for item in logger.templates]
            self.assertEqual(len(labels), 3)
            self.assertEqual(
                sorted(label for label in labels if "site.html" in label),
                sorted(
                    [
                        f"site.html [{builtin.name}]",
                        f"site.html [{user.name}]",
                    ]
                ),
            )
            self.assertTrue(logger.select_template(2))
            self.assertEqual(logger.current_template.path, user / "site.html")
            self.assertFalse(logger.select_template(99))

            (builtin / "new.html").write_text("<html>new</html>", encoding="utf-8")
            refreshed = logger.refresh_templates()
            self.assertEqual(len(refreshed), 4)
            self.assertEqual(logger.current_template.path, user / "site.html")

    def test_injects_tracker_before_body_end(self):
        page = inject_tracker("<html><body>Hi</body></html>", "/pixel.gif?v=abc")
        self.assertLess(page.index("<script>"), page.index("</body>"))
        self.assertIn("/pixel.gif?v=abc", page)
        self.assertIn("<noscript>", page)


class IpLoggerServingTest(unittest.TestCase):
    def test_serves_site_beacon_and_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "site.html").write_text(
                "<html><head><title>Phishing Test</title></head>"
                "<body><h1>Hi</h1></body></html>",
                encoding="utf-8",
            )
            (root / "style.css").write_text("body { color: red }", encoding="utf-8")

            async def scenario():
                logger = IpLogger(geo=FakeGeo(), template_dirs=[root])
                await logger.start_server(free_port())
                try:
                    async with ClientSession() as client:
                        base = f"http://127.0.0.1:{logger.port}"
                        async with client.get(base + "/") as response:
                            html = await response.text()
                        self.assertEqual(response.status, 200)
                        self.assertIn("<h1>Hi</h1>", html)
                        self.assertEqual(len(logger.hits), 1)
                        self.assertEqual(logger.hits[0]["page_path"], "/")

                        match = re.search(
                            r'"(/__skyfall_iplogger/[^"]+/pixel\.gif)\?v='
                            r'([A-Za-z0-9_-]+)"',
                            html,
                        )
                        self.assertIsNotNone(match)
                        beacon_path, view_id = match.groups()

                        async with client.get(base + "/style.css") as response:
                            self.assertEqual(
                                await response.text(), "body { color: red }"
                            )
                        self.assertEqual(len(logger.hits), 1)

                        async with client.get(
                            base + beacon_path,
                            params={
                                "v": view_id,
                                "e": json.dumps(
                                    {
                                        "page_title": "Phishing Test",
                                        "screen": "1920x1080",
                                        "timezone": "Europe/Moscow",
                                    }
                                ),
                            },
                        ) as response:
                            self.assertEqual(response.status, 200)
                            self.assertEqual(
                                response.headers["Content-Type"], "image/gif"
                            )
                        self.assertEqual(len(logger.hits), 1)
                        hit = logger.hits[0]
                        self.assertEqual(hit["page_title"], "Phishing Test")
                        self.assertEqual(hit["screen"], "1920x1080")
                        self.assertEqual(hit["timezone"], "Europe/Moscow")
                        self.assertEqual(hit["location"], "Testville, Testland")
                finally:
                    await logger.stop()

            asyncio.run(scenario())

    def test_fallback_page_is_logged_without_templates(self):
        with tempfile.TemporaryDirectory() as folder:

            async def scenario():
                logger = IpLogger(geo=FakeGeo(), template_dirs=[Path(folder)])
                await logger.start_server(free_port())
                try:
                    async with ClientSession() as client:
                        async with client.get(
                            f"http://127.0.0.1:{logger.port}/"
                        ) as response:
                            html = await response.text()
                    self.assertIn("SkyFall IP Logger", html)
                    self.assertEqual(len(logger.hits), 1)
                finally:
                    await logger.stop()

            asyncio.run(scenario())


class ElevationIntegrationTest(unittest.TestCase):
    def test_low_port_serves_through_mocked_elevated_forwarder(self):
        async def scenario():
            logger = IpLogger(geo=FakeGeo(), template_dirs=[])
            with (
                mock.patch("src.modules.ip_logger.needs_elevation", return_value=True),
                mock.patch(
                    "src.modules.ip_logger.PrivilegedForwarder"
                ) as forwarder_class,
            ):
                forwarder_class.return_value.start = mock.AsyncMock()
                forwarder_class.return_value.stop = mock.AsyncMock()
                await logger.start_server(999)
                try:
                    self.assertEqual(logger.port, 999)
                    listen_port, target_port = forwarder_class.call_args.args
                    self.assertEqual(listen_port, 999)
                    self.assertGreater(target_port, 1024)
                    forwarder_class.return_value.start.assert_awaited_once()
                    async with ClientSession() as client:
                        async with client.get(
                            f"http://127.0.0.1:{target_port}/"
                        ) as response:
                            self.assertEqual(response.status, 200)
                finally:
                    await logger.stop()
                    forwarder_class.return_value.stop.assert_awaited_once()

        asyncio.run(scenario())


class FakeText:
    def __init__(self):
        self.text = ""

    def setPlainText(self, text):  # noqa: N802 - Qt API
        self.text = text

    def toPlainText(self):  # noqa: N802 - Qt API
        return self.text


class FakeMap:
    def __init__(self):
        self.html = ""

    def setHtml(self, html):  # noqa: N802 - Qt API
        self.html = html


class FakeUI:
    def __init__(self):
        self.ipLoggerDebug = FakeText()
        self.ipLoggerMap = FakeMap()


class ControllerDisplayTest(unittest.TestCase):
    def test_hit_details_are_visible_without_geolocation(self):
        logger = IpLogger(geo=FakeGeo(), template_dirs=[])
        ui = FakeUI()
        controller = IpLoggerController(ui, logger)
        controller.hits = [
            {
                "time": "2026-01-01T00:00:00+00:00",
                "ip": "1.2.3.4",
                "method": "GET",
                "path": "/",
                "host": "example:999",
                "user_agent": "TestAgent",
                "language": "en",
                "browser_language": "ru",
                "screen": "1920x1080",
                "timezone": "Europe/Moscow",
                "page_title": "Test Page",
                "page_url": "http://example:999/",
                "page_referrer": "http://example.org/",
                "isp": "Test ISP",
                "asn": "AS1",
                "geo_status": "ERROR",
                "geo_note": "no coords",
                "usage_type": "CDN",
            }
        ]
        controller._render()

        report = ui.ipLoggerDebug.toPlainText()
        for expected in (
            "1.2.3.4",
            "user-agent: TestAgent",
            "host: example:999",
            "isp/asn: Test ISP AS1",
            "title: Test Page",
            "page: http://example:999/",
            "page-referer: http://example.org/",
            "browser-language: ru",
            "browser: 1920x1080 Europe/Moscow",
            "geo: ERROR",
            "usage_type: CDN",
        ):
            self.assertIn(expected, report)

        # The map view keeps only geographic markers; all hit details live in
        # the debug pane.
        self.assertNotIn("TestAgent", ui.ipLoggerMap.html)


class ClientAddressTest(unittest.TestCase):
    def test_proxy_header_sets_remote_and_ignores_spoofed_xff(self):
        async def scenario():
            logger = IpLogger(geo=FakeGeo(), template_dirs=[])
            await logger.start_server(free_port())
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", logger.port)
                writer.write(
                    b"PROXY TCP4 203.0.113.7 10.0.0.1 5555 999\r\n"
                    b"GET / HTTP/1.1\r\nHost: x\r\n"
                    b"X-Forwarded-For: 9.9.9.9\r\nConnection: close\r\n\r\n"
                )
                await writer.drain()
                await reader.read()
                writer.close()
                await asyncio.sleep(0.05)
                hit = logger.hits[0]
                self.assertEqual(hit["ip"], "203.0.113.7")
                self.assertEqual(hit["ip_source"], "direct")
                self.assertEqual(hit["x_forwarded_for"], "9.9.9.9")
            finally:
                await logger.stop()

        asyncio.run(scenario())

    def test_direct_request_cannot_spoof_ip_via_xff(self):
        async def scenario():
            logger = IpLogger(geo=FakeGeo(), template_dirs=[])
            await logger.start_server(free_port())
            try:
                async with ClientSession() as client:
                    async with client.get(
                        f"http://127.0.0.1:{logger.port}/",
                        headers={"X-Forwarded-For": "9.9.9.9"},
                    ) as response:
                        await response.read()
                hit = logger.hits[0]
                self.assertEqual(hit["ip"], "127.0.0.1")
                self.assertEqual(hit["ip_source"], "direct")
                self.assertEqual(hit["x_forwarded_for"], "9.9.9.9")
            finally:
                await logger.stop()

        asyncio.run(scenario())

    def test_trusted_proxy_honours_xff(self):
        async def scenario():
            logger = IpLogger(
                geo=FakeGeo(), template_dirs=[], trusted_proxies=["127.0.0.1"]
            )
            await logger.start_server(free_port())
            try:
                async with ClientSession() as client:
                    async with client.get(
                        f"http://127.0.0.1:{logger.port}/",
                        headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"},
                    ) as response:
                        await response.read()
                hit = logger.hits[0]
                self.assertEqual(hit["ip"], "203.0.113.9")
                self.assertEqual(hit["ip_source"], "x-forwarded-for")
            finally:
                await logger.stop()

        asyncio.run(scenario())

    def test_parse_proxy_header(self):
        self.assertEqual(
            parse_proxy_header(b"PROXY TCP4 1.2.3.4 5.6.7.8 111 222"),
            ("1.2.3.4", 111),
        )
        self.assertEqual(
            parse_proxy_header(b"PROXY TCP6 2001:db8::1 2001:db8::2 5 6"),
            ("2001:db8::1", 5),
        )
        self.assertIsNone(parse_proxy_header(b"PROXY UNKNOWN"))
        self.assertIsNone(parse_proxy_header(b"not a proxy header"))

    def test_forwarder_builds_proxy_header(self):
        self.assertEqual(
            _proxy_header(("203.0.113.7", 5555), ("10.0.0.1", 999)),
            b"PROXY TCP4 203.0.113.7 10.0.0.1 5555 999\r\n",
        )
        self.assertEqual(
            _proxy_header(("2001:db8::1", 5), ("2001:db8::2", 6)),
            b"PROXY TCP6 2001:db8::1 2001:db8::2 5 6\r\n",
        )
        self.assertEqual(_proxy_header(None, None), b"PROXY UNKNOWN\r\n")


class PublicIpTest(unittest.TestCase):
    def test_urls_include_public_ip_and_bracket_ipv6(self):
        logger = IpLogger(geo=FakeGeo(), template_dirs=[])
        logger.port = 999
        logger.public_ip = "203.0.113.5"
        self.assertIn("http://203.0.113.5:999/", logger.urls())
        logger.public_ip = "2001:db8::1"
        self.assertIn("http://[2001:db8::1]:999/", logger.urls())

    def test_resolve_public_ip_notifies_state_and_resets_on_stop(self):
        async def scenario():
            logger = IpLogger(geo=FakeGeo(), template_dirs=[])
            await logger.start_server(free_port())
            seen = []
            logger.on_state(lambda: seen.append(logger.public_ip))
            with mock.patch(
                "src.modules.ip_logger._fetch_public_ip",
                return_value="198.51.100.4",
            ):
                ip = await logger.resolve_public_ip()
            self.assertEqual(ip, "198.51.100.4")
            self.assertEqual(seen, ["198.51.100.4"])
            await logger.stop()
            self.assertEqual(logger.public_ip, "")

        asyncio.run(scenario())


class PrivilegeTest(unittest.TestCase):
    def test_only_low_ports_need_elevation(self):
        with mock.patch(
            "src.modules.ip_logger_privilege.os.geteuid", return_value=1000
        ):
            self.assertTrue(needs_elevation(999))
            self.assertFalse(needs_elevation(1024))
            self.assertFalse(needs_elevation(8080))
        with mock.patch("src.modules.ip_logger_privilege.os.geteuid", return_value=0):
            self.assertFalse(needs_elevation(80))

    def test_native_command_builders(self):
        args = ["forwarder.py", "999", "43210"]
        command = linux_command(args, python="/usr/bin/python3")
        self.assertEqual(command, ["pkexec", "/usr/bin/python3", *args])
        script = macos_script(args, python="/usr/bin/python3")
        self.assertIn("with administrator privileges", script)
        self.assertIn("/usr/bin/python3", script)
        self.assertEqual(
            windows_forwarder("/usr/bin/python.exe"), "/usr/bin/python.exe"
        )


if __name__ == "__main__":
    unittest.main()
