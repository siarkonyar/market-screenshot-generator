"""Frankfurt Stock Exchange companies from Deutsche Börse's listed companies file."""
import re
from typing import Callable
from urllib.parse import urljoin

from chart_screenshots.symbol_sources.http import (
    SymbolSourceError,
    download,
    read_excel,
    table_below_header,
)

BASE_URL = "https://www.cashmarket.deutsche-boerse.com"
LISTED_COMPANIES_PAGE = BASE_URL + "/cash-en/Data-Tech/statistics/listed-companies"
LINK_PATTERN = re.compile(rb'href="([^"]*Listed-companies\.xlsx)"')
COMPANY_SHEETS = ("Prime Standard", "General Standard", "Scale", "Basic Board")
YAHOO_SUFFIX = ".F"  # Yahoo's Frankfurt quotes


def find_listed_companies_link(page: bytes) -> str:
    """The file's URL changes with every update, so read it from the statistics page."""
    match = LINK_PATTERN.search(page)
    if match is None:
        raise SymbolSourceError(f"No Listed-companies.xlsx link found on {LISTED_COMPANIES_PAGE}.")
    return urljoin(BASE_URL, match.group(1).decode())


def parse_fwb(content: bytes) -> list[str]:
    """Trading symbols from every company segment sheet in the file."""
    sheets = read_excel(content, sheet_name=None, header=None)
    return [
        f"{symbol.strip()}{YAHOO_SUFFIX}"
        for name in COMPANY_SHEETS
        if name in sheets
        for symbol in table_below_header(sheets[name], "ISIN")["Trading Symbol"].dropna()
    ]


def fetch_fwb(download: Callable[..., bytes] = download) -> list[str]:
    xlsx_url = find_listed_companies_link(download(LISTED_COMPANIES_PAGE))
    return parse_fwb(download(xlsx_url))
