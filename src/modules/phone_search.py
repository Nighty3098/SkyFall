import asyncio
import json

import httpx
import phonenumbers
from loguru import logger
from phonenumbers import carrier, geocoder, timezone


class PhoneSearch:
    def __init__(self):
        logger.debug("Init: PhoneSearch")

    def parse_and_validate(
        self,
        phone: str,
        default_region: str = None,
    ) -> dict:
        data: dict = {"phone": phone}
        try:
            num = phonenumbers.parse(phone, default_region)
        except phonenumbers.NumberParseException as e:
            return {"phone": phone, "error": f"Parse error: {e}"}

        valid = phonenumbers.is_valid_number(num)
        possible = phonenumbers.is_possible_number(num)
        data["valid"] = valid
        data["possible"] = possible

        if valid or possible:
            data["international"] = phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            data["national"] = phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.NATIONAL
            )
            data["e164"] = phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.E164
            )
            data["country_code"] = f"+{num.country_code}"
            data["national_number"] = num.national_number
            data["region"] = phonenumbers.region_code_for_number(num)
            data["line_type"] = self._number_type_name(num)

            try:
                carrier_name = carrier.name_for_number(num, "en")
                if carrier_name:
                    data["carrier"] = carrier_name
            except Exception:
                pass

            try:
                location = geocoder.description_for_number(num, "en")
                if location:
                    data["location"] = location
            except Exception:
                pass

            try:
                tzs = timezone.time_zones_for_number(num)
                if tzs:
                    data["timezones"] = list(tzs)
            except Exception:
                pass

        return data

    async def reverse_lookup(
        self,
        phone: str,
        numverify_key: str = "",
        abstractapi_key: str = "",
    ) -> dict:
        if not numverify_key and not abstractapi_key:
            return {
                "phone": phone,
                "message": (
                    "No API keys configured. Add NumVerify or AbstractAPI key"
                    " in settings."
                ),
            }

        data: dict = {"phone": phone}

        if numverify_key:
            data["numverify"] = await self._query_numverify(phone, numverify_key)

        if abstractapi_key:
            data["abstractapi"] = await self._query_abstractapi(phone, abstractapi_key)

        return data

    async def _query_numverify(self, phone: str, key: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.numverify.com/validate",
                    params={"access_key": key, "number": phone},
                )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return {"error": "Invalid access key or subscription required"}
            return {"error": f"API error {resp.status_code}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {e}"}

    async def _query_abstractapi(self, phone: str, key: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://phonevalidation.abstractapi.com/v1/",
                    params={"api_key": key, "phone": phone},
                )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 422:
                return {"error": "Invalid phone number or missing API key"}
            return {"error": f"API error {resp.status_code}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {e}"}

    async def check_leaks(
        self,
        phone: str,
        intelx_key: str = "",
    ) -> dict:
        if not intelx_key:
            return {
                "phone": phone,
                "message": "IntelX API key not configured. Add it in settings.",
            }

        data: dict = {"phone": phone}
        headers = {
            "x-key": intelx_key,
            "User-Agent": "SkyFall-OSINT/1.0",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        search_data = {
            "term": phone,
            "lookuplevel": 0,
            "maxresults": 100,
            "timeout": None,
            "datefrom": "",
            "dateto": "",
            "sort": 2,
            "media": 0,
            "terminate": [],
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                init_resp = await client.post(
                    "https://public.intelx.io/intelligent/search",
                    data=json.dumps(search_data),
                    headers=headers,
                )

            if init_resp.status_code != 200:
                data["error"] = f"API error {init_resp.status_code}"
                return data

            search_id = init_resp.json().get("id")
            data["search_id"] = search_id

            await asyncio.sleep(3)

            async with httpx.AsyncClient(timeout=30) as client:
                res_resp = await client.get(
                    "https://public.intelx.io/intelligent/search/result",
                    params={"id": search_id, "limit": 100},
                    headers=headers,
                )

            if res_resp.status_code == 200:
                payload = res_resp.json()
                records = payload.get("records") or []
                data["records"] = len(records)

                findings = []
                for item in records[:20]:
                    finding = {
                        "name": item.get("name") or item.get("description") or "N/A",
                        "date": item.get("date", ""),
                        "bucket": item.get("bucketid")
                        or item.get("bucket")
                        or item.get("bucketId"),
                    }
                    findings.append(finding)
                data["findings"] = findings
            else:
                data["error"] = f"API error {res_resp.status_code}"

        except httpx.RequestError as e:
            data["error"] = f"Request failed: {e}"
        except Exception as e:
            data["error"] = f"Error: {e}"

        return data

    async def search_7tel(
        self,
        phone: str,
    ) -> dict:
        """Search phone number on 7tel.ru (caller ID reviews)."""
        import re

        data: dict = {"phone": phone}

        digits = re.sub(r"\D", "", phone)
        if digits.startswith("7") and len(digits) == 11:
            slug = digits[1:]
        elif digits.startswith("8") and len(digits) == 11:
            slug = digits[1:]
        elif len(digits) == 10:
            slug = digits
        else:
            data["error"] = "Invalid phone number format"
            return data

        url = f"https://xn--7-jtbs0a.xn--p1ai/{slug}"
        data["url"] = url

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    },
                )
        except httpx.RequestError as e:
            data["error"] = f"Request failed: {e}"
            return data

        if resp.status_code == 404:
            data["message"] = "Phone number not found on 7tel.ru"
            return data

        if resp.status_code != 200:
            data["error"] = f"HTTP {resp.status_code}"
            return data

        html = resp.text

        score = "unknown"
        score_m = re.search(r'<span class="score\s+(negative|neutral|positive)"', html)
        if score_m:
            score = score_m.group(1)
        data["score"] = score

        main_info = re.findall(
            r"<span>([^<]+)</span>",
            html.split('<div class="MainPhone">')[1].split("</div>")[0]
            if '<div class="MainPhone">' in html
            else "",
        )
        if main_info[1:]:
            data["info"] = [item.strip() for item in main_info[1:]]

        review_count_m = re.search(r"negative.*?(\d+)", html)
        if review_count_m:
            data["negative_reviews"] = review_count_m.group(1)

        review_pattern = re.compile(
            r'<div class="review">.*?'
            r'<div class="date">(.*?)</div>.*?'
            r'itemprop="author">(.*?)</span>.*?'
            r'class="comment"[^>]*>(.*?)</span>',
            re.DOTALL,
        )
        reviews = []
        for m in review_pattern.finditer(html):
            reviews.append(
                {
                    "date": m.group(1).strip(),
                    "author": m.group(2).strip(),
                    "comment": re.sub(r"<[^>]+>", "", m.group(3)).strip(),
                }
            )
        if reviews:
            data["reviews"] = reviews

        similar_m = re.findall(
            r'<a href="/(\d+)">\+?(\d+)</a>',
            html.split('<div class="similar">')[1].split("</div>")[0]
            if '<div class="similar">' in html
            else "",
        )
        if similar_m:
            data["similar"] = [f"+{num}" for _, num in similar_m[:10]]

        return data

    def _number_type_name(self, num) -> str:
        ntype = phonenumbers.number_type(num)
        mapping = {
            phonenumbers.PhoneNumberType.MOBILE: "Mobile",
            phonenumbers.PhoneNumberType.FIXED_LINE: "Fixed Line",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
            phonenumbers.PhoneNumberType.VOIP: "VoIP",
            phonenumbers.PhoneNumberType.TOLL_FREE: "Toll Free",
            phonenumbers.PhoneNumberType.PREMIUM_RATE: "Premium Rate",
            phonenumbers.PhoneNumberType.SHARED_COST: "Shared Cost",
            phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
            phonenumbers.PhoneNumberType.PAGER: "Pager",
            phonenumbers.PhoneNumberType.UAN: "UAN",
            phonenumbers.PhoneNumberType.VOICEMAIL: "Voicemail",
            phonenumbers.PhoneNumberType.UNKNOWN: "Unknown",
        }
        return mapping.get(ntype, "Unknown")
