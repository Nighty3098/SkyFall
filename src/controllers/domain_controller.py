import json
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.domain_analyzer import DomainAnalyzer


STEPS = 8


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
        QApplication.processEvents()

    async def analyze_domain(self):
        self.ui.domainProgress.setValue(0)

        self.ui.serverRobotsDebug.setPlainText(
            await self.domain_analyzer.get_robots_txt(self.domain),
        )
        self._update_progress(1)

        self.ui.serverLocationDebug.setPlainText(
            json.dumps(
                await self.domain_analyzer.get_ip_and_location(self.domain),
                indent=2,
                ensure_ascii=False,
            )
        )
        self._update_progress(2)

        self.ui.serverTlsDebug.setPlainText(
            json.dumps(
                await self.domain_analyzer.get_ssl_tls_info(self.domain),
                indent=2,
                ensure_ascii=False,
            )
        )
        self._update_progress(3)

        self.ui.serverDnsAnalyzeDebug.setPlainText(
            json.dumps(
                await self.domain_analyzer.get_dns_and_hosts(self.domain),
                indent=2,
                ensure_ascii=False,
            )
        )
        self._update_progress(4)

        self.ui.serverWafDebug.setPlainText(
            json.dumps(
                await self.domain_analyzer.analyze_web_stack(self.domain),
                indent=2,
                ensure_ascii=False,
            )
        )
        self._update_progress(5)

        self.ui.serverWhoisDebug.setPlainText(
            json.dumps(
                await self.domain_analyzer.get_whois_info(self.domain),
                indent=2,
                ensure_ascii=False,
            )
        )
        self._update_progress(6)

        self.ui.serverOpenPortsDebug.setPlainText(
            json.dumps(
                await self.domain_analyzer.run_nmap_scan(self.domain),
                indent=2,
                ensure_ascii=False,
            )
        )
        self._update_progress(7)

        self.ui.serverMalwareDebug.setPlainText(
            json.dumps(
                await self.domain_analyzer.check_malware_reputation(self.domain),
                indent=2,
                ensure_ascii=False,
            )
        )
        self._update_progress(8)
