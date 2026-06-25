import asyncio
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.mac_location import MacLocation


LEAFLET_HTML = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin: 0; padding: 0; background: #0A0A0A; }}
  #mapWrap {{ border-radius: 15px; overflow: hidden; width: 100%; height: 100vh; }}
  #map {{ width: 100%; height: 100%; }}
</style>
</head>
<body>
<div id="mapWrap"><div id="map"></div></div>
<script>
var map = L.map('map', {{ zoomControl: false }}).setView([{lat}, {lng}], 5);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 18,
  attribution: '&copy; OpenStreetMap'
}}).addTo(map);
{markers}
</script>
</body>
</html>"""


MARKER_JS = (
    """L.marker([{lat}, {lng}]).addTo(map)"""
    """.bindPopup('<b>{provider}</b><br>{lat}, {lng}');"""
)


class MacLocationController:
    def __init__(
        self,
        ui: "QMainWindow",
        mac_location: "MacLocation",
    ):
        logger.debug("Init: MacLocationController")

        self.ui = ui
        self.mac_location = mac_location

    async def start_searching(self):
        result = await asyncio.to_thread(
            self.mac_location.locate, self.ui.macAddrEdit.text()
        )
        lines = [f"MAC: {result['mac']}"]
        markers = []
        first = None
        for provider, loc in result["location"].items():
            if loc is None:
                lines.append(f"  {provider}: no data")
            else:
                lat, lng = loc["latitude"], loc["longitude"]
                lines.append(f"  {provider}: {lat}, {lng}")
                markers.append(MARKER_JS.format(provider=provider, lat=lat, lng=lng))
                if first is None:
                    first = (lat, lng)
        self.ui.macAddrLocationDebug.setPlainText("\n".join(lines))

        if first:
            html = LEAFLET_HTML.format(
                lat=first[0], lng=first[1], markers="\n".join(markers)
            )
            self.ui.macLocationMapView.setHtml(html)
