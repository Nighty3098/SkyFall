import unittest
from unittest.mock import patch

from src.modules import whois_freaks


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


def _history_payload():
    return {
        "status": True,
        "whois": "historical",
        "total_records": "2",
        "whois_domains_historical": [
            {
                "query_time": "2024-01-01 00:00:00",
                "create_date": "2019-03-19",
                "update_date": "2024-02-18",
                "expiry_date": "2025-03-19",
                "domain_registrar": {"registrar_name": "NAMECHEAP INC"},
                "registrant_contact": {
                    "name": "Redacted for Privacy",
                    "company": "Privacy service provided by Withheld for Privacy",
                    "email_address": "redacted@example.test",
                },
                "name_servers": ["ns1.example.test"],
                "domain_status": ["clienttransferprohibited"],
            },
            {
                "query_time": "2015-01-01 00:00:00",
                "registrant_contact": {
                    "name": "Jane Analyst",
                    "company": "Acme Research",
                    "email_address": "jane@acme.test",
                },
                "name_servers": ["old.example.test"],
            },
        ],
    }


class WhoisFreaksHistoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_key_is_skipped_without_a_request(self):
        with patch.object(whois_freaks.requests, "get") as request:
            result = await whois_freaks.WhoisFreaks("").history("example.com")
        self.assertEqual(result["status"], "SKIPPED")
        request.assert_not_called()

    async def test_history_request_and_parsing(self):
        seen = {}

        def fake_get(url, **kwargs):
            seen["url"] = url
            seen["params"] = kwargs["params"]
            return FakeResponse(_history_payload())

        with patch.object(whois_freaks.requests, "get", side_effect=fake_get):
            result = await whois_freaks.WhoisFreaks("key-123").history(
                "https://Example.com/path", limit=1
            )

        self.assertTrue(seen["url"].endswith("/history"))
        self.assertEqual(seen["params"]["apiKey"], "key-123")
        self.assertEqual(seen["params"]["domainName"], "example.com")
        self.assertEqual(result["total_records"], 2)
        self.assertEqual(result["returned"], 1)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["records"][0]["registrar"], "NAMECHEAP INC")
        self.assertEqual(
            result["records"][0]["registrant"]["name"], "Redacted for Privacy"
        )

    async def test_invalid_key_is_reported(self):
        with patch.object(
            whois_freaks.requests,
            "get",
            return_value=FakeResponse({"message": "Provided API key is invalid"}, 401),
        ):
            result = await whois_freaks.WhoisFreaks("bad").history("example.com")

        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid API key", result["note"])


class WhoisFreaksReverseTest(unittest.IsolatedAsyncioTestCase):
    async def test_reverse_requires_one_pivot(self):
        whois = whois_freaks.WhoisFreaks("key")
        result = await whois.reverse()
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("exactly one", result["note"])

        result = await whois.reverse(email="a@b.test", company="Acme")
        self.assertEqual(result["status"], "ERROR")

    async def test_reverse_request_and_parsing(self):
        seen = {}

        def fake_get(url, **kwargs):
            seen["url"] = url
            seen["params"] = kwargs["params"]
            return FakeResponse(
                {
                    "total_Result": 1,
                    "total_Pages": 1,
                    "current_Page": 1,
                    "whois_domains_historical": [
                        {
                            "domain_name": "acme.test",
                            "create_date": "2020-01-01",
                            "domain_registrar": {"registrar_name": "Registrar"},
                            "registrant_contact": {
                                "name": "Jane",
                                "company": "Acme",
                                "email_address": "jane@acme.test",
                            },
                        }
                    ],
                }
            )

        with patch.object(whois_freaks.requests, "get", side_effect=fake_get):
            result = await whois_freaks.WhoisFreaks("key").reverse(
                company="Acme", mode="mini", exact=True
            )

        self.assertTrue(seen["url"].endswith("/reverse"))
        self.assertEqual(seen["params"]["company"], "Acme")
        self.assertEqual(seen["params"]["exact"], "true")
        self.assertEqual(seen["params"]["mode"], "mini")
        self.assertEqual(result["total_results"], 1)
        self.assertEqual(result["domains"][0]["domain_name"], "acme.test")
        self.assertEqual(result["domains"][0]["email"], "jane@acme.test")


class WhoisPivotTest(unittest.TestCase):
    def test_build_pivots_skips_redacted_values(self):
        pivots = whois_freaks.build_reverse_pivots(
            {"records": _history_payload()["whois_domains_historical"]}
        )
        self.assertEqual(
            pivots,
            [
                {"type": "email", "value": "jane@acme.test"},
                {"type": "company", "value": "Acme Research"},
            ],
        )

    def test_build_pivots_can_fall_back_to_current_whois(self):
        pivots = whois_freaks.build_reverse_pivots(
            None, current_whois={"emails": ["owner@example.test"], "org": "Example"}
        )
        self.assertEqual(
            pivots,
            [
                {"type": "email", "value": "owner@example.test"},
                {"type": "company", "value": "Example"},
            ],
        )

    def test_parse_reverse_query(self):
        self.assertEqual(
            whois_freaks.parse_reverse_query("jane@acme.test"),
            {"email": "jane@acme.test"},
        )
        self.assertEqual(
            whois_freaks.parse_reverse_query("Acme Research"),
            {"company": "Acme Research"},
        )
        self.assertEqual(
            whois_freaks.parse_reverse_query("keyword:acme"),
            {"keyword": "acme"},
        )
        self.assertIsNone(whois_freaks.parse_reverse_query(""))

    def test_merge_deduplicates_domains(self):
        pivots = [
            {"type": "email", "value": "jane@acme.test"},
            {"type": "company", "value": "Acme"},
        ]
        results = [
            {
                "status": "OK",
                "total_results": 2,
                "total_pages": 1,
                "domains": [
                    {"domain_name": "acme.test", "email": "jane@acme.test"},
                    {"domain_name": "one.test"},
                ],
            },
            {
                "status": "OK",
                "total_results": 1,
                "total_pages": 1,
                "domains": [{"domain_name": "ACME.test", "company": "Acme"}],
            },
        ]
        merged = whois_freaks.merge_reverse_results(results, pivots)
        self.assertEqual(merged["status"], "OK")
        self.assertEqual(merged["total_domains"], 2)
        acme = next(d for d in merged["domains"] if d["domain_name"] == "acme.test")
        self.assertEqual(len(acme["matched_on"]), 2)


if __name__ == "__main__":
    unittest.main()
