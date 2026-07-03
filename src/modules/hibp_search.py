import asyncio
import re
import urllib.parse

import requests
from loguru import logger

from src.ui.output_formatter import bullet, divider, error, kv, section, title


class HibpSearch:
    def __init__(self, api_key=""):
        logger.debug("Init: HibpSearch")
        self.api_key = api_key
        self.base_url = "https://haveibeenpwned.com/api/v3"
        self._update_headers()

    def _update_headers(self):
        self.headers = {
            "hibp-api-key": self.api_key,
            "User-Agent": "SkyFall/1.0 (github.com/Nighty3098/SkyFall)",
        }

    async def get_data(self, email):
        encoded_email = urllib.parse.quote(email.strip())
        url = f"{self.base_url}/breachedaccount/{encoded_email}"

        for attempt in range(3):
            try:
                resp = await asyncio.to_thread(
                    requests.get,
                    url,
                    headers=self.headers,
                    timeout=10,
                )

                if resp.status_code == 200:
                    return self._format_result(email, resp.json())
                elif resp.status_code == 404:
                    return f"\n{divider()}\n{title(f'Have I Been Pwned — {email}')}\n\nNo breaches found.\n{divider()}"
                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 30))
                    logger.warning(f"HIBP rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    return error(f"HIBP error {resp.status_code}: {resp.text[:200]}")

            except requests.exceptions.RequestException as e:
                logger.error(f"HIBP network error: {e}")
                return error(f"Network error: {e}")

        return error("Rate limit exceeded, max retries reached.")

    def _format_result(self, email, breaches):
        result = f"\n{divider()}\n"
        result += f"{title(f'Have I Been Pwned — {email}')}\n\n"
        result += f"Found in {len(breaches)} breach{'es' if len(breaches) != 1 else ''}:\n\n"

        for b in breaches:
            name = b.get("Name", "Unknown")
            domain = b.get("Domain", "")
            date = b.get("BreachDate", "Unknown")
            classes = b.get("DataClasses", [])
            desc = b.get("Description", "")
            result += f"{section(name)}\n"
            if domain:
                result += f"{kv('Domain', domain)}\n"
            result += f"{kv('Date', date)}\n"
            result += f"{kv('Data', ', '.join(classes))}\n"
            if desc:
                clean = re.sub(r"<[^>]+>", "", desc)[:300]
                result += f"{kv('Description', clean)}\n"
            result += "\n"

        result += divider()
        return result
