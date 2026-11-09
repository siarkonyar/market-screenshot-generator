"""Binance USDT-margined perpetual futures that are currently trading."""
import json
import re
from typing import Callable

from chart_screenshots.symbol_sources.http import SymbolSourceError, download

EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
PLAIN_SYMBOL = re.compile(r"[A-Z0-9]+")  # skips contracts named in Chinese characters


def parse_binance(content: bytes) -> list[str]:
    try:
        contracts = json.loads(content)["symbols"]
    except (ValueError, KeyError, TypeError) as error:
        raise SymbolSourceError(f"Unexpected format in {EXCHANGE_INFO_URL}: {error!r}") from error
    return [
        contract["symbol"]
        for contract in contracts
        if contract.get("contractType") == "PERPETUAL"
        and contract.get("quoteAsset") == "USDT"
        and contract.get("status") == "TRADING"
        and PLAIN_SYMBOL.fullmatch(contract.get("symbol", ""))
    ]


def fetch_binance(download: Callable[..., bytes] = download) -> list[str]:
    return parse_binance(download(EXCHANGE_INFO_URL))
