"""Unit tests for :mod:`src.controllers.wifi_map_controller` formatting."""

import unittest

from src.controllers.wifi_map_controller import WifiMapController


def hotspot(ssid, security="WPA/WPA2", password=None, has_password=True, city="Berlin"):
    return {
        "ssid": ssid,
        "security": security,
        "security_type": 2,
        "password": password,
        "has_password": has_password,
        "public_web": password is not None,
        "user_name": "anonymous",
        "city": city,
        "country": "Germany",
        "lat": 52.5,
        "lng": 13.4,
        "p_internet": 1,
        "last_seen": "2026-01-02T10:00:00+00:00",
        "created_at": "2020-01-01T00:00:00+00:00",
        "id": 1,
    }


def sample(extra=None):
    hotspots = [
        hotspot("Illnet", password="ostern0815"),
        hotspot("Parter@", city="Potsdam"),
        hotspot("REWE", security="Open", has_password=False, password=None),
    ]
    if extra:
        hotspots.extend(extra)
    return {
        "query": "Berlin",
        "location": "Berlin, Deutschland",
        "lat": 52.5,
        "lng": 13.4,
        "bbox": (52.3382, 52.6755, 13.0883, 13.7612),
        "total": len(hotspots),
        "public_web": 1,
        "passwords": sum(1 for h in hotspots if h["password"]),
        "hotspots": hotspots,
    }


def controller():
    return WifiMapController(ui=object(), wifi=object())


class ClipTest(unittest.TestCase):
    def test_short_kept(self):
        self.assertEqual(WifiMapController._clip("abc", 5), "abc")

    def test_long_truncated_with_ellipsis(self):
        self.assertEqual(WifiMapController._clip("abcdefgh", 4), "abc…")


class ReportTest(unittest.TestCase):
    def test_summary_lines(self):
        text = controller()._report(sample())
        self.assertIn("Berlin — Public Wi-Fi hotspots", text)
        self.assertIn("Location   Berlin, Deutschland", text)
        self.assertIn("Total      3", text)
        self.assertIn("open 1  ·  secured 2", text)

    def test_published_and_other_sections(self):
        text = controller()._report(sample())
        self.assertIn("Shared passwords (1)", text)
        self.assertIn("ostern0815", text)
        self.assertIn("Other hotspots (2)", text)
        self.assertIn("SECURITY", text)

    def test_open_access_column(self):
        text = controller()._report(sample())
        self.assertIn("open", text)
        self.assertIn("locked", text)

    def test_listings_are_not_capped(self):
        extra = [hotspot(f"AP-{i}", password="pw") for i in range(200)]
        text = controller()._report(sample(extra))
        self.assertIn("Shared passwords (201)", text)
        self.assertIn("AP-199", text)

    def test_report_columns_align(self):
        text = controller()._report(sample())
        header = [ln for ln in text.splitlines() if ln.startswith("SSID")][0]
        self.assertIn("PASSWORD", header)


class PopupTest(unittest.TestCase):
    def test_popup_shows_password(self):
        popup = controller()._popup(hotspot("Illnet", password="ostern0815"))
        self.assertIn("ostern0815", popup)

    def test_popup_not_published(self):
        popup = controller()._popup(hotspot("Parter@"))
        self.assertIn("not published", popup)

    def test_popup_open_network(self):
        popup = controller()._popup(
            hotspot("REWE", security="Open", has_password=False)
        )
        self.assertIn("open network", popup)


if __name__ == "__main__":
    unittest.main()
