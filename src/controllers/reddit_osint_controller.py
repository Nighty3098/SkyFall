"""Controller for the Reddit OSINT tab.

Bridges the widgets declared in ``resources/form.ui`` with
:class:`src.modules.reddit_osint.RedditOsint`.  The controller keeps a short
lived cache of the last report so the per-section buttons (posts, comments,
removed, …) do not refetch the archives for the same query.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import error, info

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.reddit_osint import RedditOsint

#: Combo label → archive sources to query.
SOURCE_LABELS = {
    "Both archives": ("arctic", "pullpush"),
    "Arctic Shift": ("arctic",),
    "PullPush": ("pullpush",),
}

ALL_SECTIONS = [
    "overview",
    "posts",
    "comments",
    "removed",
    "identifiers",
    "activity",
    "affiliations",
]


class RedditOsintController:
    """Drive the Reddit OSINT tab."""

    #: Reports are reused for this many seconds for an identical query.
    CACHE_TTL = 900

    def __init__(
        self, ui: QMainWindow, reddit_osint: RedditOsint, proxy=None, case_manager=None
    ):
        logger.debug("Init: RedditOsintController")
        self.ui = ui
        self.reddit = reddit_osint
        self.proxy = proxy
        self.case_manager = case_manager
        self._cache: dict[tuple, tuple[float, dict, list[str]]] = {}

    # ── UI helpers ──────────────────────────────────────────────

    def _set_text(self, text: str) -> None:
        widget = getattr(self.ui, "redditOsintDebug", None)
        if widget is not None:
            widget.setPlainText(text)

    def _busy(self, busy: bool) -> None:
        bar = getattr(self.ui, "redditProgressBar", None)
        if bar is None:
            return
        if busy:
            bar.setRange(0, 0)
        else:
            bar.setRange(0, 100)
            bar.setValue(100)

    def _state(self) -> dict:
        """Read the current form configuration into a plain dict."""
        username = ""
        widget = getattr(self.ui, "redditUsernameEdit", None)
        if widget is not None:
            username = widget.text().strip().removeprefix("u/").removeprefix("U/")

        subreddit = ""
        widget = getattr(self.ui, "redditSubredditEdit", None)
        if widget is not None:
            subreddit = widget.text().strip().removeprefix("r/")

        keywords = ""
        widget = getattr(self.ui, "redditKeywordsEdit", None)
        if widget is not None:
            keywords = widget.text().strip()

        label = "Both archives"
        widget = getattr(self.ui, "redditSourceCombo", None)
        if widget is not None:
            label = widget.currentText()

        nsfw = "Any"
        widget = getattr(self.ui, "redditNsfwCombo", None)
        if widget is not None:
            nsfw = widget.currentText()

        max_pages = 40
        widget = getattr(self.ui, "redditMaxPagesSpin", None)
        if widget is not None:
            max_pages = int(widget.value())

        over18 = None
        if nsfw == "NSFW only":
            over18 = True
        elif nsfw == "Safe only":
            over18 = False

        return {
            "username": username,
            "sources": SOURCE_LABELS.get(label, ("arctic", "pullpush")),
            "subreddit": subreddit or None,
            "keywords": keywords or None,
            "over18": over18,
            "max_pages": max_pages,
        }

    def _cache_key(self, state: dict) -> tuple:
        return (
            state["username"],
            state["sources"],
            state["subreddit"],
            state["keywords"],
            state["over18"],
            state["max_pages"],
        )

    async def _report(self, state: dict) -> tuple[dict, list[str]]:
        key = self._cache_key(state)
        cached = self._cache.get(key)
        now = time.monotonic()
        if cached and now - cached[0] < self.CACHE_TTL:
            return cached[1], cached[2]

        if self.proxy is not None:
            self.reddit.set_proxy(self.proxy.get_proxy_url())

        report, errors = await self.reddit.full_report(
            state["username"],
            sources=state["sources"],
            subreddit=state["subreddit"],
            keywords=state["keywords"],
            over18=state["over18"],
            max_pages=state["max_pages"],
        )
        self._cache[key] = (now, report, errors)
        return report, errors

    async def _run(self, sections: list[str]) -> None:
        state = self._state()
        if not state["username"]:
            self._set_text(error("Enter a Reddit username first"))
            return

        self._set_text(info(f"Collecting Reddit archives for u/{state['username']}…"))
        self._busy(True)
        try:
            report, errors = await self._report(state)
            self._set_text(
                self.reddit.render_report(report, sections=sections, errors=errors)
            )
        except Exception as exc:  # noqa: BLE001 - surface everything to the user
            logger.exception("Reddit OSINT failed")
            self._set_text(error(f"Reddit OSINT failed: {exc}"))
        finally:
            self._busy(False)

    # ── actions ─────────────────────────────────────────────────

    async def full_report(self) -> None:
        await self._run(ALL_SECTIONS)

    async def posts(self) -> None:
        await self._run(["posts"])

    async def comments(self) -> None:
        await self._run(["comments"])

    async def removed(self) -> None:
        await self._run(["removed"])

    async def identifiers(self) -> None:
        await self._run(["identifiers"])

    async def activity(self) -> None:
        await self._run(["activity"])

    async def affiliations(self) -> None:
        await self._run(["affiliations"])

    async def archive_search(self) -> None:
        state = self._state()
        if not state["keywords"]:
            self._set_text(error("Enter keywords to search the archive"))
            return

        if self.proxy is not None:
            self.reddit.set_proxy(self.proxy.get_proxy_url())

        self._set_text(info(f"Searching the archive for {state['keywords']!r}…"))
        self._busy(True)
        try:
            rows = await self.reddit.search_archive(
                keywords=state["keywords"],
                author=state["username"] or None,
                subreddit=state["subreddit"],
            )
            self._set_text(
                self.reddit.render_search(
                    rows,
                    keywords=state["keywords"],
                    author=state["username"] or None,
                )
            )
        except Exception as exc:  # noqa: BLE001 - surface everything to the user
            logger.exception("Reddit archive search failed")
            self._set_text(error(f"Reddit archive search failed: {exc}"))
        finally:
            self._busy(False)
