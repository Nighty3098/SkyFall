"""Tests for the Shodan API client, tab controller helpers and transforms."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import src.modules.shodan_search as shodan_module
from src.controllers.graph_transform_controller import (
    GraphTransformController,
    _parse_shodan_dns,
    _parse_shodan_exploits,
    _parse_shodan_honeyscore,
    _parse_shodan_host,
    _parse_shodan_search,
)
from src.controllers.shodan_controller import ShodanController
from src.modules.shodan_search import ShodanSearch

HOST = {
    "ip": "1.2.3.4",
    "org": "Example Org",
    "isp": "Example ISP",
    "asn": "AS64500",
    "city": "Berlin",
    "country_name": "Germany",
    "latitude": 52.52,
    "longitude": 13.405,
    "hostnames": ["api.example.com", "www.example.com"],
    "ports": [80, 443],
    "data": [
        {
            "port": 443,
            "transport": "tcp",
            "product": "nginx",
            "version": "1.25",
            "banner": "HTTP/1.1 200 OK",
            "_shodan": {"module": "https"},
        }
    ],
    "vulns": {"CVE-2024-0001": {"cvss": 9.8}},
}


class FakeDns:
    def domain_info(self, domain, history=False, type=None, page=1):
        return {
            "domain": domain,
            "data": [
                {"subdomain": "www", "type": "A", "value": "1.2.3.4"},
                {"subdomain": "www", "type": "A", "value": "1.2.3.4"},
            ],
        }


class FakeExploits:
    def search(self, query, page=1, facets=None):
        return {
            "total": 1,
            "matches": [
                {
                    "source": "exploit-db",
                    "cve": "CVE-2024-0001",
                    "description": "Demo exploit",
                }
            ],
        }

    def count(self, query, facets=None):
        return {"total": 1}


class FakeLabs:
    def honeyscore(self, ip):
        return 0.75


class FakeTools:
    def myip(self):
        return "203.0.113.1"


class FakeClient:
    def __init__(self, api_key, proxies=None):
        self.api_key = api_key
        self.proxies = proxies
        self.dns = FakeDns()
        self.exploits = FakeExploits()
        self.labs = FakeLabs()
        self.tools = FakeTools()

    def info(self):
        return {"plan": "dev", "query_credits": 100}

    def host(self, ips, history=False, minify=False):
        return HOST

    def search(self, query, page=1, minify=True, **kwargs):
        return {
            "total": 1,
            "matches": [{"ip_str": "1.2.3.4", "port": 443, "org": "Example Org"}],
            "facets": {"country": [{"value": "DE", "count": 1}]},
        }

    def count(self, query, facets=None):
        return {"total": 1}

    def queries(self, page=1, sort="timestamp", order="desc"):
        return {"total": 1, "matches": [{"title": "nginx"}]}

    def search_facets(self):
        return ["country", "port"]

    def search_filters(self):
        return ["hostname", "port"]

    def search_tokens(self, query):
        return ["token"]

    def ports(self):
        return [80, 443]

    def protocols(self):
        return ["http", "https"]

    def services(self):
        return {"https": "Hypertext Transfer Protocol Secure"}

    def scan(self, ips, force=False):
        return {"id": "scan-1", "status": "SUBMITTED"}

    def scan_status(self, scan_id):
        return {"id": scan_id, "status": "DONE"}

    def scans(self, page=1):
        return {"matches": [{"id": "scan-1"}]}

    def alerts(self, aid=None, include_expired=True):
        return {"matches": [{"id": "alert-1"}]}

    def create_alert(self, name, ip, expires=0):
        return {"id": "alert-1", "name": name}

    def delete_alert(self, aid):
        return None

    def edit_alert(self, aid, ip):
        return None

    def alert_triggers(self):
        return [{"name": "Malware"}]

    def add_alert_notifier(self, aid, nid):
        return None

    def remove_alert_notifier(self, aid, nid):
        return None


class FakeSdk(SimpleNamespace):
    Shodan = FakeClient


class ShodanClientTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = ShodanSearch("test-key")
        self.sdk_patch = patch.object(shodan_module, "shodan_sdk", FakeSdk())
        self.sdk_patch.start()

    def tearDown(self):
        self.sdk_patch.stop()

    async def test_missing_api_key_is_reported(self):
        engine = ShodanSearch()
        result = await engine.host("1.2.3.4")
        self.assertIn("error", result)
        self.assertIn("API key", result["error"])

    async def test_key_update_invalidates_client(self):
        await self.engine.info()
        old_client = self.engine._client
        self.engine.set_api_key("new-key")
        await self.engine.info()
        self.assertIsNot(self.engine._client, old_client)
        self.assertEqual(self.engine._client.api_key, "new-key")

    async def test_host_search_count_and_dns(self):
        host = await self.engine.host("1.2.3.4")
        self.assertEqual(host["ip"], "1.2.3.4")

        search = await self.engine.search("apache", page=2)
        self.assertEqual(search["total"], 1)

        count = await self.engine.count("apache")
        self.assertEqual(count["total"], 1)

        dns = await self.engine.domain_info("example.com")
        self.assertEqual(dns["domain"], "example.com")

    async def test_api_utilities_are_wrapped(self):
        self.assertEqual((await self.engine.info())["plan"], "dev")
        self.assertEqual((await self.engine.my_ip())["ip"], "203.0.113.1")
        self.assertEqual((await self.engine.ports())["ports"], [80, 443])
        protocols = await self.engine.protocols()
        self.assertEqual(protocols["protocols"], ["http", "https"])
        self.assertIn("https", (await self.engine.services())["services"])
        facets = await self.engine.search_facets()
        self.assertEqual(facets["facets"], ["country", "port"])
        tokens = await self.engine.search_tokens("nginx")
        self.assertEqual(tokens["tokens"], ["token"])

    async def test_intelligence_and_scans(self):
        honey = await self.engine.honeyscore("1.2.3.4")
        self.assertEqual(honey["honeyscore"], 0.75)

        exploits = await self.engine.exploits("CVE-2024")
        self.assertEqual(exploits["total"], 1)
        self.assertEqual((await self.engine.exploits_count("CVE-2024"))["total"], 1)

        scan = await self.engine.scan("1.2.3.4")
        self.assertEqual(scan["id"], "scan-1")
        self.assertEqual((await self.engine.scan_status("scan-1"))["status"], "DONE")
        self.assertEqual((await self.engine.scans())["matches"][0]["id"], "scan-1")

    async def test_alerts(self):
        self.assertEqual((await self.engine.alerts())["matches"][0]["id"], "alert-1")
        created = await self.engine.create_alert("test", "1.2.3.4")
        self.assertEqual(created["name"], "test")
        deleted = await self.engine.delete_alert("alert-1")
        self.assertEqual(deleted["deleted"], "alert-1")
        self.assertEqual(
            (await self.engine.edit_alert("alert-1", "1.2.3.5"))["ip"], "1.2.3.5"
        )
        triggers = await self.engine.alert_triggers()
        self.assertEqual(triggers["triggers"][0]["name"], "Malware")
        added = await self.engine.add_alert_notifier("alert-1", "notifier-1")
        self.assertTrue(added["added"])
        removed = await self.engine.remove_alert_notifier("alert-1", "notifier-1")
        self.assertTrue(removed["removed"])

    async def test_sdk_errors_are_converted_to_dicts(self):
        class BrokenClient(FakeClient):
            def host(self, ips, history=False, minify=False):
                raise RuntimeError("rate limited")

        broken_sdk = SimpleNamespace(Shodan=BrokenClient)
        with patch.object(shodan_module, "shodan_sdk", broken_sdk):
            result = await self.engine.host("1.2.3.4")
        self.assertIsInstance(result, dict)
        self.assertIn("rate limited", result["error"])


class ShodanTransformTest(unittest.TestCase):
    def test_settings_wiring_is_complete(self):
        from src import security
        from src.controllers.settings_controller import DEFAULT_SETTINGS, FIELD_MAP

        self.assertIn("shodan_api_key", DEFAULT_SETTINGS)
        self.assertEqual(FIELD_MAP["shodan_api_key"], "shodanApiKeyEdit")
        self.assertIn("shodan_api_key", security.SENSITIVE_KEYS)

    def test_registry_integrates_shodan_transforms(self):
        controller = GraphTransformController(None, {}, plugin_dir=None)

        def names(entity_type):
            node = type("Node", (), {"entity_type": entity_type})()
            return {transform.name for transform in controller.get_transforms(node)}

        self.assertIn("Shodan Host", names("IP"))
        self.assertIn("Shodan Honeyscore", names("IP"))
        self.assertIn("Shodan DNS", names("Domain"))
        self.assertIn("Shodan Hosts", names("Domain"))
        self.assertIn("Shodan Hosts", names("Organization"))
        self.assertIn("Shodan Search", names("Custom"))
        self.assertIn("Shodan Exploits", names("Custom"))

    def test_host_parser_builds_entity_nodes(self):
        result = _parse_shodan_host(HOST, "1.2.3.4")
        self.assertIn("1.2.3.4", result.content)
        self.assertIn("https://www.shodan.io/host/1.2.3.4", result.evidence)
        types = {child.entity_type for child in result.children}
        self.assertIn("Organization", types)
        self.assertIn("Geolocation", types)
        self.assertIn("Domain", types)
        self.assertIn("Custom", types)
        titles = [child.title for child in result.children]
        self.assertIn("CVE-2024-0001", titles)

    def test_dns_parser_deduplicates_records(self):
        result = _parse_shodan_dns(
            {
                "domain": "example.com",
                "data": [
                    {"subdomain": "www", "type": "A", "value": "1.2.3.4"},
                    {"subdomain": "www", "type": "A", "value": "1.2.3.4"},
                    {"subdomain": "api", "type": "A", "value": "1.2.3.5"},
                ],
            },
            "example.com",
        )
        titles = [child.title for child in result.children]
        self.assertEqual(titles, ["www.example.com", "api.example.com"])

    def test_search_parser_and_errors(self):
        result = _parse_shodan_search(
            {
                "total": 1,
                "matches": [{"ip_str": "1.2.3.4", "port": 443}],
                "facets": {"country": [{"value": "DE", "count": 1}]},
            },
            "apache",
        )
        self.assertTrue(result.children)
        self.assertEqual(result.children[0].entity_type, "IP")
        self.assertIn("apache", result.content)

        missing = _parse_shodan_search({"error": "no key"}, "apache")
        self.assertIn("no key", missing.content)

    def test_honeyscore_and_exploits_parsers(self):
        score = {"ip": "1.2.3.4", "honeyscore": 0.8}
        honey = _parse_shodan_honeyscore(score, "1.2.3.4")
        self.assertIn("likely honeypot", honey.content)
        self.assertEqual(honey.children[0].entity_type, "Custom")

        exploits = _parse_shodan_exploits(
            {"total": 1, "matches": [{"cve": "CVE-2024-0001", "description": "demo"}]},
            "CVE-2024",
        )
        self.assertEqual(exploits.children[0].title, "CVE-2024-0001")
        self.assertIn("demo", exploits.content)

    def test_graph_payload_helpers(self):
        anchor, children = ShodanController._graph_payload("host", "1.2.3.4", HOST)
        self.assertEqual(anchor, "IP")
        self.assertTrue(children)
        self.assertTrue(all("entity_type" in child for child in children))


if __name__ == "__main__":
    unittest.main()
