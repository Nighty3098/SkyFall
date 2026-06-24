from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import (
    end_of,
    error,
)

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

    async def parse_validate(self):
        number = self._get_number()
        if not number:
            self.ui.phoneDebug.appendPlainText(error("Enter a phone number"))
            return

        self.ui.phoneDebug.clear()
        self.ui.phoneProgress.setValue(0)
        self.ui.phoneProgress.setRange(0, 0)

        try:
            result = self.phone_search.parse_and_validate(
                number,
                default_region=self._get_region(),
            )
            self.ui.phoneDebug.appendPlainText(result)
            self.ui.phoneDebug.appendPlainText(end_of("parse"))
        except Exception as e:
            self.ui.phoneDebug.appendPlainText(error(f"Error: {e}"))
        finally:
            self.ui.phoneProgress.setRange(0, 100)
            self.ui.phoneProgress.setValue(100)

    async def reverse_lookup(self):
        number = self._get_number()
        if not number:
            self.ui.phoneDebug.appendPlainText(error("Enter a phone number"))
            return

        self.ui.phoneDebug.clear()
        self.ui.phoneProgress.setValue(0)
        self.ui.phoneProgress.setRange(0, 0)

        try:
            result = await self.phone_search.reverse_lookup(
                number,
                numverify_key=self.numverify_key,
                abstractapi_key=self.abstractapi_key,
            )
            self.ui.phoneDebug.appendPlainText(result)
            self.ui.phoneDebug.appendPlainText(end_of("reverse lookup"))
        except Exception as e:
            self.ui.phoneDebug.appendPlainText(error(f"Error: {e}"))
        finally:
            self.ui.phoneProgress.setRange(0, 100)
            self.ui.phoneProgress.setValue(100)

    async def check_leaks(self):
        number = self._get_number()
        if not number:
            self.ui.phoneDebug.appendPlainText(error("Enter a phone number"))
            return

        self.ui.phoneDebug.clear()
        self.ui.phoneProgress.setValue(0)
        self.ui.phoneProgress.setRange(0, 0)

        try:
            result = await self.phone_search.check_leaks(
                number,
                intelx_key=self.intelx_key,
            )
            self.ui.phoneDebug.appendPlainText(result)
            self.ui.phoneDebug.appendPlainText(end_of("leak check"))
        except Exception as e:
            self.ui.phoneDebug.appendPlainText(error(f"Error: {e}"))
        finally:
            self.ui.phoneProgress.setRange(0, 100)
            self.ui.phoneProgress.setValue(100)
