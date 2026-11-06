"""Shared helpers used by built-in transforms and transform plugins."""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .models import TransformResult

CHILD_THRESHOLD = 5

_PATTERNS: dict[str, re.Pattern] = {
    "Domain": re.compile(
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}"
    ),
    "IP": re.compile(
        r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"
    ),
    "Email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "Phone": re.compile(r"\+?\d[\d\s\-().]{6,}\d"),
    "MAC": re.compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}"),
    "Crypto": re.compile(r"(?:1|3|bc1|0x)[a-zA-Z0-9]{25,}"),
}


def transform_input(node, etype, title, content, default_prefix):
    """Pick the value a transform should send to its handler."""
    if etype == "Photo":
        candidates = [title, content, *(getattr(node, "evidence", None) or [])]
        for candidate in candidates:
            path = local_file_path(candidate)
            if path:
                return path
        return ""

    pattern = _PATTERNS.get(etype)
    if pattern:
        match = pattern.fullmatch(title) if title and title != default_prefix else None
        if match:
            return match.group()
        match = pattern.search(content) if content else None
        if match:
            return match.group()
        return ""

    if title and title != default_prefix:
        return title
    return content


def local_file_path(value):
    if not value:
        return ""
    text = str(value).strip().strip("\"'")
    if not text or text.startswith(("http://", "https://")):
        return ""
    text = text.removeprefix("file://").strip()
    path = Path(text).expanduser()
    if path.exists():
        return str(path)
    return ""


def pack_content(lines: list[str]) -> str:
    return "\n".join(str(line) for line in lines if line)


async def run_transform(
    modules: dict,
    module_key: str,
    method: str,
    input_value: str,
    parser: Callable,
    label: str | None = None,
    **kwargs,
) -> TransformResult:
    """Compatibility helper for transforms that call a SkyFall module.

    The target method may be synchronous or asynchronous.  The parser receives
    the raw result and the input value, matching the built-in transform style.
    """

    engine = modules.get(module_key)
    if not engine:
        message = label or module_key.replace("_", " ").title().replace(" ", "")
        return TransformResult(content=f"{message} module not available")
    function = getattr(engine, method)
    result = (
        await function(input_value, **kwargs)
        if inspect.iscoroutinefunction(function)
        else function(input_value, **kwargs)
    )
    return parser(result, input_value)


def setting(modules: dict, name: str) -> str:
    settings = modules.get("settings")
    return str(getattr(settings, name, "") or "") if settings is not None else ""


def safe_float(value: Any):
    """Best-effort float conversion; returns None instead of raising."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Backwards-compatible private aliases used by built-in handlers and tests.
_transform_input = transform_input
_local_file_path = local_file_path
_pack_content = pack_content
_run_transform = run_transform
_setting = setting
_safe_float = safe_float

__all__ = [
    "CHILD_THRESHOLD",
    "local_file_path",
    "pack_content",
    "run_transform",
    "safe_float",
    "setting",
    "transform_input",
    "_local_file_path",
    "_pack_content",
    "_run_transform",
    "_safe_float",
    "_setting",
    "_transform_input",
]
