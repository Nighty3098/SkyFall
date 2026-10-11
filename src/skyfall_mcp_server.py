import argparse
import hmac
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anyio.to_thread

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from src.security import (
    AUTH_ENV,
    TOKEN_ENV,
    decrypt_settings,
    get_or_create_token,
)

CONFIG_DIR = Path.home() / ".skyfall"
CONFIG_FILE = CONFIG_DIR / "settings.json"


def _load_settings() -> dict:
    if CONFIG_FILE.exists():
        try:
            return decrypt_settings(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            return {}
    return {}


_settings = _load_settings()


def _auth_enabled() -> bool:
    env = os.environ.get(AUTH_ENV)
    if env is not None:
        return env.strip().lower() in ("1", "true", "yes", "on")
    return bool(_settings.get("mcp_require_auth", False))


_AUTH_ENABLED = _auth_enabled()
_MCP_TOKEN = os.environ.get(TOKEN_ENV) or (
    get_or_create_token() if _AUTH_ENABLED else ""
)


class _StaticTokenVerifier:
    """Accept a single pre-shared bearer token (local, non-OAuth deployment)."""

    def __init__(self, token: str):
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if self._token and hmac.compare_digest(self._token, token):
            return AccessToken(token=token, client_id="skyfall-local", scopes=[])
        return None


def _auth_settings(host: str = "127.0.0.1", port: int = 9877) -> AuthSettings:
    url = f"http://{host}:{port}"
    return AuthSettings(issuer_url=url, resource_server_url=url)


class _OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url
        self._model = _settings.get(
            "ollama_model",
            "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q8_0",
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        import httpx

        with httpx.Client(base_url=self.base_url, timeout=120) as client:
            resp = client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json()

    def _generate(self, prompt: str) -> str:
        import httpx

        logger.debug(f"Prompt length: {len(prompt)} chars, model: {self._model}")
        with httpx.Client(base_url=self.base_url, timeout=600) as client:
            resp = client.post(
                "/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                return f"Error from Ollama: {data['error']}"
            return data.get("response", "")

    def set_model(self, model: str) -> str:
        self._model = model
        return f"Model set to: {self._model}"

    def get_model(self) -> str:
        return self._model

    def list_models(self) -> list[dict]:
        data = self._request("GET", "/api/tags")
        return data.get("models", [])

    def set_base_url(self, url: str) -> str:
        self.base_url = url
        return f"Ollama base URL set to: {self.base_url}"


_ollama = _OllamaClient()

mcp = FastMCP(
    "SkyFall MCP Server",
    host="127.0.0.1",
    port=9877,
    auth=_auth_settings() if _AUTH_ENABLED else None,
    token_verifier=_StaticTokenVerifier(_MCP_TOKEN) if _AUTH_ENABLED else None,
    instructions="""
MCP server for the SkyFall OSINT toolkit. Provides tools to:
- Analyze domains (DNS, WHOIS, SSL, NMAP, WAF, malware, subdomains+brute,
  threat intel via AbuseIPDB/GreyNoise/ThreatFox/URLHaus, JS secrets scan)
- Search usernames across 3300+ sites
- Look up usernames on Bluesky, Mastodon and Instagram
- Search emails via IntelX and HIBP, and find accounts registered to an email
- Search leaks and infostealer logs (Hudson Rock, LeakCheck, HIBP, Dehashed)
- Geo analysis: sun/shadow geometry, shadow geolocation, NASA FIRMS fires,
  GDACS disaster alerts
- Web archives: Wayback Machine (check, list, save) and archive.today
- Analyze phone numbers
- GitHub OSINT (users, repos, commits, secrets)
- Blockchain transaction search across 10+ chains
- MAC/BSSID geolocation
- File analysis and steganography
- Dorking with 7974 Google dorks
- Interactive graph building (nodes and edges)
- Generate AI OSINT reports via Ollama

Data tools return JSON strings. Report generation returns plain text markdown.
Graph tools require a running SkyFall GUI. Without GUI they return descriptive errors.
""",
)


def _extract_json(obj: str | dict | list, error_msg: str = "No data") -> str:
    try:
        if isinstance(obj, str):
            parsed = json.loads(obj)
        else:
            parsed = obj
        return json.dumps(parsed, ensure_ascii=False, default=str, indent=2)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"raw": str(obj)}, ensure_ascii=False)


def _try_get_qt_app() -> tuple:
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None, None
        from src.libs.graph_lib import GraphWidget, NodeItem

        for widget in app.allWidgets():
            if isinstance(widget, GraphWidget):
                return widget, NodeItem
        return None, None
    except Exception:
        return None, None


def _graph_not_available() -> str:
    return json.dumps(
        {
            "error": "Graph requires a running SkyFall GUI (PySide6 QApplication)",
        },
        ensure_ascii=False,
    )


def _graph_bridge():
    try:
        from src.graph_bridge import GraphBridgeClient

        return GraphBridgeClient()
    except Exception:
        return None


def _graph_bridge_available() -> bool:
    try:
        import socket

        from src.graph_bridge import GRAPH_BRIDGE_HOST, GRAPH_BRIDGE_PORT

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((GRAPH_BRIDGE_HOST, GRAPH_BRIDGE_PORT))
        s.close()
        return True
    except Exception:
        return False


async def _graph_bridge_send(bridge, method: str, *args, **kwargs) -> str:
    """Run a bridge method in a thread to avoid blocking the event loop."""
    func = getattr(bridge, method)
    result = await anyio.to_thread.run_sync(lambda: func(*args, **kwargs))
    return _extract_json(result)


def _graph_not_available_bridge() -> str:
    return json.dumps(
        {
            "error": "Graph bridge not available. "
            "Start SkyFall GUI and click 'Start MCP Server' in SETTINGS.",
        },
        ensure_ascii=False,
    )


# ── Ollama tools ──────────────────────────────────────────────────────


@mcp.tool()
def skyfall_ollama_list_models() -> str:
    """List all available models in local Ollama."""
    try:
        models = _ollama.list_models()
        return _extract_json(
            [{"name": m["name"], "size": m.get("size", 0)} for m in models]
        )
    except Exception as e:
        return _extract_json({"error": str(e)})


@mcp.tool()
def skyfall_ollama_set_model(model_name: str) -> str:
    """Set the Ollama model to use for report generation."""
    return _ollama.set_model(model_name)


@mcp.tool()
def skyfall_ollama_get_model() -> str:
    """Get the currently configured Ollama model name."""
    return json.dumps({"model": _ollama.get_model()})


@mcp.tool()
def skyfall_ollama_set_url(url: str) -> str:
    """Set the Ollama API base URL."""
    return _ollama.set_base_url(url)


# ── Domain Analyzer ───────────────────────────────────────────────────


async def _make_da():
    from src.modules.domain_analyzer import DomainAnalyzer

    s = _settings
    return DomainAnalyzer(
        virustotal_api_key=s.get("virustotal_api_key", ""),
        google_safe_api_key=s.get("google_safe_api_key", ""),
        ipinfo_api_key=s.get("ipinfo_api_key", ""),
        abuseipdb_api_key=s.get("abuseipdb_api_key", ""),
        greynoise_api_key=s.get("greynoise_api_key", ""),
    )


@mcp.tool()
async def skyfall_domain_ip(domain: str) -> str:
    """Resolve domain to IP and get geolocation data."""
    da = await _make_da()
    result = await da.get_ip_and_location(domain)
    if isinstance(result, str):
        return result
    return _extract_json(result)


@mcp.tool()
async def skyfall_ip_domains(ip: str) -> str:
    """Find domains on an IP via PTR + Shodan InternetDB + HackerTarget."""
    da = await _make_da()
    result = await da.get_domains_on_ip(ip)
    return _extract_json(result)


@mcp.tool()
async def skyfall_domain_dns(domain: str) -> str:
    """Get DNS records (A, AAAA, MX, TXT, NS, CNAME, SOA) for a domain."""
    da = await _make_da()
    result = await da.get_dns(domain)
    return result if isinstance(result, str) else _extract_json(result)


@mcp.tool()
async def skyfall_domain_whois(domain: str) -> str:
    """Get WHOIS information for a domain."""
    da = await _make_da()
    result = await da.get_whois_info(domain)
    if isinstance(result, str):
        return result
    return _extract_json(result)


@mcp.tool()
async def skyfall_domain_ssl(domain: str) -> str:
    """Get SSL/TLS certificate info for a domain."""
    da = await _make_da()
    result = await da.get_ssl_tls_info(domain)
    if isinstance(result, str):
        return result
    return _extract_json(result)


@mcp.tool()
async def skyfall_domain_headers(domain: str) -> str:
    """Get HTTP response headers for a domain."""
    da = await _make_da()
    result = await da.get_http_headers(domain)
    if isinstance(result, str):
        return result
    return _extract_json(result)


@mcp.tool()
async def skyfall_domain_web_stack(domain: str) -> str:
    """Detect web technology stack for a domain."""
    da = await _make_da()
    result = await da.analyze_web_stack(domain)
    if isinstance(result, str):
        return result
    return _extract_json(result)


@mcp.tool()
async def skyfall_domain_nmap(domain: str, ports: str = "1-1024") -> str:
    """Run NMAP port scan on a domain.

    Args:
        domain: Target domain or IP
        ports: Port range to scan (e.g. "1-1024", "80,443,8080")
    """
    da = await _make_da()
    result = await da.run_nmap_scan(domain, ports)
    if isinstance(result, (dict, list)):
        return _extract_json(result)
    return str(result)


@mcp.tool()
async def skyfall_domain_waf(domain: str) -> str:
    """Detect WAF (Web Application Firewall) for a domain."""
    da = await _make_da()
    result = await da.detect_waf(domain)
    if isinstance(result, (dict, list)):
        return _extract_json(result)
    return str(result)


@mcp.tool()
async def skyfall_domain_malware(domain: str) -> str:
    """Check domain reputation across VT, Google Safe Browsing, CRDF Labs,
    AbuseIPDB, GreyNoise, ThreatFox and URLHaus (aggregated verdict)."""
    da = await _make_da()
    result = await da.check_malware_reputation(domain)
    if isinstance(result, (dict, list)):
        return _extract_json(result)
    return str(result)


@mcp.tool()
async def skyfall_domain_subdomains(domain: str, use_brute: bool = True) -> str:
    """Discover subdomains via passive sources + DNS brute-force.

    Args:
        domain: Target domain (e.g. "example.com")
        use_brute: Also brute-force common labels via DNS (default: True)
    """
    da = await _make_da()
    result = await da.find_subdomains(domain, use_brute=use_brute)
    return result if isinstance(result, str) else str(result)


@mcp.tool()
async def skyfall_domain_threat_intel(target: str) -> str:
    """One-click reputation: AbuseIPDB + GreyNoise + ThreatFox + URLHaus.

    Args:
        target: Domain or IP address
    """
    da = await _make_da()
    result = await da.check_threat_intel(target)
    return result if isinstance(result, str) else _extract_json(result)


@mcp.tool()
async def skyfall_domain_js_secrets(domain: str, max_files: int = 15) -> str:
    """Scan site JavaScript for exposed API keys, secrets and endpoints.

    Args:
        domain: Target domain (e.g. "example.com")
        max_files: Max JS files to download and scan (default: 15)
    """
    da = await _make_da()
    return await da.scan_js_secrets(domain, max_files=max_files)


@mcp.tool()
async def skyfall_domain_robots(domain: str) -> str:
    """Get robots.txt content for a domain."""
    da = await _make_da()
    return await da.get_robots_txt(domain)


@mcp.tool()
async def skyfall_domain_security_txt(domain: str) -> str:
    """Get security.txt content for a domain."""
    da = await _make_da()
    return await da.get_security_txt(domain)


@mcp.tool()
async def skyfall_domain_social_tags(domain: str) -> str:
    """Get Open Graph and Twitter social tags from a domain."""
    da = await _make_da()
    return await da.get_social_tags(domain)


# ── Username Search ───────────────────────────────────────────────────


@mcp.tool()
async def skyfall_username_search(username: str, timeout: int = 60) -> str:
    """Search for a username across ~3307 sites (Sherlock-style)."""
    from src.modules.username_search import UsernameSearch

    searcher = UsernameSearch()
    results = await searcher.acheck(username, timeout=timeout)
    claimed = [r for r in results if r["status"] == UsernameSearch.Status.CLAIMED]
    return _extract_json(
        {
            "username": username,
            "total_checked": len(results),
            "claimed": len(claimed),
            "results": [
                {
                    "site": r["site"],
                    "url": r["url_user"],
                    "status": r["status"],
                    "http_status": r.get("http_status", ""),
                }
                for r in claimed
            ],
        }
    )


@mcp.tool()
async def skyfall_maigret_search(username: str) -> str:
    """Search for a username across ~510 sites via Maigret engine."""
    from src.modules.maigret_search import MaigretSearch

    ms = MaigretSearch()
    result = await ms.search_and_report(username)
    return result


@mcp.tool()
async def skyfall_social_search(username: str, mastodon_instance: str = "") -> str:
    """Find a username on Bluesky and Mastodon (public APIs, no keys)."""
    from src.modules.social_search import SocialSearch

    engine = SocialSearch()
    data = await engine.search_structured(username, mastodon_instance or None)
    return _extract_json(data)


@mcp.tool()
async def skyfall_instagram_profile(username: str) -> str:
    """Look up a public Instagram profile by username (via instaloader)."""
    from src.modules.social_search import SocialSearch

    engine = SocialSearch()
    data = await engine.instagram_profile(username)
    return _extract_json(data)


# ── Email Search ──────────────────────────────────────────────────────


@mcp.tool()
async def skyfall_email_intelx(email: str) -> str:
    """Search email in IntelX intelligence database."""
    from src.modules.mail_search_engine import MailSearchEngine

    s = _settings
    engine = MailSearchEngine(
        intelx_api_key=s.get("intelligent_x_api_key", ""),
        hibp_api_key=s.get("hibp_api_key", ""),
    )
    return await engine.search_intelx(email)


@mcp.tool()
async def skyfall_email_hibp(email: str) -> str:
    """Check email against Have I Been Pwned breach database."""
    from src.modules.mail_search_engine import MailSearchEngine

    s = _settings
    engine = MailSearchEngine(
        intelx_api_key=s.get("intelligent_x_api_key", ""),
        hibp_api_key=s.get("hibp_api_key", ""),
    )
    return await engine.check_hibp(email)


@mcp.tool()
async def skyfall_email_search(email: str) -> str:
    """Search email in all sources (IntelX + HIBP)."""
    from src.modules.mail_search_engine import MailSearchEngine

    s = _settings
    engine = MailSearchEngine(
        intelx_api_key=s.get("intelligent_x_api_key", ""),
        hibp_api_key=s.get("hibp_api_key", ""),
    )
    intelx_result = await engine.search_intelx(email)
    hibp_result = await engine.check_hibp(email)
    return _extract_json(
        {
            "email": email,
            "intelx": intelx_result,
            "hibp": hibp_result,
        }
    )


@mcp.tool()
async def skyfall_email_accounts(email: str) -> str:
    """Find services where an email is registered (Gravatar, Microsoft, etc.)."""
    from src.modules.email_accounts import EmailAccounts

    engine = EmailAccounts()
    results = await engine.accounts(email)
    return _extract_json({"email": email, "accounts": results})


@mcp.tool()
async def skyfall_email_header_file(filepath: str) -> str:
    """Analyze .eml file headers: Received chain, SPF/DKIM/DMARC, origin IP geo."""
    from src.modules.email_header_analyzer import EmailHeaderAnalyzer

    analyzer = EmailHeaderAnalyzer()
    return await analyzer.analyze_file(filepath)


@mcp.tool()
async def skyfall_email_header_text(headers: str) -> str:
    """Analyze pasted email headers (Received chain, auth, verdict)."""
    from src.modules.email_header_analyzer import EmailHeaderAnalyzer

    analyzer = EmailHeaderAnalyzer()
    return await analyzer.analyze_text(headers)


# ── Leaks / Infostealers ──────────────────────────────────────────────


def _leak_keys() -> dict:
    s = _settings
    return {
        "leakcheck_api_key": s.get("leakcheck_api_key", ""),
        "dehashed_email": s.get("dehashed_email", ""),
        "dehashed_api_key": s.get("dehashed_api_key", ""),
        "hibp_api_key": s.get("hibp_api_key", ""),
    }


@mcp.tool()
async def skyfall_leak_check(target: str) -> str:
    """Search leaks and infostealer logs for an email, username or domain.

    Aggregates Hudson Rock (infostealers, no key), LeakCheck, HIBP and
    Dehashed. Optional providers require API keys in SkyFall settings.
    """
    from src.modules.leak_search import LeakSearch

    engine = LeakSearch()
    data = await engine.search_all(target, _leak_keys())
    return _extract_json(data)


@mcp.tool()
async def skyfall_infostealer_search(target: str) -> str:
    """Search Hudson Rock infostealer logs for an email, username or domain."""
    from src.modules.leak_search import LeakSearch

    engine = LeakSearch()
    data = await engine.infostealer(target)
    return _extract_json(data)


# ── Phone Search ──────────────────────────────────────────────────────


@mcp.tool()
def skyfall_phone_parse(phone: str, default_region: str = "RU") -> str:
    """Parse and validate a phone number.

    Args:
        phone: Phone number to parse
        default_region: 2-letter ISO country code (e.g. RU, US, DE)
    """
    from src.modules.phone_search import PhoneSearch

    ps = PhoneSearch()
    parse_result = ps.parse_and_validate(phone, default_region=default_region)
    return parse_result


@mcp.tool()
async def skyfall_phone_reverse_lookup(phone: str) -> str:
    """Reverse phone lookup via NumVerify and AbstractAPI."""
    from src.modules.phone_search import PhoneSearch

    s = _settings
    ps = PhoneSearch()
    result = await ps.reverse_lookup(
        phone,
        numverify_key=s.get("numverify_api_key", ""),
        abstractapi_key=s.get("abstractapi_api_key", ""),
    )
    return result


@mcp.tool()
async def skyfall_phone_leak_check(phone: str) -> str:
    """Check phone number in IntelX leak database."""
    from src.modules.phone_search import PhoneSearch

    s = _settings
    ps = PhoneSearch()
    result = await ps.check_leaks(
        phone,
        intelx_key=s.get("intelligent_x_api_key", ""),
    )
    return result


@mcp.tool()
async def skyfall_phone_full(phone: str, default_region: str = "RU") -> str:
    """Full phone OSINT: parse, reverse lookup, leak check."""
    from src.modules.phone_search import PhoneSearch

    s = _settings
    ps = PhoneSearch()
    parse_result = ps.parse_and_validate(phone, default_region=default_region)
    rev_result = await ps.reverse_lookup(
        phone,
        numverify_key=s.get("numverify_api_key", ""),
        abstractapi_key=s.get("abstractapi_api_key", ""),
    )
    leak_result = await ps.check_leaks(
        phone,
        intelx_key=s.get("intelligent_x_api_key", ""),
    )
    return _extract_json(
        {
            "phone": phone,
            "parse": parse_result,
            "reverse_lookup": rev_result,
            "leak_check": leak_result,
        }
    )


@mcp.tool()
async def skyfall_phone_7tel(phone: str) -> str:
    """Search phone number on 7tel.ru for caller ID reviews and reputation.

    Returns rating score, carrier info, region, line type, reviews with dates,
    and similar phone numbers. No API key required.
    """
    from src.modules.phone_search import PhoneSearch

    ps = PhoneSearch()
    return await ps.search_7tel(phone)


# ── GitHub OSINT ──────────────────────────────────────────────────────


@mcp.tool()
async def skyfall_github_user(username: str) -> str:
    """Get GitHub user profile information."""
    from src.modules.github_search import GitHubSearch

    s = _settings
    gh = GitHubSearch(token=s.get("github_token", ""))
    return await gh.search_user(username)


@mcp.tool()
async def skyfall_github_repo_search(query: str) -> str:
    """Search GitHub repositories.

    Args:
        query: GitHub search query (e.g. "skyfall osint" or "user:nighty3098")
    """
    from src.modules.github_search import GitHubSearch

    s = _settings
    gh = GitHubSearch(token=s.get("github_token", ""))
    return await gh.search_repos(query)


@mcp.tool()
async def skyfall_github_commit_search(query: str) -> str:
    """Search GitHub commits for emails or keywords.

    Args:
        query: Search query (e.g. "nighty3098 email" or a domain)
    """
    from src.modules.github_search import GitHubSearch

    s = _settings
    gh = GitHubSearch(token=s.get("github_token", ""))
    return await gh.search_commits(query)


@mcp.tool()
async def skyfall_github_email_search(query: str) -> str:
    """Search GitHub code for emails associated with a query."""
    from src.modules.github_search import GitHubSearch

    s = _settings
    gh = GitHubSearch(token=s.get("github_token", ""))
    return await gh.search_emails(query)


@mcp.tool()
async def skyfall_github_secret_search(query: str) -> str:
    """Search GitHub for exposed secrets/tokens.

    Args:
        query: Search query (e.g. "nighty3098" or org name)
    """
    from src.modules.github_search import GitHubSearch

    s = _settings
    gh = GitHubSearch(token=s.get("github_token", ""))
    return await gh.search_secrets(query)


@mcp.tool()
async def skyfall_github_dork(query: str) -> str:
    """Search GitHub with a custom dork query."""
    from src.modules.github_search import GitHubSearch

    s = _settings
    gh = GitHubSearch(token=s.get("github_token", ""))
    return await gh.search_dork(query)


# ── Blockchain Search ─────────────────────────────────────────────────


@mcp.tool()
async def skyfall_blockchain_search(
    network: str,
    coin: str,
    time_from: str,
    time_to: str,
    amount: float | None = None,
    memo: str | None = None,
) -> str:
    """Search blockchain transactions by time range and optional amount/memo.

    Supported networks: tron, ton, eth, bsc, base, sol, btc, ltc, doge, bch
    Supported coins: USDT, BTC, ETH, TRX, TON, SOL, LTC, DOGE, BCH, BNB, etc.

    Args:
        network: Blockchain network name (e.g. "tron", "eth", "btc")
        coin: Coin/token symbol (e.g. "USDT", "BTC", "ETH")
        time_from: Start time (ISO format, e.g. "2025-01-01T00:00:00")
        time_to: End time (ISO format, e.g. "2025-06-01T00:00:00")
        amount: Optional exact amount to match
        memo: Optional memo text to search for
    """
    from src.modules.blockchain_search import BlockchainSearch

    s = _settings
    bs = BlockchainSearch(
        {
            "trongrid_api_key": s.get("trongrid_api_key", ""),
            "etherscan_api_key": s.get("etherscan_api_key", ""),
            "bscscan_api_key": s.get("bscscan_api_key", ""),
            "tonapi_api_key": s.get("tonapi_api_key", ""),
            "helius_api_key": s.get("helius_api_key", ""),
        }
    )
    try:
        dt_from = datetime.fromisoformat(time_from)
        dt_to = datetime.fromisoformat(time_to)
    except ValueError as e:
        return _extract_json({"error": f"Invalid date format: {e}"})

    result = await bs.search(
        network=network,
        coin=coin,
        time_from=dt_from,
        time_to=dt_to,
        amount=amount,
        memo=memo,
    )
    return result


# ── MAC / BSSID Geolocation ─────────────────────────────────────────────


@mcp.tool()
def skyfall_mac_locate(mac: str, providers: str = "all") -> str:
    """Geolocate a MAC address or BSSID using multiple providers.

    Providers: Yandex, Apple, Google, Microsoft, Mylnikov

    Args:
        mac: MAC address or BSSID (e.g. "00:11:22:33:44:55")
        providers: Comma-separated providers or "all"
    """
    from src.modules.mac_location import MacLocation

    ml = MacLocation()
    provider_list = (
        None if providers == "all" else [p.strip() for p in providers.split(",")]
    )
    result = ml.locate_json(mac, providers=provider_list)
    return _extract_json(result)


# ── Geo Analysis ──────────────────────────────────────────────────────


@mcp.tool()
def skyfall_geo_sun_shadow(latitude: float, longitude: float) -> str:
    """Compute sun position and cast-shadow geometry for a coordinate (UTC now).

    Returns sun altitude/azimuth, shadow bearing and shadow length ratio.
    """
    from src.modules.geo_analysis import GeoAnalysis

    engine = GeoAnalysis()
    data = engine.sun_shadow(latitude, longitude, datetime.now())
    return _extract_json(data)


@mcp.tool()
def skyfall_shadow_geolocate(
    shadow_ratio: float,
    shadow_bearing: float,
    iso_time: str = "",
    step: float = 2.0,
) -> str:
    """Find candidate coordinates matching an observed shadow.

    Args:
        shadow_ratio: Shadow length / object height
        shadow_bearing: Compass direction the shadow points to (degrees)
        iso_time: Observation time (ISO 8601, UTC). Defaults to now.
        step: Grid step in degrees (smaller = slower, more precise)
    """
    from src.modules.geo_analysis import GeoAnalysis

    when = datetime.fromisoformat(iso_time) if iso_time else datetime.now()
    engine = GeoAnalysis()
    results = engine.shadow_search(shadow_ratio, shadow_bearing, when, step=step)
    return _extract_json({"count": len(results), "candidates": results})


@mcp.tool()
async def skyfall_firms_fires(
    latitude: float = 0.0,
    longitude: float = 0.0,
    day_range: int = 1,
) -> str:
    """Active fires near a coordinate from NASA FIRMS (requires MAP_KEY)."""
    from src.modules.geo_analysis import GeoAnalysis

    engine = GeoAnalysis()
    engine.firms_key = _settings.get("firms_map_key", "")
    bbox = (longitude - 2.0, latitude - 2.0, longitude + 2.0, latitude + 2.0)
    data = await engine.firms(
        _settings.get("firms_map_key", ""), bbox=bbox, day_range=day_range
    )
    return _extract_json(data)


@mcp.tool()
async def skyfall_gdacs_disasters(
    event_types: str = "EQ,TC,FL,VO,WF,DR",
    date_from: str = "",
    date_to: str = "",
) -> str:
    """Recent global disaster alerts from GDACS (no key).

    Args:
        event_types: Comma list (EQ,TC,FL,VO,WF,DR)
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
    """
    from src.modules.geo_analysis import GeoAnalysis

    engine = GeoAnalysis()
    data = await engine.gdacs(event_types, date_from or None, date_to or None)
    return _extract_json(data)


# ── Archive / Evidence ────────────────────────────────────────────────


@mcp.tool()
async def skyfall_archive_url(url: str) -> str:
    """Check the Wayback Machine and archive.today for an archived URL."""
    from src.modules.archive_search import ArchiveSearch

    engine = ArchiveSearch()
    availability = await engine.availability(url)
    archive_today = await engine.archive_today(url)
    return _extract_json(
        {"url": url, "wayback": availability, "archive_today": archive_today}
    )


@mcp.tool()
async def skyfall_archive_snapshots(url: str, limit: int = 20) -> str:
    """List Wayback Machine snapshots (CDX) for a URL."""
    from src.modules.archive_search import ArchiveSearch

    engine = ArchiveSearch()
    return _extract_json(await engine.snapshots(url, limit))


@mcp.tool()
async def skyfall_archive_save(url: str) -> str:
    """Submit a URL to the Wayback Machine (best-effort, may take a while)."""
    from src.modules.archive_search import ArchiveSearch

    engine = ArchiveSearch()
    return _extract_json(await engine.save(url))


# ── File Analysis ──────────────────────────────────────────────────────


@mcp.tool()
def skyfall_file_info(filepath: str) -> str:
    """Get basic file info: size, MIME type, dimensions, GPS coords."""
    from src.modules.file_analyzer import FileAnalyzer

    fa = FileAnalyzer(virustotal_api_key="")
    result = fa.extract_file_info_sync(filepath)
    return _extract_json(result)


@mcp.tool()
async def skyfall_file_metadata(filepath: str) -> str:
    """Extract metadata from a file (EXIF, Hachoir)."""
    from src.modules.file_analyzer import FileAnalyzer

    fa = FileAnalyzer(virustotal_api_key="")
    return await fa.get_metadata(filepath)


@mcp.tool()
async def skyfall_file_virustotal(filepath: str) -> str:
    """Check file against VirusTotal by hash and optionally upload."""
    from src.modules.file_analyzer import FileAnalyzer

    s = _settings
    fa = FileAnalyzer(virustotal_api_key=s.get("virustotal_api_key", ""))
    result = await fa.virustotal_analyze(filepath)
    return (
        result
        if result
        else _extract_json(
            {"error": "VirusTotal API key not configured or file not found"}
        )
    )


@mcp.tool()
async def skyfall_file_tail_data(filepath: str) -> str:
    """Check for hidden data after EOF markers in files."""
    from src.modules.file_analyzer import FileAnalyzer

    fa = FileAnalyzer(virustotal_api_key="")
    return await fa.check_tail_data(filepath)


@mcp.tool()
async def skyfall_file_strings(filepath: str, min_length: int = 6) -> str:
    """Extract ASCII strings from a file.

    Args:
        filepath: Path to the file
        min_length: Minimum string length (default: 6)
    """
    from src.modules.file_analyzer import FileAnalyzer

    fa = FileAnalyzer(virustotal_api_key="")
    strings = await fa.get_strings(filepath, min_len=min_length)
    return _extract_json({"strings_found": len(strings), "strings": strings[:200]})


# ── Steganography ────────────────────────────────────────────────────────


@mcp.tool()
async def skyfall_steganography_lsb(filepath: str) -> str:
    """Analyze LSB (Least Significant Bit) steganography in an image."""
    from src.modules.steganography import SteganographyAnalyzer

    sa = SteganographyAnalyzer()
    return await sa.analyze_lsb(filepath)


@mcp.tool()
async def skyfall_steganography_spectral(filepath: str) -> str:
    """Perform spectral analysis of an image for anomalies."""
    from src.modules.steganography import SteganographyAnalyzer

    sa = SteganographyAnalyzer()
    return await sa.analyze_spectral(filepath)


@mcp.tool()
async def skyfall_steganography_eoi(filepath: str) -> str:
    """Detect hidden data after EOI (End of Image) markers."""
    from src.modules.steganography import SteganographyAnalyzer

    sa = SteganographyAnalyzer()
    return await sa.analyze_eoi(filepath)


@mcp.tool()
async def skyfall_steganography_tail(filepath: str) -> str:
    """Detect hidden tail data after known image format boundaries."""
    from src.modules.steganography import SteganographyAnalyzer

    sa = SteganographyAnalyzer()
    return await sa.detect_tail_data(filepath)


@mcp.tool()
async def skyfall_steganography_full(filepath: str) -> str:
    """Run full steganography analysis (LSB, spectral, EOI, tail, ELA)."""
    from src.modules.steganography import SteganographyAnalyzer

    sa = SteganographyAnalyzer()
    result = await sa.run_full_analysis(filepath)
    return _extract_json(result)


@mcp.tool()
async def skyfall_steganography_ela(filepath: str, quality: int = 90) -> str:
    """Run Error Level Analysis on an image, save ELA heatmap next to the file.

    Args:
        filepath: Path to the image
        quality: JPEG recompress quality for ELA (default: 90)
    """
    from src.modules.steganography import SteganographyAnalyzer

    sa = SteganographyAnalyzer()
    return await sa.analyze_ela(filepath, quality=quality)


# ── Dorking ────────────────────────────────────────────────────────────────


@mcp.tool()
async def skyfall_dorking_search(dork: str, use_searxng: bool = False) -> str:
    """Search using a Google dork query via DuckDuckGo or SearXNG.

    Args:
        dork: The dork query (e.g. 'site:example.com filetype:pdf')
        use_searxng: Use local SearXNG instance instead of DuckDuckGo
    """
    from src.modules.dorks_search_engine import DorksSearchEngine

    de = DorksSearchEngine()
    return await de.search_dork(dork, use_searxng=use_searxng)


# ── Graph (requires GUI) ──────────────────────────────────────────────────────


@mcp.tool()
async def skyfall_graph_add_node(
    title: str,
    content: str = "",
    entity_type: str = "Custom",
) -> str:
    """Add a node to the SkyFall investigation graph.

    Args:
        title: Node title/name
        content: Optional description or data
        entity_type: Type: Person, Domain, IP, Email, Phone, MAC, Username,
                     Crypto, Organization, Passport, Photo, Geolocation, Custom
    """
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "add_node", title, content, entity_type)


@mcp.tool()
async def skyfall_graph_add_edge(
    source_id: str,
    target_id: str,
    relationship: str = "associated_with",
    label: str = "",
    source_port: str = "right",
    target_port: str = "left",
) -> str:
    """Add an edge (connection) between two graph nodes.

    Args:
        source_id: ID of the source node
        target_id: ID of the target node
        relationship: Type: owns, registered_at, resolved_to, member_of,
                      located_at, communicates_with, associated_with,
                      works_at, created_by, attends, hosted_by, linked_to
        label: Optional edge label text
        source_port: Port on source node: left, right, top, bottom (default: right)
        target_port: Port on target node: left, right, top, bottom (default: left)
    """
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(
        bridge,
        "add_edge",
        source_id,
        target_id,
        relationship,
        label,
        source_port,
        target_port,
    )


@mcp.tool()
async def skyfall_graph_get() -> str:
    """Get the current state of the investigation graph as JSON."""
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "get_graph")


@mcp.tool()
async def skyfall_graph_summary() -> str:
    """Get a human-readable summary of the investigation graph.
    Shows total nodes/edges, entity type breakdown, and lists all nodes and connections.
    Use this to understand the current investigation state before making changes."""
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "graph_summary")


@mcp.tool()
async def skyfall_graph_get_node(node_id: str) -> str:
    """Get detailed info about a specific graph node including its connections.

    Args:
        node_id: The node ID to look up
    """
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "get_node", node_id)


@mcp.tool()
async def skyfall_graph_move_node(node_id: str, x: float, y: float) -> str:
    """Move a graph node to a specific position on the canvas.

    Use this to organize and lay out the graph visually. The (x, y) coordinates
    are scene coordinates — get current positions via skyfall_graph_get_node
    or skyfall_graph_get.

    Args:
        node_id: The node ID to move
        x: New X coordinate in scene space
        y: New Y coordinate in scene space
    """
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "move_node", node_id, x, y)


@mcp.tool()
async def skyfall_graph_update_node(
    node_id: str,
    title: str | None = None,
    content: str | None = None,
    entity_type: str | None = None,
) -> str:
    """Update properties of an existing graph node.

    Args:
        node_id: The node ID to update
        title: New title (optional)
        content: New content/description (optional)
        entity_type: New entity type (optional): Person, Domain, IP, Email, Phone,
                     MAC, Username, Crypto, Organization, Passport, Photo,
                     Geolocation, Custom
    """
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(
        bridge, "update_node", node_id, title, content, entity_type
    )


@mcp.tool()
async def skyfall_graph_remove_node(node_id: str) -> str:
    """Remove a node and all its connected edges from the graph.

    Args:
        node_id: The node ID to remove
    """
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "remove_node", node_id)


@mcp.tool()
async def skyfall_graph_remove_edge(source_id: str, target_id: str) -> str:
    """Remove an edge between two nodes.

    Args:
        source_id: ID of the source node
        target_id: ID of the target node
    """
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "remove_edge", source_id, target_id)


@mcp.tool()
async def skyfall_graph_clear() -> str:
    """Clear all nodes and edges from the graph."""
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "clear_graph")


@mcp.tool()
async def skyfall_graph_import_file(filepath: str) -> str:
    """Import a graph file into the main investigation graph (replaces it).

    Accepts SkyFall JSON, TG Analyzer GraphML/GEXF/node-link JSON/CSV.
    TG graphs get entity mapping + auto-layout.

    Args:
        filepath: Path to the graph file
    """
    from src.modules.graph_io import load_graph_file

    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    try:
        data = await anyio.to_thread.run_sync(lambda: load_graph_file(filepath))
    except Exception as e:
        return _extract_json({"error": str(e)})
    return await _graph_bridge_send(bridge, "import_dict", data)


@mcp.tool()
async def skyfall_graph_export_image(filepath: str) -> str:
    """Export the current investigation graph as PNG or SVG (by suffix).

    Args:
        filepath: Destination path ending with .png or .svg
    """
    if not _graph_bridge_available():
        return _graph_not_available_bridge()
    bridge = _graph_bridge()
    if bridge is None:
        return _graph_not_available_bridge()
    return await _graph_bridge_send(bridge, "export_image", filepath)


# ── Case Management ──────────────────────────────────────────────────────────


@mcp.tool()
def skyfall_cases_list() -> str:
    """List all investigation cases in ~/.skyfall/data/."""
    cases_dir = Path.home() / ".skyfall" / "data"
    if not cases_dir.exists():
        return _extract_json([])
    cases = []
    for entry in cases_dir.iterdir():
        if entry.is_dir():
            cases.append(
                {
                    "name": entry.name,
                    "path": str(entry),
                    "categories": [cat.name for cat in entry.iterdir() if cat.is_dir()],
                }
            )
    return _extract_json(cases)


@mcp.tool()
def skyfall_case_get(name: str) -> str:
    """Get data from a specific investigation case.

    Args:
        name: Case folder name
    """
    case_dir = Path.home() / ".skyfall" / "data" / name
    if not case_dir.exists():
        return _extract_json({"error": f"Case '{name}' not found"})
    data = {"name": name, "path": str(case_dir), "categories": {}}
    for cat_dir in case_dir.iterdir():
        if cat_dir.is_dir():
            files = []
            for f in sorted(
                cat_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True
            ):
                files.append(
                    {
                        "name": f.name,
                        "size": f.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            f.stat().st_mtime
                        ).isoformat(),
                    }
                )
            data["categories"][cat_dir.name] = files
    return _extract_json(data)


# ── Report Generation ────────────────────────────────────────────────────────────


@mcp.tool()
def skyfall_generate_report(data: str, language: str = "Russian") -> str:
    """Generate an AI OSINT report from collected data.

    This is a plain text tool — returns markdown report, not JSON.

    Args:
        data: JSON string containing collected OSINT data
        language: Report language (e.g. Russian, English, German)
    """
    from src.ollama_mcp_server import _build_prompt

    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        parsed = {"raw": data}
    prompt = _build_prompt(parsed, language)
    return _ollama._generate(prompt)


# ── Resources ──────────────────────────────────────────────────────────────────────


@mcp.resource("skyfall://modules")
def resource_modules() -> str:
    """List all available MCP tools/modules in SkyFall."""
    tools = [
        "Domain Analysis: skyfall_domain_* (16 tools: ip, dns, whois, ssl, headers, "
        "web_stack, nmap, waf, malware, threat_intel, js_secrets, subdomains, "
        "robots, security_txt, social_tags) + skyfall_ip_domains",
        "Username Search: skyfall_username_search, skyfall_maigret_search",
        "Social: skyfall_social_search (Bluesky/Mastodon), skyfall_instagram_profile",
        "Email Search: skyfall_email_* (IntelX, HIBP, combined, headers/EML)",
        "Leaks: skyfall_leak_check, skyfall_infostealer_search (Hudson Rock)",
        "Geo: skyfall_geo_sun_shadow, skyfall_shadow_geolocate, skyfall_firms_fires, "
        "skyfall_gdacs_disasters",
        "Archive: skyfall_archive_url, skyfall_archive_snapshots, skyfall_archive_save",
        "Phone OSINT: skyfall_phone_* (parse, reverse lookup, leaks, 7tel.ru)",
        "GitHub OSINT: skyfall_github_* (user, repos, commits, secrets, dork)",
        "Blockchain: skyfall_blockchain_search (10 chains)",
        "MAC Geolocation: skyfall_mac_locate (5 providers)",
        "File Analysis: skyfall_file_* (info, metadata, VT, tail, strings)",
        "Steganography: skyfall_steganography_* (LSB, spectral, EOI, tail, ELA, full)",
        "Dorking: skyfall_dorking_search (DDG/SearXNG)",
        "Graph: skyfall_graph_* (nodes/edges, TG import, PNG/SVG export, GUI)",
        "Cases: skyfall_cases_*, skyfall_case_get",
        "Report: skyfall_generate_report (via Ollama)",
        "Ollama: skyfall_ollama_* (list, set model, set URL)",
    ]
    return "\n".join(tools)


@mcp.resource("skyfall://settings")
def resource_settings() -> str:
    """Show configured API keys (masked) and SkyFall settings."""
    safe = {}
    for key, val in _settings.items():
        if "api" in key.lower() or "token" in key.lower() or "key" in key.lower():
            safe[key] = (
                val[:8] + "..."
                if val and len(val) > 8
                else ("set" if val else "not set")
            )
        else:
            safe[key] = val
    return _extract_json(safe)


# ── Main ──────────────────────────────────────────────────────────────────────────


async def _make_s4f():
    from src.modules.search4faces import Search4Faces

    return Search4Faces()


@mcp.tool()
async def skyfall_s4f_search(image_path: str, max_results: int = 500) -> str:
    """Search for face matches on search4faces.com using a local image file."""
    s4f = await _make_s4f()
    profiles = await s4f.search_face(image_path, max_results)
    return _extract_json(profiles)


def main():
    parser = argparse.ArgumentParser(description="SkyFall MCP Server")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=9877, help="Port (default: 9877)")
    parser.add_argument(
        "--ollama-url", default="http://127.0.0.1:11434", help="Ollama base URL"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    if _AUTH_ENABLED:
        mcp.settings.auth = _auth_settings(args.host, args.port)

    _ollama.set_base_url(args.ollama_url)

    logger.info(f"Starting SkyFall MCP Server ({args.transport})")
    logger.info(f"Ollama URL: {args.ollama_url}")
    logger.info(f"Settings loaded from: {CONFIG_FILE}")
    logger.info(
        "MCP auth: enabled (bearer token required)"
        if _AUTH_ENABLED
        else "MCP auth: disabled"
    )

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
