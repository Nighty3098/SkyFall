"""Unit tests for :mod:`src.modules.wifi_map`.

The network is never touched: ``requests.get`` is patched with a small fake
that returns canned Nominatim / PostgREST payloads.
"""

import unittest
from unittest import mock

from src.modules.wifi_map import HOTSPOT_COLUMNS, WifiMap


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def make_map():
    return WifiMap(api_key="test-key")


class ParseCoordsTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(make_map().parse_coords("37.5, -122.25"), (37.5, -122.25))

    def test_no_comma(self):
        self.assertIsNone(make_map().parse_coords("Amsterdam"))

    def test_not_numbers(self):
        self.assertIsNone(make_map().parse_coords("north, west"))

    def test_out_of_range(self):
        self.assertIsNone(make_map().parse_coords("200, 10"))


class BuildParamsTest(unittest.TestCase):
    def test_bounds_and_limit(self):
        params = make_map().build_params((37.0, 38.0, -123.0, -122.0), limit=100)
        self.assertIn(("lat", "gte.37.0"), params)
        self.assertIn(("lat", "lte.38.0"), params)
        self.assertIn(("lng", "gte.-123.0"), params)
        self.assertIn(("lng", "lte.-122.0"), params)
        self.assertIn(("limit", "100"), params)
        self.assertEqual(params[0], ("select", HOTSPOT_COLUMNS))


class GeocodeTest(unittest.TestCase):
    def test_coordinates_skip_nominatim(self):
        with mock.patch("src.modules.wifi_map.requests.get") as get:
            result = make_map().geocode("37.5, -122.25")
        get.assert_not_called()
        self.assertEqual(result["lat"], 37.5)
        self.assertEqual(result["lng"], -122.25)
        south, north, west, east = result["bbox"]
        self.assertLess(south, north)
        self.assertLess(west, east)

    def test_nominatim_parses_bbox(self):
        payload = [
            {
                "display_name": "Amsterdam, Netherlands",
                "lat": "52.37",
                "lon": "4.89",
                "boundingbox": ["52.27", "52.47", "4.72", "5.07"],
            }
        ]
        with mock.patch(
            "src.modules.wifi_map.requests.get", return_value=FakeResponse(payload)
        ):
            result = make_map().geocode("Amsterdam")
        self.assertEqual(result["display_name"], "Amsterdam, Netherlands")
        self.assertEqual(result["bbox"], (52.27, 52.47, 4.72, 5.07))

    def test_nominatim_no_result(self):
        with mock.patch(
            "src.modules.wifi_map.requests.get", return_value=FakeResponse([])
        ):
            self.assertIsNone(make_map().geocode("Nowhereville"))


class SecurityNameTest(unittest.TestCase):
    def test_known_codes(self):
        self.assertEqual(WifiMap.security_name(2), "WPA/WPA2")
        self.assertEqual(WifiMap.security_name(4), "Open")

    def test_unknown_code(self):
        self.assertEqual(WifiMap.security_name(99), "Type 99")
        self.assertEqual(WifiMap.security_name(None), "Unknown")


class GetPasswordTest(unittest.TestCase):
    def test_returns_password(self):
        with mock.patch(
            "src.modules.wifi_map.requests.post",
            return_value=FakeResponse("hunter2"),
        ) as post:
            password = make_map().get_password(42)
        self.assertEqual(password, "hunter2")
        _, kwargs = post.call_args
        self.assertEqual(kwargs["json"], {"p_id": 42})

    def test_null_becomes_none(self):
        with mock.patch(
            "src.modules.wifi_map.requests.post", return_value=FakeResponse(None)
        ):
            self.assertIsNone(make_map().get_password(1))


class SearchTest(unittest.TestCase):
    def _hotspot(self, hsid="1", ssid="CafeWifi", lat=52.3, lng=4.8, public_web=False):
        return {
            "id": hsid,
            "ssid": ssid,
            "security_type": 2,
            "has_password": True,
            "is_public": True,
            "public_web": public_web,
            "user_name": "bob",
            "country": "NL",
            "city": "Amsterdam",
            "lat": lat,
            "lng": lng,
            "p_internet": 1,
            "last_seen": "2026-01-01T00:00:00Z",
            "created_at": "2025-01-01T00:00:00Z",
        }

    def test_search_returns_normalized_hotspots(self):
        nominatim = [
            {
                "display_name": "Amsterdam, Netherlands",
                "lat": "52.37",
                "lon": "4.89",
                "boundingbox": ["52.27", "52.47", "4.72", "5.07"],
            }
        ]
        rows = [self._hotspot("a"), self._hotspot("b", ssid="Open", lat=52.4)]
        responses = [FakeResponse(nominatim), FakeResponse(rows)]

        with mock.patch(
            "src.modules.wifi_map.requests.get", side_effect=responses
        ) as get:
            result = make_map().search("Amsterdam", limit=50)

        self.assertNotIn("error", result)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["hotspots"][0]["ssid"], "CafeWifi")
        self.assertEqual(result["hotspots"][0]["security"], "WPA/WPA2")
        self.assertTrue(result["hotspots"][0]["has_password"])
        # Second call must carry the bounding box filters and limit.
        _, kwargs = get.call_args_list[1]
        self.assertIn(("lat", "gte.52.27"), kwargs["params"])
        self.assertIn(("limit", "50"), kwargs["params"])

    def test_search_attaches_passwords_for_public_web(self):
        nominatim = [
            {
                "display_name": "Amsterdam, Netherlands",
                "lat": "52.37",
                "lon": "4.89",
                "boundingbox": ["52.27", "52.47", "4.72", "5.07"],
            }
        ]
        rows = [
            self._hotspot("a", public_web=True),
            self._hotspot("b", ssid="Hidden", public_web=False),
        ]
        responses = [FakeResponse(nominatim), FakeResponse(rows)]

        with (
            mock.patch("src.modules.wifi_map.requests.get", side_effect=responses),
            mock.patch(
                "src.modules.wifi_map.requests.post",
                return_value=FakeResponse("s3cr3t"),
            ) as post,
        ):
            result = make_map().search("Amsterdam", limit=50)

        self.assertEqual(result["passwords"], 1)
        self.assertEqual(result["hotspots"][0]["password"], "s3cr3t")
        self.assertIsNone(result["hotspots"][1]["password"])
        # Only the public_web hotspot triggers an RPC call.
        self.assertEqual(post.call_count, 1)
        _, kwargs = post.call_args
        self.assertEqual(kwargs["json"], {"p_id": "a"})

    def test_search_skips_rows_without_coordinates(self):
        nominatim = [
            {
                "display_name": "X",
                "lat": "1",
                "lon": "1",
                "boundingbox": ["0", "2", "0", "2"],
            }
        ]
        rows = [self._hotspot("a"), {"id": "b", "lat": None, "lng": None}]
        responses = [FakeResponse(nominatim), FakeResponse(rows)]

        with mock.patch("src.modules.wifi_map.requests.get", side_effect=responses):
            result = make_map().search("X")

        self.assertEqual(result["total"], 1)

    def test_search_pages_past_server_cap(self):
        nominatim = [
            {
                "display_name": "X",
                "lat": "1",
                "lon": "1",
                "boundingbox": ["0", "2", "0", "2"],
            }
        ]
        page1 = [self._hotspot(str(i), lat=52.0 + i / 1000) for i in range(5)]
        page2 = [self._hotspot(str(100 + i), lat=52.5 + i / 1000) for i in range(2)]
        responses = [FakeResponse(nominatim), FakeResponse(page1), FakeResponse(page2)]

        with (
            mock.patch("src.modules.wifi_map.PAGE_SIZE", 5),
            mock.patch(
                "src.modules.wifi_map.requests.get", side_effect=responses
            ) as get,
        ):
            result = make_map().search("X", with_passwords=False)

        self.assertEqual(result["total"], 7)
        # geocode + two pages of hotspots
        self.assertEqual(get.call_count, 3)
        first_page = get.call_args_list[1].kwargs["params"]
        second_page = get.call_args_list[2].kwargs["params"]
        self.assertIn(("offset", "0"), first_page)
        self.assertIn(("offset", "5"), second_page)
        self.assertIn(("order", "id.asc"), first_page)

    def test_search_reports_unknown_location(self):
        with mock.patch(
            "src.modules.wifi_map.requests.get", return_value=FakeResponse([])
        ):
            result = make_map().search("Nowhereville")
        self.assertIn("error", result)

    def test_search_empty_query(self):
        self.assertIn("error", make_map().search("   "))


if __name__ == "__main__":
    unittest.main()
