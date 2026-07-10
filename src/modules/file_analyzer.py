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

from src.ui.output_formatter import (
    divider,
    end_of,
    error,
    info,
    kv,
    line,
    section,
    title,
)

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
        result = divider() + "\n"
        result += title(f"VirusTotal: {hash_value[:16]}...") + "\n"
        result += kv("Malicious", stats.get("malicious", 0)) + "\n"
        result += kv("Suspicious", stats.get("suspicious", 0)) + "\n"
        result += kv("Harmless", stats.get("harmless", 0)) + "\n"
        result += kv("Undetected", stats.get("undetected", 0)) + "\n"
        result += divider() + "\n"

        if results:
            result += section("Detected") + "\n"
            found_threats = False
            for engine, details in results.items():
                category = details.get("category")
                if category in ["malicious", "suspicious"]:
                    found_threats = True
                    result_name = details.get("result", "Unknown Threat")
                    result += (
                        line(f"[{category.upper()}] {engine}: {result_name}") + "\n"
                    )

            if not found_threats:
                result += info("Not found") + "\n"
            result += divider() + "\n"

        result += end_of("virustotal") + "\n"
        result += divider() + "\n"

        return result

    async def virustotal_analyze(self, path):
        if not os.path.exists(path):
            logger.debug(f"Error: File {path} not found.")
            return ""

        file_hash = await self._calculate_sha256(path)
        logger.debug(f"SHA-256: {file_hash}")

        report = await self.check_file_by_hash(file_hash)

        if report:
            logger.debug("Found in VirusTotal DB!")
            attributes = report["data"]["attributes"]
            stats = attributes["last_analysis_stats"]
            results = attributes.get("last_analysis_results")
            return self.get_virustotal_info(file_hash, stats, results)
        else:
            logger.debug("File not found in VirusTotal DB.")
            analysis_id = await self.upload_and_scan_file(path)
            if analysis_id:
                results = await self.wait_for_analysis(analysis_id)
                if results:
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
            return ""

    def get_file_type(self, path):
        path = Path(path)
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(str(path))
            return line(file_type) + "\n"
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
        result = divider() + "\n"
        result += title("Tail Data") + "\n"

        data = await self._read_file_bytes(path)

        png_eof = b"IEND\xaeB`\x82"
        idx = data.find(png_eof)

        if idx != -1:
            tail = data[idx + len(png_eof) :]
            if len(tail) > 0:
                result += (
                    info(f"Hidden data discovered after EOF! Size: {len(tail)} bytes.")
                    + "\n"
                )
        result += line("Clean") + "\n"
        result += end_of("tail data") + "\n"
        result += divider() + "\n"

        return result

    async def get_metadata(self, path):
        path = Path(path)
        result = ""

        if not path.exists():
            result += error(f"File '{path}' not found.")
            return result

        result += divider() + "\n"
        result += title("Metadata") + "\n"

        file_stat = path.stat()

        def _ts_to_str(ts):
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

        created_time = _ts_to_str(file_stat.st_ctime)
        modified_time = _ts_to_str(file_stat.st_mtime)
        accessed_time = _ts_to_str(file_stat.st_atime)

        file_permissions = stat.filemode(file_stat.st_mode)

        result += kv("File", path.name) + "\n"
        size_kb = file_stat.st_size / 1024
        result += kv("Size", f"{size_kb:.2f} KB ({file_stat.st_size} bytes)") + "\n"

        result += kv("Created (OS)", created_time) + "\n"
        result += kv("Modified (OS)", modified_time) + "\n"
        result += kv("Accessed (OS)", accessed_time) + "\n"
        result += kv("Permissions", file_permissions) + "\n"

        hashes = await self._get_file_hashes(path)
        result += kv("MD5 Hash", hashes["md5"]) + "\n"
        result += kv("SHA-256 Hash", hashes["sha256"]) + "\n"

        try:

            def _mime(path):
                mime = magic.Magic(mime=True)
                return mime.from_file(str(path))

            file_type = await asyncio.to_thread(_mime, path)
            result += kv("MIME type", file_type) + "\n"
        except Exception as e:
            result += line(f"Could not determine MIME type: {e}") + "\n"

        result += divider() + "\n"
        result += section("Internal Metadata (Hachoir)") + "\n"

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
                result += line("Hachoir could not parse this format.") + "\n"
                result += divider() + "\n"
                return result

            if text_data:
                for md_line in text_data:
                    result += line(md_line) + "\n"
            else:
                result += line("No internal metadata found in file.") + "\n"
        except Exception as e:
            result += line(f"Error reading metadata: {e}") + "\n"

        result += end_of("metadata") + "\n"
        result += divider() + "\n"

        return result

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
        with open(path, "rb") as f:
            content = f.read()

        # Matches printable ASCII characters: space (32) to ~ (126)
        # The {min_len,} ensures it only picks up sequences of at least X characters
        pattern = rb"[ -~]{" + str(min_len).encode() + rb",}"

        return [s.decode("ascii") for s in _re.findall(pattern, content)]
