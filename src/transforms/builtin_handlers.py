"""Built-in SkyFall graph transforms.

The large collection of parsers and transform handlers lives here so the
controller can focus on graph integration and plugin discovery.  User plugins
should not import this module directly; use the public ``src.transforms`` API
instead.
"""

from __future__ import annotations

import inspect
import math
import re
from datetime import UTC, datetime
from pathlib import Path

from src.modules import username_merge
from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    kv,
    render,
    section,
    title,
)
from src.ui.output_formatter import (
    info as fmt_info,
)

from .helpers import (
    _PATTERNS,
    CHILD_THRESHOLD,
    _pack_content,
    _run_transform,
    _safe_float,
    _setting,
)
from .models import ChildNodeDef, TransformResult

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
    lat = _safe_float(data.get("lat"))
    lon = _safe_float(data.get("lon"))
    if lat is not None and lon is not None:
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
    for rtype in ["A", "AAAA", "MX", "TXT", "NS", "CNAME"]:
        records = data.get(rtype, [])
        if records:
            lines.append(section(rtype))
            for rec in records[:3]:
                lines.append(bullet(str(rec)))
                child_type = "IP" if rtype in ("A", "AAAA") else "Custom"
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


def _parse_domain_subdomains(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Subdomains: {domain}"))
    subs = data.get("subdomains", [])
    children = [
        ChildNodeDef(title=sub, entity_type="Domain") for sub in subs[:CHILD_THRESHOLD]
    ]
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
        content=render(data, f"Subdomains: {domain}"),
    )


def _parse_domain_ct(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(
            content=render(data, f"Certificate Transparency: {domain}")
        )
    domains = data.get("domains", [])[:CHILD_THRESHOLD]
    children = [ChildNodeDef(title=d, entity_type="Domain") for d in domains]
    return TransformResult(
        children=children,
        content=render(data, f"Certificate Transparency: {domain}"),
    )


def _parse_domain_social(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Social tags: {domain}"))
    tags = data.get("tags", {})
    items = list(tags.items())
    children = []
    for key, val in items[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=key if len(key) < 40 else key[:37] + "...",
                entity_type="Custom",
                content=str(val),
            )
        )
    if len(items) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(items) - CHILD_THRESHOLD} more tags",
                entity_type="Custom",
                content="\n".join(f"{k}: {v}" for k, v in items[CHILD_THRESHOLD:]),
            )
        )
    return TransformResult(
        children=children,
        content=render(data, f"Social tags: {domain}"),
    )


def _parse_domain_malware(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Malware: {domain}"))
    children = []
    for src in data.get("sources", []):
        label = src.get("source", "?")
        status = src.get("status", "?")
        detail = ", ".join(
            f"{k}={v}"
            for k, v in src.items()
            if k not in ("source", "status") and v not in ("", None, [], {})
        )
        children.append(
            ChildNodeDef(
                title=f"{label}: {status}",
                entity_type="Custom",
                content="\n".join(
                    [kv("Source", label), kv("Status", status), detail[:400]]
                ),
            )
        )
    return TransformResult(
        children=children[: CHILD_THRESHOLD + 1],
        content=render(data, f"Malware: {domain}"),
    )


def _parse_domain_securitytxt(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"security.txt: {domain}"))
    if not data.get("found"):
        return TransformResult(content=render(data, f"security.txt: {domain}"))
    return TransformResult(
        children=[
            ChildNodeDef(
                title="security.txt",
                entity_type="Custom",
                content=str(data.get("content", ""))[:500],
            )
        ],
        content=render(data, f"security.txt: {domain}"),
    )


def _parse_domain_cookies(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Cookies: {domain}"))
    cookies = data.get("cookies", [])
    children = []
    for cookie in cookies[: CHILD_THRESHOLD * 2]:
        name = cookie.get("name", "?")
        children.append(
            ChildNodeDef(
                title=f"Cookie: {name}" if len(name) < 50 else name[:47] + "...",
                entity_type="Custom",
                content=str(cookie.get("value", "")),
            )
        )
    if len(cookies) > CHILD_THRESHOLD * 2:
        children.append(
            ChildNodeDef(
                title=f"+{len(cookies) - CHILD_THRESHOLD * 2} more cookies",
                entity_type="Custom",
                content="\n".join(
                    c.get("name", "") for c in cookies[CHILD_THRESHOLD * 2 :]
                ),
            )
        )
    return TransformResult(
        children=children[: CHILD_THRESHOLD + 1],
        content=render(data, f"Cookies: {domain}"),
    )


def _parse_domain_robots(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Robots.txt: {domain}"))
    if not data.get("found"):
        return TransformResult(content=render(data, f"Robots.txt: {domain}"))
    return TransformResult(
        children=[
            ChildNodeDef(
                title="robots.txt",
                entity_type="Custom",
                content=str(data.get("content", ""))[:500],
            )
        ],
        content=render(data, f"Robots.txt: {domain}"),
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
    lat = _safe_float(data.get("lat"))
    lon = _safe_float(data.get("lon"))
    children = []
    if lat is not None and lon is not None:
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


def _parse_ip_domains(data, ip_addr):
    if not isinstance(data, dict) or "error" in data:
        return TransformResult(content=str(data))

    domain_re = _PATTERNS["Domain"]
    seen = set()
    all_domains = []
    for domain in data.get("all_domains", []):
        host = str(domain).strip().rstrip(".").lower()
        if not host or host in seen or not domain_re.fullmatch(host):
            continue
        seen.add(host)
        all_domains.append(host)

    children = []
    for domain in all_domains[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=domain,
                entity_type="Domain",
                content=domain,
            )
        )
    if len(all_domains) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(all_domains) - CHILD_THRESHOLD} more domains",
                entity_type="Domain",
                content="\n".join(all_domains[CHILD_THRESHOLD:]),
            )
        )

    lines = [
        kv("IP", ip_addr),
        kv("Total unique domains", data.get("total_unique", 0)),
        "",
        section("PTR"),
    ]
    for d in data.get("ptr", []):
        lines.append(bullet(d))
    lines.append("")
    lines.append(section("Shodan InternetDB"))
    for d in data.get("hostnames", []):
        lines.append(bullet(d))
    lines.append("")
    lines.append(section("HackerTarget"))
    for d in data.get("hacker_target", []):
        lines.append(bullet(d))

    return TransformResult(
        children=children,
        content=_pack_content(lines),
    )


def _parse_email_intelx(raw, email):
    if not isinstance(raw, dict):
        return TransformResult(content=str(raw))
    content = render(raw, title=f"IntelX: {email}")
    if raw.get("error") or raw.get("message"):
        return TransformResult(content=content)
    databases = [str(db).strip() for db in raw.get("databases") or []]
    children = []
    seen = set()
    for db in databases[:CHILD_THRESHOLD]:
        if db and db not in seen:
            seen.add(db)
            children.append(
                ChildNodeDef(
                    title=db[:50],
                    entity_type="Custom",
                    content=f"Database: {db}\nEmail: {email}",
                )
            )
    if len(databases) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(databases) - CHILD_THRESHOLD} more databases",
                entity_type="Custom",
                content="\n".join(databases[CHILD_THRESHOLD:]),
            )
        )
    return TransformResult(children=children, content=content)


def _parse_phone_parse(raw, phone):
    if not isinstance(raw, dict):
        return TransformResult(content=str(raw))
    content = render(raw, title=f"Phone: {phone}")
    if raw.get("error"):
        return TransformResult(content=content)

    e164 = raw.get("e164") or phone
    children = [
        ChildNodeDef(title=e164, entity_type="Phone", content=content),
    ]

    location = raw.get("location")
    if location:
        children.append(
            ChildNodeDef(
                title=location,
                entity_type="Geolocation",
                content=f"{kv('Phone', e164)}\n{kv('Location', location)}",
            )
        )
    carrier_name = raw.get("carrier")
    if carrier_name:
        children.append(
            ChildNodeDef(
                title=carrier_name,
                entity_type="Organization",
                content=f"{kv('Phone', e164)}\n{kv('Carrier', carrier_name)}",
            )
        )
    line_type = raw.get("line_type")
    if line_type:
        children.append(
            ChildNodeDef(
                title=line_type,
                entity_type="Custom",
                content=f"{kv('Phone', e164)}\n{kv('Line Type', line_type)}",
            )
        )
    region = raw.get("region")
    if region:
        children.append(
            ChildNodeDef(
                title=region,
                entity_type="Custom",
                content=f"{kv('Phone', e164)}\n{kv('Region', region)}",
            )
        )
    for tz in raw.get("timezones") or []:
        city = tz.split("/")[-1] if "/" in tz else tz
        children.append(
            ChildNodeDef(
                title=city,
                entity_type="Geolocation",
                content=f"{kv('Phone', e164)}\n{kv('Timezone', tz)}",
            )
        )
    return TransformResult(children=children, content=content)


def _parse_phone_lookup(raw, phone):
    if not isinstance(raw, dict):
        return TransformResult(content=str(raw))
    content = render(raw, title=f"Phone: {phone}")
    if raw.get("message") or raw.get("error"):
        return TransformResult(content=content)

    children = []
    for provider in ("numverify", "abstractapi"):
        block = raw.get(provider)
        if not isinstance(block, dict):
            continue
        for key, val in list(block.items())[:CHILD_THRESHOLD]:
            if key == "error" or val in (None, "", [], {}):
                continue
            children.append(
                ChildNodeDef(
                    title=f"{key}"[:50],
                    entity_type="Custom",
                    content=f"{kv(provider, key)}\n{kv('Value', val)}",
                )
            )
    return TransformResult(children=children, content=content)


def _parse_phone_leaks(raw, phone):
    if not isinstance(raw, dict):
        return TransformResult(content=str(raw))
    content = render(raw, title=f"Phone: {phone}")
    findings = raw.get("findings") or []
    if not findings:
        return TransformResult(content=content)

    children = []
    for item in findings[:CHILD_THRESHOLD]:
        details = [f"{kv('Name', item.get('name'))}"]
        if item.get("date"):
            details.append(kv("Date", item["date"]))
        if item.get("bucket"):
            details.append(kv("Bucket", item["bucket"]))
        children.append(
            ChildNodeDef(
                title=str(item.get("name", "N/A"))[:50],
                entity_type="Custom",
                content="\n".join(details),
            )
        )
    if len(findings) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(findings) - CHILD_THRESHOLD} more records",
                entity_type="Custom",
                content="\n".join(
                    str(f.get("name", "N/A")) for f in findings[CHILD_THRESHOLD:]
                ),
            )
        )
    return TransformResult(children=children, content=content)


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
    engine = modules.get("maigret_search")
    if not engine:
        return TransformResult(content="Maigret module not available")
    report_data, matches = await engine.search_and_report_structured(username)
    children = []
    for m in matches:
        lines = [
            kv("Status", m.get("status", "")),
            kv("URL", m.get("url_user", "")),
        ]
        lines += [kv(k, v) for k, v in m.get("ids", {}).items() if v not in (None, "")]
        children.append(
            ChildNodeDef(
                title=m["site"],
                entity_type="Custom",
                content="\n".join(lines),
                evidence=[m["url_user"]] if m.get("url_user") else [],
            )
        )
    return TransformResult(
        children=children,
        content=render(report_data, f"Maigret: {username}"),
    )


async def _transform_username_merged(username, modules):
    """Run both engines and surface the accounts confirmed by each other."""
    sherlock = modules.get("username_search")
    maigret = modules.get("maigret_search")
    if not sherlock or not maigret:
        return TransformResult(content="Username engines not available")

    results = await sherlock.acheck(username)
    claimed = [r for r in results if r.get("status") == "Claimed"]
    _, matches = await maigret.search_and_report_structured(username)
    confirmed, sherlock_only, maigret_only = username_merge.merge_sources(
        claimed, matches
    )

    children = []
    for entry, other in confirmed[:CHILD_THRESHOLD]:
        url = entry.get("url_user") or other.get("url_user", "")
        site = entry.get("site") or other.get("site")
        children.append(
            ChildNodeDef(
                title=f"{username_merge.CONFIRMED_MARK} {site}",
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("URL", url),
                        kv("Sherlock", entry.get("status", "?")),
                        kv("Maigret", other.get("status", "?")),
                    ]
                ),
                evidence=[url] if url else [],
            )
        )
    if len(confirmed) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(confirmed) - CHILD_THRESHOLD} confirmed",
                entity_type="Custom",
                content="\n".join(
                    entry.get("url_user") or other.get("url_user", "")
                    for entry, other in confirmed[CHILD_THRESHOLD:]
                ),
            )
        )
    return TransformResult(
        children=children,
        content=username_merge.render_report(
            username, confirmed, sherlock_only, maigret_only
        ),
    )


_REDDIT_IDENTIFIER_TYPES = {
    "email": "Email",
    "btc": "Crypto",
    "eth": "Crypto",
    "xmr": "Crypto",
    "phone": "Phone",
    "mention": "Username",
}


def _parse_reddit_report(report, errors=None):
    """Build graph children (subreddits, identifiers, domains) from a report."""
    username = report.get("username", "?")
    children = []

    for entry in report.get("top_subreddits", [])[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=f"r/{entry.get('subreddit', '?')}",
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Items", entry.get("items", 0)),
                        kv("Account", f"u/{username}"),
                    ]
                ),
            )
        )

    for identifier in report.get("identifiers", [])[:CHILD_THRESHOLD]:
        tag, _, value = identifier.partition(":")
        if not value:
            continue
        children.append(
            ChildNodeDef(
                title=value,
                entity_type=_REDDIT_IDENTIFIER_TYPES.get(tag, "Custom"),
                content=kv("Type", tag),
            )
        )

    for entry in report.get("external_domains", [])[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=entry.get("domain", "?"),
                entity_type="Domain",
                content=kv("Mentions", entry.get("times", 0)),
            )
        )

    for entry in report.get("mentioned_users", [])[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=entry.get("user", "?"),
                entity_type="Username",
                content=kv("Mentions", entry.get("times", 0)),
            )
        )

    technologies = report.get("technologies", [])
    if technologies:
        children.append(
            ChildNodeDef(
                title="Technologies",
                entity_type="Custom",
                content=", ".join(
                    f"{item.get('tech')} ×{item.get('times')}" for item in technologies
                ),
            )
        )

    totals = report.get("totals", {})
    timezone = report.get("timezone_guess", {})
    lines = [
        divider(),
        title(f"Reddit OSINT: u/{username}"),
        bullet(
            f"posts {totals.get('posts', 0)} · "
            f"comments {totals.get('comments', 0)} · items {totals.get('items', 0)}"
        ),
        kv("Live", totals.get("live", 0)),
        kv("Removed by mods", totals.get("removed_by_mods", 0)),
        kv("Deleted by author", totals.get("deleted_by_author", 0)),
        kv("Exposure (0-100)", report.get("score_exposure_0_100", 0)),
        kv("Timezone", timezone.get("estimated_region", "?")),
        kv("Last activity", totals.get("last_activity") or "?"),
    ]
    lines += [fmt_info(message) for message in (errors or [])]
    lines += [end_of("reddit osint"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_reddit_osint(username, modules):
    engine = modules.get("reddit_osint")
    if not engine:
        return TransformResult(content="Reddit OSINT module not available")
    try:
        report, errors = await engine.full_report(username)
    except Exception as exc:  # noqa: BLE001 - surface everything in the graph
        return TransformResult(content=f"Reddit OSINT failed: {exc}")
    return _parse_reddit_report(report, errors)


def _parse_social_search(data, username):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    children = []
    bsky = data.get("bluesky")
    if bsky:
        children.append(
            ChildNodeDef(
                title=bsky.get("handle", "Bluesky"),
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Platform", "Bluesky"),
                        kv("Handle", bsky.get("handle", "?")),
                        kv("Display", bsky.get("displayName", "")),
                        kv("Followers", bsky.get("followersCount", "?")),
                        kv("Posts", bsky.get("postsCount", "?")),
                    ]
                ),
                evidence=[f"https://bsky.app/profile/{bsky.get('handle', '')}"]
                if bsky.get("handle")
                else [],
            )
        )
    mstd = data.get("mastodon")
    if mstd:
        acct = mstd.get("acct", "")
        children.append(
            ChildNodeDef(
                title=f"@{acct}",
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv(
                            "Platform",
                            f"Mastodon ({data.get('mastodon_instance', '')})",
                        ),
                        kv("Account", acct),
                        kv("Display", mstd.get("display_name", "")),
                        kv("Followers", mstd.get("followers_count", "?")),
                        kv("Posts", mstd.get("statuses_count", "?")),
                    ]
                ),
                evidence=[mstd.get("url", "")] if mstd.get("url") else [],
            )
        )
    lines = [divider(), title(f"Social: {username}")]
    if bsky:
        lines.append(bullet(f"Bluesky: {bsky.get('handle', '?')}"))
    if mstd:
        lines.append(bullet(f"Mastodon: @{mstd.get('acct', '?')}"))
    if not children:
        lines.append(fmt_info("No profiles found"))
    lines += [end_of("social search"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_social_search(username, modules):
    engine = modules.get("social_search")
    if not engine:
        return TransformResult(content="Social module not available")
    data = await engine.search_structured(username)
    return _parse_social_search(data, username)


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


async def _transform_ip_domains(ip_addr, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_domains_on_ip", ip_addr, _parse_ip_domains
    )


async def _transform_email_intelx(email, modules):
    return await _run_transform(
        modules, "mail_search", "get_data", email, _parse_email_intelx, label="IntelX"
    )


def _parse_email_accounts(results, email):
    if not isinstance(results, list) or not results:
        return TransformResult(content=f"No account data for {email}")
    registered = [r for r in results if r.get("registered") is True]
    children = []
    for r in registered[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=r.get("site", "?"),
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Site", r.get("site", "?")),
                        kv("Domain", r.get("domain", "")),
                        kv("Detail", r.get("detail", "")),
                    ]
                ),
            )
        )
    if len(registered) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(registered) - CHILD_THRESHOLD} more sites",
                entity_type="Custom",
                content="\n".join(r["site"] for r in registered[CHILD_THRESHOLD:]),
            )
        )
    lines = [
        divider(),
        title(f"Registered accounts: {email}"),
        kv("Found", len(registered)),
        kv("Checked", len(results)),
    ]
    for r in registered:
        detail = f" - {r['detail']}" if r.get("detail") else ""
        lines.append(bullet(f"{r.get('site', '?')}{detail}"))
    if not registered:
        lines.append(fmt_info("No registered accounts found"))
    lines += [end_of("account check"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_email_accounts(email, modules):
    engine = modules.get("email_accounts")
    if not engine:
        return TransformResult(content="Email accounts module not available")
    results = await engine.accounts(email)
    return _parse_email_accounts(results, email)


async def _transform_phone_parse(phone, modules):
    return await _run_transform(
        modules, "phone_search", "parse_and_validate", phone, _parse_phone_parse
    )


async def _transform_phone_lookup(phone, modules):
    return await _run_transform(
        modules,
        "phone_search",
        "reverse_lookup",
        phone,
        _parse_phone_lookup,
        numverify_key=_setting(modules, "numverify_api_key"),
        abstractapi_key=_setting(modules, "abstractapi_api_key"),
    )


async def _transform_phone_leaks(phone, modules):
    return await _run_transform(
        modules,
        "phone_search",
        "check_leaks",
        phone,
        _parse_phone_leaks,
        intelx_key=_setting(modules, "intelligent_x_api_key"),
    )


async def _transform_mac_geo(mac, modules):
    return await _run_transform(
        modules, "mac_location", "locate_async", mac, _parse_mac_geo
    )


def _parse_threat_intel(data, target):
    if not isinstance(data, dict) or "error" in data:
        return TransformResult(content=str(data))
    verdict = data.get("verdict", "?")
    children = []
    for r in data.get("results", []):
        status = r.get("status", "?")
        src = r.get("source", "?")
        detail = ", ".join(
            f"{k}={v}"
            for k, v in r.items()
            if k not in ("source", "status") and v not in ("", None, [], {})
        )
        children.append(
            ChildNodeDef(
                title=f"{src}: {status}",
                entity_type="Custom",
                content=f"{kv('Source', src)}\n{kv('Status', status)}\n{detail[:400]}",
            )
        )
    lines = [divider(), title(f"Threat Intel: {target}"), kv("Verdict", verdict)]
    for r in data.get("results", []):
        lines.append(bullet(f"{r.get('source')}: {r.get('status')}"))
    lines.append(end_of("threat intel"))
    lines.append(divider())
    return TransformResult(children=children, content=_pack_content(lines))


def _parse_js_secrets(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"JS secrets: {domain}"))
    findings = data.get("findings", [])
    children = []
    for finding in findings[:CHILD_THRESHOLD]:
        label = (
            f"[{finding.get('severity', '?')}] "
            f"{finding.get('type', '?')}: {finding.get('match', '')}"
        )
        children.append(
            ChildNodeDef(title=label[:60], entity_type="Custom", content=label)
        )
    if len(findings) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(findings) - CHILD_THRESHOLD} more findings",
                entity_type="Custom",
                content="\n".join(
                    f"[{f.get('severity')}] {f.get('type')}: {f.get('match')}"
                    for f in findings[CHILD_THRESHOLD:]
                ),
            )
        )
    if not children:
        children.append(
            ChildNodeDef(
                title="JS scan done", entity_type="Custom", content=render(data)
            )
        )
    return TransformResult(
        children=children,
        content=render(data, f"JS secrets: {domain}"),
    )


async def _transform_domain_js_secrets(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "scan_js_secrets", domain, _parse_js_secrets
    )


async def _transform_domain_threat_intel(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "check_threat_intel", domain, _parse_threat_intel
    )


async def _transform_ip_threat_intel(ip_addr, modules):
    return await _run_transform(
        modules, "domain_analyzer", "check_threat_intel", ip_addr, _parse_threat_intel
    )


# ── Leaks / infostealers ──────────────────────────────────────────


def _parse_leak_search(data, target):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    children = []

    infostealer = data.get("infostealer") or {}
    if infostealer and not infostealer.get("error"):
        if infostealer.get("kind") == "domain":
            users = infostealer.get("users", 0)
            if users:
                children.append(
                    ChildNodeDef(
                        title=f"Infostealer: {users} user(s)",
                        entity_type="Custom",
                        content=_pack_content(
                            [
                                kv("Total records", infostealer.get("total", 0)),
                                kv("Users", users),
                                kv("Employees", infostealer.get("employees", 0)),
                            ]
                        ),
                    )
                )
        else:
            stealers = infostealer.get("stealers") or []
            if stealers:
                children.append(
                    ChildNodeDef(
                        title=f"Infostealer logs: {len(stealers)}",
                        entity_type="Custom",
                        content=_pack_content(
                            [
                                kv("Infected machines", len(stealers)),
                                kv(
                                    "Corporate services",
                                    infostealer.get("total_corporate_services", 0),
                                ),
                                kv(
                                    "User services",
                                    infostealer.get("total_user_services", 0),
                                ),
                            ]
                        ),
                    )
                )

    leakcheck = data.get("leakcheck") or {}
    if leakcheck and not leakcheck.get("error") and leakcheck.get("found"):
        children.append(
            ChildNodeDef(
                title=f"LeakCheck: {leakcheck['found']} records",
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Engine", leakcheck.get("engine", "public")),
                        kv("Records", leakcheck.get("found", 0)),
                    ]
                ),
            )
        )
        for src in (leakcheck.get("sources") or [])[:CHILD_THRESHOLD]:
            children.append(
                ChildNodeDef(
                    title=str(src.get("name", "?")),
                    entity_type="Organization",
                    content=kv("Breach date", src.get("date", "?")),
                )
            )

    hibp = data.get("hibp") or {}
    for breach in (hibp.get("breaches") or [])[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=str(breach.get("Name", "?")),
                entity_type="Organization",
                content=_pack_content(
                    [
                        kv("Breach date", breach.get("BreachDate", "?")),
                        kv("Pwn count", breach.get("PwnCount", "?")),
                    ]
                ),
            )
        )

    lines = [divider(), title(f"Leaks: {target}")]
    if infostealer.get("error"):
        lines.append(fmt_info(f"Infostealer: {infostealer['error']}"))
    if leakcheck.get("error"):
        lines.append(fmt_info(f"LeakCheck: {leakcheck['error']}"))
    elif leakcheck.get("found"):
        lines.append(bullet(f"LeakCheck: {leakcheck['found']} records"))
    for breach in hibp.get("breaches") or []:
        lines.append(bullet(f"HIBP: {breach.get('Name', '?')}"))
    if not children:
        lines.append(fmt_info("No leaks found"))
    lines += [end_of("leak search"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_leak_search(target, modules):
    engine = modules.get("leak_search")
    if not engine:
        return TransformResult(content="Leak module not available")
    data = await engine.search_all(target)
    return _parse_leak_search(data, target)


# ── Archive ───────────────────────────────────────────────────────


def _parse_archive_snapshots(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        err = (data or {}).get("error", "error")
        return TransformResult(content=f"Wayback snapshots unavailable: {err}")
    children = []
    for snap in (data.get("snapshots") or [])[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=str(snap.get("timestamp", "?")),
                entity_type="Custom",
                content=kv("URL", snap.get("url", "?")),
                evidence=[snap.get("url", "")] if snap.get("url") else [],
            )
        )
    lines = [
        divider(),
        title(f"Wayback snapshots: {domain}"),
        kv("Count", data.get("count", 0)),
    ]
    for snap in data.get("snapshots") or []:
        lines.append(bullet(f"{snap.get('timestamp', '?')} {snap.get('url', '')}"))
    lines += [end_of("archive lookup"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_archive_snapshots(domain, modules):
    engine = modules.get("archive_search")
    if not engine:
        return TransformResult(content="Archive module not available")
    data = await engine.snapshots(domain)
    return _parse_archive_snapshots(data, domain)


# ── Geo ───────────────────────────────────────────────────────────


def _parse_geo_sun_shadow(data, target):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    content = _pack_content(
        [
            divider(),
            title(f"Sun / shadow: {target}"),
            kv("Time (UTC)", data.get("time_utc", "?")),
            kv("Sun altitude", f"{data.get('sun_altitude_deg')} deg"),
            kv("Sun azimuth", f"{data.get('sun_azimuth_deg')} deg"),
            kv("Shadow bearing", f"{data.get('shadow_bearing_deg')} deg"),
            kv("Shadow ratio", data.get("shadow_ratio")),
            end_of("geo analysis"),
            divider(),
        ]
    )
    children = [
        ChildNodeDef(
            title=f"Shadow {data.get('shadow_bearing_deg')} deg",
            entity_type="Custom",
            content=content,
        )
    ]
    return TransformResult(children=children, content=content)


def _haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


async def _transform_geo_sun_shadow(target, modules):
    engine = modules.get("geo_analysis")
    if not engine:
        return TransformResult(content="Geo module not available")
    coords = engine.parse_coords(target)
    if coords is None:
        return TransformResult(content=f"Invalid coordinates: {target}")
    data = engine.sun_shadow(coords[0], coords[1], datetime.now(UTC))
    return _parse_geo_sun_shadow(data, target)


def _parse_geo_gdacs(data, target):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(
            content=f"GDACS unavailable: {(data or {}).get('error', 'error')}"
        )
    coords = data.get("_coords") or (None, None)
    children = []
    for event in data.get("events") or []:
        lat, lon = event.get("latitude"), event.get("longitude")
        distance = ""
        if coords[0] is not None and lat is not None and lon is not None:
            distance = kv(
                "Distance (km)",
                round(_haversine_km(coords[0], coords[1], lat, lon), 1),
            )
        children.append(
            ChildNodeDef(
                title=f"{event.get('event_type', '?')}: {event.get('name', '?')}",
                entity_type="Geolocation",
                content=_pack_content(
                    [
                        kv("Alert level", event.get("alert_level", "?")),
                        kv("Country", event.get("country", "?")),
                        kv("Date", event.get("from_date", "?")),
                        f"{kv('Coordinates', f'{lat}, {lon}')}" if lat else "",
                        distance,
                    ]
                ),
                evidence=[
                    f"https://www.gdacs.org/report.aspx?eventtype="
                    f"{event.get('event_type', '')}&eventid={event.get('event_id', '')}"
                ],
            )
        )
    lines = [
        divider(),
        title(f"GDACS near {target}"),
        kv("Events", data.get("count", 0)),
    ]
    for event in (data.get("events") or [])[:15]:
        lines.append(bullet(f"{event.get('event_type')}: {event.get('name')}"))
    lines += [end_of("disaster lookup"), divider()]
    return TransformResult(
        children=children[:CHILD_THRESHOLD], content=_pack_content(lines)
    )


async def _transform_geo_gdacs(target, modules):
    engine = modules.get("geo_analysis")
    if not engine:
        return TransformResult(content="Geo module not available")
    data = await engine.gdacs()
    coords = engine.parse_coords(target)
    data["_coords"] = coords or (None, None)
    return _parse_geo_gdacs(data, target)


# ── Additional transforms ─────────────────────────────────────────


def _parse_instagram_profile(data, username):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"Instagram unavailable: {data['error']}")

    handle = str(data.get("username") or username).lstrip("@")
    url = f"https://www.instagram.com/{handle}/" if handle else ""
    profile = _pack_content(
        [
            kv("Handle", f"@{handle}"),
            kv("Full name", data.get("full_name", "")),
            kv("Biography", data.get("biography", "")),
            kv("Followers", data.get("followers", "?")),
            kv("Following", data.get("followees", "?")),
            kv("Posts", data.get("posts", "?")),
            kv("Private", data.get("is_private", "?")),
            kv("Verified", data.get("is_verified", "?")),
            kv("External URL", data.get("external_url", "")),
            kv("User ID", data.get("userid", "")),
        ]
    )
    children = [
        ChildNodeDef(
            title=f"@{handle}" if handle else "Instagram profile",
            entity_type="Custom",
            content=profile,
            evidence=[url] if url else [],
        )
    ]
    lines = [divider(), title(f"Instagram: @{handle}")]
    if data.get("full_name"):
        lines.append(bullet(data["full_name"]))
    if data.get("biography"):
        lines.append(bullet(data["biography"]))
    lines.append(kv("Followers", data.get("followers", "?")))
    lines.append(kv("Posts", data.get("posts", "?")))
    if data.get("external_url"):
        lines.append(kv("External URL", data["external_url"]))
    lines += [end_of("instagram"), divider()]
    return TransformResult(
        children=children,
        content=_pack_content(lines),
        evidence=[url] if url else [],
    )


async def _transform_instagram_profile(username, modules):
    engine = modules.get("social_search")
    if not engine:
        return TransformResult(content="Social module not available")
    data = await engine.instagram_profile(username)
    return _parse_instagram_profile(data, username)


def _parse_github_user(data, username):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"GitHub unavailable: {data['error']}")

    profile = data.get("profile") or {}
    login = str(profile.get("login") or username)
    url = f"https://github.com/{login}"
    profile_text = _pack_content(
        [
            kv("Login", login),
            kv("Name", profile.get("name", "")),
            kv("Company", profile.get("company", "")),
            kv("Location", profile.get("location", "")),
            kv("Blog", profile.get("blog", "")),
            kv("Email", profile.get("email", "")),
            kv("Twitter", profile.get("twitter", "")),
            kv("Bio", profile.get("bio", "")),
            kv("Public repos", profile.get("public_repos", "?")),
            kv("Followers", profile.get("followers", "?")),
            kv("Following", profile.get("following", "?")),
            kv("Created", profile.get("created", "")),
            kv("Type", profile.get("type", "")),
        ]
    )
    children = [
        ChildNodeDef(
            title=f"GitHub: {login}",
            entity_type="Custom",
            content=profile_text,
            evidence=[url],
        )
    ]
    repos = data.get("repos") or []
    for repo in repos[:CHILD_THRESHOLD]:
        repo_name = repo.get("full_name", "?")
        children.append(
            ChildNodeDef(
                title=repo_name,
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Repository", repo_name),
                        kv("Language", repo.get("language", "N/A")),
                    ]
                ),
                evidence=[f"https://github.com/{repo_name}"],
            )
        )
    if len(repos) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(repos) - CHILD_THRESHOLD} more repos",
                entity_type="Custom",
                content="\n".join(
                    str(repo.get("full_name", "?")) for repo in repos[CHILD_THRESHOLD:]
                ),
            )
        )

    lines = [
        divider(),
        title(f"GitHub profile: {login}"),
        kv("Name", profile.get("name", "")),
        kv("Repos", profile.get("public_repos", "?")),
        kv("Followers", profile.get("followers", "?")),
        kv("Location", profile.get("location", "")),
    ]
    lines += [end_of("github profile"), divider()]
    return TransformResult(
        children=children,
        content=_pack_content(lines),
        evidence=[url],
    )


async def _transform_github_user(username, modules):
    engine = modules.get("github_search")
    if not engine:
        return TransformResult(content="GitHub module not available")
    data = await engine.search_user(username)
    return _parse_github_user(data, username)


def _parse_github_repos(data, query):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(
            content=f"GitHub repositories unavailable: {data['error']}"
        )
    repos = data.get("repositories") or []
    children = []
    for repo in repos[:CHILD_THRESHOLD]:
        name = repo.get("full_name", "?")
        children.append(
            ChildNodeDef(
                title=name,
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Repository", name),
                        kv("Description", repo.get("description", "")),
                        kv("Language", repo.get("language", "N/A")),
                        kv("Stars", repo.get("stars", "?")),
                        kv("Forks", repo.get("forks", "?")),
                    ]
                ),
                evidence=[repo.get("url", "")] if repo.get("url") else [],
            )
        )
    if len(repos) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(repos) - CHILD_THRESHOLD} more repos",
                entity_type="Custom",
                content="\n".join(
                    str(repo.get("full_name", "?")) for repo in repos[CHILD_THRESHOLD:]
                ),
            )
        )
    lines = [
        divider(),
        title(f"GitHub repositories: {query}"),
        kv("Found", len(repos)),
    ]
    for repo in repos[:20]:
        lines.append(
            bullet(f"{repo.get('full_name', '?')} ({repo.get('stars', 0)} stars)")
        )
    for err in data.get("errors") or []:
        lines.append(fmt_info(err))
    if not repos:
        lines.append(fmt_info(data.get("message", "No repositories found")))
    lines += [end_of("github repositories"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_github_repos(query, modules):
    engine = modules.get("github_search")
    if not engine:
        return TransformResult(content="GitHub module not available")
    data = await engine.search_repos(f"org:{query}")
    return _parse_github_repos(data, query)


def _parse_github_emails(data, email):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(
            content=f"GitHub email search unavailable: {data['error']}"
        )
    results = data.get("results") or []
    children = []
    for item in results[:CHILD_THRESHOLD]:
        repo = item.get("repo", "?")
        children.append(
            ChildNodeDef(
                title=repo,
                entity_type="Organization",
                content=_pack_content(
                    [
                        kv("Repository", repo),
                        kv("Path", item.get("path", "")),
                        kv("Email", email),
                    ]
                ),
                evidence=[item.get("url", "")] if item.get("url") else [],
            )
        )
    if len(results) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(results) - CHILD_THRESHOLD} more files",
                entity_type="Custom",
                content="\n".join(
                    str(item.get("url", "")) for item in results[CHILD_THRESHOLD:]
                ),
            )
        )
    lines = [
        divider(),
        title(f"GitHub code search: {email}"),
        kv("Matches", len(results)),
    ]
    for item in results[:20]:
        lines.append(bullet(f"{item.get('repo', '?')}: {item.get('path', '')}"))
    for err in data.get("errors") or []:
        lines.append(fmt_info(err))
    if not results:
        lines.append(fmt_info(data.get("message", "No matches found")))
    lines += [end_of("github email search"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_github_emails(email, modules):
    engine = modules.get("github_search")
    if not engine:
        return TransformResult(content="GitHub module not available")
    data = await engine.search_emails(email)
    return _parse_github_emails(data, email)


def _shodan_vulns(data):
    vulns = data.get("vulns") or []
    if isinstance(vulns, dict):
        return list(vulns.keys())
    return list(vulns)


def _parse_shodan_host(data, ip):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"Shodan unavailable: {data['error']}")

    host_ip = data.get("ip", ip)
    hostnames = [str(name) for name in (data.get("hostnames") or []) if name]
    services = data.get("data") or []
    vulns = _shodan_vulns(data)
    lines = [
        divider(),
        title(f"Shodan host: {host_ip}"),
        kv("Organization", data.get("org", "?")),
        kv("ISP", data.get("isp", "?")),
        kv("ASN", data.get("asn", "?")),
        kv("OS", data.get("os", "?")),
        kv("Country", data.get("country_name", "?")),
        kv("City", data.get("city", "?")),
        kv("Last update", data.get("last_update", "?")),
        kv("Open ports", ", ".join(str(p) for p in data.get("ports", [])[:30])),
        kv("Hostnames", ", ".join(hostnames[:10])),
        kv("Vulnerabilities", len(vulns)),
    ]

    children = []
    org = data.get("org") or data.get("isp")
    if org:
        children.append(
            ChildNodeDef(
                title=str(org)[:60],
                entity_type="Organization",
                content=_pack_content(
                    [
                        kv("ISP", data.get("isp", "?")),
                        kv("ASN", data.get("asn", "?")),
                        kv("Organization", org),
                    ]
                ),
            )
        )
    lat = _safe_float(data.get("latitude"))
    lon = _safe_float(data.get("longitude"))
    if lat is not None and lon is not None:
        children.append(
            ChildNodeDef(
                title=f"{lat:.4f}, {lon:.4f}",
                entity_type="Geolocation",
                content=_pack_content(
                    [
                        kv("Latitude", lat),
                        kv("Longitude", lon),
                        kv("City", data.get("city", "?")),
                        kv("Country", data.get("country_name", "?")),
                    ]
                ),
            )
        )
    for hostname in hostnames[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=hostname,
                entity_type="Domain",
                content=kv("Hostname", hostname),
            )
        )
    for record in services[:CHILD_THRESHOLD]:
        port = record.get("port", "?")
        transport = record.get("transport", "tcp")
        children.append(
            ChildNodeDef(
                title=f"Port {port}/{transport}",
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Port", port),
                        kv("Transport", transport),
                        kv("Product", record.get("product", "?")),
                        kv("Version", record.get("version", "?")),
                        kv("Module", (record.get("_shodan") or {}).get("module", "?")),
                        str(record.get("banner", ""))[:400],
                    ]
                ),
            )
        )
    for cve in vulns[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=str(cve),
                entity_type="Custom",
                content=kv("Vulnerability", cve),
                evidence=[f"https://www.shodan.io/host/{host_ip}"],
            )
        )
    lines += [end_of("shodan host"), divider()]
    return TransformResult(
        children=children,
        content=_pack_content(lines),
        evidence=[f"https://www.shodan.io/host/{host_ip}"],
    )


async def _transform_shodan_host(ip, modules):
    engine = modules.get("shodan_search")
    if not engine:
        return TransformResult(content="Shodan module not available")
    data = await engine.host(ip)
    return _parse_shodan_host(data, ip)


def _parse_shodan_dns(data, domain):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"Shodan DNS unavailable: {data['error']}")

    base = str(data.get("domain") or domain)
    records = data.get("data") or []
    seen = set()
    children = []
    for record in records:
        subdomain = str(record.get("subdomain") or "").strip()
        if subdomain:
            suffix = f".{base}"
            full = subdomain if subdomain.endswith(suffix) else f"{subdomain}.{base}"
        else:
            full = base
        if full in seen:
            continue
        seen.add(full)
        children.append(
            ChildNodeDef(
                title=full,
                entity_type="Domain",
                content=_pack_content(
                    [
                        kv("Subdomain", subdomain or base),
                        kv("Type", record.get("type", "?")),
                        kv("Value", record.get("value", "?")),
                        kv("Last seen", record.get("last_seen", "?")),
                    ]
                ),
            )
        )
        if len(children) >= CHILD_THRESHOLD:
            break

    lines = [
        divider(),
        title(f"Shodan DNS: {base}"),
        kv("Records", len(records)),
        kv("Unique names", len(seen)),
    ]
    for record in records[:20]:
        lines.append(
            bullet(
                f"{record.get('subdomain') or base} "
                f"{record.get('type', '?')} {record.get('value', '')}"
            )
        )
    lines += [end_of("shodan dns"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_shodan_dns(domain, modules):
    engine = modules.get("shodan_search")
    if not engine:
        return TransformResult(content="Shodan module not available")
    data = await engine.domain_info(domain)
    return _parse_shodan_dns(data, domain)


def _parse_shodan_search(data, query):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"Shodan search unavailable: {data['error']}")

    matches = data.get("matches") or []
    children = []
    for match in matches[:CHILD_THRESHOLD]:
        ip = match.get("ip_str", "?")
        port = match.get("port", "?")
        location = match.get("location") or {}
        hostnames = match.get("hostnames") or []
        children.append(
            ChildNodeDef(
                title=f"{ip}:{port}",
                entity_type="IP",
                content=_pack_content(
                    [
                        kv("IP", ip),
                        kv("Port", port),
                        kv("Hostnames", ", ".join(hostnames[:5])),
                        kv("Organization", match.get("org", "?")),
                        kv("Product", match.get("product", "?")),
                        kv("Country", location.get("country_name", "?")),
                        kv("City", location.get("city", "?")),
                    ]
                ),
                evidence=[f"https://www.shodan.io/host/{ip}"],
            )
        )
    if len(matches) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(matches) - CHILD_THRESHOLD} more hosts",
                entity_type="Custom",
                content="\n".join(
                    f"{m.get('ip_str', '?')}:{m.get('port', '?')}"
                    for m in matches[CHILD_THRESHOLD:]
                ),
            )
        )

    lines = [
        divider(),
        title(f"Shodan search: {query}"),
        kv("Total", data.get("total", len(matches))),
        kv("Matches", len(matches)),
    ]
    facets = data.get("facets") or {}
    for name, values in list(facets.items())[:5]:
        top = values[:5] if isinstance(values, list) else []
        if top:
            lines.append(
                bullet(
                    f"{name}: "
                    + ", ".join(
                        f"{item.get('value', '?')} ({item.get('count', '?')})"
                        for item in top
                        if isinstance(item, dict)
                    )
                )
            )
    for match in matches[:20]:
        lines.append(
            bullet(
                f"{match.get('ip_str', '?')}:{match.get('port', '?')} "
                f"{match.get('org', '') or match.get('product', '')}"
            )
        )
    if not matches:
        lines.append(fmt_info("No Shodan matches found"))
    lines += [end_of("shodan search"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_shodan_search(query, modules):
    engine = modules.get("shodan_search")
    if not engine:
        return TransformResult(content="Shodan module not available")
    data = await engine.search(query)
    return _parse_shodan_search(data, query)


async def _transform_shodan_domain_search(domain, modules):
    engine = modules.get("shodan_search")
    if not engine:
        return TransformResult(content="Shodan module not available")
    query = f"hostname:{domain}"
    data = await engine.search(query)
    return _parse_shodan_search(data, query)


async def _transform_shodan_org_search(org, modules):
    engine = modules.get("shodan_search")
    if not engine:
        return TransformResult(content="Shodan module not available")
    query = f'org:"{str(org).replace(chr(34), "")}"'
    data = await engine.search(query)
    return _parse_shodan_search(data, query)


def _parse_shodan_honeyscore(data, ip):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"Shodan unavailable: {data['error']}")
    score = data.get("honeyscore", "?")
    interpretation = "likely honeypot" if _honeyscore_is_high(score) else "low"
    lines = [
        divider(),
        title(f"Shodan honeyscore: {ip}"),
        kv("Score", score),
        kv("Interpretation", interpretation),
    ]
    lines += [end_of("honeyscore"), divider()]
    return TransformResult(
        children=[
            ChildNodeDef(
                title=f"Honeyscore: {score}",
                entity_type="Custom",
                content=_pack_content([kv("IP", ip), kv("Honeyscore", score)]),
                evidence=[f"https://www.shodan.io/host/{ip}"],
            )
        ],
        content=_pack_content(lines),
    )


def _honeyscore_is_high(score):
    try:
        return float(score) >= 0.5
    except (TypeError, ValueError):
        return False


async def _transform_shodan_honeyscore(ip, modules):
    engine = modules.get("shodan_search")
    if not engine:
        return TransformResult(content="Shodan module not available")
    data = await engine.honeyscore(ip)
    return _parse_shodan_honeyscore(data, ip)


def _parse_shodan_exploits(data, query):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"Shodan exploits unavailable: {data['error']}")

    matches = data.get("matches") or []
    children = []
    for match in matches[:CHILD_THRESHOLD]:
        label = match.get("cve") or match.get("source") or match.get("_id") or "Exploit"
        children.append(
            ChildNodeDef(
                title=str(label)[:70],
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Source", match.get("source", "?")),
                        kv("CVE", match.get("cve", "?")),
                        kv("Platform", match.get("platform", "?")),
                        kv("Date", match.get("date", "?")),
                        str(match.get("description", ""))[:500],
                    ]
                ),
                evidence=[str(match.get("source", ""))] if match.get("source") else [],
            )
        )
    if len(matches) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(matches) - CHILD_THRESHOLD} more exploits",
                entity_type="Custom",
                content="\n".join(
                    str(m.get("cve") or m.get("source") or m.get("_id") or "Exploit")
                    for m in matches[CHILD_THRESHOLD:]
                ),
            )
        )

    lines = [
        divider(),
        title(f"Shodan exploits: {query}"),
        kv("Total", data.get("total", len(matches))),
        kv("Matches", len(matches)),
    ]
    for match in matches[:20]:
        lines.append(
            bullet(
                f"{match.get('cve') or match.get('source') or 'Exploit'}: "
                f"{str(match.get('description', ''))[:120]}"
            )
        )
    if not matches:
        lines.append(fmt_info("No exploits found"))
    lines += [end_of("shodan exploits"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_shodan_exploits(query, modules):
    engine = modules.get("shodan_search")
    if not engine:
        return TransformResult(content="Shodan module not available")
    data = await engine.exploits(query)
    return _parse_shodan_exploits(data, query)


def _parse_email_hibp(data, email):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"HIBP unavailable: {data['error']}")
    if data.get("message"):
        return TransformResult(content=str(data["message"]))
    breaches = data.get("breaches") or []
    children = []
    for breach in breaches[:CHILD_THRESHOLD]:
        name = breach.get("name", "?")
        children.append(
            ChildNodeDef(
                title=str(name)[:60],
                entity_type="Organization",
                content=_pack_content(
                    [
                        kv("Breach", name),
                        kv("Domain", breach.get("domain", "?")),
                        kv("Date", breach.get("date", "?")),
                        kv("Records", breach.get("records", "?")),
                        kv("Data classes", ", ".join(breach.get("data") or [])),
                    ]
                ),
                evidence=[f"https://haveibeenpwned.com/PwnedWebsites#{name}"],
            )
        )
    lines = [
        divider(),
        title(f"HIBP: {email}"),
        kv("Breaches", len(breaches)),
    ]
    for breach in breaches[:20]:
        lines.append(bullet(f"{breach.get('name', '?')} ({breach.get('date', '?')})"))
    if not breaches:
        lines.append(fmt_info("No HIBP breaches found"))
    lines += [end_of("hibp"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_email_hibp(email, modules):
    engine = modules.get("mail_search")
    if not engine:
        return TransformResult(content="Mail module not available")
    data = await engine.check_hibp(email)
    return _parse_email_hibp(data, email)


def _parse_phone_7tel(data, phone):
    if not isinstance(data, dict):
        return TransformResult(content=str(data))
    if data.get("error"):
        return TransformResult(content=f"7tel unavailable: {data['error']}")
    url = data.get("url", "")
    lines = [divider(), title(f"7tel caller ID: {phone}")]
    if data.get("message"):
        lines.append(fmt_info(data["message"]))
    score = data.get("score")
    if score and score != "unknown":
        lines.append(kv("Score", score))
    info = data.get("info") or []
    if info:
        lines.append(bullet(", ".join(str(item) for item in info)))
    children = []
    if score and score != "unknown":
        children.append(
            ChildNodeDef(
                title=f"Reputation: {score}",
                entity_type="Custom",
                content=kv("Phone", phone) + "\n" + kv("Score", score),
                evidence=[url] if url else [],
            )
        )
    if info:
        children.append(
            ChildNodeDef(
                title="Caller ID details",
                entity_type="Custom",
                content="\n".join(str(item) for item in info),
                evidence=[url] if url else [],
            )
        )
    reviews = data.get("reviews") or []
    for review in reviews[:CHILD_THRESHOLD]:
        author = review.get("author", "?")
        children.append(
            ChildNodeDef(
                title=f"Review: {author}"[:60],
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Author", author),
                        kv("Date", review.get("date", "?")),
                        kv("Comment", review.get("comment", "")),
                    ]
                ),
                evidence=[url] if url else [],
            )
        )
        lines.append(bullet(f"{author}: {review.get('comment', '')}"))
    for similar in (data.get("similar") or [])[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=str(similar),
                entity_type="Phone",
                content=kv("Similar number", similar),
            )
        )
    lines += [end_of("7tel"), divider()]
    return TransformResult(
        children=children,
        content=_pack_content(lines),
        evidence=[url] if url else [],
    )


async def _transform_phone_7tel(phone, modules):
    engine = modules.get("phone_search")
    if not engine:
        return TransformResult(content="Phone module not available")
    data = await engine.search_7tel(phone)
    return _parse_phone_7tel(data, phone)


def _parse_domain_headers(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"HTTP headers: {domain}"))
    headers = {str(k).lower(): str(v) for k, v in (data.get("headers") or {}).items()}
    status = data.get("status_code", "?")
    final_url = str(data.get("final_url", ""))
    header_text = "\n".join(f"{key}: {val}" for key, val in headers.items())
    children = [
        ChildNodeDef(
            title=f"HTTP {status}",
            entity_type="Custom",
            content=header_text[:3000],
            evidence=[final_url] if final_url else [],
        )
    ]
    interesting = (
        "server",
        "x-powered-by",
        "content-security-policy",
        "strict-transport-security",
        "x-frame-options",
        "cf-ray",
        "via",
    )
    for key in interesting:
        if key in headers:
            children.append(
                ChildNodeDef(
                    title=f"{key}: {headers[key]}",
                    entity_type="Custom",
                    content=kv(key, headers[key]),
                )
            )
    lines = [
        divider(),
        title(f"HTTP headers: {domain}"),
        kv("Status", status),
        kv("Final URL", final_url),
        *[bullet(f"{key}: {val}") for key, val in headers.items()],
        end_of("http headers"),
        divider(),
    ]
    return TransformResult(
        children=children[: CHILD_THRESHOLD + 1], content=_pack_content(lines)
    )


async def _transform_domain_headers(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_http_headers", domain, _parse_domain_headers
    )


def _parse_domain_waf(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"WAF: {domain}"))
    providers = [str(p) for p in (data.get("waf_providers") or [])]
    server = data.get("server", "Unknown")
    children = []
    if not providers or providers == ["NONE"]:
        children.append(
            ChildNodeDef(
                title="No WAF detected",
                entity_type="Custom",
                content=kv("Server", server),
            )
        )
    else:
        for provider in providers[:CHILD_THRESHOLD]:
            children.append(
                ChildNodeDef(
                    title=f"WAF: {provider}",
                    entity_type="Custom",
                    content=_pack_content(
                        [kv("Provider", provider), kv("Server", server)]
                    ),
                )
            )
    lines = [
        divider(),
        title(f"WAF detection: {domain}"),
        kv("Detected", data.get("waf_detected", False)),
        kv("Providers", ", ".join(providers)),
        kv("Server", server),
        end_of("waf detection"),
        divider(),
    ]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_domain_waf(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "detect_waf", domain, _parse_domain_waf
    )


def _parse_domain_hosts(data, domain):
    if isinstance(data, dict) and data.get("error"):
        return TransformResult(content=f"Host discovery failed: {data['error']}")
    hosts = data if isinstance(data, list) else []
    children = [
        ChildNodeDef(title=str(host), entity_type="Domain", content=kv("Host", host))
        for host in hosts[:CHILD_THRESHOLD]
    ]
    if len(hosts) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(hosts) - CHILD_THRESHOLD} more hosts",
                entity_type="Domain",
                content="\n".join(str(host) for host in hosts[CHILD_THRESHOLD:]),
            )
        )
    lines = [divider(), title(f"Host discovery: {domain}"), kv("Found", len(hosts))]
    lines.extend(bullet(host) for host in hosts)
    if not hosts:
        lines.append(fmt_info("No additional hosts resolved"))
    lines += [end_of("host discovery"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_domain_hosts(domain, modules):
    return await _run_transform(
        modules, "domain_analyzer", "get_hosts", domain, _parse_domain_hosts
    )


def _parse_archive_availability(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Archive availability: {domain}"))
    snapshot = data.get("snapshot") or {}
    children = []
    if snapshot:
        url = snapshot.get("url", "")
        children.append(
            ChildNodeDef(
                title=f"Wayback: {snapshot.get('timestamp', '?')}",
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("URL", url),
                        kv("Timestamp", snapshot.get("timestamp", "?")),
                        kv("Status", snapshot.get("status", "")),
                    ]
                ),
                evidence=[url] if url else [],
            )
        )
    lines = [
        divider(),
        title(f"Archive availability: {domain}"),
        kv("Available", bool(snapshot)),
    ]
    if snapshot:
        lines.append(bullet(f"Wayback: {snapshot.get('url', '')}"))
    else:
        lines.append(fmt_info("No Wayback snapshot found"))
    lines += [end_of("archive availability"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_archive_availability(domain, modules):
    engine = modules.get("archive_search")
    if not engine:
        return TransformResult(content="Archive module not available")
    data = await engine.availability(domain)
    return _parse_archive_availability(data, domain)


def _parse_archive_check(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Archive check: {domain}"))
    children = []
    wayback = data.get("wayback") or {}
    snapshot = wayback.get("snapshot") or {}
    if snapshot:
        url = snapshot.get("url", "")
        children.append(
            ChildNodeDef(
                title=f"Wayback: {snapshot.get('timestamp', '?')}",
                entity_type="Custom",
                content=_pack_content(
                    [kv("URL", url), kv("Timestamp", snapshot.get("timestamp", "?"))]
                ),
                evidence=[url] if url else [],
            )
        )
    archive_today = data.get("archive_today") or {}
    if archive_today.get("found"):
        url = archive_today.get("snapshot", "")
        children.append(
            ChildNodeDef(
                title="archive.today snapshot",
                entity_type="Custom",
                content=_pack_content(
                    [kv("URL", url), kv("Status", archive_today.get("status", "?"))]
                ),
                evidence=[url] if url else [],
            )
        )
    lines = [
        divider(),
        title(f"Archive check: {domain}"),
        kv("Wayback", bool(snapshot)),
        kv("archive.today", bool(archive_today.get("found"))),
    ]
    if snapshot:
        lines.append(bullet(f"Wayback: {snapshot.get('url', '')}"))
    if archive_today.get("found"):
        lines.append(bullet(f"archive.today: {archive_today.get('snapshot', '')}"))
    lines += [end_of("archive check"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_archive_check(domain, modules):
    engine = modules.get("archive_search")
    if not engine:
        return TransformResult(content="Archive module not available")
    data = await engine.check(domain)
    return _parse_archive_check(data, domain)


def _parse_archive_save(data, domain):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Wayback save: {domain}"))
    archive_url = data.get("archive_url", "")
    children = []
    if archive_url:
        children.append(
            ChildNodeDef(
                title="Wayback snapshot saved",
                entity_type="Custom",
                content=_pack_content(
                    [
                        kv("Original URL", data.get("url", domain)),
                        kv("Archive URL", archive_url),
                    ]
                ),
                evidence=[archive_url],
            )
        )
    lines = [
        divider(),
        title(f"Wayback save: {domain}"),
        kv("Saved", data.get("saved", False)),
        kv("Archive URL", archive_url),
        end_of("wayback save"),
        divider(),
    ]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_archive_save(domain, modules):
    engine = modules.get("archive_search")
    if not engine:
        return TransformResult(content="Archive module not available")
    data = await engine.save(domain)
    return _parse_archive_save(data, domain)


def _parse_geo_firms(data, target):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"NASA FIRMS: {target}"))
    fires = data.get("fires") or []
    children = []
    for fire in fires[:CHILD_THRESHOLD]:
        lat, lon = fire.get("latitude"), fire.get("longitude")
        if lat is None or lon is None:
            continue
        children.append(
            ChildNodeDef(
                title=f"{lat}, {lon}",
                entity_type="Geolocation",
                content=_pack_content(
                    [
                        kv("Latitude", lat),
                        kv("Longitude", lon),
                        kv("Brightness", fire.get("brightness", "?")),
                        kv("FRP", fire.get("frp", "?")),
                        kv("Confidence", fire.get("confidence", "?")),
                        kv("Date", fire.get("date", "?")),
                        kv("Time", fire.get("time", "?")),
                    ]
                ),
            )
        )
    lines = [
        divider(),
        title(f"NASA FIRMS near {target}"),
        kv("Detections", data.get("count", 0)),
        kv("Source", data.get("source", "?")),
    ]
    for fire in fires[:20]:
        lines.append(
            bullet(
                f"{fire.get('latitude')}, {fire.get('longitude')} "
                f"({fire.get('date', '?')} {fire.get('time', '?')})"
            )
        )
    if not fires:
        lines.append(fmt_info("No active fires detected"))
    lines += [end_of("firms"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_geo_firms(target, modules):
    engine = modules.get("geo_analysis")
    if not engine:
        return TransformResult(content="Geo module not available")
    coords = engine.parse_coords(target)
    if coords is None:
        return TransformResult(content=f"Invalid coordinates: {target}")
    lat, lon = coords
    data = await engine.firms(bbox=(lon - 2.0, lat - 2.0, lon + 2.0, lat + 2.0))
    return _parse_geo_firms(data, target)


def _parse_geo_report(data, target):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Location report: {target}"))
    children = []
    lines = [divider(), title(f"Location report: {target}")]
    for name, value in data.items():
        children.append(
            ChildNodeDef(
                title=str(name)[:60],
                entity_type="Custom",
                content=render(value),
            )
        )
        lines.append(bullet(str(name)))
    lines += [end_of("location report"), divider()]
    return TransformResult(
        children=children[:CHILD_THRESHOLD], content=_pack_content(lines)
    )


async def _transform_geo_report(target, modules):
    engine = modules.get("geo_analysis")
    if not engine:
        return TransformResult(content="Geo module not available")
    coords = engine.parse_coords(target)
    if coords is None:
        return TransformResult(content=f"Invalid coordinates: {target}")
    data = await engine.report(coords[0], coords[1])
    return _parse_geo_report(data, target)


def _parse_geo_shadow_search(results, params):
    results = results or []
    children = []
    for item in results[:CHILD_THRESHOLD]:
        lat, lon = item.get("latitude"), item.get("longitude")
        if lat is None or lon is None:
            continue
        children.append(
            ChildNodeDef(
                title=f"{lat}, {lon}",
                entity_type="Geolocation",
                content=_pack_content(
                    [
                        kv("Latitude", lat),
                        kv("Longitude", lon),
                        kv("Sun altitude", item.get("sun_altitude_deg")),
                        kv("Shadow bearing", item.get("shadow_bearing_deg")),
                        kv("Error", item.get("error_deg")),
                    ]
                ),
            )
        )
    lines = [
        divider(),
        title("Shadow search"),
        kv("Ratio", params.get("ratio", "?")),
        kv("Bearing", params.get("bearing", "?")),
        kv("Candidates", len(results)),
    ]
    for item in results[:20]:
        lines.append(
            bullet(
                f"{item.get('latitude')}, {item.get('longitude')} "
                f"(err {item.get('error_deg')} deg)"
            )
        )
    if not results:
        lines.append(fmt_info("No matching coordinates found"))
    lines += [end_of("shadow search"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_geo_shadow_search(content, modules):
    engine = modules.get("geo_analysis")
    if not engine:
        return TransformResult(content="Geo module not available")
    ratio_match = re.search(
        r"shadow\s*ratio\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", content, re.IGNORECASE
    )
    bearing_match = re.search(
        r"shadow\s*bearing\s*[:=]\s*(-?[0-9]+(?:\.[0-9]+)?)", content, re.IGNORECASE
    )
    if not ratio_match or not bearing_match:
        return TransformResult(
            content=(
                "Shadow Search needs 'Shadow ratio: <n>' and "
                "'Shadow bearing: <deg>' in the node content."
            )
        )
    ratio = float(ratio_match.group(1))
    bearing = float(bearing_match.group(1))
    when = datetime.now(UTC)
    results = engine.shadow_search(ratio, bearing, when)
    params = {"ratio": ratio, "bearing": bearing, "time": when.isoformat()}
    return _parse_geo_shadow_search(results, params)


def _parse_photo_metadata(data, path):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Metadata: {path}"))
    text = render(data, f"Metadata: {Path(path).name}")
    return TransformResult(
        children=[
            ChildNodeDef(
                title="File metadata",
                entity_type="Custom",
                content=text,
                evidence=[path],
            )
        ],
        content=text,
        evidence=[path],
    )


async def _transform_photo_metadata(path, modules):
    engine = modules.get("file_analyzer")
    if not engine:
        return TransformResult(content="File analyzer module not available")
    data = await engine.get_metadata(path)
    return _parse_photo_metadata(data, path)


def _parse_photo_gps(coords, path):
    if not coords:
        return TransformResult(content=f"No GPS coordinates found in {Path(path).name}")
    lat, lon = coords
    content = _pack_content(
        [
            divider(),
            title(f"GPS: {Path(path).name}"),
            kv("Latitude", lat),
            kv("Longitude", lon),
            end_of("gps"),
            divider(),
        ]
    )
    return TransformResult(
        children=[
            ChildNodeDef(
                title=f"{lat}, {lon}",
                entity_type="Geolocation",
                content=content,
                evidence=[path],
            )
        ],
        content=content,
        evidence=[path],
    )


async def _transform_photo_gps(path, modules):
    engine = modules.get("file_analyzer")
    if not engine:
        return TransformResult(content="File analyzer module not available")
    coords = await engine.get_gps_coordinates(path)
    return _parse_photo_gps(coords, path)


def _parse_photo_stego(data, path):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"Steganography: {path}"))
    children = []
    for name, value in data.items():
        children.append(
            ChildNodeDef(
                title=str(name).title(),
                entity_type="Custom",
                content=str(value)[:4000],
                evidence=[path],
            )
        )
    lines = [divider(), title(f"Steganography: {Path(path).name}")]
    for name, value in data.items():
        first_line = str(value).splitlines()[0] if str(value).strip() else "empty"
        lines.append(bullet(f"{name}: {first_line}"))
    lines += [end_of("steganography"), divider()]
    return TransformResult(
        children=children[:CHILD_THRESHOLD],
        content=_pack_content(lines),
        evidence=[path],
    )


async def _transform_photo_stego(path, modules):
    engine = modules.get("steg_analyzer")
    if not engine:
        return TransformResult(content="Steganography module not available")
    data = await engine.run_full_analysis(path)
    return _parse_photo_stego(data, path)


def _parse_photo_faces(results, path):
    if not isinstance(results, list):
        return TransformResult(content=str(results))
    children = []
    for match in results[:CHILD_THRESHOLD]:
        first = match.get("first_name", "")
        last = match.get("last_name", "")
        name = (
            " ".join(part for part in (first, last) if part)
            or match.get("vk_url")
            or "Match"
        )
        children.append(
            ChildNodeDef(
                title=str(name)[:60],
                entity_type="Person",
                content=_pack_content(
                    [
                        kv("Name", name),
                        kv("Age", match.get("age", "?")),
                        kv("City", match.get("city", "")),
                        kv("Country", match.get("country", "")),
                        kv("Similarity", match.get("similarity", "?")),
                        kv("Profile", match.get("vk_url", "")),
                    ]
                ),
                evidence=[
                    url for url in (match.get("vk_url"), match.get("photo_url")) if url
                ],
            )
        )
    if len(results) > CHILD_THRESHOLD:
        children.append(
            ChildNodeDef(
                title=f"+{len(results) - CHILD_THRESHOLD} more matches",
                entity_type="Person",
                content="\n".join(
                    match.get("vk_url", "") for match in results[CHILD_THRESHOLD:]
                ),
            )
        )
    lines = [
        divider(),
        title(f"Face search: {Path(path).name}"),
        kv("Matches", len(results)),
    ]
    for match in results[:20]:
        name = " ".join(
            part for part in (match.get("first_name"), match.get("last_name")) if part
        )
        lines.append(
            bullet(
                f"{name or match.get('vk_url', '?')} ({match.get('similarity', '?')})"
            )
        )
    if not results:
        lines.append(fmt_info("No faces found"))
    lines += [end_of("face search"), divider()]
    return TransformResult(
        children=children, content=_pack_content(lines), evidence=[path]
    )


async def _transform_photo_faces(path, modules):
    engine = modules.get("search4faces")
    if not engine:
        return TransformResult(content="Search4Faces module not available")
    results = await engine.search_face(path)
    return _parse_photo_faces(results, path)


def _parse_photo_virustotal(data, path):
    if not isinstance(data, dict) or data.get("error"):
        return TransformResult(content=render(data, f"VirusTotal: {path}"))
    lines = [
        divider(),
        title(f"VirusTotal: {Path(path).name}"),
        kv("Hash", data.get("hash", "?")),
        kv("Malicious", data.get("malicious", 0)),
        kv("Suspicious", data.get("suspicious", 0)),
        kv("Harmless", data.get("harmless", 0)),
        kv("Undetected", data.get("undetected", 0)),
    ]
    children = []
    for detected in (data.get("detected") or [])[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=str(detected)[:60],
                entity_type="Custom",
                content=str(detected),
                evidence=[path],
            )
        )
    for detected in data.get("detected") or []:
        lines.append(bullet(str(detected)))
    lines += [end_of("virustotal"), divider()]
    return TransformResult(
        children=children,
        content=_pack_content(lines),
        evidence=[path],
    )


async def _transform_photo_virustotal(path, modules):
    engine = modules.get("file_analyzer")
    if not engine:
        return TransformResult(content="File analyzer module not available")
    data = await engine.virustotal_analyze(path)
    return _parse_photo_virustotal(data, path)


def _parse_web_search(text, query):
    if not isinstance(text, str):
        return TransformResult(content=str(text))
    stripped = text.strip()
    if not stripped or stripped == "Not found.":
        return TransformResult(content=f"Web search: {query}\n  · Not found.")
    if stripped.startswith("Error:"):
        return TransformResult(content=f"Web search failed: {stripped[6:].strip()}")
    pattern = re.compile(
        r"\n\d+\s+-\s+(.*?)\nURL:\s*(.*?)\nSNIPPET:\s*(.*?)(?=\n\d+\s+-|\Z)",
        re.DOTALL,
    )
    matches = pattern.findall(text)
    children = []
    for title_text, url, snippet in matches[:CHILD_THRESHOLD]:
        children.append(
            ChildNodeDef(
                title=" ".join(title_text.split())[:60] or url,
                entity_type="Custom",
                content=" ".join(snippet.split()),
                evidence=[url] if url else [],
            )
        )
    lines = [divider(), title(f"Web search: {query}"), kv("Results", len(matches))]
    for title_text, url, _snippet in matches[:10]:
        lines.append(bullet(f"{' '.join(title_text.split())}: {url}"))
    if not matches:
        lines.append(fmt_info("No results parsed"))
    lines += [end_of("web search"), divider()]
    return TransformResult(children=children, content=_pack_content(lines))


async def _transform_web_search(query, modules):
    engine = modules.get("dorks_search_engine")
    if not engine:
        return TransformResult(content="Web search module not available")
    text = await engine.search_dork(query)
    return _parse_web_search(text, query)


__all__ = [
    name
    for name, value in globals().items()
    if (inspect.isfunction(value) or inspect.isclass(value))
    and getattr(value, "__module__", None) == __name__
]
