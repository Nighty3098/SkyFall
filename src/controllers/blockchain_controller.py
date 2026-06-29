import datetime
from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import error

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.blockchain_search import BlockchainSearch


NETWORK_MAP = {
    "tron": "tron",
    "ton": "ton",
    "eth": "eth",
    "bsc": "bsc",
    "base": "base",
    "sol": "sol",
    "btc": "btc",
    "ltc": "ltc",
    "doge": "doge",
    "bch": "bch",
}


class BlockchainController:
    def __init__(
        self,
        ui: "QMainWindow",
        blockchain_search: "BlockchainSearch",
    ):
        logger.debug("Init: BlockchainController")
        self.ui = ui
        self.blockchain_search = blockchain_search

    def _get_network(self) -> str | None:
        text = self.ui.bcNetworkCombo.currentText().strip().lower()
        return NETWORK_MAP.get(text)

    def _get_coin(self) -> str:
        return self.ui.bcCoinCombo.currentText().strip().upper()

    def _get_date(self) -> tuple[datetime.date, datetime.date] | None:
        raw = self.ui.bcDateEdit.text().strip()
        if not raw:
            return None

        try:
            if "-" in raw:
                parts = raw.split("-", 1)
                d1 = datetime.datetime.strptime(parts[0].strip(), "%d.%m.%Y").date()
                d2 = datetime.datetime.strptime(parts[1].strip(), "%d.%m.%Y").date()
                return (d1, d2)
            else:
                d = datetime.datetime.strptime(raw, "%d.%m.%Y").date()
                return (d, d)
        except ValueError:
            return None

    def _get_time(self) -> datetime.time | None:
        raw = self.ui.bcTimeEdit.text().strip()
        if not raw:
            return None
        try:
            if raw.count(":") == 2:
                return datetime.datetime.strptime(raw, "%H:%M:%S").time()
            else:
                return datetime.datetime.strptime(raw, "%H:%M").time()
        except ValueError:
            return None

    def _get_time_range_seconds(self) -> int | None:
        text = self.ui.bcTimeRangeCombo.currentText().strip()
        mapping = {
            "exact": 0,
            "±1min": 60,
            "±5min": 300,
            "±15min": 900,
            "custom": None,
        }
        return mapping.get(text)

    def _get_amount(self) -> tuple[float | None, float | None]:
        raw = self.ui.bcAmountEdit.text().strip()
        if not raw:
            return (None, None)
        try:
            if "-" in raw:
                parts = raw.split("-", 1)
                return (float(parts[0].strip()), float(parts[1].strip()))
            else:
                return (float(raw), None)
        except ValueError:
            return (None, None)

    def _get_tolerance(self) -> float:
        return self.ui.bcToleranceSpin.value()

    def _get_memo(self) -> str | None:
        text = self.ui.bcMemoEdit.text().strip()
        return text or None

    def _append(self, text: str):
        self.ui.bcDebug.appendPlainText(text)

    def _clear(self):
        self.ui.bcDebug.clear()

    async def search(self):
        network = self._get_network()
        if not network:
            self._append(error("Select a network"))
            return

        coin = self._get_coin()
        if not coin:
            self._append(error("Select a coin"))
            return

        date = self._get_date()
        if not date:
            self._append(
                error("Invalid date. Use format: DD.MM.YYYY or DD.MM.YYYY-DD.MM.YYYY")
            )
            return

        time_val = self._get_time()
        if not time_val:
            self._append(error("Invalid time. Use format: HH:MM"))
            return

        date_from, date_to = date
        time_from = datetime.datetime.combine(date_from, time_val, tzinfo=datetime.UTC)
        time_to = datetime.datetime.combine(date_to, time_val, tzinfo=datetime.UTC)

        range_sec = self._get_time_range_seconds()
        if range_sec is None:
            self._append(error("Custom time range not supported yet. Use preset."))
            return

        if range_sec > 0:
            time_from -= datetime.timedelta(seconds=range_sec)
            time_to += datetime.timedelta(seconds=range_sec)
        else:
            time_to += datetime.timedelta(seconds=59)

        amount, amount_to = self._get_amount()
        tolerance = self._get_tolerance()
        memo = self._get_memo()

        self._clear()
        self.ui.bcProgressBar.setValue(0)
        self.ui.bcProgressBar.setRange(0, 0)

        try:
            await self.blockchain_search.search(
                network=network,
                coin=coin,
                time_from=time_from,
                time_to=time_to,
                amount=amount,
                amount_to=amount_to,
                amount_tolerance=tolerance,
                memo=memo,
                on_result=self._append,
            )
        except Exception as e:
            self._append(error(f"Error: {e}"))
            logger.error(f"BlockchainController error: {e}")
        finally:
            self.ui.bcProgressBar.setRange(0, 100)
            self.ui.bcProgressBar.setValue(100)
