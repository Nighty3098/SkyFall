"""IP2Location.io IP intelligence lookup.

Uses the IP2Location.io API to return geolocation, network/ASN details and
proxy/threat signals for an IP.  The API can be queried without a key
(1,000 queries/day); an optional free key raises the quota to 50,000
queries/month.  Some fields (the nested ``proxy`` object and
``fraud_score``) are only populated on paid plans, so every field is
treated as optional.
"""

from __future__ import annotations

import asyncio
import ipaddress

import requests
from loguru import logger

API_URL = "https://api.ip2location.io/"


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


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y")
    return False


def _as_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def classify_ip2location(data):
    """Return ``(status, reasons)`` from an IP2Location.io payload.

    This is a triage signal, not a verdict: VPN/proxy/hosting usage can be
    legitimate.  Strong indicators escalate the status.
    """
    if not isinstance(data, dict):
        return "UNKNOWN", []

    proxy = data.get("proxy")
    if not isinstance(proxy, dict):
        proxy = {}

    is_proxy = _as_bool(data.get("is_proxy")) or _as_bool(proxy.get("is_proxy"))
    is_vpn = _as_bool(proxy.get("is_vpn"))
    is_tor = _as_bool(proxy.get("is_tor"))
    is_residential_proxy = _as_bool(proxy.get("is_residential_proxy"))
    is_data_center = _as_bool(proxy.get("is_data_center"))
    fraud_score = _as_int(data.get("fraud_score"))
    threat = _pick(data, "threat_type", "threat")

    reasons = []
    if is_tor:
        reasons.append("Tor exit node")
    if is_vpn:
        reasons.append("VPN")
    if is_residential_proxy:
        reasons.append("residential proxy")
    if is_proxy:
        reasons.append("proxy")
    if is_data_center:
        reasons.append("data center")
    if threat:
        reasons.append(str(threat))
    if fraud_score is not None:
        reasons.append(f"fraud score {fraud_score}")

    if is_tor or threat or (fraud_score is not None and fraud_score >= 85):
        return "MALICIOUS", reasons
    if (
        is_vpn
        or is_residential_proxy
        or is_proxy
        or (fraud_score is not None and fraud_score >= 25)
    ):
        return "SUSPICIOUS", reasons
    if is_data_center:
        return "INFO", reasons
    if reasons:
        return "INFO", reasons
    return "CLEAN", [f"fraud score {fraud_score}"] if fraud_score is not None else []


class IP2LocationIO:
    def __init__(self, api_key="", timeout=15):
        logger.debug("Init: IP2LocationIO")
        self.api_key = (api_key or "").strip()
        self.timeout = timeout

    async def lookup(self, ip):
        logger.debug("Trying to check IP2Location.io")
        ip = (ip or "").strip()
        if not _is_ip(ip):
            return {
                "source": "IP2Location.io",
                "status": "SKIPPED",
                "note": "Valid IP address required",
            }

        params = {"ip": ip, "format": "json"}
        if self.api_key:
            params["key"] = self.api_key

        def _do():
            return requests.get(
                API_URL,
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )

        try:
            resp = await asyncio.to_thread(_do)
        except Exception as e:
            logger.debug(f"IP2Location.io failed for {ip}: {e}")
            return {
                "source": "IP2Location.io",
                "status": "ERROR",
                "note": str(e)[:200],
            }

        if resp.status_code == 401:
            return {
                "source": "IP2Location.io",
                "status": "ERROR",
                "note": "Invalid API key or unauthorized",
            }
        if resp.status_code == 429:
            return {
                "source": "IP2Location.io",
                "status": "ERROR",
                "note": "Rate limited (keyless: 1,000/day; free key: 50,000/month)",
            }
        if resp.status_code != 200:
            return {
                "source": "IP2Location.io",
                "status": "ERROR",
                "note": f"HTTP {resp.status_code}",
            }

        try:
            data = resp.json()
        except ValueError:
            return {
                "source": "IP2Location.io",
                "status": "ERROR",
                "note": "Invalid JSON response",
            }

        if isinstance(data, dict) and data.get("error"):
            err = data.get("error")
            if isinstance(err, dict):
                note = _pick(err, "error_message", "message", default=str(err))
            else:
                note = str(err)
            return {
                "source": "IP2Location.io",
                "status": "ERROR",
                "ip": ip,
                "note": str(note)[:200],
            }

        if not isinstance(data, dict):
            return {
                "source": "IP2Location.io",
                "status": "ERROR",
                "ip": ip,
                "note": "Unexpected response",
            }

        status, reasons = classify_ip2location(data)
        proxy = data.get("proxy") if isinstance(data.get("proxy"), dict) else {}

        result = {
            "source": "IP2Location.io",
            "status": status,
            "ip": _pick(data, "ip", default=ip),
            "country": _pick(data, "country_name", "country"),
            "country_code": _pick(data, "country_code"),
            "region": _pick(data, "region_name", "region"),
            "city": _pick(data, "city_name", "city"),
            "zip": _pick(data, "zip_code", "zip"),
            "timezone": _pick(data, "time_zone", "timezone"),
            "lat": _pick(data, "latitude", "lat"),
            "lon": _pick(data, "longitude", "lon"),
            "asn": _pick(data, "asn"),
            "as": _pick(data, "as"),
            "isp": _pick(data, "isp"),
            "domain": _pick(data, "domain"),
            "usage_type": _pick(data, "usage_type"),
            "is_proxy": _as_bool(data.get("is_proxy"))
            or _as_bool(proxy.get("is_proxy")),
            "is_vpn": _as_bool(proxy.get("is_vpn")),
            "is_tor": _as_bool(proxy.get("is_tor")),
            "is_data_center": _as_bool(proxy.get("is_data_center")),
            "is_residential_proxy": _as_bool(proxy.get("is_residential_proxy")),
            "fraud_score": _as_int(data.get("fraud_score")),
            "reasons": reasons,
            "keyless": not self.api_key,
            "note": (
                "Triage signal: anonymizer/cloud flags and fraud score are "
                "not proof of malicious activity."
            ),
        }
        return {k: v for k, v in result.items() if v not in ("", [], None, {})}
