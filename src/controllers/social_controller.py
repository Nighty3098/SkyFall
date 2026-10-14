from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.social_search import SocialSearch


class SocialController:
    def __init__(self, ui: "QMainWindow", social_search: "SocialSearch"):
        logger.debug("Init: SocialController")
        self.ui = ui
        self.social_search = social_search

    async def search(self, username, instance=None):
        widget = getattr(self.ui, "socialDebug", None)
        if widget is None:
            return
        instance = instance or getattr(self.ui, "socialInstanceEdit", None)
        instance_text = instance.text() if instance is not None else None
        widget.setPlainText("Searching social networks...")
        data = await self.social_search.search(username, instance_text or None)
        widget.setPlainText(render(data, f"Social search: {username}"))

    async def search_bluesky(self, username):
        widget = getattr(self.ui, "socialDebug", None)
        if widget is None:
            return
        if not username:
            widget.setPlainText("Empty username")
            return
        widget.setPlainText("Searching Bluesky...")
        profile = await self.social_search.bluesky_profile(username)
        matches = await self.social_search.bluesky_search(username)
        data = {
            "profile": profile or {"note": "no exact profile"},
            "matches": [
                f"{a.get('handle', '?')} ({a.get('displayName', '')})"
                for a in matches[:10]
            ],
        }
        widget.setPlainText(render(data, f"Bluesky: {username}"))

    async def search_mastodon(self, username):
        widget = getattr(self.ui, "socialDebug", None)
        if widget is None:
            return
        if not username:
            widget.setPlainText("Empty username")
            return
        widget.setPlainText("Searching Mastodon...")
        account = await self.social_search.mastodon_lookup(username)
        matches = await self.social_search.mastodon_search(username)
        data = {
            "account": account or {"note": "no account on instance"},
            "matches": [
                f"@{a.get('acct', '?')} ({a.get('display_name', '')})"
                for a in matches[:10]
            ],
        }
        widget.setPlainText(render(data, f"Mastodon: {username}"))

    async def search_instagram(self, username):
        widget = getattr(self.ui, "socialDebug", None)
        if widget is None:
            return
        if not username:
            widget.setPlainText("Empty username")
            return
        widget.setPlainText("Searching Instagram...")
        data = await self.social_search.instagram_profile(username)
        if data.get("error"):
            widget.setPlainText(render({"error": data["error"]}, "Instagram"))
            return
        widget.setPlainText(
            render(data, f"Instagram: @{data.get('username', username)}")
        )
