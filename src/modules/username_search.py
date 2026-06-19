import asyncio
import concurrent.futures
import json
import os
import re
from time import monotonic

import requests
from loguru import logger


class UsernameSearch:
    class Status:
        CLAIMED = "Claimed"
        AVAILABLE = "Available"
        UNKNOWN = "Unknown"
        ILLEGAL = "Illegal"
        WAF = "WAF"

    @staticmethod
    def _interpolate(obj, username):
        if isinstance(obj, str):
            return obj.replace("{}", username)
        if isinstance(obj, dict):
            return {k: UsernameSearch._interpolate(v, username) for k, v in obj.items()}
        if isinstance(obj, list):
            return [UsernameSearch._interpolate(i, username) for i in obj]
        return obj

    def __init__(self, data_path=None, data=None):
        self.waf_fingerprints = [
            r".loading-spinner{visibility:hidden}body.no-js .challenge-running{display:none}body.dark{background-color:#222;color:#d9d9d9}body.dark a{color:#fff}body.dark a:hover{color:#ee730a;text-decoration:underline}body.dark .lds-ring div{border-color:#999 transparent transparent}body.dark .font-red{color:#b20f03}body.dark",  # noqa: E501
            r'<span id="challenge-error-text">',
            r"AwsWafIntegration.forceRefreshToken",
            r'{return l.onPageView}}),Object.defineProperty(r,"perimeterxIdentifiers",{enumerable:',  # noqa: E501
        ]
        self.MAX_WORKERS = 20
        self.DATA_FILE = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data/username_data.json",
        )
        self.REMOTE_DATA_URL = "https://data.sherlockproject.xyz"
        self._site_data = data
        self._data_path = data_path

    def _load_sites(self):
        if self._site_data is not None:
            return self._site_data
        path = self._data_path
        if path is None:
            path = (
                self.DATA_FILE
                if os.path.isfile(self.DATA_FILE)
                else self.REMOTE_DATA_URL
            )
        if path.startswith(("http://", "https://")):
            resp = requests.get(path, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        else:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        data.pop("$schema", None)
        self._site_data = data
        return data

    def _check_site(self, site_name, net_info, username, proxy=None, timeout=60):
        regex_check = net_info.get("regexCheck")
        if regex_check and re.search(regex_check, username) is None:
            return {
                "site": site_name,
                "url_main": net_info.get("urlMain", ""),
                "url_user": "",
                "status": self.Status.ILLEGAL,
                "http_status": "",
                "response_time": None,
                "context": None,
            }

        url = self._interpolate(net_info["url"], username.replace(" ", "%20"))
        url_probe = self._interpolate(net_info.get("urlProbe", url), username)

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",  # noqa: E501
        }
        headers.update(net_info.get("headers", {}))

        raw_error_type = net_info["errorType"]
        error_types = (
            [raw_error_type] if isinstance(raw_error_type, str) else raw_error_type
        )

        request_method = net_info.get("request_method")
        if request_method is None:
            request_method = "HEAD" if raw_error_type == "status_code" else "GET"
        method_map = {
            "GET": requests.get,
            "HEAD": requests.head,
            "POST": requests.post,
            "PUT": requests.put,
        }
        request_func = method_map[request_method]

        request_payload = (
            self._interpolate(net_info.get("request_payload"), username)
            if net_info.get("request_payload")
            else None
        )
        allow_redirects = "response_url" not in error_types

        start = monotonic()
        response = None
        error_context = None
        try:
            kwargs = {
                "url": url_probe,
                "headers": headers,
                "allow_redirects": allow_redirects,
                "timeout": timeout,
            }
            if proxy:
                kwargs["proxies"] = {"http": proxy, "https": proxy}
            if request_payload:
                kwargs["json"] = request_payload
            response = request_func(**kwargs)
        except requests.exceptions.HTTPError as e:
            error_context = f"HTTP Error: {e}"
        except requests.exceptions.ProxyError as e:
            error_context = f"Proxy Error: {e}"
        except requests.exceptions.ConnectionError as e:
            error_context = f"Connection Error: {e}"
        except requests.exceptions.Timeout as e:
            error_context = f"Timeout Error: {e}"
        except requests.exceptions.RequestException as e:
            error_context = f"Request Error: {e}"
        except UnicodeError as e:
            error_context = f"Encoding Error: {e}"

        response_time = monotonic() - start

        if error_context:
            return {
                "site": site_name,
                "url_main": net_info.get("urlMain", ""),
                "url_user": url,
                "status": self.Status.UNKNOWN,
                "http_status": getattr(response, "status_code", "?"),
                "response_time": response_time,
                "context": error_context,
            }

        http_status = response.status_code
        resp_text = response.text

        for fp in self.waf_fingerprints:
            if fp in resp_text:
                return {
                    "site": site_name,
                    "url_main": net_info.get("urlMain", ""),
                    "url_user": url,
                    "status": self.Status.WAF,
                    "http_status": http_status,
                    "response_time": response_time,
                    "context": None,
                }

        if any(
            et not in ("message", "status_code", "response_url") for et in error_types
        ):
            return {
                "site": site_name,
                "url_main": net_info.get("urlMain", ""),
                "url_user": url,
                "status": self.Status.UNKNOWN,
                "http_status": http_status,
                "response_time": response_time,
                "context": f"Unknown error type '{raw_error_type}'",
            }

        query_status = self.Status.UNKNOWN

        if "message" in error_types:
            error_flag = True
            errors = net_info.get("errorMsg")
            if isinstance(errors, str):
                if errors in resp_text:
                    error_flag = False
            else:
                for error in errors:
                    if error in resp_text:
                        error_flag = False
                        break
            query_status = self.Status.CLAIMED if error_flag else self.Status.AVAILABLE

        if "status_code" in error_types and query_status is not self.Status.AVAILABLE:
            error_codes = net_info.get("errorCode")
            query_status = self.Status.CLAIMED
            if isinstance(error_codes, int):
                error_codes = [error_codes]
            if error_codes is not None and http_status in error_codes:
                query_status = self.Status.AVAILABLE
            elif http_status >= 300 or http_status < 200:
                query_status = self.Status.AVAILABLE

        if "response_url" in error_types and query_status is not self.Status.AVAILABLE:
            query_status = (
                self.Status.CLAIMED
                if 200 <= http_status < 300
                else self.Status.AVAILABLE
            )

        return {
            "site": site_name,
            "url_main": net_info.get("urlMain", ""),
            "url_user": url,
            "status": query_status,
            "http_status": http_status,
            "response_time": response_time,
            "context": None,
        }

    def check(
        self,
        username,
        timeout=60,
        proxy=None,
        on_result=None,
        on_progress=None,
    ):
        site_data = self._load_sites()
        total = len(site_data)
        if on_progress:
            on_progress(0, total)

        results = []
        done = 0
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.MAX_WORKERS
        ) as executor:
            futures = {
                executor.submit(
                    self._check_site, name, info, username, proxy, timeout
                ): name
                for name, info in site_data.items()
            }
            for future in concurrent.futures.as_completed(futures):
                r = future.result()
                results.append(r)
                done += 1
                if r["status"] == self.Status.CLAIMED:
                    if on_result:
                        on_result(r)

                if on_progress:
                    on_progress(done, total)

                if r["status"] == self.Status.UNKNOWN and r["context"]:
                    logger.warning(f"[{r['site']}] {r['context']}")

        return results

    async def acheck(
        self,
        username,
        timeout=60,
        proxy=None,
        on_result=None,
        on_progress=None,
    ):
        site_data = await asyncio.to_thread(self._load_sites)
        total = len(site_data)
        if on_progress:
            on_progress(0, total)

        results = []
        done = 0
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.MAX_WORKERS
        ) as executor:
            tasks = [
                loop.run_in_executor(
                    executor,
                    self._check_site,
                    name,
                    info,
                    username,
                    proxy,
                    timeout,
                )
                for name, info in site_data.items()
            ]
            for coro in asyncio.as_completed(tasks):
                r = await coro
                results.append(r)
                done += 1
                if r["status"] == self.Status.CLAIMED:
                    if on_result:
                        on_result(r)
                if on_progress:
                    on_progress(done, total)
                if r["status"] == self.Status.UNKNOWN and r["context"]:
                    logger.warning(f"[{r['site']}] {r['context']}")

        return results
