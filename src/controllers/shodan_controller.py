from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QPointF

from src.ui.output_formatter import error, render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.shodan_search import ShodanSearch


class ShodanController:
    """UI controller for the Shodan tab."""

    def __init__(
        self,
        ui: "QMainWindow",
        shodan_search: "ShodanSearch",
        graph_widget=None,
    ):
        logger.debug("Init: ShodanController")
        self.ui = ui
        self.shodan_search = shodan_search
        self.graph_widget = graph_widget
        self._last_result: tuple[str, str, dict] | None = None

    # ── Output helpers ───────────────────────────────────────────

    def _start(self) -> None:
        self.ui.shodanDebug.clear()
        self.ui.shodanProgress.setValue(0)
        self.ui.shodanProgress.setRange(0, 0)

    def _finish(self) -> None:
        self.ui.shodanProgress.setRange(0, 100)
        self.ui.shodanProgress.setValue(100)

    def _render(self, data, title: str) -> None:
        if isinstance(data, dict) and data.get("error"):
            self.ui.shodanDebug.setPlainText(error(data["error"]))
            return
        self.ui.shodanDebug.setPlainText(render(data, title=title))

    def _target(self, widget_name: str = "shodanTargetEdit") -> str:
        widget = getattr(self.ui, widget_name, None)
        return widget.text().strip() if widget is not None else ""

    def _page(self) -> int:
        widget = getattr(self.ui, "shodanPageSpin", None)
        return widget.value() if widget is not None else 1

    async def _run(self, action, title: str) -> None:
        self._start()
        try:
            data = await action()
            self._render(data, title)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            logger.exception("Shodan action failed")
            self.ui.shodanDebug.setPlainText(error(f"Error: {exc}"))
        finally:
            self._finish()

    def _remember(self, kind: str, target: str, data) -> None:
        if isinstance(data, dict) and not data.get("error"):
            self._last_result = (kind, target, data)

    # ── Lookup / search actions ──────────────────────────────────

    async def host_lookup(self) -> None:
        target = self._target()
        if not target:
            self.ui.shodanDebug.setPlainText(error("Enter an IP address or hostname"))
            return

        async def action():
            self._last_result = None
            data = await self.shodan_search.host(target)
            self._remember("host", target, data)
            return data

        await self._run(action, f"Shodan host: {target}")

    async def search(self) -> None:
        query = self._target()
        if not query:
            self.ui.shodanDebug.setPlainText(error("Enter a Shodan search query"))
            return

        async def action():
            self._last_result = None
            data = await self.shodan_search.search(query, page=self._page())
            self._remember("search", query, data)
            return data

        await self._run(action, f"Shodan search: {query}")

    async def count(self) -> None:
        query = self._target()
        if not query:
            self.ui.shodanDebug.setPlainText(error("Enter a Shodan search query"))
            return

        await self._run(
            lambda: self.shodan_search.count(query),
            f"Shodan count: {query}",
        )

    async def facets(self) -> None:
        await self._run(
            self.shodan_search.search_facets,
            "Shodan search facets",
        )

    async def community_queries(self) -> None:
        async def action():
            return await self.shodan_search.queries(page=self._page())

        await self._run(action, "Shodan community queries")

    # ── DNS / intelligence ───────────────────────────────────────

    async def domain_info(self) -> None:
        domain = self._target("shodanDomainEdit")
        if not domain:
            self.ui.shodanDebug.setPlainText(error("Enter a domain name"))
            return

        async def action():
            self._last_result = None
            data = await self.shodan_search.domain_info(domain, page=self._page())
            self._remember("dns", domain, data)
            return data

        await self._run(action, f"Shodan DNS: {domain}")

    async def honeyscore(self) -> None:
        target = self._target()
        if not target:
            self.ui.shodanDebug.setPlainText(error("Enter an IP address"))
            return

        async def action():
            self._last_result = None
            data = await self.shodan_search.honeyscore(target)
            self._remember("honeyscore", target, data)
            return data

        await self._run(action, f"Honeyscore: {target}")

    async def exploits(self) -> None:
        query = self._target("shodanExploitEdit")
        if not query:
            self.ui.shodanDebug.setPlainText(error("Enter an exploit search query"))
            return

        async def action():
            self._last_result = None
            data = await self.shodan_search.exploits(query, page=self._page())
            self._remember("exploits", query, data)
            return data

        await self._run(action, f"Shodan exploits: {query}")

    # ── API utilities ────────────────────────────────────────────

    async def account_info(self) -> None:
        await self._run(self.shodan_search.info, "Shodan account")

    async def my_ip(self) -> None:
        await self._run(self.shodan_search.my_ip, "Shodan: my IP")

    async def catalog(self) -> None:
        async def action():
            data = await self.shodan_search.services()
            if isinstance(data, dict) and data.get("error"):
                return data
            ports = await self.shodan_search.ports()
            protocols = await self.shodan_search.protocols()
            return {
                "services": data.get("services", data),
                "ports": ports.get("ports", ports),
                "protocols": protocols.get("protocols", protocols),
            }

        await self._run(action, "Shodan catalog")

    # ── Scans / alerts ───────────────────────────────────────────

    async def request_scan(self) -> None:
        target = self._target()
        if not target:
            self.ui.shodanDebug.setPlainText(error("Enter an IP address or network"))
            return

        await self._run(
            lambda: self.shodan_search.scan(target),
            f"Shodan scan requested: {target}",
        )

    async def scan_status(self) -> None:
        scan_id = self._target("shodanScanIdEdit")
        if not scan_id:
            self.ui.shodanDebug.setPlainText(error("Enter a scan ID"))
            return

        await self._run(
            lambda: self.shodan_search.scan_status(scan_id),
            f"Shodan scan: {scan_id}",
        )

    async def create_alert(self) -> None:
        name = self._target("shodanAlertNameEdit")
        network = self._target("shodanAlertIpEdit")
        if not name or not network:
            self.ui.shodanDebug.setPlainText(
                error("Enter an alert name and an IP or network")
            )
            return

        await self._run(
            lambda: self.shodan_search.create_alert(name, network),
            f"Shodan alert created: {name}",
        )

    async def list_alerts(self) -> None:
        await self._run(self.shodan_search.alerts, "Shodan alerts")

    async def delete_alert(self) -> None:
        alert_id = self._target("shodanAlertIdEdit")
        if not alert_id:
            self.ui.shodanDebug.setPlainText(error("Enter an alert ID"))
            return

        await self._run(
            lambda: self.shodan_search.delete_alert(alert_id),
            f"Shodan alert deleted: {alert_id}",
        )

    # ── Graph integration ────────────────────────────────────────

    async def send_to_graph(self) -> None:
        if self._last_result is None:
            self.ui.shodanDebug.setPlainText(
                error("Run a host, search, DNS or exploit query first")
            )
            return
        if self.graph_widget is None:
            self.ui.shodanDebug.setPlainText(error("Graph widget is not available"))
            return

        kind, target, data = self._last_result
        anchor_type, children = self._graph_payload(kind, target, data)
        graph = self.graph_widget
        scene_pos = graph.mapToScene(graph.viewport().rect().center())

        begin = getattr(graph, "begin_bulk_edit", None)
        end = getattr(graph, "end_bulk_edit", None)
        if callable(begin):
            begin()
        created = []
        try:
            root = graph.add_node(scene_pos, anchor_type)
            root.title = target
            root.content = f"Shodan {kind}: {target}"
            root.update()
            created.append(root)

            for index, child in enumerate(children):
                offset = QPointF(260, (index - len(children) / 2) * 90)
                node = graph.add_node(scene_pos + offset, child["entity_type"])
                node.title = child["title"]
                node.content = child.get("content", "")
                node.evidence = list(child.get("evidence", []))
                node.update()
                graph.add_edge(
                    root,
                    node,
                    source_port="right",
                    target_port="left",
                )
                created.append(node)
        finally:
            if callable(end):
                end()

        scene = graph.scene()
        if scene is not None:
            scene.clearSelection()
        for node in created:
            node.setSelected(True)
        if hasattr(graph, "fit_selection"):
            graph.fit_selection()
        graph.status_message(
            f"Shodan → graph: {len(created) - 1} node"
            f"{'s' if len(created) - 1 != 1 else ''}"
        )
        self.ui.shodanDebug.appendPlainText(
            f"\nSent {len(created) - 1} related node(s) to the graph."
        )

    @staticmethod
    def _graph_payload(kind: str, target: str, data: dict):
        if kind == "host":
            return "IP", ShodanController._host_children(data)
        if kind == "dns":
            return "Domain", ShodanController._dns_children(data)
        if kind == "search":
            return "Custom", ShodanController._search_children(data)
        if kind == "exploits":
            return "Custom", ShodanController._exploit_children(data)
        if kind == "honeyscore":
            score = data.get("honeyscore", "?")
            return "IP", [
                {
                    "entity_type": "Custom",
                    "title": f"Honeyscore: {score}",
                    "content": f"Honeyscore for {target}: {score}",
                }
            ]
        return "Custom", []

    @staticmethod
    def _host_children(data: dict) -> list[dict]:
        children = []
        org = data.get("org") or data.get("isp")
        if org:
            children.append(
                {
                    "entity_type": "Organization",
                    "title": str(org)[:60],
                    "content": (
                        f"ISP: {data.get('isp', '?')}\nASN: {data.get('asn', '?')}"
                    ),
                }
            )
        lat, lon = data.get("latitude"), data.get("longitude")
        if lat is not None and lon is not None:
            children.append(
                {
                    "entity_type": "Geolocation",
                    "title": f"{float(lat):.2f}, {float(lon):.2f}",
                    "content": f"City: {data.get('city', '?')}\n"
                    f"Country: {data.get('country_name', '?')}",
                }
            )
        for hostname in (data.get("hostnames") or [])[:5]:
            children.append(
                {
                    "entity_type": "Domain",
                    "title": str(hostname),
                    "content": "Hostname reported by Shodan",
                }
            )
        for record in (data.get("data") or [])[:10]:
            port = record.get("port", "?")
            transport = record.get("transport", "tcp")
            children.append(
                {
                    "entity_type": "Custom",
                    "title": f"Port {port}/{transport}",
                    "content": "\n".join(
                        part
                        for part in (
                            f"Product: {record.get('product', '?')}",
                            f"Version: {record.get('version', '?')}",
                            f"Module: {record.get('_shodan', {}).get('module', '?')}",
                            str(record.get("banner", ""))[:300],
                        )
                        if part
                    ),
                }
            )
        for cve in list((data.get("vulns") or {}).keys())[:8]:
            children.append(
                {
                    "entity_type": "Custom",
                    "title": str(cve),
                    "content": (
                        f"Vulnerability reported by Shodan for {data.get('ip', 'host')}"
                    ),
                }
            )
        return children

    @staticmethod
    def _dns_children(data: dict) -> list[dict]:
        children = []
        seen = set()
        domain = data.get("domain", "")
        for record in (data.get("data") or [])[:20]:
            subdomain = str(record.get("subdomain", "")).strip()
            if not subdomain:
                continue
            full = (
                subdomain
                if subdomain.endswith(f".{domain}")
                else (f"{subdomain}.{domain}")
            )
            if full in seen:
                continue
            seen.add(full)
            children.append(
                {
                    "entity_type": "Domain",
                    "title": full,
                    "content": f"Record: {record.get('type', '?')} → "
                    f"{record.get('value', '?')}\n"
                    f"Last seen: {record.get('last_seen', '?')}",
                }
            )
        return children

    @staticmethod
    def _search_children(data: dict) -> list[dict]:
        children = []
        for match in (data.get("matches") or [])[:15]:
            ip = match.get("ip_str", "?")
            port = match.get("port", "?")
            hostnames = match.get("hostnames") or []
            title = hostnames[0] if hostnames else f"{ip}:{port}"
            children.append(
                {
                    "entity_type": "IP",
                    "title": f"{ip}:{port}",
                    "content": "\n".join(
                        part
                        for part in (
                            f"Hostname: {title}",
                            f"Organization: {match.get('org', '?')}",
                            f"Product: {match.get('product', '?')}",
                            f"Location: {match.get('location', {}).get('city', '?')}, "
                            f"{match.get('location', {}).get('country_name', '?')}",
                        )
                        if part
                    ),
                    "evidence": [f"https://www.shodan.io/host/{ip}"],
                }
            )
        return children

    @staticmethod
    def _exploit_children(data: dict) -> list[dict]:
        children = []
        for match in (data.get("matches") or [])[:15]:
            title = (
                match.get("cve") or match.get("source") or match.get("_id") or "Exploit"
            )
            children.append(
                {
                    "entity_type": "Custom",
                    "title": str(title)[:70],
                    "content": str(match.get("description", ""))[:500],
                    "evidence": [str(match.get("source", ""))],
                }
            )
        return children
