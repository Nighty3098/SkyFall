"""Tiny HTTP hit logger backing the IP LOGGER tab.

The server runs on the application's asyncio loop and exposes a 1x1 GIF for
every request.  Each hit is stored in memory, enriched with geolocation and
pushed to the UI through a callback.
"""

from __future__ import annotations

import asyncio
import inspect
import ipaddress
import socket
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from aiohttp import web
from loguru import logger

from src.modules.ip2location_io import IP2LocationIO

if TYPE_CHECKING:
    from collections.abc import Awaitable

HitCallback = Callable[[dict[str, Any]], "Awaitable[None] | None"]

# 1x1 transparent GIF — invisible to whoever opens the link.
PIXEL = bytes.fromhex(
    "47494638396101000100800000000000ffffff21f90401000000002c"
    "00000000010001000002024401003b"
)


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class IpLogger:
    def __init__(
        self,
        api_key: str = "",
        geo: IP2LocationIO | None = None,
        geo_timeout: float = 6.0,
    ):
        logger.debug("Init: IP Logger")
        self._geo_timeout = geo_timeout
        self._geo = geo or IP2LocationIO(api_key=api_key, timeout=geo_timeout)
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._on_hit: HitCallback | None = None
        self._tasks: set[asyncio.Task] = set()
        self.port: int | None = None
        self.hits: list[dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        return self._runner is not None

    def set_api_key(self, key: str) -> None:
        self._geo.api_key = (key or "").strip()

    def on_hit(self, callback: HitCallback) -> None:
        self._on_hit = callback

    @staticmethod
    def _parse_port(port: str | int) -> int:
        try:
            value = int(str(port).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("Port must be a number") from exc
        if not 1 <= value <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return value

    @staticmethod
    def _lan_ip() -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"

    @staticmethod
    def _client_ip(request: web.Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            candidate = forwarded.split(",", 1)[0].strip()
            try:
                ipaddress.ip_address(candidate)
            except ValueError:
                pass
            else:
                return candidate
        return request.remote or "unknown"

    def urls(self) -> list[str]:
        if self.port is None:
            return []
        hosts = []
        lan_ip = self._lan_ip()
        if lan_ip != "127.0.0.1":
            hosts.append(lan_ip)
        hosts.append("127.0.0.1")
        return [f"http://{host}:{self.port}/" for host in dict.fromkeys(hosts)]

    async def start_server(self, port: str | int) -> dict[str, Any]:
        if self.is_running:
            raise RuntimeError("IP logger server is already running")

        port_number = self._parse_port(port)
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", self._handle_request)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        try:
            site = web.TCPSite(runner, host="0.0.0.0", port=port_number)
            await site.start()
        except Exception:
            await runner.cleanup()
            raise

        self._runner = runner
        self._site = site
        self.port = port_number
        self.hits.clear()
        logger.info(f"IP logger listening on port {port_number}")
        return {"port": port_number, "urls": self.urls()}

    async def stop(self) -> None:
        runner = self._runner
        self._runner = None
        self._site = None
        self.port = None

        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if runner is not None:
            await runner.cleanup()

    async def _handle_request(self, request: web.Request) -> web.Response:
        hit: dict[str, Any] = {
            "time": datetime.now(UTC).isoformat(timespec="seconds"),
            "ip": self._client_ip(request),
            "method": request.method,
            "path": request.path,
            "host": request.headers.get("Host", ""),
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
            "language": request.headers.get("Accept-Language", ""),
            "x_forwarded_for": request.headers.get("X-Forwarded-For", ""),
        }
        self.hits.append(hit)
        self._notify(hit)

        task = asyncio.create_task(self._enrich(hit))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        return web.Response(
            body=PIXEL,
            content_type="image/gif",
            headers={"Cache-Control": "no-store"},
        )

    async def _enrich(self, hit: dict[str, Any]) -> None:
        try:
            geo = await asyncio.wait_for(
                self._geo.lookup(hit["ip"]), timeout=self._geo_timeout
            )
        except Exception as exc:
            geo = {"status": "ERROR", "note": str(exc)[:200]}
        if not isinstance(geo, dict):
            geo = {}

        hit["location"] = ", ".join(
            str(geo[key]) for key in ("city", "region", "country") if geo.get(key)
        )
        hit["lat"] = _as_float(geo.get("lat", geo.get("latitude")))
        hit["lng"] = _as_float(geo.get("lon", geo.get("longitude")))
        hit["isp"] = geo.get("isp", "")
        hit["asn"] = geo.get("asn", "")
        hit["geo_status"] = geo.get("status", "")
        if geo.get("note"):
            hit["geo_note"] = str(geo["note"])[:200]
        self._notify(hit)

    def _notify(self, hit: dict[str, Any]) -> None:
        callback = self._on_hit
        if callback is None:
            return
        try:
            result = callback(dict(hit))
        except Exception:
            logger.exception("IP logger hit callback failed")
            return
        if inspect.isawaitable(result):
            task = asyncio.create_task(result)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
