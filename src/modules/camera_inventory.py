"""Load and filter a local inventory of cameras managed by the user."""

import json
import math
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from loguru import logger

CAMERA_API_URL = "https://camlist.net/"
REQUEST_TIMEOUT = 10
CACHE_TTL_SECONDS = 30 * 60
CACHE_PATH = Path.home() / ".skyfall" / "cache" / "camera_inventory.json"
CAMERA_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:158.0) "
        "Gecko/20100101 Firefox/158.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "DNT": "1",
    "Priority": "u=0, i",
}


class CameraDataError(ValueError):
    """Raised when a camera inventory file is invalid."""


@dataclass(frozen=True)
class Camera:
    stream: str
    country: str
    country_code: str
    region: str
    city: str
    latitude: float | None
    longitude: float | None
    timezone: str
    is_iframe: bool | None
    is_static: bool | None
    is_popular: bool | None
    categories: tuple[str, ...]


def _text(record: dict, key: str, index: int) -> str:
    value = record.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise CameraDataError(f"Camera {index}: '{key}' must be a string.")
    return value.strip()


def _coordinate(record: dict, key: str, index: int) -> float | None:
    value = record.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CameraDataError(f"Camera {index}: '{key}' must be a number or null.")
    coordinate = float(value)
    limit = 90 if key == "latitude" else 180
    if not math.isfinite(coordinate) or not -limit <= coordinate <= limit:
        raise CameraDataError(f"Camera {index}: '{key}' is out of range.")
    return coordinate


def _flag(record: dict, key: str, index: int) -> bool | None:
    value = record.get(key)
    if value is not None and not isinstance(value, bool):
        raise CameraDataError(f"Camera {index}: '{key}' must be a boolean or null.")
    return value


def load_cameras(path: str | Path) -> list[Camera]:
    """Load camera metadata from a local JSON file."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CameraDataError(f"Could not read camera JSON: {exc}") from exc

    return parse_cameras(payload)


def fetch_cameras(
    url: str = CAMERA_API_URL,
    cache_path: str | Path = CACHE_PATH,
) -> list[Camera]:
    """Return cached camera metadata or refresh it from the local inventory API."""
    cache_path = Path(cache_path)
    cached = _read_cache(cache_path)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            url,
            headers=CAMERA_REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        message = f"Could not fetch camera inventory from {url}: {exc}"
        raise CameraDataError(message) from exc
    cameras = parse_cameras(payload)
    _write_cache(cache_path, cameras)
    return cameras


def _read_cache(cache_path: Path) -> list[Camera] | None:
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        cached_at = cached["cached_at"]
        payload = cached["cameras"]
        age = time.time() - cached_at
        if (
            isinstance(cached_at, bool)
            or not isinstance(cached_at, (int, float))
            or not math.isfinite(cached_at)
            or age < 0
            or age >= CACHE_TTL_SECONDS
        ):
            return None
        return parse_cameras(payload)
    except FileNotFoundError:
        return None
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        CameraDataError,
    ) as exc:
        logger.warning(f"Ignoring invalid camera cache at {cache_path}: {exc}")
        return None


def _write_cache(cache_path: Path, cameras: list[Camera]) -> None:
    cache_data = {
        "cached_at": time.time(),
        "cameras": [
            {
                "country": camera.country,
                "country_code": camera.country_code,
                "region": camera.region,
                "city": camera.city,
                "latitude": camera.latitude,
                "longitude": camera.longitude,
                "timezone": camera.timezone,
                "is_iframe": camera.is_iframe,
                "is_static": camera.is_static,
                "is_popular": camera.is_popular,
                "categories": list(camera.categories),
            }
            for camera in cameras
        ],
    }
    temporary_path = None
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=cache_path.parent,
            prefix=f".{cache_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(cache_data, temporary_file, ensure_ascii=False)
        os.replace(temporary_path, cache_path)
    except OSError as exc:
        logger.warning(f"Could not write camera cache at {cache_path}: {exc}")
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as cleanup_error:
                logger.warning(
                    f"Could not remove temporary camera cache {temporary_path}: "
                    f"{cleanup_error}"
                )


def parse_cameras(payload) -> list[Camera]:
    """Validate camera records, retaining metadata but not stream URLs."""
    if not isinstance(payload, list):
        raise CameraDataError("Camera JSON must contain an array.")

    cameras = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise CameraDataError(f"Camera {index} must be a JSON object.")

        latitude = _coordinate(item, "latitude", index)
        longitude = _coordinate(item, "longitude", index)
        if (latitude is None) != (longitude is None):
            raise CameraDataError(
                f"Camera {index} must have both coordinates or neither."
            )

        categories = item.get("categories", [])
        if not isinstance(categories, list) or any(
            not isinstance(category, str) for category in categories
        ):
            raise CameraDataError(
                f"Camera {index}: 'categories' must be an array of strings."
            )

        cameras.append(
            Camera(
                stream=_text(item, "stream", index),
                country=_text(item, "country", index),
                country_code=_text(item, "country_code", index),
                region=_text(item, "region", index),
                city=_text(item, "city", index),
                latitude=latitude,
                longitude=longitude,
                timezone=_text(item, "timezone", index),
                is_iframe=_flag(item, "is_iframe", index),
                is_static=_flag(item, "is_static", index),
                is_popular=_flag(item, "is_popular", index),
                categories=tuple(categories),
            )
        )
    return cameras


def filter_cameras(cameras: list[Camera], query: str) -> list[Camera]:
    """Match a filter against the camera's city or country, case-insensitively."""
    query = query.strip().casefold()
    if not query:
        return list(cameras)
    return [
        camera
        for camera in cameras
        if query in camera.city.casefold() or query in camera.country.casefold()
    ]
