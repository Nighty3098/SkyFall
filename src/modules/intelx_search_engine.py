import asyncio
import json

import requests
from loguru import logger


class IntelxSearchEngine:
    def __init__(self, api_key):
        logger.debug("Init: IntelxSearchEngine")

        self.base_url = "https://public.intelx.io"
        self.api_key = api_key
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-key": self.api_key,
            "Origin": "https://intelx.io",
            "Referer": "https://intelx.io/",
            "Connection": "keep-alive",
        }

    async def _send_request(self, email):
        search_data = {
            "term": email,
            "lookuplevel": 0,
            "maxresults": 1000,
            "timeout": None,
            "datefrom": "",
            "dateto": "",
            "sort": 2,
            "media": 0,
            "terminate": [],
        }

        try:
            raw_data = json.dumps(search_data)
            init_response = await asyncio.to_thread(
                requests.post,
                f"{self.base_url}/intelligent/search",
                data=raw_data,
                headers=self.headers,
            )
            init_response.raise_for_status()

            search_id = init_response.json().get("id")
            logger.debug(f"Search task created successfully. ID: {search_id}")
            return search_id
        except Exception as e:
            logger.error(f"Error initializing search: {e}")
            return None

    async def get_data(self, email):
        search_id = await self._send_request(email)
        if not search_id:
            return "[!] Failed to initialize search task."

        databases = set()

        try:
            for i in range(5):
                await asyncio.sleep(2)
                try:
                    result_url = (
                        f"{self.base_url}/intelligent/search/result"
                        f"?id={search_id}&limit=1000"
                    )
                    res_response = await asyncio.to_thread(
                        requests.get, result_url, headers=self.headers
                    )
                    res_response.raise_for_status()

                    data = res_response.json()
                    records = data.get("records", [])

                    for item in records:
                        name = item.get("name") or item.get("description")
                        if name:
                            databases.add(name)

                    if data.get("status") == 1:
                        logger.debug("IntelX backend finished searching.")
                        break
                except Exception as e:
                    logger.error(f"Error fetching results (attempt {i + 1}): {e}")
                    break

            result = "\n" + "=" * 45 + "\n"
            if databases:
                result += f"[+] Found ({len(databases)}):\n"
                for db in sorted(databases):
                    result += f"  - {db}\n"
            else:
                logger.debug("No databases found for this target.")
                result += "Not found\n"

            result += "=" * 45
            return result

        except Exception as e:
            logger.error(f"Critical error in get_data: {e}")
            return "[!] Critical error occurred while processing data."
