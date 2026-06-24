import asyncio
import json
from collections.abc import Callable

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
        on_result: Callable | None = None,
    ) -> str:
        lines = []
        try:
            num = phonenumbers.parse(phone, default_region)
        except phonenumbers.NumberParseException as e:
            return f"[!] Parse error: {e}"

        valid = phonenumbers.is_valid_number(num)
        possible = phonenumbers.is_possible_number(num)

        lines.append(f"{'Valid':20} {'Yes' if valid else 'No'}")
        if on_result:
            on_result(lines[-1])
        lines.append(f"{'Possible':20} {'Yes' if possible else 'No'}")
        if on_result:
            on_result(lines[-1])

        if valid or possible:
            intl = phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            national = phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.NATIONAL
            )
            e164 = phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.E164
            )
            lines.append(f"{'International':20} {intl}")
            if on_result:
                on_result(lines[-1])
            lines.append(f"{'National':20} {national}")
            if on_result:
                on_result(lines[-1])
            lines.append(f"{'E.164':20} {e164}")
            if on_result:
                on_result(lines[-1])

            country_code = num.country_code
            national_number = num.national_number
            lines.append(f"{'Country Code':20} +{country_code}")
            if on_result:
                on_result(lines[-1])
            lines.append(f"{'National Num':20} {national_number}")
            if on_result:
                on_result(lines[-1])

            region_code = phonenumbers.region_code_for_number(num)
            lines.append(f"{'Region':20} {region_code}")
            if on_result:
                on_result(lines[-1])

            type_name = self._number_type_name(num)
            lines.append(f"{'Line Type':20} {type_name}")
            if on_result:
                on_result(lines[-1])

            try:
                carrier_name = carrier.name_for_number(num, "en")
                if carrier_name:
                    lines.append(f"{'Carrier':20} {carrier_name}")
                    if on_result:
                        on_result(lines[-1])
            except Exception:
                pass

            try:
                location = geocoder.description_for_number(num, "en")
                if location:
                    lines.append(f"{'Location':20} {location}")
                    if on_result:
                        on_result(lines[-1])
            except Exception:
                pass

            try:
                tzs = timezone.time_zones_for_number(num)
                if tzs:
                    lines.append(f"{'Timezones':20} {', '.join(tzs)}")
                    if on_result:
                        on_result(lines[-1])
            except Exception:
                pass

        if not lines:
            return "[!] No information available for this number."

        return f"[+] Phone info for {phone}:\n" + "\n".join(lines)

    async def reverse_lookup(
        self,
        phone: str,
        numverify_key: str = "",
        abstractapi_key: str = "",
        on_result: Callable | None = None,
    ) -> str:
        lines = []

        if numverify_key:
            lines.append("--- NumVerify ---")
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
                        line = f"  {key:20} {val}"
                        lines.append(line)
                        if on_result:
                            on_result(line)
                elif resp.status_code == 404:
                    line = "  [i] Invalid access key or subscription required"
                    lines.append(line)
                    if on_result:
                        on_result(line)
                else:
                    line = f"  [i] API error {resp.status_code}"
                    lines.append(line)
                    if on_result:
                        on_result(line)
            except httpx.RequestError as e:
                line = f"  [i] Request failed: {e}"
                lines.append(line)
                if on_result:
                    on_result(line)

        if abstractapi_key:
            lines.append("--- AbstractAPI ---")
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
                        line = f"  {key:20} {val}"
                        lines.append(line)
                        if on_result:
                            on_result(line)
                elif resp.status_code == 422:
                    line = "  [i] Invalid phone number or missing API key"
                    lines.append(line)
                    if on_result:
                        on_result(line)
                else:
                    line = f"  [i] API error {resp.status_code}"
                    lines.append(line)
                    if on_result:
                        on_result(line)
            except httpx.RequestError as e:
                line = f"  [i] Request failed: {e}"
                lines.append(line)
                if on_result:
                    on_result(line)

        if not numverify_key and not abstractapi_key:
            msg = (
                "[i] No API keys configured. "
                "Add NumVerify or AbstractAPI key in settings."
            )
            if on_result:
                on_result(msg)
            return msg

        if not lines:
            return "No data returned."

        return f"[+] Reverse lookup for {phone}:\n" + "\n".join(lines)

    async def check_leaks(
        self,
        phone: str,
        intelx_key: str = "",
        on_result: Callable | None = None,
    ) -> str:
        lines = []

        if not intelx_key:
            return "[i] IntelX API key not configured. Add it in settings."

        lines.append("--- IntelX Search ---")

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
                line = f"  [i] API error {init_resp.status_code}"
                lines.append(line)
                if on_result:
                    on_result(line)
                return f"[+] Leak check for {phone}:\n" + "\n".join(lines)

            search_id = init_resp.json().get("id")
            line = f"  Search ID: {search_id}"
            lines.append(line)
            if on_result:
                on_result(line)

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
                line = f"  Found {len(records)} records"
                lines.append(line)
                if on_result:
                    on_result(line)

                for item in records[:20]:
                    name = (
                        item.get("name")
                        or item.get("description")
                        or "N/A"
                    )
                    date = item.get("date", "")
                    bucket_id = (
                        item.get("bucketid")
                        or item.get("bucket")
                        or item.get("bucketId")
                    )
                    line = f"\n  [{name}]"
                    if date:
                        line += f" ({date})"
                    if bucket_id:
                        line += f"\n    Bucket: {bucket_id}"
                    lines.append(line)
                    if on_result:
                        on_result(line)

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
                                content_line = f"    Content: {dumped[:500]}"
                                lines.append(content_line)
                                if on_result:
                                    on_result(content_line)
                        except httpx.RequestError:
                            pass
            else:
                line = f"  [i] API error {res_resp.status_code}"
                lines.append(line)
                if on_result:
                    on_result(line)

        except httpx.RequestError as e:
            line = f"  [i] Request failed: {e}"
            lines.append(line)
            if on_result:
                on_result(line)
        except Exception as e:
            line = f"  [i] Error: {e}"
            lines.append(line)
            if on_result:
                on_result(line)

        if not lines:
            return "No leak data found."

        return f"[+] Leak check for {phone}:\n" + "\n".join(lines)

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
