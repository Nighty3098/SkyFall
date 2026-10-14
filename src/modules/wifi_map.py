"""Public Wi-Fi hotspot lookup.

Backed by the Supabase/PostgREST ``hotspots_public`` view used by the
"WiFi Passwords" mobile app.  A city name (or an explicit ``lat, lng`` pair)
is resolved to a geographic bounding box through Nominatim, the hotspots
inside that box are fetched, and - for the subset the owner published on the
web (``public_web``) - their passwords are pulled from the
``get_hotspot_password`` RPC.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from loguru import logger

BASE_URL = "https://auth.wifi-passwords.com/rest/v1/hotspots_public"
PASSWORD_RPC_URL = "https://auth.wifi-passwords.com/rest/v1/rpc/get_hotspot_password"
API_KEY = "sb_publishable_DSQWCiq5aRxSI-NDPwDhjw_ybBv976h"

HOTSPOT_COLUMNS = (
    "id,ssid,security_type,has_password,has_password_or_open,is_public,"
    "public_web,user_name,country,city,lat,lng,p_internet,region_id,"
    "last_seen,last_connection_at,created_at"
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SkyFallWifiMap/1.0 (+https://github.com/Nighty3098/SkyFall)"

DEFAULT_LIMIT = None
COORD_DELTA = 0.1
PAGE_SIZE = 1000
MAX_PAGES = 1000
PASSWORD_WORKERS = 16

# ``security_type`` is a numeric enum in the app.  The names below are a
# best-effort mapping inferred from the API (4 == open, 2 == WPA/WPA2); codes
# without a confident name fall back to ``Type <n>``.
SECURITY_TYPES = {
    -1: "Unknown",
    0: "WPA",
    1: "WEP",
    2: "WPA/WPA2",
    3: "WPA2",
    4: "Open",
    5: "WPA3",
}


class WifiMap:
    def __init__(self, api_key: str = API_KEY):
        logger.debug("Init: WifiMap")
        self.base_url = BASE_URL
        self.password_rpc_url = PASSWORD_RPC_URL
        self.api_key = api_key
        self.headers = {
            "apikey": self.api_key,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def parse_coords(text: str):
        """Parse ``"lat, lng"`` into a ``(lat, lng)`` tuple (or ``None``)."""
        if not text or "," not in text:
            return None
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 2:
            return None
        try:
            lat, lng = float(parts[0]), float(parts[1])
        except ValueError:
            return None
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return None
        return lat, lng

    @staticmethod
    def security_name(code):
        if code is None:
            return "Unknown"
        return SECURITY_TYPES.get(code, f"Type {code}")

    @staticmethod
    def build_params(
        bbox,
        limit: int = PAGE_SIZE,
        offset: int = 0,
        select: str = HOTSPOT_COLUMNS,
    ):
        """Build the PostgREST query parameters for a ``(s, n, w, e)`` box."""
        south, north, west, east = bbox
        return [
            ("select", select),
            ("lat", f"gte.{south}"),
            ("lat", f"lte.{north}"),
            ("lng", f"gte.{west}"),
            ("lng", f"lte.{east}"),
            ("order", "id.asc"),
            ("limit", str(limit)),
            ("offset", str(offset)),
        ]

    # ── Geocoding ─────────────────────────────────────────────────

    def geocode(self, query: str, timeout: int = 20):
        """Resolve a city name or ``lat, lng`` pair into a bounding box."""
        coords = self.parse_coords(query)
        if coords is not None:
            lat, lng = coords
            return {
                "display_name": f"{lat:.5f}, {lng:.5f}",
                "lat": lat,
                "lng": lng,
                "bbox": (
                    lat - COORD_DELTA,
                    lat + COORD_DELTA,
                    lng - COORD_DELTA,
                    lng + COORD_DELTA,
                ),
            }

        response = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return None

        top = data[0]
        south, north, west, east = (float(v) for v in top["boundingbox"])
        return {
            "display_name": top.get("display_name", query),
            "lat": float(top.get("lat", (south + north) / 2)),
            "lng": float(top.get("lon", (west + east) / 2)),
            "bbox": (south, north, west, east),
        }

    # ── Passwords ─────────────────────────────────────────────────

    def get_password(self, hotspot_id, timeout: int = 20):
        """Fetch a hotspot password via the ``get_hotspot_password`` RPC.

        The RPC only returns a value for hotspots whose owner published the
        password on the web (``public_web == true``); it is ``null`` for the
        rest.  Returns the password string or ``None``.
        """
        response = requests.post(
            self.password_rpc_url,
            json={"p_id": hotspot_id},
            headers=self.headers,
            timeout=timeout,
        )
        response.raise_for_status()
        value = response.json()
        return value if isinstance(value, str) and value else None

    def _attach_passwords(self, hotspots, timeout: int = 20):
        targets = [h for h in hotspots if h.get("public_web") and h.get("has_password")]
        if not targets:
            return

        with ThreadPoolExecutor(max_workers=PASSWORD_WORKERS) as pool:
            futures = {
                pool.submit(self.get_password, h["id"], timeout): h for h in targets
            }
            for future in as_completed(futures):
                hotspot = futures[future]
                try:
                    hotspot["password"] = future.result()
                except Exception as e:
                    logger.debug(f"Password lookup failed for {hotspot['id']}: {e}")
                    hotspot["password"] = None

    # ── Hotspots ──────────────────────────────────────────────────

    def _fetch_all(self, bbox, limit, timeout: int = 20):
        """Fetch every hotspot in ``bbox``, paging past the 1000-row server cap.

        ``limit`` caps the total number of rows; ``None`` means "all".
        """
        page_size = PAGE_SIZE
        if limit is not None:
            page_size = min(PAGE_SIZE, limit)

        records = []
        offset = 0
        for _ in range(MAX_PAGES):
            size = page_size
            if limit is not None:
                size = min(size, limit - len(records))
                if size <= 0:
                    break
            response = requests.get(
                self.base_url,
                params=self.build_params(bbox, size, offset),
                headers=self.headers,
                timeout=timeout,
            )
            response.raise_for_status()
            batch = response.json()
            records.extend(batch)
            if len(batch) < size:
                break
            offset += len(batch)
        return records

    def search(
        self,
        query: str,
        limit: int | None = DEFAULT_LIMIT,
        timeout: int = 20,
        with_passwords: bool = True,
    ):
        """Return the public hotspots inside the bounding box of ``query``."""
        if not query or not query.strip():
            return {"query": query, "error": "Empty query."}
        query = query.strip()

        try:
            location = self.geocode(query, timeout=timeout)
        except Exception as e:
            logger.error(f"WifiMap geocoding failed for '{query}': {e}")
            return {"query": query, "error": f"Geocoding failed: {e}"}

        if location is None:
            return {"query": query, "error": f"Could not locate '{query}'."}

        try:
            records = self._fetch_all(location["bbox"], limit, timeout)
        except Exception as e:
            logger.error(f"WifiMap hotspot fetch failed for '{query}': {e}")
            return {"query": query, "error": f"Hotspot request failed: {e}"}

        hotspots = []
        for item in records:
            if item.get("lat") is None or item.get("lng") is None:
                continue
            hotspots.append(self._normalize(item))

        password_count = 0
        if with_passwords:
            self._attach_passwords(hotspots, timeout=timeout)
            password_count = sum(1 for h in hotspots if h.get("password"))

        return {
            "query": query,
            "location": location["display_name"],
            "lat": location["lat"],
            "lng": location["lng"],
            "bbox": location["bbox"],
            "total": len(hotspots),
            "public_web": sum(1 for h in hotspots if h.get("public_web")),
            "passwords": password_count,
            "hotspots": hotspots,
        }

    async def search_async(
        self,
        query: str,
        limit: int | None = DEFAULT_LIMIT,
        timeout: int = 20,
        with_passwords: bool = True,
    ):
        return await asyncio.to_thread(
            self.search, query, limit, timeout, with_passwords
        )

    @classmethod
    def _normalize(cls, item: dict) -> dict:
        code = item.get("security_type")
        return {
            "id": item.get("id"),
            "ssid": item.get("ssid") or "",
            "security_type": code,
            "security": cls.security_name(code),
            "has_password": bool(item.get("has_password")),
            "has_password_or_open": bool(item.get("has_password_or_open")),
            "is_public": bool(item.get("is_public")),
            "public_web": bool(item.get("public_web")),
            "user_name": item.get("user_name") or "",
            "country": item.get("country") or "",
            "city": item.get("city") or "",
            "region_id": item.get("region_id"),
            "lat": float(item["lat"]),
            "lng": float(item["lng"]),
            "p_internet": item.get("p_internet"),
            "last_seen": item.get("last_seen") or "",
            "last_connection_at": item.get("last_connection_at") or "",
            "created_at": item.get("created_at") or "",
            "password": None,
        }
