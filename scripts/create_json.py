#!/usr/bin/env python3
"""
Скрипт для извлечения Google-дорков из XML-файла Exploit-DB GHDB
и сохранения их в JSON с группировкой по категориям.
"""

import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict


def parse_ghdb_xml(input_file, output_file):
    tree = ET.parse(input_file)
    root = tree.getroot()

    dorks_by_category = defaultdict(list)

    for entry in root.iter("entry"):
        category = entry.findtext("category", default="Unknown").strip()
        query = entry.findtext("query", default="").strip()

        if query:
            dorks_by_category[category].append(query)

    result = dict(dorks_by_category)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(
        f"Готово! Найдено {sum(len(v) for v in result.values())} дорков в {len(result)} категориях."
    )
    print(f"Результат сохранён в {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python parse_ghdb.py <входной.xml> <выходной.json>")
        sys.exit(1)

    input_xml = sys.argv[1]
    output_json = sys.argv[2]
    parse_ghdb_xml(input_xml, output_json)
