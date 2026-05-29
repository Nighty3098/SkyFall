from ddgs import DDGS
from loguru import logger

from src.searxng_search import searxng_search


class DorksSearchEngine:
    def __init__(self) -> None:
        logger.debug("Init: DorksSearchEngine")

        self._last_search = ""

    def search_dork(self, dork: str, max_results: int = 100):
        try:
            logger.debug("Running dork: {}", dork)
            self._last_search = ""
            results = searxng_search(dork)
            count = 0
            for index, r in enumerate(results, start=1):
                self._last_search += f"\n{index} - {r['title']}\nURL: {r['href']}\nSNIPPET: {r['body']}\n"
                count += 1
            if count == 0:
                return "Not found."
            else:
                logger.debug("Dork search completed successfully")
                return self._last_search
        except Exception as e:
            return f"Error: {e}"
