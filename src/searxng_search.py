import requests
from loguru import logger


def searxng_search(query: str, instance_url: str = "http://localhost:8080"):
    url = f"{instance_url}/search"
    formatted_results = []
    seen_urls = set()
    page = 1

    logger.info("Starting unlimited search for query: '{}'", query)

    while True:
        params = {
            "q": query,
            "format": "json",
            "lang": "ru",
            "pageno": page,
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            raw_results = response.json().get("results", [])

            if not raw_results:
                logger.debug("Page {} is empty. Search finished.", page)
                break

            new_results_on_page = 0

            for r in raw_results:
                link = r.get("url")

                if not link or link in seen_urls:
                    continue

                seen_urls.add(link)
                new_results_on_page += 1

                formatted_results.append(
                    {
                        "title": r.get("title", "No Title"),
                        "href": link,
                        "body": r.get("content", ""),
                    }
                )

            logger.debug(
                "Page {}: Found {} raw results ({} uniques added)",
                page,
                len(raw_results),
                new_results_on_page,
            )

            if new_results_on_page == 0 and page > 5:
                logger.debug("No new unique results found. Stopping to avoid loop.")
                break

            page += 1

        except Exception as e:
            logger.error("Error on page {}: {}. Returning accumulated data.", page, e)
            break

    return formatted_results
