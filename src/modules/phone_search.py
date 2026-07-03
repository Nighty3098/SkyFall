import asyncio
import json
from collections.abc import Callable

import httpx
import phonenumbers
from loguru import logger
from phonenumbers import carrier, geocoder, timezone

from src.ui.output_formatter import (
    divider,
    end_of,
    error,
    info,
    kv,
    section,
    title,
)


class PhoneSearch:
    def __init__(self):
        logger.debug("Init: PhoneSearch")

    def parse_and_validate(
        self,
        phone: str,
        default_region: str = None,
        on_result: Callable | None = None,
    ) -> str:
        lines = [divider(), title(f"Phone: {phone}"), section("Parse & Validate")]
        if on_result:
            on_result(lines[-1])

        try:
            num = phonenumbers.parse(phone, default_region)
        except phonenumbers.NumberParseException as e:
            return error(f"Parse error: {e}")

        valid = phonenumbers.is_valid_number(num)
        possible = phonenumbers.is_possible_number(num)

        lines.append(kv("Valid", "Yes" if valid else "No"))
        if on_result:
            on_result(lines[-1])
        lines.append(kv("Possible", "Yes" if possible else "No"))
        if on_result:
            on_result(lines[-1])

        if valid or possible:
            intl = phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            national = phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.NATIONAL
            )
            e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
            lines.append(kv("International", intl))
            if on_result:
                on_result(lines[-1])
            lines.append(kv("National", national))
            if on_result:
                on_result(lines[-1])
            lines.append(kv("E.164", e164))
            if on_result:
                on_result(lines[-1])

            lines.append(kv("Country Code", f"+{num.country_code}"))
            if on_result:
                on_result(lines[-1])
            lines.append(kv("National Num", num.national_number))
            if on_result:
                on_result(lines[-1])

            region_code = phonenumbers.region_code_for_number(num)
            lines.append(kv("Region", region_code))
            if on_result:
                on_result(lines[-1])

            type_name = self._number_type_name(num)
            lines.append(kv("Line Type", type_name))
            if on_result:
                on_result(lines[-1])

            try:
                carrier_name = carrier.name_for_number(num, "en")
                if carrier_name:
                    lines.append(kv("Carrier", carrier_name))
                    if on_result:
                        on_result(lines[-1])
            except Exception:
                pass

            try:
                location = geocoder.description_for_number(num, "en")
                if location:
                    lines.append(kv("Location", location))
                    if on_result:
                        on_result(lines[-1])
            except Exception:
                pass

            try:
                tzs = timezone.time_zones_for_number(num)
                if tzs:
                    lines.append(kv("Timezones", ", ".join(tzs)))
                    if on_result:
                        on_result(lines[-1])
            except Exception:
                pass

        if len(lines) <= 3:
            return info("No information available for this number.")

        lines.append(end_of("parse & validate"))
        lines.append(divider())
        return "\n".join(lines)

    async def reverse_lookup(
        self,
        phone: str,
        numverify_key: str = "",
        abstractapi_key: str = "",
        on_result: Callable | None = None,
    ) -> str:
        if not numverify_key and not abstractapi_key:
            msg = info(
                "No API keys configured. Add NumVerify or AbstractAPI key in settings."
            )
            if on_result:
                on_result(msg)
            return msg

        lines = [divider(), title(f"Phone: {phone}")]

        if numverify_key:
            lines.append(section("NumVerify"))
            if on_result:
                on_result(lines[-1])
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        "https://api.numverify.com/validate",
                        params={
                            "access_key": numverify_key,
                            "number": phone,
                        },
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    for key, val in data.items():
                        line = kv(key, val)
                        lines.append(line)
                        if on_result:
                            on_result(line)
                elif resp.status_code == 404:
                    lines.append(info("Invalid access key or subscription required"))
                else:
                    lines.append(info(f"API error {resp.status_code}"))
            except httpx.RequestError as e:
                lines.append(info(f"Request failed: {e}"))

        if abstractapi_key:
            lines.append(section("AbstractAPI"))
            if on_result:
                on_result(lines[-1])
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        "https://phonevalidation.abstractapi.com/v1/",
                        params={
                            "api_key": abstractapi_key,
                            "phone": phone,
                        },
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    for key, val in data.items():
                        line = kv(key, val)
                        lines.append(line)
                        if on_result:
                            on_result(line)
                elif resp.status_code == 422:
                    lines.append(info("Invalid phone number or missing API key"))
                else:
                    lines.append(info(f"API error {resp.status_code}"))
            except httpx.RequestError as e:
                lines.append(info(f"Request failed: {e}"))

        if len(lines) <= 2:
            return info("No data returned.")

        lines.append(end_of("reverse lookup"))
        lines.append(divider())
        return "\n".join(lines)

    async def check_leaks(
        self,
        phone: str,
        intelx_key: str = "",
        on_result: Callable | None = None,
    ) -> str:
        if not intelx_key:
            msg = info("IntelX API key not configured. Add it in settings.")
            if on_result:
                on_result(msg)
            return msg

        lines = [divider(), title(f"Phone: {phone}"), section("IntelX Search")]
        if on_result:
            on_result(lines[-1])

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
                lines.append(info(f"API error {init_resp.status_code}"))
                return "\n".join(lines)

            search_id = init_resp.json().get("id")
            lines.append(kv("Search ID", search_id))
            if on_result:
                on_result(lines[-1])

            await asyncio.sleep(3)

            async with httpx.AsyncClient(timeout=30) as client:
                res_resp = await client.get(
                    "https://public.intelx.io/intelligent/search/result",
                    params={"id": search_id, "limit": 100},
                    headers=headers,
                )

            if res_resp.status_code == 200:
                data = res_resp.json()
                records = data.get("records") or []
                lines.append(kv("Records", len(records)))
                if on_result:
                    on_result(lines[-1])

                for item in records[:20]:
                    name = item.get("name") or item.get("description") or "N/A"
                    date = item.get("date", "")
                    bucket_id = (
                        item.get("bucketid")
                        or item.get("bucket")
                        or item.get("bucketId")
                    )
                    lines.append(bullet(name))
                    if on_result:
                        on_result(lines[-1])
                    if date:
                        lines.append(line(f"Date:   {date}"))
                    if bucket_id:
                        lines.append(line(f"Bucket: {bucket_id}"))
                    if bucket_id:
                        try:
                            async with httpx.AsyncClient(timeout=15) as client:
                                bucket_resp = await client.get(
                                    "https://public.intelx.io/intelligent/bucket",
                                    params={"id": bucket_id},
                                    headers=headers,
                                )
                            if bucket_resp.status_code == 200:
                                content = bucket_resp.json()
                                dumped = json.dumps(
                                    content, indent=6, ensure_ascii=False
                                )
                                cline = kv("Content", dumped[:500])
                                lines.append(cline)
                                if on_result:
                                    on_result(cline)
                        except httpx.RequestError:
                            pass
            else:
                lines.append(info(f"API error {res_resp.status_code}"))

        except httpx.RequestError as e:
            lines.append(info(f"Request failed: {e}"))
        except Exception as e:
            lines.append(info(f"Error: {e}"))

        if len(lines) <= 3:
            return info("No leak data found.")

        lines.append(end_of("leak check"))
        lines.append(divider())
        return "\n".join(lines)

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
