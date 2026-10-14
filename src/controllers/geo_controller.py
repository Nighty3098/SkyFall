from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.geo_analysis import GeoAnalysis


class GeoController:
    def __init__(self, ui: "QMainWindow", geo: "GeoAnalysis", firms_key: str = ""):
        logger.debug("Init: GeoController")
        self.ui = ui
        self.geo = geo
        self.firms_key = firms_key

    def _debug(self):
        return getattr(self.ui, "geoDebug", None)

    def _coords(self):
        text = getattr(self.ui, "geoCoordEdit", None)
        return text.text().strip() if text is not None else ""

    def _when(self) -> datetime:
        widget = getattr(self.ui, "geoDateTimeEdit", None)
        if widget is not None:
            dt = widget.dateTime().toPython()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        return datetime.now(UTC)

    async def sun_shadow(self):
        widget = self._debug()
        if widget is None:
            return
        coords = self.geo.parse_coords(self._coords())
        if coords is None:
            widget.setPlainText("Enter coordinates as 'lat, lon'")
            return
        widget.setPlainText("Computing sun / shadow geometry...")
        data = self.geo.sun_shadow(coords[0], coords[1], self._when())
        summary = self.geo.summarize_sun_shadow(data)
        widget.setPlainText(render(summary, "Sun / shadow geometry"))

    async def shadow_search(self):
        widget = self._debug()
        if widget is None:
            return
        widget.setPlainText(
            "Searching for coordinates matching the shadow (this may take a while)..."
        )
        ratio_widget = getattr(self.ui, "geoShadowRatioEdit", None)
        bearing_widget = getattr(self.ui, "geoShadowBearingEdit", None)
        try:
            ratio = float(ratio_widget.text()) if ratio_widget is not None else 1.0
            bearing = (
                float(bearing_widget.text()) if bearing_widget is not None else 0.0
            )
        except ValueError:
            widget.setPlainText("Shadow ratio / bearing must be numbers")
            return
        results = self.geo.shadow_search(ratio, bearing, self._when())
        params = {
            "ratio": ratio,
            "bearing": bearing,
            "time": self._when().isoformat(),
        }
        summary = self.geo.summarize_shadow_search(results, params)
        widget.setPlainText(render(summary, "Shadow geolocation candidates"))

    async def firms(self):
        widget = self._debug()
        if widget is None:
            return
        coords = self.geo.parse_coords(self._coords())
        widget.setPlainText("Querying NASA FIRMS...")
        bbox = None
        if coords is not None:
            lat, lon = coords
            bbox = (lon - 2.0, lat - 2.0, lon + 2.0, lat + 2.0)
        data = await self.geo.firms(self.firms_key, bbox=bbox)
        summary = self.geo.summarize_firms(data)
        widget.setPlainText(render(summary, "NASA FIRMS - active fires"))

    async def gdacs(self):
        widget = self._debug()
        if widget is None:
            return
        widget.setPlainText("Querying GDACS...")
        data = await self.geo.gdacs()
        summary = self.geo.summarize_gdacs(data)
        widget.setPlainText(render(summary, "GDACS - disaster alerts"))

    async def full_report(self):
        widget = self._debug()
        if widget is None:
            return
        coords = self.geo.parse_coords(self._coords())
        if coords is None:
            widget.setPlainText("Enter coordinates as 'lat, lon'")
            return
        widget.setPlainText("Running geo analysis...")
        data = await self.geo.report(coords[0], coords[1], self._when(), self.firms_key)
        widget.setPlainText(render(data, f"Geo analysis: {coords[0]}, {coords[1]}"))
