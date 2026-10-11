"""Web archive / evidence capture helpers.

* **Wayback Machine** — closest/oldest/newest snapshot via the fast
  availability API, full snapshot listing via the CDX server and on-demand
  saving through ``waybackpy``.
* **archive.today** — check whether a URL is already archived.

Network providers are best-effort: errors are reported, never raised.
"""

import asyncio

import httpx
from loguru import logger

from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    error,
    info,
    kv,
    section,
    title,
)

TIMEOUT = 20.0
SAVE_TIMEOUT = 120.0
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0"

AVAILABILITY_API = "http://archive.org/wayback/available"
ARCHIVE_TODAY = "https://archive.ph/newest"


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


class ArchiveSearch:
    """Query and populate web archives (Wayback Machine, archive.today)."""

    def __init__(self, timeout: float = TIMEOUT):
        logger.debug("Init: ArchiveSearch")
        self.timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    # ── Wayback availability (fast) ───────────────────────────────

    async def availability(self, url: str, timestamp: str = "") -> dict:
        url = normalize_url(url)
        if not url:
            return {"error": "Empty URL"}
        # The availability API matches the stored URL closely, so try the
        # scheme-less form as well when the first lookup has no snapshot.
        without_scheme = url.split("://", 1)[-1]
        forms = [url] if url == without_scheme else [url, without_scheme]
        last: dict = {"url": url, "snapshot": {}}
        async with self._client() as client:
            for form in forms:
                params = {"url": form}
                if timestamp:
                    params["timestamp"] = timestamp
                try:
                    resp = await client.get(AVAILABILITY_API, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    logger.debug(f"Wayback availability error: {exc}")
                    return {"error": str(exc), "url": url}
                snap = (data.get("archived_snapshots") or {}).get("closest") or {}
                last = {
                    "url": url,
                    "timestamp_query": timestamp or "",
                    "snapshot": snap,
                }
                if snap:
                    return last
        return last

    # ── Wayback save (waybackpy) ──────────────────────────────────

    async def save(self, url: str) -> dict:
        url = normalize_url(url)
        if not url:
            return {"error": "Empty URL"}

        def _do_save() -> str:
            from waybackpy import WaybackMachineSaveAPI

            return WaybackMachineSaveAPI(url, max_tries=3).save()

        try:
            archive_url = await asyncio.wait_for(
                asyncio.to_thread(_do_save), timeout=SAVE_TIMEOUT
            )
        except Exception as exc:
            logger.debug(f"Wayback save error: {exc}")
            return {"error": str(exc), "url": url}
        return {"url": url, "archive_url": archive_url, "saved": True}

    # ── Wayback CDX snapshots (best-effort) ───────────────────────

    async def snapshots(self, url: str, limit: int = 20) -> dict:
        url = normalize_url(url)
        if not url:
            return {"error": "Empty URL"}

        def _do_list() -> list[dict]:
            from waybackpy import WaybackMachineCDXServerAPI

            cdx = WaybackMachineCDXServerAPI(url, max_tries=2)
            out = []
            for i, snap in enumerate(cdx.snapshots()):
                if i >= limit:
                    break
                out.append(
                    {
                        "url": snap.archive_url,
                        "timestamp": snap.timestamp,
                        "statuscode": getattr(snap, "statuscode", ""),
                    }
                )
            return out

        try:
            snaps = await asyncio.wait_for(
                asyncio.to_thread(_do_list), timeout=SAVE_TIMEOUT
            )
        except Exception as exc:
            logger.debug(f"Wayback CDX error: {exc}")
            return {"error": str(exc), "url": url}
        return {"url": url, "count": len(snaps), "snapshots": snaps}

    # ── archive.today ─────────────────────────────────────────────

    async def archive_today(self, url: str) -> dict:
        url = normalize_url(url)
        if not url:
            return {"error": "Empty URL"}
        async with self._client() as client:
            try:
                resp = await client.get(f"{ARCHIVE_TODAY}/{url}")
            except Exception as exc:
                logger.debug(f"archive.today error: {exc}")
                return {"error": str(exc), "url": url}
        found = resp.status_code == 200 and "archive.ph" in str(resp.url)
        return {
            "url": url,
            "found": found,
            "snapshot": str(resp.url) if found else "",
            "status": resp.status_code,
        }

    # ── Text rendering ────────────────────────────────────────────

    def render_availability(self, data: dict) -> str:
        lines = [title("Wayback Machine")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
            lines.append(divider())
            return "\n".join(lines)
        lines.append(kv("URL", data["url"]))
        snap = data.get("snapshot") or {}
        if snap:
            lines.append(kv("Snapshot", snap.get("url", "?")))
            lines.append(kv("Timestamp", snap.get("timestamp", "?")))
            lines.append(kv("Status", snap.get("status", "?")))
            lines.append(kv("Available", snap.get("available", False)))
        else:
            lines.append(info("No snapshot found"))
        lines.append(divider())
        return "\n".join(lines)

    def render_save(self, data: dict) -> str:
        lines = [title("Wayback save")]
        if data.get("error"):
            lines.append(info(f"Save failed: {data['error']}"))
        else:
            lines.append(kv("Archived", data.get("archive_url", "?")))
        lines.append(divider())
        return "\n".join(lines)

    def render_snapshots(self, data: dict) -> str:
        lines = [title("Wayback snapshots")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
            lines.append(divider())
            return "\n".join(lines)
        lines.append(kv("Snapshots", data.get("count", 0)))
        for s in (data.get("snapshots") or [])[:30]:
            lines.append(
                bullet(f"{s['timestamp']} ({s.get('statuscode', '?')}) {s['url']}")
            )
        lines.append(divider())
        return "\n".join(lines)

    def render_archive_today(self, data: dict) -> str:
        lines = [title("archive.today")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
        elif data.get("found"):
            lines.append(kv("Snapshot", data.get("snapshot", "?")))
        else:
            lines.append(info(f"No snapshot (HTTP {data.get('status', '?')})"))
        lines.append(divider())
        return "\n".join(lines)

    def render_all(self, results: dict) -> str:
        lines = [title(f"Archive: {results.get('url', '')}")]
        lines.append(section("Wayback"))
        lines.append(self.render_availability(results.get("availability", {})).strip())
        lines.append(section("archive.today"))
        today = self.render_archive_today(results.get("archive_today", {})).strip()
        lines.append(today)
        lines.append(end_of("archive lookup"))
        return "\n".join(lines)

    async def check(self, url: str) -> str:
        url = normalize_url(url)
        if not url:
            return error("Empty URL")
        availability = await self.availability(url)
        archive_today = await self.archive_today(url)
        return self.render_all(
            {"url": url, "availability": availability, "archive_today": archive_today}
        )
