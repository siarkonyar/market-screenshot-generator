"""The markets covered by all-markets mode: where their symbols and prices come from."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from chart_screenshots.binance_data import fetch_binance_daily
from chart_screenshots.data import fetch_daily
from chart_screenshots.symbol_sources import binance, bist, euronext, fwb, krx, lse, tse, us

SYMBOLS_DIR = Path(__file__).resolve().parent.parent / "symbols"


@dataclass(frozen=True)
class Market:
    code: str
    name: str
    fetch_symbols: Callable[[], list[str]]
    fetch_daily: Callable[[str, int], pd.DataFrame]


MARKETS = (
    Market("NYS", "New York Stock Exchange", us.fetch_nyse, fetch_daily),
    Market("NASDAQ", "Nasdaq Stock Market", us.fetch_nasdaq, fetch_daily),
    Market("LSE", "London Stock Exchange", lse.fetch_lse, fetch_daily),
    Market("TSE", "Tokyo Stock Exchange", tse.fetch_tse, fetch_daily),
    Market("FWB", "Frankfurt Stock Exchange", fwb.fetch_fwb, fetch_daily),
    Market("EURONEXT", "Euronext Paris", euronext.fetch_euronext, fetch_daily),
    Market("KRX", "Korea Exchange", krx.fetch_krx, fetch_daily),
    Market("BIST", "Borsa Istanbul", bist.fetch_bist, fetch_daily),
    Market("BINANCE", "Binance USDT perpetual futures", binance.fetch_binance, fetch_binance_daily),
)


def symbols_file(market: Market, symbols_dir: Path = SYMBOLS_DIR) -> Path:
    return Path(symbols_dir) / f"{market.code}.txt"


def select_markets(codes: list[str], markets: tuple[Market, ...] = MARKETS) -> tuple[Market, ...]:
    """Pick markets by code (case-insensitive); no codes means every market."""
    wanted = {code.upper() for code in codes}
    unknown = wanted - {market.code for market in markets}
    if unknown:
        known = ", ".join(market.code for market in markets)
        raise ValueError(f"Unknown market(s): {', '.join(sorted(unknown))}. Choose from: {known}.")
    return tuple(market for market in markets if not wanted or market.code in wanted)
