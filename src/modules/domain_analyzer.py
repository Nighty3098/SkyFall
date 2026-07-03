import asyncio
import socket
import ssl
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

from src.ui.output_formatter import bullet, divider, end_of, error, info, kv, line, section, title


class DomainAnalyzer:
    def __init__(self, virustotal_api_key, google_safe_api_key, ipinfo_api_key) -> None:
        logger.debug("Init: DomainAnalyzer")
        self.API_KEYS = {
            "VIRUSTOTAL": virustotal_api_key,
            "GOOGLE_SAFE": google_safe_api_key,
            "IPINFO": ipinfo_api_key,
        }
        self.ua = UserAgent()

    async def get_robots_txt(self, domain):
        logger.debug("Trying to get robots.txt")
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"https://{domain}/robots.txt",
                timeout=5,
                headers={"User-Agent": self.ua.random},
            )

            return "\n".join([
                divider(),
                title(f"Robots.txt: {domain}"),
                response.text,
                end_of("robots.txt"),
                divider(),
            ])

        except Exception as e:
            logger.error(f"Robots.txt: Error: {e}")
            return "\n".join([
                divider(),
                title(f"Robots.txt: {domain}"),
                error(f"Error getting robots.txt: {e}"),
                end_of("robots.txt"),
                divider(),
            ])

    async def get_ip_and_location(self, domain):
        logger.debug("Trying to get IP and location")
        try:
            ip = await asyncio.to_thread(socket.gethostbyname, domain)
        except Exception as e:
            return {"error": f"GET IP: Domain not resolve IP: {e}"}

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
                    return provider["parser"](data)
            except Exception as err:
                logger.error(f"Error {provider['url']}: {err}")
                errors.append(f"Error {provider['url']}: {err}")

        return {
            "ip": ip,
            "error": "GEO Error.",
            "details": errors,
        }

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
            associated_hosts = []
            for sub in ["www", "mail", "dev", "api", "test"]:
                try:
                    sub_domain = f"{sub}.{domain}"
                    await asyncio.to_thread(socket.gethostbyname, sub_domain)
                    associated_hosts.append(sub_domain)
                except socket.gaierror:
                    pass

            return associated_hosts
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

    async def run_nmap_scan(self, domain):
        logger.debug("Trying to get nmap info")
        try:
            nm = nmap.PortScanner()
            await asyncio.to_thread(
                nm.scan, domain, "1-65535", arguments="-T4 --open --script=vuln"
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

    async def check_malware_reputation(self, domain):
        logger.debug("Trying to get malware info")

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
                    return {
                        "source": "VirusTotal API",
                        "malicious_votes": stats.get("malicious", 0),
                        "status": "OK",
                    }
            except Exception as e:
                logger.error(f"Error VirusTotal API: {e}")
                return {"error": f"Error VirusTotal API: {e}"}

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
                    return {
                        "source": "Google Safe Browsing",
                        "status": "DANGER" if matches else "CLEAN",
                    }
            except Exception as e:
                logger.error(f"Error Google Safe Browsing API: {e}")
                return {"error": f"Error Google Safe Browsing API: {e}"}

        try:
            url = f"https://www.crdf.fr/{domain}"
            response = await asyncio.to_thread(requests.get, url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "source": "CRDF Labs (FREE)",
                    "status": "DANGER"
                    if data.get("danger_score", 0) > 0
                    else "CLEAN / NOT FOUND IN BLACKLIST",
                }
        except Exception as e:
            logger.error(f"Error: {e}")

        return {
            "status": "CLEAN",
            "note": "API KEYS NOT FOUND",
        }

    async def find_subdomains(self, domain):
        logger.debug("Trying to find subdomains")
        try:
            dork = f"site:{domain} -www"
            max_results = 1000000000000
            discovered_subdomains = set()

            def _search():
                local_results = set()
                with DDGS() as ddgs:
                    results = ddgs.text(dork, max_results=max_results)
                    for r in results:
                        url = r.get("href")
                        if url:
                            parsed_url = urlparse(url)
                            hostname = parsed_url.hostname
                            if hostname and hostname.endswith(domain):
                                local_results.add(hostname)
                return local_results

            discovered_subdomains = await asyncio.to_thread(_search)

            lines = [divider(), title(f"Subdomains: {domain}")]
            for sub in sorted(discovered_subdomains):
                lines.append(bullet(sub))
            lines.extend([end_of("subdomains"), divider()])
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Subdomains: Error: {e}")
            return "\n".join([
                divider(),
                title(f"Subdomains: {domain}"),
                error(str(e)),
                end_of("subdomains"),
                divider(),
            ])

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
            return "\n".join([
                divider(),
                title(f"Security.txt: {domain}"),
                error(str(e)),
                end_of("security.txt"),
                divider(),
            ])

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
            return "\n".join([
                divider(),
                title(f"Cookies: {domain}"),
                error(str(e)),
                end_of("cookies"),
                divider(),
            ])

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
            return "\n".join([
                divider(),
                title(f"Social Tags: {domain}"),
                error(str(e)),
                end_of("social tags"),
                divider(),
            ])
