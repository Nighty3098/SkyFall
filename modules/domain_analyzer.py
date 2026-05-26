import asyncio
import socket
import ssl

import dns.resolver
import nmap
import requests
import whois
from fake_useragent import UserAgent
from loguru import logger


class DomainAnalyzer:
    def __init__(self) -> None:
        logger.debug("Init: DomainAnalyzer")
        self.API_KEYS = {
            "VIRUSTOTAL": "",
            "GOOGLE_SAFE": "",
            "IPINFO": "",
        }
        self.ua = UserAgent()

    async def get_robots_txt(self, domain):
        logger.debug("Trying to get robots.txt")
        try:
            response = requests.get(
                f"https://{domain}/robots.txt",
                timeout=5,
                headers={"User-Agent": self.ua.random},
            )

            return response.text

        except Exception as e:
            logger.error(f"Error: {e}")
            return f"Error getting robots.txt: {e}"

    async def get_ip_and_location(self, domain):
        logger.debug("Trying to get IP and location")
        try:
            ip = socket.gethostbyname(domain)
        except Exception as e:
            return {"error": f"Domain not resolve IP: {e}"}

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
                response = requests.get(provider["url"], timeout=4)
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
        context = ssl.create_default_context()
        try:
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
        except Exception as e:
            logger.error(f"Error SSL/TLS: {e}")
            return {"error": f"Error SSL/TLS: {e}"}

    async def get_dns_and_hosts(self, domain):
        logger.debug("Trying to get DNS and hosts info")
        try:
            record_types = ["A", "MX", "TXT", "NS", "CNAME"]
            dns_results = {}
            for r_type in record_types:
                try:
                    answers = dns.resolver.resolve(domain, r_type)
                    dns_results[r_type] = [str(rdata) for rdata in answers]
                except Exception:
                    dns_results[r_type] = []

            associated_hosts = []
            for sub in ["www", "mail", "dev", "api", "test"]:
                try:
                    sub_domain = f"{sub}.{domain}"
                    socket.gethostbyname(sub_domain)
                    associated_hosts.append(sub_domain)
                except socket.gaierror:
                    pass

            return {"dns_records": dns_results, "associated_hosts": associated_hosts}
        except Exception as e:
            logger.error(f"Error DNS: {e}")
            return {"error": f"Error DNS: {e}"}

    async def analyze_web_stack(self, domain):
        logger.debug("Trying to analyze web stack")
        try:
            response = requests.get(
                f"https://{domain}", timeout=5, headers={"User-Agent": self.ua.random}
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
            logger.error(f"Error: {e}")
            return {"error": f"Error: {e}"}

    async def get_whois_info(self, domain):
        logger.debug("Trying to get whois info")
        try:
            w = whois.whois(domain)
            return {
                "registrar": w.registrar,
                "creation_date": str(
                    w.creation_date
                    if isinstance(w.creation_date, list)
                    else w.creation_date
                ),
                "expiration_date": str(
                    w.expiration_date
                    if isinstance(w.expiration_date, list)
                    else w.expiration_date
                ),
                "name_servers": w.name_servers,
            }
        except Exception as e:
            logger.error(f"Error WHOIS: {e}")
            return {"error": f"Error WHOIS: {e}"}

    async def run_nmap_scan(self, domain):
        logger.debug("Trying to get nmap info")
        try:
            nm = nmap.PortScanner()
            nm.scan(domain, "1-65535", arguments="-T4 --open --script=vuln")

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
                res = requests.get(url, headers=headers, timeout=5)
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
                res = requests.post(url, json=payload, timeout=5)
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
            response = requests.get(url, timeout=5)
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
