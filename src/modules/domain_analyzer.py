import asyncio
import ipaddress
import socket
import ssl
import uuid
from urllib.parse import urlparse

import cloudscraper
import dns.resolver
import nmap
import requests
import whois
from bs4 import BeautifulSoup
from ddgs import DDGS
from fake_useragent import UserAgent
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


class DomainAnalyzer:
    def __init__(
        self,
        virustotal_api_key,
        google_safe_api_key,
        ipinfo_api_key,
        abuseipdb_api_key: str = "",
        greynoise_api_key: str = "",
    ) -> None:
        logger.debug("Init: DomainAnalyzer")
        self.API_KEYS = {
            "VIRUSTOTAL": virustotal_api_key,
            "GOOGLE_SAFE": google_safe_api_key,
            "IPINFO": ipinfo_api_key,
            "ABUSEIPDB": abuseipdb_api_key or "",
            "GREYNOISE": greynoise_api_key or "",
        }
        self.ua = UserAgent()

    def update_threat_keys(self, abuseipdb_api_key="", greynoise_api_key=""):
        self.API_KEYS["ABUSEIPDB"] = abuseipdb_api_key or ""
        self.API_KEYS["GREYNOISE"] = greynoise_api_key or ""

    @staticmethod
    def _normalize_host(value):
        """Reduce a user supplied value to a bare lower-case host name.

        Accepts full URLs (``https://host/path``), ``host:port`` pairs, IPv4 /
        IPv6 literals and values with a trailing dot; returns ``""`` when
        nothing usable is left.
        """
        value = (value or "").strip()
        if not value:
            return ""
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            pass
        if "://" in value:
            value = urlparse(value).hostname or ""
        else:
            value = value.split("/")[0]
        if value.startswith("["):  # bracketed IPv6 with optional port
            value = value[1:].split("]", 1)[0]
        elif value.count(":") == 1:  # host:port
            value = value.split(":", 1)[0]
        return value.strip().strip(".").lower()

    @staticmethod
    def _resolve_type(host, rtype):
        """Synchronously resolve ``host`` for one record type; never raises."""
        try:
            return {str(r) for r in dns.resolver.resolve(host, rtype)}
        except Exception:
            return set()

    async def _resolve_ips(self, host):
        """Return every A/AAAA address for ``host`` as a set of strings."""
        host = self._normalize_host(host)
        if not host:
            return set()
        try:
            ipaddress.ip_address(host)
            return {host}
        except ValueError:
            pass
        a, aaaa = await asyncio.gather(
            asyncio.to_thread(self._resolve_type, host, "A"),
            asyncio.to_thread(self._resolve_type, host, "AAAA"),
        )
        return a | aaaa

    async def get_robots_txt(self, domain):
        logger.debug("Trying to get robots.txt")
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"https://{domain}/robots.txt",
                timeout=5,
                headers={"User-Agent": self.ua.random},
            )

            return "\n".join(
                [
                    divider(),
                    title(f"Robots.txt: {domain}"),
                    response.text,
                    end_of("robots.txt"),
                    divider(),
                ]
            )

        except Exception as e:
            logger.error(f"Robots.txt: Error: {e}")
            return "\n".join(
                [
                    divider(),
                    title(f"Robots.txt: {domain}"),
                    error(f"Error getting robots.txt: {e}"),
                    end_of("robots.txt"),
                    divider(),
                ]
            )

    async def get_ip_and_location(self, domain):
        logger.debug("Trying to get IP and location")
        ips = await self._resolve_ips(domain)
        if not ips:
            return {"error": "GET IP: Domain did not resolve to any IP"}

        # Geo providers (the free ip-api tier in particular) are IPv4-only, so
        # pick an IPv4 address when one exists and keep the rest for callers.
        ip = next((addr for addr in sorted(ips) if ":" not in addr), sorted(ips)[0])
        all_ips = sorted(ips)

        ipinfo_url = f"https://ipinfo.io/{ip}/json"
        if self.API_KEYS["IPINFO"]:
            ipinfo_url += "?token=" + self.API_KEYS["IPINFO"]

        providers = [
            {
                "url": f"https://ipapi.co/{ip}/json/",
                "parser": lambda res: {
                    "ip": ip,
                    "country": res.get("country_name"),
                    "city": res.get("city"),
                    "asn": res.get("org"),
                    "lat": res.get("latitude"),
                    "lon": res.get("longitude"),
                    "provider": "ipapi.co",
                },
            },
            {
                "url": f"http://ip-api.com/json/{ip}",
                "parser": lambda res: {
                    "ip": ip,
                    "country": res.get("country"),
                    "city": res.get("city"),
                    "asn": res.get("as"),
                    "lat": res.get("lat"),
                    "lon": res.get("lon"),
                    "provider": "ip-api.com",
                },
            },
            {
                "url": ipinfo_url,
                "parser": lambda res: {
                    "ip": ip,
                    "country": res.get("country"),
                    "city": res.get("city"),
                    "asn": res.get("org"),
                    "lat": res.get("loc", "").split(",")[0] if res.get("loc") else None,
                    "lon": res.get("loc", "").split(",")[1] if res.get("loc") else None,
                    "provider": "ipinfo.io",
                },
            },
        ]

        errors = []
        for provider in providers:
            try:
                response = await asyncio.to_thread(
                    requests.get, provider["url"], timeout=4
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "fail":
                        continue
                    result = provider["parser"](data)
                    result["all_ips"] = all_ips
                    return result
            except Exception as err:
                logger.error(f"Error {provider['url']}: {err}")
                errors.append(f"Error {provider['url']}: {err}")

        return {
            "ip": ip,
            "all_ips": all_ips,
            "error": "GEO Error.",
            "details": errors,
        }

    async def get_domains_on_ip(self, ip):
        logger.debug(f"Trying to find domains on IP: {ip}")
        result = {"ip": ip, "ptr": [], "hostnames": [], "hacker_target": []}

        try:
            ip_addr = ipaddress.ip_address(ip.strip())
        except ValueError:
            result["error"] = f"Invalid IP address: {ip}"
            return result

        def _clean(entries):
            cleaned = []
            for entry in entries:
                host = str(entry).strip().rstrip(".").lower()
                if host:
                    cleaned.append(host)
            return cleaned

        try:
            answers = await asyncio.to_thread(
                dns.resolver.resolve, ip_addr.reverse_pointer, "PTR"
            )
            result["ptr"] = _clean(str(rdata) for rdata in answers)
        except Exception as e:
            logger.debug(f"PTR lookup failed for {ip}: {e}")

        try:
            response = await asyncio.to_thread(
                requests.get,
                f"https://internetdb.shodan.io/{ip}",
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                result["hostnames"] = _clean(data.get("hostnames", []))
        except Exception as e:
            logger.debug(f"InternetDB failed for {ip}: {e}")

        try:
            response = await asyncio.to_thread(
                requests.get,
                f"https://api.hackertarget.com/reverseiplookup/?q={ip}",
                timeout=10,
            )
            if response.status_code == 200 and "error" not in response.text.lower():
                result["hacker_target"] = _clean(response.text.strip().split("\n"))
        except Exception as e:
            logger.debug(f"HackerTarget failed for {ip}: {e}")

        raw = set(result["ptr"] + result["hostnames"] + result["hacker_target"])
        all_domains = set()
        for entry in raw:
            try:
                ipaddress.ip_address(entry)
                continue
            except ValueError:
                pass
            if ":" in entry:  # leftover IPv6 / port notation
                continue
            all_domains.add(entry)
        result["total_unique"] = len(all_domains)
        result["all_domains"] = sorted(all_domains)
        logger.info(f"Domains on IP {ip}: {len(all_domains)} unique domains found")

        return result

    async def get_ssl_tls_info(self, domain):
        logger.debug("Trying to get SSL and TLS info")

        def _fetch_ssl():
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    return {
                        "version": ssock.version(),
                        "cipher": ssock.cipher(),
                        "issuer": {k: v for t in cert.get("issuer", []) for k, v in t},
                        "subject": {
                            k: v for t in cert.get("subject", []) for k, v in t
                        },
                        "expires": cert.get("notAfter"),
                    }

        try:
            return await asyncio.to_thread(_fetch_ssl)
        except Exception as e:
            logger.error(f"Error SSL/TLS: {e}")
            return {"error": f"Error SSL/TLS: {e}"}

    async def get_http_headers(self, domain):
        logger.debug("Trying to get HTTP headers")
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"https://{domain}",
                timeout=5,
                headers={"User-Agent": self.ua.random},
                allow_redirects=True,
            )
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "final_url": response.url,
            }
        except Exception as e:
            logger.error(f"HTTP Headers Error: {e}")
            return {"error": f"HTTP Headers Error: {e}"}

    async def detect_waf(self, domain):
        logger.debug("Trying to detect WAF")
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"https://{domain}",
                timeout=5,
                headers={"User-Agent": self.ua.random},
            )
            headers = {k.lower(): v for k, v in response.headers.items()}
            server = headers.get("server", "").lower()

            waf_signatures = {
                "cloudflare": ["cf-ray", "cloudflare"],
                "akamai": ["akamai", "akamaighost"],
                "cloudfront": ["cloudfront", "x-amz-cf-id"],
                "fastly": ["fastly", "x-fastly"],
                "sucuri": ["sucuri", "x-sucuri-id"],
                "imperva": ["imperva", "incap_ses"],
                "fortinet": ["fortiweb"],
                "barracuda": ["barracounter"],
                "f5": ["bigip", "f5"],
                "dosarrest": ["dosarrest"],
                "radware": ["radware"],
            }

            detected = []
            for waf_name, signatures in waf_signatures.items():
                for sig in signatures:
                    header_match = any(sig in str(v).lower() for v in headers.values())
                    if header_match or sig in server:
                        detected.append(waf_name)
                        break

            return {
                "waf_detected": bool(detected),
                "waf_providers": detected if detected else ["NONE"],
                "server": headers.get("server", "Unknown"),
            }
        except Exception as e:
            logger.error(f"WAF Detection Error: {e}")
            return {"error": f"WAF Detection Error: {e}"}

    async def get_dns(self, domain):
        logger.debug("Trying to get DNS info")
        try:
            record_types = ["A", "MX", "TXT", "NS", "CNAME"]
            dns_results = {}
            for r_type in record_types:
                try:
                    answers = await asyncio.to_thread(
                        dns.resolver.resolve, domain, r_type
                    )
                    dns_results[r_type] = [str(rdata) for rdata in answers]
                except Exception:
                    dns_results[r_type] = []

            soa = {}
            try:
                soa_record = await asyncio.to_thread(
                    dns.resolver.resolve, domain, "SOA"
                )
                soa = soa_record[0]
                dns_results["SOA"] = {
                    "mname": str(soa.mname),
                    "rname": str(soa.rname),
                    "serial": soa.serial,
                    "refresh": soa.refresh,
                    "retry": soa.retry,
                    "expire": soa.expire,
                    "minimum": soa.minimum,
                }
            except Exception:
                dns_results["SOA"] = {}

            ns_ips = {}
            for ns in dns_results.get("NS", []):
                try:
                    answers = await asyncio.to_thread(dns.resolver.resolve, ns, "A")
                    ns_ips[ns] = [str(rdata) for rdata in answers]
                except Exception:
                    ns_ips[ns] = []
            dns_results["NS_IP"] = ns_ips

            return dns_results
        except Exception as e:
            logger.error(f"Error DNS: {e}")
            return {"error": f"Error DNS: {e}"}

    async def get_hosts(self, domain):
        logger.debug("Trying to get associated hosts")
        try:
            domain = self._normalize_host(domain)
            if not domain:
                return []
            # Reuse the shared brute-force wordlist instead of a second,
            # hard-coded list so the check stays consistent with
            # ``find_subdomains``.
            labels = self.SUBDOMAIN_WORDLIST[:8]
            hosts = [f"{label}.{domain}" for label in labels]
            resolved = await asyncio.gather(*[self._resolve_ips(h) for h in hosts])
            return [host for host, ips in zip(hosts, resolved, strict=True) if ips]
        except Exception as e:
            logger.error(f"Error hosts: {e}")
            return {"error": f"Error hosts: {e}"}

    async def analyze_web_stack(self, domain):
        logger.debug("Trying to analyze web stack")
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"https://{domain}",
                timeout=5,
                headers={"User-Agent": self.ua.random},
            )
            headers = dict(response.headers)
            html = response.text.lower()

            waf = "NOT FOUND"
            if "cloudflare" in headers.get("Server", "").lower() or "cf-ray" in headers:
                waf = "Cloudflare"
            elif (
                "sucuri" in headers.get("X-Sucuri-ID", "")
                or "x-sucuri-cache" in headers
            ):
                waf = "Sucuri"

            tech_stack = []
            if "nginx" in headers.get("Server", "").lower():
                tech_stack.append("Nginx")
            if "apache" in headers.get("Server", "").lower():
                tech_stack.append("Apache")
            if "wp-content" in html:
                tech_stack.append("WordPress CMS")
            if "bitrix" in html:
                tech_stack.append("1C-Bitrix")
            if "jquery" in html:
                tech_stack.append("jQuery")

            return {
                "http_headers": headers,
                "web_server": headers.get("Server", "Not resolve"),
                "waf": waf,
                "detected_tech": tech_stack if tech_stack else "DEFAULT HTML/JS",
            }
        except Exception as e:
            logger.error(f"Stack Error: {e}")
            return {"error": f"Stack Error: {e}"}

    async def get_whois_info(self, domain):
        logger.debug("Trying to get whois info")
        try:
            w = await asyncio.to_thread(whois.whois, domain)
            return w
        except Exception as e:
            logger.error(f"Error WHOIS: {e}")
            return {"error": f"Error WHOIS: {e}"}

    async def run_nmap_scan(self, domain, ports="1-1024"):
        logger.debug("Trying to get nmap info")
        try:
            nm = nmap.PortScanner()
            await asyncio.to_thread(
                nm.scan, domain, ports, arguments="-T4 --open --script=vuln"
            )

            scan_data = {}
            for host in nm.all_hosts():
                scan_data[host] = []
                for proto in nm[host].all_protocols():
                    for port in nm[host][proto].keys():
                        port_info = nm[host][proto][port]
                        script_output = port_info.get("script")
                        domain_vulns = ""
                        if script_output:
                            for script_name, output in script_output.items():
                                domain_vulns += f" '{script_name}' "
                        scan_data[host].append(
                            {
                                "port": port,
                                "state": port_info["state"],
                                "service": port_info["name"],
                                "version": port_info["version"],
                                "product": port_info["product"],
                                "extrainfo": port_info["extrainfo"],
                                "conf": port_info["conf"],
                                "vulns": domain_vulns,
                            }
                        )
            return scan_data if scan_data else "ALL PORT CLOSED"
        except Exception as e:
            logger.error(f"Error NMAP: {e}")
            return {"error": f"NMAP not found: {e}"}

    async def check_malware_reputation(self, domain, include_intel=True):
        logger.debug("Trying to get malware info")
        sources = []

        if self.API_KEYS["VIRUSTOTAL"]:
            try:
                url = f"https://www.virustotal.com/api/v3/domains/{domain}"
                headers = {"x-apikey": self.API_KEYS["VIRUSTOTAL"]}
                res = await asyncio.to_thread(
                    requests.get, url, headers=headers, timeout=5
                )
                if res.status_code == 200:
                    stats = (
                        res.json()
                        .get("data", {})
                        .get("attributes", {})
                        .get("last_analysis_stats", {})
                    )
                    malicious = stats.get("malicious", 0)
                    sources.append(
                        {
                            "source": "VirusTotal",
                            "status": "MALICIOUS" if malicious > 0 else "CLEAN",
                            "malicious_votes": malicious,
                            "harmless": stats.get("harmless", 0),
                            "undetected": stats.get("undetected", 0),
                        }
                    )
            except Exception as e:
                logger.error(f"Error VirusTotal API: {e}")
                sources.append(
                    {"source": "VirusTotal", "status": "ERROR", "note": str(e)[:200]}
                )

        if self.API_KEYS["GOOGLE_SAFE"]:
            try:
                url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={self.API_KEYS['GOOGLE_SAFE']}"
                payload = {
                    "client": {"clientId": "scanner-app", "clientVersion": "1.0.0"},
                    "threatInfo": {
                        "threatTypes": [
                            "MALWARE",
                            "SOCIAL_ENGINEERING",
                            "UNWANTED_SOFTWARE",
                        ],
                        "platformTypes": ["ANY_PLATFORM"],
                        "threatEntryTypes": ["URL"],
                        "threatEntries": [{"url": f"http://{domain}/"}],
                    },
                }
                res = await asyncio.to_thread(
                    requests.post, url, json=payload, timeout=5
                )
                if res.status_code == 200:
                    matches = res.json().get("matches", [])
                    sources.append(
                        {
                            "source": "Google Safe Browsing",
                            "status": "MALICIOUS" if matches else "CLEAN",
                            "matches": len(matches),
                        }
                    )
            except Exception as e:
                logger.error(f"Error Google Safe Browsing API: {e}")
                sources.append(
                    {
                        "source": "Google Safe Browsing",
                        "status": "ERROR",
                        "note": str(e)[:200],
                    }
                )

        try:
            url = f"https://www.crdf.fr/{domain}"
            response = await asyncio.to_thread(requests.get, url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                sources.append(
                    {
                        "source": "CRDF Labs (FREE)",
                        "status": "MALICIOUS"
                        if data.get("danger_score", 0) > 0
                        else "CLEAN",
                    }
                )
        except Exception as e:
            logger.debug(f"CRDF failed: {e}")

        # ── AbuseIPDB / GreyNoise / ThreatFox / URLHaus ──
        verdict = ""
        if include_intel:
            try:
                intel = await self.check_threat_intel(domain)
                if isinstance(intel, dict):
                    for r in intel.get("results", []):
                        if r.get("status") not in ("SKIPPED",):
                            sources.append(r)
                    verdict = intel.get("verdict", "")
            except Exception as e:
                logger.debug(f"Threat intel aggregation failed: {e}")

        if not sources:
            return {"status": "CLEAN", "note": "API KEYS NOT FOUND", "sources": []}

        overall = "CLEAN"
        for s in sources:
            if s.get("status") == "MALICIOUS":
                overall = "MALICIOUS"
                break
        if overall != "MALICIOUS" and any(
            s.get("status") in ("SUSPICIOUS", "NOISE") for s in sources
        ):
            overall = "SUSPICIOUS"
        return {"status": overall, "verdict": verdict or overall, "sources": sources}

    async def check_threat_intel(self, target):
        logger.debug("Trying to get threat intel")
        from src.modules.threat_intel import ThreatIntel

        target = (
            (target or "")
            .strip()
            .lower()
            .removeprefix("http://")
            .removeprefix("https://")
            .split("/")[0]
        )
        resolved_ip = ""
        try:
            resolved_ip = await asyncio.to_thread(socket.gethostbyname, target)
        except Exception:
            resolved_ip = ""
        ti = ThreatIntel(
            abuseipdb_api_key=self.API_KEYS.get("ABUSEIPDB", ""),
            greynoise_api_key=self.API_KEYS.get("GREYNOISE", ""),
        )
        return await ti.aggregate(target, resolved_ip=resolved_ip)

    async def scan_js_secrets(self, domain, max_files=15):
        logger.debug("Trying to scan JS secrets")
        from src.modules.js_secrets import scan_domain_js

        try:
            text, _ = await scan_domain_js(domain, max_files=max_files)
            return text
        except Exception as e:
            logger.error(f"JS secrets scan error: {e}")
            return "\n".join(
                [
                    divider(),
                    title(f"JS Secrets: {domain}"),
                    error(str(e)),
                    end_of("js secrets"),
                    divider(),
                ]
            )

    SUBDOMAIN_WORDLIST = [
        "www",
        "mail",
        "ftp",
        "api",
        "dev",
        "test",
        "stage",
        "staging",
        "prod",
        "admin",
        "portal",
        "blog",
        "shop",
        "forum",
        "vpn",
        "remote",
        "mx",
        "webmail",
        "cpanel",
        "whm",
        "ns1",
        "ns2",
        "dns",
        "cdn",
        "static",
        "assets",
        "img",
        "images",
        "media",
        "files",
        "docs",
        "drive",
        "cloud",
        "app",
        "mobile",
        "beta",
        "alpha",
        "demo",
        "sandbox",
        "internal",
        "intranet",
        "extranet",
        "crm",
        "erp",
        "hr",
        "pay",
        "billing",
        "secure",
        "login",
        "sso",
        "auth",
        "oauth",
        "git",
        "gitlab",
        "github",
        "jira",
        "confluence",
        "jenkins",
        "ci",
        "cd",
        "monitoring",
        "grafana",
        "kibana",
        "elastic",
        "db",
        "mysql",
        "postgres",
        "redis",
        "mongo",
        "kafka",
        "rabbit",
        "proxy",
        "gw",
        "gateway",
        "edge",
        "origin",
        "m",
        "wap",
        "old",
        "new",
        "v2",
        "vpn2",
        "backup",
        "mirror",
        "status",
        "health",
        "metrics",
        "logs",
        "sentry",
        "analytics",
        "ads",
        "cdn1",
        "cdn2",
        "s1",
        "s2",
        "lb",
        "balancer",
        "k8s",
        "docker",
        "registry",
        "artifacts",
        "packages",
        "releases",
        "support",
        "help",
        "helpdesk",
        "ticket",
        "chat",
        "meet",
        "zoom",
        "call",
        "video",
        "stream",
        "live",
        "news",
        "press",
        "events",
        "careers",
        "jobs",
        "partner",
        "partners",
        "reseller",
        "affiliate",
        "checkout",
        "cart",
        "order",
        "account",
        "profile",
        "user",
        "dashboard",
        "console",
        "panel",
        "manage",
        "my",
        "id",
        "devops",
        "secops",
        "soc",
        "siem",
        "waf",
        "fw",
        "ids",
        "honeypot",
    ]

    async def _subdomains_ddg(self, domain):
        def _search():
            local = set()
            try:
                with DDGS() as ddgs:
                    for r in ddgs.text(f"site:{domain} -www", max_results=200):
                        url = r.get("href")
                        if url:
                            host = urlparse(url).hostname
                            if host and (host == domain or host.endswith("." + domain)):
                                local.add(host.lower())
            except Exception as e:
                logger.debug(f"DDG subdomains failed: {e}")
            return local

        return await asyncio.to_thread(_search)

    async def _subdomains_crtsh(self, domain):
        def _fetch():
            try:
                scraper = cloudscraper.create_scraper()
                resp = scraper.get(
                    f"https://crt.sh/?q=%25.{domain}&output=json",
                    timeout=30,
                    headers={"User-Agent": self.ua.random},
                )
                if resp.status_code != 200:
                    return set()
                out = set()
                for entry in resp.json():
                    for name in str(entry.get("name_value", "")).split("\n"):
                        name = name.strip().lower().lstrip("*.")
                        if name == domain or name.endswith("." + domain):
                            out.add(name)
                return out
            except Exception as e:
                logger.debug(f"crt.sh subdomains failed: {e}")
                return set()

        return await asyncio.to_thread(_fetch)

    async def _subdomains_otx(self, domain):
        def _fetch():
            try:
                resp = requests.get(
                    f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns",
                    timeout=15,
                    headers={"User-Agent": self.ua.random},
                )
                if resp.status_code != 200:
                    return set()
                out = set()
                for row in resp.json().get("passive_dns", []):
                    host = str(row.get("hostname", "")).lower().lstrip("*.")
                    if host == domain or host.endswith("." + domain):
                        out.add(host)
                return out
            except Exception as e:
                logger.debug(f"OTX subdomains failed: {e}")
                return set()

        return await asyncio.to_thread(_fetch)

    async def _subdomains_hackertarget(self, domain):
        def _fetch():
            try:
                resp = requests.get(
                    f"https://api.hackertarget.com/hostsearch/?q={domain}", timeout=15
                )
                if resp.status_code != 200 or "error" in resp.text.lower():
                    return set()
                out = set()
                for ln in resp.text.strip().split("\n"):
                    host = ln.split(",")[0].strip().lower()
                    if host == domain or host.endswith("." + domain):
                        out.add(host)
                return out
            except Exception as e:
                logger.debug(f"HackerTarget subdomains failed: {e}")
                return set()

        return await asyncio.to_thread(_fetch)

    async def _subdomains_anubis(self, domain):
        def _fetch():
            try:
                resp = requests.get(
                    f"https://jldc.me/anubis/subdomains/{domain}",
                    timeout=15,
                    headers={"User-Agent": self.ua.random},
                )
                if resp.status_code != 200:
                    return set()
                data = resp.json()
                subs = data if isinstance(data, list) else data.get("subdomains", [])
                out = set()
                for s in subs:
                    host = str(s).strip().lower().lstrip("*.")
                    if host == domain or host.endswith("." + domain):
                        out.add(host)
                return out
            except Exception as e:
                logger.debug(f"AnubisDB subdomains failed: {e}")
                return set()

        return await asyncio.to_thread(_fetch)

    async def _subdomains_brute(self, domain, wordlist=None, concurrency=40):
        words = wordlist or self.SUBDOMAIN_WORDLIST
        sem = asyncio.Semaphore(concurrency)
        found = set()

        # Detect wildcard DNS first: if ``*.domain`` resolves, every label
        # would otherwise appear to exist and flood the results.
        wildcard = await self._resolve_ips(f"{uuid.uuid4().hex}.{domain}")
        if wildcard:
            logger.info(
                f"Wildcard DNS detected for {domain} "
                f"({', '.join(sorted(wildcard))}); filtering brute hits"
            )

        async def _probe(label):
            async with sem:
                host = f"{label}.{domain}"
                ips = await self._resolve_ips(host)
                if not ips:
                    return
                if wildcard and ips <= wildcard:
                    return
                found.add(host.lower())

        await asyncio.gather(*[_probe(w) for w in words])
        return found

    async def find_subdomains(self, domain, use_brute=True, wordlist=None):
        logger.debug("Trying to find subdomains")
        try:
            domain = self._normalize_host(domain)
            if not domain:
                return "\n".join([divider(), error("Invalid domain"), divider()])
            per_source = {}
            ddg, crt, otx, ht, anubis = await asyncio.gather(
                self._subdomains_ddg(domain),
                self._subdomains_crtsh(domain),
                self._subdomains_otx(domain),
                self._subdomains_hackertarget(domain),
                self._subdomains_anubis(domain),
            )
            per_source = {
                "DuckDuckGo": ddg,
                "crt.sh": crt,
                "AlienVault OTX": otx,
                "HackerTarget": ht,
                "AnubisDB": anubis,
            }
            brute = set()
            if use_brute:
                brute = await self._subdomains_brute(domain, wordlist=wordlist)
                per_source["DNS brute"] = brute

            all_subs = sorted(set().union(*per_source.values())) if per_source else []
            lines = [divider(), title(f"Subdomains: {domain}")]
            lines.append(kv("Total unique", len(all_subs)))
            for src, subs in per_source.items():
                lines.append(section(f"{src} ({len(subs)})"))
                for sub in sorted(subs)[:100]:
                    lines.append(bullet(sub))
                if len(subs) > 100:
                    lines.append(line(f"… +{len(subs) - 100} more from {src}"))
            if all_subs:
                lines.append("")
                lines.append(section(f"Combined ({len(all_subs)})"))
                for sub in all_subs:
                    lines.append(bullet(sub))
            else:
                lines.append(info("No subdomains found"))
            lines.extend([end_of("subdomains"), divider()])
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Subdomains: Error: {e}")
            return "\n".join(
                [
                    divider(),
                    title(f"Subdomains: {domain}"),
                    error(str(e)),
                    end_of("subdomains"),
                    divider(),
                ]
            )

    async def get_security_txt(self, domain):
        logger.debug("Trying to find security.txt")

        try:
            response = await asyncio.to_thread(
                requests.get, f"https://{domain}/.well-known/security.txt", timeout=5
            )

            lines = [divider(), title(f"Security.txt: {domain}")]
            if response.status_code == 404:
                lines.append(info("Not Found"))
            else:
                lines.append(response.text)
            lines.extend([end_of("security.txt"), divider()])
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Security.txt: Error: {e}")
            return "\n".join(
                [
                    divider(),
                    title(f"Security.txt: {domain}"),
                    error(str(e)),
                    end_of("security.txt"),
                    divider(),
                ]
            )

    async def get_cookies(self, domain):
        logger.debug("Trying to get cookies")

        try:
            response = await asyncio.to_thread(
                requests.get, f"https://{domain}", timeout=5
            )

            cookie_lines = []
            for cookie in response.cookies:
                http_only = cookie.has_nonstandard_attr("HttpOnly")
                cookie_lines.append(kv(cookie.name, cookie.value))
                cookie_lines.append(
                    line(
                        f"domain={cookie.domain}, path={cookie.path},"
                        f" secure={cookie.secure}, httpOnly={http_only}",
                    )
                )

            lines = [divider(), title(f"Cookies: {domain}")]
            if cookie_lines:
                lines.extend(cookie_lines)
            else:
                lines.append(info("No cookies"))
            lines.extend([end_of("cookies"), divider()])
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Cookies: Error: {e}")
            return "\n".join(
                [
                    divider(),
                    title(f"Cookies: {domain}"),
                    error(str(e)),
                    end_of("cookies"),
                    divider(),
                ]
            )

    async def get_certificate_transparency(self, domain):
        logger.debug("Trying to get Certificate Transparency logs")
        try:
            scraper = cloudscraper.create_scraper()
            url = f"https://crt.sh/?q={domain}&output=json"
            response = await asyncio.to_thread(
                scraper.get,
                url,
                timeout=30,
                headers={"User-Agent": self.ua.random},
            )
            if response.status_code != 200:
                return error(f"crt.sh returned {response.status_code}")

            data = response.json()
            if not data:
                return info("No certificates found")

            unique_domains = set()
            unique_issuers = set()
            certs = []
            for entry in data[:100]:
                names = entry.get("name_value", "")
                for n in names.split("\n"):
                    unique_domains.add(n.strip().lower())
                issuer = entry.get("issuer_name", "")
                unique_issuers.add(issuer)
                certs.append(
                    {
                        "id": entry.get("id"),
                        "issuer": issuer,
                        "common_name": entry.get("common_name", ""),
                        "not_before": entry.get("not_before", ""),
                        "not_after": entry.get("not_after", ""),
                        "serial": entry.get("serial_number", ""),
                    }
                )

            lines = [
                divider(),
                title("Certificate Transparency: detail"),
                kv("Total certs found", min(len(data), 100)),
                kv("Unique domains", len(unique_domains)),
                kv("Unique issuers (CAs)", len(unique_issuers)),
                "",
                section("Discovered domains"),
            ]
            for d in sorted(unique_domains):
                lines.append(bullet(d))
            lines.append("")
            lines.append(section("Recent certificates (up to 100)"))
            for c in certs[:20]:
                lines.append(
                    line(
                        f"#{c['id']} | {c['common_name']} | "
                        f"{c['not_before']} → {c['not_after']}"
                    )
                )
                lines.append(line(f"issuer: {c['issuer']}"))
                lines.append(line(f"serial: {c['serial']}"))
                lines.append("")

            lines.extend([end_of("certificate transparency"), divider()])
            return "\n".join(lines)

        except requests.exceptions.Timeout:
            return error("crt.sh request timed out (30s)")
        except requests.exceptions.RequestException as e:
            logger.error(f"Certificate Transparency request error: {e}")
            return error(f"Certificate Transparency request error: {e}")
        except Exception as e:
            logger.error(f"Certificate Transparency error: {e}")
            return error(f"Certificate Transparency error: {e}")

    async def get_social_tags(self, domain):
        logger.debug("Trying to get social tags")
        try:
            response = await asyncio.to_thread(
                requests.get, f"https://{domain}", timeout=5
            )
            soup = BeautifulSoup(response.text, "html.parser")

            tags = {}
            for meta in soup.find_all("meta"):
                key = meta.get("property") or meta.get("name")
                if not key:
                    continue
                if isinstance(key, list):
                    key = " ".join(key)
                if key.startswith("og:") or key.startswith("twitter:"):
                    tags[key] = meta.get("content", "")

            lines = [divider(), title(f"Social Tags: {domain}")]
            if not tags:
                lines.append(info("Not found"))
            else:
                lines.extend(kv(k, v) for k, v in tags.items())
            lines.extend([end_of("social tags"), divider()])
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Social tags: Error: {e}")
            return "\n".join(
                [
                    divider(),
                    title(f"Social Tags: {domain}"),
                    error(str(e)),
                    end_of("social tags"),
                    divider(),
                ]
            )
