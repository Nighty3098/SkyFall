import asyncio
import json
from typing import TYPE_CHECKING

from loguru import logger

from src.thread_utils import invoke

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.domain_analyzer import DomainAnalyzer


STEPS = 9


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
        invoke(self.ui.domainProgress, "setValue", int(step / STEPS * 100))

    def analyze_domain(self):
        invoke(self.ui.domainProgress, "setValue", 0)

        if self.ui.domainRobotsCheck.isChecked():
            invoke(
                self.ui.serverRobotsDebug,
                "setPlainText",
                asyncio.run(self.domain_analyzer.get_robots_txt(self.domain)),
            )
        self._update_progress(1)

        if self.ui.domainLocationCheck.isChecked():
            invoke(
                self.ui.serverLocationDebug,
                "setPlainText",
                json.dumps(
                    asyncio.run(self.domain_analyzer.get_ip_and_location(self.domain)),
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        self._update_progress(2)

        if self.ui.domainSSLCheck.isChecked():
            invoke(
                self.ui.serverTlsDebug,
                "setPlainText",
                json.dumps(
                    asyncio.run(self.domain_analyzer.get_ssl_tls_info(self.domain)),
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        self._update_progress(3)

        if self.ui.domainDNSCheck.isChecked():
            dns_records = asyncio.run(self.domain_analyzer.get_dns(self.domain))
            associated_hosts = asyncio.run(self.domain_analyzer.get_hosts(self.domain))
            invoke(
                self.ui.serverDnsAnalyzeDebug,
                "setPlainText",
                json.dumps(
                    {"dns_records": dns_records, "associated_hosts": associated_hosts},
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        self._update_progress(4)

        if self.ui.domainHeadersCheck.isChecked():
            invoke(
                self.ui.serverWafDebug,
                "setPlainText",
                json.dumps(
                    asyncio.run(self.domain_analyzer.analyze_web_stack(self.domain)),
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        self._update_progress(5)

        if self.ui.domainWhoisCheck.isChecked():
            invoke(
                self.ui.serverWhoisDebug,
                "setPlainText",
                json.dumps(
                    asyncio.run(self.domain_analyzer.get_whois_info(self.domain)),
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        self._update_progress(6)

        if self.ui.domainNmapCheck.isChecked():
            invoke(
                self.ui.serverNmapDebug,
                "setPlainText",
                json.dumps(
                    asyncio.run(self.domain_analyzer.run_nmap_scan(self.domain)),
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        self._update_progress(7)

        if self.ui.domainMalwareCheck.isChecked():
            invoke(
                self.ui.serverMalwareDebug,
                "setPlainText",
                json.dumps(
                    asyncio.run(
                        self.domain_analyzer.check_malware_reputation(self.domain)
                    ),
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        self._update_progress(8)

        if self.ui.domainSubdomainsCheck.isChecked():
            invoke(
                self.ui.serverSubdomainsDebug,
                "setPlainText",
                json.dumps(
                    asyncio.run(self.domain_analyzer.find_subdomains(self.domain)),
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        self._update_progress(9)
