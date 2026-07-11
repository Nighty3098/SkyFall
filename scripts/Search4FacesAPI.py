import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests


class Search4FacesAPI:
    def __init__(self):
        self.base_url = "https://search4faces.com"
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
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

    def get_cookies(self) -> bool:
        try:
            response = self.session.get(f"{self.base_url}/search_vkwall.html")
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to get cookies: {e}")
            return False

    def upload_image(self, image_path: str) -> Optional[Dict]:
        url = f"{self.base_url}/assets/php/upload.php"

        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            response = self.session.post(
                url, data=image_data, headers={"Content-Type": "image/jpeg"}
            )

            if response.status_code != 200:
                print(f"Upload error: HTTP {response.status_code}")
                return None

            result = response.json()
            print(f"Image uploaded. File: {result.get('url')}")
            return result

        except FileNotFoundError:
            print(f"File not found: {image_path}")
            return None
        except json.JSONDecodeError:
            print("Failed to parse JSON response")
            return None
        except Exception as e:
            print(f"Image upload error: {e}")
            return None

    def detect_faces(
        self,
        filename: str,
        boundings: List,
        query: str = "vk01",
        results: int = 500,
        lang: str = "ru",
    ) -> Optional[Dict]:
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
                print(f"Search error: HTTP {response.status_code}")
                return None

            result = response.json()
            faces_found = result.get("faces_found", 0)
            print(f"Matches found: {faces_found}")
            return result

        except Exception as e:
            print(f"Search execution error: {e}")
            return None

    def search_face(
        self, image_path: str, max_results: int = 500
    ) -> Optional[List[Dict]]:
        print(f"\nStarting face search for: {image_path}")
        print("=" * 60)

        print("\nStep 1: Getting session...")
        if not self.get_cookies():
            print("Failed to get cookies")
            return None

        print("\nStep 2: Uploading image...")
        upload_result = self.upload_image(image_path)
        if not upload_result:
            print("Image upload failed")
            return None

        filename = upload_result.get("url")
        boundings = upload_result.get("boundings", [])

        if not filename or not boundings:
            print("Invalid server response")
            return None

        if isinstance(boundings, list) and len(boundings) > 0:
            if isinstance(boundings[0], list):
                boundings_flat = [item for sublist in boundings for item in sublist]
            else:
                boundings_flat = boundings
        else:
            boundings_flat = []

        time.sleep(1)

        print("\nStep 3: Searching for matches...")
        detect_result = self.detect_faces(
            filename=filename, boundings=boundings_flat, results=max_results
        )

        if not detect_result:
            print("Search failed")
            return None

        faces = detect_result.get("faces", [])
        if not faces:
            print("No matches found")
            return []

        print(f"\n{'=' * 60}")
        print(f"FOUND {len(faces)} MATCHES")
        print(f"{'=' * 60}\n")

        profiles = []
        for i, face in enumerate(faces, 1):
            profile = self._parse_face_data(face, i)
            profiles.append(profile)
            self._print_profile(profile)

        return profiles

    def _parse_face_data(self, face: List, index: int) -> Dict:
        return {
            "index": index,
            "source": face[0] if len(face) > 0 else "",
            "vk_url": face[1] if len(face) > 1 else "",
            "face_image_url": face[2] if len(face) > 2 else "",
            "photo_url": face[3] if len(face) > 3 else "",
            "photo_id": face[4] if len(face) > 4 else "",
            "coordinates": {
                "x1": face[5] if len(face) > 5 else 0,
                "y1": face[6] if len(face) > 6 else 0,
                "x2": face[7] if len(face) > 7 else 0,
                "y2": face[8] if len(face) > 8 else 0,
            },
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
            "extra": face[19] if len(face) > 19 else "",
        }

    def _print_profile(self, profile: Dict):
        print(f"Profile #{profile['index']}")
        print(f"   Name: {profile['first_name']} {profile['last_name']}")
        if profile["middle_name"]:
            print(f"   Middle name: {profile['middle_name']}")
        print(f"   Age: {profile['age'] if profile['age'] else 'not specified'}")
        if profile["birthday"]:
            print(f"   Birthday: {profile['birthday']}")
        print(f"   City: {profile['city']}, {profile['country']}")
        print(f"   Similarity: {profile['similarity']}%")
        print(f"   VK ID: {profile['vk_url']}")
        print(f"   Profile photo: {profile['face_image_url']}")
        print(f"   Original photo: {profile['full_photo_url']}")
        print("-" * 60)

    def download_images(
        self,
        profiles: List[Dict],
        download_dir: str = "downloaded_faces",
        download_full: bool = True,
    ) -> List[str]:
        if not profiles:
            return []

        Path(download_dir).mkdir(parents=True, exist_ok=True)

        downloaded_files = []

        for i, profile in enumerate(profiles, 1):
            try:
                face_url = profile.get("face_image_url")
                if face_url:
                    safe_name = self._safe_filename(
                        f"{profile['first_name']}_{profile['last_name']}"
                    )
                    face_filename = f"{download_dir}/face_{i}_{safe_name}.jpg"
                    self._download_file(face_url, face_filename)
                    downloaded_files.append(face_filename)
                    print(f"Downloaded face: {face_filename}")

                if download_full:
                    full_url = profile.get("full_photo_url")
                    if full_url:
                        safe_name = self._safe_filename(
                            f"{profile['first_name']}_{profile['last_name']}"
                        )
                        full_filename = f"{download_dir}/full_{i}_{safe_name}.jpg"
                        self._download_file(full_url, full_filename)
                        downloaded_files.append(full_filename)
                        print(f"Downloaded full photo: {full_filename}")

            except Exception as e:
                print(f"Download error for profile #{i}: {e}")

        return downloaded_files

    def _safe_filename(self, name: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")
        return name.strip()

    def _download_file(self, url: str, filepath: str):
        response = self.session.get(url, stream=True)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    def save_results_to_json(
        self, profiles: List[Dict], output_file: str = "results.json"
    ):
        if not profiles:
            print("No data to save")
            return

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(profiles, f, ensure_ascii=False, indent=2)
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Save error: {e}")


def main():
    api = Search4FacesAPI()

    image_path = "test_image.jpg"

    profiles = api.search_face(image_path, max_results=500)

    if profiles:
        api.save_results_to_json(profiles, "search_results.json")

        print("\nDownloading images...")
        downloaded = api.download_images(
            profiles, download_dir="results", download_full=True
        )
        print(f"Downloaded {len(downloaded)} files")

        print(f"\nSearch complete! Found {len(profiles)} profiles")
    else:
        print("\nSearch returned no results")


if __name__ == "__main__":
    main()
