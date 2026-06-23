import logging

from loguru import logger
from maigret import search as maigret_search
from maigret.sites import MaigretDatabase
from maigret.db_updater import BUNDLED_DB_PATH

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
    ) -> str:
        try:
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

            return self.report(username, all_results)

        except Exception as e:
            error_msg = f"Error during search: {e}"
            logger.error(error_msg)
            return error_msg

    def report(self, username: str, data: dict) -> str:
        from maigret.result import MaigretCheckStatus

        output_lines = []
        output_lines.append(f"Searching: {username}\n")

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

        if matches:
            output_lines.append(f"Found accounts: {len(matches)}")
            for match in matches:
                output_lines.append(
                    f"  - {match['site']}: {match['url_user']} (Status: {match['status']})"
                )
                if match["ids"]:
                    for k, v in match["ids"].items():
                        output_lines.append(f"    {k}: {v}")
            output_lines.append("")
        else:
            output_lines.append("No accounts found.\n")

        if not_found:
            display = not_found[:50]
            suffix = "..." if len(not_found) > 50 else ""
            output_lines.append(f"Not found on: {', '.join(display)}{suffix}")

        if disabled:
            display = disabled[:30]
            suffix = "..." if len(disabled) > 30 else ""
            output_lines.append(f"Skipped (disabled): {', '.join(display)}{suffix}")

        if unknown:
            display = [str(s) for s in unknown[:20]]
            suffix = "..." if len(unknown) > 20 else ""
            output_lines.append(f"Unknown/Error on: {', '.join(display)}{suffix}")

        return "\n".join(output_lines)
