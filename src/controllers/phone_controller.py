from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import error, render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.phone_search import PhoneSearch


class PhoneController:
    def __init__(
        self,
        ui: "QMainWindow",
        phone_search: "PhoneSearch",
        numverify_key: str = "",
        abstractapi_key: str = "",
        intelx_key: str = "",
    ):
        logger.debug("Init: PhoneController")
        self.ui = ui
        self.phone_search = phone_search
        self.numverify_key = numverify_key
        self.abstractapi_key = abstractapi_key
        self.intelx_key = intelx_key

    def _get_number(self) -> str:
        return self.ui.phoneNumberEdit.text().strip()

    def _get_region(self) -> str:
        return self.ui.phoneRegionEdit.text().strip() or None

    async def _run(self, coro):
        number = self._get_number()
        if not number:
            self.ui.phoneDebug.setPlainText(error("Enter a phone number"))
            return

        self.ui.phoneDebug.clear()
        self.ui.phoneProgress.setValue(0)
        self.ui.phoneProgress.setRange(0, 0)

        try:
            result = await coro(number)
            self.ui.phoneDebug.setPlainText(render(result, title=f"Phone: {number}"))
        except Exception as e:
            self.ui.phoneDebug.setPlainText(error(f"Error: {e}"))
        finally:
            self.ui.phoneProgress.setRange(0, 100)
            self.ui.phoneProgress.setValue(100)

    async def parse_validate(self):
        number = self._get_number()
        if not number:
            self.ui.phoneDebug.setPlainText(error("Enter a phone number"))
            return

        self.ui.phoneDebug.clear()
        self.ui.phoneProgress.setValue(0)
        self.ui.phoneProgress.setRange(0, 0)

        try:
            result = self.phone_search.parse_and_validate(
                number,
                default_region=self._get_region(),
            )
            self.ui.phoneDebug.setPlainText(render(result, title=f"Phone: {number}"))
        except Exception as e:
            self.ui.phoneDebug.setPlainText(error(f"Error: {e}"))
        finally:
            self.ui.phoneProgress.setRange(0, 100)
            self.ui.phoneProgress.setValue(100)

    async def reverse_lookup(self):
        await self._run(
            lambda number: self.phone_search.reverse_lookup(
                number,
                numverify_key=self.numverify_key,
                abstractapi_key=self.abstractapi_key,
            )
        )

    async def search_7tel(self):
        await self._run(self.phone_search.search_7tel)

    async def check_leaks(self):
        await self._run(
            lambda number: self.phone_search.check_leaks(
                number,
                intelx_key=self.intelx_key,
            )
        )
