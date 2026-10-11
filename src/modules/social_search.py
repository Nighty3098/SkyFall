"""Social-network OSINT for open platforms (Bluesky, Mastodon, Instagram).

Only public APIs are used — no API keys required.

* **Bluesky** (AT Protocol) — public AppView at ``public.api.bsky.app``:
  handle resolution, profile lookup and actor search.
* **Mastodon** — public ActivityPub REST API on any instance
  (default ``mastodon.social``): account lookup and search.
* **Instagram** — public profile lookup via ``instaloader`` (best-effort,
  no login; Instagram often rate-limits anonymous requests).
"""

import asyncio

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

TIMEOUT = 15.0
DEFAULT_INSTANCE = "mastodon.social"
BLUESKY_API = "https://public.api.bsky.app/xrpc"
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0"


class SocialSearch:
    """Look up a username on Bluesky and Mastodon."""

    def __init__(
        self, mastodon_instance: str = DEFAULT_INSTANCE, timeout: float = TIMEOUT
    ):
        logger.debug("Init: SocialSearch")
        self.mastodon_instance = mastodon_instance.strip() or DEFAULT_INSTANCE
        self.timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
        )

    # ── Bluesky ───────────────────────────────────────────────────

    async def bluesky_profile(self, handle: str) -> dict | None:
        handle = handle.strip().lstrip("@")
        if not handle:
            return None
        candidates = [handle]
        if "." not in handle:
            candidates.append(f"{handle}.bsky.social")
        async with self._client() as client:
            for cand in candidates:
                try:
                    resp = await client.get(
                        f"{BLUESKY_API}/app.bsky.actor.getProfile",
                        params={"actor": cand},
                    )
                except Exception as exc:
                    logger.debug(f"Bluesky profile error ({cand}): {exc}")
                    continue
                if resp.status_code == 200:
                    return resp.json()
        return None

    async def bluesky_search(self, query: str, limit: int = 10) -> list[dict]:
        query = query.strip().lstrip("@")
        if not query:
            return []
        async with self._client() as client:
            try:
                resp = await client.get(
                    f"{BLUESKY_API}/app.bsky.actor.searchActors",
                    params={"q": query, "limit": limit},
                )
                resp.raise_for_status()
                return resp.json().get("actors", [])
            except Exception as exc:
                logger.debug(f"Bluesky search error: {exc}")
                return []

    # ── Mastodon ──────────────────────────────────────────────────

    def _instance_url(self, instance: str | None = None) -> str:
        host = (instance or self.mastodon_instance).strip().removeprefix("https://")
        host = host.removeprefix("http://").strip("/")
        return f"https://{host}"

    async def mastodon_lookup(
        self, username: str, instance: str | None = None
    ) -> dict | None:
        acct = username.strip().lstrip("@")
        if not acct:
            return None
        async with self._client() as client:
            try:
                resp = await client.get(
                    f"{self._instance_url(instance)}/api/v1/accounts/lookup",
                    params={"acct": acct},
                )
            except Exception as exc:
                logger.debug(f"Mastodon lookup error ({acct}): {exc}")
                return None
            if resp.status_code == 200:
                return resp.json()
        return None

    async def mastodon_search(
        self, query: str, instance: str | None = None, limit: int = 10
    ) -> list[dict]:
        query = query.strip().lstrip("@")
        if not query:
            return []
        async with self._client() as client:
            try:
                resp = await client.get(
                    f"{self._instance_url(instance)}/api/v2/search",
                    params={"q": query, "type": "accounts", "limit": limit},
                )
                resp.raise_for_status()
                return resp.json().get("accounts", [])
            except Exception as exc:
                logger.debug(f"Mastodon search error: {exc}")
                return []

    # ── Instagram ─────────────────────────────────────────────────

    async def instagram_profile(self, username: str, timeout: float = 30.0) -> dict:
        username = (username or "").strip().lstrip("@")
        if not username:
            return {"error": "Empty username"}

        def _do() -> dict:
            import instaloader

            loader = instaloader.Instaloader(
                quiet=True, download_pictures=False, download_videos=False
            )
            profile = instaloader.Profile.from_username(loader.context, username)
            return {
                "username": profile.username,
                "full_name": profile.full_name,
                "biography": profile.biography,
                "followers": profile.followers,
                "followees": profile.followees,
                "posts": profile.mediacount,
                "is_private": profile.is_private,
                "is_verified": profile.is_verified,
                "external_url": profile.external_url,
                "userid": profile.userid,
            }

        try:
            return await asyncio.wait_for(asyncio.to_thread(_do), timeout=timeout)
        except Exception as exc:
            logger.debug(f"Instagram lookup error ({username}): {exc}")
            return {"error": str(exc), "username": username}

    # ── Combined ──────────────────────────────────────────────────

    async def search_structured(
        self, username: str, instance: str | None = None
    ) -> dict:
        profile = await self.bluesky_profile(username)
        matches = await self.bluesky_search(username)
        mastodon = await self.mastodon_lookup(username, instance)
        mastodon_matches = await self.mastodon_search(username, instance)
        return {
            "bluesky": profile,
            "bluesky_matches": matches,
            "mastodon": mastodon,
            "mastodon_matches": mastodon_matches,
            "mastodon_instance": instance or self.mastodon_instance,
        }

    async def search(self, username: str, instance: str | None = None) -> str:
        username = (username or "").strip()
        if not username:
            return error("Empty username")

        data = await self.search_structured(username, instance)
        bsky = data["bluesky"]
        mstd = data["mastodon"]
        inst = data["mastodon_instance"]

        lines = [title(f"Social search: {username}")]
        lines.append(section("Bluesky"))
        if bsky:
            lines.append(bullet(bsky.get("handle", "?")))
            if bsky.get("displayName"):
                lines.append(kv("Display name", bsky["displayName"]))
            lines.append(kv("DID", bsky.get("did", "?")))
            lines.append(kv("Followers", bsky.get("followersCount", "?")))
            lines.append(kv("Following", bsky.get("followsCount", "?")))
            lines.append(kv("Posts", bsky.get("postsCount", "?")))
            lines.append(kv("Created", bsky.get("createdAt", "?")))
            if bsky.get("description"):
                lines.append(kv("Bio", bsky["description"].replace("\n", " ")[:160]))
        else:
            lines.append(info("No exact Bluesky profile"))
        other = [
            a
            for a in data["bluesky_matches"]
            if a.get("handle") != (bsky or {}).get("handle")
        ]
        if other:
            lines.append(info(f"Bluesky handle matches: {len(other)}"))
            for a in other[:5]:
                lines.append(
                    bullet(f"{a.get('handle', '?')} ({a.get('displayName', '')})")
                )

        lines.append(section(f"Mastodon @ {inst}"))
        if mstd:
            lines.append(bullet(f"@{mstd.get('acct', '?')}"))
            if mstd.get("display_name"):
                lines.append(kv("Display name", mstd["display_name"]))
            lines.append(kv("Followers", mstd.get("followers_count", "?")))
            lines.append(kv("Following", mstd.get("following_count", "?")))
            lines.append(kv("Posts", mstd.get("statuses_count", "?")))
            lines.append(kv("Created", mstd.get("created_at", "?")))
            lines.append(kv("Bot", mstd.get("bot", False)))
            lines.append(kv("Locked", mstd.get("locked", False)))
            if mstd.get("note"):
                lines.append(kv("Bio", mstd["note"].replace("\n", " ")[:160]))
        else:
            lines.append(info(f"No Mastodon account on {inst}"))
        other_m = [
            a
            for a in data["mastodon_matches"]
            if a.get("acct") != (mstd or {}).get("acct")
        ]
        if other_m:
            lines.append(info(f"Mastodon matches: {len(other_m)}"))
            for a in other_m[:5]:
                label = f"@{a.get('acct', '?')} ({a.get('display_name', '')})"
                lines.append(bullet(label))

        lines.append(end_of("social search"))
        lines.append(divider())
        return "\n".join(lines)
