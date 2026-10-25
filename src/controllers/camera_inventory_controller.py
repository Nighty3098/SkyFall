import asyncio
import json

from src.modules.camera_inventory import (
    Camera,
    CameraDataError,
    fetch_cameras,
    filter_cameras,
)
from src.ui.theme import dialog_palette

CAMERA_MAP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map {{
    margin: 0; padding: 0; width: 100%; height: 100%; background: {bg};
  }}
</style>
</head>
<body>
<div id="map"></div>
<script>
var cameras = {cameras};
var map = L.map('map', {{ zoomControl: true }}).setView([20, 0], 2);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap'
}}).addTo(map);
function popupFor(camera) {{
  var content = document.createElement('div');
  function add(label, value, bold) {{
    if (!value) return;
    var row = document.createElement('div');
    if (bold) {{
      var title = document.createElement('strong');
      title.textContent = value;
      row.appendChild(title);
    }} else {{
      row.textContent = label + ': ' + value;
    }}
    content.appendChild(row);
  }}
  add('', [camera.city, camera.country].filter(Boolean).join(', '), true);
  add('Stream', camera.stream);
  add('Region', camera.region);
  add('Timezone', camera.timezone);
  add('Categories', camera.categories.join(', '));
  add('Coordinates', camera.latitude.toFixed(5) + ', ' + camera.longitude.toFixed(5));
  add('Iframe', camera.is_iframe === null ? '' : (camera.is_iframe ? 'Yes' : 'No'));
  add('Static', camera.is_static === null ? '' : (camera.is_static ? 'Yes' : 'No'));
  add('Popular', camera.is_popular === null ? '' : (camera.is_popular ? 'Yes' : 'No'));
  return content;
}}
cameras.forEach(function (camera) {{
  L.marker([camera.latitude, camera.longitude])
    .addTo(map)
    .bindPopup(popupFor(camera));
}});
if (cameras.length === 1) {{
  map.setView([cameras[0].latitude, cameras[0].longitude], 12);
}} else if (cameras.length > 1) {{
  map.fitBounds(cameras.map(function (camera) {{
    return [camera.latitude, camera.longitude];
  }}), {{ padding: [20, 20] }});
}}
</script>
</body>
</html>"""


class CameraInventoryController:
    def __init__(self, ui):
        self.ui = ui
        self.cameras: list[Camera] = []
        self.ui.cameraInfoText.setReadOnly(True)
        self.ui.cameraStatusLabel.setText(
            "Loading camera metadata ..."
        )
        self._render()

    async def load_from_url(self):
        self.ui.cameraLoadButton.setEnabled(False)
        self.ui.cameraStatusLabel.setText("Loading camera metadata...")
        try:
            cameras = await asyncio.to_thread(fetch_cameras)
        except CameraDataError as exc:
            self.ui.cameraStatusLabel.setText(str(exc))
        else:
            self.cameras = cameras
            self.ui.cameraStatusLabel.setText(
                f"Loaded {len(cameras)} camera record(s)."
            )
            self._render(self.ui.cameraFilterEdit.text())
        finally:
            self.ui.cameraLoadButton.setEnabled(True)

    def filter_changed(self, query: str):
        self._render(query)

    def _render(self, query: str = ""):
        cameras = filter_cameras(self.cameras, query)
        located = [
            camera
            for camera in cameras
            if camera.latitude is not None and camera.longitude is not None
        ]
        self.ui.cameraInfoText.setPlainText(self._report(cameras, located))

        palette = dialog_palette()
        page = CAMERA_MAP_HTML.format(
            cameras=self._script_json(
                [
                    {
                        "stream": camera.stream,
                        "city": camera.city,
                        "country": camera.country,
                        "region": camera.region,
                        "timezone": camera.timezone,
                        "categories": camera.categories,
                        "latitude": camera.latitude,
                        "longitude": camera.longitude,
                        "is_iframe": camera.is_iframe,
                        "is_static": camera.is_static,
                        "is_popular": camera.is_popular,
                    }
                    for camera in located
                ]
            ),
            bg=palette["bg"],
        )
        self.ui.cameraMapView.setHtml(page)

    @staticmethod
    def _script_json(value) -> str:
        return (
            json.dumps(value, ensure_ascii=True)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )

    @staticmethod
    def _report(cameras: list[Camera], located: list[Camera]) -> str:
        if not cameras:
            return "No cameras match this filter."

        lines = [f"Showing {len(cameras)} camera record(s); {len(located)} mapped.", ""]
        for index, camera in enumerate(cameras, start=1):
            place = ", ".join(value for value in (camera.city, camera.country) if value)
            lines.append(f"{index}. {place or 'Unnamed camera'}")
            lines.append(f"   Stream: {camera.stream}")
            if camera.region:
                lines.append(f"   Region: {camera.region}")
            if camera.latitude is not None and camera.longitude is not None:
                lines.append(
                    f"   Coordinates: {camera.latitude:.5f}, {camera.longitude:.5f}"
                )
            else:
                lines.append("   Coordinates: not set")
            if camera.timezone:
                lines.append(f"   Timezone: {camera.timezone}")
            if camera.categories:
                lines.append(f"   Categories: {', '.join(camera.categories)}")
            lines.append("")
        return "\n".join(lines).rstrip()
