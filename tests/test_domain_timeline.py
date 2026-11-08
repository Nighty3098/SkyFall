import unittest

from src.modules.ipgeolocation_security import classify_security
from src.modules.whois_freaks import build_domain_timeline


class BuildDomainTimelineTest(unittest.TestCase):
    def test_builds_observed_and_reported_events(self):
        dns = {
            "snapshots": [
                {
                    "query_time": "2024-01-02T00:00:00Z",
                    "domain_name": "example.com",
                    "dns_types": ["A", "NS"],
                    "records": [
                        {"type": "A", "addresses": ["1.2.3.4"]},
                        {"type": "NS", "value": "ns1.example.net"},
                    ],
                }
            ]
        }
        whois = {
            "records": [
                {
                    "query_time": "2024-01-03T00:00:00Z",
                    "created": "2020-01-01",
                    "registrar": "Example Registrar",
                }
            ]
        }

        result = build_domain_timeline(dns_history=dns, whois_history=whois)

        self.assertEqual(result["status"], "OK")
        types = [e["type"] for e in result["events"]]
        self.assertIn("dns_snapshot", types)
        self.assertIn("whois_snapshot", types)
        self.assertIn("reported_creation_date", types)
        dns_event = next(e for e in result["events"] if e["type"] == "dns_snapshot")
        self.assertEqual(dns_event["details"]["ip_addresses"], ["1.2.3.4"])
        self.assertEqual(dns_event["semantics"], "observed")

    def test_handles_missing_data(self):
        result = build_domain_timeline(dns_history=None, whois_history=None)
        self.assertEqual(result["status"], "NO_DATA")
        self.assertEqual(result["events"], [])
        self.assertTrue(result["notes"])


class IPGeolocationClassificationTest(unittest.TestCase):
    def test_high_score_is_suspicious_or_worse(self):
        status, reasons = classify_security({"threat_score": 90})
        self.assertIn(status, ("SUSPICIOUS", "MALICIOUS"))
        self.assertTrue(reasons)

    def test_known_attacker_is_malicious(self):
        status, reasons = classify_security(
            {"threat_score": 10, "is_known_attacker": True}
        )
        self.assertEqual(status, "MALICIOUS")
        self.assertIn("known attacker", reasons)

    def test_proxy_is_suspicious_signal(self):
        status, reasons = classify_security({"threat_score": 0, "is_proxy": True})
        self.assertEqual(status, "SUSPICIOUS")
        self.assertIn("proxy", reasons)

    def test_clean_low_score(self):
        status, reasons = classify_security({"threat_score": 0})
        self.assertEqual(status, "CLEAN")
        self.assertTrue(reasons)


if __name__ == "__main__":
    unittest.main()
