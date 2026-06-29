import asyncio
import datetime
import os
import sys
from collections.abc import Callable
from pathlib import Path

from loguru import logger

from src.ui.output_formatter import (
    divider,
    end_of,
    error,
    info,
    kv,
    title,
)

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
        key_map = {
            "TRONGRID_API_KEY": settings.get("trongrid_api_key"),
            "ETHERSCAN_API_KEY": settings.get("etherscan_api_key"),
            "BSCSCAN_API_KEY": settings.get("bscscan_api_key"),
            "TONAPI_KEY": settings.get("tonapi_api_key"),
            "HELIUS_API_KEY": settings.get("helius_api_key"),
        }
        for env_key, val in key_map.items():
            if val:
                os.environ[env_key] = val

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
        on_result: Callable | None = None,
    ) -> str:
        from modules.models import TXQuery

        network = network.lower()
        coin = coin.upper()

        adapter_cls = self._adapters.get(network)
        if not adapter_cls:
            msg = error(f"Unsupported network: {network}")
            if on_result:
                on_result(msg)
            return msg

        query = TXQuery(
            time_from=time_from,
            time_to=time_to,
            coin=coin,
            amount=amount,
            amount_to=amount_to,
            amount_tolerance=amount_tolerance,
            memo=memo,
        )

        lines = [title(f"Blockchain: {network.upper()} / {coin}")]
        if on_result:
            on_result(lines[-1])

        try:
            adapter = adapter_cls()
            candidates = await asyncio.to_thread(adapter.fetch_candidates, query)
        except Exception as e:
            msg = error(f"Search failed: {e}")
            logger.error(f"Blockchain search error: {e}")
            if on_result:
                on_result(msg)
            return msg

        if not candidates:
            msg = info("No transactions found matching criteria.")
            if on_result:
                on_result(msg)
            lines.append(msg)
            lines.append(end_of("blockchain search"))
            if on_result:
                on_result(lines[-1])
            return "\n".join(lines)

        lines.append(kv("Results", len(candidates)))
        if on_result:
            on_result(lines[-1])

        for i, c in enumerate(candidates, 1):
            line_text = (
                f"  {i}. [{c.confidence:.0%}] {c.tx_id[:16]}..."
                f"  |  {c.timestamp.strftime('%H:%M:%S')}"
                f"  |  {c.amount:.6f} {c.coin}"
            )
            lines.append(line_text)
            if on_result:
                on_result(line_text)

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
                    detail_text = kv("Scores", " | ".join(parts))
                    lines.append(detail_text)
                    if on_result:
                        on_result(detail_text)

            if c.from_address or c.to_address:
                addr_text = (
                    f"    From: {c.from_address or '-'}"
                    f"  \u2192  To: {c.to_address or '-'}"
                )
                lines.append(addr_text)
                if on_result:
                    on_result(addr_text)

            if c.memo:
                memo_text = kv("Memo", c.memo)
                lines.append(memo_text)
                if on_result:
                    on_result(memo_text)

        lines.append(divider())
        if on_result:
            on_result(lines[-1])
        lines.append(end_of("blockchain search"))
        if on_result:
            on_result(lines[-1])
        return "\n".join(lines)
