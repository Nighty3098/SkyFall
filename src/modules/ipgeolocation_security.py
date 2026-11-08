"""IPGeolocation.io IP security/threat lookup.

Uses the IPGeolocation API (``security=1``) to return anonymizer and risk
signals for an IP: threat score, VPN/proxy/Tor/bot flags, provider details,
and cloud/attacker/spam indicators. Requires an optional API key.
"""

from __future__ import annotations

import asyncio
import ipaddress

import requests
from loguru import logger

API_URL = "https://api.ipgeolocation.io/ipgeo"


def _is_ip(value):
    try:
        ipaddress.ip_address((value or "").strip())
        return True
    except (TypeError, ValueError):
        return False


def _pick(mapping, *keys, default=None):
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def classify_security(security):
    """Return (status, reasons) from an IPGeolocation security payload.

    This is a triage signal, not a verdict: VPN/proxy/cloud usage can be
    legitimate. Strong indicators escalate status.
    """
    if not isinstance(security, dict):
        return "UNKNOWN", []

    reasons = []
    score = _pick(security, "threat_score", "threatScore", default=0)
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 0

    flags = {
        "known attacker": bool(security.get("is_known_attacker")),
        "spam source": bool(security.get("is_spam")),
        "bot": bool(security.get("is_bot")),
        "Tor": bool(security.get("is_tor")),
        "proxy": bool(security.get("is_proxy")),
        "VPN": bool(security.get("is_vpn")),
        "anonymous": bool(security.get("is_anonymous")),
        "cloud provider": bool(security.get("is_cloud_provider")),
    }
    for label, enabled in flags.items():
        if enabled:
            reasons.append(label)

    if flags["known attacker"] or flags["spam source"] or score >= 85:
        return "MALICIOUS", reasons or [f"threat score {score}"]
    if flags["bot"] or flags["Tor"] or score >= 60:
        return "SUSPICIOUS", reasons or [f"threat score {score}"]
    if flags["proxy"] or flags["VPN"] or flags["anonymous"] or score >= 25:
        return "SUSPICIOUS", reasons or [f"threat score {score}"]
    if reasons:
        return "INFO", reasons
    return "CLEAN", [f"threat score {score}"]


class IPGeolocationSecurity:
    def __init__(self, api_key="", timeout=15):
        logger.debug("Init: IPGeolocationSecurity")
        self.api_key = (api_key or "").strip()
        self.timeout = timeout

    async def check(self, ip):
        logger.debug("Trying to check IPGeolocation security")
        ip = (ip or "").strip()
        if not _is_ip(ip):
            return {
                "source": "IPGeolocation",
                "status": "SKIPPED",
                "note": "Valid IP address required",
            }
        if not self.api_key:
            return {
                "source": "IPGeolocation",
                "status": "SKIPPED",
                "note": "API key not configured",
            }

        def _do():
            return requests.get(
                API_URL,
                params={"apiKey": self.api_key, "ip": ip, "security": 1},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )

        try:
            resp = await asyncio.to_thread(_do)
        except Exception as e:
            logger.debug(f"IPGeolocation security failed for {ip}: {e}")
            return {"source": "IPGeolocation", "status": "ERROR", "note": str(e)[:200]}

        if resp.status_code == 401:
            return {
                "source": "IPGeolocation",
                "status": "ERROR",
                "note": "Invalid API key or unauthorized",
            }
        if resp.status_code == 429:
            return {
                "source": "IPGeolocation",
                "status": "ERROR",
                "note": "Rate limited",
            }
        if resp.status_code != 200:
            return {
                "source": "IPGeolocation",
                "status": "ERROR",
                "note": f"HTTP {resp.status_code}",
            }

        try:
            data = resp.json()
        except ValueError:
            return {
                "source": "IPGeolocation",
                "status": "ERROR",
                "note": "Invalid JSON response",
            }

        if isinstance(data, dict) and data.get("message") and not data.get("ip"):
            return {
                "source": "IPGeolocation",
                "status": "ERROR",
                "note": str(data.get("message"))[:200],
            }

        security = data.get("security") if isinstance(data, dict) else {}
        if not isinstance(security, dict):
            security = {}
        status, reasons = classify_security(security)

        location = data.get("location") if isinstance(data, dict) else {}
        network = data.get("network") if isinstance(data, dict) else {}
        if not isinstance(location, dict):
            location = {}
        if not isinstance(network, dict):
            network = {}

        result = {
            "source": "IPGeolocation",
            "status": status,
            "ip": _pick(data, "ip", default=ip),
            "threat_score": security.get(
                "threat_score", security.get("threatScore", 0)
            ),
            "is_vpn": bool(security.get("is_vpn")),
            "is_proxy": bool(security.get("is_proxy")),
            "is_tor": bool(security.get("is_tor")),
            "is_anonymous": bool(security.get("is_anonymous")),
            "is_bot": bool(security.get("is_bot")),
            "is_known_attacker": bool(security.get("is_known_attacker")),
            "is_spam": bool(security.get("is_spam")),
            "is_cloud_provider": bool(security.get("is_cloud_provider")),
            "proxy_type": security.get("proxy_type", ""),
            "proxy_provider": security.get("proxy_provider", ""),
            "cloud_provider": security.get("cloud_provider", ""),
            "country": _pick(location, "country_name", "country"),
            "city": _pick(location, "city"),
            "isp": _pick(network, "isp") or _pick(network.get("company") or {}, "name"),
            "asn": _pick(
                (network.get("asn") or {})
                if isinstance(network.get("asn"), dict)
                else {},
                "as_number",
                "asn",
            )
            or _pick(network, "asn"),
            "reasons": reasons,
            "note": (
                "Triage signal: anonymizer/cloud flags and score are not "
                "proof of malicious activity."
            ),
        }
        return {k: v for k, v in result.items() if v not in ("", [], None, {})}
