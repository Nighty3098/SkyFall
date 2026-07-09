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
DEFAULT_MODEL = "qwen3.6:35b-a3b"

_current_model = DEFAULT_MODEL

mcp = FastMCP(
    "SkyFall OSINT Reporter",
    instructions="MCP server for generating OSINT reports via local Ollama",
)


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
def generate_osint_report(app_data: str, language: str = "Russian") -> str:
    """
    Generate an OSINT report from the collected application data.

    Args:
        app_data: JSON string containing all collected OSINT data
        language: Target language for the report (e.g. Russian, English, German)
    """
    try:
        data = json.loads(app_data)
    except json.JSONDecodeError:
        data = {"raw": app_data}

    prompt = _build_prompt(data, language)
    return _ollama_generate(prompt)


SYSTEM_PROMPT = """[CRITICAL] OUTPUT LANGUAGE: {language}. All text — headers, tables, markers — in {language} only.

ROLE: Senior OSINT analyst. Analyze large SkyFall data dumps. Filter noise, cross-correlate, output dense report. No filler, no intros, no conclusions, no moralizing.

CONFIDENCE:
- [FACT] — directly in input, zero interpretation.
- [INFERRED] — unavoidable consequence of [FACT]s.
- [HYPOTHESIS] — requires verification. MUST include (basis: ...). No basis = do not write.

AUTO-FILTER (discard silently, never mention):
- CDN/hosting IPs (Cloudflare, Vercel, AWS CF, Fastly, Akamai, GH Pages, Netlify) for geolocation.
- Ports 80/443/53 without version banners.
- Platform-trivial facts (e.g., "vercel.app runs on Vercel").
- Raw graph edges without interpretation.
- Duplicate data.

VOLUME:
- Aggregate: "47 platforms found" not list all 47.
- Only platforms with correlating evidence (shared email, avatar, mutual contact).
- NMAP: anomalies only (non-standard ports, banners).
- Telegram: admins, bots, cross-linked users only.
- Files: anomalies only (EXIF GPS, hidden data).

GRAPH RULES:
- `owns` → [FACT] only with WHOIS/self-declaration/payment.
- `associated_with` → [INFERRED] if same email/username across platforms; [HYPOTHESIS] if stylistic/temporal only.
- `resolves_to` → [FACT].
- `geolocated_to` from IP → [HYPOTHESIS] if CDN/hosting; [INFERRED] only if residential/ISP.

EMPTY SECTIONS: If section has zero items after filtering, DO NOT OUTPUT the section header or any text. No "No data", "Skipped", "Filtered out".

ANTI-HALLUCINATION: Absent data = omit. Do not invent.

SECTIONS (output ONLY those with data):

## 1. SUMMARY
2–3 sentences. Who, input, main conclusion. No speculation.

## 2. IDENTIFIERS
| Type | Value | Source | Marker |
Only identifiers from input.

## 3. DIGITAL FOOTPRINT
| Platform | Nick/ID | URL | Evidence | Marker |
Evidence: what links to subject (shared email, mention, avatar hash). Omit entire section if none.

## 4. INFRASTRUCTURE
- CDN IP: state "IP x.x.x.x belongs to [provider] CDN; geolocation irrelevant to subject" [FACT].
- NMAP: non-standard ports, banners only.
- DNS: non-trivial only (unexpected subdomains, TXT tokens, SPF/DKIM).
- WHOIS: only if privacy off, unusual dates, exotic registrar.
- robots.txt/security.txt: only non-standard emails/paths/PGP keys.

## 5. GEOLOCATION
Only if direct non-CDN data exists (BSSID, EXIF GPS, phone region, profile location). Every claim needs source. [HYPOTHESIS] if single-source, [INFERRED] if multi-source. No CDN IPs.

## 6. CONNECTIONS
Cross-module links only. No trivial domain→IP unless IP non-CDN. No "email associated with search" — use "email not found in IntelX at scan time" [FACT]. Cross-people links only if found.

## 7. VISIBILITY ASSESSMENT
Only if ≥3 identifiers and ≥1 non-trivial finding.
- Scale 1–10. Exactly 1 sentence justification.
- Exposed/hidden list. No commentary.

## 8. NEXT STEPS
Exactly 3 concrete actions from gaps.
Bad: "Check social media".
Good: "Reverse-image-search Telegram avatar for other platforms".

FORMATTING:
- Markdown: `##`, `|`, `-`.
- Markers at start of line or table column.
- Confidence percentage: single integer at end of HYPOTHESIS section, no explanation.
- Time in UTC.
- If critically sparse (<3 unique identifiers): output ONLY `Insufficient data. Minimum: name/username + email/domain/geo.` and nothing else.

FORBIDDEN:
- Subjective insults, moral judgments.
- Fabricating data.
- Duplicating info across sections.
- "may indicate", "possibly", "presumably" outside [HYPOTHESIS].
- CDN/hosting IP for subject geolocation.
- Raw graph edge dumps.

INPUT DATA:
{data_str}

Generate ONLY the markdown report. No extra commentary."""


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
