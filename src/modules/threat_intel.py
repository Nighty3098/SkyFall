import asyncio
import ipaddress

import requests
from loguru import logger


def is_ip(value):
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


class ThreatIntel:
    def __init__(self, abuseipdb_api_key="", greynoise_api_key=""):
        logger.debug("Init: ThreatIntel")
        self.abuseipdb_api_key = (abuseipdb_api_key or "").strip()
        self.greynoise_api_key = (greynoise_api_key or "").strip()

    async def check_abuseipdb(self, ip):
        logger.debug("Trying to check AbuseIPDB")
        if not self.abuseipdb_api_key:
            return {
                "source": "AbuseIPDB",
                "status": "SKIPPED",
                "note": "API key not configured",
            }

        def _do():
            return requests.get(
                "https://api.abuseipdb.com/api/v2/check",
                headers={
                    "Key": self.abuseipdb_api_key,
                    "Accept": "application/json",
                },
                params={"ipAddress": ip, "maxAgeInDays": 90, "verbose": ""},
                timeout=10,
            )

        try:
            resp = await asyncio.to_thread(_do)
            if resp.status_code == 401:
                return {
                    "source": "AbuseIPDB",
                    "status": "ERROR",
                    "note": "Invalid API key",
                }
            if resp.status_code == 429:
                return {
                    "source": "AbuseIPDB",
                    "status": "ERROR",
                    "note": "Rate limited (free: 1000/day)",
                }
            if resp.status_code != 200:
                return {
                    "source": "AbuseIPDB",
                    "status": "ERROR",
                    "note": f"HTTP {resp.status_code}",
                }
            d = resp.json().get("data", {})
            score = d.get("abuseConfidenceScore", 0)
            return {
                "source": "AbuseIPDB",
                "status": "MALICIOUS"
                if score >= 50
                else ("SUSPICIOUS" if score >= 10 else "CLEAN"),
                "abuse_score": score,
                "total_reports": d.get("totalReports", 0),
                "last_reported": d.get("lastReportedAt", ""),
                "country": d.get("countryCode", ""),
                "usage_type": d.get("usageType", ""),
                "isp": d.get("isp", ""),
            }
        except Exception as e:
            logger.debug(f"AbuseIPDB failed for {ip}: {e}")
            return {"source": "AbuseIPDB", "status": "ERROR", "note": str(e)[:200]}

    async def check_greynoise(self, ip):
        logger.debug("Trying to check GreyNoise")

        def _do():
            headers = {"Accept": "application/json"}
            if self.greynoise_api_key:
                headers["key"] = self.greynoise_api_key
            return requests.get(
                f"https://api.greynoise.io/v3/community/{ip}",
                headers=headers,
                timeout=10,
            )

        try:
            resp = await asyncio.to_thread(_do)
            if resp.status_code == 404:
                return {
                    "source": "GreyNoise",
                    "status": "CLEAN",
                    "note": "IP not observed scanning",
                }
            if resp.status_code == 429:
                return {
                    "source": "GreyNoise",
                    "status": "ERROR",
                    "note": "Rate limited",
                }
            if resp.status_code != 200:
                return {
                    "source": "GreyNoise",
                    "status": "ERROR",
                    "note": f"HTTP {resp.status_code}",
                }
            d = resp.json()
            noise = d.get("noise")
            riot = d.get("riot")
            if noise is True:
                return {
                    "source": "GreyNoise",
                    "status": "NOISE",
                    "classification": d.get("classification", ""),
                    "actor": d.get("actor", ""),
                    "tags": ", ".join(d.get("tags", [])[:10]),
                    "last_seen": d.get("last_seen", ""),
                    "note": "Internet background noise, likely benign scanner",
                }
            if riot is True:
                return {
                    "source": "GreyNoise",
                    "status": "RIOT",
                    "classification": d.get("classification", ""),
                    "trust_level": d.get("trust_level", ""),
                    "note": "Benign business service (RIOT)",
                }
            return {
                "source": "GreyNoise",
                "status": "CLEAN",
                "classification": d.get("classification", "unknown"),
                "name": d.get("name", ""),
            }
        except Exception as e:
            logger.debug(f"GreyNoise failed for {ip}: {e}")
            return {"source": "GreyNoise", "status": "ERROR", "note": str(e)[:200]}

    async def check_threatfox(self, ioc):
        logger.debug("Trying to check ThreatFox")

        def _do():
            return requests.post(
                "https://threatfox-api.abuse.ch/api/v1/",
                json={"query": "search_ioc", "search_term": ioc},
                timeout=15,
            )

        try:
            resp = await asyncio.to_thread(_do)
            if resp.status_code != 200:
                return {
                    "source": "ThreatFox",
                    "status": "ERROR",
                    "note": f"HTTP {resp.status_code}",
                }
            d = resp.json()
            if d.get("query_status") != "ok" or not d.get("data"):
                return {
                    "source": "ThreatFox",
                    "status": "CLEAN",
                    "note": "Not found in ThreatFox",
                }
            entry = d["data"][0]
            conf = entry.get("confidence_level", 0)
            return {
                "source": "ThreatFox",
                "status": "MALICIOUS",
                "threat_type": entry.get("threat_type", ""),
                "malware": entry.get("malware_printable", entry.get("malware", "")),
                "confidence": conf,
                "first_seen": entry.get("first_seen", ""),
                "reference": (entry.get("reference", "") or "")[:200],
                "total_entries": len(d["data"]),
            }
        except Exception as e:
            logger.debug(f"ThreatFox failed for {ioc}: {e}")
            return {"source": "ThreatFox", "status": "ERROR", "note": str(e)[:200]}

    async def check_urlhaus(self, host):
        logger.debug("Trying to check URLHaus")

        def _do():
            return requests.post(
                "https://urlhaus-api.abuse.ch/v1/host/",
                data={"host": host},
                timeout=15,
            )

        try:
            resp = await asyncio.to_thread(_do)
            if resp.status_code != 200:
                return {
                    "source": "URLHaus",
                    "status": "ERROR",
                    "note": f"HTTP {resp.status_code}",
                }
            d = resp.json()
            if d.get("query_status") != "ok" or not d.get("urls"):
                return {
                    "source": "URLHaus",
                    "status": "CLEAN",
                    "note": "No malicious URLs for host",
                }
            urls = d["urls"]
            return {
                "source": "URLHaus",
                "status": "MALICIOUS",
                "url_count": d.get("url_count", len(urls)),
                "blacklists": d.get("blacklists", {}),
                "sample": [
                    {
                        "url": u.get("url", "")[:150],
                        "threat": u.get("threat", ""),
                        "date_added": u.get("date_added", ""),
                    }
                    for u in urls[:5]
                ],
            }
        except Exception as e:
            logger.debug(f"URLHaus failed for {host}: {e}")
            return {"source": "URLHaus", "status": "ERROR", "note": str(e)[:200]}

    async def aggregate(self, target, resolved_ip=""):
        logger.debug("Trying to aggregate threat intel")
        target = (target or "").strip()
        ip = resolved_ip or (target if is_ip(target) else "")
        results = []
        if ip and is_ip(ip):
            ab, gn = await asyncio.gather(
                self.check_abuseipdb(ip), self.check_greynoise(ip)
            )
            results += [ab, gn]
            results.append(await self.check_threatfox(ip))
        else:
            results.append(
                {
                    "source": "AbuseIPDB",
                    "status": "SKIPPED",
                    "note": "IP-only source, resolve domain first",
                }
            )
            results.append(
                {
                    "source": "GreyNoise",
                    "status": "SKIPPED",
                    "note": "IP-only source, resolve domain first",
                }
            )
            results.append(await self.check_threatfox(target))
        results.append(await self.check_urlhaus(target if not is_ip(target) else ip))
        verdict = "CLEAN"
        for r in results:
            if r.get("status") == "MALICIOUS":
                verdict = "MALICIOUS"
                break
        if verdict != "MALICIOUS" and any(
            r.get("status") in ("SUSPICIOUS", "NOISE") for r in results
        ):
            verdict = "SUSPICIOUS"
        if all(r.get("status") in ("SKIPPED", "ERROR") for r in results):
            verdict = "UNKNOWN"
        return {"target": target, "ip": ip, "verdict": verdict, "results": results}
