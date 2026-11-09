"""London Stock Exchange company shares from the monthly instrument list."""
import json
from typing import Callable

from chart_screenshots.symbol_sources.http import (
    SymbolSourceError,
    download,
    read_excel,
    table_below_header,
)

LATEST_REPORT_URL = "https://docs.londonstockexchange.com/reports/instruments/latest.json"
SHARES_SHEET = "1.1 Shares"
EXCLUDED_LISTING_CATEGORIES = {"Closed-ended investment funds"}


def find_report_link(content: bytes) -> str:
    """Read the current instrument list's download link from latest.json."""
    try:
        return json.loads(content)["Data"][0]["downloadLink"]
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise SymbolSourceError(f"Unexpected format in {LATEST_REPORT_URL}: {error!r}") from error


def parse_lse_shares(content: bytes) -> list[str]:
    """Company shares from the 'Shares' sheet, without closed-ended investment funds."""
    raw = read_excel(content, sheet_name=SHARES_SHEET, header=None)
    table = table_below_header(raw, "TIDM")
    category = table["FCA Listing Category"].fillna("").str.strip()
    tidms = table.loc[~category.isin(EXCLUDED_LISTING_CATEGORIES), "TIDM"].dropna()
    return [_to_yahoo(tidm) for tidm in tidms]


def fetch_lse(download: Callable[..., bytes] = download) -> list[str]:
    report_url = find_report_link(download(LATEST_REPORT_URL))
    return parse_lse_shares(download(report_url))


def _to_yahoo(tidm: str) -> str:
    """RR. -> RR.L and BT.A -> BT-A.L, the way Yahoo writes London tickers."""
    return tidm.strip().rstrip(".").replace(".", "-") + ".L"
