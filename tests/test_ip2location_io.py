import unittest
from unittest.mock import patch

from src.controllers.domain_controller import DomainController
from src.modules.domain_analyzer import DomainAnalyzer
from src.modules.ip2location_io import (
    IP2LocationIO,
    classify_ip2location,
)
from src.transforms.builtin import build_builtin_registry
from src.transforms.builtin_handlers import _parse_domain_ip


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


PAYLOAD = {
    "ip": "8.8.8.8",
    "country_code": "US",
    "country_name": "United States of America",
    "region_name": "California",
    "city_name": "Mountain View",
    "latitude": 37.405992,
    "longitude": -122.078515,
    "zip_code": "94043",
    "time_zone": "-07:00",
    "asn": "15169",
    "as": "Google LLC",
    "isp": "Google LLC",
    "domain": "google.com",
    "usage_type": "DCH",
    "is_proxy": False,
}


class ClassifyTest(unittest.TestCase):
    def test_clean_payload(self):
        status, reasons = classify_ip2location(PAYLOAD)
        self.assertEqual(status, "CLEAN")
        self.assertEqual(reasons, [])

    def test_proxy_is_suspicious(self):
        status, reasons = classify_ip2location({"is_proxy": True})
        self.assertEqual(status, "SUSPICIOUS")
        self.assertIn("proxy", reasons)

    def test_tor_and_high_fraud_are_malicious(self):
        status, _ = classify_ip2location({"proxy": {"is_tor": True}})
        self.assertEqual(status, "MALICIOUS")
        status, _ = classify_ip2location({"fraud_score": 92})
        self.assertEqual(status, "MALICIOUS")

    def test_data_center_is_info(self):
        status, reasons = classify_ip2location({"proxy": {"is_data_center": True}})
        self.assertEqual(status, "INFO")
        self.assertIn("data center", reasons)


class LookupTest(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_invalid_ip(self):
        result = await IP2LocationIO().lookup("not-an-ip")
        self.assertEqual(result["status"], "SKIPPED")

    async def test_keyless_lookup_omits_key_and_normalizes(self):
        with patch(
            "src.modules.ip2location_io.requests.get",
            return_value=FakeResponse(payload=PAYLOAD),
        ) as get:
            result = await IP2LocationIO().lookup("8.8.8.8")

        params = get.call_args.kwargs["params"]
        self.assertNotIn("key", params)
        self.assertEqual(params["ip"], "8.8.8.8")
        self.assertEqual(result["source"], "IP2Location.io")
        self.assertEqual(result["country"], "United States of America")
        self.assertEqual(result["country_code"], "US")
        self.assertEqual(result["city"], "Mountain View")
        self.assertEqual(result["asn"], "15169")
        self.assertEqual(result["lat"], 37.405992)
        self.assertTrue(result["keyless"])
        self.assertEqual(result["status"], "CLEAN")

    async def test_configured_key_is_sent(self):
        with patch(
            "src.modules.ip2location_io.requests.get",
            return_value=FakeResponse(payload=PAYLOAD),
        ) as get:
            await IP2LocationIO("secret-key").lookup("8.8.8.8")

        self.assertEqual(get.call_args.kwargs["params"]["key"], "secret-key")

    async def test_api_error_object_is_reported(self):
        payload = {"error": {"error_code": 10000, "error_message": "Invalid IP"}}
        with patch(
            "src.modules.ip2location_io.requests.get",
            return_value=FakeResponse(payload=payload),
        ):
            result = await IP2LocationIO().lookup("8.8.8.8")

        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Invalid IP", result["note"])

    async def test_rate_limit_is_reported(self):
        with patch(
            "src.modules.ip2location_io.requests.get",
            return_value=FakeResponse(status_code=429),
        ):
            result = await IP2LocationIO().lookup("8.8.8.8")

        self.assertEqual(result["status"], "ERROR")
        self.assertIn("Rate limited", result["note"])


class ControllerBlocksTest(unittest.TestCase):
    def test_success_is_split_into_labelled_blocks(self):
        geo, network, threat = DomainController._ip2location_blocks(
            {
                "ip": "8.8.8.8",
                "status": "SUSPICIOUS",
                "country_name": "United States",
                "city_name": "Mountain View",
                "asn": "15169",
                "as": "Google LLC",
                "isp": "Google LLC",
                "usage_type": "DCH",
                "is_proxy": True,
                "fraud_score": 40,
                "keyless": True,
            }
        )

        self.assertIn("United States", geo)
        self.assertIn("15169", network)
        self.assertIn("Proxy", threat)
        self.assertIn("Fraud score", threat)
        self.assertIn("Flags", threat)

    def test_error_is_repeated_in_every_block(self):
        blocks = DomainController._ip2location_blocks(
            {"status": "ERROR", "note": "Rate limited"}
        )
        self.assertEqual(len(blocks), 3)
        for block in blocks:
            self.assertIn("Rate limited", block)


class TransformRegistryTest(unittest.TestCase):
    def test_ip_nodes_have_ip2location_transform(self):
        names = [t.name for t in build_builtin_registry()["IP"]]
        self.assertIn("IP2Location.io lookup", names)

    def test_domain_ip_parser_renders_provider_consensus(self):
        result = _parse_domain_ip(
            {
                "ip": "8.8.8.8",
                "country": "United States",
                "city": "Mountain View",
                "asn": "15169",
                "provider": "ipapi.co",
                "confidence": "high",
                "consensus": {
                    "country": "United States",
                    "country_agreement": "3/3",
                    "providers": 3,
                },
                "providers": [
                    {"provider": "ipapi.co", "country": "United States"},
                    {"provider": "IP2Location.io", "country": "United States"},
                ],
            },
            "example.com",
        )

        self.assertIn("Country consensus: United States (3/3)", result.content)
        self.assertIn("IP2Location.io", result.content)
        self.assertNotIn("{'provider'", result.content)


class GeoConsensusTest(unittest.TestCase):
    def test_two_providers_agreeing_raise_confidence(self):
        results = [
            {
                "provider": "ipapi.co",
                "country": "United States",
                "country_code": "US",
                "city": "Ashburn",
                "asn": "AS14618 Amazon",
            },
            {
                "provider": "IP2Location.io",
                "country": "United States of America",
                "country_code": "US",
                "city": "Ashburn",
                "asn": "14618 Amazon",
            },
            {
                "provider": "ipinfo.io",
                "country": "Canada",
                "city": "Toronto",
                "asn": "AS123 Example",
            },
        ]

        consensus, confidence = DomainAnalyzer._geo_consensus(results)

        self.assertEqual(consensus["country"], "United States")
        self.assertEqual(consensus["country_agreement"], "2/3")
        self.assertEqual(consensus["city"], "Ashburn")
        self.assertEqual(consensus["asn"], "AS14618 Amazon")
        self.assertEqual(consensus["providers"], 3)
        self.assertEqual(confidence, "high")

    def test_single_provider_has_low_confidence(self):
        consensus, confidence = DomainAnalyzer._geo_consensus(
            [{"country": "Germany", "city": "Berlin"}]
        )
        self.assertEqual(confidence, "low")
        self.assertNotIn("country", consensus)


if __name__ == "__main__":
    unittest.main()
