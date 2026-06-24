from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.github_search import GitHubSearch


class GitHubController:
    def __init__(
        self,
        ui: "QMainWindow",
        github_search: "GitHubSearch",
    ):
        logger.debug("Init: GitHubController")
        self.ui = ui
        self.github_search = github_search

    async def search_user(self):
        username = self.ui.githubUserEdit.text().strip()
        if not username:
            self.ui.githubDebug.appendPlainText("[!] Enter a username")
            return

        self.ui.githubDebug.clear()
        self.ui.githubProgress.setValue(0)
        self.ui.githubProgress.setRange(0, 0)

        try:
            await self.github_search.search_user(
                username,
                on_result=lambda line: self.ui.githubDebug.appendPlainText(line),
            )
            self.ui.githubDebug.appendPlainText("\n--- End of user search ---")
        except Exception as e:
            self.ui.githubDebug.appendPlainText(f"\n[!] Error: {e}")
        finally:
            self.ui.githubProgress.setRange(0, 100)
            self.ui.githubProgress.setValue(100)

    async def search_repos(self):
        query = self.ui.githubRepoEdit.text().strip()
        if not query:
            self.ui.githubDebug.appendPlainText("[!] Enter a search query")
            return

        self.ui.githubDebug.clear()
        self.ui.githubProgress.setValue(0)
        self.ui.githubProgress.setRange(0, 0)

        try:
            await self.github_search.search_repos(
                query,
                on_result=lambda line: self.ui.githubDebug.appendPlainText(line),
                on_progress=lambda p, r, lim: self.ui.githubDebug.appendPlainText(
                    f"[Page {p}] Rate: {r}/{lim}"
                ),
            )
            self.ui.githubDebug.appendPlainText("\n--- End of repo search ---")
        except Exception as e:
            self.ui.githubDebug.appendPlainText(f"\n[!] Error: {e}")
        finally:
            self.ui.githubProgress.setRange(0, 100)
            self.ui.githubProgress.setValue(100)

    async def search_emails(self):
        query = self.ui.githubEmailEdit.text().strip()
        if not query:
            self.ui.githubDebug.appendPlainText("[!] Enter a search query")
            return

        self.ui.githubDebug.clear()
        self.ui.githubProgress.setValue(0)
        self.ui.githubProgress.setRange(0, 0)

        try:
            await self.github_search.search_emails(
                query,
                on_result=lambda line: self.ui.githubDebug.appendPlainText(line),
            )
            self.ui.githubDebug.appendPlainText("\n--- End of email search ---")
        except Exception as e:
            self.ui.githubDebug.appendPlainText(f"\n[!] Error: {e}")
        finally:
            self.ui.githubProgress.setRange(0, 100)
            self.ui.githubProgress.setValue(100)

    async def search_commits(self):
        query = self.ui.githubCommitEdit.text().strip()
        if not query:
            self.ui.githubDebug.appendPlainText("[!] Enter a search query")
            return

        self.ui.githubDebug.clear()
        self.ui.githubProgress.setValue(0)
        self.ui.githubProgress.setRange(0, 0)
        has_results = False

        def on_result(line):
            nonlocal has_results
            has_results = True
            self.ui.githubDebug.appendPlainText(line)

        try:
            result = await self.github_search.search_commits(
                query,
                on_result=on_result,
            )
            if not has_results:
                self.ui.githubDebug.appendPlainText(result)
            self.ui.githubDebug.appendPlainText("\n--- End of commit search ---")
        except Exception as e:
            self.ui.githubDebug.appendPlainText(f"\n[!] Error: {e}")
        finally:
            self.ui.githubProgress.setRange(0, 100)
            self.ui.githubProgress.setValue(100)

    async def search_secrets(self):
        query = self.ui.githubSecretEdit.text().strip()
        if not query:
            self.ui.githubDebug.appendPlainText("[!] Enter a search query")
            return

        self.ui.githubDebug.clear()
        self.ui.githubProgress.setValue(0)
        self.ui.githubProgress.setRange(0, 0)
        has_results = False

        def on_result(line):
            nonlocal has_results
            has_results = True
            self.ui.githubDebug.appendPlainText(line)

        def on_progress(done, total, pattern):
            self.ui.githubProgress.setRange(0, total)
            self.ui.githubProgress.setValue(done)

        try:
            result = await self.github_search.search_secrets(
                query,
                on_result=on_result,
                on_progress=on_progress,
            )
            if not has_results:
                self.ui.githubDebug.appendPlainText(result)
            self.ui.githubDebug.appendPlainText("\n--- End of secret scan ---")
        except Exception as e:
            self.ui.githubDebug.appendPlainText(f"\n[!] Error: {e}")
        finally:
            self.ui.githubProgress.setRange(0, 100)
            self.ui.githubProgress.setValue(100)

    async def search_dork(self):
        query = self.ui.githubDorkEdit.text().strip()
        if not query:
            self.ui.githubDebug.appendPlainText("[!] Enter a dork query")
            return

        self.ui.githubDebug.clear()
        self.ui.githubProgress.setValue(0)
        self.ui.githubProgress.setRange(0, 0)

        dork_type = "code"
        if self.ui.githubDorkCommitsCheck.isChecked():
            dork_type = "commits"
        elif self.ui.githubDorkIssuesCheck.isChecked():
            dork_type = "issues"
        elif self.ui.githubDorkReposCheck.isChecked():
            dork_type = "repositories"
        elif self.ui.githubDorkUsersCheck.isChecked():
            dork_type = "users"

        try:
            await self.github_search.search_dork(
                query,
                dork_type=dork_type,
                on_result=lambda line: self.ui.githubDebug.appendPlainText(line),
            )
            self.ui.githubDebug.appendPlainText("\n--- End of dork search ---")
        except Exception as e:
            self.ui.githubDebug.appendPlainText(f"\n[!] Error: {e}")
        finally:
            self.ui.githubProgress.setRange(0, 100)
            self.ui.githubProgress.setValue(100)
