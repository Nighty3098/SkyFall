"""Discovery and loading of user-provided transform plugins."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import sys
import time
from pathlib import Path

from loguru import logger

from .models import TransformDef
from .template import PLUGIN_README

DEFAULT_TRANSFORM_DIR = Path.home() / ".skyfall" / "transforms"
PLUGIN_DIR_ENV = "SKYFALL_TRANSFORMS_DIR"


def plugin_directory(directory: str | Path | None = None) -> Path:
    """Return the configured plugin directory without creating it."""

    if directory is not None:
        return Path(directory).expanduser()
    override = os.environ.get(PLUGIN_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return DEFAULT_TRANSFORM_DIR


def ensure_plugin_dir(directory: str | Path | None = None) -> Path:
    """Create the plugin directory and a short README on first use."""

    path = plugin_directory(directory)
    path.mkdir(parents=True, exist_ok=True)
    readme = path / "README.md"
    if not readme.exists():
        try:
            readme.write_text(PLUGIN_README, encoding="utf-8")
        except OSError as exc:  # pragma: no cover - permission dependent
            logger.warning("Could not write transform plugin README: {}", exc)
    return path


class PluginLoader:
    """Load ``*.py`` transform plugins from a directory.

    The loader is intentionally forgiving: a broken plugin is logged and
    skipped, while built-in transforms and all other plugins continue to work.
    The directory signature is checked periodically so adding or editing a
    plugin while SkyFall is running is picked up without a restart.
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        *,
        create: bool = True,
        check_interval: float = 2.0,
    ):
        self.directory = plugin_directory(directory)
        self._create = create
        self._check_interval = max(0.0, check_interval)
        self._transforms: list[TransformDef] = []
        self._errors: list[str] = []
        self._loaded_files: list[Path] = []
        self._signature: tuple[tuple[str, int, int], ...] = ()
        self._last_check = 0.0
        self.reload()

    @property
    def transforms(self) -> list[TransformDef]:
        return list(self._transforms)

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    @property
    def loaded_files(self) -> list[Path]:
        return list(self._loaded_files)

    def refresh_if_changed(self, *, force: bool = False) -> bool:
        """Reload plugins if the directory changed.

        Returns ``True`` when the plugin set was reloaded.
        """

        now = time.monotonic()
        if not force and now - self._last_check < self._check_interval:
            return False
        self._last_check = now
        signature = self._scan_signature()
        if not force and signature == self._signature:
            return False
        self.reload()
        return True

    def reload(self) -> list[TransformDef]:
        """Reload all plugin files from disk."""

        if self._create:
            ensure_plugin_dir(self.directory)
        self._signature = self._scan_signature()
        self._last_check = time.monotonic()

        transforms: list[TransformDef] = []
        errors: list[str] = []
        loaded_files: list[Path] = []
        for path in self._plugin_files():
            try:
                plugin_transforms = self._load_file(path)
            except Exception as exc:  # noqa: BLE001 - isolate broken plugins
                message = f"{path.name}: {exc}"
                errors.append(message)
                logger.warning("Transform plugin failed: {}", message)
                continue
            transforms.extend(plugin_transforms)
            loaded_files.append(path)

        self._transforms = transforms
        self._errors = errors
        self._loaded_files = loaded_files
        if transforms:
            logger.info(
                "Loaded {} custom transform(s) from {}",
                len(transforms),
                self.directory,
            )
        else:
            logger.debug("No custom transform plugins in {}", self.directory)
        return list(transforms)

    def _plugin_files(self) -> list[Path]:
        if not self.directory.is_dir():
            return []
        return sorted(
            path
            for path in self.directory.glob("*.py")
            if path.is_file() and not path.name.startswith("_")
        )

    def _scan_signature(self) -> tuple[tuple[str, int, int], ...]:
        signature = []
        for path in self._plugin_files():
            try:
                stat = path.stat()
            except OSError:
                continue
            signature.append((path.name, stat.st_mtime_ns, stat.st_size))
        return tuple(signature)

    def _load_file(self, path: Path) -> list[TransformDef]:
        module_name = self._module_name(path)
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError("could not create an import spec")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        return self._extract(module, path)

    def _extract(self, module, path: Path) -> list[TransformDef]:
        factory = getattr(module, "get_transforms", None)
        if callable(factory):
            raw = factory()
        elif hasattr(module, "TRANSFORMS"):
            raw = module.TRANSFORMS
        else:
            raise ValueError("define TRANSFORMS or get_transforms()")

        if raw is None:
            return []
        if isinstance(raw, TransformDef):
            raw = [raw]
        else:
            raw = list(raw)

        transforms = []
        for item in raw:
            if not isinstance(item, TransformDef):
                raise TypeError(
                    f"{path.name}: expected TransformDef, got {type(item).__name__}"
                )
            self._validate(item, path)
            transforms.append(item)
        return transforms

    def _validate(self, transform: TransformDef, path: Path) -> None:
        if not str(transform.name or "").strip():
            raise ValueError(f"{path.name}: transform name is empty")
        if isinstance(transform.input_types, str):
            transform.input_types = [transform.input_types]
        if not transform.input_types:
            raise ValueError(
                f"{path.name}: transform {transform.name!r} has no input_types"
            )
        if not callable(transform.handler):
            raise ValueError(
                f"{path.name}: transform {transform.name!r} has no handler"
            )

    def _module_name(self, path: Path) -> str:
        stem = re.sub(r"[^0-9A-Za-z_]", "_", path.stem)
        digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
        return f"_skyfall_transform_{stem}_{digest}"


__all__ = [
    "DEFAULT_TRANSFORM_DIR",
    "PLUGIN_DIR_ENV",
    "PluginLoader",
    "ensure_plugin_dir",
    "plugin_directory",
]
