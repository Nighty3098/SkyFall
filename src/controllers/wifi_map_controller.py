import html
import json
from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.wifi_map import WifiMap


LEAFLET_HTML = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin: 0; padding: 0; background: {bg}; }}
  #mapWrap {{ border-radius: {radius}; overflow: hidden; width: 100%; height: 100vh; }}
  #map {{ width: 100%; height: 100%; }}
</style>
</head>
<body>
<div id="mapWrap"><div id="map"></div></div>
<script>
var map = L.map('map', {{ zoomControl: true }}).setView([{lat}, {lng}], 12);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap'
}}).addTo(map);
var hotspots = {hotspots};
hotspots.forEach(function (h) {{
  L.marker([h.lat, h.lng]).addTo(map).bindPopup(h.popup);
}});
var bounds = {bounds};
if (bounds.length >= 2) {{ map.fitBounds(bounds, {{ padding: [20, 20] }}); }}
</script>
</body>
</html>"""


class WifiMapController:
    def __init__(self, ui: "QMainWindow", wifi: "WifiMap"):
        logger.debug("Init: WifiMapController")
        self.ui = ui
        self.wifi = wifi

    # ── Formatting helpers ────────────────────────────────────────

    @staticmethod
    def _clip(text, width: int) -> str:
        text = str(text)
        if len(text) <= width:
            return text
        return text[: width - 1] + "…"

    @classmethod
    def _table(cls, headers, rows, widths) -> list[str]:
        def fmt(cells):
            return "  ".join(
                cls._clip(cell, w).ljust(w) for cell, w in zip(cells, widths)
            )

        lines = [fmt(headers), "  ".join("─" * w for w in widths)]
        lines.extend(fmt(row) for row in rows)
        return lines

    @staticmethod
    def _password_label(hotspot: dict) -> str:
        if hotspot.get("password"):
            return hotspot["password"]
        if hotspot.get("has_password"):
            return "not published"
        return "open (no password)"

    # ── Map popups ────────────────────────────────────────────────

    def _popup(self, hotspot: dict) -> str:
        ssid = html.escape(hotspot.get("ssid") or "(hidden)")
        security = html.escape(hotspot.get("security") or "unknown")
        rows = [f"<b>{ssid}</b>", f"Security: {security}"]

        password = hotspot.get("password")
        if password:
            rows.append(f"Password: <b>{html.escape(password)}</b>")
        elif hotspot.get("has_password"):
            rows.append("Password: not published")
        else:
            rows.append("Password: open network")

        place = ", ".join(p for p in (hotspot.get("city"), hotspot.get("country")) if p)
        if place:
            rows.append(html.escape(place))
        if hotspot.get("user_name"):
            rows.append(f"Added by: {html.escape(hotspot['user_name'])}")
        if hotspot.get("last_seen"):
            rows.append(f"Last seen: {html.escape(str(hotspot['last_seen']))}")
        rows.append(f"{hotspot['lat']:.5f}, {hotspot['lng']:.5f}")
        return "<br>".join(rows)

    # ── Report ────────────────────────────────────────────────────

    @staticmethod
    def _seen(hotspot: dict) -> str:
        return str(hotspot.get("last_seen") or "")[:10] or "—"

    @staticmethod
    def _sort_key(hotspot: dict):
        return (hotspot.get("city") or "", hotspot.get("ssid") or "")

    def _report(self, data: dict) -> str:
        hotspots = data.get("hotspots", [])
        south, north, west, east = data["bbox"]
        open_count = sum(1 for h in hotspots if not h.get("has_password"))
        secured = len(hotspots) - open_count
        published = [h for h in hotspots if h.get("password")]
        others = [h for h in hotspots if not h.get("password")]

        published.sort(key=self._sort_key)
        others.sort(key=self._sort_key)

        public_web = data.get("public_web", 0)
        out = [
            f"{data.get('query')} — Public Wi-Fi hotspots",
            "─" * 60,
            f"  Location   {data.get('location')}",
            f"  Bounds     lat {south:.4f}..{north:.4f}  ·  lng {west:.4f}..{east:.4f}",
            f"  Total      {len(hotspots)}   open {open_count}  ·  secured {secured}",
            f"  Passwords  {len(published)} of {public_web} public hotspots",
            "",
        ]

        if published:
            out.append(f"Shared passwords ({len(published)})")
            rows = [
                (
                    h.get("ssid") or "(hidden)",
                    h.get("security") or "unknown",
                    h.get("password") or "",
                    self._seen(h),
                    ", ".join(p for p in (h.get("city"), h.get("country")) if p),
                )
                for h in published
            ]
            out += self._table(
                ["SSID", "SECURITY", "PASSWORD", "LAST SEEN", "LOCATION"],
                rows,
                [28, 10, 20, 10, 24],
            )
            out.append("")

        out.append(f"Other hotspots ({len(others)})")
        rows = [
            (
                h.get("ssid") or "(hidden)",
                h.get("security") or "unknown",
                "open" if not h.get("has_password") else "locked",
                self._seen(h),
                ", ".join(p for p in (h.get("city"), h.get("country")) if p),
            )
            for h in others
        ]
        out += self._table(
            ["SSID", "SECURITY", "ACCESS", "LAST SEEN", "LOCATION"],
            rows,
            [28, 10, 8, 10, 24],
        )
        return "\n".join(out)

    # ── Entry point ───────────────────────────────────────────────

    async def search(self) -> None:
        widget = getattr(self.ui, "wifiDebug", None)
        map_view = getattr(self.ui, "wifiMapView", None)
        if widget is None:
            return

        query = self.ui.wifiCityEdit.text().strip()
        if not query:
            widget.setPlainText("Enter a city name or 'lat, lng'")
            return

        widget.setPlainText(f"Searching public Wi-Fi hotspots in {query}...")
        data = await self.wifi.search_async(query)

        if data.get("error"):
            widget.setPlainText(render(data, "Public Wi-Fi hotspots"))
            return

        widget.setPlainText(self._report(data))

        if map_view is None:
            return

        markers = [
            {
                "lat": h["lat"],
                "lng": h["lng"],
                "popup": self._popup(h),
            }
            for h in data.get("hotspots", [])
        ]
        south, north, west, east = data["bbox"]
        bounds = [[south, west], [north, east]]

        from src.ui.theme import dialog_palette

        pal = dialog_palette()
        page = LEAFLET_HTML.format(
            lat=data.get("lat", (south + north) / 2),
            lng=data.get("lng", (west + east) / 2),
            hotspots=json.dumps(markers),
            bounds=json.dumps(bounds),
            bg=pal["bg"],
            radius=pal["radius"],
        )
        map_view.setHtml(page)
        map_view.show()
