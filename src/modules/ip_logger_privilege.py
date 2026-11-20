"""Native elevation for IP LOGGER listeners on privileged ports.

Ports below 1024 cannot be bound by an unprivileged user on Unix.  Instead of
asking for a password inside the Qt window, SkyFall uses the platform's native
prompt and starts a tiny, elevated TCP forwarder:

* Linux   — ``pkexec`` (PolicyKit dialog)
* Windows — ``ShellExecuteW(..., "runas", ...)`` (UAC dialog)
* macOS   — ``osascript ... with administrator privileges`` (system dialog)

The forwarder binds the low port and relays traffic to the aiohttp site that
the application keeps on an ephemeral loopback port, so the main process never
needs to run as root.
"""

from __future__ import annotations

import asyncio
import ctypes
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PRIVILEGED_PORT = 1024

FORWARDER_SCRIPT = Path(__file__).with_name("ip_logger_forwarder.py")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def needs_elevation(port: int) -> bool:
    """Whether ``port`` requires an elevated helper for the current user."""
    if not 0 < port < PRIVILEGED_PORT:
        return False
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return False
    return True


def linux_command(
    args: list[str], python: str = "", pkexec: str = "pkexec"
) -> list[str]:
    """Build the ``pkexec`` command that launches the forwarder as root."""
    return [pkexec, python or sys.executable, *args]


def macos_script(args: list[str], python: str = "") -> str:
    """Build the AppleScript that launches the forwarder with admin rights."""
    directory = shlex.quote(str(PROJECT_ROOT))
    command = shlex.join([python or sys.executable, *args])
    shell_command = f"cd {directory} && {command}"
    escaped = shell_command.replace("\\", "\\\\").replace('"', '\\"')
    return f'do shell script "{escaped}" with administrator privileges'


def windows_forwarder(exe: str = "") -> str:
    """Prefer the windowless interpreter so UAC does not open a console."""
    path = Path(exe or sys.executable)
    if path.name.lower() == "python.exe":
        windowless = path.with_name("pythonw.exe")
        if windowless.is_file():
            return str(windowless)
    return str(path)


class PrivilegedForwarder:
    """Elevated low-port listener, started and stopped from the asyncio loop."""

    def __init__(self, listen_port: int, target_port: int):
        self.listen_port = listen_port
        self.target_port = target_port
        self._temp: tempfile.TemporaryDirectory[str] | None = None
        self._process: asyncio.subprocess.Process | None = None
        self._stop_file: Path | None = None
        self._log_file: Path | None = None

    @property
    def is_running(self) -> bool:
        return self._temp is not None

    async def start(self) -> None:
        if not needs_elevation(self.listen_port):
            return

        self._temp = tempfile.TemporaryDirectory(prefix="skyfall_iplogger_")
        root = Path(self._temp.name)
        self._stop_file = root / "stop"
        self._log_file = root / "error.log"

        args = [
            str(FORWARDER_SCRIPT),
            str(self.listen_port),
            str(self.target_port),
            str(self._stop_file),
            str(self._log_file),
        ]
        try:
            await self._launch(args)
            await self._wait_until_listening()
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        if self._temp is None:
            return
        if self._stop_file is not None:
            try:
                self._stop_file.write_text("stop", encoding="ascii")
            except OSError:
                pass
        process, self._process = self._process, None
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=3)
            except TimeoutError:
                process.kill()
                await process.wait()
        temp, self._temp = self._temp, None
        temp.cleanup()
        self._stop_file = None
        self._log_file = None

    async def _launch(self, args: list[str]) -> None:
        if sys.platform == "win32":
            await self._launch_windows(args)
        elif sys.platform == "darwin":
            await self._launch_macos(args)
        else:
            await self._launch_linux(args)

    async def _launch_linux(self, args: list[str]) -> None:
        pkexec = shutil.which("pkexec")
        if pkexec is None:
            raise RuntimeError(
                "Ports below 1024 need pkexec (polkit) to request admin rights."
            )
        command = linux_command(args, pkexec=pkexec)
        assert self._log_file is not None
        with self._log_file.open("ab") as error_log:
            self._process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=error_log,
                start_new_session=True,
            )

    async def _launch_macos(self, args: list[str]) -> None:
        osascript = shutil.which("osascript")
        if osascript is None:
            raise RuntimeError("osascript is required to request admin rights.")
        script = macos_script(args)
        assert self._log_file is not None
        with self._log_file.open("ab") as error_log:
            self._process = await asyncio.create_subprocess_exec(
                osascript,
                "-e",
                script,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=error_log,
                start_new_session=True,
            )

    async def _launch_windows(self, args: list[str]) -> None:
        parameters = subprocess.list2cmdline(args)
        executable = windows_forwarder()

        def runas() -> int:
            return int(
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    executable,
                    parameters,
                    str(PROJECT_ROOT),
                    1,
                )
            )

        result = await asyncio.to_thread(runas)
        if result <= 32:
            raise OSError(result, "UAC elevation was cancelled or denied")

    async def _wait_until_listening(self) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 20
        while loop.time() < deadline:
            message = self._failure_log()
            if message:
                raise RuntimeError(message)
            if self._process is not None and self._process.returncode is not None:
                raise RuntimeError(
                    "Admin authorization was cancelled or the elevated "
                    "listener failed to start "
                    f"(exit code {self._process.returncode})."
                )
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", self.listen_port),
                    timeout=0.5,
                )
                writer.close()
                return
            except (OSError, TimeoutError):
                await asyncio.sleep(0.2)
        raise RuntimeError(self._failure_log("Timed out waiting for the admin prompt."))

    def _failure_log(self, fallback: str = "") -> str:
        if self._log_file is None:
            return fallback
        try:
            text = self._log_file.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return fallback
        if not text:
            return fallback
        detail = text[-600:]
        return f"Privileged listener failed:\n{detail}"
