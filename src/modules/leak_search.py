"""Leak and infostealer search for emails, usernames and domains.

Sources:

* **Hudson Rock Cavalier** — free infostealer-log intelligence, no API key
  (search by email, username or domain).
* **LeakCheck** — public endpoint needs no key (aggregated hit counter);
  the API v2 endpoint is used when an API key is configured.
* **Dehashed** — requires an API key (email + key, HTTP basic auth).
* **Have I Been Pwned** — requires an API key.

Every provider is best-effort: missing keys or network errors degrade to a
descriptive message instead of raising.
"""

import re

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

TIMEOUT = 25.0
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0"

HUDSON_BASE = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools"
LEAKCHECK_PUBLIC = "https://leakcheck.io/api/public"
LEAKCHECK_V2 = "https://leakcheck.io/api/v2/query"
DEHASHED_API = "https://api.dehashed.com/search"
HIBP_API = "https://haveibeenpwned.com/api/v3"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_DOMAIN_RE = re.compile(r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}")


def classify_target(target: str) -> str:
    """Return ``email``, ``domain`` or ``username`` for a raw target."""
    target = (target or "").strip()
    if _EMAIL_RE.fullmatch(target):
        return "email"
    if _DOMAIN_RE.fullmatch(target):
        return "domain"
    return "username"


class LeakSearch:
    """Search leaks and infostealer logs for a target."""

    def __init__(self, timeout: float = TIMEOUT):
        logger.debug("Init: LeakSearch")
        self.timeout = timeout
        self.keys: dict = {}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
        )

    # ── Hudson Rock (infostealers, no key) ────────────────────────

    async def infostealer(self, target: str, kind: str | None = None) -> dict:
        target = (target or "").strip()
        kind = kind or classify_target(target)
        if not target:
            return {"error": "Empty target"}
        if kind == "email":
            endpoint, param = "search-by-email", "email"
        elif kind == "domain":
            endpoint, param = "search-by-domain", "domain"
        else:
            endpoint, param = "search-by-username", "username"

        async with self._client() as client:
            try:
                resp = await client.get(
                    f"{HUDSON_BASE}/{endpoint}", params={param: target}
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.debug(f"Hudson Rock error: {exc}")
                return {"error": str(exc), "target": target, "kind": kind}

        data["target"] = target
        data["kind"] = kind
        return data

    # ── LeakCheck ─────────────────────────────────────────────────

    async def leakcheck(self, target: str, api_key: str = "") -> dict:
        target = (target or "").strip()
        if not target:
            return {"error": "Empty target"}
        async with self._client() as client:
            try:
                if api_key:
                    resp = await client.get(
                        f"{LEAKCHECK_V2}/{target}",
                        headers={"X-API-Key": api_key},
                    )
                else:
                    resp = await client.get(LEAKCHECK_PUBLIC, params={"check": target})
                if resp.status_code == 401:
                    return {"error": "Invalid LeakCheck API key", "target": target}
                if resp.status_code == 429:
                    return {"error": "LeakCheck rate limit reached", "target": target}
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.debug(f"LeakCheck error: {exc}")
                return {"error": str(exc), "target": target}
        data["target"] = target
        data["engine"] = "api-v2" if api_key else "public"
        return data

    # ── Dehashed (key) ────────────────────────────────────────────

    async def dehashed(self, target: str, email: str = "", api_key: str = "") -> dict:
        target = (target or "").strip()
        if not api_key or not email:
            return {"error": "Dehashed key not configured", "target": target}
        async with self._client() as client:
            try:
                resp = await client.get(
                    DEHASHED_API,
                    params={"query": f'"{target}"'},
                    auth=(email, api_key),
                )
                if resp.status_code in (401, 403):
                    return {"error": "Dehashed auth failed", "target": target}
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.debug(f"Dehashed error: {exc}")
                return {"error": str(exc), "target": target}
        data["target"] = target
        return data

    # ── Have I Been Pwned (key) ───────────────────────────────────

    async def hibp(self, email: str, api_key: str = "") -> dict:
        email = (email or "").strip()
        if not api_key:
            return {"error": "HIBP key not configured", "email": email}
        async with self._client() as client:
            try:
                resp = await client.get(
                    f"{HIBP_API}/breachedaccount/{email}",
                    params={"truncateResponse": "false"},
                    headers={"hibp-api-key": api_key},
                )
                if resp.status_code == 404:
                    return {"email": email, "breaches": [], "found": 0}
                if resp.status_code == 401:
                    return {"error": "Invalid HIBP key", "email": email}
                resp.raise_for_status()
                breaches = resp.json()
            except Exception as exc:
                logger.debug(f"HIBP error: {exc}")
                return {"error": str(exc), "email": email}
        return {"email": email, "breaches": breaches, "found": len(breaches)}

    # ── Aggregation ───────────────────────────────────────────────

    async def search_all(self, target: str, keys: dict | None = None) -> dict:
        keys = keys or self.keys
        kind = classify_target(target)
        result: dict = {"target": target, "kind": kind}
        result["infostealer"] = await self.infostealer(target, kind)
        result["leakcheck"] = await self.leakcheck(
            target, keys.get("leakcheck_api_key", "")
        )
        if kind == "email":
            result["hibp"] = await self.hibp(target, keys.get("hibp_api_key", ""))
        if keys.get("dehashed_api_key"):
            result["dehashed"] = await self.dehashed(
                target,
                keys.get("dehashed_email", ""),
                keys.get("dehashed_api_key", ""),
            )
        return result

    # ── Text rendering ────────────────────────────────────────────

    @staticmethod
    def _render_infostealer(data: dict) -> list[str]:
        lines = [section("Infostealer logs (Hudson Rock)")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
            return lines
        if data.get("kind") == "domain":
            lines.append(kv("Total records", data.get("total", 0)))
            lines.append(kv("Infected users", data.get("users", 0)))
            lines.append(kv("Infected employees", data.get("employees", 0)))
            for rec in (data.get("data") or [])[:10]:
                label = rec.get("name") or rec.get("username") or rec.get("email", "?")
                count = rec.get("stealerFamilies") or rec.get("total", "")
                lines.append(bullet(f"{label}: {count}"))
            return lines
        stealers = data.get("stealers") or []
        if not stealers:
            lines.append(info("No infostealer logs found"))
            return lines
        lines.append(kv("Infected machines", len(stealers)))
        lines.append(kv("Corporate services", data.get("total_corporate_services", 0)))
        lines.append(kv("User services", data.get("total_user_services", 0)))
        for s in stealers[:10]:
            comp = s.get("computer_name") or "?"
            date = (s.get("date_compromised") or "?")[:10]
            lines.append(bullet(f"{date} - {comp} ({s.get('operating_system', '?')})"))
        return lines

    @staticmethod
    def _render_leakcheck(data: dict) -> list[str]:
        lines = [section("LeakCheck")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
            return lines
        lines.append(kv("Engine", data.get("engine", "public")))
        lines.append(kv("Records found", data.get("found", 0)))
        sources = data.get("sources") or []
        if sources:
            names = ", ".join(str(s.get("name", "?")) for s in sources[:8])
            lines.append(kv("Sources", names))
        fields = data.get("fields")
        if fields:
            if isinstance(fields, dict):
                fields = list(fields.keys())
            lines.append(kv("Exposed fields", ", ".join(map(str, fields[:15]))))
        return lines

    @staticmethod
    def _render_hibp(data: dict) -> list[str]:
        lines = [section("Have I Been Pwned")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
            return lines
        breaches = data.get("breaches") or []
        lines.append(kv("Breaches", len(breaches)))
        for b in breaches[:10]:
            lines.append(bullet(f"{b.get('Name', '?')} ({b.get('BreachDate', '?')})"))
        return lines

    @staticmethod
    def _render_dehashed(data: dict) -> list[str]:
        lines = [section("Dehashed")]
        if data.get("error"):
            lines.append(info(f"Unavailable: {data['error']}"))
            return lines
        lines.append(kv("Total entries", data.get("total", 0)))
        for e in (data.get("entries") or [])[:8]:
            ident = e.get("email") or e.get("username") or e.get("name", "?")
            lines.append(bullet(f"{ident} @ {e.get('database_name', '?')}"))
        return lines

    async def check(self, target: str, keys: dict | None = None) -> str:
        target = (target or "").strip()
        if not target:
            return error("Empty target")

        data = await self.search_all(target, keys)
        lines = [title(f"Leak / infostealer search: {target}")]
        lines.append(info(f"Target type: {data['kind']}"))
        lines += self._render_infostealer(data.get("infostealer", {}))
        lines += self._render_leakcheck(data.get("leakcheck", {}))
        if "hibp" in data:
            lines += self._render_hibp(data["hibp"])
        if "dehashed" in data:
            lines += self._render_dehashed(data["dehashed"])
        lines.append(end_of("leak search"))
        lines.append(divider())
        return "\n".join(lines)
