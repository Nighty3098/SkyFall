import asyncio

from ddgs import DDGS
from loguru import logger

from src.searxng_search import searxng_search


class DorksSearchEngine:
    def __init__(self) -> None:
        logger.debug("Init: DorksSearchEngine")

        self._last_search = ""

    async def search_dork(self, dork: str, use_searxng: bool = False):
        try:
            logger.debug("Running dork: {}", dork)
            self._last_search = ""

            if use_searxng:
                def _search_searxng():
                    local_results = ""
                    results = searxng_search(dork)
                    count = 0
                    for index, r in enumerate(results, start=1):
                        local_results += (
                            f"\n{index} - {r['title']}"
                            f"\nURL: {r['href']}\nSNIPPET: {r['body']}\n"
                        )
                        count += 1
                    return local_results, count

                result, count = await asyncio.to_thread(_search_searxng)
                self._last_search = result
            else:
                def _search_ddgs():
                    local_results = ""
                    with DDGS() as ddgs:
                        results = ddgs.text(dork, max_results=1000000000)
                        count = 0
                        for index, r in enumerate(results, start=1):
                            local_results += (
                                f"\n{index} - {r['title']}"
                                f"\nURL: {r['href']}\nSNIPPET: {r['body']}\n"
                            )
                            count += 1
                    return local_results, count

                result, count = await asyncio.to_thread(_search_ddgs)
                self._last_search = result

            if count == 0:
                return "Not found."
            else:
                logger.debug("Dork search completed successfully")
                return self._last_search

        except Exception as e:
            return f"Error: {e}"
