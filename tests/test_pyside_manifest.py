import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PySideManifestTest(unittest.TestCase):
    def test_manifest_lists_existing_complete_app_sources_and_resources(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        declared = set(project["tool"]["pyside6-project"]["files"])
        expected = {
            "main.py",
            "logger_setup.py",
            "setup_telegram.py",
            *(
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / "src").rglob("*.py")
            ),
            *(
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / "resources").iterdir()
                if path.is_file()
            ),
        }

        self.assertEqual(declared, expected)
        self.assertTrue(all((ROOT / path).is_file() for path in declared))


if __name__ == "__main__":
    unittest.main()
