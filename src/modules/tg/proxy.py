import os
import random
import socket
from typing import Optional
from urllib.parse import parse_qs, urlparse


def parse_proxies_text(text: str) -> list[tuple]:
    """Parse proxy text into a list of proxy tuples.

    Supports the same formats as load_proxies() but operates on a string
    directly instead of a file path.

    Returns:
        List[Tuple]: List of tuples (type, host, port, user, password).
    """
    proxies = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "t.me/proxy" in line or "tg://proxy" in line:
            try:
                if "t.me/proxy" in line:
                    line = line.replace("https://t.me/proxy", "tg://proxy")
                parsed = urlparse(line)
                params = parse_qs(parsed.query)
                server = params.get("server", [""])[0]
                port = int(params.get("port", ["443"])[0])
                secret = params.get("secret", [""])[0]
                if server and secret:
                    proxies.append(("mtproto", server, port, secret, None))
                continue
            except:
                continue

        proxy_type = "socks5"
        connection_string = line

        if "://" in line:
            proxy_type, connection_string = line.split("://", 1)
            proxy_type = proxy_type.lower()

        if proxy_type == "mtproto":
            if "@" in connection_string:
                secret, host_port = connection_string.split("@")
                host, port = (
                    host_port.split(":") if ":" in host_port else (host_port, 443)
                )
                proxies.append(("mtproto", host, int(port), secret, None))
            else:
                parts = connection_string.split(":")
                if len(parts) >= 3:
                    proxies.append(
                        ("mtproto", parts[0], int(parts[1]), parts[2], None)
                    )
                elif len(parts) == 2:
                    proxies.append(("mtproto", parts[0], int(parts[1]), "", None))
            continue

        if "@" in connection_string:
            auth, host_port = connection_string.split("@")
            user, password = auth.split(":", 1) if ":" in auth else (auth, "")
            host, port = (
                host_port.split(":") if ":" in host_port else (host_port, 1080)
            )
            proxies.append((proxy_type, host, int(port), user, password))
        else:
            if ":" in connection_string:
                host, port = connection_string.split(":")
            else:
                host, port = connection_string, 1080
            proxies.append((proxy_type, host, int(port), None, None))

    return proxies


def load_proxies(proxies_file: str = "resources/proxies.txt") -> list[tuple]:
    """Load proxies from a file with support for multiple formats.

    Supports:
    - MTProto proxies (t.me/proxy links or host:port:secret format)
    - SOCKS5/SOCKS4/HTTP proxies with optional authentication
    - Proxies with or without protocol prefix (e.g., socks5://)

    Args:
        proxies_file (str): Path to the proxy list file.

    Returns:
        List[Tuple]: List of tuples (type, host, port, user, password).
    """
    if not os.path.exists(proxies_file):
        return []

    with open(proxies_file, encoding="utf-8") as f:
        return parse_proxies_text(f.read())


def prepare_mtproto_proxy(proxy_tuple: tuple) -> tuple:
    """Normalize an MTProto proxy tuple.

    Ensures the secret is a hex string and formats the tuple correctly.

    Args:
        proxy_tuple: Proxy tuple to normalize.

    Returns:
        tuple: Normalized proxy tuple.
    """
    if not proxy_tuple or proxy_tuple[0] != "mtproto":
        return proxy_tuple
    ptype, host, port, secret, *_ = proxy_tuple
    if isinstance(secret, bytes):
        secret = secret.hex()
    return (ptype, host, port, secret, None)


def test_proxy(proxy) -> bool:
    """Test if a proxy is reachable by attempting a TCP connection.

    Args:
        proxy: Proxy tuple (type, host, port, ...) or dict with addr/host and port.

    Returns:
        bool: True if connection succeeds, False otherwise.
    """
    try:
        if isinstance(proxy, dict):
            addr = proxy.get("addr") or proxy.get("host")
            port = proxy.get("port")
        else:
            _, addr, port, *_ = proxy
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((str(addr), int(port)))
        sock.close()
        return True
    except:
        return False


def get_working_proxy(proxies: list, max_attempts: int = 30) -> Optional:
    """Find a working proxy from a list by testing connections.

    Tests MTProto proxies first, then falls back to SOCKS proxies.

    Args:
        proxies (List): List of proxy tuples.
        max_attempts (int): Maximum number of tests per proxy type.

    Returns:
        A working proxy tuple or None if no working proxy found.
    """
    if not proxies:
        return None

    mtproto_proxies = [
        p for p in proxies if isinstance(p, tuple) and len(p) > 0 and p[0] == "mtproto"
    ]
    socks_proxies = [
        p
        for p in proxies
        if not (isinstance(p, tuple) and len(p) > 0 and p[0] == "mtproto")
    ]

    for _ in range(max_attempts):
        if mtproto_proxies:
            p = random.choice(mtproto_proxies)
            if test_proxy(p):
                return p

    for _ in range(max_attempts):
        if socks_proxies:
            p = random.choice(socks_proxies)
            if test_proxy(p):
                return p

    return None
