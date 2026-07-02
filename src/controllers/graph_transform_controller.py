import asyncio
import math
from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF

CHILD_THRESHOLD = 5


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
        default_prefix = f"New {node.entity_type}"
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
                220 + len(child_nodes) * 40,
                -30 * max(1, len(children)) + len(child_nodes) * 60,
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
        radius = 200
        start_angle = -80
        end_angle = 80
        for i, child in enumerate(children):
            frac = i / max(count - 1, 1)
            angle = start_angle + frac * (end_angle - start_angle)
            rad = math.radians(angle)
            x = parent.pos().x() + radius * math.cos(rad)
            y = parent.pos().y() + radius * math.sin(rad)
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
                    description="Look up carrier and location via NumVerify/AbstractAPI",
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
    return "\n".join(str(l) for l in lines if l)


# ── Username transforms ──────────────────────────────────────────


async def _transform_username_search(username: str, modules) -> TransformResult:
    engine = modules.get("username_search")
    if not engine:
        return TransformResult(content="UsernameSearch module not available")
    results = await engine.acheck(username)
    claimed = [r for r in results if r.get("status") == "Claimed"]

    detail = f"Username search: found on {len(claimed)}/{len(results)} sites\n"
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

    site_lines = [
        f"{r['site']}: {r.get('url_user', r.get('url_main', ''))}" for r in claimed
    ]
    return TransformResult(
        children=children,
        content=detail + "\n".join(site_lines)
        if site_lines
        else detail + "No accounts found",
        evidence=[r.get("url_main", "") for r in claimed if r.get("url_main")],
    )


async def _transform_maigret_search(username: str, modules) -> TransformResult:
    engine = modules.get("maigret_search")
    if not engine:
        return TransformResult(content="MaigretSearch module not available")
    report = await engine.search_and_report(username)
    return TransformResult(
        content=report,
    )


# ── Domain transforms ────────────────────────────────────────────


async def _transform_domain_ip(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    data = await da.get_ip_and_location(domain)
    if isinstance(data, dict):
        ip = data.get("ip", "")
        children = []
        if ip:
            children.append(
                ChildNodeDef(
                    title=ip,
                    entity_type="IP",
                    content=_pack_content(
                        [
                            f"Country: {data.get('country', '?')}",
                            f"City: {data.get('city', '?')}",
                            f"ASN: {data.get('asn', '?')}",
                            f"Provider: {data.get('provider', '?')}",
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
                    content=f"Latitude: {lat}\nLongitude: {lon}",
                )
            )
        info = _pack_content([f"{k}: {v}" for k, v in data.items() if v])
        return TransformResult(children=children, content=info or str(data))
    return TransformResult(content=str(data))


async def _transform_domain_dns(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    data = await da.get_dns(domain)
    if isinstance(data, dict) and "error" not in data:
        lines = []
        children = []
        for rtype in ["A", "MX", "TXT", "NS", "CNAME"]:
            records = data.get(rtype, [])
            if records:
                lines.append(f"{rtype}: {', '.join(records[:3])}")
                for rec in records[:3]:
                    child_type = "IP" if rtype == "A" else "Custom"
                    children.append(
                        ChildNodeDef(title=str(rec), entity_type=child_type)
                    )
        soa = data.get("SOA", {})
        if soa:
            lines.append(f"SOA: {soa.get('mname', '?')}")
        return TransformResult(
            children=children[:CHILD_THRESHOLD],
            content=_pack_content(lines) if lines else "No DNS records found",
        )
    return TransformResult(content="DNS lookup failed")


async def _transform_domain_ssl(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    data = await da.get_ssl_tls_info(domain)
    if isinstance(data, dict) and "error" not in data:
        issuer = data.get("issuer", {})
        subject = data.get("subject", {})
        lines = [
            f"Version: {data.get('version', '?')}",
            f"Cipher: {data.get('cipher', '?')}",
            f"Issuer: {issuer.get('organizationName', issuer.get('commonName', '?'))}",
            f"Subject: {subject.get('commonName', '?')}",
            f"Expires: {data.get('expires', '?')}",
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
    return TransformResult(content=str(data))


async def _transform_domain_webstack(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    data = await da.analyze_web_stack(domain)
    if isinstance(data, dict) and "error" not in data:
        tech = data.get("detected_tech", [])
        waf = data.get("waf", "?")
        server = data.get("web_server", "?")
        lines = [
            f"Server: {server}",
            f"WAF: {waf}",
            f"Tech: {', '.join(tech) if isinstance(tech, list) else tech}",
        ]
        children = []
        if server and server != "Not resolve":
            children.append(
                ChildNodeDef(
                    title=f"Server: {server}",
                    entity_type="Custom",
                    content=f"Web server: {server}",
                )
            )
        if waf and waf != "NOT FOUND":
            children.append(
                ChildNodeDef(
                    title=f"WAF: {waf}",
                    entity_type="Custom",
                    content=f"WAF detected: {waf}",
                )
            )
        if isinstance(tech, list):
            for t in tech[:CHILD_THRESHOLD]:
                children.append(
                    ChildNodeDef(
                        title=t,
                        entity_type="Custom",
                        content=f"Technology: {t}",
                    )
                )
        return TransformResult(
            children=children[: CHILD_THRESHOLD + 2],
            content=_pack_content(lines),
            evidence=[str(data.get("http_headers", {}))]
            if data.get("http_headers")
            else [],
        )
    return TransformResult(content=str(data))


async def _transform_domain_whois(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    data = await da.get_whois_info(domain)
    if isinstance(data, dict) and "error" not in data:
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
                    content=_pack_content(
                        [
                            f"Registrar: {registrar}",
                            f"Created: {creation}",
                            f"Expires: {expiration}",
                        ]
                    ),
                )
            )
        return TransformResult(
            children=children,
            content=_pack_content(
                [f"{k}: {v}" for k, v in data.items() if not k.startswith("_")]
            ),
        )
    return TransformResult(content=str(data))


async def _transform_domain_subdomains(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    raw = await da.find_subdomains(domain)
    if isinstance(raw, str) and raw and "Error" not in raw:
        subs = [s.strip() for s in raw.split("\n") if s.strip()]
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
            content=f"Found {len(subs)} subdomains\n" + "\n".join(subs) if subs else "",
        )
    return TransformResult(content=str(raw))


async def _transform_domain_ct(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    raw = await da.get_certificate_transparency(domain)
    if isinstance(raw, str) and raw and "Error" not in raw:
        lines = raw.split("\n")
        domains = [l[2:] for l in lines if l.startswith("- ")][:CHILD_THRESHOLD]
        children = [ChildNodeDef(title=d, entity_type="Domain") for d in domains]
        return TransformResult(
            children=children,
            content=raw,
        )
    return TransformResult(content=str(raw))


async def _transform_domain_social(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    raw = await da.get_social_tags(domain)
    if raw and "Not found" not in raw:
        tags = [l for l in raw.split("\n") if ":" in l]
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
    return TransformResult(content="No social tags found")


async def _transform_domain_malware(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    data = await da.check_malware_reputation(domain)
    if isinstance(data, dict) and "error" not in data:
        status = data.get("status", "?")
        source = data.get("source", "?")
        malicious = data.get("malicious_votes", 0)
        return TransformResult(
            children=[
                ChildNodeDef(
                    title=f"Reputation: {status}",
                    entity_type="Custom",
                    content=f"Source: {source}\nMalicious votes: {malicious}",
                )
            ],
            content=f"Status: {status}\nSource: {source}\nMalicious votes: {malicious}",
        )
    return TransformResult(content=str(data))


async def _transform_domain_securitytxt(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    raw = await da.get_security_txt(domain)
    if raw and "Not Found" not in raw:
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
    return TransformResult(content="No security.txt found")


async def _transform_domain_cookies(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    raw = await da.get_cookies(domain)
    if raw and "No cookies" not in raw:
        lines = [l for l in raw.split("\n") if l.strip()]
        children = []
        for i, line in enumerate(lines[: CHILD_THRESHOLD * 2]):
            if ":" in line and not line.startswith(" "):
                name = line.split(":", 1)[0].strip()
                val = line.split(":", 1)[1].strip()
                children.append(
                    ChildNodeDef(
                        title=f"Cookie: {name}"
                        if len(name) < 50
                        else name[:47] + "...",
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
    return TransformResult(content="No cookies found")


async def _transform_domain_robots(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    raw = await da.get_robots_txt(domain)
    if raw and "Error" not in raw:
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
    return TransformResult(content=str(raw))


async def _transform_domain_nmap(domain: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    data = await da.run_nmap_scan(domain)
    if isinstance(data, dict) and "error" not in data:
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
        lines = []
        for host, ports in data.items():
            for p in ports:
                lines.append(
                    f"Port {p['port']}/{p.get('service', '?')} - {p.get('state', '?')}"
                )
        return TransformResult(
            children=children[:CHILD_THRESHOLD],
            content=_pack_content(lines) if lines else "All ports closed",
        )
    return TransformResult(content=str(data))


# ── IP transforms ────────────────────────────────────────────────


async def _transform_ip_geo(ip_addr: str, modules) -> TransformResult:
    da = modules.get("domain_analyzer")
    if not da:
        return TransformResult(content="DomainAnalyzer module not available")
    data = await da.get_ip_and_location(ip_addr)
    if isinstance(data, dict):
        lat = data.get("lat")
        lon = data.get("lon")
        children = []
        if lat and lon:
            children.append(
                ChildNodeDef(
                    title=f"{lat:.2f}, {lon:.2f}",
                    entity_type="Geolocation",
                    content=_pack_content(
                        [
                            f"IP: {data.get('ip', ip_addr)}",
                            f"Country: {data.get('country', '?')}",
                            f"City: {data.get('city', '?')}",
                            f"Latitude: {lat}",
                            f"Longitude: {lon}",
                        ]
                    ),
                ),
            )
        info = _pack_content([f"{k}: {v}" for k, v in data.items() if v])
        return TransformResult(children=children, content=info or str(data))
    return TransformResult(content=str(data))


# ── Email transforms ─────────────────────────────────────────────


async def _transform_email_intelx(email: str, modules) -> TransformResult:
    engine = modules.get("intelx_search")
    if not engine:
        return TransformResult(content="IntelX module not available")
    raw = await engine.get_data(email)
    if raw and "Not found" not in raw:
        lines = raw.split("\n")
        db_lines = [l[2:] for l in lines if l.startswith("  • ") or l.startswith("  -")]
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
    return TransformResult(content=str(raw))


# ── Phone transforms ─────────────────────────────────────────────


async def _transform_phone_parse(phone: str, modules) -> TransformResult:
    engine = modules.get("phone_search")
    if not engine:
        return TransformResult(content="PhoneSearch module not available")
    raw = engine.parse_and_validate(phone)
    if raw and "Parse error" not in raw:
        data = {}
        for line in raw.split("\n"):
            if ":" in line and not line.startswith("["):
                key = line.split(":", 1)[0].strip()
                val = line.split(":", 1)[1].strip()
                if key and val:
                    data[key] = val

        e164 = data.get("E.164", phone)
        children = []

        children.append(ChildNodeDef(
            title=e164,
            entity_type="Phone",
            content=raw,
        ))

        location = data.get("Location")
        if location:
            children.append(ChildNodeDef(
                title=location,
                entity_type="Geolocation",
                content=f"Phone: {e164}\nLocation: {location}",
            ))

        carrier_name = data.get("Carrier")
        if carrier_name:
            children.append(ChildNodeDef(
                title=carrier_name,
                entity_type="Organization",
                content=f"Phone: {e164}\nCarrier: {carrier_name}",
            ))

        line_type = data.get("Line Type")
        if line_type:
            children.append(ChildNodeDef(
                title=line_type,
                entity_type="Custom",
                content=f"Phone: {e164}\nLine Type: {line_type}",
            ))

        region = data.get("Region")
        if region:
            children.append(ChildNodeDef(
                title=region,
                entity_type="Custom",
                content=f"Phone: {e164}\nRegion: {region}",
            ))

        timezones_str = data.get("Timezones")
        if timezones_str:
            tzs = [t.strip() for t in timezones_str.split(",")]
            for tz in tzs[:CHILD_THRESHOLD]:
                city = tz.split("/")[-1] if "/" in tz else tz
                children.append(ChildNodeDef(
                    title=city,
                    entity_type="Geolocation",
                    content=f"Phone: {e164}\nTimezone: {tz}",
                ))
            if len(tzs) > CHILD_THRESHOLD:
                children.append(ChildNodeDef(
                    title=f"+{len(tzs) - CHILD_THRESHOLD} more timezones",
                    entity_type="Custom",
                    content="\n".join(tzs[CHILD_THRESHOLD:]),
                ))

        return TransformResult(children=children, content=raw)
    return TransformResult(content=str(raw))


async def _transform_phone_lookup(phone: str, modules) -> TransformResult:
    engine = modules.get("phone_search")
    if not engine:
        return TransformResult(content="PhoneSearch module not available")
    raw = await engine.reverse_lookup(phone)
    if raw and "No API keys" not in raw:
        lines = [l for l in raw.split("\n") if l.strip() and ":" in l]
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
    return TransformResult(content=str(raw))


async def _transform_phone_leaks(phone: str, modules) -> TransformResult:
    engine = modules.get("phone_search")
    if not engine:
        return TransformResult(content="PhoneSearch module not available")
    raw = await engine.check_leaks(phone)
    if raw and "No API keys" not in raw and "Not found" not in raw:
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
    return TransformResult(content=str(raw))


# ── MAC transforms ───────────────────────────────────────────────


async def _transform_mac_geo(mac: str, modules) -> TransformResult:
    engine = modules.get("mac_location")
    if not engine:
        return TransformResult(content="MacLocation module not available")
    data = await engine.locate_async(mac)
    if isinstance(data, dict):
        locs = data.get("location", {})
        found = {name: loc for name, loc in locs.items() if loc}
        if found:
            name, loc = next(iter(found.items()))
            lat, lon = loc["latitude"], loc["longitude"]
            return TransformResult(
                children=[
                    ChildNodeDef(
                        title=f"{lat:.4f}, {lon:.4f}",
                        entity_type="Geolocation",
                        content=_pack_content(
                            [
                                f"MAC: {mac}",
                                f"Provider: {name}",
                                f"Latitude: {lat}",
                                f"Longitude: {lon}",
                            ]
                        ),
                    ),
                ],
                content=_pack_content(
                    [
                        f"{n}: {l['latitude']:.4f}, {l['longitude']:.4f}"
                        for n, l in found.items()
                    ]
                ),
            )
        return TransformResult(content="No geolocation data found for this MAC")
    return TransformResult(content=str(data))
