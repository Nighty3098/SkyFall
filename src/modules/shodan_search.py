"""Shodan API client used by the Shodan tab and the graph transforms.

The module is a thin, asynchronous wrapper around the official ``shodan``
package.  Every public method returns plain JSON-serialisable data so the same
result can be rendered in the UI, added to a graph, or returned by the MCP
server.  API errors are reported as ``{"error": "..."}`` instead of raising so
the UI can show them without special-case exception handling.
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

try:  # pragma: no cover - exercised indirectly through the UI
    import shodan as shodan_sdk
except ImportError:  # pragma: no cover - requirements.txt installs it
    shodan_sdk = None


class ShodanError(RuntimeError):
    """Raised for local configuration problems."""


class ShodanSearch:
    """Asynchronous wrapper around :class:`shodan.Shodan`."""

    def __init__(self, api_key: str = "", proxy: str | None = None):
        logger.debug("Init: ShodanSearch")
        self.api_key = (api_key or "").strip()
        self.proxy = (proxy or "").strip() or None
        self._client = None
        self._client_key = None
        self._client_proxy = None

    # ── Configuration ────────────────────────────────────────────

    def configured(self) -> bool:
        return bool(self.api_key)

    def set_api_key(self, api_key: str) -> None:
        api_key = (api_key or "").strip()
        if api_key != self.api_key:
            self.api_key = api_key
            self._client = None
            self._client_key = None

    def set_proxy(self, proxy: str | None) -> None:
        proxy = (proxy or "").strip() or None
        if proxy != self.proxy:
            self.proxy = proxy
            self._client = None
            self._client_proxy = None

    def _get_client(self):
        if shodan_sdk is None:
            raise ShodanError(
                "The 'shodan' package is not installed. "
                "Run pip install -r requirements.txt."
            )
        if not self.api_key:
            raise ShodanError("Shodan API key is not configured (Settings → SHODAN).")

        if (
            self._client is None
            or self._client_key != self.api_key
            or self._client_proxy != self.proxy
        ):
            proxies = None
            if self.proxy:
                proxies = {"http": self.proxy, "https": self.proxy}
            try:
                self._client = shodan_sdk.Shodan(self.api_key, proxies=proxies)
            except TypeError:  # pragma: no cover - older shodan releases
                self._client = shodan_sdk.Shodan(self.api_key)
            self._client_key = self.api_key
            self._client_proxy = self.proxy
        return self._client

    # ── Request plumbing ─────────────────────────────────────────

    def _call(self, action) -> Any:
        try:
            return action(self._get_client())
        except ShodanError as exc:
            return {"error": str(exc)}
        except Exception as exc:  # noqa: BLE001 - API failures belong in the UI
            logger.warning(f"Shodan request failed: {exc}")
            message = str(exc).strip() or exc.__class__.__name__
            return {"error": f"Shodan API error: {message}"}

    async def _async_call(self, action) -> Any:
        return await asyncio.to_thread(self._call, action)

    @staticmethod
    def _error(data: Any) -> str:
        return str(data.get("error", "")) if isinstance(data, dict) else ""

    @staticmethod
    def _wrap(key: str, data: Any) -> dict:
        if isinstance(data, dict) and data.get("error"):
            return data
        return {key: data}

    # ── Account / API ────────────────────────────────────────────

    async def info(self) -> dict:
        """Return the API plan, credits and query limits."""
        return await self._async_call(lambda client: client.info())

    async def my_ip(self) -> dict:
        """Return the public IP address as seen by Shodan."""
        data = await self._async_call(lambda client: client.tools.myip())
        return self._wrap("ip", data)

    async def ports(self) -> dict:
        data = await self._async_call(lambda client: client.ports())
        return self._wrap("ports", data)

    async def protocols(self) -> dict:
        data = await self._async_call(lambda client: client.protocols())
        return self._wrap("protocols", data)

    async def services(self) -> dict:
        data = await self._async_call(lambda client: client.services())
        return self._wrap("services", data)

    async def search_facets(self) -> dict:
        data = await self._async_call(lambda client: client.search_facets())
        return self._wrap("facets", data)

    async def search_filters(self) -> dict:
        data = await self._async_call(lambda client: client.search_filters())
        return self._wrap("filters", data)

    async def search_tokens(self, query: str) -> dict:
        data = await self._async_call(lambda client: client.search_tokens(query))
        return self._wrap("tokens", data)

    # ── Hosts / search ───────────────────────────────────────────

    async def host(self, ip: str, history: bool = False, minify: bool = False) -> dict:
        data = await self._async_call(
            lambda client: client.host(ip, history=history, minify=minify)
        )
        return data if isinstance(data, dict) else self._wrap("host", data)

    async def search(
        self,
        query: str,
        page: int = 1,
        limit: int | None = None,
        facets: str | list[str] | None = None,
        minify: bool = True,
        fields: str | list[str] | None = None,
    ) -> dict:
        kwargs: dict[str, Any] = {
            "page": max(1, int(page or 1)),
            "minify": minify,
        }
        if limit is not None:
            kwargs["limit"] = max(1, int(limit))
        if facets:
            kwargs["facets"] = facets
        if fields:
            kwargs["fields"] = fields
        data = await self._async_call(lambda client: client.search(query, **kwargs))
        return data if isinstance(data, dict) else self._wrap("matches", data)

    async def count(self, query: str, facets: str | None = None) -> dict:
        data = await self._async_call(lambda client: client.count(query, facets=facets))
        return data if isinstance(data, dict) else self._wrap("total", data)

    async def queries(
        self, page: int = 1, sort: str = "timestamp", order: str = "desc"
    ) -> dict:
        data = await self._async_call(
            lambda client: client.queries(
                page=max(1, int(page or 1)), sort=sort, order=order
            )
        )
        return data if isinstance(data, dict) else self._wrap("matches", data)

    # ── DNS / intelligence ───────────────────────────────────────

    async def domain_info(
        self,
        domain: str,
        history: bool = False,
        record_type: str | None = None,
        page: int = 1,
    ) -> dict:
        def action(client):
            return client.dns.domain_info(
                domain,
                history=history,
                type=record_type,
                page=max(1, int(page or 1)),
            )

        data = await self._async_call(action)
        return data if isinstance(data, dict) else self._wrap("data", data)

    async def honeyscore(self, ip: str) -> dict:
        data = await self._async_call(lambda client: client.labs.honeyscore(ip))
        if isinstance(data, dict) and data.get("error"):
            return data
        return {"ip": ip, "honeyscore": data}

    async def exploits(
        self, query: str, page: int = 1, facets: str | None = None
    ) -> dict:
        def action(client):
            return client.exploits.search(
                query, page=max(1, int(page or 1)), facets=facets
            )

        data = await self._async_call(action)
        return data if isinstance(data, dict) else self._wrap("matches", data)

    async def exploits_count(self, query: str, facets: str | None = None) -> dict:
        data = await self._async_call(
            lambda client: client.exploits.count(query, facets=facets)
        )
        return data if isinstance(data, dict) else self._wrap("total", data)

    # ── On-demand scans ──────────────────────────────────────────

    async def scan(self, ips: str, force: bool = False) -> dict:
        data = await self._async_call(lambda client: client.scan(ips, force=force))
        return data if isinstance(data, dict) else self._wrap("scan", data)

    async def scan_status(self, scan_id: str) -> dict:
        data = await self._async_call(lambda client: client.scan_status(scan_id))
        return data if isinstance(data, dict) else self._wrap("scan", data)

    async def scans(self, page: int = 1) -> dict:
        data = await self._async_call(
            lambda client: client.scans(page=max(1, int(page or 1)))
        )
        return data if isinstance(data, dict) else self._wrap("matches", data)

    # ── Alerts ───────────────────────────────────────────────────

    async def alerts(
        self, alert_id: str | None = None, include_expired: bool = True
    ) -> dict:
        data = await self._async_call(
            lambda client: client.alerts(alert_id, include_expired=include_expired)
        )
        return data if isinstance(data, dict) else self._wrap("matches", data)

    async def create_alert(self, name: str, ip: str, expires: int = 0) -> dict:
        data = await self._async_call(
            lambda client: client.create_alert(name, ip, expires=expires)
        )
        return data if isinstance(data, dict) else self._wrap("alert", data)

    async def delete_alert(self, alert_id: str) -> dict:
        data = await self._async_call(lambda client: client.delete_alert(alert_id))
        if data is None:
            return {"deleted": alert_id}
        return data if isinstance(data, dict) else self._wrap("alert", data)

    async def edit_alert(self, alert_id: str, ip: str) -> dict:
        data = await self._async_call(lambda client: client.edit_alert(alert_id, ip))
        if data is None:
            return {"updated": alert_id, "ip": ip}
        return data if isinstance(data, dict) else self._wrap("alert", data)

    async def alert_triggers(self) -> dict:
        data = await self._async_call(lambda client: client.alert_triggers())
        return self._wrap("triggers", data)

    async def add_alert_notifier(self, alert_id: str, notifier_id: str) -> dict:
        data = await self._async_call(
            lambda client: client.add_alert_notifier(alert_id, notifier_id)
        )
        if data is None:
            return {"alert": alert_id, "notifier": notifier_id, "added": True}
        return data if isinstance(data, dict) else self._wrap("alert", data)

    async def remove_alert_notifier(self, alert_id: str, notifier_id: str) -> dict:
        data = await self._async_call(
            lambda client: client.remove_alert_notifier(alert_id, notifier_id)
        )
        if data is None:
            return {"alert": alert_id, "notifier": notifier_id, "removed": True}
        return data if isinstance(data, dict) else self._wrap("alert", data)
