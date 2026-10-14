import logging

from loguru import logger
from maigret import search as maigret_search
from maigret.db_updater import BUNDLED_DB_PATH
from maigret.sites import MaigretDatabase

_maigret_logger = logging.getLogger("maigret")
_maigret_logger.setLevel(logging.WARNING)


class MaigretSearch:
    def __init__(self):
        self.db = MaigretDatabase().load_from_path(BUNDLED_DB_PATH)

    async def search_and_report(
        self,
        username: str,
        on_progress=None,
        top_sites=510,
    ) -> dict:
        try:
            all_results = await self._search_all(username, on_progress, top_sites)
            return self.report(username, all_results)
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return {"error": f"Error during search: {e}"}

    async def search_and_report_structured(
        self,
        username: str,
        on_progress=None,
        top_sites=510,
    ) -> tuple[dict, list[dict]]:
        try:
            all_results = await self._search_all(username, on_progress, top_sites)
            return self.report_structured(username, all_results)
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return {"error": f"Error during search: {e}"}, []

    async def _search_all(self, username, on_progress=None, top_sites=510):
        sites = self.db.ranked_sites_dict(top=top_sites, disabled=False)
        all_results = {}
        sites_list = list(sites.items())
        total = len(sites_list)
        chunk_size = max(50, total // 10)

        for i in range(0, total, chunk_size):
            chunk = dict(sites_list[i : i + chunk_size])
            try:
                results = await maigret_search(
                    username=username,
                    site_dict=chunk,
                    logger=_maigret_logger,
                    timeout=30,
                    is_parsing_enabled=True,
                    max_connections=100,
                )
                all_results.update(results)
            except Exception as e:
                logger.error(f"Maigret chunk error: {e}")

            done = min(i + chunk_size, total)
            if on_progress:
                on_progress(done, total)

        return all_results

    def report_structured(self, username: str, data: dict) -> tuple[dict, list[dict]]:
        matches, _, _, _ = self._collect_matches(data)
        return self.report(username, data), matches

    def _collect_matches(self, data: dict) -> tuple[list[dict], list, list, list]:
        from maigret.result import MaigretCheckStatus

        matches = []
        not_found = []
        unknown = []
        disabled = []

        for site_name, result in data.items():
            status_result = result.get("status")
            url_user = result.get("url_user", "")

            if status_result is None:
                unknown.append(site_name)
                continue

            status = status_result.status

            if status == MaigretCheckStatus.CLAIMED:
                matches.append(
                    {
                        "site": site_name,
                        "url_user": url_user,
                        "status": str(status),
                        "ids": status_result.ids_data or {},
                    }
                )
            elif status == MaigretCheckStatus.AVAILABLE:
                not_found.append(site_name)
            elif status == MaigretCheckStatus.ILLEGAL:
                disabled.append(site_name)
            else:
                unknown.append(site_name)

        return matches, not_found, unknown, disabled

    def report(self, username: str, data: dict) -> dict:
        matches, not_found, unknown, disabled = self._collect_matches(data)

        result: dict = {"username": username}
        if matches:
            result["Found accounts"] = [
                {
                    "site": match["site"],
                    "url": match["url_user"],
                    "status": match["status"],
                    "ids": match.get("ids") or {},
                }
                for match in matches
            ]
        else:
            result["Found accounts"] = ["No accounts found."]

        if not_found:
            display = not_found[:50]
            if len(not_found) > 50:
                display = list(display) + [f"... and {len(not_found) - 50} more"]
            result["Not found"] = display

        if disabled:
            display = disabled[:30]
            if len(disabled) > 30:
                display = list(display) + [f"... and {len(disabled) - 30} more"]
            result["Disabled"] = display

        if unknown:
            display = [str(s) for s in unknown[:20]]
            if len(unknown) > 20:
                display = display + [f"... and {len(unknown) - 20} more"]
            result["Unknown/Error"] = display

        return result
