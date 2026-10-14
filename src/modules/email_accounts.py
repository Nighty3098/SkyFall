"""Discover where an email address is registered (holehe-style).

Hybrid strategy:

* Built-in HTTP checks that need **no API key and no extra dependency**
  (Gravatar, Microsoft, Mozilla, ProtonMail, Duolingo, Twitter/X).
* Optional: if the ``holehe`` package is installed, its full sweep
  (~120 sites) runs as well.  The library is imported lazily, so it is
  never a hard requirement.

Both paths share a single ``httpx.AsyncClient`` and run concurrently.
"""

import asyncio
import hashlib
import re
from dataclasses import asdict, dataclass

import httpx
from loguru import logger

TIMEOUT = 15.0
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0"


@dataclass
class AccountResult:
    """A single "is this email registered here?" answer."""

    site: str
    domain: str
    registered: bool | None
    detail: str = ""


# ── Built-in checkers (no key, no dependency) ─────────────────────


async def _check_gravatar(client: httpx.AsyncClient, email: str) -> AccountResult:
    digest = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    resp = await client.get(f"https://gravatar.com/avatar/{digest}?d=404")
    if resp.status_code == 200:
        return AccountResult("Gravatar", "gravatar.com", True, "Has a Gravatar")
    if resp.status_code == 404:
        return AccountResult("Gravatar", "gravatar.com", False)
    return AccountResult("Gravatar", "gravatar.com", None, f"HTTP {resp.status_code}")


async def _check_microsoft(client: httpx.AsyncClient, email: str) -> AccountResult:
    resp = await client.post(
        "https://login.microsoftonline.com/common/GetCredentialType",
        json={"Username": email},
        headers={"Content-Type": "application/json"},
    )
    data = resp.json()
    if_exists = data.get("IfExistsResult")
    if if_exists == 0:
        return AccountResult("Microsoft", "microsoft.com", True)
    if if_exists == 1:
        return AccountResult("Microsoft", "microsoft.com", False)
    if if_exists in (5, 6):
        return AccountResult(
            "Microsoft", "microsoft.com", True, "Federated / external account"
        )
    return AccountResult("Microsoft", "microsoft.com", None, f"code {if_exists}")


async def _check_mozilla(client: httpx.AsyncClient, email: str) -> AccountResult:
    resp = await client.post(
        "https://api.accounts.firefox.com/v1/account/status",
        json={"email": email},
    )
    exists = resp.json().get("exists")
    if exists is True:
        return AccountResult("Mozilla", "mozilla.com", True)
    if exists is False:
        return AccountResult("Mozilla", "mozilla.com", False)
    return AccountResult("Mozilla", "mozilla.com", None, f"HTTP {resp.status_code}")


async def _check_protonmail(client: httpx.AsyncClient, email: str) -> AccountResult:
    resp = await client.get(
        "https://api.protonmail.ch/pks/lookup",
        params={"op": "get", "search": email},
    )
    if resp.status_code == 200 and "BEGIN PGP PUBLIC KEY" in resp.text:
        return AccountResult("ProtonMail", "proton.me", True, "PGP key published")
    if resp.status_code == 200 and "No results found" in resp.text:
        return AccountResult("ProtonMail", "proton.me", False)
    if resp.status_code == 404:
        return AccountResult("ProtonMail", "proton.me", False)
    return AccountResult("ProtonMail", "proton.me", None, f"HTTP {resp.status_code}")


async def _check_duolingo(client: httpx.AsyncClient, email: str) -> AccountResult:
    resp = await client.get(
        "https://www.duolingo.com/2017-06-30/users", params={"email": email}
    )
    data = resp.json()
    users = data.get("users") if isinstance(data, dict) else None
    if isinstance(users, list):
        return AccountResult(
            "Duolingo", "duolingo.com", bool(users), f"{len(users)} profile(s)"
        )
    return AccountResult("Duolingo", "duolingo.com", None, f"HTTP {resp.status_code}")


async def _check_twitter(client: httpx.AsyncClient, email: str) -> AccountResult:
    resp = await client.get(
        "https://api.twitter.com/i/users/email_available.json",
        params={"email": email},
    )
    valid = resp.json().get("valid")
    if valid is True:
        return AccountResult("Twitter / X", "x.com", False)
    if valid is False:
        return AccountResult("Twitter / X", "x.com", True)
    return AccountResult("Twitter / X", "x.com", None, f"HTTP {resp.status_code}")


_BUILTIN_CHECKERS = (
    _check_gravatar,
    _check_microsoft,
    _check_mozilla,
    _check_protonmail,
    _check_duolingo,
    _check_twitter,
)


# ── Optional holehe integration ───────────────────────────────────


def _holehe_available() -> bool:
    try:
        import holehe.core  # noqa: F401

        return True
    except Exception:
        return False


async def _run_holehe(
    client: httpx.AsyncClient, email: str, timeout: float
) -> list[AccountResult]:
    if not _holehe_available():
        return []
    try:
        from holehe.core import get_functions, import_submodules

        modules = import_submodules("holehe.modules")
        functions = get_functions(modules, None)
    except Exception as exc:  # pragma: no cover - depends on optional pkg
        logger.warning(f"holehe import failed: {exc}")
        return []

    out: list[dict] = []

    async def _safe(func) -> None:
        try:
            await func(email, client, out)
        except Exception:
            return

    await asyncio.gather(*[_safe(f) for f in functions], return_exceptions=True)

    results: list[AccountResult] = []
    for entry in out:
        if entry.get("rateLimit"):
            continue
        if entry.get("error"):
            continue
        name = entry.get("name", "?")
        detail_parts = []
        for field in ("emailrecovery", "phoneNumber"):
            if entry.get(field):
                detail_parts.append(str(entry[field]))
        results.append(
            AccountResult(
                site=name,
                domain=entry.get("domain", ""),
                registered=bool(entry.get("exists")),
                detail=" / ".join(detail_parts),
            )
        )
    return results


# ── Public API ────────────────────────────────────────────────────


class EmailAccounts:
    """Find the services an email address is registered on."""

    def __init__(self, timeout: float = TIMEOUT):
        logger.debug("Init: EmailAccounts")
        self.timeout = timeout
        self.holehe_available = _holehe_available()

    async def accounts(self, email: str) -> list[dict]:
        email = (email or "").strip()
        if not _EMAIL_RE.fullmatch(email):
            return []

        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        results: list[AccountResult] = []
        async with httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=True, headers=headers
        ) as client:
            raw = await asyncio.gather(
                *[checker(client, email) for checker in _BUILTIN_CHECKERS],
                return_exceptions=True,
            )
            for checker, item in zip(_BUILTIN_CHECKERS, raw, strict=True):
                if isinstance(item, AccountResult):
                    results.append(item)
                else:
                    site = checker.__name__.removeprefix("_check_").title()
                    reason = str(item) or type(item).__name__
                    results.append(AccountResult(site, "", None, reason))
            results.extend(await _run_holehe(client, email, self.timeout))

        results.sort(key=lambda r: (r.registered is not True, r.site.lower()))
        return [asdict(r) for r in results]

    async def check(self, email: str) -> dict:
        email = (email or "").strip()
        if not _EMAIL_RE.fullmatch(email):
            return {
                "email": email,
                "error": f"Invalid email address: {email or '(empty)'}",
            }

        results = await self.accounts(email)
        if not results:
            return {"email": email, "error": "No checks were performed."}

        registered = [r for r in results if r["registered"] is True]
        absent = [r for r in results if r["registered"] is False]
        unknown = [r for r in results if r["registered"] is None]

        engine = "built-in + holehe" if self.holehe_available else "built-in"
        return {
            "email": email,
            "engine": engine,
            "summary": f"{len(registered)} found / {len(results)} checked",
            "registered": [
                {"site": r["site"], "detail": r["detail"]} for r in registered
            ],
            "not_found": [r["site"] for r in absent],
            "unknown": [
                {"site": r["site"], "detail": r["detail"] or "unknown"} for r in unknown
            ],
        }
