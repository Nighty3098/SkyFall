from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import (
    info,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.file_analyzer import FileAnalyzer


LEAFLET_HTML = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin: 0; padding: 0; background: #0A0A0A; }}
  #mapWrap {{ border-radius: 10px; overflow: hidden; width: 100%; height: 100vh; }}
  #map {{ width: 100%; height: 100%; }}
</style>
</head>
<body>
<div id="mapWrap"><div id="map"></div></div>
<script>
var map = L.map('map', {{ zoomControl: false }}).setView([{lat}, {lng}], 15);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 18,
  attribution: '&copy; OpenStreetMap'
}}).addTo(map);
L.circleMarker([{lat}, {lng}], {{
  radius: 8,
  fillColor: '#ff4444',
  color: '#ffffff',
  weight: 2,
  fillOpacity: 0.9,
}}).addTo(map).bindPopup('<b>File GPS</b><br>{lat}, {lng}');
</script>
</body>
</html>"""


class FileAnalyzeController:
    def __init__(
        self,
        ui: "QMainWindow",
        file_analyzer: "FileAnalyzer",
    ):
        logger.debug("Init: FileAnalyzeController")

        self.ui = ui
        self.file_analyzer = file_analyzer

    async def start_file_analyzer(self, path):
        if self.ui.fileMetadataCheck.isChecked():
            self.ui.metadataDebug.setPlainText(info("Loading..."))
            result = await self.file_analyzer.get_metadata(path)
            result += "\n\n"
            result += await self.file_analyzer.check_tail_data(path)
            self.ui.metadataDebug.setPlainText(result)

            gps = await self.file_analyzer.get_gps_coordinates(path)
            if gps:
                lat, lng = gps
                html = LEAFLET_HTML.format(lat=lat, lng=lng)
                self.ui.metadataMapView.setHtml(html)
                self.ui.metadataMapView.show()
            else:
                self.ui.metadataMapView.hide()

        if self.ui.fileStringsCheck.isChecked():
            self.ui.stringsFileDebug.setPlainText(info("Loading..."))
            strings_result = await self.file_analyzer.get_strings(path)
            self.ui.stringsFileDebug.setPlainText("\n".join(strings_result))

        if self.ui.fileVirustotalCheck.isChecked():
            self.ui.virustotalFileDebug.setPlainText(info("Loading..."))
            virustotal_result = await self.file_analyzer.virustotal_analyze(path)
            self.ui.virustotalFileDebug.setPlainText(virustotal_result)

    def get_file_type(self, path):
        return self.file_analyzer.get_file_type(path)
