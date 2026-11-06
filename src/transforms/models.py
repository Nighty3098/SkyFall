"""Data structures shared by built-in and user-provided graph transforms."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TransformDef:
    """Description of one action shown in the graph transform picker.

    Plugin authors only need to fill in ``name``, ``input_types`` and
    ``handler``; the remaining fields have sensible defaults.
    """

    name: str
    description: str = ""
    input_types: list[str] = field(default_factory=list)
    output_type: str = "Custom"
    relationship: str = "related_to"
    handler: Callable[[str, dict[str, Any]], Any] | None = None
    use_content: bool = False


@dataclass
class ChildNodeDef:
    """A node that a transform wants to attach to the selected graph node."""

    title: str
    entity_type: str = "Custom"
    content: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass
class TransformResult:
    """Result of a transform.

    ``children`` are materialised as graph nodes.  ``content`` is used as the
    child content when no explicit children are returned and is also useful
    for the graph status output.  ``evidence`` is copied to generated nodes.
    """

    children: list[ChildNodeDef] = field(default_factory=list)
    content: str = ""
    evidence: list[str] = field(default_factory=list)


def coerce_transform_result(value: Any) -> TransformResult:
    """Normalise common return values from third-party transform handlers.

    Built-in handlers return :class:`TransformResult` directly.  Plugins may
    also return ``None``, a string, a single child, a list of children, or a
    mapping with ``children``/``content``/``evidence`` keys.
    """

    if isinstance(value, TransformResult):
        return value
    if value is None:
        return TransformResult()
    if isinstance(value, str):
        return TransformResult(content=value)
    if isinstance(value, ChildNodeDef):
        return TransformResult(children=[value])
    if isinstance(value, Mapping):
        payload = dict(value)
        raw_children = payload.get("children") or []
        children = _coerce_children(raw_children)
        return TransformResult(
            children=children,
            content=str(payload.get("content") or ""),
            evidence=[str(item) for item in (payload.get("evidence") or [])],
        )
    if isinstance(value, Iterable):
        return TransformResult(children=_coerce_children(value))
    return TransformResult(content=str(value))


def _coerce_children(value: Any) -> list[ChildNodeDef]:
    if isinstance(value, ChildNodeDef):
        return [value]
    children = []
    for item in value or []:
        if isinstance(item, ChildNodeDef):
            children.append(item)
        elif isinstance(item, Mapping):
            children.append(ChildNodeDef(**dict(item)))
        else:
            raise TypeError(
                "transform children must be ChildNodeDef instances or mappings"
            )
    return children
