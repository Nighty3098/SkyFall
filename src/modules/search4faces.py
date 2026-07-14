import asyncio

import requests
from loguru import logger


class Search4Faces:
    def __init__(self) -> None:
        logger.debug("Init: Search4Faces")
        self.base_url = "https://search4faces.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://search4faces.com",
                "Referer": "https://search4faces.com/search_vkwall.html",
                "Sec-Ch-Ua": '"Chromium";v="149", "Not)A;Brand";v="24"',
                "Sec-Ch-Ua-Platform": '"Linux"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Accept-Encoding": "gzip, deflate, br",
                "Priority": "u=1, i",
            }
        )

    def _get_cookies(self) -> bool:
        try:
            response = self.session.get(f"{self.base_url}/search_vkwall.html")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"S4F get cookies failed: {e}")
            return False

    def _upload_image(self, image_path: str) -> dict | None:
        url = f"{self.base_url}/assets/php/upload.php"
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            response = self.session.post(
                url, data=image_data, headers={"Content-Type": "image/jpeg"}
            )
            if response.status_code != 200:
                logger.error(f"S4F upload error: HTTP {response.status_code}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"S4F upload error: {e}")
            return None

    def _detect_faces(
        self,
        filename: str,
        boundings: list,
        query: str = "vk01",
        results: int = 500,
        lang: str = "ru",
    ) -> dict | None:
        url = f"{self.base_url}/assets/php/detect.php"
        payload = {
            "query": query,
            "results": results,
            "lang": lang,
            "filename": filename,
            "boundings": boundings,
        }
        try:
            response = self.session.post(
                url, json=payload, headers={"Content-Type": "text/plain;charset=UTF-8"}
            )
            if response.status_code != 200:
                logger.error(f"S4F detect error: HTTP {response.status_code}")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"S4F detect error: {e}")
            return None

    def _parse_face(self, face: list, index: int) -> dict:
        return {
            "index": index,
            "source": face[0] if len(face) > 0 else "",
            "vk_url": face[1] if len(face) > 1 else "",
            "face_image_url": face[2] if len(face) > 2 else "",
            "photo_url": face[3] if len(face) > 3 else "",
            "photo_id": face[4] if len(face) > 4 else "",
            "full_photo_url": face[9] if len(face) > 9 else "",
            "similarity": float(face[10]) if len(face) > 10 and face[10] else 0,
            "type": face[11] if len(face) > 11 else "",
            "age": (
                int(face[12])
                if len(face) > 12 and face[12] != "" and face[12] != "-1"
                else None
            ),
            "first_name": face[13] if len(face) > 13 else "",
            "last_name": face[14] if len(face) > 14 else "",
            "middle_name": face[15] if len(face) > 15 else "",
            "city": face[16] if len(face) > 16 else "",
            "country": face[17] if len(face) > 17 else "",
            "birthday": face[18] if len(face) > 18 and face[18] != "" else "",
        }

    def _search_sync(self, image_path: str, max_results: int = 500) -> list[dict]:
        logger.debug(f"S4F search: {image_path}")

        if not self._get_cookies():
            logger.error("S4F: failed to get cookies")
            return []

        upload = self._upload_image(image_path)
        if not upload:
            return []

        filename = upload.get("url")
        boundings = upload.get("boundings", [])
        if not filename or not boundings:
            return []

        if isinstance(boundings, list) and boundings:
            if isinstance(boundings[0], list):
                boundings = [item for sub in boundings for item in sub]

        import time

        time.sleep(1)

        detect = self._detect_faces(filename, boundings, results=max_results)
        if not detect:
            return []

        faces = detect.get("faces", [])
        profiles = [self._parse_face(f, i) for i, f in enumerate(faces, 1)]
        logger.info(f"S4F: found {len(profiles)} matches")
        return profiles

    async def search_face(self, image_path: str, max_results: int = 500) -> list[dict]:
        return await asyncio.to_thread(self._search_sync, image_path, max_results)

    def download_image_sync(self, url: str) -> bytes | None:
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"S4F download error: {e}")
        return None

    async def download_image(self, url: str) -> bytes | None:
        return await asyncio.to_thread(self.download_image_sync, url)
