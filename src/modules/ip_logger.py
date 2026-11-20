"""HTTP site + hit logger backing the IP LOGGER tab.

The selected HTML template is served on the chosen port.  Every page response
gets a small tracking beacon injected into it; the beacon records the visitor
and stores browser-side details (title, URL, screen, timezone) on the same hit.
Geolocation is resolved in the background and pushed to the UI via a callback.

Ports below 1024 are handled by ``PrivilegedForwarder``: the app listens on an
ephemeral loopback port while a native admin prompt starts an elevated helper
that owns the low port and relays connections back to the app.
"""

from __future__ import annotations

import asyncio
import inspect
import ipaddress
import json
import secrets
import socket
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape as escape_html
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

from aiohttp import web
from loguru import logger

from src.modules.ip2location_io import IP2LocationIO
from src.modules.ip_logger_privilege import (
    PrivilegedForwarder,
    needs_elevation,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable

HitCallback = Callable[[dict[str, Any]], "Awaitable[None] | None"]

# 1x1 transparent GIF — invisible to whoever opens the link.
PIXEL = bytes.fromhex(
    "47494638396101000100800000000000ffffff21f90401000000002c"
    "00000000010001000002024401003b"
)
BEACON_PREFIX = "/__skyfall_iplogger/"
HTML_SUFFIXES = (".html", ".htm")
META_KEYS = (
    "page_title",
    "page_url",
    "page_referrer",
    "screen",
    "timezone",
    "browser_language",
)

# Public-IP services used to advertise a reachable external link.  Tried in
# order; the first valid answer wins.
PUBLIC_IP_ENDPOINTS = (
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
    "https://icanhazip.com",
)
# PROXY protocol v1 (text) header.  The elevated forwarder emits it so the
# real client address survives the low-port relay.
PROXY_PREFIX = b"PROXY "
PROXY_MAX_HEADER = 108

FALLBACK_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>SkyFall IP Logger</title></head>
<body>
  <h1>SkyFall IP Logger</h1>
  <p>Add HTML files to <code>src/templates</code> or
  <code>~/.skyfall/data/www_templates</code>, then pick one in the site
  selector to serve it on this port.</p>
</body>
</html>"""


@dataclass(frozen=True)
class SiteTemplate:
    label: str
    path: Path


def default_template_dirs() -> list[Path]:
    """Built-in template folder plus the per-user SkyFall data folder."""
    root = Path(__file__).resolve().parents[2]
    return [
        root / "src" / "templates",
        root / "src" / "www_templates",
        Path.home() / ".skyfall" / "data" / "www_templates",
    ]


def tracker_snippet(beacon_src: str) -> str:
    """Tracking code appended to a served HTML page."""
    return Template("""<script>
(function () {
  var info = {
    page_title: document.title || '',
    page_url: location.href,
    page_referrer: document.referrer || '',
    screen: window.screen ? screen.width + 'x' + screen.height : '',
    timezone: (Intl.DateTimeFormat().resolvedOptions().timeZone || ''),
    browser_language: navigator.language || ''
  };
  var pixel = new Image(1, 1);
  pixel.src = $src + '&e=' + encodeURIComponent(JSON.stringify(info));
})();
</script>
<noscript><img src="$plain" alt="" width="1" height="1"></noscript>""").substitute(
        src=json.dumps(beacon_src), plain=escape_html(beacon_src, quote=True)
    )


def inject_tracker(html: str, beacon_src: str) -> str:
    """Insert the tracking beacon without changing the template's own markup."""
    snippet = tracker_snippet(beacon_src)
    lowered = html.lower()
    for closing_tag in ("</body>", "</html>"):
        position = lowered.rfind(closing_tag)
        if position != -1:
            return html[:position] + snippet + html[position:]
    return html + snippet


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address((value or "").strip())
        return True
    except (TypeError, ValueError):
        return False


def _parse_networks(
    values: list[str] | None,
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    """Parse trusted-proxy entries (IPs or CIDRs), ignoring invalid ones."""
    networks = []
    for value in values or []:
        try:
            networks.append(ipaddress.ip_network(value.strip(), strict=False))
        except ValueError:
            logger.warning(f"IP logger: ignoring invalid trusted proxy {value!r}")
    return tuple(networks)


def _url_host(host: str) -> str:
    """Wrap IPv6 literals in brackets so they form a valid URL authority."""
    return f"[{host}]" if ":" in host else host


def _fetch_public_ip(timeout: float = 4.0) -> str:
    """Best-effort public IP lookup; returns "" when offline or blocked."""
    for url in PUBLIC_IP_ENDPOINTS:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                text = response.read(64).decode("ascii", "ignore").strip()
        except Exception:
            continue
        if _is_ip(text):
            return text
    return ""


def parse_proxy_header(line: bytes) -> tuple[str, int] | None:
    """Parse a PROXY protocol v1 line into ``(address, port)`` or ``None``."""
    try:
        parts = line.decode("ascii").split()
    except UnicodeDecodeError:
        return None
    if len(parts) < 6 or parts[0] != "PROXY" or parts[1] not in ("TCP4", "TCP6"):
        return None
    source = parts[2]
    if not _is_ip(source):
        return None
    try:
        port = int(parts[4])
    except ValueError:
        return None
    return source, port


class _PeerTransport:
    """Transport wrapper that reports a substituted peer address.

    aiohttp reads ``request.remote`` from ``transport.get_extra_info("peername")``;
    overriding just that key lets the PROXY header's client address flow through
    without patching aiohttp internals.
    """

    __slots__ = ("_transport", "_peer", "__weakref__")

    def __init__(self, transport: asyncio.Transport, peer: tuple[str, int] | None):
        self._transport = transport
        self._peer = peer

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        if name == "peername" and self._peer is not None:
            return self._peer
        return self._transport.get_extra_info(name, default)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._transport, item)


class ProxyProtocolHandler(asyncio.Protocol):
    """Strip an optional PROXY v1 header, then hand the stream to aiohttp.

    Connections that do not start with ``PROXY `` (direct clients on a
    non-privileged port) are passed through untouched.
    """

    def __init__(self, factory: Callable[[], asyncio.Protocol]):
        self._factory = factory
        self._protocol: asyncio.Protocol | None = None
        self._buffer = b""
        self._transport: asyncio.Transport | None = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self._transport = transport

    def data_received(self, data: bytes) -> None:
        if self._protocol is not None:
            self._protocol.data_received(data)
            return
        self._buffer += data
        if not self._buffer.startswith(PROXY_PREFIX):
            self._start(None, self._buffer)
            return
        end = self._buffer.find(b"\r\n")
        if end == -1:
            if len(self._buffer) > PROXY_MAX_HEADER:
                self._start(None, self._buffer)
            return
        peer = parse_proxy_header(self._buffer[:end])
        self._start(peer, self._buffer[end + 2 :])

    def _start(self, peer: tuple[str, int] | None, remainder: bytes) -> None:
        protocol = self._factory()
        self._protocol = protocol
        assert self._transport is not None
        transport = (
            self._transport if peer is None else _PeerTransport(self._transport, peer)
        )
        protocol.connection_made(transport)
        if remainder:
            protocol.data_received(remainder)

    def eof_received(self) -> bool | None:
        if self._protocol is None:
            return False
        return self._protocol.eof_received()

    def connection_lost(self, exc: Exception | None) -> None:
        if self._protocol is not None:
            self._protocol.connection_lost(exc)


class IpLogger:
    def __init__(
        self,
        api_key: str = "",
        geo: IP2LocationIO | None = None,
        geo_timeout: float = 6.0,
        template_dirs: list[Path] | None = None,
        trusted_proxies: list[str] | None = None,
    ):
        logger.debug("Init: IP Logger")
        self._geo_timeout = geo_timeout
        self._geo = geo or IP2LocationIO(api_key=api_key, timeout=geo_timeout)
        self._template_dirs = list(template_dirs or default_template_dirs())
        self._trusted_networks = _parse_networks(trusted_proxies)
        self._runner: web.AppRunner | None = None
        self._server: asyncio.Server | None = None
        self._forwarder: PrivilegedForwarder | None = None
        self._on_hit: HitCallback | None = None
        self._on_state: Callable[[], None] | None = None
        self._tasks: set[asyncio.Task] = set()
        self.port: int | None = None
        self.public_ip = ""
        self.hits: list[dict[str, Any]] = []
        self._beacon_token = secrets.token_urlsafe(6)
        self._templates: list[SiteTemplate] = []
        self._template_index = 0
        self.refresh_templates()

    @property
    def is_running(self) -> bool:
        return self._runner is not None

    @property
    def templates(self) -> list[SiteTemplate]:
        return list(self._templates)

    @property
    def current_template(self) -> SiteTemplate | None:
        if 0 <= self._template_index < len(self._templates):
            return self._templates[self._template_index]
        return None

    def set_api_key(self, key: str) -> None:
        self._geo.api_key = (key or "").strip()

    def on_hit(self, callback: HitCallback) -> None:
        self._on_hit = callback

    def on_state(self, callback: Callable[[], None]) -> None:
        """Register a callback fired when server state changes (e.g. public IP)."""
        self._on_state = callback

    def _notify_state(self) -> None:
        callback = self._on_state
        if callback is None:
            return
        try:
            callback()
        except Exception:
            logger.exception("IP logger state callback failed")

    async def resolve_public_ip(self, timeout: float = 4.0) -> str:
        """Look up the router's public IP and advertise it as a link.

        Best-effort: failures (offline, CGNAT, blocked service) are silent and
        simply leave the link list without a public entry.
        """
        ip = await asyncio.to_thread(_fetch_public_ip, timeout)
        if ip and self.is_running:
            self.public_ip = ip
            self._notify_state()
        return ip

    def _is_trusted_proxy(self, address: str) -> bool:
        if not self._trusted_networks:
            return False
        try:
            ip = ipaddress.ip_address((address or "").strip())
        except ValueError:
            return False
        return any(ip in network for network in self._trusted_networks)

    def refresh_templates(self) -> list[SiteTemplate]:
        """Re-scan template folders, keeping the same site selected if possible."""
        previous = self.current_template
        found: list[SiteTemplate] = []
        seen: set[Path] = set()
        for directory in self._template_dirs:
            if not directory.is_dir():
                continue
            try:
                paths = sorted(directory.iterdir(), key=lambda item: item.name.lower())
            except OSError:
                continue
            for path in paths:
                if not path.is_file() or path.suffix.lower() not in HTML_SUFFIXES:
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                found.append(SiteTemplate(path.name, path))

        counts = {
            item.label: sum(t.label == item.label for t in found) for item in found
        }
        templates = [
            SiteTemplate(
                f"{item.label} [{item.path.parent.name}]"
                if counts[item.label] > 1
                else item.label,
                item.path,
            )
            for item in found
        ]
        self._templates = templates
        self._template_index = 0
        if previous is not None:
            for index, template in enumerate(templates):
                if template.path == previous.path:
                    self._template_index = index
                    break
        return self.templates

    def select_template(self, index: int) -> bool:
        if not isinstance(index, int) or not 0 <= index < len(self._templates):
            return False
        self._template_index = index
        return True

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

    def _resolve_client(self, request: web.Request) -> tuple[str, str]:
        """Return ``(client_ip, source)`` without trusting spoofable headers.

        The real TCP peer wins by default.  ``X-Forwarded-For``/``X-Real-IP``
        are only honoured when the immediate peer is a configured trusted proxy
        (or when the elevated forwarder already replaced the peer via the PROXY
        protocol).
        """
        remote = request.remote or "unknown"
        if self._is_trusted_proxy(remote):
            forwarded = request.headers.get("X-Forwarded-For", "")
            if forwarded:
                candidate = forwarded.split(",", 1)[0].strip()
                if _is_ip(candidate):
                    return candidate, "x-forwarded-for"
            real_ip = request.headers.get("X-Real-IP", "")
            if _is_ip(real_ip):
                return real_ip, "x-real-ip"
        return remote, "direct"

    def _client_ip(self, request: web.Request) -> str:
        return self._resolve_client(request)[0]

    @staticmethod
    def _decode_meta(raw: str) -> dict[str, str]:
        if not raw or len(raw) > 4096:
            return {}
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        meta: dict[str, str] = {}
        for key in META_KEYS:
            value = data.get(key)
            if isinstance(value, (str, int, float)) and str(value):
                meta[key] = str(value)[:300]
        return meta

    def urls(self) -> list[str]:
        if self.port is None:
            return []
        hosts = []
        if self.public_ip:
            hosts.append(self.public_ip)
        lan_ip = self._lan_ip()
        if lan_ip != "127.0.0.1":
            hosts.append(lan_ip)
        hosts.append("127.0.0.1")
        return [
            f"http://{_url_host(host)}:{self.port}/" for host in dict.fromkeys(hosts)
        ]

    async def start_server(self, port: str | int) -> dict[str, Any]:
        if self.is_running:
            raise RuntimeError("IP logger server is already running")

        port_number = self._parse_port(port)
        self.refresh_templates()
        self._beacon_token = secrets.token_urlsafe(6)
        beacon_path = f"{BEACON_PREFIX}{self._beacon_token}/pixel.gif"

        app = web.Application()
        app.router.add_get(beacon_path, self._handle_beacon)
        app.router.add_route("*", "/{tail:.*}", self._handle_page)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        server_protocol = runner.server
        assert server_protocol is not None

        def protocol_factory() -> asyncio.Protocol:
            return ProxyProtocolHandler(server_protocol)

        loop = asyncio.get_running_loop()
        forwarder: PrivilegedForwarder | None = None
        server: asyncio.Server | None = None
        elevated = needs_elevation(port_number)
        try:
            if elevated:
                # Loopback only; the elevated forwarder owns the low port and
                # relays here with a PROXY header carrying the real client.
                server = await loop.create_server(
                    protocol_factory, host="127.0.0.1", port=0
                )
                local_port = server.sockets[0].getsockname()[1]
                forwarder = PrivilegedForwarder(port_number, local_port)
                await forwarder.start()
            else:
                # Dual-stack: bind IPv4 and IPv6 on the requested port.
                try:
                    server = await loop.create_server(
                        protocol_factory, host=None, port=port_number
                    )
                except OSError:
                    server = await loop.create_server(
                        protocol_factory, host="0.0.0.0", port=port_number
                    )
        except Exception:
            if server is not None:
                server.close()
                await server.wait_closed()
            if forwarder is not None:
                await forwarder.stop()
            await runner.cleanup()
            raise

        self._runner = runner
        self._server = server
        self._forwarder = forwarder
        self.port = port_number
        self.public_ip = ""
        self.hits.clear()
        template = self.current_template
        logger.info(
            f"IP logger listening on port {port_number}"
            + (f" (site: {template.label})" if template else "")
        )
        return {
            "port": port_number,
            "urls": self.urls(),
            "template": template.label if template else "",
            "elevated": elevated,
            "beacon": beacon_path,
        }

    async def stop(self) -> None:
        runner = self._runner
        server = self._server
        forwarder = self._forwarder
        self._runner = None
        self._server = None
        self._forwarder = None
        self.port = None
        self.public_ip = ""

        if server is not None:
            server.close()
            await server.wait_closed()

        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if forwarder is not None:
            await forwarder.stop()
        if runner is not None:
            await runner.cleanup()

    async def _handle_page(self, request: web.Request) -> web.Response:
        template = self.current_template
        path = request.path.lstrip("/")
        target: Path | None = None

        if not path:
            target = template.path if template else None
        elif template is not None:
            try:
                candidate = (template.path.parent / unquote(path)).resolve()
                candidate.relative_to(template.path.parent.resolve())
            except (ValueError, OSError):
                candidate = None
            if candidate is not None and candidate.is_file():
                target = candidate

        if target is None or not target.is_file():
            suffix = Path(path).suffix.lower()
            if suffix and suffix not in HTML_SUFFIXES:
                return web.Response(status=404, text="Not found")
            target = template.path if template else None

        is_page = target is None or target.suffix.lower() in HTML_SUFFIXES
        if not is_page:
            return web.FileResponse(target, headers={"Cache-Control": "no-store"})

        view_id = secrets.token_urlsafe(8)
        self._record_hit(request, view_id=view_id, page_path="/" + path)
        try:
            source = target.read_text(encoding="utf-8") if target else FALLBACK_HTML
        except OSError:
            source = FALLBACK_HTML
        beacon_src = f"{BEACON_PREFIX}{self._beacon_token}/pixel.gif?v={view_id}"
        return web.Response(
            text=inject_tracker(source, beacon_src),
            content_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    async def _handle_beacon(self, request: web.Request) -> web.Response:
        view_id = request.query.get("v", "")
        meta = self._decode_meta(request.query.get("e", ""))
        hit: dict[str, Any] | None = None
        if view_id:
            hit = next(
                (
                    item
                    for item in reversed(self.hits[-100:])
                    if item.get("view_id") == view_id
                ),
                None,
            )
        if hit is not None:
            hit.update(meta)
            self._notify(hit)
        else:
            self._record_hit(request, view_id=view_id, extras=meta)
        return web.Response(
            body=PIXEL,
            content_type="image/gif",
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    def _record_hit(
        self,
        request: web.Request,
        view_id: str = "",
        page_path: str = "",
        extras: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client_ip, ip_source = self._resolve_client(request)
        hit: dict[str, Any] = {
            "time": datetime.now(UTC).isoformat(timespec="seconds"),
            "ip": client_ip,
            "ip_source": ip_source,
            "method": request.method,
            "path": page_path or request.path,
            "page_path": page_path or request.path,
            "host": request.headers.get("Host", ""),
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
            "language": request.headers.get("Accept-Language", ""),
            "x_forwarded_for": request.headers.get("X-Forwarded-For", ""),
            "x_real_ip": request.headers.get("X-Real-IP", ""),
            "forwarded": request.headers.get("Forwarded", ""),
            "view_id": view_id,
        }
        if extras:
            hit.update(extras)
        self.hits.append(hit)
        self._notify(hit)

        task = asyncio.create_task(self._enrich(hit))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return hit

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
