import asyncio
import ipaddress
import os
import re
import shutil
import tarfile
import tempfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote, urljoin, urlsplit

import aiohttp
from aiohttp.resolver import DefaultResolver
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
MAX_TAR_MEMBERS = 100_000
MAX_TAR_EXPANDED_SIZE = 1_073_741_824
MAX_REDIRECTS = 10


def _validate_http_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise ValueError("Invalid download URL.") from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(
            "Only public HTTP(S) URLs without embedded credentials are allowed."
        )

    host = hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Downloads to local hosts are not allowed.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return url
    if not address.is_global:
        raise ValueError("Downloads to non-public IP addresses are not allowed.")
    return url


class _PublicResolver(aiohttp.abc.AbstractResolver):
    def __init__(self):
        self._resolver = DefaultResolver()

    async def resolve(self, host, port=0, family=0):
        try:
            literal = ipaddress.ip_address(host.rstrip("."))
        except ValueError:
            literal = None
        if literal is not None and not literal.is_global:
            raise OSError("Downloads to non-public IP addresses are not allowed.")

        addresses = await self._resolver.resolve(host, port, family)
        if not addresses:
            raise OSError("The download host did not resolve to an address.")
        for result in addresses:
            resolved_ip = ipaddress.ip_address(result["host"])
            if not resolved_ip.is_global:
                raise OSError("Downloads to non-public IP addresses are not allowed.")
        return addresses

    async def close(self):
        await self._resolver.close()


def _safe_tar_members(tar):
    members = tar.getmembers()
    if len(members) > MAX_TAR_MEMBERS:
        raise ValueError("Archive contains too many entries.")

    total_size = 0
    validated = []
    roots = set()
    for member in members:
        name = member.name
        path = PurePosixPath(name)
        windows_path = PureWindowsPath(name)
        if (
            not name
            or "\x00" in name
            or ":" in name
            or "\\" in name
            or path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or any(part in {"", ".", ".."} for part in name.rstrip("/").split("/"))
        ):
            raise ValueError(f"Unsafe archive member path: {name!r}")
        if not (member.isdir() or member.isfile()):
            raise ValueError(f"Unsupported archive member type: {name!r}")
        parts = path.parts
        roots.add(parts[0])
        if member.isfile():
            total_size += member.size
            if total_size > MAX_TAR_EXPANDED_SIZE:
                raise ValueError("Archive exceeds the maximum expanded size.")
        validated.append((member, parts))

    if len(roots) != 1:
        raise ValueError("Repository archive must contain one top-level directory.")
    root_name = next(iter(roots))
    root_member = next(
        (member for member, parts in validated if len(parts) == 1 and member.isdir()),
        None,
    )
    if root_member is None:
        raise ValueError("Repository archive is missing its top-level directory.")
    return root_name, validated


def _is_github_git_url(url: str) -> bool:
    if re.fullmatch(r"git@github\.com:[^/]+/[^/]+(?:\.git)?", url):
        return True
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return parsed.scheme.lower() in {"https", "ssh"} and (
        parsed.hostname or ""
    ).lower() in {"github.com", "www.github.com"}


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
        if host in YOUTUBE_HOSTS and urlsplit(url).scheme.lower() in {
            "http",
            "https",
        }:
            return "youtube"
        if host in {"github.com", "www.github.com"} and urlsplit(
            url
        ).scheme.lower() in {"http", "https"}:
            return "github"
        if _is_github_git_url(url):
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
        allow_proxy: bool = False,
    ) -> str:
        url = _validate_http_url(url)
        log(f"Downloading: {url}")

        if proxy_url:
            hostname = (urlsplit(url).hostname or "").lower()
            if not allow_proxy or hostname not in {
                "github.com",
                "codeload.github.com",
            }:
                raise ValueError(
                    "Proxies are not supported for arbitrary URLs because their "
                    "destination cannot be safely verified."
                )
            connector = ProxyConnector.from_url(proxy_url, rdns=False)
        else:
            connector = aiohttp.TCPConnector(
                resolver=_PublicResolver(),
                use_dns_cache=False,
            )
        timeout = aiohttp.ClientTimeout(connect=30, total=300)
        temporary_path = None
        try:
            async with aiohttp.ClientSession(
                connector=connector, timeout=timeout
            ) as session:
                current_url = url
                for redirect_count in range(MAX_REDIRECTS + 1):
                    _validate_http_url(current_url)
                    if proxy_url:
                        current_host = (urlsplit(current_url).hostname or "").lower()
                        if current_host not in {"github.com", "codeload.github.com"}:
                            raise ValueError(
                                "Proxy redirects outside github.com are not allowed."
                            )
                    async with session.get(
                        current_url, allow_redirects=False
                    ) as response:
                        if response.status in {301, 302, 303, 307, 308}:
                            location = response.headers.get("Location")
                            if not location or redirect_count == MAX_REDIRECTS:
                                raise ValueError("Invalid or excessive redirect chain.")
                            current_url = _validate_http_url(
                                urljoin(current_url, location)
                            )
                            continue
                        response.raise_for_status()
                        filename = _sanitize_filename(
                            name or _filename_from_response(current_url, response)
                        )
                        filepath = dest_dir / filename
                        total = int(response.headers.get("Content-Length", 0)) or None
                        downloaded = 0
                        with tempfile.NamedTemporaryFile(
                            mode="wb",
                            prefix=f".{filename}.",
                            suffix=".part",
                            dir=dest_dir,
                            delete=False,
                        ) as file:
                            temporary_path = Path(file.name)
                            async for chunk in response.content.iter_chunked(
                                128 * 1024
                            ):
                                file.write(chunk)
                                downloaded += len(chunk)
                                percent = (
                                    int(downloaded * 100 / total) if total else None
                                )
                                progress(percent, downloaded, total)
                            file.flush()
                            os.fsync(file.fileno())
                        break
                else:
                    raise ValueError("Too many redirects.")

                os.link(temporary_path, filepath)
                temporary_path.unlink()
                temporary_path = None
            log(f"Saved: {filepath} ({downloaded} bytes)")
            return str(filepath)
        except Exception as e:
            logger.error("download_file: {}", e)
            raise RuntimeError(f"Download failed: {e}") from e
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    async def _download_youtube(
        self,
        url: str,
        dest_dir: Path,
        proxy_url: str | None,
        log: log_cb_t,
        progress: progress_cb_t,
    ) -> str:
        _validate_http_url(url)
        if (urlsplit(url).hostname or "").lower() not in YOUTUBE_HOSTS:
            raise ValueError("Only supported YouTube hosts can use this downloader.")
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
            raise ValueError("Expected a direct GitHub repository URL.")

        owner, repo = match.groups()
        archive_url = f"https://github.com/{owner}/{repo}/archive/HEAD.tar.gz"
        log(f"Downloading GitHub repo archive: {owner}/{repo}")

        archive = dest_dir / f"{repo}.tar.gz"
        await self._download_file(
            archive_url,
            dest_dir,
            proxy_url,
            log,
            progress,
            name=archive.name,
            allow_proxy=True,
        )

        repo_dir = dest_dir / repo
        await asyncio.to_thread(self._extract_archive, archive, repo_dir)

        log(f"Saved: {repo_dir}")
        return str(repo_dir)

    @staticmethod
    def _extract_archive(archive: Path, repo_dir: Path):
        try:
            with tarfile.open(archive, "r:gz") as tar:
                top_dir, members = _safe_tar_members(tar)
                with tempfile.TemporaryDirectory(
                    prefix=".skyfall_github_", dir=archive.parent
                ) as temp_dir:
                    extraction_root = Path(temp_dir).resolve()
                    for member, parts in members:
                        target = extraction_root.joinpath(*parts)
                        if not target.resolve().is_relative_to(extraction_root):
                            raise ValueError(
                                f"Archive member escapes extraction directory: "
                                f"{member.name!r}"
                            )
                        if member.isdir():
                            target.mkdir(parents=True, exist_ok=True)
                            continue
                        target.parent.mkdir(parents=True, exist_ok=True)
                        source = tar.extractfile(member)
                        if source is None:
                            raise ValueError(
                                f"Could not read archive member: {member.name!r}"
                            )
                        written = 0
                        with source, target.open("xb") as output:
                            while chunk := source.read(1024 * 1024):
                                written += len(chunk)
                                if written > member.size:
                                    raise ValueError(
                                        f"Archive member exceeds its declared size: "
                                        f"{member.name!r}"
                                    )
                                output.write(chunk)
                        if written != member.size:
                            raise ValueError(
                                f"Archive member has an unexpected size: "
                                f"{member.name!r}"
                            )
                        safe_mode = 0o644 | (member.mode & 0o111)
                        os.chmod(target, safe_mode)

                    source_dir = extraction_root / top_dir
                    if not source_dir.is_dir():
                        raise ValueError("Repository archive root is not a directory.")
                    if repo_dir.is_symlink():
                        raise ValueError(
                            "Repository destination must not be a symlink."
                        )
                    if repo_dir.exists():
                        if not repo_dir.is_dir() or any(
                            path.is_symlink() for path in repo_dir.rglob("*")
                        ):
                            raise ValueError(
                                "Repository destination contains unsupported entries."
                            )
                        shutil.copytree(source_dir, repo_dir, dirs_exist_ok=True)
                    else:
                        os.replace(source_dir, repo_dir)
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
        if not _is_github_git_url(url):
            raise ValueError("Git clone is restricted to GitHub repository URLs.")
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
