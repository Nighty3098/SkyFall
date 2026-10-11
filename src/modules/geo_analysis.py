"""Geo analysis: sun/shadow geometry, NASA FIRMS fires and GDACS disasters.

* **Sun / shadow** — computed locally with ``suncalc`` (no API key).  From a
  coordinate and a UTC time it returns the sun position and the direction /
  length ratio of a cast shadow.  The inverse search finds candidate
  coordinates whose shadow matches an observed ratio and direction.
* **NASA FIRMS** — active fire detections (requires a free ``MAP_KEY``).
* **GDACS** — global disaster alerts (no key).

All network providers are best-effort and never raise.
"""

import csv
import io
import math
from datetime import UTC, datetime, timedelta

import httpx
from loguru import logger

from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    info,
    kv,
    section,
    title,
)

TIMEOUT = 30.0
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0"

FIRMS_API = "https://firms.modaps.eosdis.nasa.gov/api"
GDACS_API = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

GDACS_EVENTS = {
    "EQ": "Earthquakes",
    "TC": "Tropical cyclones",
    "FL": "Floods",
    "VO": "Volcanoes",
    "WF": "Wildfires",
    "DR": "Droughts",
}

FIRMS_SOURCES = {
    "VIIRS_SNPP_NRT": "VIIRS SNPP (NRT)",
    "VIIRS_NOAA20_NRT": "VIIRS NOAA-20 (NRT)",
    "MODIS_NRT": "MODIS (NRT)",
    "VIIRS_SNPP_SP": "VIIRS SNPP (standard)",
}


def _normalize_deg(value: float) -> float:
    return value % 360.0


def _angle_diff(a: float, b: float) -> float:
    """Smallest absolute difference between two compass angles in degrees."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


class GeoAnalysis:
    """Sun/shadow math plus FIRMS and GDACS lookups."""

    def __init__(self, timeout: float = TIMEOUT):
        logger.debug("Init: GeoAnalysis")
        self.timeout = timeout
        self.firms_key = ""

    # ── Sun / shadow ──────────────────────────────────────────────

    @staticmethod
    def sun_shadow(lat: float, lon: float, when: datetime) -> dict:
        from suncalc import get_position

        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        pos = get_position(when, lon, lat)
        azimuth = float(pos["azimuth"])
        altitude = float(pos["altitude"])

        # suncalc azimuth: radians from south, positive towards west.
        sun_bearing = _normalize_deg(math.degrees(azimuth) + 180.0)
        shadow_bearing = _normalize_deg(sun_bearing + 180.0)
        altitude_deg = math.degrees(altitude)

        ratio = None
        if altitude > 0.0:
            ratio = 1.0 / math.tan(altitude)

        return {
            "latitude": lat,
            "longitude": lon,
            "time_utc": when.astimezone(UTC).isoformat(),
            "sun_altitude_deg": round(altitude_deg, 3),
            "sun_azimuth_deg": round(sun_bearing, 3),
            "shadow_bearing_deg": round(shadow_bearing, 3),
            "shadow_ratio": round(ratio, 4) if ratio is not None else None,
            "sun_up": altitude > 0.0,
        }

    @staticmethod
    def shadow_search(
        shadow_ratio: float,
        shadow_bearing: float,
        when: datetime,
        lat_range: tuple[float, float] = (-60.0, 60.0),
        lon_range: tuple[float, float] = (-180.0, 180.0),
        step: float = 2.0,
        altitude_tol: float = 1.0,
        bearing_tol: float = 3.0,
        max_results: int = 100,
    ) -> list[dict]:
        import numpy as np
        from suncalc import get_position

        if shadow_ratio <= 0:
            return []
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)

        target_altitude = math.degrees(math.atan(1.0 / shadow_ratio))
        target_bearing = _normalize_deg(shadow_bearing + 180.0)

        lat_lo, lat_hi = sorted(lat_range)
        lon_lo, lon_hi = sorted(lon_range)
        lats = np.arange(lat_lo, lat_hi + 1e-9, step)
        lons = np.arange(lon_lo, lon_hi + 1e-9, step)

        results: list[dict] = []
        for lat in lats:
            for lon in lons:
                pos = get_position(when, float(lon), float(lat))
                alt_deg = math.degrees(float(pos["altitude"]))
                if alt_deg <= 0:
                    continue
                if abs(alt_deg - target_altitude) > altitude_tol:
                    continue
                bearing = _normalize_deg(math.degrees(float(pos["azimuth"])) + 180.0)
                diff = _angle_diff(bearing, target_bearing)
                if diff > bearing_tol:
                    continue
                results.append(
                    {
                        "latitude": round(float(lat), 4),
                        "longitude": round(float(lon), 4),
                        "sun_altitude_deg": round(alt_deg, 3),
                        "shadow_bearing_deg": round(_normalize_deg(bearing + 180.0), 3),
                        "error_deg": round(diff, 3),
                    }
                )
        results.sort(key=lambda r: r["error_deg"])
        return results[:max_results]

    # ── NASA FIRMS ────────────────────────────────────────────────

    async def firms(
        self,
        map_key: str = "",
        source: str = "VIIRS_SNPP_NRT",
        bbox: tuple[float, float, float, float] | None = None,
        day_range: int = 1,
    ) -> dict:
        map_key = map_key or self.firms_key
        if not map_key:
            return {"error": "NASA FIRMS MAP_KEY not configured"}
        source = source if source in FIRMS_SOURCES else "VIIRS_SNPP_NRT"
        day_range = max(1, min(int(day_range), 10))
        if bbox:
            lon_lo, lat_lo, lon_hi, lat_hi = bbox
            area = f"{lon_lo},{lat_lo},{lon_hi},{lat_hi}"
        else:
            area = "world"
        url = f"{FIRMS_API}/area/csv/{map_key}/{source}/{area}/{day_range}"

        async with httpx.AsyncClient(
            timeout=self.timeout, headers={"User-Agent": _USER_AGENT}
        ) as client:
            try:
                resp = await client.get(url)
            except Exception as exc:
                logger.debug(f"FIRMS error: {exc}")
                return {"error": str(exc)}
        text = resp.text.strip()
        if resp.status_code != 200 or text.lower().startswith("invalid"):
            return {"error": text[:200] or f"HTTP {resp.status_code}"}

        rows = list(csv.DictReader(io.StringIO(text)))
        fires = []
        for row in rows[:500]:
            try:
                fires.append(
                    {
                        "latitude": float(row.get("latitude", 0)),
                        "longitude": float(row.get("longitude", 0)),
                        "brightness": row.get("bright_ti4")
                        or row.get("brightness", ""),
                        "frp": row.get("frp", ""),
                        "confidence": row.get("confidence", ""),
                        "date": row.get("acq_date", ""),
                        "time": row.get("acq_time", ""),
                        "satellite": row.get("satellite", ""),
                    }
                )
            except (TypeError, ValueError):
                continue
        return {
            "source": source,
            "area": area,
            "day_range": day_range,
            "count": len(rows),
            "fires": fires,
        }

    # ── GDACS ─────────────────────────────────────────────────────

    async def gdacs(
        self,
        event_types: str = "EQ,TC,FL,VO,WF,DR",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        today = datetime.now(UTC).date()
        date_to = date_to or today.isoformat()
        date_from = date_from or (today - timedelta(days=30)).isoformat()
        params = {
            "eventlist": event_types,
            "from": date_from,
            "to": date_to,
        }
        async with httpx.AsyncClient(
            timeout=self.timeout, headers={"User-Agent": _USER_AGENT}
        ) as client:
            try:
                resp = await client.get(GDACS_API, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.debug(f"GDACS error: {exc}")
                return {"error": str(exc)}

        events = []
        for feat in data.get("features", [])[:500]:
            props = feat.get("properties", {})
            coords = (feat.get("geometry") or {}).get("coordinates") or [None, None]
            events.append(
                {
                    "event_type": props.get("eventtype", "?"),
                    "event_id": props.get("eventid", "?"),
                    "name": props.get("name") or props.get("eventname", "?"),
                    "alert_level": props.get("alertlevel", "?"),
                    "country": props.get("country", "?"),
                    "from_date": props.get("fromdate", "?"),
                    "longitude": coords[0],
                    "latitude": coords[1],
                }
            )
        return {
            "date_from": date_from,
            "date_to": date_to,
            "event_types": event_types,
            "count": len(events),
            "events": events,
        }

    # ── Text rendering ────────────────────────────────────────────

    def render_sun_shadow(self, data: dict) -> str:
        lines = [title("Sun / shadow geometry")]
        lines.append(kv("Coordinates", f"{data['latitude']}, {data['longitude']}"))
        lines.append(kv("Time (UTC)", data["time_utc"]))
        lines.append(kv("Sun altitude", f"{data['sun_altitude_deg']} deg"))
        lines.append(kv("Sun azimuth", f"{data['sun_azimuth_deg']} deg"))
        if data["sun_up"]:
            lines.append(kv("Shadow bearing", f"{data['shadow_bearing_deg']} deg"))
            lines.append(kv("Shadow length ratio", f"{data['shadow_ratio']} x height"))
        else:
            lines.append(info("Sun is below the horizon"))
        lines.append(divider())
        return "\n".join(lines)

    def render_shadow_search(self, results: list[dict], params: dict) -> str:
        lines = [title("Shadow geolocation candidates")]
        lines.append(
            info(
                f"ratio={params['ratio']} bearing={params['bearing']} deg "
                f"@ {params['time']} | {len(results)} candidate(s)"
            )
        )
        if not results:
            lines.append(info("No matching coordinates found"))
        for r in results[:30]:
            lines.append(
                bullet(
                    f"{r['latitude']}, {r['longitude']} "
                    f"(alt {r['sun_altitude_deg']} deg, err {r['error_deg']} deg)"
                )
            )
        lines.append(divider())
        return "\n".join(lines)

    def render_firms(self, data: dict) -> str:
        lines = [title("NASA FIRMS - active fires")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
            lines.append(divider())
            return "\n".join(lines)
        lines.append(kv("Source", data.get("source", "?")))
        lines.append(kv("Area", data.get("area", "?")))
        lines.append(kv("Detections", data.get("count", 0)))
        for f in (data.get("fires") or [])[:25]:
            lines.append(
                bullet(
                    f"{f['latitude']}, {f['longitude']} "
                    f"(FRP {f.get('frp', '?')}, "
                    f"{f.get('date', '?')} {f.get('time', '?')})"
                )
            )
        lines.append(divider())
        return "\n".join(lines)

    def render_gdacs(self, data: dict) -> str:
        lines = [title("GDACS - disaster alerts")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
            lines.append(divider())
            return "\n".join(lines)
        lines.append(kv("Period", f"{data.get('date_from')} .. {data.get('date_to')}"))
        lines.append(kv("Events", data.get("count", 0)))
        for e in (data.get("events") or [])[:40]:
            etype = GDACS_EVENTS.get(e["event_type"], e["event_type"])
            lines.append(
                bullet(
                    f"[{e['alert_level']}] {etype}: {e['name']} "
                    f"({e['country']}, {e['from_date']})"
                )
            )
        lines.append(divider())
        return "\n".join(lines)

    # ── Combined text entry point ─────────────────────────────────

    async def report(
        self,
        lat: float,
        lon: float,
        when: datetime | None = None,
        firms_key: str = "",
        firms_delta: float = 2.0,
    ) -> str:
        when = when or datetime.now(UTC)
        lines = [self.render_sun_shadow(self.sun_shadow(lat, lon, when))]
        lines.append(section("Nearby active fires (FIRMS)"))
        bbox = (
            lon - firms_delta,
            lat - firms_delta,
            lon + firms_delta,
            lat + firms_delta,
        )
        lines.append(self.render_firms(await self.firms(firms_key, bbox=bbox)))
        lines.append(end_of("geo analysis"))
        return "\n".join(lines)

    @staticmethod
    def parse_coords(raw: str) -> tuple[float, float] | None:
        import re

        m = re.fullmatch(
            r"\s*(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)\s*", raw or ""
        )
        if not m:
            return None
        lat, lon = float(m.group(1)), float(m.group(2))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        return lat, lon
