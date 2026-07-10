import asyncio
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF

from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    kv,
    section,
    title,
)
from src.ui.output_formatter import (
    info as fmt_info,
)

CHILD_THRESHOLD = 5

_PATTERNS: dict[str, re.Pattern] = {
    "Domain": re.compile(
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}"
    ),
    "IP": re.compile(
        r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"
    ),
    "Email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "Phone": re.compile(r"\+?\d[\d\s\-().]{6,}\d"),
    "MAC": re.compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}"),
    "Crypto": re.compile(r"(?:1|3|bc1|0x)[a-zA-Z0-9]{25,}"),
}


@dataclass
class TransformDef:
    name: str
    description: str
    input_types: list[str]
    output_type: str
    relationship: str
    handler: Callable | None = None


@dataclass
class ChildNodeDef:
    title: str
    entity_type: str = "Custom"
    content: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass
class TransformResult:
    children: list[ChildNodeDef] = field(default_factory=list)
    content: str = ""
    evidence: list[str] = field(default_factory=list)


class GraphTransformController:
    def __init__(self, graph_widget, modules):
        self._graph = graph_widget
        self._modules = modules
        self._registry = self._build_registry()

    def get_transforms(self, node):
        etype = node.entity_type
        return self._registry.get(etype, [])

    def execute(self, node, transform_def):
        asyncio.ensure_future(self._execute_async(node, transform_def))

    async def _execute_async(self, node, transform_def):
        title = (node.title or "").strip()
        content = (node.content or "").strip()
        etype = node.entity_type
        default_prefix = f"New {etype}"

        pattern = _PATTERNS.get(etype)
        if pattern:
            m = pattern.fullmatch(title) if title and title != default_prefix else None
            if m:
                input_value = m.group()
            else:
                m = pattern.search(content) if content else None
                if m:
                    input_value = m.group()
                else:
                    return
        else:
            if title and title != default_prefix:
                input_value = title
            elif content:
                input_value = content
            else:
                return

        result = await transform_def.handler(input_value, self._modules)

        children = list(result.children)
        if not children and result.content:
            children.append(
                ChildNodeDef(
                    title=result.content.split("\n")[0][:60],
                    entity_type=transform_def.output_type or "Custom",
                    content=result.content,
                )
            )

        child_nodes = []
        for cd in children:
            pos = node.pos() + QPointF(
                220 + len(child_nodes) * 80,
                -40 * len(children) + len(child_nodes) * 80,
            )
            child = self._graph.add_node(pos, cd.entity_type)
            child.title = cd.title
            child.content = cd.content
            child.evidence = cd.evidence
            child.update()
            child_nodes.append(child)

            self._graph.add_edge(node, child, source_port="right", target_port="left")
            if transform_def.relationship:
                for edge in child._edges:
                    if edge.target == child or edge.source == child:
                        edge.relationship_type = transform_def.relationship
                        edge.update()

        if child_nodes:
            self._layout_children(node, child_nodes)

    def _layout_children(self, parent, children):
        count = len(children)
        if count == 0:
            return

        node_w = 180
        spacing = 20

        if count == 1:
            radius = 200
            rad = math.radians(-80)
            x = parent.pos().x() + radius * math.cos(rad)
            y = parent.pos().y() + radius * math.sin(rad)
            children[0].setPos(x, y)
            return

        arc_deg = min(130 + count * 3, 270)
        half_arc = arc_deg / 2
        delta = math.radians(arc_deg / (count - 1))
        min_radius = (node_w + spacing) / (2 * math.sin(delta / 2))
        radius = max(min_radius, 200)

        for i, child in enumerate(children):
            frac = i / (count - 1)
            angle = math.radians(-half_arc + frac * arc_deg)
            x = parent.pos().x() + radius * math.cos(angle)
            y = parent.pos().y() + radius * math.sin(angle)
            child.setPos(x, y)

    def _build_registry(self):
        return {
            "Username": [
                TransformDef(
                    name="Search Social Networks",
                    description="Check 400+ sites for this username",
                    input_types=["Username"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_username_search,
                ),
                TransformDef(
                    name="Maigret Deep Search",
                    description="Deep search via Maigret (510 sites)",
                    input_types=["Username"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_maigret_search,
                ),
            ],
            "Domain": [
                TransformDef(
                    name="Resolve IP",
                    description="Resolve domain to IP and geolocation",
                    input_types=["Domain"],
                    output_type="IP",
                    relationship="resolved_to",
                    handler=_transform_domain_ip,
                ),
                TransformDef(
                    name="DNS Records",
                    description="A, MX, TXT, NS, CNAME, SOA records",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="hosted_by",
                    handler=_transform_domain_dns,
                ),
                TransformDef(
                    name="SSL/TLS Info",
                    description="SSL certificate and TLS version info",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="hosted_by",
                    handler=_transform_domain_ssl,
                ),
                TransformDef(
                    name="Web Stack",
                    description="Detect web server, WAF, CMS, tech stack",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="hosted_by",
                    handler=_transform_domain_webstack,
                ),
                TransformDef(
                    name="WHOIS Lookup",
                    description="Domain registration WHOIS data",
                    input_types=["Domain"],
                    output_type="Organization",
                    relationship="registered_at",
                    handler=_transform_domain_whois,
                ),
                TransformDef(
                    name="Subdomains",
                    description="Discover subdomains via DuckDuckGo",
                    input_types=["Domain"],
                    output_type="Domain",
                    relationship="hosted_by",
                    handler=_transform_domain_subdomains,
                ),
                TransformDef(
                    name="Certificate Transparency",
                    description="crt.sh certificate transparency logs",
                    input_types=["Domain"],
                    output_type="Domain",
                    relationship="associated_with",
                    handler=_transform_domain_ct,
                ),
                TransformDef(
                    name="Social Tags",
                    description="Open Graph and Twitter meta tags",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_domain_social,
                ),
                TransformDef(
                    name="Malware Check",
                    description="Check reputation via VirusTotal / Google Safe",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_domain_malware,
                ),
                TransformDef(
                    name="Security.txt",
                    description="Fetch security.txt from /.well-known/",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_domain_securitytxt,
                ),
                TransformDef(
                    name="Cookies",
                    description="Dump HTTP cookies from domain",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_domain_cookies,
                ),
                TransformDef(
                    name="Robots.txt",
                    description="Fetch robots.txt",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_domain_robots,
                ),
                TransformDef(
                    name="Port Scan",
                    description="Nmap port scan (1-65535)",
                    input_types=["Domain"],
                    output_type="Custom",
                    relationship="hosted_by",
                    handler=_transform_domain_nmap,
                ),
            ],
            "IP": [
                TransformDef(
                    name="Geolocation",
                    description="Look up IP geolocation",
                    input_types=["IP"],
                    output_type="Geolocation",
                    relationship="located_at",
                    handler=_transform_ip_geo,
                ),
                TransformDef(
                    name="Port Scan",
                    description="Nmap port scan (1-65535)",
                    input_types=["IP"],
                    output_type="Custom",
                    relationship="hosted_by",
                    handler=_transform_domain_nmap,
                ),
            ],
            "Email": [
                TransformDef(
                    name="IntelX Search",
                    description="Search email in IntelX breach database",
                    input_types=["Email"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_email_intelx,
                ),
            ],
            "Phone": [
                TransformDef(
                    name="Parse & Validate",
                    description="Validate phone number format and get carrier info",
                    input_types=["Phone"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_phone_parse,
                ),
                TransformDef(
                    name="Reverse Lookup",
                    description="Reverse phone lookup via NumVerify/AbstractAPI",
                    input_types=["Phone"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_phone_lookup,
                ),
                TransformDef(
                    name="Check Leaks",
                    description="Search phone in IntelX leak database",
                    input_types=["Phone"],
                    output_type="Custom",
                    relationship="associated_with",
                    handler=_transform_phone_leaks,
                ),
            ],
            "MAC": [
                TransformDef(
                    name="Geolocate",
                    description="Geolocate MAC address via 5 providers",
                    input_types=["MAC"],
                    output_type="Geolocation",
                    relationship="located_at",
                    handler=_transform_mac_geo,
                ),
            ],
        }

    def get_all_types(self):
        return list(self._registry.keys())


def _pack_content(lines: list[str]) -> str:
    return "\n".join(str(ln) for ln in lines if ln)


# ── Universal transform runner ────────────────────────────────────


async def _run_transform(
    modules: dict,
    module_key: str,
    method: str,
    input_value: str,
    parser: Callable,
    label: str | None = None,
) -> TransformResult:
    engine = modules.get(module_key)
    if not engine:
        msg = label or module_key.replace("_", " ").title().replace(" ", "")
        return TransformResult(content=f"{msg} module not available")
    fn = getattr(engine, method)
    result = (
        await fn(input_value) if asyncio.iscoroutinefunction(fn) else fn(input_value)
    )
    return parser(result, input_value)


# ── Parsers ───────────────────────────────────────────────────────


def _parse_username_search(results, username):
    claimed = [r for r in results if r.get("status") == "Claimed"]
    children = []
    for r in claimed[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=r["site"],
                entity_type="Custom",
                content=r.get("url_user", ""),
                evidence=[r.get("url_main", "")],
            )
        )
    if len(claimed) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(claimed) - CHILD_THRESHOLD} more sites",
                entity_type="Custom",
                content="\n".join(
                    f"{r['site']}: {r.get('url_user', '')}"
                    for r in claimed[CHILD_THRESHOLD:]
                ),
            )
        )
    content_lines = [
        divider(),
        title(f"Username search: {len(claimed)}/{len(results)} sites"),
    ]
    for r in claimed:
        url = r.get("url_user", r.get("url_main", ""))
        content_lines.append(bullet(f"{r['site']}: {url}"))
    if not claimed:
        content_lines.append(fmt_info("No accounts found"))
    content_lines.append(end_of("username search"))
    content_lines.append(divider())
    return TransformResult(
        children=children,
        content="\n".join(content_lines),
        evidence=[r.get("url_main", "") for r in claimed if r.get("url_main")],
    )


def _parse_maigret_search(report, username):
    return TransformResult(content=report)


def _parse_domain_ip(data, domain):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    ip = data.get("ip", "")
    children = []
    if ip:
        children.append(
            ChildNodeDef(
                title=ip,
                entity_type="IP",
                content="\n".join(
                    [
                        kv("Country", data.get("country", "?")),
                        kv("City", data.get("city", "?")),
                        kv("ASN", data.get("asn", "?")),
                        kv("Provider", data.get("provider", "?")),
                    ]
                ),
            ),
        )
    lat = data.get("lat")
    lon = data.get("lon")
    if lat and lon:
        children.append(
            ChildNodeDef(
                title=f"{lat:.2f}, {lon:.2f}",
                entity_type="Geolocation",
                content=f"{kv('Latitude', lat)}\n{kv('Longitude', lon)}",
            )
        )
    content = _pack_content([kv(k, v) for k, v in data.items() if v])
    return TransformResult(children=children, content=content or str(data))


def _parse_domain_dns(data, domain):
    if not isinstance(data, dict) or "error" in data:
        return TransformResult(content="DNS lookup failed")
    lines = [divider(), title(f"DNS: {domain}")]
    children = []
    for rtype in ["A", "MX", "TXT", "NS", "CNAME"]:
        records = data.get(rtype, [])
        if records:
            lines.append(section(rtype))
            for rec in records[:3]:
                lines.append(bullet(str(rec)))
                child_type = "IP" if rtype == "A" else "Custom"
                children.append(ChildNodeDef(title=str(rec), entity_type=child_type))
    soa = data.get("SOA", {})
    if soa:
        lines.append(section("SOA"))
        lines.append(kv("MNAME", soa.get("mname", "?")))
    lines.append(end_of("dns lookup"))
    lines.append(divider())
    return TransformResult(
        children=children[:CHILD_THRESHOLD],
        content=_pack_content(lines) if lines else "No DNS records found",
    )


def _parse_domain_ssl(data, domain):
    if not isinstance(data, dict) or "error" in data:
        return TransformResult(content=str(data))
    issuer = data.get("issuer", {})
    subject = data.get("subject", {})
    lines = [
        divider(),
        title(f"SSL/TLS: {domain}"),
        kv("Version", data.get("version", "?")),
        kv("Cipher", data.get("cipher", "?")),
        kv("Issuer", issuer.get("organizationName", issuer.get("commonName", "?"))),
        kv("Subject", subject.get("commonName", "?")),
        kv("Expires", data.get("expires", "?")),
        end_of("ssl/tls"),
        divider(),
    ]
    return TransformResult(
        children=[
            ChildNodeDef(
                title=subject.get("commonName", domain),
                entity_type="Custom",
                content=_pack_content(lines),
            ),
        ],
        content=_pack_content(lines),
    )


def _parse_domain_webstack(data, domain):
    if not isinstance(data, dict) or "error" in data:
        return TransformResult(content=str(data))
    tech = data.get("detected_tech", [])
    waf = data.get("waf", "?")
    server = data.get("web_server", "?")
    lines = [
        divider(),
        title(f"Web Stack: {domain}"),
        kv("Server", server),
        kv("WAF", waf),
        kv("Tech", ", ".join(tech) if isinstance(tech, list) else tech),
        end_of("web stack"),
        divider(),
    ]
    children = []
    if server and server != "Not resolve":
        children.append(
            ChildNodeDef(
                title=f"Server: {server}",
                entity_type="Custom",
                content=kv("Web server", server),
            )
        )
    if waf and waf != "NOT FOUND":
        children.append(
            ChildNodeDef(
                title=f"WAF: {waf}",
                entity_type="Custom",
                content=kv("WAF detected", waf),
            )
        )
    if isinstance(tech, list):
        for t in tech[:CHILD_THRESHOLD]:
            children.append(
                ChildNodeDef(
                    title=t,
                    entity_type="Custom",
                    content=kv("Technology", t),
                )
            )
    return TransformResult(
        children=children[: CHILD_THRESHOLD + 2],
        content=_pack_content(lines),
        evidence=[str(data.get("http_headers", {}))]
        if data.get("http_headers")
        else [],
    )


def _parse_domain_whois(data, domain):
    if not isinstance(data, dict) or "error" in data:
        return TransformResult(content=str(data))
    org = data.get("org") or data.get("name") or ""
    registrar = data.get("registrar", "?")
    creation = data.get("creation_date", "?")
    expiration = data.get("expiration_date", "?")
    if isinstance(creation, list):
        creation = creation[0]
    if isinstance(expiration, list):
        expiration = expiration[0]
    children = []
    if org:
        children.append(
            ChildNodeDef(
                title=str(org)[:60],
                entity_type="Organization",
                content="\n".join(
                    [
                        kv("Registrar", registrar),
                        kv("Created", creation),
                        kv("Expires", expiration),
                    ]
                ),
            )
        )
    fields = [kv(k, v) for k, v in data.items() if not k.startswith("_")]
    content = "\n".join(
        [divider(), title(f"WHOIS: {domain}")] + fields + [end_of("whois"), divider()]
    )
    return TransformResult(
        children=children,
        content=content,
    )


def _parse_domain_subdomains(raw, domain):
    if not isinstance(raw, str) or not raw or "Error" in raw:
        return TransformResult(content=str(raw))
    result_lines = raw.split("\n")
    subs = [
        ln.strip().lstrip("- ").strip() for ln in result_lines if ln.startswith("  - ")
    ]
    children = []
    for sub in subs[:CHILD_THRESHOLD]:
        children.append(ChildNodeDef(title=sub, entity_type="Domain"))
    if len(subs) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(subs) - CHILD_THRESHOLD} more",
                entity_type="Custom",
                content="\n".join(subs[CHILD_THRESHOLD:]),
            )
        )
    return TransformResult(
        children=children,
        content=raw,
    )


def _parse_domain_ct(raw, domain):
    if not isinstance(raw, str) or not raw or "Error" in raw:
        return TransformResult(content=str(raw))
    result_lines = raw.split("\n")
    domains = [
        ln.strip()[2:].strip() for ln in result_lines if ln.strip().startswith("- ")
    ][:CHILD_THRESHOLD]
    children = [ChildNodeDef(title=d, entity_type="Domain") for d in domains]
    return TransformResult(
        children=children,
        content=raw,
    )


def _parse_domain_social(raw, domain):
    if not raw or "Not found" in raw:
        return TransformResult(content="No social tags found")
    tags = [ln for ln in raw.split("\n") if ":" in ln]
    children = []
    seen = set()
    for tag in tags[:CHILD_THRESHOLD]:
        key = tag.split(":", 1)[0].strip()
        val = tag.split(":", 1)[1].strip() if ":" in tag else ""
        if key not in seen:
            seen.add(key)
            children.append(
                ChildNodeDef(
                    title=key if len(key) < 40 else key[:37] + "...",
                    entity_type="Custom",
                    content=val,
                )
            )
    if len(tags) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(tags) - CHILD_THRESHOLD} more tags",
                entity_type="Custom",
                content="\n".join(tags[CHILD_THRESHOLD:]),
            )
        )
    return TransformResult(children=children, content=raw)


def _parse_domain_malware(data, domain):
    if not isinstance(data, dict) or "error" in data:
        return TransformResult(content=str(data))
    status = data.get("status", "?")
    source = data.get("source", "?")
    malicious = data.get("malicious_votes", 0)
    return TransformResult(
        children=[
            ChildNodeDef(
                title=f"Reputation: {status}",
                entity_type="Custom",
                content=(f"{kv('Source', source)}\n{kv('Malicious votes', malicious)}"),
            )
        ],
        content="\n".join(
            [
                divider(),
                title(f"Malware: {domain}"),
                kv("Status", status),
                kv("Source", source),
                kv("Malicious votes", malicious),
                end_of("malware check"),
                divider(),
            ]
        ),
    )


def _parse_domain_securitytxt(raw, domain):
    if not raw or "Not Found" in raw:
        return TransformResult(content="No security.txt found")
    return TransformResult(
        children=[
            ChildNodeDef(
                title="security.txt",
                entity_type="Custom",
                content=raw[:500],
            )
        ],
        content=raw,
    )


def _parse_domain_cookies(raw, domain):
    if not raw or "No cookies" in raw:
        return TransformResult(content="No cookies found")
    lines = [ln for ln in raw.split("\n") if ln.strip()]
    children = []
    for i, line in enumerate(lines[: CHILD_THRESHOLD * 2]):
        if ":" in line and line.startswith("  ") and not line.startswith("    "):
            name = line.split(":", 1)[0].strip()
            val = line.split(":", 1)[1].strip()
            children.append(
                ChildNodeDef(
                    title=f"Cookie: {name}" if len(name) < 50 else name[:47] + "...",
                    entity_type="Custom",
                    content=val,
                )
            )
    if len(lines) > CHILD_THRESHOLD * 2:
        children.append(
            ChildNodeDef(
                title=f"+{len(lines) - CHILD_THRESHOLD * 2} more cookies",
                entity_type="Custom",
                content="\n".join(lines[CHILD_THRESHOLD * 2 :]),
            )
        )
    return TransformResult(
        children=children[: CHILD_THRESHOLD + 1],
        content=raw,
    )


def _parse_domain_robots(raw, domain):
    if not raw or "Error" in raw:
        return TransformResult(content=str(raw))
    return TransformResult(
        children=[
            ChildNodeDef(
                title="robots.txt",
                entity_type="Custom",
                content=raw[:500],
            )
        ],
        content=raw,
    )


def _parse_domain_nmap(data, domain):
    if not isinstance(data, dict) or "error" in data:
        return TransformResult(content=str(data))
    children = []
    for host, ports in data.items():
        for p in ports[:CHILD_THRESHOLD]:
            children.append(
                ChildNodeDef(
                    title=f"Port {p['port']}/{p.get('service', '?')}",
                    entity_type="Custom",
                    content=_pack_content(
                        [
                            f"State: {p.get('state', '?')}",
                            f"Service: {p.get('service', '?')}",
                            f"Product: {p.get('product', '?')}",
                            f"Version: {p.get('version', '?')}",
                        ]
                    ),
                )
            )
    lines = [divider(), title(f"Nmap: {domain}")]
    for host, ports in data.items():
        lines.append(section(host))
        for p in ports:
            lines.append(
                bullet(
                    f"Port {p['port']}/{p.get('service', '?')} - {p.get('state', '?')}"
                )
            )
    if not any(data.values()):
        lines.append(fmt_info("All ports closed"))
    lines.append(end_of("port scan"))
    lines.append(divider())
    return TransformResult(
        children=children[:CHILD_THRESHOLD],
        content=_pack_content(lines),
    )


def _parse_ip_geo(data, ip_addr):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    lat = data.get("lat")
    lon = data.get("lon")
    children = []
    if lat and lon:
        children.append(
            ChildNodeDef(
                title=f"{lat:.2f}, {lon:.2f}",
                entity_type="Geolocation",
                content="\n".join(
                    [
                        kv("IP", data.get("ip", ip_addr)),
                        kv("Country", data.get("country", "?")),
                        kv("City", data.get("city", "?")),
                        kv("Latitude", lat),
                        kv("Longitude", lon),
                    ]
                ),
            ),
        )
    fields = [kv(k, v) for k, v in data.items() if v]
    content = "\n".join(
        [divider(), title(f"IP Geo: {ip_addr}")]
        + fields
        + [end_of("ip geo"), divider()]
    )
    return TransformResult(children=children, content=content or str(data))


def _parse_email_intelx(raw, email):
    if not raw or "Not found" in raw:
        return TransformResult(content=str(raw))
    lines = raw.split("\n")
    db_lines = [ln.lstrip()[2:] for ln in lines if ln.startswith("  -")]
    children = []
    seen = set()
    for db in db_lines[:CHILD_THRESHOLD]:
        clean = db.strip()
        if clean and clean not in seen:
            seen.add(clean)
            children.append(
                ChildNodeDef(
                    title=clean[:50],
                    entity_type="Custom",
                    content=f"Database: {clean}\nEmail: {email}",
                )
            )
    if len(db_lines) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(db_lines) - CHILD_THRESHOLD} more databases",
                entity_type="Custom",
                content="\n".join(db_lines[CHILD_THRESHOLD:]),
            )
        )
    return TransformResult(children=children, content=raw)


def _parse_phone_parse(raw, phone):
    if not raw or "Parse error" in raw:
        return TransformResult(content=str(raw))
    data = {}
    for line in raw.split("\n"):
        if ":" in line and not line.startswith("["):
            key = line.split(":", 1)[0].strip()
            val = line.split(":", 1)[1].strip()
            if key and val:
                data[key] = val
    e164 = data.get("E.164", phone)
    children = []
    children.append(
        ChildNodeDef(
            title=e164,
            entity_type="Phone",
            content=raw,
        )
    )
    location = data.get("Location")
    if location:
        children.append(
            ChildNodeDef(
                title=location,
                entity_type="Geolocation",
                content=f"{kv('Phone', e164)}\n{kv('Location', location)}",
            )
        )
    carrier_name = data.get("Carrier")
    if carrier_name:
        children.append(
            ChildNodeDef(
                title=carrier_name,
                entity_type="Organization",
                content=f"{kv('Phone', e164)}\n{kv('Carrier', carrier_name)}",
            )
        )
    line_type = data.get("Line Type")
    if line_type:
        children.append(
            ChildNodeDef(
                title=line_type,
                entity_type="Custom",
                content=f"{kv('Phone', e164)}\n{kv('Line Type', line_type)}",
            )
        )
    region = data.get("Region")
    if region:
        children.append(
            ChildNodeDef(
                title=region,
                entity_type="Custom",
                content=f"{kv('Phone', e164)}\n{kv('Region', region)}",
            )
        )
    timezones_str = data.get("Timezones")
    if timezones_str:
        for tz in [t.strip() for t in timezones_str.split(",")]:
            city = tz.split("/")[-1] if "/" in tz else tz
            children.append(
                ChildNodeDef(
                    title=city,
                    entity_type="Geolocation",
                    content=f"{kv('Phone', e164)}\n{kv('Timezone', tz)}",
                )
            )
    return TransformResult(children=children, content=raw)


def _parse_phone_lookup(raw, phone):
    if not raw or "No API keys" in raw:
        return TransformResult(content=str(raw))
    lines = [ln for ln in raw.split("\n") if ln.strip() and ":" in ln]
    children = []
    for line in lines[:CHILD_THRESHOLD]:
        key = line.split(":", 1)[0].strip()
        val = line.split(":", 1)[1].strip() if ":" in line else ""
        children.append(
            ChildNodeDef(
                title=key[:50],
                entity_type="Custom",
                content=val,
            )
        )
    return TransformResult(children=children, content=raw)


def _parse_phone_leaks(raw, phone):
    if not raw or "No API keys" in raw or "Not found" in raw:
        return TransformResult(content=str(raw))
    return TransformResult(
        children=[
            ChildNodeDef(
                title="Leak Check Results",
                entity_type="Custom",
                content=raw[:500],
            )
        ],
        content=raw,
    )


def _parse_mac_geo(data, mac):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    locs = data.get("location", {})
    children = []
    content_lines = [divider(), title(f"MAC Geo: {mac}")]
    for name, loc in locs.items():
        if loc:
            lat, lon = loc["latitude"], loc["longitude"]
            children.append(
                ChildNodeDef(
                    title=f"{lat:.4f}, {lon:.4f}",
                    entity_type="Geolocation",
                    content="\n".join(
                        [
                            kv("MAC", mac),
                            kv("Provider", name),
                            kv("Latitude", lat),
                            kv("Longitude", lon),
                        ]
                    ),
                )
            )
            content_lines.append(bullet(f"{name}: {lat:.4f}, {lon:.4f}"))
        else:
            content_lines.append(bullet(f"{name}: no data"))
    content_lines.append(end_of("mac geo"))
    content_lines.append(divider())
    if children:
        return TransformResult(children=children, content=_pack_content(content_lines))
    return TransformResult(content="No geolocation data found for this MAC")


# ── Transform wrappers ────────────────────────────────────────────


async def _transform_username_search(username, modules):
    return await _run_transform(
        modules, "username_search", "acheck", username, _parse_username_search
    )


async def _transform_maigret_search(username, modules):
    return await _run_transform(
        modules, "maigret_search", "search_and_report", username, _parse_maigret_search
    )


async def _transform_domain_ip(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_ip_and_location", domain, _parse_domain_ip
    )


async def _transform_domain_dns(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_dns", domain, _parse_domain_dns
    )


async def _transform_domain_ssl(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_ssl_tls_info", domain, _parse_domain_ssl
    )


async def _transform_domain_webstack(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "analyze_web_stack", domain, _parse_domain_webstack
    )


async def _transform_domain_whois(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_whois_info", domain, _parse_domain_whois
    )


async def _transform_domain_subdomains(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "find_subdomains", domain, _parse_domain_subdomains
    )


async def _transform_domain_ct(domain, modules):
    return await _run_transform(
        modules,
        "domain_analyzer",
        "get_certificate_transparency",
        domain,
        _parse_domain_ct,
    )


async def _transform_domain_social(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_social_tags", domain, _parse_domain_social
    )


async def _transform_domain_malware(domain, modules):
    return await _run_transform(
        modules,
        "domain_analyzer",
        "check_malware_reputation",
        domain,
        _parse_domain_malware,
    )


async def _transform_domain_securitytxt(domain, modules):
    return await _run_transform(
        modules,
        "domain_analyzer",
        "get_security_txt",
        domain,
        _parse_domain_securitytxt,
    )


async def _transform_domain_cookies(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_cookies", domain, _parse_domain_cookies
    )


async def _transform_domain_robots(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_robots_txt", domain, _parse_domain_robots
    )


async def _transform_domain_nmap(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "run_nmap_scan", domain, _parse_domain_nmap
    )


async def _transform_ip_geo(ip_addr, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_ip_and_location", ip_addr, _parse_ip_geo
    )


async def _transform_email_intelx(email, modules):
    return await _run_transform(
        modules, "mail_search", "get_data", email, _parse_email_intelx, label="IntelX"
    )


async def _transform_phone_parse(phone, modules):
    return await _run_transform(
        modules, "phone_search", "parse_and_validate", phone, _parse_phone_parse
    )


async def _transform_phone_lookup(phone, modules):
    return await _run_transform(
        modules, "phone_search", "reverse_lookup", phone, _parse_phone_lookup
    )


async def _transform_phone_leaks(phone, modules):
    return await _run_transform(
        modules, "phone_search", "check_leaks", phone, _parse_phone_leaks
    )


async def _transform_mac_geo(mac, modules):
    return await _run_transform(
        modules, "mac_location", "locate_async", mac, _parse_mac_geo
    )
