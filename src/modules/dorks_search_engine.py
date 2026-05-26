from ddgs import DDGS
from loguru import logger


class DorksSearchEngine:
    def __init__(self) -> None:
        logger.debug("Init: DorksSearchEngine")

        self._last_search = ""

    def search_dork(self, dork: str, max_results: int = 100):
        try:
            logger.debug("Running dork: {}", dork)
            self._last_search = ""
            with DDGS() as ddgs:
                results = ddgs.text(dork, max_results=max_results)
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
