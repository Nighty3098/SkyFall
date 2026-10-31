import asyncio
import io
import json
import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import src.skyfall_mcp_server as mcp_server
from src.modules import downloader, metadata_cleaner


class ArchiveCleaningSecurityTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def _zip(self, path, entries):
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in entries:
                archive.writestr(name, content)

    def test_zip_path_traversal_is_rejected_without_writing_outside(self):
        archive = self.root / "hostile.zip"
        outside = self.root / "escaped.txt"
        self._zip(archive, [("../escaped.txt", "pwned")])
        original = archive.read_bytes()

        self.assertFalse(metadata_cleaner.remove_metadata_from_zip(archive))
        self.assertFalse(outside.exists())
        self.assertEqual(archive.read_bytes(), original)

    def test_zip_symlink_member_is_rejected(self):
        archive = self.root / "symlink.zip"
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr(info, "../outside")

        self.assertFalse(metadata_cleaner.remove_metadata_from_zip(archive))

    def test_zip_expansion_limit_is_enforced_without_modifying_input(self):
        archive = self.root / "large.zip"
        self._zip(archive, [("large.bin", b"0123456789")])
        original = archive.read_bytes()

        with patch.object(metadata_cleaner, "MAX_ARCHIVE_SIZE", 5):
            self.assertFalse(metadata_cleaner.remove_metadata_from_zip(archive))

        self.assertEqual(archive.read_bytes(), original)

    def test_epub_path_traversal_is_rejected_without_modifying_input(self):
        archive = self.root / "hostile.epub"
        self._zip(archive, [("../escaped.opf", "<metadata>secret</metadata>")])
        original = archive.read_bytes()

        self.assertFalse(metadata_cleaner.remove_metadata_from_epub(archive))
        self.assertFalse((self.root / "escaped.opf").exists())
        self.assertEqual(archive.read_bytes(), original)

    def test_archive_replacement_failure_preserves_original(self):
        archive = self.root / "safe.zip"
        self._zip(archive, [("notes.txt", "safe content")])
        original = archive.read_bytes()

        with patch.object(metadata_cleaner.os, "replace", side_effect=OSError("disk")):
            self.assertFalse(metadata_cleaner.remove_metadata_from_zip(archive))

        self.assertEqual(archive.read_bytes(), original)
        self.assertEqual(list(self.root.glob(".safe.zip.*.tmp")), [])

    def test_valid_zip_entries_survive_metadata_cleaning(self):
        archive = self.root / "valid.zip"
        self._zip(archive, [("notes.txt", "safe content")])

        self.assertTrue(metadata_cleaner.remove_metadata_from_zip(archive))
        with zipfile.ZipFile(archive) as cleaned:
            self.assertEqual(cleaned.namelist(), ["notes.txt"])
            self.assertEqual(cleaned.read("notes.txt"), b"safe content")

    def test_epub_preserves_mimetype_first_and_uncompressed(self):
        archive = self.root / "valid.epub"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")
            output.writestr(
                "META-INF/book.opf",
                "<package><metadata><title>Private</title></metadata></package>",
            )

        self.assertTrue(metadata_cleaner.remove_metadata_from_epub(archive))
        with zipfile.ZipFile(archive) as cleaned:
            self.assertEqual(cleaned.namelist()[0], "mimetype")
            self.assertEqual(
                cleaned.getinfo("mimetype").compress_type, zipfile.ZIP_STORED
            )
            self.assertNotIn(b"Private", cleaned.read("META-INF/book.opf"))


class TarExtractionSecurityTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def _tar(self, path, members):
        with tarfile.open(path, "w:gz") as archive:
            for name, content in members:
                info = tarfile.TarInfo(name)
                if name.endswith("/"):
                    info.type = tarfile.DIRTYPE
                else:
                    info.size = len(content)
                archive.addfile(info, io.BytesIO(content))

    def test_tar_traversal_is_rejected(self):
        archive = self.root / "hostile.tar.gz"
        self._tar(archive, [("repo/../../escaped.txt", b"no")])

        with self.assertRaises(ValueError):
            downloader.DownloadManager._extract_archive(archive, self.root / "repo")
        self.assertFalse((self.root / "escaped.txt").exists())

    def test_tar_extracts_only_one_safe_root_directory(self):
        archive = self.root / "safe.tar.gz"
        self._tar(archive, [("repo/", b""), ("repo/file.txt", b"content")])

        downloader.DownloadManager._extract_archive(archive, self.root / "checkout")
        self.assertEqual(
            (self.root / "checkout" / "file.txt").read_bytes(),
            b"content",
        )


class CaseLookupSecurityTest(unittest.TestCase):
    def test_case_lookup_rejects_traversal_absolute_paths_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = root / ".skyfall" / "data"
            (cases / "valid" / "evidence").mkdir(parents=True)
            (cases / "valid" / "evidence" / "file.txt").write_text("ok")
            outside = root / "outside"
            (outside / "evidence").mkdir(parents=True)
            (outside / "evidence" / "secret.txt").write_text("secret")
            (cases / "escape").symlink_to(outside, target_is_directory=True)

            with patch.object(Path, "home", return_value=root):
                traversal = json.loads(mcp_server.skyfall_case_get("../outside"))
                absolute = json.loads(mcp_server.skyfall_case_get(str(outside)))
                symlink = json.loads(mcp_server.skyfall_case_get("escape"))
                valid = json.loads(mcp_server.skyfall_case_get("valid"))

        self.assertIn("error", traversal)
        self.assertIn("error", absolute)
        self.assertIn("error", symlink)
        self.assertEqual(valid["categories"]["evidence"][0]["name"], "file.txt")


class DownloadBoundarySecurityTest(unittest.TestCase):
    def test_url_validation_rejects_private_hosts_and_non_http_schemes(self):
        for url in (
            "http://127.0.0.1/private",
            "http://[::1]/private",
            "http://localhost/private",
            "file:///etc/passwd",
            "http://user:pass@example.com/file",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                downloader._validate_http_url(url)

    def test_resolver_rejects_private_dns_results(self):
        async def run():
            resolver = downloader._PublicResolver()
            resolver._resolver.resolve = lambda *args: _resolved_private_address()
            try:
                with self.assertRaises(OSError):
                    await resolver.resolve("public.example")
            finally:
                await resolver.close()

        async def _resolved_private_address():
            return [
                {
                    "hostname": "public.example",
                    "host": "10.0.0.7",
                    "port": 80,
                    "family": 2,
                    "proto": 0,
                    "flags": 0,
                }
            ]

        asyncio.run(run())

    def test_numeric_loopback_dns_result_is_rejected(self):
        async def run():
            resolver = downloader._PublicResolver()
            resolver._resolver.resolve = lambda *args: _resolved_loopback()
            try:
                with self.assertRaises(OSError):
                    await resolver.resolve("2130706433")
            finally:
                await resolver.close()

        async def _resolved_loopback():
            return [
                {
                    "hostname": "2130706433",
                    "host": "127.0.0.1",
                    "port": 80,
                    "family": 2,
                    "proto": 0,
                    "flags": 0,
                }
            ]

        asyncio.run(run())

    def test_download_routing_does_not_match_github_inside_untrusted_host(self):
        self.assertEqual(
            downloader.DownloadManager._detect(
                "https://github.com.attacker.example/owner/repo"
            ),
            "file",
        )
        self.assertEqual(
            downloader.DownloadManager._detect("https://github.com/owner/repo"),
            "github",
        )
        self.assertEqual(
            downloader.DownloadManager._detect("ssh://internal.example/repo.git"),
            "file",
        )

    def test_redirect_to_private_address_is_rejected_before_following(self):
        async def run():
            calls = []

            class Response:
                status = 302
                headers = {"Location": "http://127.0.0.1/private"}

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_args):
                    return False

            class Session:
                def __init__(self, **_kwargs):
                    pass

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_args):
                    return False

                def get(self, url, **_kwargs):
                    calls.append(url)
                    return Response()

            with (
                tempfile.TemporaryDirectory() as temporary,
                patch.object(downloader.aiohttp, "TCPConnector"),
                patch.object(downloader.aiohttp, "ClientSession", Session),
            ):
                with self.assertRaises(RuntimeError):
                    await downloader.DownloadManager()._download_file(
                        "https://8.8.8.8/file.bin",
                        Path(temporary),
                        None,
                        lambda _message: None,
                        lambda *_args: None,
                    )

            self.assertEqual(calls, ["https://8.8.8.8/file.bin"])

        asyncio.run(run())

    def test_failed_download_does_not_replace_existing_file(self):
        async def run():
            with tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary)
                target = destination / "artifact.bin"
                target.write_bytes(b"original")

                class Content:
                    async def iter_chunked(self, _size):
                        yield b"partial"
                        raise OSError("connection interrupted")

                class Response:
                    status = 200
                    headers = {
                        "Content-Disposition": 'attachment; filename="artifact.bin"'
                    }
                    content = Content()

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *_args):
                        return False

                    def raise_for_status(self):
                        pass

                class Session:
                    def __init__(self, **_kwargs):
                        pass

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *_args):
                        return False

                    def get(self, *_args, **_kwargs):
                        return Response()

                with (
                    patch.object(downloader.aiohttp, "TCPConnector"),
                    patch.object(downloader.aiohttp, "ClientSession", Session),
                ):
                    with self.assertRaises(RuntimeError):
                        await downloader.DownloadManager()._download_file(
                            "https://8.8.8.8/artifact.bin",
                            destination,
                            None,
                            lambda _message: None,
                            lambda *_args: None,
                        )

                self.assertEqual(target.read_bytes(), b"original")
                self.assertEqual(list(destination.glob("*.part")), [])
                self.assertEqual(list(destination.glob(".artifact.bin.*.part")), [])

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
