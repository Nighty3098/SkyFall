import asyncio
import datetime
import sys
from pathlib import Path

from loguru import logger

_txfetch_path = str(Path(__file__).parent.parent.parent / "thirdparty" / "txfetch")
if _txfetch_path not in sys.path:
    sys.path.insert(0, _txfetch_path)


class BlockchainSearch:
    def __init__(self, settings: dict | None = None):
        logger.debug("Init: BlockchainSearch")
        self._adapters: dict = {}
        if settings:
            self._set_env_keys(settings)
        self._import_adapters()

    def _set_env_keys(self, settings: dict):
        from modules import config as txfetch_config

        key_map = {
            "TRONGRID_API_KEY": settings.get("trongrid_api_key"),
            "ETHERSCAN_API_KEY": settings.get("etherscan_api_key"),
            "BSCSCAN_API_KEY": settings.get("bscscan_api_key"),
            "TONAPI_KEY": settings.get("tonapi_api_key"),
            "HELIUS_API_KEY": settings.get("helius_api_key"),
        }
        for env_key, val in key_map.items():
            if val:
                txfetch_config.setenv(env_key, val)

        # Patch frozen class-level API_KEY on EVM adapter classes
        _patch_map = {
            "eth": "etherscan_api_key",
            "bsc": "bscscan_api_key",
            "base": "etherscan_api_key",
        }
        for name, settings_key in _patch_map.items():
            val = settings.get(settings_key)
            cls = self._adapters.get(name)
            if val and cls and hasattr(cls, "API_KEY"):
                cls.API_KEY = val

    def _import_adapters(self):
        from modules.base_chain import BaseAdapter
        from modules.bch import BCHAdapter
        from modules.bsc import BSCAdapter
        from modules.btc import BTCAdapter
        from modules.doge import DOGEAdapter
        from modules.eth import ETHAdapter
        from modules.ltc import LTCAdapter
        from modules.sol import SolanaAdapter
        from modules.ton import TonAdapter
        from modules.tron import TronAdapter

        self._adapters = {
            "tron": TronAdapter,
            "ton": TonAdapter,
            "eth": ETHAdapter,
            "bsc": BSCAdapter,
            "base": BaseAdapter,
            "sol": SolanaAdapter,
            "btc": BTCAdapter,
            "ltc": LTCAdapter,
            "doge": DOGEAdapter,
            "bch": BCHAdapter,
        }

    async def search(
        self,
        network: str,
        coin: str,
        time_from: datetime.datetime,
        time_to: datetime.datetime,
        amount: float | None = None,
        amount_to: float | None = None,
        amount_tolerance: float = 0.01,
        memo: str | None = None,
    ) -> dict:
        from modules.models import TXQuery

        network = network.lower()
        coin = coin.upper()

        adapter_cls = self._adapters.get(network)
        if not adapter_cls:
            return {
                "network": network,
                "coin": coin,
                "error": f"Unsupported network: {network}",
            }

        query = TXQuery(
            time_from=time_from,
            time_to=time_to,
            coin=coin,
            amount=amount,
            amount_to=amount_to,
            amount_tolerance=amount_tolerance,
            memo=memo,
        )

        try:
            adapter = adapter_cls()
            candidates = await asyncio.to_thread(adapter.fetch_candidates, query)
        except Exception as e:
            logger.error(f"Blockchain search error: {e}")
            return {"network": network, "coin": coin, "error": f"Search failed: {e}"}

        data: dict = {"network": network, "coin": coin}
        if not candidates:
            data["message"] = "No transactions found matching criteria."
            return data

        transactions = []
        for c in candidates:
            tx: dict = {
                "confidence": f"{c.confidence:.0%}",
                "tx_id": c.tx_id,
                "time": c.timestamp.strftime("%H:%M:%S"),
                "amount": f"{c.amount:.6f} {c.coin}",
            }
            detail = c.score_detail
            if detail:
                parts = []
                if "time_delta_sec" in detail:
                    parts.append(f"Δt={detail['time_delta_sec']}s")
                if "time_score" in detail:
                    parts.append(f"T={detail['time_score']}")
                if "amount_score" in detail:
                    parts.append(f"A={detail['amount_score']}")
                if "memo_score" in detail:
                    parts.append(f"M={detail['memo_score']}")
                if parts:
                    tx["scores"] = " | ".join(parts)
            if c.from_address or c.to_address:
                tx["from"] = c.from_address or "-"
                tx["to"] = c.to_address or "-"
            if c.memo:
                tx["memo"] = c.memo
            transactions.append(tx)

        data["count"] = len(transactions)
        data["transactions"] = transactions
        return data
