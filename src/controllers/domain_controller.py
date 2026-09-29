from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import info

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.domain_analyzer import DomainAnalyzer


STEPS = 16


def _val(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _fmt(data, indent=2):
    p = " " * indent
    if isinstance(data, dict):
        parts = []
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                parts.append(f"{p}{k}:")
                parts.append(_fmt(v, indent + 2))
            else:
                parts.append(f"{p}{k}: {_val(v)}")
        return "\n".join(parts)
    if isinstance(data, list):
        parts = []
        for item in data:
            if isinstance(item, (dict, list)):
                parts.append(_fmt(item, indent))
            else:
                parts.append(f"{p}- {item}")
        return "\n".join(parts)
    return f"{p}{data}"


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

    def set_domain(self, domain):
        self.domain = domain

    def _update_progress(self, step: int):
        self.ui.domainProgress.setValue(int(step / STEPS * 100))

    async def analyze_domain(self):
        self.ui.domainProgress.setValue(0)

        if self.ui.domainRobotsCheck.isChecked():
            self.ui.serverRobotsDebug.setPlainText(info("Loading..."))
            self.ui.serverRobotsDebug.setPlainText(
                await self.domain_analyzer.get_robots_txt(self.domain),
            )
        self._update_progress(1)

        if self.ui.domainLocationCheck.isChecked():
            self.ui.serverLocationDebug.setPlainText(info("Loading..."))
            self.ui.serverLocationDebug.setPlainText(
                _fmt(
                    await self.domain_analyzer.get_ip_and_location(self.domain),
                )
            )
        self._update_progress(2)

        if self.ui.domainSSLCheck.isChecked():
            self.ui.serverTlsDebug.setPlainText(info("Loading..."))
            self.ui.serverTlsDebug.setPlainText(
                _fmt(
                    await self.domain_analyzer.get_ssl_tls_info(self.domain),
                )
            )
        self._update_progress(3)

        if self.ui.domainDNSCheck.isChecked():
            self.ui.serverDnsAnalyzeDebug.setPlainText(info("Loading..."))
            dns_records = await self.domain_analyzer.get_dns(self.domain)
            associated_hosts = await self.domain_analyzer.get_hosts(self.domain)
            self.ui.serverDnsAnalyzeDebug.setPlainText(
                _fmt(
                    {"dns_records": dns_records, "associated_hosts": associated_hosts},
                )
            )
        self._update_progress(4)

        if self.ui.domainHeadersCheck.isChecked():
            self.ui.serverWafDebug.setPlainText(info("Loading..."))
            web_stack = await self.domain_analyzer.analyze_web_stack(self.domain)
            combined = _fmt(web_stack)
            # JS secrets piggyback: only when no dedicated panel exists in form.ui.
            if getattr(self.ui, "serverJsSecretsDebug", None) is None:
                try:
                    js_text = await self.domain_analyzer.scan_js_secrets(self.domain)
                except Exception as e:
                    logger.warning(f"JS secrets scan failed: {e}")
                    js_text = ""
                if js_text:
                    combined = f"{combined}\n\n{js_text}"
            self.ui.serverWafDebug.setPlainText(combined)
        self._update_progress(5)

        if self.ui.domainWhoisCheck.isChecked():
            self.ui.serverWhoisDebug.setPlainText(info("Loading..."))
            self.ui.serverWhoisDebug.setPlainText(
                _fmt(
                    await self.domain_analyzer.get_whois_info(self.domain),
                )
            )
        self._update_progress(6)

        if self.ui.domainNmapCheck.isChecked():
            self.ui.serverNmapDebug.setPlainText(info("Loading..."))
            self.ui.serverNmapDebug.setPlainText(
                _fmt(
                    await self.domain_analyzer.run_nmap_scan(self.domain),
                )
            )
        self._update_progress(7)

        if self.ui.domainMalwareCheck.isChecked():
            self.ui.serverMalwareDebug.setPlainText(info("Loading..."))
            # Skip the intel round here when the dedicated Threat Intel step
            # runs too — avoids duplicate AbuseIPDB/GreyNoise/ThreatFox/URLHaus calls.
            threat_separate = (
                getattr(self.ui, "domainThreatIntelCheck", None) is not None
                and self.ui.domainThreatIntelCheck.isChecked()
            )
            self.ui.serverMalwareDebug.setPlainText(
                _fmt(
                    await self.domain_analyzer.check_malware_reputation(
                        self.domain, include_intel=not threat_separate
                    ),
                )
            )
        self._update_progress(8)

        if self.ui.domainSubdomainsCheck.isChecked():
            self.ui.serverSubdomainsDebug.setPlainText(info("Loading..."))
            self.ui.serverSubdomainsDebug.setPlainText(
                _fmt(
                    await self.domain_analyzer.find_subdomains(self.domain),
                )
            )
        self._update_progress(9)

        if self.ui.securityTxtCheck.isChecked():
            self.ui.securityTxtDebug.setPlainText(info("Loading..."))
            self.ui.securityTxtDebug.setPlainText(
                await self.domain_analyzer.get_security_txt(self.domain)
            )
        self._update_progress(10)

        if self.ui.cookiesCheck.isChecked():
            self.ui.cookiesDebug.setPlainText(info("Loading..."))
            self.ui.cookiesDebug.setPlainText(
                await self.domain_analyzer.get_cookies(self.domain)
            )
        self._update_progress(11)

        if self.ui.socialTagsCheck.isChecked():
            self.ui.socialTagsDebug.setPlainText(info("Loading..."))
            self.ui.socialTagsDebug.setPlainText(
                await self.domain_analyzer.get_social_tags(self.domain)
            )
        self._update_progress(12)

        if self.ui.certTrCheck.isChecked():
            self.ui.certTrDebug.setPlainText(info("Loading..."))
            self.ui.certTrDebug.setPlainText(
                await self.domain_analyzer.get_certificate_transparency(self.domain)
            )
        self._update_progress(13)

        if self.ui.domainsOnIpCheck.isChecked():
            self.ui.domainsOnIpDebug.setPlainText(info("Loading..."))
            ip_data = await self.domain_analyzer.get_ip_and_location(self.domain)
            ip_addr = ip_data.get("ip", "")
            if ip_addr and "error" not in ip_data:
                self.ui.domainsOnIpDebug.setPlainText(
                    _fmt(await self.domain_analyzer.get_domains_on_ip(ip_addr))
                )
            else:
                self.ui.domainsOnIpDebug.setPlainText(
                    info(f"Could not resolve IP for {self.domain}")
                )
        self._update_progress(14)

        # ── Dedicated panels (present in form.ui; getattr keeps back-compat) ──
        js_check = getattr(self.ui, "domainJsSecretsCheck", None)
        js_debug = getattr(self.ui, "serverJsSecretsDebug", None)
        if js_check is not None and js_debug is not None and js_check.isChecked():
            js_debug.setPlainText(info("Loading..."))
            try:
                js_debug.setPlainText(
                    await self.domain_analyzer.scan_js_secrets(self.domain)
                )
            except Exception as e:
                logger.warning(f"JS secrets scan failed: {e}")
                js_debug.setPlainText(info(f"JS secrets scan failed: {e}"))
        self._update_progress(15)

        threat_check = getattr(self.ui, "domainThreatIntelCheck", None)
        threat_debug = getattr(self.ui, "serverThreatIntelDebug", None)
        if (
            threat_check is not None
            and threat_debug is not None
            and threat_check.isChecked()
        ):
            threat_debug.setPlainText(info("Loading..."))
            try:
                threat_debug.setPlainText(
                    _fmt(await self.domain_analyzer.check_threat_intel(self.domain))
                )
            except Exception as e:
                logger.warning(f"Threat intel check failed: {e}")
                threat_debug.setPlainText(info(f"Threat intel check failed: {e}"))
        self._update_progress(16)
