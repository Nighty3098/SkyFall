import json
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.domain_analyzer import DomainAnalyzer


STEPS = 12


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
            self.ui.serverRobotsDebug.setPlainText("Loading")
            self.ui.serverRobotsDebug.setPlainText(
                await self.domain_analyzer.get_robots_txt(self.domain),
            )
        self._update_progress(1)

        if self.ui.domainLocationCheck.isChecked():
            self.ui.serverLocationDebug.setPlainText("Loading")
            self.ui.serverLocationDebug.setPlainText(
                json.dumps(
                    await self.domain_analyzer.get_ip_and_location(self.domain),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        self._update_progress(2)

        if self.ui.domainSSLCheck.isChecked():
            self.ui.serverTlsDebug.setPlainText("Loading")
            self.ui.serverTlsDebug.setPlainText(
                json.dumps(
                    await self.domain_analyzer.get_ssl_tls_info(self.domain),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        self._update_progress(3)

        if self.ui.domainDNSCheck.isChecked():
            self.ui.serverDnsAnalyzeDebug.setPlainText("Loading")
            dns_records = await self.domain_analyzer.get_dns(self.domain)
            associated_hosts = await self.domain_analyzer.get_hosts(self.domain)
            self.ui.serverDnsAnalyzeDebug.setPlainText(
                json.dumps(
                    {"dns_records": dns_records, "associated_hosts": associated_hosts},
                    indent=2,
                    ensure_ascii=False,
                )
            )
        self._update_progress(4)

        if self.ui.domainHeadersCheck.isChecked():
            self.ui.serverWafDebug.setPlainText("Loading")
            self.ui.serverWafDebug.setPlainText(
                json.dumps(
                    await self.domain_analyzer.analyze_web_stack(self.domain),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        self._update_progress(5)

        if self.ui.domainWhoisCheck.isChecked():
            self.ui.serverWhoisDebug.setPlainText("Loading")
            self.ui.serverWhoisDebug.setPlainText(
                json.dumps(
                    await self.domain_analyzer.get_whois_info(self.domain),
                    indent=2,
                    ensure_ascii=False,
                    default=lambda o: (
                        o.isoformat() if isinstance(o, datetime) else str(o)
                    ),
                )
            )
        self._update_progress(6)

        if self.ui.domainNmapCheck.isChecked():
            self.ui.serverNmapDebug.setPlainText("Loading")
            self.ui.serverNmapDebug.setPlainText(
                json.dumps(
                    await self.domain_analyzer.run_nmap_scan(self.domain),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        self._update_progress(7)

        if self.ui.domainMalwareCheck.isChecked():
            self.ui.serverMalwareDebug.setPlainText("Loading")
            self.ui.serverMalwareDebug.setPlainText(
                json.dumps(
                    await self.domain_analyzer.check_malware_reputation(self.domain),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        self._update_progress(8)

        if self.ui.domainSubdomainsCheck.isChecked():
            self.ui.serverSubdomainsDebug.setPlainText("Loading")
            self.ui.serverSubdomainsDebug.setPlainText(
                json.dumps(
                    await self.domain_analyzer.find_subdomains(self.domain),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        self._update_progress(9)

        if self.ui.securityTxtCheck.isChecked():
            self.ui.securityTxtDebug.setPlainText("Loading")
            self.ui.securityTxtDebug.setPlainText(
                await self.domain_analyzer.get_security_txt(self.domain)
            )
        self._update_progress(10)

        if self.ui.cookiesCheck.isChecked():
            self.ui.cookiesDebug.setPlainText("Loading")
            self.ui.cookiesDebug.setPlainText(
                await self.domain_analyzer.get_cookies(self.domain)
            )
        self._update_progress(11)

        if self.ui.socialTagsCheck.isChecked():
            self.ui.socialTagsDebug.setPlainText("Loading")
            self.ui.socialTagsDebug.setPlainText(
                await self.domain_analyzer.get_social_tags(self.domain)
            )
        self._update_progress(12)
