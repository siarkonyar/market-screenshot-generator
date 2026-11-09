"""NYSE and Nasdaq common stocks from the Nasdaq Trader symbol directory."""
import io
import re
from typing import Callable

import pandas as pd

from chart_screenshots.symbol_sources.http import download

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
NYSE_EXCHANGE_CODE = "N"
FOOTER_PREFIX = "File Creation Time"
COMMON_STOCK = re.compile(r"common stock|ordinary shares?|common shares?", re.IGNORECASE)
NOT_COMMON_STOCK = re.compile(r"depositary|warrant|\brights?\b|\bunits?\b|preferred", re.IGNORECASE)


def parse_nasdaq_listed(content: bytes) -> list[str]:
    """Common stocks listed on Nasdaq, from nasdaqlisted.txt."""
    frame = _read_pipe_table(content)
    keep = _is_plain_listing(frame) & frame["Security Name"].map(_is_common_stock)
    return [_to_yahoo(symbol) for symbol in frame.loc[keep, "Symbol"]]


def parse_nyse_listed(content: bytes) -> list[str]:
    """Common stocks listed on the New York Stock Exchange, from otherlisted.txt."""
    frame = _read_pipe_table(content)
    on_nyse = frame["Exchange"] == NYSE_EXCHANGE_CODE
    keep = on_nyse & _is_plain_listing(frame) & frame["Security Name"].map(_is_common_stock)
    return [_to_yahoo(symbol) for symbol in frame.loc[keep, "ACT Symbol"]]


def fetch_nasdaq(download: Callable[..., bytes] = download) -> list[str]:
    return parse_nasdaq_listed(download(NASDAQ_LISTED_URL))


def fetch_nyse(download: Callable[..., bytes] = download) -> list[str]:
    return parse_nyse_listed(download(OTHER_LISTED_URL))


def _read_pipe_table(content: bytes) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(content), sep="|", dtype=str, keep_default_na=False)
    return frame[~frame.iloc[:, 0].str.startswith(FOOTER_PREFIX)]


def _is_plain_listing(frame: pd.DataFrame) -> pd.Series:
    return (frame["ETF"] == "N") & (frame["Test Issue"] == "N")


def _is_common_stock(name: str) -> bool:
    return bool(COMMON_STOCK.search(name)) and not NOT_COMMON_STOCK.search(name)


def _to_yahoo(symbol: str) -> str:
    """Yahoo writes share classes with a dash: BRK.B -> BRK-B."""
    return symbol.strip().replace(".", "-")
