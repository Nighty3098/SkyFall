import json

from loguru import logger


class GoogleDorksDB:
    def __init__(self):
        logger.debug("Init: GoogleDorksDB")

        self.dorks_db_path = "data/dorks.json"
        self.dorks_db: dict[str, dict[str, list[str]]] = {}

    def _load_dorks_db(self):
        if self.dorks_db_path in self.dorks_db:
            return self.dorks_db[self.dorks_db_path]

        try:
            with open(self.dorks_db_path, encoding="utf-8") as db:
                data = json.load(db)
        except FileNotFoundError:
            raise FileNotFoundError(f"File '{self.dorks_db_path}' not found.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error reading JSON file: '{self.dorks_db_path}': {e}")

        if not isinstance(data, dict):
            raise ValueError(
                "JSON must contain an object (dictionary) at the top level."
            )

        cleaned = {}
        for category, dorks in data.items():
            if isinstance(dorks, list):
                cleaned[category] = [str(d) for d in dorks]
            else:
                cleaned[category] = [str(dorks)]

        self.dorks_db[self.dorks_db_path] = cleaned
        return cleaned

    def get_all_categories(self) -> list[str]:
        data = self._load_dorks_db()
        return sorted(data.keys())

    def get_dorks_by_category(self, category: str) -> list[str]:
        data = self._load_dorks_db()
        return data.get(category, [])


if __name__ == "__main__":
    from loguru import logger

    gddb = GoogleDorksDB()
    categories = gddb.get_all_categories()
    category = "Vulnerable Files"
    logger.info(gddb.get_dorks_by_category(category))
