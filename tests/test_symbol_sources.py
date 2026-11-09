import io
import json

import pandas as pd
import pytest
import requests

from chart_screenshots.symbol_sources import binance, bist, euronext, fwb, krx, lse, tse, us
from chart_screenshots.symbol_sources.http import SymbolSourceError, download


def to_xlsx(sheets):
    """Build an .xlsx file in memory from {sheet name: list of rows}."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, header=False, index=False)
    return buffer.getvalue()


def fake_download(responses):
    """Return a download function that serves canned bytes by URL."""
    return lambda url, **kwargs: responses[url]


NASDAQ_LISTED = b"""Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N
BRGT|Bright Things Inc. - Class A Common Stock|Q|N|N|100|N|N
QQQ|Invesco QQQ Trust, Series 1|G|N|N|100|Y|N
ABCDW|ABC Corp - Warrant|S|N|N|100|N|N
AACG|ATA Creativity Global - American Depositary Shares|S|N|N|100|N|N
ZXZZT|NASDAQ TEST STOCK|Q|Y|N|100|N|N
File Creation Time: 1106202617:00|||||||
"""

OTHER_LISTED = b"""ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
IBM|International Business Machines Corporation Common Stock|N|IBM|N|100|N|IBM
BRK.B|Berkshire Hathaway Inc. Class B Common Stock|N|BRK.B|N|100|N|BRK=B
SPY|SPDR S&P 500 ETF Trust|P|SPY|Y|100|N|SPY
XYZ|XYZ Corp Common Stock|A|XYZ|N|100|N|XYZ
BAC$K|Bank of America Corporation Preferred Stock|N|BACpK|N|100|N|BAC-K
File Creation Time: 1106202617:00|||||||
"""


def test_parse_nasdaq_keeps_only_common_stocks():
    assert us.parse_nasdaq_listed(NASDAQ_LISTED) == ["AAPL", "BRGT"]


def test_parse_nyse_keeps_only_nyse_common_stocks_in_yahoo_format():
    assert us.parse_nyse_listed(OTHER_LISTED) == ["IBM", "BRK-B"]


def test_fetch_nasdaq_and_nyse_download_from_nasdaq_trader():
    # Arrange
    get = fake_download({us.NASDAQ_LISTED_URL: NASDAQ_LISTED, us.OTHER_LISTED_URL: OTHER_LISTED})

    # Act / Assert
    assert us.fetch_nasdaq(download=get) == ["AAPL", "BRGT"]
    assert us.fetch_nyse(download=get) == ["IBM", "BRK-B"]


LSE_SHARES = to_xlsx({
    "1.1 Shares": [
        ["Equity Instruments - Shares", None, None],
        [None, None, None],
        ["TIDM", "Issuer Name", "FCA Listing Category"],
        ["III", "3I GROUP PLC", None],
        ["RR.", "ROLLS-ROYCE HOLDINGS PLC", "Equity shares (commercial companies)"],
        ["BT.A", "BT GROUP PLC", "Equity shares (commercial companies)"],
        ["3IN", "3I INFRASTRUCTURE PLC", "Closed-ended investment funds"],
    ],
})


def test_parse_lse_shares_converts_tidm_and_skips_investment_funds():
    assert lse.parse_lse_shares(LSE_SHARES) == ["III.L", "RR.L", "BT-A.L"]


def test_fetch_lse_follows_latest_report_link():
    # Arrange
    report_url = "https://docs.example/Instrument%20list.xlsx"
    latest = json.dumps({"Data": [{"downloadLink": report_url}]}).encode()
    get = fake_download({lse.LATEST_REPORT_URL: latest, report_url: LSE_SHARES})

    # Act / Assert
    assert lse.fetch_lse(download=get) == ["III.L", "RR.L", "BT-A.L"]


def test_fetch_lse_reports_unexpected_latest_report_format():
    get = fake_download({lse.LATEST_REPORT_URL: b'{"Data": []}'})

    with pytest.raises(SymbolSourceError):
        lse.fetch_lse(download=get)


def test_parse_tse_keeps_only_domestic_stocks():
    # Arrange
    content = to_xlsx({
        "Sheet1": [
            ["日付", "コード", "銘柄名", "市場・商品区分"],
            [20261031, "7203", "トヨタ自動車", "プライム（内国株式）"],
            [20261031, "130A", "Veritas In Silico", "グロース（内国株式）"],
            [20261031, "1306", "ＮＥＸＴ ＦＵＮＤＳ ＴＯＰＩＸ連動型上場投信", "ETF・ETN"],
            [20261031, "9999", "Foreign Co", "スタンダード（外国株式）"],
        ],
    })

    # Act / Assert
    assert tse.parse_tse(content) == ["7203.T", "130A.T"]


def test_fetch_fwb_finds_link_and_reads_every_company_sheet():
    # Arrange
    page = b'<a href="/resource/blob/1/abc/data/Listed-companies.xlsx">Download</a>'
    header = ["ISIN", "Trading Symbol", "Company"]
    content = to_xlsx({
        "Cover": [["Issuer Services"]],
        "Prime Standard": [["Companies in Prime Standard"], [None], header, ["DE0007164600", "SAP", "SAP SE"]],
        "Scale": [["Companies in Scale"], header, ["DE000A0Z2ZZ5", "FNTN", "FREENET AG"]],
    })
    xlsx_url = fwb.BASE_URL + "/resource/blob/1/abc/data/Listed-companies.xlsx"
    get = fake_download({fwb.LISTED_COMPANIES_PAGE: page, xlsx_url: content})

    # Act / Assert
    assert fwb.fetch_fwb(download=get) == ["SAP.F", "FNTN.F"]


def test_fetch_fwb_reports_missing_download_link():
    get = fake_download({fwb.LISTED_COMPANIES_PAGE: b"<html>no link</html>"})

    with pytest.raises(SymbolSourceError):
        fwb.fetch_fwb(download=get)


EURONEXT_CSV = """﻿Name;ISIN;Symbol;Market;Currency
"European Equities"
"06 Nov 2026"
"All datapoints provided as of end of last active trading day."
74SOFTWARE;FR0011040500;74SW;"Euronext Paris";EUR
"AB SCIENCE";FR0010557264;AB;"Euronext Paris";EUR
"AB SCIENCE BSA";FR001400ZRT0;ABBS;"Euronext Paris";EUR
"AB SCIENCE BSAAU25";FR001400ZRT1;ABBSA;"Euronext Paris";EUR
"ALTAMIR";FR0000053837;LTA;"Euronext Growth Paris";EUR
""".encode("utf-8")


def test_parse_euronext_skips_warrants():
    assert euronext.parse_euronext(EURONEXT_CSV) == ["74SW.PA", "AB.PA", "LTA.PA"]


def test_fetch_euronext_posts_the_download_form():
    # Arrange
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return EURONEXT_CSV

    # Act
    symbols = euronext.fetch_euronext(download=get)

    # Assert
    assert symbols == ["74SW.PA", "AB.PA", "LTA.PA"]
    assert calls == [(euronext.DOWNLOAD_URL, {"data": euronext.FORM_DATA})]


def krx_table(rows):
    body = "".join(f"<tr><td>{name}</td><td>{code}</td></tr>" for name, code in rows)
    html = f"<table><tr><th>회사명</th><th>종목코드</th></tr>{body}</table>"
    return html.encode("euc-kr")


def test_parse_krx_keeps_leading_zeros_and_skips_spacs():
    # Arrange
    content = krx_table([("삼성전자", "005930"), ("아이엠스팩1호", "0222E0"), ("한화", "0220W0")])

    # Act / Assert
    assert krx.parse_krx(content, ".KS") == ["005930.KS", "0220W0.KS"]


def test_fetch_krx_combines_kospi_and_kosdaq():
    # Arrange
    get = fake_download({
        krx.CORP_LIST_URL.format(market="stockMkt"): krx_table([("삼성전자", "005930")]),
        krx.CORP_LIST_URL.format(market="kosdaqMkt"): krx_table([("에코프로", "086520")]),
    })

    # Act / Assert
    assert krx.fetch_krx(download=get) == ["005930.KS", "086520.KQ"]


BIST_CSV = """BILESEN KODU;BULTEN_ADI;ENDEKS KODU;ENDEKS ADI;ENDEKS INGILIZCE ADI;TARIH(GG/AA/YYYY)
CONSTITUENT CODE;CONSTITUENT NAME;INDEX CODE;INDEX NAME IN TURKISH;INDEX NAME IN ENGLISH;DATE(DD/MM/YYYY)
AEFES.E;ANADOLU EFES;XU100;BIST 100;BIST 100;09/11/2026
A1CAP.E;A1 CAPITAL YATIRIM;XUTUM;BIST TUM;BIST ALL SHARES;09/11/2026
THYAO.E;TURK HAVA YOLLARI;XUTUM;BIST TUM;BIST ALL SHARES;09/11/2026
""".encode("latin-1")


def test_fetch_bist_uses_all_shares_index_members():
    get = fake_download({bist.INDEX_CONSTITUENTS_URL: BIST_CSV})

    assert bist.fetch_bist(download=get) == ["A1CAP.IS", "THYAO.IS"]


def test_fetch_binance_keeps_trading_usdt_perpetuals_with_plain_names():
    # Arrange
    info = {"symbols": [
        {"symbol": "BTCUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING"},
        {"symbol": "BTCUSDT_261225", "contractType": "CURRENT_QUARTER", "quoteAsset": "USDT", "status": "TRADING"},
        {"symbol": "ETHUSDC", "contractType": "PERPETUAL", "quoteAsset": "USDC", "status": "TRADING"},
        {"symbol": "OLDUSDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "SETTLING"},
        {"symbol": "币安人生USDT", "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING"},
    ]}
    get = fake_download({binance.EXCHANGE_INFO_URL: json.dumps(info).encode()})

    # Act / Assert
    assert binance.fetch_binance(download=get) == ["BTCUSDT"]


def test_download_wraps_network_errors(monkeypatch):
    # Arrange
    def failing_request(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "request", failing_request)

    # Act / Assert
    with pytest.raises(SymbolSourceError, match="offline"):
        download("https://example.com/list.csv")
