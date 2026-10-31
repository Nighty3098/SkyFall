import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.controllers.dorking_controller import DorkingController


class DorkingControllerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.item = SimpleNamespace(text=lambda: "site:example.com")
        self.ui = SimpleNamespace(
            useCustomDorkCheck=SimpleNamespace(isChecked=lambda: False),
            useSearxngCheck=SimpleNamespace(isChecked=lambda: True),
            dorksList=SimpleNamespace(currentItem=lambda: self.item),
            customDorkEdit=SimpleNamespace(text=lambda: "custom dork"),
            dorksResult=SimpleNamespace(
                setPlainText=lambda value: setattr(self, "result", value)
            ),
        )
        self.search_dork = AsyncMock(return_value="search results")
        self.controller = DorkingController(
            ui=self.ui,
            google_dorks_db=object(),
            dorks_search_engine=SimpleNamespace(search_dork=self.search_dork),
        )

    async def test_button_search_uses_current_item(self):
        await self.controller.search_dork()

        self.search_dork.assert_awaited_once_with("site:example.com", True)
        self.assertEqual(self.result, "search results")

    async def test_custom_dork_search_does_not_require_list_item(self):
        self.ui.useCustomDorkCheck.isChecked = lambda: True

        await self.controller.search_dork()

        self.search_dork.assert_awaited_once_with("custom dork", True)

    async def test_missing_selection_displays_error(self):
        self.ui.dorksList.currentItem = lambda: None

        await self.controller.search_dork()

        self.search_dork.assert_not_awaited()
        self.assertIn("Select a dork", self.result)


if __name__ == "__main__":
    unittest.main()
