import datetime
import hashlib
import stat
from pathlib import Path

import magic
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser


class FileAnalyzer:
    def __init__(self):
        self.result = ""

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
