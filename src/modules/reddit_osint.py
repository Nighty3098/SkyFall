"""Reddit OSINT through public archives.

The engine reconstructs the activity profile of a Reddit account from the two
community archives that kept a copy of the data before Reddit removed it:

* **Arctic Shift** (``arctic-shift.photon-reddit.com``) — the community
  successor to Pushshift. Primary source, covers 2022 → today and keeps the
  original scrape (``selftext``, ``removed_by_category``, flair).
* **PullPush** (``api.pullpush.io``) — a second index of the historical
  Pushshift dumps. Fallback, merged by id.

Where the reference implementation paginates one source at a time, this engine
queries both sources for posts *and* comments concurrently, merges the results
by id, and classifies every item as ``live``, ``removed`` (a moderator acted)
or ``deleted`` (the author acted). On top of that it extracts identifiers
(emails, crypto addresses, Telegram handles, phones, domains, mentions),
estimates the author's timezone from the quiet hours of the day, detects
mentioned technologies and produces a PII exposure score.

An optional Reddit OAuth application (client id + secret, configured in the
settings tab) enriches the report with the *live* account metadata that the
archives cannot provide (current karma, cake day, suspension flag).
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from datetime import UTC, datetime
from urllib.parse import quote, urlencode

import httpx
from loguru import logger

from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    error,
    info,
    kv,
    section,
    title,
)

ARCTIC_DEFAULT = "https://arctic-shift.photon-reddit.com"
PULLPUSH_DEFAULT = "https://api.pullpush.io"
OAUTH_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_ABOUT_URL = "https://oauth.reddit.com/user/{user}/about"
PERMALINK_BASE = "https://www.reddit.com"

_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) SkyFall-Reddit/1.0"
PAGE_LIMIT = 100
TEXT_LIMIT = 600
DEFAULT_MAX_PAGES = 40
DEFAULT_DELAY = 0.35
MAX_BAN_SLEEP = 10.0
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

#: HTTP statuses that mean "the endpoint is throttling / blocking us".
BAN_STATUS = {401, 403, 407, 422, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
BAN_HINTS = ("slow down", "rate limit", "too many requests", "timeout")

SELF_DOMAINS = (
    "reddit.com",
    "redd.it",
    "redditstatic.com",
    "redditmedia.com",
    "reddituploads.com",
    "imgur.com",
)

TECHNOLOGIES = (
    "python javascript typescript java c++ c# go golang rust ruby php swift kotlin "
    "react vue angular svelte nextjs node nodejs deno bun django flask fastapi spring "
    "postgres postgresql mysql sqlite redis mongodb elasticsearch kafka docker "
    "kubernetes aws gcp azure cloudflare nginx apache linux ubuntu debian fedora kali "
    "windows macos android ios terraform ansible jenkins git github gitlab vim neovim "
    "vscode emacs bitcoin ethereum solana monero blockchain web3 defi nvidia amd intel "
    "rtx ryzen tailwind figma lambda dynamodb"
).split()

_EMAIL_RE = re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")
_BTC_RE = re.compile(
    r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"
)
_ETH_RE = re.compile(r"\b(0x[a-fA-F0-9]{40})\b")
_XMR_RE = re.compile(r"\b(4[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b")
_TG_RE = re.compile(r"(?:t\.me/|telegram:\s*@)([a-zA-Z0-9_]{5,32})\b", re.I)
_MENTION_RE = re.compile(r"(?:^|[\s/])u/([a-zA-Z0-9_-]{3,30})")
_URL_RE = re.compile(r"https?://([^\s<>\"')]+)")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{8,17}\d")
_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


class RedditArchiveError(RuntimeError):
    """Raised when an archive request cannot be satisfied."""


def normalize_username(username: str | None) -> str:
    """Strip a ``u/`` prefix, ``@`` or ``/user/`` noise from a username."""
    text = (username or "").strip()
    text = text.removeprefix("/user/").removeprefix("/u/")
    text = text.removeprefix("u/").removeprefix("U/").removeprefix("@")
    return text.strip("/").strip()


def status_of(item: dict, kind: str) -> str:
    """Classify an archived item as ``live``, ``removed`` or ``deleted``."""
    text = item.get("selftext") if kind == "posts" else item.get("body")
    author = item.get("author")
    if text in ("[removed]", "[ Removed by Reddit ]") or (
        kind == "posts" and item.get("removed_by_category")
    ):
        return "removed"
    if text == "[deleted]" or author == "[deleted]":
        return "deleted"
    return "live"


def text_of(item: dict, kind: str) -> str:
    """Return the searchable text of a post (title + body) or a comment."""
    if kind == "posts":
        return f"{item.get('title') or ''} {item.get('selftext') or ''}".strip()
    return (item.get("body") or "").strip()


def permalink_of(item: dict) -> str | None:
    if item.get("permalink"):
        return PERMALINK_BASE + item["permalink"]
    return item.get("url")


def summarize_item(item: dict, kind: str, text_limit: int = TEXT_LIMIT) -> dict:
    """Project a raw archive row into the stable report shape."""
    text = text_of(item, kind)
    ts = item.get("created_utc")
    return {
        "id": item.get("id"),
        "kind": kind,
        "status": status_of(item, kind),
        "subreddit": item.get("subreddit"),
        "score": item.get("score"),
        "num_comments": item.get("num_comments"),
        "over_18": item.get("over_18"),
        "created_utc": ts,
        "utc": iso(ts),
        "title": item.get("title"),
        "text": text[:text_limit],
        "text_truncated": len(text) > text_limit,
        "url": permalink_of(item),
    }


def extract_signals(text: str) -> list[tuple[str, str]]:
    """Extract identifiers (email, crypto, telegram, phone, domain, mention)."""
    out: list[tuple[str, str]] = []

    for match in _BTC_RE.finditer(text):
        value = match.group(1)
        if len(value) > 25 and not value.isalpha():
            out.append(("btc", value))
    for match in _ETH_RE.finditer(text):
        out.append(("eth", match.group(1)))
    for match in _XMR_RE.finditer(text):
        out.append(("xmr", match.group(1)))
    for match in _EMAIL_RE.finditer(text):
        value = match.group(1).lower()
        if not value.endswith(_IMAGE_SUFFIXES):
            out.append(("email", value))
    for match in _TG_RE.finditer(text):
        out.append(("telegram", "@" + match.group(1)))
    for match in _MENTION_RE.finditer(text):
        out.append(("mention", "u/" + match.group(1)))
    for match in _URL_RE.finditer(text):
        host = match.group(1).split("/")[0].lower().removeprefix("www.")
        out.append(("domain", host))
    for match in _PHONE_RE.finditer(text):
        raw = re.sub(r"[^\d+]", "", match.group(0))
        if 10 <= len(raw.lstrip("+")) <= 15:
            out.append(("phone", raw))
    return out


def detect_technologies(text: str, technologies: tuple[str, ...] = None) -> list[str]:
    """Return the tracked technologies mentioned in ``text``."""
    low = text.lower()
    words = tuple(technologies or TECHNOLOGIES)
    return [tech for tech in words if re.search(rf"\b{re.escape(tech)}\b", low)]


def guess_timezone(hours: list[int]) -> tuple[int, str]:
    """Infer a region from the quietest 6-hour window of the day (UTC hours)."""
    if len(hours) != 24:
        return 0, "Unknown / distributed"
    scores = [sum(hours[(start + i) % 24] for i in range(6)) for start in range(24)]
    best = min(range(24), key=lambda start: scores[start])
    if not sum(hours) or max(scores) - min(scores) <= 1:
        return best, "Unknown / distributed"
    if 5 <= best <= 9:
        return best, "Americas (UTC-8..UTC-5)"
    if best >= 22 or best <= 3:
        return best, "Europe / Middle East / Africa (UTC+0..UTC+3)"
    if 14 <= best <= 20:
        return best, "Asia / Oceania (UTC+7..UTC+11)"
    return best, "Unknown / distributed"


def build_search_url(
    source: str,
    kind: str,
    *,
    author: str | None = None,
    cursor: int | None = None,
    subreddit: str | None = None,
    keywords: str | None = None,
    over18: bool | None = None,
    sort: str = "asc",
    limit: int = PAGE_LIMIT,
    arctic: str = ARCTIC_DEFAULT,
    pullpush: str = PULLPUSH_DEFAULT,
) -> str:
    """Build the archive search URL for one (source, kind) pair."""
    if not author and not keywords:
        raise ValueError("build_search_url needs an author, keywords, or both")

    params: dict[str, object] = {"limit": limit, "sort": sort}
    if author:
        params["author"] = author
    if subreddit:
        params["subreddit"] = subreddit
    if source == "arctic":
        if over18 is not None:
            params["over_18"] = "true" if over18 else "false"
        if keywords:
            params["query" if kind == "posts" else "body"] = keywords
        base = f"{arctic.rstrip('/')}/api/{kind}/search"
    else:
        if keywords:
            params["q"] = keywords
        endpoint = "submission" if kind == "posts" else "comment"
        base = f"{pullpush.rstrip('/')}/reddit/search/{endpoint}/"

    if cursor:
        params["after"] = cursor

    sep = "&" if "?" in base else "?"
    return base + sep + urlencode(params)


def analyze(
    username: str,
    items_by_kind: dict[str, list[dict]],
    meta: dict | None = None,
    live: dict | None = None,
) -> dict:
    """Turn raw archive items into the structured report."""
    posts = items_by_kind.get("posts") or []
    comments = items_by_kind.get("comments") or []
    everything = sorted(
        [("posts", p) for p in posts] + [("comments", c) for c in comments],
        key=lambda pair: pair[1].get("created_utc") or 0,
    )

    subs: Counter = Counter()
    hours = [0] * 24
    weekdays = [0] * 7
    per_month: Counter = Counter()
    statuses: Counter = Counter()
    signals: Counter = Counter()
    domains: Counter = Counter()
    mentions: Counter = Counter()
    techs: Counter = Counter()
    flagged: list[dict] = []

    for kind, item in everything:
        text = text_of(item, kind)
        sub = (item.get("subreddit") or "").lower()
        if sub:
            subs[sub] += 1
        ts = item.get("created_utc")
        if ts:
            stamp = datetime.fromtimestamp(ts, UTC)
            hours[stamp.hour] += 1
            weekdays[stamp.weekday()] += 1
            per_month[stamp.strftime("%Y-%m")] += 1

        status = status_of(item, kind)
        statuses[status] += 1
        if status != "live":
            flagged.append(
                {
                    "id": item.get("id"),
                    "kind": kind,
                    "status": status,
                    "subreddit": item.get("subreddit"),
                    "utc": iso(ts),
                    "score": item.get("score"),
                    "title": (item.get("title") or "")[:120],
                    "permalink": permalink_of(item),
                }
            )

        for tech in detect_technologies(text):
            techs[tech] += 1
        for tag, value in extract_signals(text):
            if tag == "domain":
                if value.endswith(SELF_DOMAINS):
                    continue
                domains[value] += 1
            elif tag == "mention":
                if value.lower() == f"u/{username}".lower():
                    continue
                mentions[value] += 1
            elif tag == "phone":
                signals["phone"] += 1
            else:
                signals[f"{tag}:{value}"] += 1

    tz_start, tz_name = guess_timezone(hours)
    total = len(everything)
    cutoff = datetime.now(UTC).timestamp() - 365 * 24 * 3600
    recent = sum(1 for _, it in everything if (it.get("created_utc") or 0) > cutoff)

    exposure = min(
        100,
        round(
            (
                len([s for s in signals if s.startswith("email")]) * 10
                + len([s for s in signals if s.startswith("btc")]) * 8
                + len([s for s in signals if s.startswith("eth")]) * 6
                + len([s for s in signals if s.startswith("xmr")]) * 6
                + len([s for s in signals if s.startswith("telegram")]) * 4
                + signals.get("phone", 0) * 4
                + len(domains) * 2
                + len(mentions) * 2
            )
            / 30
            * 100
        ),
    )

    return {
        "username": username,
        "archive_meta": meta,
        "live_profile": live,
        "totals": {
            "posts": len(posts),
            "comments": len(comments),
            "items": total,
            "live": statuses["live"],
            "removed_by_mods": statuses["removed"],
            "deleted_by_author": statuses["deleted"],
            "deleted_pct": round((total - statuses["live"]) / total * 100, 1)
            if total
            else 0.0,
            "items_last_12m": recent,
            "first_activity": iso(everything[0][1].get("created_utc"))
            if everything
            else None,
            "last_activity": iso(everything[-1][1].get("created_utc"))
            if everything
            else None,
        },
        "score_exposure_0_100": exposure,
        "timezone_guess": {
            "quiet_window_utc": f"{tz_start:02d}:00-{(tz_start + 6) % 24:02d}:00",
            "estimated_region": tz_name,
            "busiest_hour_utc": f"{hours.index(max(hours)):02d}:00" if total else None,
        },
        "activity_by_hour_utc": hours,
        "activity_by_weekday": {WEEKDAYS[i]: weekdays[i] for i in range(7)},
        "activity_by_month": dict(sorted(per_month.items())),
        "top_subreddits": [
            {"subreddit": sub, "items": count} for sub, count in subs.most_common(20)
        ],
        "identifiers": sorted(signals),
        "external_domains": [
            {"domain": dom, "times": count} for dom, count in domains.most_common(30)
        ],
        "mentioned_users": [
            {"user": usr, "times": count} for usr, count in mentions.most_common(30)
        ],
        "technologies": [
            {"tech": tech, "times": count} for tech, count in techs.most_common(30)
        ],
        "deleted_removed_items": sorted(
            flagged, key=lambda entry: entry["utc"] or "", reverse=True
        ),
        "items": [summarize_item(item, kind, 2000) for kind, item in everything],
    }


def iso(ts: int | float | None) -> str | None:
    """Unix timestamp → ISO-8601 UTC, or ``None``."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts, UTC).isoformat()


class RedditOsint:
    """Async Reddit archive client with optional proxy and OAuth support."""

    def __init__(
        self,
        *,
        arctic: str = ARCTIC_DEFAULT,
        pullpush: str = PULLPUSH_DEFAULT,
        timeout: float = 20.0,
        delay: float = DEFAULT_DELAY,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_attempts: int = 3,
        rate_limit_retries: int = 2,
        max_backoff: float = 120.0,
        proxy: str | None = None,
        client_id: str = "",
        client_secret: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
        sleeper=None,
    ):
        logger.debug("Init: RedditOsint")
        self.arctic = arctic
        self.pullpush = pullpush
        self.timeout = timeout
        self.delay = delay
        self.max_pages = max_pages
        self.max_attempts = max_attempts
        self.rate_limit_retries = rate_limit_retries
        self.max_backoff = max_backoff
        self.proxy = proxy or None
        self.client_id = client_id
        self.client_secret = client_secret
        self._transport = transport
        self._sleep = sleeper or asyncio.sleep

    # ── configuration ────────────────────────────────────────────

    def set_proxy(self, proxy: str | None) -> None:
        self.proxy = proxy or None

    def set_credentials(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""

    # ── transport ────────────────────────────────────────────────

    def _client(self, timeout: float | None = None) -> httpx.AsyncClient:
        headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
        if self._transport is not None:
            return httpx.AsyncClient(
                timeout=timeout or self.timeout,
                headers=headers,
                transport=self._transport,
                follow_redirects=True,
            )
        return httpx.AsyncClient(
            timeout=timeout or self.timeout,
            headers=headers,
            proxy=self.proxy,
            follow_redirects=True,
        )

    async def _get_json(self, client: httpx.AsyncClient, url: str) -> dict:
        last: str = "unknown error"
        for attempt in range(self.max_attempts):
            try:
                resp = await client.get(url)
            except httpx.HTTPError as exc:
                last = f"{type(exc).__name__}: {exc}"
                await self._sleep(min(0.5 * (2**attempt), 5.0))
                continue

            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError as exc:
                    last = f"invalid JSON: {exc}"
                    await self._sleep(min(0.5 * (2**attempt), 5.0))
                    continue

            body = resp.text[:180]
            banned = resp.status_code in BAN_STATUS or (
                resp.status_code in (400, 409)
                and any(hint in body.lower() for hint in BAN_HINTS)
            )
            last = f"HTTP {resp.status_code}: {body}"
            if banned:
                logger.debug(f"Reddit archive throttled: {last}")
                await self._sleep(min(self.delay + 2**attempt, MAX_BAN_SLEEP))
                continue
            raise RedditArchiveError(last)
        raise RedditArchiveError(last)

    # ── fetching ─────────────────────────────────────────────────

    async def fetch_all(
        self,
        source: str,
        kind: str,
        author: str,
        *,
        client: httpx.AsyncClient | None = None,
        subreddit: str | None = None,
        keywords: str | None = None,
        over18: bool | None = None,
        max_pages: int | None = None,
        limit: int = PAGE_LIMIT,
        on_page=None,
    ) -> list[dict]:
        """Page through one (source, kind) feed using a stable cursor."""
        owns = client is None
        client = client or self._client()
        pages = min(max_pages or self.max_pages, self.max_pages)
        out: list[dict] = []
        seen: set[str] = set()
        cursor: int | None = None
        page = 0
        rl_retries = 0
        try:
            while page < pages:
                url = build_search_url(
                    source,
                    kind,
                    author=author,
                    cursor=cursor,
                    subreddit=subreddit,
                    keywords=keywords,
                    over18=over18,
                    limit=limit,
                    arctic=self.arctic,
                    pullpush=self.pullpush,
                )
                try:
                    data = (await self._get_json(client, url)).get("data") or []
                except RedditArchiveError:
                    if rl_retries < self.rate_limit_retries:
                        rl_retries += 1
                        nap = min(self.delay + 30.0 * rl_retries, self.max_backoff)
                        await self._sleep(nap)
                        continue
                    raise
                rl_retries = 0

                if not data:
                    break
                fresh = [row for row in data if row.get("id") and row["id"] not in seen]
                seen.update(row["id"] for row in fresh)
                out.extend(fresh)
                page += 1
                if on_page:
                    on_page(source, kind, page, len(out))
                if len(data) < limit:
                    break
                oldest = min((row.get("created_utc") or 0) for row in data)
                next_cursor = oldest + 1
                if cursor and next_cursor <= cursor:
                    break
                cursor = next_cursor
                if self.delay:
                    await self._sleep(self.delay)
            return out
        finally:
            if owns:
                await client.aclose()

    async def collect(
        self,
        username: str,
        *,
        sources: tuple[str, ...] | list[str] = ("arctic", "pullpush"),
        subreddit: str | None = None,
        keywords: str | None = None,
        over18: bool | None = None,
        max_pages: int | None = None,
        client: httpx.AsyncClient | None = None,
        on_page=None,
    ) -> tuple[dict[str, list[dict]], list[str]]:
        """Fetch posts and comments from every source concurrently, merged by id."""
        sources = [src for src in sources if src in ("arctic", "pullpush")]
        if not sources:
            sources = ["arctic"]
        owns = client is None
        client = client or self._client()
        errors: list[str] = []
        try:
            jobs = [
                (source, kind) for source in sources for kind in ("posts", "comments")
            ]
            results = await asyncio.gather(
                *(
                    self.fetch_all(
                        source,
                        kind,
                        username,
                        client=client,
                        subreddit=subreddit,
                        keywords=keywords,
                        over18=over18,
                        max_pages=max_pages,
                        on_page=on_page,
                    )
                    for source, kind in jobs
                ),
                return_exceptions=True,
            )
        finally:
            if owns:
                await client.aclose()

        merged: dict[str, dict[str, dict]] = {"posts": {}, "comments": {}}
        for (source, kind), result in zip(jobs, results, strict=True):
            if isinstance(result, BaseException):
                errors.append(f"{source}/{kind}: {result}")
                continue
            for row in result:
                if row.get("id"):
                    merged[kind].setdefault(row["id"], row)

        items = {
            kind: sorted(rows.values(), key=lambda row: row.get("created_utc") or 0)
            for kind, rows in merged.items()
        }
        return items, errors

    async def fetch_meta(
        self, username: str, *, client: httpx.AsyncClient | None = None
    ) -> dict | None:
        """Fetch the archive's own profile metadata (karma, counts)."""
        owns = client is None
        client = client or self._client()
        base = self.arctic.rstrip("/")
        url = f"{base}/api/users/search?author={quote(username)}&limit=1"
        try:
            data = (await self._get_json(client, url)).get("data") or []
            return (data[0].get("_meta") if data else None) or None
        except RedditArchiveError as exc:
            logger.debug(f"Reddit profile metadata unavailable: {exc}")
            return None
        finally:
            if owns:
                await client.aclose()

    async def fetch_live_profile(
        self, username: str, *, client: httpx.AsyncClient | None = None
    ) -> dict | None:
        """Fetch the live ``/user/about`` payload via an app-only OAuth token."""
        if not (self.client_id and self.client_secret):
            return None
        owns = client is None
        client = client or self._client()
        try:
            token_resp = await client.post(
                OAUTH_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            if token_resp.status_code != 200:
                raise RedditArchiveError(
                    f"oauth HTTP {token_resp.status_code}: {token_resp.text[:120]}"
                )
            token = token_resp.json().get("access_token")
            if not token:
                return None
            resp = await client.get(
                OAUTH_ABOUT_URL.format(user=quote(username)),
                headers={"Authorization": f"bearer {token}"},
            )
            if resp.status_code != 200:
                return None
            return resp.json().get("data")
        except (RedditArchiveError, ValueError) as exc:
            logger.debug(f"Reddit live profile unavailable: {exc}")
            return None
        finally:
            if owns:
                await client.aclose()

    async def search_archive(
        self,
        *,
        keywords: str | None = None,
        kind: str = "posts",
        author: str | None = None,
        subreddit: str | None = None,
        limit: int = 50,
        sort: str = "desc",
    ) -> list[dict]:
        """Archive-wide phrase search, optionally scoped to one author."""
        async with self._client() as client:
            url = build_search_url(
                "arctic",
                kind,
                author=author,
                subreddit=subreddit,
                keywords=keywords,
                limit=limit,
                sort=sort,
                arctic=self.arctic,
                pullpush=self.pullpush,
            )
            rows = (await self._get_json(client, url)).get("data") or []
        rows.sort(key=lambda row: row.get("created_utc") or 0, reverse=sort != "asc")
        return [summarize_item(row, kind) for row in rows[:limit]]

    async def full_report(
        self,
        username: str,
        *,
        sources: tuple[str, ...] | list[str] = ("arctic", "pullpush"),
        subreddit: str | None = None,
        keywords: str | None = None,
        over18: bool | None = None,
        max_pages: int | None = None,
        include_live: bool = True,
        on_page=None,
    ) -> tuple[dict, list[str]]:
        """Collect, enrich and analyze a username in a single pass."""
        username = normalize_username(username)
        items, errors = await self.collect(
            username,
            sources=sources,
            subreddit=subreddit,
            keywords=keywords,
            over18=over18,
            max_pages=max_pages,
            on_page=on_page,
        )
        meta = await self.fetch_meta(username)
        live = await self.fetch_live_profile(username) if include_live else None
        report = analyze(username, items, meta, live)
        report["sources_merged"] = [
            src for src in sources if src in ("arctic", "pullpush")
        ] or ["arctic"]
        report["errors"] = errors
        return report, errors

    # ── rendering ────────────────────────────────────────────────

    @staticmethod
    def render_search(
        rows: list[dict],
        *,
        keywords: str | None = None,
        author: str | None = None,
        item_limit: int = 50,
    ) -> str:
        """Render archive phrase-search hits as plain text."""
        scope = author or "archive"
        lines = [
            divider(),
            title(f"Archive search: {keywords!r} @ {scope}"),
        ]
        if not rows:
            lines.append(info("No matching items"))
        for row in rows[:item_limit]:
            label = row.get("title") or row.get("text", "")[:80]
            lines.append(bullet(f"[{row.get('status')}] {label}"))
            lines.append(
                "    "
                + f"r/{row.get('subreddit') or '?'} · {row.get('utc') or '?'} "
                + f"· score {row.get('score')}"
            )
            if row.get("url"):
                lines.append(f"    {row['url']}")
        lines.append(end_of("archive search"))
        lines.append(divider())
        return "\n".join(lines)

    def render_report(
        self,
        report: dict,
        *,
        sections: list[str] | None = None,
        errors: list[str] | None = None,
        item_limit: int = 20,
    ) -> str:
        """Render the report as plain text for the debug pane."""
        wanted = set(sections or _ALL_SECTIONS)
        lines: list[str] = []
        if "overview" in wanted:
            lines += _render_overview(report)
        else:
            lines.append(divider())
            lines.append(title(f"Reddit OSINT: u/{report.get('username', '?')}"))
        if "posts" in wanted:
            lines += _render_items(report, "posts", item_limit)
        if "comments" in wanted:
            lines += _render_items(report, "comments", item_limit)
        if "removed" in wanted:
            lines += _render_removed(report, item_limit)
        if "identifiers" in wanted:
            lines += _render_identifiers(report)
        if "activity" in wanted:
            lines += _render_activity(report)
        if "affiliations" in wanted:
            lines += _render_affiliations(report)
        for message in errors if errors is not None else report.get("errors", []):
            lines.append(error(message))
        if not lines:
            lines.append(info("Nothing to show"))
        lines.append(end_of("reddit osint"))
        lines.append(divider())
        return "\n".join(lines)


_ALL_SECTIONS = (
    "overview",
    "posts",
    "comments",
    "removed",
    "identifiers",
    "activity",
    "affiliations",
)


def _render_overview(report: dict) -> list[str]:
    user = report.get("username", "?")
    totals = report.get("totals", {})
    lines = [divider(), title(f"Reddit OSINT: u/{user}")]
    lines.append(
        "  "
        + " | ".join(
            [
                f"posts {totals.get('posts', 0)}",
                f"comments {totals.get('comments', 0)}",
                f"items {totals.get('items', 0)}",
            ]
        )
    )
    lines.append(section("Status"))
    lines.append(kv("Live", totals.get("live", 0)))
    lines.append(kv("Removed by mods", totals.get("removed_by_mods", 0)))
    lines.append(kv("Deleted by author", totals.get("deleted_by_author", 0)))
    lines.append(kv("Deleted %", totals.get("deleted_pct", 0.0)))
    lines.append(kv("Items last 12m", totals.get("items_last_12m", 0)))
    lines.append(kv("First activity", totals.get("first_activity") or "?"))
    lines.append(kv("Last activity", totals.get("last_activity") or "?"))

    lines.append(section("Exposure"))
    lines.append(kv("Score (0-100)", report.get("score_exposure_0_100", 0)))

    meta = report.get("archive_meta")
    if meta:
        lines.append(section("Archive profile"))
        lines.append(kv("Total karma", meta.get("total_karma", "?")))
        lines.append(kv("Post karma", meta.get("post_karma", "?")))
        lines.append(kv("Comment karma", meta.get("comment_karma", "?")))
        lines.append(kv("Known posts", meta.get("num_posts", "?")))
        lines.append(kv("Known comments", meta.get("num_comments", "?")))

    live = report.get("live_profile")
    if live:
        lines.append(section("Live profile (Reddit API)"))
        lines.append(kv("Name", live.get("name", "?")))
        lines.append(kv("Link karma", live.get("link_karma", "?")))
        lines.append(kv("Comment karma", live.get("comment_karma", "?")))
        lines.append(kv("Created", iso(live.get("created_utc")) or "?"))
        lines.append(kv("Suspended", live.get("is_suspended", False)))
    return lines


def _render_items(report: dict, kind: str, limit: int) -> list[str]:
    items = [item for item in report.get("items", []) if item.get("kind") == kind]
    heading = "Posts" if kind == "posts" else "Comments"
    lines = [section(f"{heading} (newest first)")]
    if not items:
        lines.append(info(f"No {kind}"))
        return lines
    for item in reversed(items[-limit:]):
        label = item.get("title") or item.get("text", "")[:60]
        lines.append(bullet(f"[{item.get('status')}] {label}"))
        lines.append(
            "    "
            + f"r/{item.get('subreddit') or '?'} · {item.get('utc') or '?'} "
            + f"· score {item.get('score')}"
        )
        if item.get("url"):
            lines.append(f"    {item['url']}")
    if len(items) > limit:
        lines.append(info(f"{len(items) - limit} older items omitted"))
    return lines


def _render_removed(report: dict, limit: int) -> list[str]:
    flagged = report.get("deleted_removed_items", [])
    lines = [section(f"Removed / deleted ({len(flagged)})")]
    if not flagged:
        lines.append(info("No removed or deleted items in the archive"))
        return lines
    for entry in flagged[:limit]:
        label = entry.get("title") or entry.get("id") or "?"
        lines.append(bullet(f"[{entry.get('status')}] {label}"))
        lines.append(
            "    " + f"r/{entry.get('subreddit') or '?'} · {entry.get('utc') or '?'}"
        )
        if entry.get("permalink"):
            lines.append(f"    {entry['permalink']}")
    return lines


def _render_identifiers(report: dict) -> list[str]:
    lines = [section("Identifiers")]
    identifiers = report.get("identifiers", [])
    if identifiers:
        for identifier in identifiers:
            lines.append(bullet(identifier))
    else:
        lines.append(info("No identifiers found in post/comment text"))

    domains = report.get("external_domains", [])
    if domains:
        lines.append(section("External domains"))
        for entry in domains:
            lines.append(bullet(f"{entry['domain']} ×{entry['times']}"))

    mentions = report.get("mentioned_users", [])
    if mentions:
        lines.append(section("Mentioned users"))
        for entry in mentions:
            lines.append(bullet(f"{entry['user']} ×{entry['times']}"))
    return lines


def _render_activity(report: dict) -> list[str]:
    hours = report.get("activity_by_hour_utc", [])
    lines = [section("Activity by hour (UTC)")]
    top = max(hours) if hours else 0
    for hour, count in enumerate(hours):
        lines.append(f"  {hour:02d} {_bar(count, top)} {count}")
    weekdays = report.get("activity_by_weekday", {})
    lines.append(section("Activity by weekday"))
    for day, count in weekdays.items():
        lines.append(f"  {day} {_bar(count, max(weekdays.values() or [0]))} {count}")
    months = report.get("activity_by_month", {})
    if months:
        lines.append(section("Recent months"))
        for month, count in list(months.items())[-12:]:
            lines.append(f"  {month} {_bar(count, max(months.values()))} {count}")
    guess = report.get("timezone_guess", {})
    lines.append(section("Timezone guess"))
    lines.append(kv("Quiet window (UTC)", guess.get("quiet_window_utc", "?")))
    lines.append(kv("Estimated region", guess.get("estimated_region", "?")))
    lines.append(kv("Busiest hour (UTC)", guess.get("busiest_hour_utc") or "?"))
    return lines


def _render_affiliations(report: dict) -> list[str]:
    lines = [section("Top subreddits")]
    subs = report.get("top_subreddits", [])
    if subs:
        for entry in subs:
            lines.append(
                f"  r/{entry['subreddit']} {_bar(entry['items'], subs[0]['items'])} "
                f"{entry['items']}"
            )
    else:
        lines.append(info("No subreddit data"))
    techs = report.get("technologies", [])
    lines.append(section("Technologies"))
    if techs:
        lines.append(
            "  " + ", ".join(f"{entry['tech']} ×{entry['times']}" for entry in techs)
        )
    else:
        lines.append(info("No tracked technologies detected"))
    return lines


def _bar(count: int, top: int, width: int = 24) -> str:
    if top <= 0:
        return ""
    filled = max(1, round(count / top * width)) if count else 0
    return "█" * filled
