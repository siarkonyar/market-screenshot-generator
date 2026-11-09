"""Euronext Paris and Euronext Growth Paris stocks from Euronext's download."""
import io
import re
from typing import Callable

import pandas as pd

from chart_screenshots.symbol_sources.http import download

DOWNLOAD_URL = "https://live.euronext.com/en/pd_es/data/stocks/download?mics=XPAR%2CALXP"
FORM_DATA = {
    "args[initialLetter]": "",
    "iDisplayLength": "20000",
    "iDisplayStart": "0",
    "display_datapoints": "dp_stocks",
    "display_filters": "df_stocks",
}
NOTE_ROWS = [1, 2, 3]  # three lines of notes sit between the header and the data
# Warrants (BSA / BSAR / BSAAR) and rights (DS) are listed as "COMPANY BSA..."
WARRANT_NAME = re.compile(r"\s(?:BSA|BSAR|BSAAR|DS)[A-Z0-9]*$")


def parse_euronext(content: bytes) -> list[str]:
    frame = pd.read_csv(
        io.BytesIO(content), sep=";", skiprows=NOTE_ROWS, dtype=str, encoding="utf-8-sig"
    )
    is_warrant = frame["Name"].fillna("").str.strip().str.contains(WARRANT_NAME)
    return [f"{symbol.strip()}.PA" for symbol in frame.loc[~is_warrant, "Symbol"].dropna()]


def fetch_euronext(download: Callable[..., bytes] = download) -> list[str]:
    return parse_euronext(download(DOWNLOAD_URL, data=FORM_DATA))
