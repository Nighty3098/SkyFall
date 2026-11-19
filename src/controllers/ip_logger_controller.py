import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.ui.output_formatter import bullet, error, info, line, render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.ip_logger import IpLogger


MAP_STYLES = (
    (
        "OpenStreetMap",
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "&copy; OpenStreetMap contributors",
    ),
    (
        "CARTO Dark",
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        "&copy; OpenStreetMap contributors &copy; CARTO",
    ),
    (
        "CARTO Light",
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "&copy; OpenStreetMap contributors &copy; CARTO",
    ),
    (
        "OpenTopoMap",
        "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "&copy; OpenStreetMap contributors &copy; OpenTopoMap",
    ),
    (
        "Esri Satellite",
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "Tiles &copy; Esri",
    ),
)

IP_LOGGER_MAP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map {{
    margin: 0; padding: 0; width: 100%; height: 100%; background: {bg}; color: {fg};
  }}
</style>
</head>
<body>
<div id="map"></div>
<script>
var map = L.map('map', {{ zoomControl: true }}).setView([20, 0], 2);
L.tileLayer({tiles}, {{
  maxZoom: 19,
  attribution: {attribution}
}}).addTo(map);
var hits = {markers};
hits.forEach(function (hit) {{
  var popup = document.createElement('div');
  var label = document.createElement('strong');
  label.textContent = hit.label;
  popup.appendChild(label);
  ['time', 'agent'].forEach(function (key) {{
    if (!hit[key]) return;
    var row = document.createElement('div');
    row.textContent = hit[key];
    popup.appendChild(row);
  }});
  L.marker([hit.lat, hit.lng]).addTo(map).bindPopup(popup);
}});
if (hits.length === 1) {{
  map.setView([hits[0].lat, hits[0].lng], 10);
}} else if (hits.length > 1) {{
  map.fitBounds(hits.map(function (hit) {{ return [hit.lat, hit.lng]; }}),
                {{ padding: [20, 20] }});
}}
</script>
</body>
</html>"""


class IpLoggerController:
    def __init__(self, ui: "QMainWindow", ip_logger: "IpLogger"):
        logger.debug("Init: IpLoggerController")
        self.ui = ui
        self.ip_logger = ip_logger
        self.hits: list[dict[str, Any]] = []
        self._style_index = 0

        selector = getattr(self.ui, "ipLoggerStyleSelector", None)
        if selector is not None:
            selector.addItems([style[0] for style in MAP_STYLES])
            self._style_index = max(0, selector.currentIndex())

        self.ip_logger.on_hit(self._on_hit)
        self.hits = list(self.ip_logger.hits)
        self._render()

    async def toggle_server(self) -> None:
        if self.ip_logger.is_running:
            await self.stop_server()
        else:
            await self.start_server()

    async def start_server(self) -> None:
        port_edit = getattr(self.ui, "ipLoggerPortEdit", None)
        if port_edit is None:
            return
        debug = getattr(self.ui, "ipLoggerDebug", None)

        port_text = port_edit.text().strip()
        if not port_text:
            if debug is not None:
                debug.setPlainText("IP Logger\n  ! Enter a port to start the server")
            return

        try:
            result = await self.ip_logger.start_server(port_text)
        except (ValueError, OSError, RuntimeError) as exc:
            if debug is not None:
                debug.setPlainText(f"IP Logger\n  ! {exc}")
            return

        self.hits = []
        self._set_button_text("STOP SERVER")
        if debug is not None:
            debug.setPlainText(
                render(
                    {
                        "status": "listening",
                        "port": result.get("port", port_text),
                        "links": result.get("urls", []),
                        "note": (
                            "Every request to a link is logged below "
                            "and plotted on the map."
                        ),
                    },
                    title="IP Logger",
                )
            )
        self._render_map()

    async def stop_server(self) -> None:
        await self.ip_logger.stop()
        self.hits = list(self.ip_logger.hits)
        self._set_button_text("START SERVER")
        self._render()

    def style_changed(self, index: int) -> None:
        if not isinstance(index, int) or not 0 <= index < len(MAP_STYLES):
            return
        self._style_index = index
        self._render_map()

    def _on_hit(self, _hit: dict[str, Any]) -> None:
        self.hits = list(self.ip_logger.hits)
        self._render()

    def _set_button_text(self, text: str) -> None:
        button = getattr(self.ui, "ipLoggerStartButton", None)
        if button is not None:
            button.setText(text)

    def _render(self) -> None:
        debug = getattr(self.ui, "ipLoggerDebug", None)
        if debug is not None:
            debug.setPlainText(self._report())
        self._render_map()

    def _report(self) -> str:
        total = len(self.hits)
        state = (
            f"listening on {self.ip_logger.port}"
            if self.ip_logger.is_running
            else "stopped"
        )
        noun = "hit" if total == 1 else "hits"
        lines = [f"IP Logger — {state} — {total} {noun}"]
        if not total:
            lines.append(
                info(
                    "Waiting for incoming requests..."
                    if self.ip_logger.is_running
                    else "Start the server to capture visitor IPs."
                )
            )
            return "\n".join(lines)

        for index, hit in enumerate(self.hits, 1):
            place = hit.get("location") or "unknown location"
            lines.append(
                bullet(f"#{index} {hit.get('time', '')}  {hit.get('ip', '')}  {place}")
            )
            method = hit.get("method") or "GET"
            lines.append(line(f"{method} {hit.get('path') or '/'}"))
            if hit.get("user_agent"):
                lines.append(line(f"user-agent: {hit['user_agent']}"))
            if hit.get("referer"):
                lines.append(line(f"referer: {hit['referer']}"))
            if hit.get("language"):
                lines.append(line(f"language: {hit['language']}"))
            if hit.get("geo_status") and hit["geo_status"] != "CLEAN":
                lines.append(line(f"geo: {hit['geo_status']}"))
            if hit.get("geo_note"):
                lines.append(error(hit["geo_note"]))
        return "\n".join(lines)

    def _render_map(self) -> None:
        map_view = getattr(self.ui, "ipLoggerMap", None)
        if map_view is None:
            return

        _, tiles, attribution = MAP_STYLES[self._style_index]
        markers = []
        for hit in self.hits:
            if hit.get("lat") is None or hit.get("lng") is None:
                continue
            markers.append(
                {
                    "lat": hit["lat"],
                    "lng": hit["lng"],
                    "label": (
                        f"{hit.get('ip', '')} — "
                        f"{hit.get('location') or 'unknown location'}"
                    ),
                    "time": hit.get("time", ""),
                    "agent": hit.get("user_agent", ""),
                }
            )

        from src.ui.theme import dialog_palette

        pal = dialog_palette()
        page = IP_LOGGER_MAP_HTML.format(
            bg=pal["bg"],
            fg=pal["text"],
            tiles=self._script_json(tiles),
            attribution=self._script_json(attribution),
            markers=self._script_json(markers),
        )
        map_view.setHtml(page)

    @staticmethod
    def _script_json(value: Any) -> str:
        return (
            json.dumps(value, ensure_ascii=True)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )
