import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import info, kv, render, set_output

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.domain_analyzer import DomainAnalyzer


DOMAIN_EDITS = (
    "whoisDomainEdit",
    "infraDomainEdit",
    "webSurfaceDomainEdit",
    "discoveryDomainEdit",
    "securityDomainEdit",
)


class DomainController:
    def __init__(
        self,
        ui: "QMainWindow",
        domain_analyzer: "DomainAnalyzer",
    ):
        logger.debug("Init: DomainController")

        self.ui = ui
        self.domain_analyzer = domain_analyzer
        self.domain = ""
        self._whois_cache = None
        self._whois_cache_domain = ""
        self._ip2location_cache = {}

    def set_domain(self, domain):
        self.domain = (domain or "").strip()

    def _resolve_domain(self, *edit_names):
        for name in edit_names:
            edit = getattr(self.ui, name, None)
            if edit is None or not hasattr(edit, "text"):
                continue
            value = (edit.text() or "").strip()
            if value:
                self.set_domain(value)
                return self.domain
        return self.domain

    def _is_checked(self, name):
        widget = getattr(self.ui, name, None)
        return widget is not None and widget.isChecked()

    def _debug(self, name):
        return getattr(self.ui, name, None)

    async def analyze_domain(self):
        """Compatibility: run enabled checks from all category tabs."""
        if not self.domain:
            self._resolve_domain(*DOMAIN_EDITS)
        if not self.domain:
            return
        progress = getattr(self.ui, "domainProgress", None)
        if progress is not None:
            progress.setValue(0)
        await self.analyze_infra(domain=self.domain)
        await self.analyze_web_surface(domain=self.domain)
        await self.analyze_discovery(domain=self.domain)
        await self.analyze_security(domain=self.domain, reuse_ip2location=True)
        await self.analyze_whois(domain=self.domain)
        if progress is not None:
            progress.setValue(100)

    async def analyze_infra(self, domain=None):
        domain = (domain or self._resolve_domain("infraDomainEdit") or "").strip()
        if not domain:
            return
        self.set_domain(domain)

        if self._is_checked("domainLocationCheck"):
            dbg = self._debug("serverLocationDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.get_ip_and_location(domain)
                set_output(dbg, render(result))

        if self._is_checked("domainDNSCheck"):
            dbg = self._debug("serverDnsAnalyzeDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                dns_info = await self.domain_analyzer.get_dns(domain)
                set_output(dbg, render(dns_info))

        if self._is_checked("domainSSLCheck"):
            dbg = self._debug("serverTlsDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                ssl_info = await self.domain_analyzer.get_ssl_tls_info(domain)
                set_output(dbg, render(ssl_info))

        if self._is_checked("domainNmapCheck"):
            dbg = self._debug("serverNmapDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.run_nmap_scan(domain)
                set_output(dbg, render(result))

        if self._is_checked("domainIP2LocationGeoCheck"):
            dbg = self._debug("ip2locationGeoDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                try:
                    result = await self._ip2location_result(domain)
                    geo_text, _, _ = self._ip2location_blocks(result)
                    set_output(dbg, geo_text)
                except Exception as e:
                    logger.warning(f"IP2Location.io geolocation check failed: {e}")
                    set_output(
                        dbg, info(f"IP2Location.io geolocation check failed: {e}")
                    )

    async def _ip2location_result(self, domain, *, refresh=True):
        """Fetch IP2Location.io once per domain and reuse it across tabs."""
        if not refresh and domain in self._ip2location_cache:
            return self._ip2location_cache[domain]
        result = await self.domain_analyzer.check_ip2location(domain)
        self._ip2location_cache[domain] = result
        return result

    async def _run_js_secrets(self, domain):
        dbg = self._debug("serverJsSecretsDebug")
        if dbg is None:
            return
        set_output(dbg, info("Loading..."))
        try:
            result = await self.domain_analyzer.scan_js_secrets(domain)
            set_output(dbg, render(result))
        except Exception as e:
            logger.warning(f"JS secrets scan failed: {e}")
            set_output(dbg, info(f"JS secrets scan failed: {e}"))

    async def analyze_web_surface(self, domain=None):
        domain = (domain or self._resolve_domain("webSurfaceDomainEdit") or "").strip()
        if not domain:
            return
        self.set_domain(domain)

        if self._is_checked("domainHeadersCheck"):
            waf_dbg = self._debug("serverWafDebug")
            if waf_dbg is not None:
                set_output(waf_dbg, info("Loading..."))
                try:
                    headers = await self.domain_analyzer.get_http_headers(domain)
                    waf = await self.domain_analyzer.detect_waf(domain)
                    set_output(waf_dbg, render({"Headers": headers, "WAF": waf}))
                except Exception as e:
                    logger.warning(f"Headers/WAF check failed: {e}")
                    set_output(waf_dbg, info(f"Headers/WAF check failed: {e}"))

        if self._is_checked("securityTxtCheck"):
            dbg = self._debug("securityTxtDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.get_security_txt(domain)
                set_output(dbg, render(result))

        if self._is_checked("cookiesCheck"):
            dbg = self._debug("cookiesDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.get_cookies(domain)
                set_output(dbg, render(result))

        if self._is_checked("socialTagsCheck"):
            dbg = self._debug("socialTagsDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.get_social_tags(domain)
                set_output(dbg, render(result))

        if self._is_checked("domainRobotsCheck"):
            dbg = self._debug("serverRobotsDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.get_robots_txt(domain)
                set_output(dbg, render(result))

        if self._is_checked("domainJsSecretsCheck"):
            await self._run_js_secrets(domain)

    async def analyze_discovery(self, domain=None):
        domain = (domain or self._resolve_domain("discoveryDomainEdit") or "").strip()
        if not domain:
            return
        self.set_domain(domain)

        if self._is_checked("domainSubdomainsCheck"):
            dbg = self._debug("serverSubdomainsDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.find_subdomains(domain)
                set_output(dbg, render(result))

        if self._is_checked("certTrCheck"):
            dbg = self._debug("certTrDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.get_certificate_transparency(domain)
                set_output(dbg, render(result))

        if self._is_checked("domainsOnIpCheck"):
            dbg = self._debug("domainsOnIpDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                try:
                    ip = await asyncio.to_thread(
                        __import__("socket").gethostbyname, domain.split("/")[0]
                    )
                except Exception as e:
                    set_output(dbg, info(f"Could not resolve IP: {e}"))
                else:
                    result = await self.domain_analyzer.get_domains_on_ip(ip)
                    set_output(dbg, render(result))

    async def analyze_security(self, domain=None, *, reuse_ip2location=False):
        domain = (domain or self._resolve_domain("securityDomainEdit") or "").strip()
        if not domain:
            return
        self.set_domain(domain)

        if self._is_checked("domainMalwareCheck"):
            dbg = self._debug("serverMalwareDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                result = await self.domain_analyzer.check_malware_reputation(domain)
                set_output(dbg, render(result))

        if self._is_checked("domainThreatIntelCheck"):
            dbg = self._debug("serverThreatIntelDebug")
            if dbg is not None:
                set_output(dbg, info("Loading..."))
                try:
                    result = await self.domain_analyzer.check_threat_intel(domain)
                    set_output(dbg, render(result))
                except Exception as e:
                    logger.warning(f"Threat intel check failed: {e}")
                    set_output(dbg, info(f"Threat intel check failed: {e}"))

        if self._is_checked("domainIP2LocationCheck"):
            net_dbg = self._debug("ip2locationNetworkDebug")
            threat_dbg = self._debug("ip2locationThreatDebug")
            debug_widgets = [
                widget for widget in (net_dbg, threat_dbg) if widget is not None
            ]
            if debug_widgets:
                for dbg in debug_widgets:
                    set_output(dbg, info("Loading..."))
                try:
                    result = await self._ip2location_result(
                        domain, refresh=not reuse_ip2location
                    )
                    _, net_text, threat_text = self._ip2location_blocks(result)
                    for dbg, text in (
                        (net_dbg, net_text),
                        (threat_dbg, threat_text),
                    ):
                        if dbg is not None:
                            set_output(dbg, text)
                except Exception as e:
                    logger.warning(f"IP2Location.io check failed: {e}")
                    for dbg in debug_widgets:
                        set_output(dbg, info(f"IP2Location.io check failed: {e}"))

    @staticmethod
    def _ip2location_blocks(result):
        """Split an IP2Location.io result into the three labelled UI blocks."""
        if not isinstance(result, dict):
            text = render(result)
            return text, text, text
        if result.get("status") in ("ERROR", "SKIPPED"):
            text = info(result.get("note", "IP2Location.io unavailable"))
            return text, text, text

        def _block(pairs):
            lines = []
            for label, value in pairs:
                if value in (None, "", [], {}):
                    continue
                if isinstance(value, (list, tuple)):
                    value = ", ".join(str(item) for item in value)
                lines.append(kv(label, value))
            return "\n".join(lines)

        geo = _block(
            [
                ("IP", result.get("ip")),
                ("Country", result.get("country_name")),
                ("Country code", result.get("country_code")),
                ("Region", result.get("region_name")),
                ("City", result.get("city_name")),
                ("ZIP", result.get("zip_code")),
                ("Timezone", result.get("time_zone")),
                ("Latitude", result.get("latitude")),
                ("Longitude", result.get("longitude")),
            ]
        )

        network = _block(
            [
                ("ASN", result.get("asn")),
                ("AS", result.get("as")),
                ("ISP", result.get("isp")),
                ("Domain", result.get("domain")),
                ("Usage type", result.get("usage_type")),
            ]
        )

        proxy_info = result.get("proxy") or {}
        flags = [
            label
            for key, label in (
                ("is_proxy", "Proxy"),
                ("is_vpn", "VPN"),
                ("is_tor", "Tor"),
                ("is_data_center", "Data center"),
                ("is_residential_proxy", "Residential proxy"),
            )
            if (result.get(key) if key == "is_proxy" else proxy_info.get(key))
        ]

        threat = _block(
            [
                ("Fraud score", result.get("fraud_score")),
                ("Flags", ", ".join(flags) if flags else "none"),
                ("Proxy type", proxy_info.get("proxy_type")),
                ("Threat", proxy_info.get("threat")),
                ("Provider", proxy_info.get("provider")),
            ]
        )

        return geo, network, threat

    async def analyze_whois(self, domain=None):
        """WHOIS/Registration tab: basic WHOIS + history + DNS + timeline + reverse."""
        if domain:
            self.set_domain(str(domain).strip())
        else:
            self._resolve_domain("whoisDomainEdit")
            if not self.domain:
                # fall back to any other domain input
                self._resolve_domain(*DOMAIN_EDITS)

        query_edit = getattr(self.ui, "reverseWhoisQueryEdit", None)
        query = query_edit.text().strip() if query_edit is not None else ""

        history_debug = self._debug("serverWhoisHistoryDebug")
        reverse_debug = self._debug("serverReverseWhoisDebug")
        timeline_debug = self._debug("serverDomainTimelineDebug")
        basic_debug = self._debug("serverWhoisDebug")

        if not self.domain and not query:
            message = info("Enter a domain or a reverse WHOIS query")
            for dbg in (history_debug, reverse_debug, timeline_debug, basic_debug):
                if dbg is not None:
                    set_output(dbg, message)
            return

        whois_history = None
        dns_history = None
        current_whois = None

        # Basic WHOIS (python-whois) if requested
        if (
            self.domain
            and self._is_checked("domainWhoisCheck")
            and basic_debug is not None
        ):
            set_output(basic_debug, info("Loading..."))
            try:
                if (
                    self._whois_cache_domain == self.domain
                    and self._whois_cache is not None
                ):
                    current_whois = self._whois_cache
                else:
                    current_whois = await self.domain_analyzer.get_whois_info(
                        self.domain
                    )
                    self._whois_cache = current_whois
                    self._whois_cache_domain = self.domain
                set_output(basic_debug, render(current_whois, "WHOIS"))
            except Exception as e:
                logger.warning(f"WHOIS info failed: {e}")
                set_output(basic_debug, info(f"WHOIS failed: {e}"))
        elif basic_debug is not None and not self.domain:
            set_output(basic_debug, info("Enter a domain"))

        if self.domain:
            if history_debug is not None:
                set_output(history_debug, info("Loading..."))
            if timeline_debug is not None:
                set_output(timeline_debug, info("Loading..."))
            try:
                whois_history, dns_history = await asyncio.gather(
                    self.domain_analyzer.get_whois_history(self.domain),
                    self.domain_analyzer.get_dns_history(self.domain),
                )
            except Exception as e:
                logger.warning(f"WHOIS/DNS history fetch failed: {e}")
            if history_debug is not None:
                if whois_history is not None:
                    set_output(history_debug, render(whois_history, "WHOIS history"))
                else:
                    set_output(history_debug, info("WHOIS history unavailable"))
            if timeline_debug is not None:
                try:
                    timeline = await self.domain_analyzer.build_domain_timeline(
                        dns_history=dns_history,
                        whois_history=whois_history,
                        current_whois=current_whois,
                    )
                    set_output(timeline_debug, render(timeline, "Domain timeline"))
                except Exception as e:
                    logger.warning(f"Domain timeline failed: {e}")
                    set_output(timeline_debug, info(f"Timeline failed: {e}"))
        else:
            if history_debug is not None:
                set_output(history_debug, info("Enter a domain to load WHOIS history"))
            if timeline_debug is not None:
                set_output(timeline_debug, info("Enter a domain to build a timeline"))

        if reverse_debug is None:
            return

        set_output(reverse_debug, info("Loading..."))
        try:
            if query:
                reverse_result = await self.domain_analyzer.reverse_whois_from_query(
                    query
                )
            elif self.domain:
                if whois_history is None:
                    whois_history = await self.domain_analyzer.get_whois_history(
                        self.domain
                    )
                # Current WHOIS is only a fallback pivot source for history
                # entries that are redacted; it does not consume credits.
                if current_whois is None and (
                    self._whois_cache_domain == self.domain
                    and self._whois_cache is not None
                ):
                    current_whois = self._whois_cache
                if current_whois is None:
                    try:
                        current_whois = await self.domain_analyzer.get_whois_info(
                            self.domain
                        )
                        self._whois_cache = current_whois
                        self._whois_cache_domain = self.domain
                        # also update basic debug if it exists and is in loading/empty
                        if basic_debug is not None and self._is_checked(
                            "domainWhoisCheck"
                        ):
                            set_output(basic_debug, render(current_whois, "WHOIS"))
                    except Exception:
                        current_whois = None
                reverse_result = await self.domain_analyzer.reverse_whois_from_pivots(
                    whois_history,
                    current_whois=current_whois,
                )
                # Refresh timeline with current WHOIS context if available.
                if timeline_debug is not None and dns_history is not None:
                    try:
                        timeline = await self.domain_analyzer.build_domain_timeline(
                            dns_history=dns_history,
                            whois_history=whois_history,
                            current_whois=current_whois,
                        )
                        set_output(timeline_debug, render(timeline, "Domain timeline"))
                    except Exception:
                        pass
            else:
                reverse_result = {
                    "status": "No query",
                    "message": "Enter a domain or a reverse WHOIS query",
                }
            set_output(reverse_debug, render(reverse_result, "Reverse WHOIS"))
        except Exception as e:
            logger.warning(f"Reverse WHOIS check failed: {e}")
            set_output(reverse_debug, info(f"Reverse WHOIS check failed: {e}"))
