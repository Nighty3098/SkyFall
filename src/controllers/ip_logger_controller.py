import asyncio
import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.ui.output_formatter import bullet, error, info, line

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.ip_logger import IpLogger


MAP_TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
MAP_ATTRIBUTION = "&copy; OpenStreetMap contributors"

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
        self._start_note = ""
        self._public_ip_task: asyncio.Task | None = None

        self._populate_sites()
        self.ip_logger.on_hit(self._on_hit)
        self.ip_logger.on_state(self._on_state)
        self.hits = list(self.ip_logger.hits)
        self._render()

    def _site_selector(self):
        selector = getattr(self.ui, "ipLoggerSiteSelector", None)
        if selector is None:
            selector = getattr(self.ui, "ipLoggerStyleSelector", None)
        return selector

    def _populate_sites(self) -> None:
        selector = self._site_selector()
        if selector is None:
            return
        templates = self.ip_logger.refresh_templates()
        selector.clear()
        if not templates:
            selector.addItem("NO HTML TEMPLATES FOUND")
            selector.setEnabled(False)
            return
        selector.setEnabled(True)
        selector.addItems([template.label for template in templates])
        current = self.ip_logger.current_template
        if current is not None:
            index = next(
                (
                    i
                    for i, template in enumerate(templates)
                    if template.path == current.path
                ),
                0,
            )
            self.ip_logger.select_template(index)
            selector.setCurrentIndex(index)

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

        self._populate_sites()
        try:
            result = await self.ip_logger.start_server(port_text)
        except (ValueError, OSError, RuntimeError) as exc:
            if debug is not None:
                debug.setPlainText(f"IP Logger\n  ! {exc}")
            return

        self.hits = []
        self._set_button_text("STOP SERVER")
        notes = [
            "Every request to a link is logged below and plotted on the map.",
            f"Site: {result.get('template') or 'built-in fallback'}",
        ]
        if result.get("elevated"):
            notes.append(
                "Low port: approved through the system admin prompt "
                "(native elevation helper)."
            )
        self._start_note = " ".join(notes)
        self._render()
        self._start_public_ip_lookup()

    def _start_public_ip_lookup(self) -> None:
        task = self._public_ip_task
        if task is not None and not task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._public_ip_task = loop.create_task(self.ip_logger.resolve_public_ip())

    async def stop_server(self) -> None:
        task, self._public_ip_task = self._public_ip_task, None
        if task is not None and not task.done():
            task.cancel()
        await self.ip_logger.stop()
        self._start_note = ""
        self.hits = list(self.ip_logger.hits)
        self._set_button_text("START SERVER")
        self._render()

    def site_changed(self, index: int) -> None:
        if not self.ip_logger.select_template(index):
            return
        if self.ip_logger.is_running:
            self._render()

    def _on_hit(self, _hit: dict[str, Any]) -> None:
        self.hits = list(self.ip_logger.hits)
        self._render()

    def _on_state(self) -> None:
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
        running = self.ip_logger.is_running
        state = f"listening on {self.ip_logger.port}" if running else "stopped"
        template = self.ip_logger.current_template
        site = f" — site: {template.label}" if template else ""
        noun = "hit" if total == 1 else "hits"
        lines = [f"IP Logger — {state}{site} — {total} {noun}"]
        if running:
            for url in self.ip_logger.urls():
                lines.append(line(f"link: {url}"))
            if self._start_note:
                lines.append(info(self._start_note))
        if not total:
            lines.append(
                info(
                    "Waiting for incoming requests..."
                    if running
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

            if hit.get("page_title"):
                lines.append(line(f"title: {hit['page_title']}"))
            if hit.get("page_url"):
                lines.append(line(f"page: {hit['page_url']}"))
            if hit.get("user_agent"):
                lines.append(line(f"user-agent: {hit['user_agent']}"))
            if hit.get("referer"):
                lines.append(line(f"referer: {hit['referer']}"))
            if hit.get("page_referrer"):
                lines.append(line(f"page-referer: {hit['page_referrer']}"))
            if hit.get("language"):
                lines.append(line(f"language: {hit['language']}"))
            if hit.get("browser_language"):
                lines.append(line(f"browser-language: {hit['browser_language']}"))
            if hit.get("screen") or hit.get("timezone"):
                lines.append(
                    line(
                        f"browser: {hit.get('screen', '')} "
                        f"{hit.get('timezone', '')}".strip()
                    )
                )
            if hit.get("host"):
                lines.append(line(f"host: {hit['host']}"))
            if hit.get("x_forwarded_for"):
                lines.append(line(f"x-forwarded-for: {hit['x_forwarded_for']}"))
            if hit.get("isp") or hit.get("asn"):
                lines.append(
                    line(f"isp/asn: {hit.get('isp', '')} {hit.get('asn', '')}".strip())
                )
            if hit.get("lat") is not None and hit.get("lng") is not None:
                lines.append(line(f"coords: {hit['lat']}, {hit['lng']}"))
            if hit.get("geo_status"):
                lines.append(line(f"geo: {hit['geo_status']}"))
            if hit.get("geo_note"):
                lines.append(error(hit["geo_note"]))

            shown = {
                "time",
                "ip",
                "method",
                "path",
                "page_path",
                "page_title",
                "page_url",
                "user_agent",
                "referer",
                "page_referrer",
                "language",
                "browser_language",
                "screen",
                "timezone",
                "host",
                "x_forwarded_for",
                "isp",
                "asn",
                "lat",
                "lng",
                "location",
                "geo_status",
                "geo_note",
                "view_id",
            }
            for key, value in hit.items():
                if key in shown or value in (None, "", [], {}):
                    continue
                lines.append(line(f"{key}: {value}"))
        return "\n".join(lines)

    def _render_map(self) -> None:
        map_view = getattr(self.ui, "ipLoggerMap", None)
        if map_view is None:
            return

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
            tiles=self._script_json(MAP_TILES),
            attribution=self._script_json(MAP_ATTRIBUTION),
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
