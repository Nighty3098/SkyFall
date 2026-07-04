import json
import os
from pathlib import Path

from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PySide6.QtWidgets import QApplication, QFileDialog


class ReportController:
    def __init__(self, ui):
        self.ui = ui

    @staticmethod
    def _server_params() -> StdioServerParameters:
        server_script = Path(__file__).parent / "ollama_mcp_server.py"
        return StdioServerParameters(
            command="python",
            args=[str(server_script)],
        )

    async def _call_tool(self, tool_name: str, arguments: dict | None = None) -> str:
        params = self._server_params()
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments or {})
                return result.content[0].text

    async def generate_report(self):
        try:
            self.ui.aiReportDebug.setPlainText("Generating report...")
            QApplication.processEvents()

            data = self._collect_all_data()

            report_text = await self._call_tool(
                "generate_osint_report",
                {
                    "app_data": json.dumps(data, ensure_ascii=False, default=str),
                },
            )

            self.ui.aiReportDebug.setPlainText(report_text)
            logger.success("OSINT report generated")

        except Exception as e:
            error_msg = f"Error generating report: {e}"
            logger.error(error_msg)
            self.ui.aiReportDebug.setPlainText(f"# Error\n\n{error_msg}")

    def _collect_all_data(self) -> dict:
        data = {}

        debug_widgets = {
            "telegram_downloader": self.ui.telegramDownloaderDebug,
            "telegram_analyzer": self.ui.telegramAnalyzerDebug,
            "username_search": self.ui.usernameScriptDebug,
            "maigret_search": self.ui.maigretDebug,
            "mail_search": self.ui.mailSearchDebug,
            "hibp_check": self.ui.hibpDebug,
            "server_location": self.ui.serverLocationDebug,
            "server_robots": self.ui.serverRobotsDebug,
            "server_tls": self.ui.serverTlsDebug,
            "server_waf": self.ui.serverWafDebug,
            "cookies": self.ui.cookiesDebug,
            "security_txt": self.ui.securityTxtDebug,
            "server_subdomains": self.ui.serverSubdomainsDebug,
            "social_tags": self.ui.socialTagsDebug,
            "server_nmap": self.ui.serverNmapDebug,
            "server_dns": self.ui.serverDnsAnalyzeDebug,
            "server_whois": self.ui.serverWhoisDebug,
            "server_malware": self.ui.serverMalwareDebug,
            "cert_transparency": self.ui.certTrDebug,
            "metadata": self.ui.metadataDebug,
            "strings": self.ui.stringsFileDebug,
            "virustotal_file": self.ui.virustotalFileDebug,
            "github": self.ui.githubDebug,
            "phone": self.ui.phoneDebug,
            "mac_location": self.ui.macAddrLocationDebug,
            "blockchain": self.ui.bcDebug,
        }

        placeholders = {"REPORT", "INTELX", "HIBP", "METADATA", "VIRUSTOTAL", "STRINGS"}

        for name, widget in debug_widgets.items():
            text = widget.toPlainText().strip()
            if text and text not in placeholders:
                data[name] = text

        try:
            data["graph"] = self.ui.graphWidget.to_dict()
        except Exception:
            pass

        inputs = {
            "url": self.ui.serverUrlEdit.text(),
            "username": self.ui.usernameEdit.text(),
            "email": self.ui.mailEdit.text(),
            "phone": self.ui.phoneNumberEdit.text(),
            "mac_address": self.ui.macAddrEdit.text(),
            "github_user": self.ui.githubUserEdit.text(),
            "github_repo": self.ui.githubRepoEdit.text(),
        }
        data["search_inputs"] = {k: v for k, v in inputs.items() if v}

        return data

    def save_report(self):
        report_text = self.ui.aiReportDebug.toPlainText()
        if not report_text or report_text in ("REPORT", "Generating report..."):
            return

        data_dir = str(Path.home() / ".skyfall" / "data")
        os.makedirs(data_dir, exist_ok=True)

        path, _ = QFileDialog.getSaveFileName(
            self.ui,
            "Save Report",
            os.path.join(data_dir, "osint_report.md"),
            "Markdown (*.md)",
        )

        if path:
            Path(path).write_text(report_text, encoding="utf-8")
            logger.success(f"Report saved to {path}")
