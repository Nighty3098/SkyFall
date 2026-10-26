"""Merge the output of the two username engines into one report.

SkyFall checks a username twice — with the built-in Sherlock-style engine
(:mod:`src.modules.username_search`) and with Maigret
(:mod:`src.modules.maigret_search`).  Both query largely the same sites, so an
account that *both* engines report is much more likely to be real.

This module cross-references the two result sets and renders a single report:

* accounts found by **both** engines are *confirmed* and listed first, each
  tagged with a check mark;
* accounts found by only one engine are *unconfirmed* and listed at the very
  bottom, grouped by the engine that found them.

An account is matched across engines by its profile URL (scheme, ``www.``,
query string and trailing slash are ignored) or, as a fallback, by the
normalised site name — the two databases spell site names differently.
"""

from __future__ import annotations

import re

#: Marker next to an account that both engines reported.
CONFIRMED_MARK = "✅"
#: Marker next to an account that only one engine reported.
UNCONFIRMED_MARK = "·"

_SCHEME_RE = re.compile(r"^https?://", re.I)
_WWW_RE = re.compile(r"^(?:www|m)\d*\.", re.I)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def canonical_url(url: str | None) -> str:
    """Normalise a profile URL so the same account matches across engines."""
    text = (url or "").strip().lower()
    text = _SCHEME_RE.sub("", text)
    text = text.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return _WWW_RE.sub("", text)


def canonical_site(site: str | None) -> str:
    """Normalise a site name (``"GitHub"`` → ``"github"``)."""
    return _NON_ALNUM_RE.sub("", (site or "").lower())


def _keys(entry: dict) -> set[str]:
    keys: set[str] = set()
    url = canonical_url(entry.get("url_user"))
    if url:
        keys.add("url:" + url)
    site = canonical_site(entry.get("site"))
    if site:
        keys.add("site:" + site)
    return keys


def _find_match(entry: dict, candidates: list[dict], used: set[int]) -> int | None:
    """Return the index of the candidate matching ``entry``, or ``None``.

    URL matches win over site-name matches on purpose: the same host is a much
    stronger signal than similar names in the two site databases.
    """
    entry_keys = _keys(entry)
    if not entry_keys:
        return None
    for prefix in ("url:", "site:"):
        wanted = {key for key in entry_keys if key.startswith(prefix)}
        if not wanted:
            continue
        for index, candidate in enumerate(candidates):
            if index in used:
                continue
            if wanted & _keys(candidate):
                return index
    return None


def merge_sources(
    sherlock: list[dict] | None,
    maigret: list[dict] | None,
) -> tuple[list[tuple[dict, dict]], list[dict], list[dict]]:
    """Cross-reference two result sets.

    Returns ``(confirmed, sherlock_only, maigret_only)`` where ``confirmed`` is
    a list of ``(sherlock_entry, maigret_entry)`` tuples.
    """
    left = [dict(entry) for entry in (sherlock or [])]
    right = [dict(entry) for entry in (maigret or [])]

    matched_left: set[int] = set()
    matched_right: set[int] = set()
    confirmed: list[tuple[dict, dict]] = []

    for index, entry in enumerate(left):
        match = _find_match(entry, right, matched_right)
        if match is None:
            continue
        matched_left.add(index)
        matched_right.add(match)
        confirmed.append((entry, right[match]))

    sherlock_only = [e for i, e in enumerate(left) if i not in matched_left]
    maigret_only = [e for j, e in enumerate(right) if j not in matched_right]
    return confirmed, sherlock_only, maigret_only


def _site(entry: dict, fallback: dict | None = None) -> str:
    return (
        entry.get("site")
        or (fallback or {}).get("site")
        or entry.get("url_user")
        or "?"
    )


def _row(entry: dict) -> dict:
    row = {
        "site": _site(entry),
        "url": entry.get("url_user") or "",
        "status": entry.get("status") or "?",
    }
    ids = entry.get("ids") or {}
    if ids:
        row["ids"] = ids
    return row


def report(
    username: str,
    confirmed: list[tuple[dict, dict]],
    sherlock_only: list[dict],
    maigret_only: list[dict],
) -> dict:
    """Build a structured merged username report (display-ready)."""
    if confirmed:
        confirmed_rows = []
        for entry, other in confirmed:
            row = _row(entry)
            row["site"] = _site(entry, other)
            row["maigret_status"] = other.get("status") or "?"
            url = other.get("url_user") or ""
            if url and not row.get("url"):
                row["url"] = url
            ids = other.get("ids") or {}
            if ids:
                existing = row.get("ids") or {}
                row["ids"] = {**existing, **ids} if existing else ids
            confirmed_rows.append(row)
    else:
        confirmed_rows = ["No account was confirmed by both engines"]

    unconfirmed = {}
    if sherlock_only:
        unconfirmed["Sherlock only"] = [_row(e) for e in sherlock_only]
    if maigret_only:
        unconfirmed["Maigret only"] = [_row(e) for e in maigret_only]
    if not unconfirmed:
        unconfirmed = {"Note": "Nothing unconfirmed"}

    return {"Confirmed": confirmed_rows, "Unconfirmed": unconfirmed}


def render_report(
    username: str,
    confirmed: list[tuple[dict, dict]],
    sherlock_only: list[dict],
    maigret_only: list[dict],
) -> str:
    """Backwards-compatible text renderer for existing tests/UI."""
    from src.ui.output_formatter import (
        bullet,
        divider,
        end_of,
        info,
        line,
        section,
        title,
    )

    confirmed_mark = "✅"
    unconfirmed_mark = "·"

    def _site(entry: dict, fallback: dict | None = None) -> str:
        return (
            entry.get("site")
            or (fallback or {}).get("site")
            or entry.get("url_user")
            or "?"
        )

    def _details(entry: dict, *, source: str, other: dict | None = None) -> str:
        status = entry.get("status") or "?"
        if other is not None:
            other_status = other.get("status") or "?"
            parts = [f"Sherlock: {status}", f"Maigret: {other_status}"]
        else:
            parts = [f"{source}: {status}"]
        ids = entry.get("ids") or (other or {}).get("ids") or {}
        if ids:
            parts.append(", ".join(f"{k}={v}" for k, v in ids.items()))
        return " · ".join(parts)

    def _render_confirmed(entry: dict, other: dict) -> str:
        label = f"{confirmed_mark} {_site(entry, other)}"
        url = entry.get("url_user") or other.get("url_user") or ""
        if url:
            label += f" — {url}"
        return (
            bullet(label) + "\n" + line(_details(entry, source="Sherlock", other=other))
        )

    def _render_single(entry: dict, source: str) -> str:
        label = f"{unconfirmed_mark} {_site(entry)}"
        url = entry.get("url_user") or ""
        if url:
            label += f" — {url}"
        return bullet(label) + "\n" + line(_details(entry, source=source))

    lines = [divider(), title(f"Username OSINT: {username}")]
    lines.append(
        "  "
        f"{confirmed_mark} confirmed {len(confirmed)} · "
        f"Sherlock only {len(sherlock_only)} · "
        f"Maigret only {len(maigret_only)}"
    )

    lines.append(section(f"Confirmed by both engines {confirmed_mark}"))
    if confirmed:
        for entry, other in confirmed:
            lines.append(_render_confirmed(entry, other))
    else:
        lines.append(info("No account was confirmed by both engines"))

    lines.append(section("Unconfirmed"))
    if sherlock_only:
        lines.append("  [ Sherlock only ]")
        for entry in sherlock_only:
            lines.append(_render_single(entry, "Sherlock"))
    if maigret_only:
        lines.append("  [ Maigret only ]")
        for entry in maigret_only:
            lines.append(_render_single(entry, "Maigret"))
    if not sherlock_only and not maigret_only:
        lines.append(info("Nothing unconfirmed"))

    lines.append(end_of("username search"))
    lines.append(divider())
    return "\n".join(lines)
