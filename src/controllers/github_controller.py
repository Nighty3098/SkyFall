from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import error, render

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

    def _start(self):
        self.ui.githubDebug.clear()
        self.ui.githubProgress.setValue(0)
        self.ui.githubProgress.setRange(0, 0)

    def _finish(self):
        self.ui.githubProgress.setRange(0, 100)
        self.ui.githubProgress.setValue(100)

    def _render(self, result, title):
        self.ui.githubDebug.setPlainText(render(result, title=title))

    async def search_user(self):
        username = self.ui.githubUserEdit.text().strip()
        if not username:
            self.ui.githubDebug.setPlainText(error("Enter a username"))
            return

        self._start()
        try:
            result = await self.github_search.search_user(username)
            self._render(result, f"GitHub User: {username}")
        except Exception as e:
            self.ui.githubDebug.setPlainText(error(f"Error: {e}"))
        finally:
            self._finish()

    async def search_repos(self):
        query = self.ui.githubRepoEdit.text().strip()
        if not query:
            self.ui.githubDebug.setPlainText(error("Enter a search query"))
            return

        self._start()
        try:
            result = await self.github_search.search_repos(query)
            self._render(result, f"Repositories: {query}")
        except Exception as e:
            self.ui.githubDebug.setPlainText(error(f"Error: {e}"))
        finally:
            self._finish()

    async def search_emails(self):
        query = self.ui.githubEmailEdit.text().strip()
        if not query:
            self.ui.githubDebug.setPlainText(error("Enter a search query"))
            return

        self._start()
        try:
            result = await self.github_search.search_emails(query)
            self._render(result, f"Emails: {query}")
        except Exception as e:
            self.ui.githubDebug.setPlainText(error(f"Error: {e}"))
        finally:
            self._finish()

    async def search_commits(self):
        query = self.ui.githubCommitEdit.text().strip()
        if not query:
            self.ui.githubDebug.setPlainText(error("Enter a search query"))
            return

        self._start()
        try:
            result = await self.github_search.search_commits(query)
            self._render(result, f"Commits: {query}")
        except Exception as e:
            self.ui.githubDebug.setPlainText(error(f"Error: {e}"))
        finally:
            self._finish()

    async def search_secrets(self):
        query = self.ui.githubSecretEdit.text().strip()
        if not query:
            self.ui.githubDebug.setPlainText(error("Enter a search query"))
            return

        self._start()

        def on_progress(done, total, pattern):
            self.ui.githubProgress.setRange(0, total)
            self.ui.githubProgress.setValue(done)

        try:
            result = await self.github_search.search_secrets(
                query,
                on_progress=on_progress,
            )
            self._render(result, f"Secrets: {query}")
        except Exception as e:
            self.ui.githubDebug.setPlainText(error(f"Error: {e}"))
        finally:
            self._finish()

    async def search_dork(self):
        query = self.ui.githubDorkEdit.text().strip()
        if not query:
            self.ui.githubDebug.setPlainText(error("Enter a dork query"))
            return

        self._start()

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
            result = await self.github_search.search_dork(
                query,
                dork_type=dork_type,
            )
            self._render(result, f"Dork ({dork_type}): {query}")
        except Exception as e:
            self.ui.githubDebug.setPlainText(error(f"Error: {e}"))
        finally:
            self._finish()
