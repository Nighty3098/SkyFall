"""Compact, block-oriented rendering for SkyFall's debug panels.

Analyzers return plain, JSON-serialisable data (``dict`` / ``list`` / scalars)
so the same value can feed the UI, the MCP server, the report generator and the
graph transformers without re-parsing display strings.  ``render`` turns that
data into the compact block text shown in the panels; the primitives below are
used by modules that still assemble text incrementally and emit the same style.

Style guide::

    Subdomains: example.com
      Total unique: 12
      crt.sh
        • a.example.com
        • b.example.com
      · No subdomains found
      ! Error: timed out
"""

from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any

from src.ui.theme import current_theme, get_palette

INDENT = "  "
BULLET = "\u2022"  # •
INFO = "\u00b7"  # ·
WARN = "!"
_MISSING = ("", None, [], {}, ())
_LIST_CAP = 20


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


def title(text: Any) -> str:
    return _scalar(text)


def section(name: Any) -> str:
    return _scalar(name)


def end_of(action: Any) -> str:
    return ""


def divider(*_args: Any, **_kwargs: Any) -> str:
    return ""


def kv(key: Any, val: Any) -> str:
    return f"{INDENT}{_scalar(key)}: {_scalar(val)}"


def bullet(text: Any) -> str:
    return f"{INDENT}{BULLET} {_scalar(text)}"


def info(msg: Any) -> str:
    return f"{INDENT}{INFO} {_scalar(msg)}"


def error(msg: Any) -> str:
    return f"{INDENT}{WARN} {_scalar(msg)}"


def line(text: Any) -> str:
    return f"{INDENT}{INDENT}{_scalar(text)}"


def _join_scalars(values: list) -> str:
    rendered = [_scalar(v) for v in values]
    if len(rendered) > _LIST_CAP:
        extra = len(rendered) - _LIST_CAP
        rendered = rendered[:_LIST_CAP] + [f"\u2026 +{extra} more"]
    return ", ".join(rendered)


def _render_value(value: Any, depth: int) -> list[str]:
    pad = INDENT * depth
    lines: list[str] = []

    if isinstance(value, dict):
        if value.get("error"):
            lines.append(f"{pad}{WARN} {_scalar(value['error'])}")
        for key, val in value.items():
            if key == "error" or val in _MISSING:
                continue
            if key == "content" and isinstance(val, str):
                lines.append(f"{pad}{_scalar(key)}:")
                lines.extend(f"{pad}{INDENT}{ln}" for ln in val.splitlines())
            elif isinstance(val, dict):
                lines.append(f"{pad}{_scalar(key)}")
                lines.extend(_render_value(val, depth + 1))
            elif isinstance(val, (list, tuple)):
                if all(not isinstance(x, (dict, list, tuple)) for x in val):
                    lines.append(f"{pad}{_scalar(key)}: {_join_scalars(list(val))}")
                else:
                    lines.append(f"{pad}{_scalar(key)}")
                    lines.extend(_render_value(list(val), depth + 1))
            else:
                lines.append(f"{pad}{_scalar(key)}: {_scalar(val)}")
    elif isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, (dict, list, tuple)):
                lines.extend(_render_value(item, depth))
            else:
                lines.append(f"{pad}{BULLET} {_scalar(item)}")
    elif value not in _MISSING:
        lines.append(f"{pad}{_scalar(value)}")

    return lines


def render(data: Any, title: str | None = None) -> str:
    """Render structured data (or a pre-built string) into compact block text."""
    if isinstance(data, str):
        body = data
    else:
        body = "\n".join(_render_value(data, 1))
    if title:
        return f"{_scalar(title)}\n{body}" if body else _scalar(title)
    return body


def render_html(text: str, theme: str | None = None) -> str:
    """Render formatted output as a compact, readable result card."""
    palette = get_palette(theme or current_theme())
    if any(line.count("\u2500") >= 8 for line in text.splitlines()):
        return (
            "<html><body style='margin:4px;font-family:monospace;font-size:10pt;"
            f"color:{palette['text']};'><pre style='white-space:pre-wrap'>"
            f"{escape(text)}</pre></body></html>"
        )

    rows = []

    for raw_line in text.splitlines():
        if not raw_line.strip():
            rows.append('<div style="height:8px"></div>')
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        content = raw_line.strip()
        safe_content = escape(content)
        margin = min(indent // len(INDENT), 4) * 14

        if indent == 0:
            rows.append(
                f'<div style="font-size:10pt;font-weight:700;margin:0 0 8px;'
                f'color:{palette["text"]}">{safe_content}</div>'
            )
        elif content.startswith(WARN):
            message = escape(content[len(WARN):].strip())
            rows.append(
                f'<div style="margin:4px 0;padding:6px 9px;border-radius:5px;'
                f'background:{palette["danger"]};color:{palette["on_danger"]};">'
                f'! {message}</div>'
            )
        elif content.startswith(INFO):
            message = escape(content[len(INFO):].strip())
            rows.append(
                f'<div style="margin:5px 0;color:{palette["text_muted"]};">'
                f'· {message}</div>'
            )
        elif content.startswith(BULLET):
            item = escape(content[len(BULLET):].strip())
            rows.append(
                f'<div style="margin:3px 0 3px {margin + 4}px;'
                f'color:{palette["text"]};">'
                f'<span style="color:{palette["accent"]}">•</span> {item}</div>'
            )
        elif ":" in content:
            key, value = content.split(":", 1)
            rows.append(
                f'<div style="margin:3px 0 3px {margin}px;'
                f'padding:4px 7px;border-radius:4px;background:{palette["surface"]};">'
                f'<span style="color:{palette["text_muted"]};">{escape(key)}</span>'
                f'&nbsp;&nbsp;<span style="color:{palette["text"]};">'
                f'{escape(value.strip())}</span></div>'
            )
        else:
            rows.append(
                f'<div style="margin:5px 0 3px {margin}px;font-weight:600;'
                f'color:{palette["accent"]}">{safe_content}</div>'
            )

    body = "".join(rows)
    return (
        "<html><body style='margin:4px;font-family:monospace;font-size:10pt;"
        f"color:{palette['text']};'>{body}</body></html>"
    )


def set_output(widget: Any, text: str) -> None:
    """Display output richly where supported, keeping other widgets compatible."""
    if hasattr(widget, "set_output_text"):
        widget.set_output_text(text)
        return
    if hasattr(widget, "setHtml"):
        widget.setHtml(render_html(text))
    else:
        widget.setPlainText(text)
