"""WhoisFreaks WHOIS/DNS history and reverse WHOIS lookups.

Endpoints share one optional API key.  Calls are only made when a key is
configured, because these lookups may consume paid credits/quota:

* WHOIS history: 2 credits per successful domain query.
* Reverse WHOIS: 5 credits per page (50 records default, 100 in mini mode).
* Historical DNS: quota/credits depend on the plan; requests are paginated and
  capped to limit usage.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import requests
from loguru import logger

BASE_URL = "https://api.whoisfreaks.com/v2.0"
WHOIS_BASE = f"{BASE_URL}/whois"
DNS_HISTORICAL_URL = f"{BASE_URL}/dns/historical"

#: Values used by registrars and privacy services instead of real registrant
#: data.  They are useless as reverse WHOIS pivots.
_REDACTION_MARKERS = (
    "redacted",
    "privacy",
    "withheld",
    "gdpr",
    "not disclosed",
    "data protected",
    "statutory masking",
    "whoisguard",
    "domains by proxy",
)

#: Short placeholders are only redactions when they are the whole value, so a
#: real company like "Nonexistent Labs" or a domain containing "none" survives.
_EXACT_REDACTION_MARKERS = frozenset({"n/a", "na", "none", "unknown", "null", "-"})


def _normalize_domain(value):
    value = (value or "").strip().lower()
    if not value:
        return ""
    if "://" in value:
        value = value.split("://", 1)[1]
    return value.split("/", 1)[0].strip(".")


def _pick(mapping, *keys):
    if not hasattr(mapping, "get"):
        return ""
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return ""


def _as_list(value):
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _first_int(payload, *keys):
    for key in keys:
        value = payload.get(key) if hasattr(payload, "get") else None
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _unwrap(payload):
    """Return the object that carries the ``whois_domains_historical`` list."""
    if isinstance(payload, list):
        if len(payload) == 1 and isinstance(payload[0], dict):
            item = payload[0]
            if "whois_domains_historical" in item or "domain_name" in item:
                return item
        return {"whois_domains_historical": payload}
    if isinstance(payload, dict):
        nested = payload.get("data")
        if isinstance(nested, dict) and "whois_domains_historical" in nested:
            return {**payload, **nested}
        return payload
    return {}


def _records(payload):
    for key in ("whois_domains_historical", "whois_domains", "domains", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    if payload.get("domain_name"):
        return [payload]
    return []


def _compact_contact(record, contact_key, prefix):
    contact = record.get(contact_key)
    if not isinstance(contact, dict):
        contact = {}
    values = {
        "name": _pick(contact, "name", "full_name")
        or _pick(record, f"{prefix}_name", f"{prefix}_contact_name"),
        "company": _pick(contact, "company", "organization")
        or _pick(record, f"{prefix}_company", f"{prefix}_organization"),
        "email": _pick(contact, "email_address", "email")
        or _pick(record, f"{prefix}_email", f"{prefix}_email_address"),
        "country": _pick(contact, "country_name", "country_code", "country")
        or _pick(record, f"{prefix}_country"),
    }
    return {key: value for key, value in values.items() if value}


def _history_record(record):
    registrar = record.get("domain_registrar")
    if isinstance(registrar, dict):
        registrar_name = _pick(registrar, "registrar_name", "normalized_name")
    else:
        registrar_name = str(registrar or "")

    compact = {
        "query_time": _pick(record, "query_time", "updated_date"),
        "created": _pick(record, "create_date", "creation_date", "created"),
        "updated": _pick(record, "update_date", "last_updated"),
        "expires": _pick(record, "expiry_date", "expiration_date"),
        "registrar": registrar_name or _pick(record, "registrar_name", "registrar"),
        "registrant": _compact_contact(record, "registrant_contact", "registrant"),
        "admin": _compact_contact(record, "administrative_contact", "admin"),
        "tech": _compact_contact(record, "technical_contact", "tech"),
        "name_servers": _as_list(
            record.get("name_servers") or record.get("nameservers")
        ),
        "status": _as_list(record.get("domain_status")),
    }
    return {key: value for key, value in compact.items() if value not in ("", [], {})}


def _reverse_record(record):
    registrant = record.get("registrant_contact")
    if not isinstance(registrant, dict):
        registrant = {}

    registrar = record.get("domain_registrar")
    if isinstance(registrar, dict):
        registrar_name = _pick(registrar, "registrar_name", "normalized_name")
    else:
        registrar_name = str(registrar or "")

    compact = {
        "domain_name": _pick(record, "domain_name", "domain"),
        "created": _pick(record, "create_date", "creation_date", "created"),
        "updated": _pick(record, "update_date", "last_updated"),
        "expires": _pick(record, "expiry_date", "expiration_date"),
        "registrar": registrar_name or _pick(record, "registrar_name", "registrar"),
        "registrant_name": _pick(registrant, "name")
        or _pick(record, "registrant_name"),
        "company": _pick(registrant, "company", "organization")
        or _pick(record, "registrant_company", "registrant_organization"),
        "email": _pick(registrant, "email_address", "email")
        or _pick(record, "registrant_email", "registrant_email_address"),
    }
    return {key: value for key, value in compact.items() if value not in ("", [], {})}


def _response_message(response):
    try:
        data = response.json()
    except ValueError:
        return (response.text or "").strip()[:300]
    if isinstance(data, dict):
        message = data.get("message") or data.get("error")
        if message:
            return str(message)[:300]
    return str(data)[:300]


def _usable(value):
    if value in (None, ""):
        return False
    text = str(value).strip()
    if len(text) < 2:
        return False
    lowered = text.lower()
    if lowered in _EXACT_REDACTION_MARKERS:
        return False
    return not any(marker in lowered for marker in _REDACTION_MARKERS)


def _add_unique(values, seen, value):
    if not _usable(value):
        return
    text = str(value).strip()
    key = text.lower()
    if key in seen:
        return
    seen.add(key)
    values.append(text)


def _record_contacts(record):
    """Yield compact contact dicts from raw API or normalised history records."""
    raw_keys = ("registrant_contact", "administrative_contact", "technical_contact")
    has_raw_contact = any(isinstance(record.get(key), dict) for key in raw_keys)
    has_flat_contact = any(
        record.get(f"{prefix}_{suffix}")
        for prefix in ("registrant", "admin", "tech")
        for suffix in ("name", "company", "organization", "email", "email_address")
    )
    if has_raw_contact or has_flat_contact:
        record = _history_record(record)

    for key in ("registrant", "admin", "tech"):
        contact = record.get(key)
        if isinstance(contact, dict):
            yield contact


def build_reverse_pivots(history=None, current_whois=None, max_pivots=2):
    """Extract non-redacted emails/companies from WHOIS history.

    Returns at most one email and one company pivot.  Private or placeholder
    registrant values are skipped, so a fully redacted history produces an
    empty list instead of a useless paid query.
    """
    emails = []
    companies = []
    seen_emails = set()
    seen_companies = set()

    records = []
    if isinstance(history, dict):
        records = history.get("records") or []
    elif isinstance(history, list):
        records = history

    for record in records:
        if not isinstance(record, dict):
            continue
        for contact in _record_contacts(record):
            _add_unique(
                emails,
                seen_emails,
                contact.get("email") or contact.get("email_address"),
            )
            _add_unique(
                companies,
                seen_companies,
                contact.get("company") or contact.get("organization"),
            )

    if hasattr(current_whois, "get"):
        current_emails = current_whois.get("emails") or current_whois.get("email")
        if isinstance(current_emails, str):
            current_emails = [current_emails]
        for value in current_emails or []:
            _add_unique(emails, seen_emails, value)
        _add_unique(
            companies,
            seen_companies,
            current_whois.get("org")
            or current_whois.get("company")
            or current_whois.get("organization"),
        )

    pivots = []
    if emails and max_pivots > 0:
        pivots.append({"type": "email", "value": emails[0]})
    if companies and len(pivots) < max_pivots:
        pivots.append({"type": "company", "value": companies[0]})
    return pivots


def parse_reverse_query(query):
    """Turn a UI query into ``reverse_whois`` keyword arguments.

    Accepts ``email:``, ``company:``, ``owner:`` and ``keyword:`` prefixes.
    A bare value containing ``@`` is treated as an email, anything else as a
    company name.
    """
    query = (query or "").strip()
    if not query:
        return None
    if ":" in query:
        prefix, value = query.split(":", 1)
        prefix = prefix.strip().lower()
        value = value.strip()
        if prefix in ("email", "company", "owner", "keyword") and value:
            return {prefix: value}
    if "@" in query:
        return {"email": query}
    return {"company": query}


def merge_reverse_results(results, pivots):
    """Merge per-pivot reverse results into one de-duplicated domain list."""
    domains = {}
    queries = []
    statuses = []

    for pivot, result in zip(pivots, results, strict=False):
        status = result.get("status", "ERROR")
        statuses.append(status)
        queries.append(
            {
                "pivot": pivot,
                "status": status,
                "total_results": result.get("total_results", 0),
                "total_pages": result.get("total_pages", 0),
                "note": result.get("note", ""),
            }
        )
        for item in result.get("domains", []):
            name = (item.get("domain_name") or "").strip().lower()
            if not name:
                continue
            label = f"{pivot['type']}:{pivot['value']}"
            if name in domains:
                if label not in domains[name]["matched_on"]:
                    domains[name]["matched_on"].append(label)
                continue
            domains[name] = {**item, "matched_on": [label]}

    if not statuses or all(status == "SKIPPED" for status in statuses):
        status = "SKIPPED"
    elif any(status in ("OK", "PARTIAL") for status in statuses):
        status = "PARTIAL" if any(s == "ERROR" for s in statuses) else "OK"
    else:
        status = "ERROR"

    merged = {
        "source": "WhoisFreaks",
        "kind": "reverse",
        "status": status,
        "pivots": pivots,
        "total_domains": len(domains),
        "queries": queries,
        "domains": list(domains.values()),
    }
    if not pivots:
        merged["note"] = (
            "No usable registrant email/company found; enter a reverse query manually."
        )
    return merged


def _parse_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (ValueError, OSError, OverflowError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _collect_ip_values(value):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {
                "address",
                "ip_address",
                "ip",
                "value",
                "target",
            } and isinstance(item, str):
                candidate = item.strip()
                if candidate and ":" in candidate:
                    found.append(candidate)
                elif candidate.count(".") == 3:
                    found.append(candidate)
            else:
                found.extend(_collect_ip_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_collect_ip_values(item))
    return found


def _dns_record(record):
    if not isinstance(record, dict):
        return {}
    dns_type = str(_pick(record, "dnsType", "type", "record_type", "dns_type")).upper()
    compact = {"type": dns_type}
    if dns_type in ("A", "AAAA"):
        ips = []
        for key in ("address", "ipAddress", "ip", "value"):
            val = record.get(key)
            if isinstance(val, str) and val.strip():
                ips.append(val.strip())
        ips.extend(_collect_ip_values(record.get("dnsRecord", record)))
        if not ips:
            ips.extend(_collect_ip_values(record))
        deduped = []
        seen = set()
        for ip in ips:
            key = ip.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(ip)
        if deduped:
            compact["addresses"] = deduped
            compact["value"] = ", ".join(deduped[:5])
    else:
        for key in ("target", "value", "address", "exchange", "nameserver", "txt"):
            val = record.get(key)
            if isinstance(val, str) and val.strip():
                compact["value"] = val.strip()[:300]
                break
            if isinstance(val, list):
                items = [str(i) for i in val if i not in (None, "")]
                if items:
                    compact["value"] = ", ".join(items)[:300]
                    break
        if "value" not in compact:
            nested = record.get("dnsRecord") or record.get("data")
            if isinstance(nested, dict):
                for key in ("target", "value", "address", "exchange", "nameserver"):
                    val = nested.get(key)
                    if isinstance(val, str) and val.strip():
                        compact["value"] = val.strip()[:300]
                        break
    return {k: v for k, v in compact.items() if v not in ("", [], None)}


def _dns_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return {}
    records_raw = snapshot.get("dnsRecords") or snapshot.get("records") or []
    if isinstance(records_raw, dict):
        records_raw = records_raw.get("records") or records_raw.get("dnsRecords") or []
    records = [_dns_record(r) for r in records_raw if isinstance(r, dict)]
    records = [r for r in records if r]
    dns_types = snapshot.get("dnsTypes") or snapshot.get("types") or []
    if isinstance(dns_types, str):
        dns_types = [dns_types]
    compact = {
        "query_time": _pick(snapshot, "queryTime", "query_time", "updated_date"),
        "domain_name": _pick(snapshot, "domainName", "domain_name", "domain"),
        "dns_types": [str(t).upper() for t in dns_types if t],
        "records": records,
    }
    return {k: v for k, v in compact.items() if v not in ("", [], None)}


def _dns_records_from_payload(payload):
    for key in (
        "historicalDnsRecords",
        "historical_dns_records",
        "historicalDNSRecords",
        "dnsRecords",
        "records",
        "result",
    ):
        value = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(value, list):
            return value
    return []


def build_domain_timeline(
    dns_history=None, whois_history=None, current_whois=None, max_events=200
):
    """Build a chronological investigation timeline.

    Timestamps are marked by meaning: DNS/WHOIS snapshots use observation/query
    times; WHOIS create/update/expiry are reported registration dates (not proof
    of when a specific change happened). Consumers should treat this as triage
    context, not a maliciousness verdict.
    """
    events = []

    dns_snapshots = []
    if isinstance(dns_history, dict):
        dns_snapshots = dns_history.get("snapshots") or dns_history.get("records") or []
    elif isinstance(dns_history, list):
        dns_snapshots = dns_history

    for snap in dns_snapshots:
        if not isinstance(snap, dict):
            continue
        ts = _pick(snap, "query_time", "queryTime", "updated_date")
        parsed = _parse_datetime(ts)
        if parsed is None:
            continue
        ips = []
        ns = []
        mx = []
        for rec in snap.get("records") or []:
            if not isinstance(rec, dict):
                continue
            rtype = str(rec.get("type", "")).upper()
            if rtype in ("A", "AAAA"):
                ips.extend(rec.get("addresses") or [])
            elif rtype == "NS" and rec.get("value"):
                ns.append(rec["value"])
            elif rtype == "MX" and rec.get("value"):
                mx.append(rec["value"])
        ips = list(dict.fromkeys(ips))
        details = {
            "source": "dns_history",
            "observed_at": ts,
            "domain": _pick(snap, "domain_name", "domainName"),
            "dns_types": snap.get("dns_types") or snap.get("dnsTypes") or [],
        }
        if ips:
            details["ip_addresses"] = ips[:20]
        if ns:
            details["name_servers"] = ns[:10]
        if mx:
            details["mx"] = mx[:10]
        dns_types_text = ", ".join((details.get("dns_types") or [])[:6]) or "records"
        ip_text = f" | IPs: {', '.join(ips[:3])}" if ips else ""
        events.append(
            {
                "timestamp": parsed.isoformat(),
                "sort_key": parsed.timestamp(),
                "type": "dns_snapshot",
                "semantics": "observed",
                "summary": f"DNS snapshot: {dns_types_text}{ip_text}",
                "details": details,
            }
        )

    whois_records = []
    if isinstance(whois_history, dict):
        whois_records = whois_history.get("records") or []
    elif isinstance(whois_history, list):
        whois_records = whois_history

    for rec in whois_records:
        if not isinstance(rec, dict):
            continue
        query_time = _pick(rec, "query_time", "queryTime")
        if query_time:
            parsed = _parse_datetime(query_time)
            if parsed is not None:
                events.append(
                    {
                        "timestamp": parsed.isoformat(),
                        "sort_key": parsed.timestamp(),
                        "type": "whois_snapshot",
                        "semantics": "observed",
                        "summary": "WHOIS snapshot"
                        + (
                            f" | registrar: {rec.get('registrar')}"
                            if rec.get("registrar")
                            else ""
                        ),
                        "details": {
                            "source": "whois_history",
                            "observed_at": query_time,
                            "registrar": rec.get("registrar", ""),
                            "name_servers": rec.get("name_servers", []),
                            "status": rec.get("status", []),
                            "registrant": rec.get("registrant", {}),
                        },
                    }
                )
        for field, label in (
            ("created", "reported_creation_date"),
            ("updated", "reported_update_date"),
            ("expires", "reported_expiry_date"),
        ):
            val = rec.get(field)
            parsed = _parse_datetime(val)
            if parsed is None:
                continue
            events.append(
                {
                    "timestamp": parsed.isoformat(),
                    "sort_key": parsed.timestamp(),
                    "type": label,
                    "semantics": "reported",
                    "summary": f"{label.replace('_', ' ').title()}: {val}",
                    "details": {
                        "source": "whois_history",
                        "value": val,
                        "query_time": query_time,
                    },
                }
            )

    if isinstance(current_whois, dict) and current_whois:
        for field, label in (
            ("creation_date", "reported_creation_date"),
            ("updated_date", "reported_update_date"),
            ("expiration_date", "reported_expiry_date"),
        ):
            val = current_whois.get(field)
            parsed = _parse_datetime(val)
            if parsed is None:
                continue
            label_text = label.replace("_", " ").title()
            events.append(
                {
                    "timestamp": parsed.isoformat(),
                    "sort_key": parsed.timestamp(),
                    "type": label,
                    "semantics": "reported",
                    "summary": f"{label_text} (current WHOIS): {val}",
                    "details": {"source": "current_whois", "value": val},
                }
            )

    events.sort(key=lambda e: e.get("sort_key", 0))
    truncated = len(events) > max_events
    if truncated:
        events = events[:max_events]
    return {
        "status": "OK" if events else "NO_DATA",
        "total_events": len(events),
        "truncated": truncated,
        "events": events,
        "notes": [
            "DNS/WHOIS snapshots use observed/query times, not proven change times.",
            "WHOIS create/update/expiry are reported dates; verify with raw records.",
            "Infrastructure/registration changes are triage signals, not verdicts.",
            "Coverage may be incomplete; check raw data and quota/rate limits.",
        ],
    }


class WhoisFreaks:
    def __init__(self, api_key="", timeout=30):
        logger.debug("Init: WhoisFreaks")
        self.api_key = (api_key or "").strip()
        self.timeout = timeout

    def _error(self, status, note):
        return {"source": "WhoisFreaks", "status": status, "note": note}

    async def _request(self, path, params, base=WHOIS_BASE):
        if not self.api_key:
            return None, self._error("SKIPPED", "API key not configured")

        request_params = {**params, "apiKey": self.api_key}
        if "format" not in request_params:
            request_params["format"] = "json"
        url = path if str(path).startswith("http") else f"{base}{path}"

        def _do():
            return requests.get(
                url,
                params=request_params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )

        try:
            response = await asyncio.to_thread(_do)
        except Exception as exc:
            logger.debug(f"WhoisFreaks request failed: {exc}")
            return None, self._error("ERROR", str(exc)[:200])

        if response.status_code == 401:
            return None, self._error(
                "ERROR", f"Invalid API key or no credits: {_response_message(response)}"
            )
        if response.status_code == 429:
            return None, self._error("ERROR", "Rate limited")
        if response.status_code not in (200, 206, 210):
            return None, self._error(
                "ERROR",
                f"HTTP {response.status_code}: {_response_message(response)}",
            )

        try:
            return response.json(), None
        except ValueError:
            return None, self._error("ERROR", "Invalid JSON response")

    async def history(self, domain, limit=None):
        domain = _normalize_domain(domain)
        if not domain:
            return self._error("ERROR", "No domain supplied")

        payload, error = await self._request("/history", {"domainName": domain})
        if error:
            return {**error, "kind": "history", "domain": domain}

        payload = _unwrap(payload)
        records = [
            _history_record(record)
            for record in _records(payload)
            if isinstance(record, dict)
        ]
        total = _first_int(payload, "total_records", "total_Result", "total_results")
        if not total:
            total = len(records)
        truncated = bool(limit and len(records) > limit)
        if limit:
            records = records[:limit]

        result = {
            "source": "WhoisFreaks",
            "kind": "history",
            "status": "OK",
            "domain": domain,
            "total_records": total,
            "returned": len(records),
            "truncated": truncated,
            "records": records,
        }
        if not records:
            result["note"] = "No historical WHOIS records found."
        return result

    async def dns_history(self, domain, dns_type="all", max_pages=5):
        """Fetch historical DNS snapshots (WhoisFreaks /dns/historical).

        Paginated; capped by ``max_pages`` to limit quota/credit usage.
        """
        domain = _normalize_domain(domain)
        if not domain:
            return self._error("ERROR", "No domain supplied")
        if not self.api_key:
            return {
                **self._error("SKIPPED", "API key not configured"),
                "kind": "dns_history",
                "domain": domain,
            }

        try:
            max_pages = max(1, min(int(max_pages), 20))
        except (TypeError, ValueError):
            max_pages = 5

        snapshots = []
        pages_fetched = 0
        total_pages = 0
        total_records = 0
        last_status = "OK"
        last_note = ""

        for page in range(1, max_pages + 1):
            payload, error = await self._request(
                DNS_HISTORICAL_URL,
                {"domainName": domain, "type": dns_type, "page": page},
                base=BASE_URL,
            )
            if error:
                if page == 1:
                    return {
                        **error,
                        "kind": "dns_history",
                        "domain": domain,
                        "dns_type": dns_type,
                    }
                last_status = "PARTIAL"
                last_note = error.get("note", "request failed")
                break

            pages_fetched += 1
            payload = _unwrap(payload) if isinstance(payload, dict) else {}
            if not isinstance(payload, dict):
                payload = {}
            total_pages = (
                _first_int(payload, "totalPages", "total_pages", "TotalPages")
                or total_pages
            )
            total_records = (
                _first_int(payload, "totalRecords", "total_records", "TotalRecords")
                or total_records
            )
            raw = _dns_records_from_payload(payload)
            if not raw and page == 1 and isinstance(payload, dict):
                # Some responses may nest differently
                nested = payload.get("data")
                if isinstance(nested, dict):
                    raw = _dns_records_from_payload(nested)
                    total_pages = total_pages or _first_int(nested, "totalPages")
                    total_records = total_records or _first_int(nested, "totalRecords")
            for snap in raw:
                if isinstance(snap, dict):
                    normalized = _dns_snapshot(snap)
                    if normalized:
                        snapshots.append(normalized)

            if not raw:
                break
            if total_pages and page >= total_pages:
                break

        if not total_records:
            total_records = len(snapshots)

        result = {
            "source": "WhoisFreaks",
            "kind": "dns_history",
            "status": last_status,
            "domain": domain,
            "dns_type": dns_type,
            "pages_fetched": pages_fetched,
            "total_pages": total_pages,
            "total_records": total_records,
            "returned": len(snapshots),
            "truncated": bool(total_pages and pages_fetched < total_pages),
            "snapshots": snapshots,
        }
        if last_note:
            result["note"] = last_note
        if not snapshots and result["status"] == "OK":
            result["note"] = "No historical DNS snapshots found."
        return result

    async def reverse(
        self,
        email="",
        company="",
        owner="",
        keyword="",
        page=1,
        mode="mini",
        exact=None,
    ):
        provided = [
            (key, str(value).strip())
            for key, value in (
                ("email", email),
                ("company", company),
                ("owner", owner),
                ("keyword", keyword),
            )
            if str(value or "").strip()
        ]
        if len(provided) != 1:
            return {
                **self._error(
                    "ERROR",
                    "Provide exactly one of email, company, owner or keyword",
                ),
                "kind": "reverse",
            }

        query_type, query_value = provided[0]
        if query_type == "email" and "@" not in query_value:
            return {
                **self._error("ERROR", "Email pivot must contain @"),
                "kind": "reverse",
            }
        if query_type == "keyword" and not 3 <= len(query_value) <= 63:
            return {
                **self._error("ERROR", "Keyword must be 3-63 characters"),
                "kind": "reverse",
            }
        if mode not in ("default", "mini"):
            return {
                **self._error("ERROR", "Mode must be 'default' or 'mini'"),
                "kind": "reverse",
            }

        try:
            page_number = max(1, int(page))
        except (TypeError, ValueError):
            page_number = 1

        params = {query_type: query_value, "mode": mode, "page": page_number}
        if exact is not None and query_type != "email":
            params["exact"] = "true" if exact else "false"

        payload, error = await self._request("/reverse", params)
        if error:
            return {
                **error,
                "kind": "reverse",
                "query": {"type": query_type, "value": query_value},
            }

        payload = _unwrap(payload)
        domains = [
            _reverse_record(record)
            for record in _records(payload)
            if isinstance(record, dict)
        ]
        total = _first_int(payload, "total_Result", "total_results", "total_records")
        if not total:
            total = len(domains)

        result = {
            "source": "WhoisFreaks",
            "kind": "reverse",
            "status": "OK",
            "query": {"type": query_type, "value": query_value},
            "page": _first_int(payload, "current_Page", "current_page", "page")
            or page_number,
            "total_results": total,
            "total_pages": _first_int(payload, "total_Pages", "total_pages"),
            "domains": domains,
        }
        if not domains:
            result["note"] = "No domains found for this pivot."
        return result
