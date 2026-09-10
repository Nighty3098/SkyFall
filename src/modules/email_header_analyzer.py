import asyncio
import re
import socket
from email import message_from_binary_file, message_from_string
from email.message import Message
from email.policy import default as default_policy
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

import dns.resolver
import httpx
from loguru import logger

from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    error,
    info,
    kv,
    line,
    section,
    title,
)

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IP_BRACKET_RE = re.compile(r"\[(\d{1,3}(?:\.\d{1,3}){3})\]")
RECEIVED_FROM_BY_RE = re.compile(
    r"from\s+(?P<from>.+?)\s+by\s+(?P<by>.+?)(?:\s+with\s+(?P<with>.+?))?"
    r"(?:\s+id\s+(?P<id>\S+?))?(?:\s+for\s+<(?P<for>[^>]+)>|;(?P<date>.*))?$",
    re.IGNORECASE | re.DOTALL,
)
AUTH_RES_RE = re.compile(
    r"(?P<method>spf|dkim|dmarc)\s*=\s*(?P<result>\w+)", re.IGNORECASE
)
HELO_RE = re.compile(r"helo=([^\s;]+)", re.IGNORECASE)
MAILFROM_RE = re.compile(r"mailfrom=([^\s;]+)", re.IGNORECASE)
HEADER_FROM_RE = re.compile(r"header\.from=([^\s;]+)", re.IGNORECASE)

PRIVATE_NETS = (
    "10.",
    "192.168.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "127.",
    "169.254.",
)


def _is_private_ip(ip: str) -> bool:
    return ip.startswith(PRIVATE_NETS)


def _parse_received(raw: str) -> dict:
    """Parse a single Received header into from/by/with/for/date/ips."""
    unfolded = " ".join(raw.replace("\r", "").split())
    parsed: dict = {"raw": unfolded, "ips": IP_RE.findall(unfolded)}

    m = RECEIVED_FROM_BY_RE.search(unfolded)
    if m:
        parsed["from"] = (m.group("from") or "").strip()
        parsed["by"] = (m.group("by") or "").strip()
        if m.group("with"):
            parsed["with"] = m.group("with").strip()
        if m.group("id"):
            parsed["id"] = m.group("id").strip()
        if m.group("for"):
            parsed["for"] = m.group("for").strip()
        if m.group("date"):
            parsed["date"] = m.group("date").strip()
    else:
        # Fallback: split off trailing date after ';'
        if ";" in unfolded:
            head, tail = unfolded.rsplit(";", 1)
            parsed["date"] = tail.strip()
            parsed["head"] = head.strip()
        else:
            parsed["head"] = unfolded
    return parsed


class EmailHeaderAnalyzer:
    """Phishing-oriented email header / .eml analyzer (offline-first)."""

    def __init__(self, geo_timeout: float = 8.0, dns_timeout: float = 8.0):
        logger.debug("Init: EmailHeaderAnalyzer")
        self.geo_timeout = geo_timeout
        self.dns_timeout = dns_timeout

    # ── public API ────────────────────────────────────────────────

    async def analyze_file(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return "\n".join(
                [
                    divider(),
                    title("Email Header Analysis"),
                    error(f"File '{p}' not found."),
                    end_of("email header analysis"),
                    divider(),
                ]
            )
        try:

            def _read() -> Message:
                with open(p, "rb") as f:
                    return message_from_binary_file(f, policy=default_policy)

            msg = await asyncio.to_thread(_read)
            return await self.analyze_message(msg, source=str(p))
        except Exception as e:
            logger.error(f"EML analyze failed: {e}")
            return "\n".join(
                [
                    divider(),
                    title("Email Header Analysis"),
                    error(f"Parse failed: {e}"),
                    end_of("email header analysis"),
                    divider(),
                ]
            )

    async def analyze_text(self, raw_headers: str) -> str:
        if not raw_headers.strip():
            return "\n".join(
                [
                    divider(),
                    title("Email Header Analysis"),
                    error("Empty headers text."),
                    end_of("email header analysis"),
                    divider(),
                ]
            )
        try:
            msg = await asyncio.to_thread(
                message_from_string, raw_headers, default_policy
            )
            return await self.analyze_message(msg, source="pasted headers")
        except Exception as e:
            logger.error(f"Header text analyze failed: {e}")
            return "\n".join(
                [
                    divider(),
                    title("Email Header Analysis"),
                    error(f"Parse failed: {e}"),
                    end_of("email header analysis"),
                    divider(),
                ]
            )

    async def analyze_message(self, msg: Message, source: str = "") -> str:
        out = [
            divider(),
            title(f"Email Header Analysis{f': {source}' if source else ''}"),
        ]

        envelope = self._envelope_section(msg)
        out.append(section("Envelope & Addresses"))
        out.extend(envelope["lines"])

        received_raw = msg.get_all("Received", [])
        received = [_parse_received(r) for r in received_raw]
        out.append(section(f"Received Chain ({len(received)} hops)"))
        if received:
            # Headers list top (final MTA) first → reverse for chronological path
            for i, hop in enumerate(reversed(received), 1):
                out.append(line(f"Hop {i} (chronological):"))
                for key in ("from", "by", "with", "id", "for", "date", "head"):
                    if hop.get(key):
                        out.append(kv(f"    {key}", hop[key]))
                if hop.get("ips"):
                    out.append(kv("    ips", ", ".join(hop["ips"])))
        else:
            out.append(
                info("No Received headers — highly suspicious for inbound mail.")
            )

        auth_lines, auth = self._auth_section(msg)
        out.append(section("Authentication (SPF/DKIM/DMARC)"))
        out.extend(auth_lines)

        dns_lines = await self._dns_section(envelope["from_domain"])
        out.append(section("Sender Domain DNS (SPF/DMARC records)"))
        out.extend(dns_lines)

        sender_ip = self._pick_sender_ip(received)
        if sender_ip:
            geo_lines = await self._geo_section(sender_ip)
            out.append(section(f"Origin IP: {sender_ip}"))
            out.extend(geo_lines)
        else:
            out.append(section("Origin IP"))
            out.append(info("No public origin IP found in Received chain."))

        verdict_lines = self._verdict_section(msg, envelope, received, auth, sender_ip)
        out.append(section("Phishing Verdict"))
        out.extend(verdict_lines)

        out.append(end_of("email header analysis"))
        out.append(divider())
        return "\n".join(out)

    # ── sections ──────────────────────────────────────────────────

    def _addr_list(self, msg: Message, name: str) -> list[str]:
        addrs = []
        for _, addr in getaddresses(msg.get_all(name, [])):
            if addr:
                addrs.append(addr)
        return addrs

    def _envelope_section(self, msg: Message) -> dict:
        lines = []
        from_addrs = self._addr_list(msg, "From")
        reply_to = self._addr_list(msg, "Reply-To")
        to_addrs = self._addr_list(msg, "To")
        return_path = (msg.get("Return-Path", "") or "").strip().strip("<>")

        from_domain = ""
        if from_addrs and "@" in from_addrs[0]:
            from_domain = from_addrs[0].rsplit("@", 1)[1].lower().strip(" >")

        lines.append(kv("From", ", ".join(from_addrs) or "MISSING"))
        lines.append(kv("Reply-To", ", ".join(reply_to) or "(same as From)"))
        lines.append(kv("To", ", ".join(to_addrs) or "MISSING"))
        lines.append(kv("Return-Path", return_path or "MISSING"))
        lines.append(kv("Subject", str(msg.get("Subject", "")) or "(empty)"))

        date_raw = msg.get("Date", "")
        if date_raw:
            try:
                dt = parsedate_to_datetime(str(date_raw))
                lines.append(kv("Date", f"{dt.isoformat()} (raw: {date_raw})"))
            except Exception:
                lines.append(kv("Date", f"{date_raw} (unparseable!)"))
        else:
            lines.append(kv("Date", "MISSING"))

        lines.append(kv("Message-ID", str(msg.get("Message-ID", "")) or "MISSING"))
        x_mailer = (
            msg.get("X-Mailer") or msg.get("User-Agent") or msg.get("X-Originating-IP")
        )
        if x_mailer:
            lines.append(kv("X-Mailer/Agent/IP", str(x_mailer)))
        return {
            "lines": lines,
            "from_addrs": from_addrs,
            "reply_to": reply_to,
            "return_path": return_path,
            "from_domain": from_domain,
        }

    def _auth_section(self, msg: Message) -> tuple[list[str], dict]:
        lines = []
        auth: dict = {"spf": None, "dkim": None, "dmarc": None}
        for hdr in ("Authentication-Results", "ARC-Authentication-Results"):
            for val in msg.get_all(hdr, []):
                flat = " ".join(str(val).replace("\r", "").split())
                for m in AUTH_RES_RE.finditer(flat):
                    auth[m.group("method").lower()] = m.group("result").lower()
                lines.append(line(f"{hdr}: {flat[:220]}"))
        spf_recv = msg.get_all("Received-SPF", [])
        for val in spf_recv:
            flat = " ".join(str(val).replace("\r", "").split())
            lines.append(line(f"Received-SPF: {flat[:220]}"))
            if auth["spf"] is None:
                low = flat.lower()
                for token in (
                    "pass",
                    "fail",
                    "softfail",
                    "neutral",
                    "none",
                    "permerror",
                    "temperror",
                ):
                    if low.startswith(token):
                        auth["spf"] = token
                        break
        dkim_sig = msg.get("DKIM-Signature", "")
        if dkim_sig:
            flat = " ".join(str(dkim_sig).replace("\r", "").split())
            m = re.search(r"d=([^;\s]+)", flat)
            lines.append(line(f"DKIM-Signature present (d={m.group(1) if m else '?'})"))
        else:
            lines.append(info("No DKIM-Signature header."))
        for method in ("spf", "dkim", "dmarc"):
            lines.append(kv(method.upper(), auth[method] or "not found"))
        return lines, auth

    async def _dns_section(self, domain: str) -> list[str]:
        lines = []
        if not domain:
            return [info("No From domain — skipping DNS checks.")]
        spf = await self._txt_lookup(domain)
        if spf is None:
            lines.append(line("SPF: DNS lookup failed (offline?)"))
        elif spf:
            lines.append(line(f"SPF record: {spf[:220]}"))
        else:
            lines.append(
                error(
                    "SPF: no TXT record starting with v=spf1 — domain can be spoofed!"
                )
            )
        dmarc = await self._txt_lookup(f"_dmarc.{domain}")
        if dmarc is None:
            lines.append(line("DMARC: DNS lookup failed (offline?)"))
        elif dmarc:
            m = re.search(r"p=([^;\s]+)", dmarc, re.IGNORECASE)
            lines.append(line(f"DMARC record: {dmarc[:220]}"))
            lines.append(kv("DMARC policy", m.group(1) if m else "unknown"))
        else:
            lines.append(
                error("DMARC: no _dmarc record — spoofed mail will not be rejected!")
            )
        return lines

    async def _txt_lookup(self, name: str) -> str | None:
        def _query():
            try:
                resolver = dns.resolver.Resolver()
                resolver.lifetime = 5
                resolver.timeout = 2
                answers = resolver.resolve(name, "TXT")
                for r in answers:
                    txt = b"".join(r.strings).decode("utf-8", errors="replace")
                    if name.startswith("_dmarc") and txt.lower().startswith("v=dmarc"):
                        return txt
                    if not name.startswith("_dmarc") and txt.lower().startswith(
                        "v=spf1"
                    ):
                        return txt
                return ""
            except Exception:
                return None

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_query), timeout=self.dns_timeout
            )
        except TimeoutError:
            return None

    def _pick_sender_ip(self, received: list[dict]) -> str | None:
        # Earliest hop = last Received header = first chronologically
        for hop in reversed(received):
            for ip in hop.get("ips", []):
                if not _is_private_ip(ip):
                    return ip
        return None

    async def _geo_section(self, ip: str) -> list[str]:
        lines = []
        lines.append(
            kv(
                "Private/loopback",
                "yes (internal hop)" if _is_private_ip(ip) else "no (public)",
            )
        )

        def _rdns():
            try:
                return socket.gethostbyaddr(ip)[0]
            except Exception:
                return None

        try:
            rdns = await asyncio.wait_for(
                asyncio.to_thread(_rdns), timeout=self.dns_timeout
            )
        except TimeoutError:
            rdns = None
        lines.append(kv("Reverse DNS", rdns or "none"))

        try:
            async with httpx.AsyncClient(timeout=self.geo_timeout) as client:
                resp = await client.get(
                    f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,as,proxy,hosting,query"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        lines.append(
                            kv(
                                "Geo",
                                f"{data.get('country')}, "
                                f"{data.get('regionName')}, "
                                f"{data.get('city')}",
                            )
                        )
                        lines.append(
                            kv("ISP/Org", f"{data.get('isp')} / {data.get('org')}")
                        )
                        lines.append(kv("AS", data.get("as") or "?"))
                        flags = []
                        if data.get("proxy"):
                            flags.append("PROXY/VPN")
                        if data.get("hosting"):
                            flags.append("HOSTING/DC")
                        lines.append(kv("Flags", ", ".join(flags) if flags else "none"))
                    else:
                        lines.append(line(f"Geo lookup failed: {data}"))
                else:
                    lines.append(line(f"Geo lookup HTTP {resp.status_code}"))
        except Exception as e:
            lines.append(line(f"Geo lookup unavailable (offline?): {e}"))
        return lines

    def _verdict_section(
        self,
        msg: Message,
        envelope: dict,
        received: list[dict],
        auth: dict,
        sender_ip: str | None,
    ) -> list[str]:
        signals = []

        from_addrs = envelope["from_addrs"]
        rp = envelope["return_path"]
        if from_addrs and rp and rp.lower() != from_addrs[0].lower():
            signals.append(f"Return-Path mismatch: {rp} vs From {from_addrs[0]}")
        if envelope["reply_to"] and from_addrs and envelope["reply_to"] != from_addrs:
            signals.append(f"Reply-To differs from From: {envelope['reply_to']}")

        for method in ("spf", "dkim", "dmarc"):
            if auth.get(method) in ("fail", "softfail", "permerror"):
                signals.append(f"{method.upper()}={auth[method]}")

        if not received:
            signals.append("Missing Received chain")
        if not msg.get("Message-ID"):
            signals.append("Missing Message-ID")
        if not msg.get("Date"):
            signals.append("Missing Date")

        from_domain = envelope["from_domain"]
        msg_id = str(msg.get("Message-ID", ""))
        if from_domain and msg_id and from_domain not in msg_id.lower():
            signals.append(
                f"Message-ID domain differs from From domain ({msg_id[:80]})"
            )

        lines = []
        if not signals:
            lines.append(info("No spoofing indicators found. Risk: LOW."))
        elif len(signals) == 1:
            lines.append(error("1 warning sign. Risk: MEDIUM."))
        else:
            lines.append(
                error(
                    f"{len(signals)} warning signs. Risk: HIGH — likely phishing/spoof."
                )
            )
        for s in signals:
            lines.append(bullet(s))
        return lines
