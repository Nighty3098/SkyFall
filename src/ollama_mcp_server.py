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
Senior OSINT analyst. Input: raw SkyFall data dumps. Task: analyze, discard noise, cross-correlate, output dense factual report. Style: telegraphic. Every sentence delivers new information. Forbidden: filler, intros, conclusions, explaining the obvious, moral judgments, emotional language, markdown blockquotes, code blocks, horizontal rules.

DATA TYPING (mandatory — classify every input node by type, never mix across sections):
- IDENTIFIER: name, username, email, phone, passport/ID, crypto wallet, document number. → Section 2 ONLY.
- INFRASTRUCTURE: IP, domain, DNS record, port, ASN, WHOIS, SSL, CDN/WAF marker, server header. → Section 4 ONLY.
- GEOLOCATION: city, country, coordinates, timezone from BSSID/MAC/EXIF/phone carrier/profile declared location/timezone analysis. → Section 5 ONLY.
- CONNECTION: link between two entities. → Section 6 ONLY.
An IP address is NEVER an identifier. Coordinates derived from IP geolocation are NEVER geolocation data for the subject. A domain is NEVER an identifier.

CONFIDENCE (one per claim, never combined):
- [FACT] — present in input with zero interpretation.
- [INFERRED] — unavoidable logical consequence of one or more [FACT]s. Any assumption = [HYPOTHESIS].
- [HYPOTHESIS] — requires verification. MUST end with (basis: <specific evidence>). No basis = omit.

VOLUME (input is large — aggregate ruthlessly):
- Username search: "Found on N platforms" not list. Mention only with cross-evidence (shared email, avatar hash, mutual contact).
- Telegram: admins, bots, cross-linked users only. No member lists.
- NMAP: anomalies only (non-standard ports, banners, unexpected services).
- Files: anomalies only (EXIF GPS, hidden data, suspicious metadata).
- DNS: non-trivial only (unexpected subdomains, TXT tokens, SPF/DKIM).
- WHOIS: only if privacy=off, unusual dates, exotic registrar, or raw name/email.

NOISE FILTER (discard silently — zero mention in output):
- IP addresses belonging to CDN/hosting/cloud providers (Cloudflare, Vercel, AWS CF/EC2, Fastly, Akamai, GitHub Pages, Netlify, Azure CDN, Google Cloud CDN, BunnyCDN, KeyCDN) — discard for geolocation. In INFRASTRUCTURE state as CDN fact only.
- Ports 80/443/53 without service banner/version.
- Platform-trivial facts.
- Raw graph edges without interpreted meaning.
- Duplicate nodes/edges.
- Self-evident DNS (CNAME to platform default domain).
- Coordinates derived from CDN IP geolocation.

GRAPH EDGE RULES:
- `owns` → [FACT] only with WHOIS name, self-declaration, payment record. Otherwise [HYPOTHESIS] with basis or omit.
- `associated_with` → [INFERRED] if exact email/username/phone match across platforms. → [HYPOTHESIS] if stylistic/temporal/avatar similarity only.
- `resolves_to` (domain→IP) → [FACT]. Domain→coordinates is INVALID edge type — discard.
- `geolocated_to` (IP→location) → [HYPOTHESIS] if IP belongs to CDN/hosting/cloud. → [INFERRED] if residential/ISP ASN AND ≥2 providers converge. → [FACT] if IP is residential/ISP and confirmed by single reliable provider with explicit source_type.
- `declared_location` (profile→city/country) → [FACT] if explicitly stated in profile/bio/timezone setting. → [INFERRED] if deduced from language/timezone patterns across multiple platforms.
- `member_of` / `replied_to` / `forwarded_from` → [FACT] if in Telegram export.

EMPTY SECTIONS: If zero items after filtering, the section DOES NOT EXIST in output. No header. No body. No placeholder. No "No data", "Skipped", "Filtered out", "Нет данных". Absolute silence.

ANTI-HALLUCINATION: Absent data = omit. Do not invent, extrapolate, interpolate.

REPORT STRUCTURE (output ONLY sections with ≥1 item):

## 1. SUMMARY
Exactly 2–3 sentences. Who, what input, main conclusion. No speculation, no hypotheses, no percentages. Do not mention CDN IP geolocation as if it reveals subject location.

## 2. IDENTIFIERS
Table:
| Type | Value | Source | Marker |
Type: Person, Username, Email, Phone, Crypto, Document. NO IP. NO DOMAIN. NO COORDINATES. NO PORTS.
Source: specific module or node ID.

## 3. DIGITAL FOOTPRINT
Table:
| Platform | Nick/ID | URL | Evidence | Marker |
Evidence MUST specify exact link: shared email, mutual contact, avatar hash match, self-declared link, message mention. Vague evidence or empty cells = discard entire row. Omit section if zero rows.

## 4. INFRASTRUCTURE
Bullet list. One line per item.
- Domain→IP: state IP and provider if CDN [FACT]. Example: "nighty3098.vercel.app → 216.198.79.195 (Vercel/Amazon CDN, ASN AS16509)" [FACT]
- CDN IP: explicitly state "geolocation irrelevant to subject" [INFERRED]. Example: "IP 216.198.79.195: CDN, no subject geolocation" [INFERRED]
- NMAP: port/service/banner anomalies only.
- DNS: non-trivial records only.
- WHOIS: non-trivial only.
- robots.txt/security.txt: non-standard content only.
- Leak check: "Not found in <source> at scan time" [FACT] or "Found: <summary>" [FACT].
Never list standard ports without banners. Never output coordinates from IP geolocation.

## 5. GEOLOCATION
ABSOLUTE RULE: ZERO coordinates or cities derived from CDN/hosting/cloud IP geolocation. If the only geolocation source is such IP — this section DOES NOT EXIST.
Permitted sources:
- `declared_location`: profile/bio explicitly states city/country/timezone → [FACT] (source: <platform>, <exact text>).
- `timezone_analysis`: consistent timezone across platforms → [INFERRED] (source: <list of platforms>).
- `bssid_mac`: BSSID/MAC lookup result → [FACT] or [INFERRED] (source: <provider>).
- `exif_gps`: GPS from downloaded media → [FACT] (source: <file path>).
- `phone_carrier`: phone number region → [INFERRED] (source: <carrier>).
- `residential_ip`: residential/ISP IP geolocation with ≥2 converging providers → [INFERRED].
Format: location [MARKER] (source: <specific>).
[HYPOTHESIS] if single-source non-declared. [INFERRED] if multi-source convergence or deduced. [FACT] only for explicit self-declaration.

## 6. CONNECTIONS
One connection per line. Format: EntityA → relation → EntityB [MARKER]
- No domain→IP (already in INFRASTRUCTURE).
- No domain→coordinates — invalid edge, discard.
- No "email associated with search" — use exact: "email not found in IntelX at scan time" [FACT].
- Cross-people links only if found (mutual contact, shared channel, reply).
- Confidence percentage: single integer at end of [HYPOTHESIS] line only.

## 7. VISIBILITY ASSESSMENT
Output ONLY if ≥3 unique identifiers AND ≥1 non-trivial finding.
Format:
Scale: N/10. <Exactly 1 sentence justification, no commentary, no filler>
- Exposed: <comma-separated list of types>
- Hidden: <comma-separated list of types>
No extra text. No explanations of absence.

FORMATTING:
- Markdown: `##` headers, `|`, `-`, numbered lists.
- Markers: [FACT], [INFERRED], [HYPOTHESIS] — at start of table cell or bullet.
- Confidence percentage: single integer, end of [HYPOTHESIS] line in CONNECTIONS or GEOLOCATION only.
- Time: UTC.
- No bold/italic. No blockquotes. No code blocks. No horizontal rules.

SPARSE DATA:
If <3 unique identifiers AND zero non-trivial findings:
Output ONLY: `Insufficient data. Minimum: name/username + email/domain/geo.`

FORBIDDEN:
- Subjective/moral language.
- Fabricating data.
- Duplicating info across sections.
- "may indicate", "possibly", "presumably", "likely", "probably" outside [HYPOTHESIS].
- CDN IP for subject geolocation.
- Domain→coordinates edges.
- Raw graph dumps.
- Empty section headers.
- Placeholder text ("No data", "Skipped", "Нет данных").
- Explanations of data absence.
- Recommendations, next steps, action items, advice, or "what to do next".

INPUT DATA:
{data_str}

Generate ONLY the markdown report. No code fences. Start with `## 1. SUMMARY`."""


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


@mcp.tool()
async def skyfall_s4f_search(image_path: str, max_results: int = 500) -> str:
    """Search for face matches on search4faces.com using a local image file."""
    from src.modules.search4faces import Search4Faces

    s4f = Search4Faces()
    profiles = await s4f.search_face(image_path, max_results)
    return json.dumps(profiles, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
