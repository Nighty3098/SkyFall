import unittest
from types import SimpleNamespace

from src.controllers.domain_controller import DomainController


class FakeOutput:
    def __init__(self):
        self.text = ""

    def set_output_text(self, text):
        self.text = text


class FakeEdit:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text


class FakeCheck:
    def __init__(self, checked=False):
        self._checked = checked

    def isChecked(self):  # noqa: N802 - Qt API
        return self._checked


class FakeAnalyzer:
    def __init__(self):
        self.calls = []
        self.history = {
            "status": "OK",
            "records": [{"registrant": {"email": "jane@acme.test"}}],
        }
        self.whois = {"emails": ["owner@example.test"], "org": "Example"}
        self.dns_history = {
            "status": "OK",
            "snapshots": [
                {
                    "query_time": "2024-01-01T00:00:00Z",
                    "domain_name": "example.com",
                    "dns_types": ["A"],
                    "records": [{"type": "A", "addresses": ["1.2.3.4"]}],
                }
            ],
        }

    async def get_whois_history(self, domain, limit=50):
        self.calls.append(("history", domain))
        return self.history

    async def get_dns_history(self, domain, dns_type="all", max_pages=5):
        self.calls.append(("dns_history", domain))
        return self.dns_history

    async def get_whois_info(self, domain):
        self.calls.append(("whois", domain))
        return self.whois

    async def reverse_whois_from_query(self, query, page=1, mode="mini"):
        self.calls.append(("query", query))
        return {"status": "OK", "kind": "reverse", "domains": []}

    async def reverse_whois_from_pivots(
        self, history, current_whois=None, max_pivots=2
    ):
        self.calls.append(("pivots", history, current_whois))
        return {"status": "OK", "kind": "reverse", "domains": []}

    async def build_domain_timeline(
        self, dns_history=None, whois_history=None, current_whois=None
    ):
        self.calls.append(("timeline", dns_history, whois_history))
        return {"status": "OK", "total_events": 1, "events": [{"type": "dns_snapshot"}]}

    async def check_ip2location(self, domain):
        self.calls.append(("ip2location", domain))
        return {
            "ip": "8.8.8.8",
            "status": "CLEAN",
            "country_name": "United States",
            "city_name": "Mountain View",
            "asn": "15169",
            "as": "Google LLC",
            "is_proxy": False,
            "keyless": True,
        }


def make_controller(url="example.com", query="", whois_domain=""):
    ui = SimpleNamespace(
        whoisDomainEdit=FakeEdit(whois_domain if whois_domain != "" else url),
        infraDomainEdit=FakeEdit(""),
        webSurfaceDomainEdit=FakeEdit(""),
        discoveryDomainEdit=FakeEdit(""),
        securityDomainEdit=FakeEdit(""),
        reverseWhoisQueryEdit=FakeEdit(query),
        serverWhoisHistoryDebug=FakeOutput(),
        serverReverseWhoisDebug=FakeOutput(),
        serverDomainTimelineDebug=FakeOutput(),
        serverWhoisDebug=FakeOutput(),
        domainWhoisCheck=FakeCheck(False),
    )
    analyzer = FakeAnalyzer()
    controller = DomainController(ui, analyzer)
    controller.set_domain(url)
    return controller, ui, analyzer


class AnalyzeWhoisTest(unittest.IsolatedAsyncioTestCase):
    async def test_runs_history_and_auto_reverse(self):
        controller, ui, analyzer = make_controller(url="Example.com/path")

        await controller.analyze_whois()

        self.assertEqual(controller.domain, "Example.com/path")
        self.assertIn(("history", "Example.com/path"), analyzer.calls)
        self.assertIn(("whois", "Example.com/path"), analyzer.calls)
        self.assertIn(
            ("pivots", analyzer.history, analyzer.whois),
            analyzer.calls,
        )
        self.assertIn("WHOIS history", ui.serverWhoisHistoryDebug.text)
        self.assertIn("Reverse WHOIS", ui.serverReverseWhoisDebug.text)

    async def test_manual_query_skips_pivot_lookup(self):
        controller, ui, analyzer = make_controller(query="company:Acme")

        await controller.analyze_whois()

        self.assertIn(("query", "company:Acme"), analyzer.calls)
        self.assertNotIn("whois", [call[0] for call in analyzer.calls])
        self.assertNotIn("pivots", [call[0] for call in analyzer.calls])

    async def test_requires_a_domain_or_query(self):
        controller, ui, analyzer = make_controller(url="")

        await controller.analyze_whois()

        self.assertEqual(analyzer.calls, [])
        self.assertIn(
            "Enter a domain or a reverse WHOIS query",
            ui.serverWhoisHistoryDebug.text,
        )
        self.assertIn(
            "Enter a domain or a reverse WHOIS query",
            ui.serverReverseWhoisDebug.text,
        )

    async def test_manual_query_works_without_domain(self):
        controller, ui, analyzer = make_controller(url="", query="company:Acme")

        await controller.analyze_whois()

        self.assertIn(("query", "company:Acme"), analyzer.calls)
        self.assertNotIn("history", [call[0] for call in analyzer.calls])
        self.assertNotIn("whois", [call[0] for call in analyzer.calls])
        self.assertNotIn("pivots", [call[0] for call in analyzer.calls])
        self.assertIn(
            "Enter a domain to load WHOIS history", ui.serverWhoisHistoryDebug.text
        )
        self.assertIn("Reverse WHOIS", ui.serverReverseWhoisDebug.text)

    async def test_falls_back_to_last_scanned_domain(self):
        controller, ui, analyzer = make_controller(url="")
        controller.set_domain("last.example")

        await controller.analyze_whois()

        self.assertEqual(controller.domain, "last.example")
        self.assertIn(("history", "last.example"), analyzer.calls)

    async def test_reuses_current_whois_from_a_basic_scan(self):
        controller, ui, analyzer = make_controller()
        cached = {"emails": ["cached@example.test"]}
        controller._whois_cache = cached
        controller._whois_cache_domain = "example.com"

        await controller.analyze_whois()

        self.assertNotIn("whois", [call[0] for call in analyzer.calls])
        self.assertIn(("pivots", analyzer.history, cached), analyzer.calls)

    async def test_uses_whois_domain_input_when_set(self):
        controller, ui, analyzer = make_controller(
            url="basic.example", whois_domain="whois.example"
        )

        await controller.analyze_whois()

        self.assertEqual(controller.domain, "whois.example")
        self.assertIn(("history", "whois.example"), analyzer.calls)
        self.assertNotIn(("history", "basic.example"), analyzer.calls)


class AnalyzeIP2LocationTabsTest(unittest.IsolatedAsyncioTestCase):
    def _enable(self, ui):
        ui.domainIP2LocationGeoCheck = FakeCheck(True)
        ui.ip2locationGeoDebug = FakeOutput()
        ui.domainIP2LocationCheck = FakeCheck(True)
        ui.ip2locationNetworkDebug = FakeOutput()
        ui.ip2locationThreatDebug = FakeOutput()

    async def test_infra_renders_only_the_geolocation_block(self):
        controller, ui, analyzer = make_controller()
        self._enable(ui)

        await controller.analyze_infra()

        self.assertIn("United States", ui.ip2locationGeoDebug.text)
        self.assertEqual(
            [call for call in analyzer.calls if call[0] == "ip2location"],
            [("ip2location", "example.com")],
        )

    async def test_security_reuses_the_infra_result(self):
        controller, ui, analyzer = make_controller()
        self._enable(ui)

        await controller.analyze_infra()
        await controller.analyze_security(reuse_ip2location=True)

        self.assertEqual([call[0] for call in analyzer.calls].count("ip2location"), 1)
        self.assertIn("15169", ui.ip2locationNetworkDebug.text)
        self.assertIn("none", ui.ip2locationThreatDebug.text)

    async def test_standalone_security_scan_refreshes_the_result(self):
        controller, ui, analyzer = make_controller()
        self._enable(ui)

        await controller.analyze_infra()
        await controller.analyze_security()

        self.assertEqual([call[0] for call in analyzer.calls].count("ip2location"), 2)


if __name__ == "__main__":
    unittest.main()
