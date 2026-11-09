"""Tokyo Stock Exchange domestic stocks from JPX's list of listed issues."""
from typing import Callable

from chart_screenshots.symbol_sources.http import download, read_excel

JPX_LIST_URL = (
    "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx"
)
MARKET_COLUMN = "市場・商品区分"  # market / product category
CODE_COLUMN = "コード"  # securities code
DOMESTIC_STOCK_MARKER = "内国株式"  # "domestic stocks" in Prime, Standard and Growth


def parse_tse(content: bytes) -> list[str]:
    """Domestic stocks only: no ETFs, REITs, PRO Market or foreign stocks."""
    frame = read_excel(content)
    is_domestic = frame[MARKET_COLUMN].fillna("").str.contains(DOMESTIC_STOCK_MARKER, regex=False)
    return [f"{code.strip()}.T" for code in frame.loc[is_domestic, CODE_COLUMN].dropna()]


def fetch_tse(download: Callable[..., bytes] = download) -> list[str]:
    return parse_tse(download(JPX_LIST_URL))
