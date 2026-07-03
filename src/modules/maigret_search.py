import logging

from loguru import logger
from maigret import search as maigret_search
from maigret.db_updater import BUNDLED_DB_PATH
from maigret.sites import MaigretDatabase

from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    info,
    kv,
    section,
    title,
)

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
        output_lines.append(divider())
        output_lines.append(title(f"Searching: {username}") + "\n")

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
            output_lines.append(info(f"Found accounts: {len(matches)}"))
            for match in matches:
                output_lines.append(
                    bullet(
                        f"{match['site']}: {match['url_user']} (Status: {match['status']})"
                    )
                )
                if match["ids"]:
                    for k, v in match["ids"].items():
                        output_lines.append(kv(k, v))
            output_lines.append("")
        else:
            output_lines.append(info("No accounts found.") + "\n")

        if not_found:
            display = not_found[:50]
            output_lines.append(section("Not found"))
            for item in display:
                output_lines.append(bullet(item))
            if len(not_found) > 50:
                output_lines.append(bullet(f"... and {len(not_found) - 50} more"))

        if disabled:
            display = disabled[:30]
            output_lines.append(section("Disabled"))
            for item in display:
                output_lines.append(bullet(item))
            if len(disabled) > 30:
                output_lines.append(bullet(f"... and {len(disabled) - 30} more"))

        if unknown:
            display = [str(s) for s in unknown[:20]]
            output_lines.append(section("Unknown/Error"))
            for item in display:
                output_lines.append(bullet(item))
            if len(unknown) > 20:
                output_lines.append(bullet(f"... and {len(unknown) - 20} more"))

        output_lines.append(end_of("maigret search"))
        output_lines.append(divider())
        return "\n".join(output_lines)
