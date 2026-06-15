import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class QueryStatus(Enum):
    CLAIMED = "Claimed"
    AVAILABLE = "Available"
    UNKNOWN = "Unknown"
    ILLEGAL = "Illegal"
    WAF = "WAF"


class ErrorType(Enum):
    MESSAGE = "message"
    STATUS_CODE = "status_code"
    RESPONSE_URL = "response_url"


@dataclass
class SiteManifest:
    name: str
    url: str
    url_main: str
    url_probe: str | None = None
    username_claimed: str = ""
    error_type: str | list[str] = "status_code"
    error_msg: str | list[str] | None = None
    error_code: int | list[int] | None = None
    error_url: str | None = None
    request_method: str | None = None
    request_payload: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    regex_check: str | None = None
    is_nsfw: bool = False
    is_false_positive: bool = False

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "SiteManifest":
        return cls(
            name=name,
            url=data.get("url", ""),
            url_main=data.get("urlMain", ""),
            url_probe=data.get("urlProbe"),
            username_claimed=data.get("username_claimed", ""),
            error_type=data.get("errorType", "status_code"),
            error_msg=data.get("errorMsg"),
            error_code=data.get("errorCode"),
            error_url=data.get("errorUrl"),
            request_method=data.get("request_method"),
            request_payload=data.get("request_payload"),
            headers=data.get("headers", {}),
            regex_check=data.get("regexCheck"),
            is_nsfw=data.get("isNSFW", False),
        )


@dataclass
class QueryResult:
    site_name: str
    url_user: str
    url_main: str
    status: QueryStatus
    http_status: int | None = None
    response_time_ms: float | None = None
    error_context: str | None = None

    @property
    def is_found(self) -> bool:
        return self.status == QueryStatus.CLAIMED


class SiteChecker:
    WAF_SIGNATURES: list[str] = [
        "Cloudflare challenge spinner",
        "Cloudflare challenge error text",
        "AwsWafIntegration.forceRefreshToken",
        "perimeterxIdentifiers",
    ]

    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0"
    )

    DEFAULT_ERROR_CODES: list[int] = [404]

    def __init__(
        self,
        session: requests.Session | None = None,
        proxy: dict[str, str] | None = None,
        timeout: int = 30,
        max_retries: int = 2,
    ):

        self.session = session or self._create_session(proxy, max_retries)
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @staticmethod
    def _create_session(
        proxy: dict[str, str] | None = None, max_retries: int = 2
    ) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        if proxy:
            session.proxies.update(proxy)
        return session

    def validate_username(self, username: str, manifest: SiteManifest) -> bool:
        if not manifest.regex_check:
            return True
        try:
            return bool(re.match(manifest.regex_check, username))
        except re.error as e:
            self.logger.warning(
                "Invalid regex for %s: %s — %s", manifest.name, manifest.regex_check, e
            )
            return True

    def generate_username_variants(self, username: str) -> list[str]:
        if "{?}" not in username:
            return [username]
        base = username.replace("{?}", "{}")
        return [base.format(sep) for sep in ("_", "-", ".")]

    def detect_waf(self, response: requests.Response) -> bool:
        response_text = response.text.lower()
        for signature in self.WAF_SIGNATURES:
            if signature.lower() in response_text:
                return True
        return False

    def _get_request_url(self, manifest: SiteManifest, username: str) -> str:
        template = manifest.url_probe or manifest.url
        return template.replace("{}", username)

    def _get_request_method(self, manifest: SiteManifest) -> str:
        if manifest.request_method:
            return manifest.request_method.upper()
        return "POST" if manifest.request_payload else "GET"

    def _prepare_headers(self, manifest: SiteManifest) -> dict[str, str]:
        headers = {"User-Agent": self.DEFAULT_USER_AGENT}
        headers.update(manifest.headers)
        return headers

    def _perform_request(
        self,
        url: str,
        method: str,
        headers: dict[str, str],
        payload: dict | None = None,
    ) -> requests.Response:
        kwargs = {
            "url": url,
            "headers": headers,
            "timeout": self.timeout,
            "allow_redirects": False,
        }
        if payload and method in ("POST", "PUT"):
            kwargs["json"] = payload

        response = self.session.request(method=method.upper(), **kwargs)
        return response

    def _check_message_error(
        self, response: requests.Response, error_msg: str | list[str]
    ) -> bool:
        response_text = response.text
        if isinstance(error_msg, str):
            return error_msg in response_text
        return any(msg in response_text for msg in error_msg)

    def _check_status_code(
        self,
        response: requests.Response,
        error_code: int | list[int] | None = None,
    ) -> bool:
        if error_code is not None:
            if isinstance(error_code, int):
                return response.status_code == error_code
            return response.status_code in error_code
        return response.status_code >= 300 or response.status_code < 200

    def _check_response_url(
        self, response: requests.Response, error_url: str | None = None
    ) -> bool:
        if 200 <= response.status_code < 300:
            return False
        if error_url and error_url in response.url:
            return True
        return response.status_code >= 300

    def _apply_error_check(
        self, response: requests.Response, manifest: SiteManifest, error_type: str
    ) -> QueryStatus | None:
        if error_type == ErrorType.MESSAGE.value:
            if manifest.error_msg is None:
                return None
            found_error_msg = self._check_message_error(response, manifest.error_msg)
            return QueryStatus.AVAILABLE if found_error_msg else QueryStatus.CLAIMED

        elif error_type == ErrorType.STATUS_CODE.value:
            is_available = self._check_status_code(response, manifest.error_code)
            return QueryStatus.AVAILABLE if is_available else QueryStatus.CLAIMED

        elif error_type == ErrorType.RESPONSE_URL.value:
            is_available = self._check_response_url(response, manifest.error_url)
            return QueryStatus.AVAILABLE if is_available else QueryStatus.CLAIMED

        return None

    def _determine_status(
        self, response: requests.Response, manifest: SiteManifest
    ) -> QueryStatus:
        if self.detect_waf(response):
            return QueryStatus.WAF

        error_types = manifest.error_type
        if isinstance(error_types, str):
            error_types = [error_types]

        for error_type in error_types:
            result = self._apply_error_check(response, manifest, error_type)
            if result == QueryStatus.AVAILABLE:
                return QueryStatus.AVAILABLE

        return QueryStatus.CLAIMED

    def check(
        self, username: str, manifest: SiteManifest, *, verbose: bool = False
    ) -> QueryResult:

        import time

        url_user = manifest.url.replace("{}", username)

        result = QueryResult(
            site_name=manifest.name,
            url_user=url_user,
            url_main=manifest.url_main,
            status=QueryStatus.UNKNOWN,
        )

        if not self.validate_username(username, manifest):
            result.status = QueryStatus.ILLEGAL
            return result

        if manifest.is_false_positive:
            result.status = QueryStatus.UNKNOWN
            result.error_context = "Site in false-positive exclusion list"
            return result

        request_url = self._get_request_url(manifest, username)
        method = self._get_request_method(manifest)
        headers = self._prepare_headers(manifest)

        start_time = time.monotonic()
        try:
            response = self._perform_request(
                url=request_url,
                method=method,
                headers=headers,
                payload=manifest.request_payload,
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000

            result.http_status = response.status_code
            if verbose:
                result.response_time_ms = round(elapsed_ms, 2)

            result.status = self._determine_status(response, manifest)

        except requests.exceptions.HTTPError as e:
            result.status = QueryStatus.UNKNOWN
            result.error_context = f"HTTPError: {e}"
        except requests.exceptions.ProxyError as e:
            result.status = QueryStatus.UNKNOWN
            result.error_context = f"ProxyError: {e}"
        except requests.exceptions.ConnectionError as e:
            result.status = QueryStatus.UNKNOWN
            result.error_context = f"ConnectionError: {e}"
        except requests.exceptions.Timeout as e:
            result.status = QueryStatus.UNKNOWN
            result.error_context = f"Timeout: {e}"
        except requests.exceptions.RequestException as e:
            result.status = QueryStatus.UNKNOWN
            result.error_context = f"RequestException: {e}"
        except UnicodeError as e:
            result.status = QueryStatus.UNKNOWN
            result.error_context = f"UnicodeError: {e}"
        except Exception as e:
            result.status = QueryStatus.UNKNOWN
            result.error_context = f"Unexpected error: {type(e).__name__}: {e}"

        return result
