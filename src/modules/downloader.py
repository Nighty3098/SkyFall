import asyncio
import os
import re
import shutil
import tarfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote, urlsplit

import aiohttp
from aiohttp_socks import ProxyConnector
from loguru import logger

log_cb_t = Callable[[str], None]
progress_cb_t = Callable[[int | None, int, int | None], None]

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def normalize_proxy(proxy: str) -> str:
    proxy = proxy.strip()
    if "://" not in proxy:
        proxy = f"http://{proxy}"
    return proxy


def _filename_from_response(url: str, response) -> str:
    disposition = response.headers.get("Content-Disposition", "")
    filename_match = re.search(r"filename\*=UTF-8\'\'([^;]+)", disposition)
    if filename_match:
        return unquote(filename_match.group(1))
    filename_match = re.search(r'filename="?([^";]+)"?', disposition)
    if filename_match:
        return filename_match.group(1).strip()
    return _filename_from_url(url)


def _filename_from_url(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    name = unquote(Path(path).name)
    if not name or name in {".", "/"}:
        name = "download"
    return name


def _sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name).strip()
    return name or "download"


def _repo_name_from_url(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    name = Path(path).name
    return name.removesuffix(".git") or "repository"


class _YtDlpLogger:
    def __init__(self, log_callback: log_cb_t):
        self._log = log_callback

    def debug(self, msg):
        pass

    def info(self, msg):
        self._log(msg)

    def warning(self, msg):
        self._log(f"Warning: {msg}")

    def error(self, msg):
        self._log(f"Error: {msg}")


class DownloadManager:
    def __init__(self):
        logger.debug("Init: DownloadManager")

    async def download(
        self,
        url: str,
        dest_dir: str,
        proxy: str | None = None,
        log_callback: log_cb_t | None = None,
        progress_callback: progress_cb_t | None = None,
    ) -> str:
        url = url.strip()
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

        log = log_callback or (lambda msg: None)
        progress = progress_callback or (lambda *args: None)

        proxy_url = normalize_proxy(proxy) if proxy else None

        logger.debug(
            "download: url={}, dest={}, proxy={}", url, dest_dir, bool(proxy_url)
        )
        if proxy_url:
            log(f"Using proxy: {proxy_url}")

        kind = self._detect(url)
        logger.debug("download: kind={}", kind)

        if kind == "youtube":
            return await self._download_youtube(url, dest, proxy_url, log, progress)
        if kind == "github":
            return await self._download_github(url, dest, proxy_url, log, progress)
        if kind == "git":
            return await self._git_clone(url, dest, proxy_url, log, progress)
        return await self._download_file(url, dest, proxy_url, log, progress)

    @staticmethod
    def _detect(url: str) -> str:
        host = (urlsplit(url).hostname or "").lower()
        if host in YOUTUBE_HOSTS:
            return "youtube"
        if (
            url.startswith("git@")
            or url.startswith("git://")
            or url.startswith("ssh://")
        ):
            return "git"
        if "github.com" in url:
            return "github"
        if url.rstrip("/").endswith(".git"):
            return "git"
        return "file"

    async def _download_file(
        self,
        url: str,
        dest_dir: Path,
        proxy_url: str | None,
        log: log_cb_t,
        progress: progress_cb_t,
        name: str | None = None,
    ) -> str:
        log(f"Downloading: {url}")

        connector = ProxyConnector.from_url(proxy_url) if proxy_url else None
        timeout = aiohttp.ClientTimeout(connect=30, total=None)
        try:
            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout
            ) as session:
                async with session.get(url, allow_redirects=True) as response:
                    response.raise_for_status()
                    filename = name or _sanitize_filename(
                        _filename_from_response(url, response)
                    )
                    filepath = dest_dir / filename
                    total = int(response.headers.get("Content-Length", 0)) or None
                    downloaded = 0
                    with open(filepath, "wb") as file:
                        async for chunk in response.content.iter_chunked(128 * 1024):
                            file.write(chunk)
                            downloaded += len(chunk)
                            percent = int(downloaded * 100 / total) if total else None
                            progress(percent, downloaded, total)
            log(f"Saved: {filepath} ({downloaded} bytes)")
            return str(filepath)
        except Exception as e:
            logger.error("download_file: {}", e)
            raise RuntimeError(f"Download failed: {e}") from e

    async def _download_youtube(
        self,
        url: str,
        dest_dir: Path,
        proxy_url: str | None,
        log: log_cb_t,
        progress: progress_cb_t,
    ) -> str:
        try:
            import yt_dlp
        except ImportError as e:
            raise RuntimeError(
                "yt-dlp is not installed. Run: pip install yt-dlp"
            ) from e

        log(f"Fetching YouTube video: {url}")
        downloaded_files: list[str] = []

        def hook(data):
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                percent = int(data["downloaded_bytes"] * 100 / total) if total else None
                progress(percent, data["downloaded_bytes"], total)
            elif data.get("status") == "finished":
                filename = data.get("filename")
                if filename:
                    downloaded_files.append(filename)
                    log(f"Downloaded: {Path(filename).name}")

        options = {
            "outtmpl": str(dest_dir / "%(title).200B [%(id)s].%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [hook],
            "logger": _YtDlpLogger(log),
        }
        if proxy_url:
            options["proxy"] = proxy_url

        def _run():
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
            return info

        try:
            await asyncio.to_thread(_run)
        except Exception as e:
            logger.error("download_youtube: {}", e)
            raise RuntimeError(f"YouTube download failed: {e}") from e

        if not downloaded_files:
            raise RuntimeError("YouTube download failed: no files produced")

        log(f"Saved: {downloaded_files[-1]}")
        return downloaded_files[-1]

    async def _download_github(
        self,
        url: str,
        dest_dir: Path,
        proxy_url: str | None,
        log: log_cb_t,
        progress: progress_cb_t,
    ) -> str:
        match = re.match(
            r"https?://(?:www\.)?github\.com/([^/]+)/([^/?#]+?)(?:\.git)?/?$",
            url,
        )
        if not match:
            log("Not a direct GitHub repo URL, trying git clone")
            return await self._git_clone(url, dest_dir, proxy_url, log, progress)

        owner, repo = match.groups()
        archive_url = f"https://github.com/{owner}/{repo}/archive/HEAD.tar.gz"
        log(f"Downloading GitHub repo archive: {owner}/{repo}")

        archive = dest_dir / f"{repo}.tar.gz"
        await self._download_file(
            archive_url, dest_dir, proxy_url, log, progress, name=archive.name
        )

        repo_dir = dest_dir / repo
        await asyncio.to_thread(self._extract_archive, archive, repo_dir)

        log(f"Saved: {repo_dir}")
        return str(repo_dir)

    @staticmethod
    def _extract_archive(archive: Path, repo_dir: Path):
        try:
            with tarfile.open(archive, "r:gz") as tar:
                top_dir = tar.getnames()[0].split("/", 1)[0]
                tar.extractall(archive.parent)
            source = archive.parent / top_dir
            if repo_dir.exists():
                shutil.copytree(source, repo_dir, dirs_exist_ok=True)
                shutil.rmtree(source)
            else:
                shutil.move(str(source), str(repo_dir))
        finally:
            if archive.exists():
                archive.unlink()

    async def _git_clone(
        self,
        url: str,
        dest_dir: Path,
        proxy_url: str | None,
        log: log_cb_t,
        progress: progress_cb_t,
    ) -> str:
        log(f"Cloning repository: {url}")
        progress(None, 0, None)

        env = os.environ.copy()
        if proxy_url:
            env["http_proxy"] = proxy_url
            env["https_proxy"] = proxy_url
            env["all_proxy"] = proxy_url

        target = dest_dir / _repo_name_from_url(url)
        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            "1",
            url,
            str(target),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = stderr.decode(errors="ignore").strip()
            logger.error("git_clone: {}", message)
            raise RuntimeError(f"git clone failed: {message}")

        for line in stdout.decode(errors="ignore").splitlines():
            if line.strip():
                log(line.strip())
        for line in stderr.decode(errors="ignore").splitlines():
            if line.strip():
                log(line.strip())

        log(f"Saved: {target}")
        return str(target)
