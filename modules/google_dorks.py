import json
from typing import Dict, List


class GoogleDorksDB:
    def __init__(self):
        self.dorks_db_path = "data/dorks.json"
        self.dorks_db: Dict[str, Dict[str, List[str]]] = {}

    def _loadDorksDB(self):
        if self.dorks_db_path in self.dorks_db:
            return self.dorks_db[self.dorks_db_path]

        try:
            with open(self.dorks_db_path, "r", encoding="utf-8") as db:
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

    def getAllCategories(self) -> List[str]:
        data = self._loadDorksDB()
        return sorted(data.keys())

    def getDorksByCategory(self, category: str) -> List[str]:
        data = self._loadDorksDB()
        return data.get(category, [])


if __name__ == "__main__":
    gddb = GoogleDorksDB()
    categories = gddb.getAllCategories()
    category = "Vulnerable Files"
    print(gddb.getDorksByCategory(category))
