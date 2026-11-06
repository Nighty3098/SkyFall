"""Merge built-in transforms with user plugins and resolve them by entity type."""

from __future__ import annotations

from collections import defaultdict

from loguru import logger

from .loader import PluginLoader
from .models import TransformDef


class TransformRegistry:
    """Registry of transforms grouped by graph entity type.

    Built-in transforms keep their original order.  Plugin transforms are
    appended after them.  A plugin cannot silently replace a built-in
    transform: duplicate ``(entity_type, name)`` pairs are skipped and logged.
    """

    def __init__(
        self,
        builtin: dict[str, list[TransformDef]],
        plugin_loader: PluginLoader | None = None,
    ):
        self._builtin = builtin
        self._plugin_loader = plugin_loader
        self._registry: dict[str, list[TransformDef]] = {}
        self._rebuild()

    @property
    def plugin_loader(self) -> PluginLoader | None:
        return self._plugin_loader

    def get_transforms(self, entity_type: str) -> list[TransformDef]:
        if self._plugin_loader is not None:
            if self._plugin_loader.refresh_if_changed():
                self._rebuild()
        return self._registry.get(entity_type, [])

    def get_all_types(self) -> list[str]:
        return list(self._registry)

    def reload_plugins(self) -> None:
        """Force a plugin reload, for example after editing a plugin file."""

        if self._plugin_loader is not None:
            self._plugin_loader.reload()
            self._rebuild()

    def _rebuild(self) -> None:
        registry: dict[str, list[TransformDef]] = defaultdict(list)
        seen: set[tuple[str, str]] = set()

        for transform in self._iter_builtin():
            self._append(registry, seen, transform, source="built-in")

        if self._plugin_loader is not None:
            for transform in self._plugin_loader.transforms:
                self._append(registry, seen, transform, source="plugin")

        self._registry = dict(registry)

    def _iter_builtin(self):
        for transforms in self._builtin.values():
            yield from transforms

    def _append(self, registry, seen, transform, *, source: str) -> None:
        for entity_type in transform.input_types:
            entity_type = str(entity_type).strip()
            if not entity_type:
                continue
            key = (entity_type, transform.name)
            if key in seen:
                logger.warning(
                    "Skipping duplicate {} transform {!r} for {}",
                    source,
                    transform.name,
                    entity_type,
                )
                continue
            seen.add(key)
            registry[entity_type].append(transform)


__all__ = ["TransformRegistry"]
