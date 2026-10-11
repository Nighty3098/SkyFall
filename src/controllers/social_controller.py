from typing import TYPE_CHECKING

from loguru import logger

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
        widget.setPlainText(
            await self.social_search.search(username, instance_text or None)
        )

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
        lines = [f"[+] Bluesky: {username}"]
        if profile:
            lines.append(f"  handle: {profile.get('handle', '?')}")
            lines.append(f"  display: {profile.get('displayName', '')}")
            lines.append(f"  followers: {profile.get('followersCount', '?')}")
            lines.append(f"  posts: {profile.get('postsCount', '?')}")
        else:
            lines.append("  [i] no exact profile")
        for a in matches[:10]:
            lines.append(f"  - {a.get('handle', '?')} ({a.get('displayName', '')})")
        widget.setPlainText("\n".join(lines))

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
        lines = [f"[+] Mastodon: {username}"]
        if account:
            lines.append(f"  @{account.get('acct', '?')}")
            lines.append(f"  display: {account.get('display_name', '')}")
            lines.append(f"  followers: {account.get('followers_count', '?')}")
            lines.append(f"  posts: {account.get('statuses_count', '?')}")
        else:
            lines.append("  [i] no account on instance")
        for a in matches[:10]:
            lines.append(f"  - @{a.get('acct', '?')} ({a.get('display_name', '')})")
        widget.setPlainText("\n".join(lines))

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
            widget.setPlainText(f"[i] Instagram: {data['error']}")
            return
        lines = [f"[+] Instagram: @{data.get('username', '?')}"]
        lines.append(f"  name: {data.get('full_name', '')}")
        lines.append(f"  followers: {data.get('followers', '?')}")
        lines.append(f"  following: {data.get('followees', '?')}")
        lines.append(f"  posts: {data.get('posts', '?')}")
        lines.append(f"  private: {data.get('is_private', False)}")
        lines.append(f"  verified: {data.get('is_verified', False)}")
        if data.get("external_url"):
            lines.append(f"  url: {data['external_url']}")
        widget.setPlainText("\n".join(lines))
