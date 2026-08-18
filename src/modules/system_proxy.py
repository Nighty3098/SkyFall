import os
import shutil
import subprocess
import sys

from loguru import logger


def _clean_proxy(value: str) -> str | None:
    value = value.strip().strip('"').strip("'")
    if not value:
        return None
    if "://" not in value:
        value = f"http://{value}"
    return value


def _run_command(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3)
        if result.returncode != 0:
            return ""
        return result.stdout
    except (subprocess.SubprocessError, OSError):
        return ""


def _gsettings_get(schema: str, key: str) -> str:
    return _run_command(["gsettings", "get", schema, key]).strip().strip("'")


def _get_linux_proxy() -> str | None:
    for key in (
        "https_proxy",
        "HTTPS_PROXY",
        "http_proxy",
        "HTTP_PROXY",
        "all_proxy",
        "ALL_PROXY",
    ):
        value = os.environ.get(key)
        if value:
            proxy = _clean_proxy(value)
            if proxy:
                return proxy

    if not shutil.which("gsettings"):
        return None

    if _gsettings_get("org.gnome.system.proxy", "mode") != "manual":
        return None

    host = _gsettings_get("org.gnome.system.proxy.https", "host")
    port = _gsettings_get("org.gnome.system.proxy.https", "port")
    if not host:
        host = _gsettings_get("org.gnome.system.proxy.http", "host")
        port = _gsettings_get("org.gnome.system.proxy.http", "port")
    if not host:
        host = _gsettings_get("org.gnome.system.proxy.socks", "host")
        port = _gsettings_get("org.gnome.system.proxy.socks", "port")
        if host:
            return f"socks5://{host}:{port or '1080'}"
        return None

    scheme = "http"
    user = ""
    password = ""
    if _gsettings_get("org.gnome.system.proxy.http", "use-authentication") == "true":
        user = _gsettings_get("org.gnome.system.proxy.http", "authentication-user")
        password = _gsettings_get(
            "org.gnome.system.proxy.http", "authentication-password"
        )
    credentials = f"{user}:{password}@" if user else ""
    return f"{scheme}://{credentials}{host}:{port or '80'}"


def _get_macos_proxy() -> str | None:
    output = _run_command(["scutil", "--proxy"])
    if not output:
        return None

    values: dict[str, str] = {}
    for line in output.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            values[key.strip()] = value.strip()

    if values.get("HTTPSProxyEnable") == "1" and values.get("HTTPSProxy"):
        return f"http://{values['HTTPSProxy']}:{values.get('HTTPSPort', '80')}"
    if values.get("HTTPProxyEnable") == "1" and values.get("HTTPProxy"):
        return f"http://{values['HTTPProxy']}:{values.get('HTTPPort', '80')}"
    if values.get("SOCKSEnable") == "1" and values.get("SOCKSProxy"):
        return f"socks5://{values['SOCKSProxy']}:{values.get('SOCKSPort', '1080')}"
    return None


def _get_windows_proxy() -> str | None:
    try:
        import winreg
    except ImportError:
        return None

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not proxy_enable:
                return None
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except OSError:
        return None

    if not proxy_server:
        return None

    if "=" in proxy_server:
        entries = {
            part.split("=", 1)[0].strip(): part.split("=", 1)[1].strip()
            for part in proxy_server.split(";")
            if "=" in part
        }
        for protocol in ("https", "http", "socks"):
            address = entries.get(protocol)
            if address:
                scheme = "socks5" if protocol == "socks" else protocol
                return f"{scheme}://{address}"
        return None

    return _clean_proxy(proxy_server)


def get_system_proxy() -> str | None:
    if sys.platform == "win32":
        proxy = _get_windows_proxy()
    elif sys.platform == "darwin":
        proxy = _get_macos_proxy()
    else:
        proxy = _get_linux_proxy()
    logger.debug("get_system_proxy: proxy={}", proxy)
    return proxy
