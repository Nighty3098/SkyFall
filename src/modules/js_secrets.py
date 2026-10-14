import asyncio
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger

from src.modules.github_search import SECRET_PATTERNS

JS_SECRET_REGEXES = [
    ("AWS Access Key", r"\bAKIA[0-9A-Z]{16}\b", "HIGH"),
    (
        "AWS Secret (assign)",
        r"(?i)aws_secret[^;'\"]{0,30}['\"][0-9A-Za-z/+]{40}['\"]",
        "HIGH",
    ),
    ("GitHub PAT", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "HIGH"),
    ("GitLab PAT", r"\bglpat-[A-Za-z0-9\-_]{20,}\b", "HIGH"),
    ("Stripe Live Secret", r"\bsk_live_[A-Za-z0-9]{16,}\b", "HIGH"),
    ("Stripe Test Secret", r"\bsk_test_[A-Za-z0-9]{16,}\b", "MEDIUM"),
    ("Stripe Publishable", r"\bpk_(live|test)_[A-Za-z0-9]{16,}\b", "LOW"),
    ("Google API Key", r"\bAIza[0-9A-Za-z\-_]{35}\b", "HIGH"),
    ("Slack Token", r"\bxox[apbors]-[A-Za-z0-9\-]{10,}\b", "HIGH"),
    (
        "Slack Webhook",
        r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/\S+",
        "HIGH",
    ),
    ("OpenAI Key", r"\bsk-[A-Za-z0-9]{20,}\b", "MEDIUM"),
    (
        "JWT",
        r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",
        "MEDIUM",
    ),
    (
        "Private Key Block",
        r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY",
        "HIGH",
    ),
    (
        "Generic Secret Assign",
        r"(?i)(api[_-]?key|secret|passwd|pwd|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        "LOW",
    ),
    ("Mongo URI", r"mongodb(?:\+srv)?://[^\s'\"`]+", "HIGH"),
    ("Postgres URI", r"postgres(?:ql)?://[^\s'\"`]+", "HIGH"),
    ("Redis URI", r"redis://[^\s'\"`]+", "HIGH"),
    ("MySQL URI", r"mysql://[^\s'\"`]+", "HIGH"),
    (
        "S3 Bucket URL",
        r"https?://[a-z0-9.\-]+\.s3[.-][a-z0-9\-]*\.amazonaws\.com\S*",
        "MEDIUM",
    ),
    ("Firebase URL", r"https://[a-z0-9\-]+\.firebaseio\.com\S*", "MEDIUM"),
    (
        "API Endpoint",
        r"(?:\"|')(?:https?://[^\"']*api[^\"']*|/[A-Za-z0-9_\-./]{2,}api[A-Za-z0-9_\-./?=&#%]{2,})(?:\"|')",
        "INFO",
    ),
    ("GraphQL Endpoint", r"(?:\"|')[^\"']*graphql[^\"']*(?:\"|')", "INFO"),
    ("WebSocket URL", r"wss?://[^\s'\"`]+", "INFO"),
]

ENDPOINT_PATTERNS = [
    ("abs_url", r"https?://[a-zA-Z0-9.\-:_/?#&=%+~@]+"),
    (
        "rel_api",
        r"(?:\"|')/(?:api|v\d|graphql|rest|oauth|auth|admin|internal)[A-Za-z0-9_\-./?=&#%]*",
    ),
]

_COMPILED_SECRETS = [(n, re.compile(p), s) for n, p, s in JS_SECRET_REGEXES]
_COMPILED_ENDPOINTS = [(n, re.compile(p)) for n, p in ENDPOINT_PATTERNS]

MAX_JS_FILES = 15
MAX_JS_BYTES = 2_000_000
REQUEST_TIMEOUT = 8

COMMON_JS_PATHS = [
    "/main.js",
    "/main.bundle.js",
    "/app.js",
    "/bundle.js",
    "/static/js/main.js",
    "/assets/js/main.js",
]


def _redact(value: str, keep: int = 8) -> str:
    value = value.strip().strip("\"'").strip()
    if len(value) <= keep + 4:
        return value[:keep] + "…"
    return value[:keep] + "…" + value[-4:]


def extract_script_urls(html, base_url):
    urls = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("script", src=True):
            abs_url = urljoin(base_url, tag["src"])
            if abs_url not in urls:
                urls.append(abs_url)
    except Exception as e:
        logger.debug(f"JS script extraction failed: {e}")
    if not urls:
        for path in COMMON_JS_PATHS:
            candidate = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            if candidate not in urls:
                urls.append(candidate)
    return urls


def scan_text(text, source=""):
    findings = []
    for name, rx, severity in _COMPILED_SECRETS:
        try:
            for m in rx.finditer(text):
                raw = m.group(0)
                if len(raw) > 500:
                    raw = raw[:500]
                findings.append(
                    {
                        "type": name,
                        "severity": severity,
                        "source": source,
                        "match": _redact(raw),
                        "length": len(m.group(0)),
                    }
                )
        except re.error:
            continue
    lowered = text.lower()
    keyword_hits = sorted({kw for kw in SECRET_PATTERNS if kw.lower() in lowered})
    endpoints = set()
    for _, rx in _COMPILED_ENDPOINTS:
        for m in rx.finditer(text):
            ep = m.group(0).strip("\"' ").strip()
            if 3 < len(ep) < 300:
                endpoints.add(ep)
    return {
        "source": source,
        "findings": findings,
        "keyword_hits": keyword_hits[:50],
        "endpoints": sorted(endpoints)[:100],
    }


async def scan_domain_js(domain, max_files=MAX_JS_FILES, timeout=REQUEST_TIMEOUT):
    logger.debug("Trying to scan JS secrets")
    ua = UserAgent()
    headers = {"User-Agent": ua.random}
    base_url = f"https://{domain}"

    def _fetch(url):
        try:
            resp = requests.get(
                url, headers=headers, timeout=timeout, allow_redirects=True
            )
            if resp.status_code == 200 and resp.text:
                return resp.text[:MAX_JS_BYTES]
        except Exception as e:
            logger.debug(f"JS fetch failed {url}: {e}")
        return None

    homepage = await asyncio.to_thread(_fetch, base_url)
    if not homepage:
        base_url = f"http://{domain}"
        homepage = await asyncio.to_thread(_fetch, base_url)
    if not homepage:
        return {"domain": domain, "error": "could not fetch homepage"}
    script_urls = extract_script_urls(homepage, base_url)[:max_files]
    scanned = []
    results = []
    inline = scan_text(homepage, source="(inline html)")
    if inline["findings"] or inline["keyword_hits"]:
        results.append(inline)
    for js_url in script_urls:
        body = await asyncio.to_thread(_fetch, js_url)
        if body:
            scanned.append(js_url)
            results.append(scan_text(body, source=js_url))
    return {
        "domain": domain,
        "scanned_files": scanned,
        "results": results,
        "findings": [f for r in results for f in r["findings"]],
    }
