import asyncio
import datetime
import hashlib
import os
import re as _re
import stat
from pathlib import Path

import hachoir.core.config as _hconfig
import hachoir.metadata.setter as _hms
import httpx
import magic
from fake_useragent import UserAgent
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from loguru import logger

_hconfig.quiet = True

_hms.DATETIME_REGEX1 = _re.compile(
    r"^([0-9]{4})~([01][0-9])~([0-9]{1,2})~([0-9]{1,2})~([0-9]{1,2})~([0-9]{1,2})$"
)
_hms.DATETIME_REGEX2 = _re.compile(
    r"^([01]?[0-9])~([0-9]{1,2})~([0-9]{4})~([0-9]{1,2})~([0-9]{1,2})~([0-9]{1,2})$"
)


class FileAnalyzer:
    def __init__(self, virustotal_api_key):
        logger.debug("Init: FileAnalyzer")
        self.API_KEYS = {
            "VIRUSTOTAL": virustotal_api_key,
        }
        self.HEADERS = {
            "accept": "application/json",
            "x-apikey": self.API_KEYS["VIRUSTOTAL"],
        }
        self.ua = UserAgent()
        self._client = httpx.AsyncClient(headers=self.HEADERS, timeout=120)

    def update_api_key(self, new_key):
        self.API_KEYS["VIRUSTOTAL"] = new_key
        self.HEADERS["x-apikey"] = new_key
        self._client.headers.update({"x-apikey": new_key})

    async def close(self):
        await self._client.aclose()

    async def _read_file_bytes(self, path):
        def _read(path):
            with open(path, "rb") as f:
                return f.read()

        return await asyncio.to_thread(_read, path)

    async def _calculate_sha256(self, path):
        logger.debug("Calc file sha256...")

        def _hash(path):
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                for byte_block in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()

        return await asyncio.to_thread(_hash, path)

    async def check_file_by_hash(self, path):
        url = f"https://www.virustotal.com/api/v3/files/{path}"
        response = await self._client.get(url)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            logger.error(f"Error: {response.status_code}")
            return None

    async def get_large_file_upload_url(self):
        url = "https://www.virustotal.com/api/v3/files/upload_url"
        response = await self._client.get(url)

        if response.status_code == 200:
            return response.json()["data"]
        else:
            logger.error(
                f"Error while getting large file upload url: {response.status_code}"
            )
            print(response.text)
            return None

    async def upload_and_scan_file(self, file_path):
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)

        logger.debug(f"File size: {file_size_mb:.2f} MB")

        if file_size_mb > 650:
            logger.error("Error: file size limit: 650 MB.")
            return None

        if file_size_mb > 32:
            logger.debug("File size > 32 MB...")
            upload_url = await self.get_large_file_upload_url()
            if not upload_url:
                return None
        else:
            logger.debug("File size < 32 mb...")
            upload_url = "https://www.virustotal.com/api/v3/files"

        logger.debug("Starting upload to virustotal...")

        def _read_file(path):
            with open(path, "rb") as f:
                return (os.path.basename(path), f.read())

        filename, content = await asyncio.to_thread(_read_file, file_path)
        files = {"file": (filename, content)}
        response = await self._client.post(upload_url, files=files)

        if response.status_code == 200:
            analysis_data = response.json()
            analysis_id = analysis_data["data"]["id"]
            return analysis_id
        else:
            logger.error(f"Error: {response.status_code}")
            logger.debug(response.text)
            return None

    async def wait_for_analysis(self, analysis_id):
        url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"

        while True:
            response = await self._client.get(url)
            if response.status_code == 200:
                status = response.json()["data"]["attributes"]["status"]
                if status == "completed":
                    logger.debug("Complete!")
                    return response.json()["data"]["attributes"]["results"]
                else:
                    await asyncio.sleep(30)
            else:
                logger.error(f"Error: {response.status_code}")
                return None

    def get_virustotal_info(self, hash_value, stats, results=None):
        info = {
            "hash": f"{hash_value[:16]}...",
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "detected": [],
        }
        if results:
            found_threats = False
            for engine, details in results.items():
                category = details.get("category")
                if category in ["malicious", "suspicious"]:
                    found_threats = True
                    result_name = details.get("result", "Unknown Threat")
                    info["detected"].append(
                        f"[{category.upper()}] {engine}: {result_name}"
                    )
            if not found_threats:
                info["detected"] = ["Not found"]
        return info

    async def virustotal_analyze(self, path):
        if not os.path.exists(path):
            logger.debug(f"Error: File {path} not found.")
            return {"error": f"File not found: {path}"}

        file_hash = await self._calculate_sha256(path)
        logger.debug(f"SHA-256: {file_hash}")

        report = await self.check_file_by_hash(file_hash)

        if report:
            logger.debug("Found in VirusTotal DB!")
            attributes = report["data"]["attributes"]
            stats = attributes["last_analysis_stats"]
            results = attributes.get("last_analysis_results")
            return self.get_virustotal_info(file_hash, stats, results)

        logger.debug("File not found in VirusTotal DB.")
        if not self.API_KEYS.get("VIRUSTOTAL"):
            return {"error": "VirusTotal API key not configured"}
        analysis_id = await self.upload_and_scan_file(path)
        if not analysis_id:
            return {"error": "Failed to upload file to VirusTotal"}
        results = await self.wait_for_analysis(analysis_id)
        if not results:
            return {"error": "VirusTotal analysis did not complete"}
        stats = {
            "malicious": 0,
            "suspicious": 0,
            "harmless": 0,
            "undetected": 0,
        }
        for engine, res in results.items():
            category = res.get("category")
            if category in stats:
                stats[category] += 1
        return self.get_virustotal_info(file_hash, stats)

    def get_file_type(self, path):
        path = Path(path)
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(str(path))
        except Exception as e:
            return str(e)

    async def _get_file_hashes(self, path: Path) -> dict:
        def _hashes(path):
            md5_hash = hashlib.md5()
            sha256_hash = hashlib.sha256()
            try:
                with open(path, "rb") as f:
                    for byte_block in iter(lambda: f.read(65536), b""):
                        md5_hash.update(byte_block)
                        sha256_hash.update(byte_block)
                return {"md5": md5_hash.hexdigest(), "sha256": sha256_hash.hexdigest()}
            except Exception:
                return {"md5": "Error", "sha256": "Error"}

        return await asyncio.to_thread(_hashes, path)

    async def check_tail_data(self, path):
        data = await self._read_file_bytes(path)

        png_eof = b"IEND\xaeB`\x82"
        idx = data.find(png_eof)

        if idx != -1:
            tail = data[idx + len(png_eof) :]
            if len(tail) > 0:
                return {"hidden_data": True, "tail_size": len(tail)}
        return {"hidden_data": False, "tail_size": 0}

    @staticmethod
    def extract_file_info_sync(path: str) -> dict:
        p = Path(path)
        info = {}

        if not p.exists():
            return info

        info["file_size"] = p.stat().st_size

        try:
            mime = magic.Magic(mime=True)
            info["mime_type"] = mime.from_file(str(p))
        except Exception:
            pass

        def _parse(path):
            parser = createParser(str(path))
            if not parser:
                return {}
            try:
                metadata = extractMetadata(parser)
                if not metadata:
                    return {}
                result = {}
                for key in ("width", "height", "duration"):
                    val = metadata.get(key)
                    if val is not None:
                        result[key] = int(val) if key != "duration" else float(val)
                lat = metadata.get("latitude")
                lng = metadata.get("longitude")
                if lat is not None and lng is not None:
                    result["gps_latitude"] = float(lat)
                    result["gps_longitude"] = float(lng)
                return result
            except Exception:
                return {}
            finally:
                parser.stream._input.close()

        info.update(_parse(p))
        return info

    async def get_metadata(self, path):
        path = Path(path)

        if not path.exists():
            return {"error": f"File '{path}' not found."}

        file_stat = path.stat()

        def _ts_to_str(ts):
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

        created_time = _ts_to_str(file_stat.st_ctime)
        modified_time = _ts_to_str(file_stat.st_mtime)
        accessed_time = _ts_to_str(file_stat.st_atime)

        file_permissions = stat.filemode(file_stat.st_mode)
        size_kb = file_stat.st_size / 1024

        meta = {
            "File": path.name,
            "Size": f"{size_kb:.2f} KB ({file_stat.st_size} bytes)",
            "Created (OS)": created_time,
            "Modified (OS)": modified_time,
            "Accessed (OS)": accessed_time,
            "Permissions": file_permissions,
        }

        hashes = await self._get_file_hashes(path)
        meta["MD5 Hash"] = hashes["md5"]
        meta["SHA-256 Hash"] = hashes["sha256"]

        try:

            def _mime(path):
                mime = magic.Magic(mime=True)
                return mime.from_file(str(path))

            file_type = await asyncio.to_thread(_mime, path)
            meta["MIME type"] = file_type
        except Exception as e:
            meta["MIME type"] = f"unknown ({e})"

        def _parse_metadata(path):
            parser = createParser(str(path))
            if not parser:
                return None
            try:
                metadata = extractMetadata(parser)
                if metadata:
                    return metadata.exportPlaintext()
                return []
            except Exception:
                raise
            finally:
                parser.stream._input.close()

        try:
            text_data = await asyncio.to_thread(_parse_metadata, path)
            if text_data is None:
                meta["Internal metadata (Hachoir)"] = [
                    "Hachoir could not parse this format."
                ]
            elif text_data:
                meta["Internal metadata (Hachoir)"] = list(text_data)
            else:
                meta["Internal metadata (Hachoir)"] = [
                    "No internal metadata found in file."
                ]
        except Exception as e:
            meta["Internal metadata (Hachoir)"] = [f"Error reading metadata: {e}"]

        return meta

    async def get_gps_coordinates(self, path) -> tuple[float, float] | None:
        def _extract(path):
            parser = createParser(str(path))
            if not parser:
                return None
            try:
                metadata = extractMetadata(parser)
                if not metadata:
                    return None
                lat = metadata.get("latitude")
                lng = metadata.get("longitude")
                if lat is not None and lng is not None:
                    return (float(lat), float(lng))
                return None
            except Exception:
                return None
            finally:
                parser.stream._input.close()

        return await asyncio.to_thread(_extract, path)

    async def get_strings(self, path, min_len=4):
        def _read_and_extract(path):
            with open(path, "rb") as f:
                content = f.read()
            pattern = rb"[ -~]{" + str(min_len).encode() + rb",}"
            return [s.decode("ascii") for s in _re.findall(pattern, content)]

        return await asyncio.to_thread(_read_and_extract, path)
