import asyncio
import json
import urllib.parse

import requests
from loguru import logger

from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    error,
    info,
    kv,
    line,
    section,
    title,
)

HIBP_API_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
HIBP_USER_AGENT = "SkyFallMailEngine/1.0"


class MailSearchEngine:
    def __init__(self, intelx_api_key, hibp_api_key=""):
        logger.debug("Init: MailSearchEngine")
        self.base_url = "https://public.intelx.io"
        self.api_key = intelx_api_key
        self.hibp_api_key = hibp_api_key
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:151.0)"
            "Gecko/20100101 Firefox/151.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-key": self.api_key,
            "Origin": "https://intelx.io",
            "Referer": "https://intelx.io/",
            "Connection": "keep-alive",
        }

    # ── IntelX ────────────────────────────────────────────────────

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

    async def _get_bucket_content(self, bucket_id):
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"{self.base_url}/intelligent/bucket",
                params={"id": bucket_id},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching bucket {bucket_id}: {e}")
            return None

    async def _get_record_details(self, record_id):
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"{self.base_url}/intelligent/record",
                params={"id": record_id},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching record {record_id}: {e}")
            return None

    async def get_data(self, email):
        search_id = await self._send_request(email)
        if not search_id:
            return error("Failed to initialize search task.")

        databases = set()
        records_with_data = []

        try:
            for i in range(5):
                await asyncio.sleep(2)
                try:
                    result_url = f"""{self.base_url}/intelligent/search/result?id=
                    {search_id}&limit=100000"""
                    res_response = await asyncio.to_thread(
                        requests.get, result_url, headers=self.headers
                    )
                    res_response.raise_for_status()

                    data = res_response.json()
                    records = data.get("records", [])

                    logger.debug(f"Found {len(records)} records")

                    for item in records:
                        name = item.get("name") or item.get("description")
                        if name:
                            databases.add(name)

                        bucket_id = (
                            item.get("bucketid")
                            or item.get("bucket")
                            or item.get("bucketId")
                        )

                        if bucket_id:
                            bucket_content = await self._get_bucket_content(bucket_id)

                            if bucket_content:
                                record_info = {
                                    "name": name,
                                    "bucket_id": bucket_id,
                                    "content": bucket_content,
                                    "size": item.get("size"),
                                    "date": item.get("date"),
                                    "tags": item.get("tags", []),
                                    "source": item.get("source", ""),
                                    "systemid": item.get("systemid", ""),
                                }
                                records_with_data.append(record_info)
                                logger.debug(f"Successfully fetched bucket {bucket_id}")
                            else:
                                record_id = item.get("id") or item.get("recordid")
                                if record_id:
                                    record_details = await self._get_record_details(
                                        record_id
                                    )
                                    if record_details:
                                        real_bucket_id = record_details.get(
                                            "bucketid"
                                        ) or record_details.get("bucket")
                                        if real_bucket_id:
                                            bucket_content = (
                                                await self._get_bucket_content(
                                                    real_bucket_id
                                                )
                                            )
                                            if bucket_content:
                                                record_info = {
                                                    "name": name,
                                                    "bucket_id": real_bucket_id,
                                                    "content": bucket_content,
                                                    "size": item.get("size"),
                                                    "date": item.get("date"),
                                                    "tags": item.get("tags", []),
                                                    "source": item.get("source", ""),
                                                    "systemid": item.get(
                                                        "systemid", ""
                                                    ),
                                                }
                                                records_with_data.append(record_info)
                                                logger.debug(
                                                    f"""Successfully fetched bucket via
                                                     record {real_bucket_id}"""
                                                )

                    if data.get("status") == 1:
                        logger.debug("IntelX backend finished searching.")
                        break
                except Exception as e:
                    logger.error(f"Error fetching results (attempt {i + 1}): {e}")
                    break

            result = f"{divider()}\n"
            result += f"{title(f'IntelX Search: {email}')}\n"

            if databases:
                result += f"{section(f'Found ({len(databases)}) databases')}\n"
                for db in sorted(databases):
                    result += f"{bullet(db)}\n"

                if records_with_data:
                    result += f"{section('Data')}\n"
                    for idx, record in enumerate(records_with_data, 1):
                        result += f"{section(f'Record #{idx}')}\n"
                        result += f"{kv('DB', record['name'])}\n"
                        result += f"{kv('Bucket ID', record['bucket_id'])}\n"
                        if record.get("date"):
                            result += f"{kv('Date', record['date'])}\n"
                        if record.get("size"):
                            result += f"{kv('Size', record['size'])}\n"
                        if record.get("source"):
                            result += f"{kv('Source', record['source'])}\n"
                        if record.get("tags"):
                            result += f"{kv('Tags', ', '.join(record['tags']))}\n"

                        content = record["content"]
                        result += "  Content:\n"
                        if isinstance(content, dict):
                            for key, value in content.items():
                                if isinstance(value, list):
                                    result += f"    {key}:\n"
                                    for item in value:
                                        result += f"    - {item}\n"
                                else:
                                    result += f"    {key}: {value}\n"
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    for k, v in item.items():
                                        result += f"    {k}: {v}\n"
                                else:
                                    result += f"    - {item}\n"
                        else:
                            result += f"    {content}\n"
            else:
                result += f"{info('Not found')}\n"

            result += f"{end_of('intelx search')}\n"
            result += divider()
            return result

        except Exception as e:
            logger.error(f"Critical error in get_data: {e}")
            return error("Critical error occurred while processing data.")

    async def get_bucket_by_id(self, bucket_id):
        return await self._get_bucket_content(bucket_id)

    # ── HIBP ──────────────────────────────────────────────────────

    async def check_hibp(self, email):
        if not self.hibp_api_key:
            return error("HIBP API key not configured. Add it in settings.")

        encoded = urllib.parse.quote(email.strip())
        url = HIBP_API_URL.format(email=encoded)
        headers = {
            "hibp-api-key": self.hibp_api_key,
            "User-Agent": HIBP_USER_AGENT,
        }

        for attempt in range(3):
            try:
                resp = await asyncio.to_thread(
                    requests.get, url, headers=headers, timeout=15
                )

                if resp.status_code == 200:
                    breaches = resp.json()
                    return self._format_hibp_result(email, breaches)
                elif resp.status_code == 404:
                    return self._format_hibp_result(email, [])
                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2))
                    logger.warning(f"HIBP rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    return error(
                        f"HIBP API error {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                logger.error(f"HIBP network error: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                return error(f"HIBP request failed: {e}")

        return error("HIBP request failed after retries")

    def _format_hibp_result(self, email, breaches):
        lines = [divider(), title(f"HIBP: {email}")]
        if not breaches:
            lines.append(info("No breaches found"))
        else:
            lines.append(section(f"Found in {len(breaches)} breach(es)"))
            for b in breaches:
                name = b.get("Name", "?")
                domain = b.get("Domain", "?")
                date = b.get("BreachDate", "?")
                classes = b.get("PwnCount", "?")
                data_classes = ", ".join(b.get("DataClasses", []))
                description = b.get("Description", "")
                lines.append(bullet(name))
                lines.append(line(f"Domain:  {domain}"))
                lines.append(line(f"Date:    {date}"))
                lines.append(line(f"Records: {classes}"))
                lines.append(line(f"Data:    {data_classes}"))
                lines.append(line(f"Info:    {description[:200]}"))
        lines.append(end_of("hibp check"))
        lines.append(divider())
        return "\n".join(lines)
