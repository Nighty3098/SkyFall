"""Security helpers for SkyFall.

Two concerns are handled here:

* **At-rest protection of API keys.**  Sensitive settings values are encrypted
  with Fernet before they are written to ``~/.skyfall/settings.json``.  The key
  itself lives in ``~/.skyfall/secret.key`` with ``0600`` permissions.  The rest
  of the code base keeps working with plaintext values, so encryption stays
  fully transparent.

* **A shared local access token** used by the MCP server and the graph bridge so
  other local processes cannot drive the OSINT tooling or the graph canvas.

Only ``cryptography`` (already a dependency) is required.
"""

from __future__ import annotations

import hmac
import os
import secrets as _secrets
import stat
from pathlib import Path

from loguru import logger

CONFIG_DIR = Path.home() / ".skyfall"
KEY_FILE = CONFIG_DIR / "secret.key"

ENC_PREFIX = "enc:v1:"

#: Environment variable carrying the shared MCP / graph-bridge token.
TOKEN_ENV = "SKYFALL_MCP_TOKEN"
#: Environment variable toggling MCP bearer-token authentication.
AUTH_ENV = "SKYFALL_MCP_REQUIRE_AUTH"

#: Settings keys that must never touch disk in plaintext.
SENSITIVE_KEYS = frozenset(
    {
        "tg_api_key",
        "telegram_api_hash",
        "telegram_phone",
        "intelligent_x_api_key",
        "hibp_api_key",
        "virustotal_api_key",
        "google_safe_api_key",
        "ipinfo_api_key",
        "github_token",
        "numverify_api_key",
        "abstractapi_api_key",
        "trongrid_api_key",
        "etherscan_api_key",
        "bscscan_api_key",
        "tonapi_api_key",
        "helius_api_key",
        "abuseipdb_api_key",
        "greynoise_api_key",
    }
)

_fernet = None
_fernet_ready = False


def restrict_file(path: Path) -> None:
    """Best-effort chmod 0600 (owner read/write only)."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:  # pragma: no cover - platform dependent
        logger.debug(f"Could not restrict permissions on {path}: {exc}")


def ensure_config_dir() -> Path:
    """Create ``~/.skyfall`` and tighten it to ``0700``."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, stat.S_IRWXU)
    except OSError as exc:  # pragma: no cover - platform dependent
        logger.debug(f"Could not restrict permissions on {CONFIG_DIR}: {exc}")
    return CONFIG_DIR


def _get_fernet():
    global _fernet, _fernet_ready
    if _fernet_ready:
        return _fernet
    _fernet_ready = True

    try:
        from cryptography.fernet import Fernet
    except ImportError:  # pragma: no cover - cryptography is a hard dependency
        logger.warning("cryptography is not installed; secrets remain unencrypted")
        return None

    try:
        ensure_config_dir()
        if KEY_FILE.exists():
            key = KEY_FILE.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            KEY_FILE.write_bytes(key)
            restrict_file(KEY_FILE)
            logger.info(f"Generated secret storage key at {KEY_FILE}")
        _fernet = Fernet(key)
    except Exception as exc:
        logger.error(f"Secret storage unavailable, falling back to plaintext: {exc}")
        _fernet = None
    return _fernet


def is_encrypted(value: object) -> bool:
    return isinstance(value, str) and value.startswith(ENC_PREFIX)


def encrypt(value: str) -> str:
    """Encrypt a single value. Empty values and failures pass through unchanged."""
    if not isinstance(value, str) or not value or is_encrypted(value):
        return value
    fernet = _get_fernet()
    if fernet is None:
        return value
    try:
        return ENC_PREFIX + fernet.encrypt(value.encode()).decode()
    except Exception as exc:  # pragma: no cover
        logger.error(f"Failed to encrypt value: {exc}")
        return value


def decrypt(value: str) -> str:
    """Decrypt a single value. Plaintext values are returned unchanged."""
    if not is_encrypted(value):
        return value
    fernet = _get_fernet()
    if fernet is None:
        logger.warning("Encrypted setting found but secret storage is unavailable")
        return ""
    try:
        return fernet.decrypt(value[len(ENC_PREFIX) :].encode()).decode()
    except Exception:
        logger.warning(
            "Could not decrypt a stored secret (key rotated or file changed); "
            "the value was reset"
        )
        return ""


def encrypt_settings(data: dict) -> dict:
    """Return a copy of ``data`` with :data:`SENSITIVE_KEYS` values encrypted."""
    return {
        key: (encrypt(val) if key in SENSITIVE_KEYS else val)
        for key, val in data.items()
    }


def decrypt_settings(data: dict) -> dict:
    """Return a copy of ``data`` with encrypted sensitive values decrypted.

    Plaintext values are left untouched so existing settings files migrate on
    the next save.
    """
    return {
        key: (decrypt(val) if key in SENSITIVE_KEYS else val)
        for key, val in data.items()
    }


def get_or_create_token(name: str = "mcp_token") -> str:
    """Return the shared local access token, generating it on first use."""
    ensure_config_dir()
    path = CONFIG_DIR / name
    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = _secrets.token_urlsafe(32)
    path.write_text(token, encoding="utf-8")
    restrict_file(path)
    logger.info(f"Generated local access token at {path}")
    return token


def read_token(name: str = "mcp_token") -> str:
    """Token from the environment when set, otherwise from the token file."""
    env = os.environ.get(TOKEN_ENV)
    if env and env.strip():
        return env.strip()
    return get_or_create_token(name)


def tokens_equal(expected: str, provided: object) -> bool:
    """Constant-time comparison that tolerates non-string input."""
    if not expected or not isinstance(provided, str):
        return False
    return hmac.compare_digest(expected, provided)
