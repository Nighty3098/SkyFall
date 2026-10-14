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
from typing import Any

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
