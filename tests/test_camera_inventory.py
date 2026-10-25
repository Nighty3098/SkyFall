import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from src.modules.camera_inventory import (
    CACHE_TTL_SECONDS,
    CAMERA_API_URL,
    CAMERA_REQUEST_HEADERS,
    CameraDataError,
    fetch_cameras,
    filter_cameras,
    load_cameras,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class CameraInventoryTest(unittest.TestCase):
    def _load(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cameras.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_cameras(path)

    def test_loads_metadata_without_stream_urls(self):
        cameras = self._load(
            [
                {
                    "stream": "http://camera.invalid/live",
                    "preview_url": "http://camera.invalid/preview.jpg",
                    "country": "Germany",
                    "city": "Berlin",
                    "latitude": 52.52,
                    "longitude": 13.405,
                    "categories": ["other"],
                }
            ]
        )

        self.assertEqual(cameras[0].city, "Berlin")
        self.assertEqual(cameras[0].latitude, 52.52)
        self.assertFalse(hasattr(cameras[0], "stream"))
        self.assertFalse(hasattr(cameras[0], "preview_url"))

    def test_accepts_template_records_without_coordinates(self):
        cameras = self._load(
            [{"city": "", "country": "", "latitude": None, "longitude": None}]
        )

        self.assertEqual(len(cameras), 1)
        self.assertIsNone(cameras[0].latitude)
        self.assertIsNone(cameras[0].longitude)

    def test_rejects_partial_or_out_of_range_coordinates(self):
        with self.assertRaises(CameraDataError):
            self._load([{"latitude": 50, "longitude": None}])
        with self.assertRaises(CameraDataError):
            self._load([{"latitude": 91, "longitude": 0}])

    def test_filter_matches_city_or_country_case_insensitively(self):
        cameras = self._load(
            [
                {"city": "Berlin", "country": "Germany"},
                {"city": "Paris", "country": "France"},
            ]
        )

        self.assertEqual(
            [camera.city for camera in filter_cameras(cameras, "gErM")],
            ["Berlin"],
        )
        self.assertEqual(
            [camera.city for camera in filter_cameras(cameras, "par")],
            ["Paris"],
        )
        self.assertEqual(len(filter_cameras(cameras, "")), 2)

    def test_fetches_metadata_from_local_api(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch(
                "src.modules.camera_inventory.requests.get",
                return_value=FakeResponse(
                    [
                        {
                            "stream": "http://camera.invalid/live",
                            "preview_url": "http://camera.invalid/preview.jpg",
                            "city": "Berlin",
                            "country": "Germany",
                            "latitude": 52.52,
                            "longitude": 13.405,
                        }
                    ]
                ),
            ) as get:
                cameras = fetch_cameras(cache_path=Path(directory) / "cache.json")

        get.assert_called_once_with(
            CAMERA_API_URL,
            headers=CAMERA_REQUEST_HEADERS,
            timeout=10,
        )
        self.assertEqual(cameras[0].city, "Berlin")
        self.assertFalse(hasattr(cameras[0], "stream"))

    def test_fetch_reports_request_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch(
                "src.modules.camera_inventory.requests.get",
                side_effect=requests.ConnectionError("connection refused"),
            ):
                with self.assertRaisesRegex(CameraDataError, "camlist.net"):
                    fetch_cameras(cache_path=Path(directory) / "cache.json")

    def test_persists_metadata_cache_across_fetches_without_stream_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "camera-cache.json"
            response = FakeResponse(
                [
                    {
                        "stream": "http://camera.invalid/live",
                        "preview_url": "http://camera.invalid/preview.jpg",
                        "city": "Berlin",
                        "country": "Germany",
                        "latitude": 52.52,
                        "longitude": 13.405,
                    }
                ]
            )
            with mock.patch(
                "src.modules.camera_inventory.requests.get",
                return_value=response,
            ) as get:
                first = fetch_cameras(cache_path=cache_path)
                second = fetch_cameras(cache_path=cache_path)

            self.assertEqual(first, second)
            get.assert_called_once()
            cached_data = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(len(cached_data["cameras"]), 1)
            self.assertNotIn("stream", cache_path.read_text(encoding="utf-8"))
            self.assertNotIn("preview_url", cache_path.read_text(encoding="utf-8"))

    def test_expired_cache_is_refetched(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "camera-cache.json"
            initial_response = FakeResponse([{"city": "Berlin"}])
            with (
                mock.patch(
                    "src.modules.camera_inventory.time.time", return_value=1000
                ),
                mock.patch(
                    "src.modules.camera_inventory.requests.get",
                    return_value=initial_response,
                ),
            ):
                fetch_cameras(cache_path=cache_path)
            with (
                mock.patch(
                    "src.modules.camera_inventory.time.time",
                    return_value=1000 + CACHE_TTL_SECONDS,
                ),
                mock.patch(
                    "src.modules.camera_inventory.requests.get",
                    return_value=FakeResponse([{"city": "Paris"}]),
                ) as get,
            ):
                cameras = fetch_cameras(cache_path=cache_path)

            get.assert_called_once()
            self.assertEqual(cameras[0].city, "Paris")


if __name__ == "__main__":
    unittest.main()
