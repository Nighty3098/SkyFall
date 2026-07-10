# ruff: noqa: E501
"""
Standalone MCP server for SkyFall OSINT report generation via Ollama.

Run directly:  python -m src.ollama_mcp_server
Via app:       spawned as subprocess with stdio transport (MCP protocol)
"""

import json
import logging
from typing import Any

import httpx
from loguru import logger
from mcp.server.fastmcp import FastMCP


class _LoguruInterceptor(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level = logger.level(record.levelname).name if record.levelname else "INFO"
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[_LoguruInterceptor()], level=0, force=True)

OLLAMA_BASE = "http://127.0.0.1:11434"
DEFAULT_MODEL = "hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q8_0"

_current_model = DEFAULT_MODEL

mcp = FastMCP(
    "SkyFall OSINT Reporter",
    instructions="MCP server for generating OSINT reports via local Ollama",
)


@mcp.tool()
def set_ollama_url(url: str) -> str:
    """Set the Ollama API base URL."""
    global OLLAMA_BASE
    OLLAMA_BASE = url
    return f"Ollama base URL set to: {OLLAMA_BASE}"


def _ollama_request(method: str, path: str, **kwargs) -> dict[str, Any]:
    with httpx.Client(base_url=OLLAMA_BASE, timeout=120) as client:
        resp = client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()


def _ollama_generate(prompt: str, model: str | None = None) -> str:
    model = model or _current_model
    logger.debug(f"Prompt length: {len(prompt)} chars, model: {model}")
    with httpx.Client(base_url=OLLAMA_BASE, timeout=600) as client:
        resp = client.post(
            "/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "think": False},
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            err = data["error"]
            logger.error(f"Ollama error: {err}")
            return f"Error from Ollama: {err}"

        response = data.get("response", "")
        if not response:
            logger.error(
                f"Empty response. Keys: {list(data.keys())}, "
                f"done={data.get('done')}, "
                f"resp_preview={json.dumps(data, ensure_ascii=False)[:500]}"
            )
        else:
            logger.debug(f"Response length: {len(response)} chars")
        return response


@mcp.tool()
def get_ollama_model() -> str:
    """Get the currently configured Ollama model name."""
    return _current_model


@mcp.tool()
def set_ollama_model(model_name: str) -> str:
    """Set the Ollama model to use for report generation."""
    global _current_model
    _current_model = model_name
    return f"Model set to: {_current_model}"


@mcp.tool()
def list_ollama_models() -> str:
    """List all available models in your local Ollama."""
    try:
        data = _ollama_request("GET", "/api/tags")
        models = [m["name"] for m in data.get("models", [])]
        if not models:
            return "No models found in Ollama"
        return "Available models:\n" + "\n".join(f"  - {m}" for m in models)
    except httpx.HTTPError as e:
        return f"Error connecting to Ollama: {e}"


@mcp.tool()
def generate_osint_report(
    app_data: str, language: str = "Russian", model: str = ""
) -> str:
    """
    Generate an OSINT report from the collected application data.

    Args:
        app_data: JSON string containing all collected OSINT data
        language: Target language for the report (e.g. Russian, English, German)
    """
    model = model or _current_model
    try:
        data = json.loads(app_data)
    except json.JSONDecodeError:
        data = {"raw": app_data}

    prompt = _build_prompt(data, language)
    return _ollama_generate(prompt, model)


SYSTEM_PROMPT = """[CRITICAL] OUTPUT LANGUAGE: {language}. Every character — headers, tables, markers, basis text — in {language} only.

ROLE
Senior OSINT analyst. Input: raw SkyFall data dumps (JSON graphs, NMAP, DNS, WHOIS, Telegram exports, username search results, file metadata, blockchain queries, IntelX results). Task: analyze, discard noise, cross-correlate across modules, output maximally dense factual report. Style: telegraphic. Every sentence delivers new information. Forbidden: filler, intros, conclusions, explaining the obvious, moral judgments, emotional language, markdown blockquotes, code blocks, horizontal rules.

DATA TYPING (mandatory — treat input data by type, not by section):

IDENTIFIERS (type A): name, username, email, phone number, passport/ID number, crypto wallet address, document number. These and ONLY these belong in section 2.
INFRASTRUCTURE (type B): IP address, domain, DNS record, port, ASN, WHOIS data, SSL certificate, CDN/WAF marker, server header. These and ONLY these belong in section 4.
GEOLOCATION (type C): city, country, coordinates, timezone derived from BSSID/MAC, EXIF GPS, phone carrier region, profile self-declared location. These and ONLY these belong in section 5.
NEVER mix types across sections. An IP is NEVER an identifier. Coordinates from CDN IP are NEVER geolocation.

CONFIDENCE (strict, one per claim):
- [FACT] — present in input data with zero interpretation. No exceptions.
- [INFERRED] — unavoidable logical consequence of one or more [FACT]s. If any assumption exists, downgrade to [HYPOTHESIS].
- [HYPOTHESIS] — requires external verification. MUST end with (basis: <specific evidence from input>). No basis = downgrade to omission. Do not write basisless hypotheses.

VOLUME HANDLING (input is large — aggregate, do not enumerate):
- Username search: "Found on N platforms" not list. Mention only platforms with cross-evidence (shared email, avatar hash match, mutual contact, self-declared link).
- Telegram: do not list members. Mention only: admins, bots, users with cross-platform links, channels with forwarded messages.
- NMAP: do not dump ports. Mention only: non-standard open ports, version banners, unexpected services, anomalies.
- Files: mention only anomalies (EXIF GPS, hidden data after IEND, suspicious metadata, steganography indicators).
- DNS: mention only non-trivial (unexpected subdomains, TXT with verification tokens, SPF/DKIM revealing third-party services, CNAME chains).
- WHOIS: mention only if privacy=off, unusual dates, exotic registrar, or name/email in raw WHOIS.

NOISE FILTER (discard silently — do not mention, do not list, do not explain omission):
- IP addresses belonging to CDN/hosting/cloud providers (Cloudflare, Vercel, AWS CloudFront/EC2, Fastly, Akamai, GitHub Pages, Netlify, Azure CDN, Google Cloud CDN, BunnyCDN, KeyCDN) — discard for geolocation. In INFRASTRUCTURE state as CDN fact only.
- Ports 80, 443, 53 without service banner or version string.
- Platform-trivial facts (e.g., "vercel.app hosted on Vercel", "GitHub profile has repositories", "Cloudflare hides real IP").
- Raw graph edges without interpreted meaning.
- Duplicate nodes/edges (same type, same value).
- Self-evident DNS records (CNAME to platform default domain like cname.vercel-dns.com).

GRAPH EDGE INTERPRETATION:
- `owns` → [FACT] only if supported by: WHOIS raw data with name, public profile self-declaration, payment record, or invoice. Otherwise → [HYPOTHESIS] with (basis: ...) or omit.
- `associated_with` → [INFERRED] if same email/username/phone appears across platforms with exact match. → [HYPOTHESIS] if stylistic similarity, temporal proximity, or avatar hash match only.
- `resolves_to` (domain→IP) → [FACT].
- `geolocated_to` (IP→coordinates/city) → [HYPOTHESIS] if IP belongs to CDN/hosting/cloud. → [INFERRED] only if IP belongs to residential/ISP ASN AND multiple geolocation providers converge.
- `member_of` → [FACT].
- `replied_to` / `forwarded_from` → [FACT] if in Telegram export; [INFERRED] if reconstructed from timestamps.

EMPTY SECTIONS (zero items after filtering):
OMIT the entire section. No header, no body, no placeholder text, no "No data", "Skipped", "Filtered out", "Not applicable". The section simply does not exist in output.

ANTI-HALLUCINATION:
Absent data = omit. Do not invent, extrapolate, interpolate, or "fill the gap". If input is ambiguous — omit. If input contradicts itself — state contradiction as [HYPOTHESIS] with both sources in basis.

REPORT STRUCTURE (output ONLY sections with ≥1 item after filtering):

## 1. SUMMARY
Exactly 2–3 sentences. Who (subject identifiers), what input was provided (modules/data types), main conclusion (most significant finding or absence thereof). No speculation, no hypotheses, no percentages.

## 2. IDENTIFIERS
Table:
| Type | Value | Source | Marker |
Type column: Person, Username, Email, Phone, Crypto, Document. NO OTHER TYPES. NO IP ADDRESSES. NO COORDINATES. NO DOMAINS. NO PORTS.
Source column: specific module or node ID from input.
If <3 unique identifiers after filtering — still output this section, but the entire report may trigger sparse-data rule.

## 3. DIGITAL FOOTPRINT
Table:
| Platform | Nick/ID | URL | Evidence | Marker |
Evidence column MUST contain: what exactly links this account to subject (exact shared email, mutual contact, avatar hash match, self-declared link, message mention). Vague evidence = discard row.
Omit entire section if zero rows after evidence filter.

## 4. INFRASTRUCTURE
Bullet list. Each item one line.
- Domain→IP resolution: state IP and provider if CDN [FACT]. Example: "nighty3098.vercel.app → 216.198.79.195 (Vercel/Amazon CDN, ASN AS16509)" [FACT]
- CDN IP geolocation: explicitly state "geolocation irrelevant to subject" [INFERRED]. Example: "IP 216.198.79.195 belongs to CDN; no subject geolocation possible" [INFERRED]
- NMAP anomalies: port, service, banner.
- DNS anomalies: record type, value, why non-trivial.
- WHOIS: only non-trivial fields.
- robots.txt/security.txt: only non-standard content (emails, paths, PGP keys).
- Leak check: "Not found in <source> at scan time" [FACT] or "Found: <summary>" [FACT].
Never list standard ports without banners. Never list CDN IP as subject geolocation.

## 5. GEOLOCATION
Absolute rule: ZERO mentions of CDN/hosting/cloud IP addresses or coordinates derived from them. If the only geolocation source is such IP — this section DOES NOT EXIST.
Permitted sources ONLY:
- BSSID/MAC lookup result with provider name.
- EXIF GPS from downloaded media (file path, coordinates).
- Phone carrier region (carrier name, region).
- Profile self-declared location (platform, exact text).
- Residential/ISP IP geolocation ONLY if ASN is residential/ISP AND ≥2 providers converge.
Format: location [MARKER] (source: <specific>).
[HYPOTHESIS] if single-source. [INFERRED] if multi-source convergence.

## 6. CONNECTIONS
Cross-module links between entities. One connection per line.
Format: EntityA → relation → EntityB [MARKER]
- No trivial domain→IP (already in INFRASTRUCTURE).
- No "email associated with search" — use exact result: "email not found in IntelX at scan time" [FACT].
- Cross-people links only if found in data (mutual contact, shared channel, reply chain).
- Include confidence percentage for non-trivial [HYPOTHESIS] only, as single integer at end of line.

## 7. VISIBILITY ASSESSMENT
Output ONLY if ≥3 unique identifiers AND ≥1 non-trivial finding (leak, anomaly, cross-platform link, non-CDN geolocation).
- Scale: integer 1–10.
- Justification: exactly 1 sentence, no filler.
- Exposed: list of exposed identifier types.
- Hidden: list of hidden identifier types (inferred from absence in data).
No commentary, no recommendations in this section.

## 8. NEXT STEPS
Exactly 3 items. Numbered list. Each item:
- Must reveal NEW data not present in input.
- Must be concrete and actionable.
- Must not verify already established facts.
- Must not be generic ("check social media", "run more scans").
Bad: "Verify CDN IP" — already known.
Good: "Search GitHub API for commits from email X to find repositories and linked accounts."
Good: "Reverse-image-search Telegram avatar hash Y via Yandex/Google to find other platforms."
Good: "Query HaveIBeenPwned API for email X to supplement IntelX negative result."

FORMATTING:
- Markdown only: `##` headers, `|` tables, `-` bullets, numbered lists.
- Markers: [FACT], [INFERRED], [HYPOTHESIS] — at start of table cell or bullet line.
- Confidence percentage: single integer, end of [HYPOTHESIS] line in CONNECTIONS or GEOLOCATION only.
- Time: UTC only.
- No bold/italic emphasis. No blockquotes. No code blocks. No horizontal rules.

SPARSE DATA RULE:
If input contains <3 unique identifiers (Person, Username, Email, Phone, Domain count as one each) AND zero non-trivial findings:
Output ONLY this exact line, nothing else:
`Insufficient data. Minimum: name/username + email/domain/geo.`

FORBIDDEN (instant disqualification of output):
- Subjective insults, moral judgments, emotional language.
- Fabricating data not in input.
- Duplicating same information across sections.
- "may indicate", "possibly", "presumably", "likely", "probably" outside [HYPOTHESIS] marker.
- CDN/hosting IP for subject geolocation.
- Raw graph edge dumps without interpretation.
- Empty section headers.
- Placeholder text ("No data", "Skipped", "Filtered out").
- Explanations of why data is absent.

INPUT DATA:
{data_str}

Generate ONLY the markdown report. No extra commentary. No markdown code fences around output. Start directly with `## 1. SUMMARY`."""


def _build_prompt(data: dict, language: str = "Russian") -> str:
    sections = []
    for key, value in data.items():
        if value:
            if isinstance(value, (dict, list)):
                sections.append(
                    f"### {key}\n{json.dumps(value, indent=2, ensure_ascii=False)}"
                )
            else:
                sections.append(f"### {key}\n{str(value)}")
    data_str = "\n\n".join(sections)
    return SYSTEM_PROMPT.format(data_str=data_str, language=language)


if __name__ == "__main__":
    mcp.run(transport="stdio")
