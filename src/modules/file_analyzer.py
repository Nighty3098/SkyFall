import datetime
import hashlib
import os
import stat
import time
from pathlib import Path

import magic
import requests
from fake_useragent import UserAgent
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from loguru import logger


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

        self.result = ""
        self.virustotal_result = ""
        self.ua = UserAgent()

    def calculate_sha256(self, path):
        sha256_hash = hashlib.sha256()
        logger.debug("Calc file sha256...")
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def check_file_by_hash(self, path):
        url = f"https://www.virustotal.com/api/v3/files/{path}"
        response = requests.get(url, headers=self.HEADERS)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            logger.error(f"Error: {response.status_code}")
            return None

    def get_large_file_upload_url(self):
        url = "https://www.virustotal.com/api/v3/files/upload_url"
        response = requests.get(url, headers=self.HEADERS)

        if response.status_code == 200:
            return response.json()["data"]
        else:
            logger.error(
                f"Error while getting large file upload url: {response.status_code}"
            )
            print(response.text)
            return None

    def upload_and_scan_file(self, file_path):
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)

        logger.debug(f"File size: {file_size_mb:.2f} MB")

        if file_size_mb > 650:
            logger.error("Error: file size limit: 650 MB.")
            return None

        if file_size_mb > 32:
            logger.debug("File size > 32 MB...")
            upload_url = self.get_large_file_upload_url()
            if not upload_url:
                return None
        else:
            logger.debug("File size < 32 mb...")
            upload_url = "https://www.virustotal.com/api/v3/files"

        logger.debug("Starting upload to virustotal...")

        with open(file_path, "rb") as file_to_upload:
            files = {"file": (os.path.basename(file_path), file_to_upload)}
            response = requests.post(upload_url, headers=self.HEADERS, files=files)

        if response.status_code == 200:
            analysis_data = response.json()
            analysis_id = analysis_data["data"]["id"]
            return analysis_id
        else:
            logger.error(f"Error: {response.status_code}")
            logger.debug(response.text)
            return None

    def wait_for_analysis(self, analysis_id):
        url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"

        while True:
            response = requests.get(url, headers=self.HEADERS)
            if response.status_code == 200:
                status = response.json()["data"]["attributes"]["status"]
                if status == "completed":
                    logger.debug("Complete!")
                    return response.json()["data"]["attributes"]["results"]
                else:
                    time.sleep(30)
            else:
                logger.error(f"Error: {response.status_code}")
                return None

    def get_virustotal_info(self, stats):
        self.virustotal_result += "-" * 50 + "\n"
        self.virustotal_result += f"❌ Malicious: {stats.get('malicious', 0)}\n"
        self.virustotal_result += f"⚠️ Suspicious: {stats.get('suspicious', 0)}\n"
        self.virustotal_result += f"✅ Harmless: {stats.get('harmless', 0)}\n"
        self.virustotal_result += f"❔ Undetected: {stats.get('undetected', 0)}\n"
        self.virustotal_result += "-" * 50 + "\n"
        return self.virustotal_result

    def virustotal_analyze(self, path):
        if not os.path.exists(path):
            logger.debug(f"Error: File {path} not found.")
            return

        file_hash = self.calculate_sha256(path)
        logger.debug(f"SHA-256: {file_hash}")

        report = self.check_file_by_hash(file_hash)

        if report:
            logger.debug("Found in VirusTotal DB!")
            stats = report["data"]["attributes"]["last_analysis_stats"]
            return self.get_virustotal_info(stats)
        else:
            logger.debug("File not found in VirusTotal DB.")
            analysis_id = self.upload_and_scan_file(path)
            if analysis_id:
                results = self.wait_for_analysis(analysis_id)
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
                    return self.get_virustotal_info(stats)

    def get_file_type(self, path):
        path = Path(path)
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(str(path))
            return f"{file_type}\n"
        except Exception as e:
            return str(e)

    def _get_file_hashes(self, path: Path) -> dict:
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

    def check_tail_data(self, path):
        self.result += "-" * 50 + "\n"
        self.result += "Append / Tail Data:\n"

        with open(path, "rb") as f:
            data = f.read()

        png_eof = b"IEND\xaeB`\x82"
        idx = data.find(png_eof)

        if idx != -1:
            tail = data[idx + len(png_eof) :]
            if len(tail) > 0:
                self.result += (
                    f"Hidden data discovered after EOF! Size: {len(tail)} bytes.\n"
                )
        self.result += "Clean\n"
        self.result += "-" * 50 + "\n"

        return self.result

    def get_metadata(self, path):
        path = Path(path)
        self.result = ""

        if not path.exists():
            self.result += f"Error: File '{path}' not found."
            return self.result

        file_stat = path.stat()

        def _ts_to_str(ts):
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

        created_time = _ts_to_str(file_stat.st_ctime)
        modified_time = _ts_to_str(file_stat.st_mtime)
        accessed_time = _ts_to_str(file_stat.st_atime)

        file_permissions = stat.filemode(file_stat.st_mode)

        self.result += f"File: {path.name}\n"
        size_kb = file_stat.st_size / 1024
        self.result += f"Size: {size_kb:.2f} KB ({file_stat.st_size} bytes)\n"

        self.result += f"Created (OS): {created_time}\n"
        self.result += f"Modified (OS): {modified_time}\n"
        self.result += f"Accessed (OS): {accessed_time}\n"
        self.result += f"Permissions: {file_permissions}\n"

        hashes = self._get_file_hashes(path)
        self.result += f"MD5 Hash: {hashes['md5']}\n"
        self.result += f"SHA-256 Hash: {hashes['sha256']}\n"

        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(str(path))
            self.result += f"MIME type: {file_type}\n"
        except Exception as e:
            self.result += f"Could not determine MIME type: {e}\n"

        self.result += "-" * 50 + "\n"
        self.result += "Internal Metadata (Hachoir):\n"

        parser = createParser(str(path))
        if not parser:
            self.result += "  Hachoir could not parse this format.\n"
            self.result += "=" * 50 + "\n"
            return self.result

        try:
            metadata = extractMetadata(parser)
            if metadata:
                text_data = metadata.exportPlaintext()
                for line in text_data:
                    self.result += f"  {line}\n"
            else:
                self.result += "  No internal metadata found in file.\n"
        except Exception as e:
            self.result += f"  Error reading metadata: {e}\n"
        finally:
            parser.stream._input.close()

        return self.result
