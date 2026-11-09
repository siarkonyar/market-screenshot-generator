"""Korea Exchange (KOSPI and KOSDAQ) companies from KRX KIND's corporate list."""
import io
from typing import Callable

import pandas as pd

from chart_screenshots.symbol_sources.http import download

CORP_LIST_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&marketType={market}"
BOARDS = (("stockMkt", ".KS"), ("kosdaqMkt", ".KQ"))  # KRX market type, Yahoo suffix
NAME_COLUMN = "회사명"  # company name
CODE_COLUMN = "종목코드"  # stock code
SPAC_MARKER = "스팩"  # "SPAC": blank-cheque shells, not operating companies
CODE_LENGTH = 6


def parse_krx(content: bytes, suffix: str) -> list[str]:
    """The download is an EUC-KR HTML table. Codes stay text to keep leading zeros."""
    html = content.decode("euc-kr", errors="replace")
    frame = pd.read_html(io.StringIO(html), converters={CODE_COLUMN: str})[0]
    is_spac = frame[NAME_COLUMN].astype(str).str.contains(SPAC_MARKER, regex=False)
    codes = frame.loc[~is_spac, CODE_COLUMN].astype(str).str.strip().str.zfill(CODE_LENGTH)
    return [f"{code}{suffix}" for code in codes]


def fetch_krx(download: Callable[..., bytes] = download) -> list[str]:
    return [
        symbol
        for market, suffix in BOARDS
        for symbol in parse_krx(download(CORP_LIST_URL.format(market=market)), suffix)
    ]
