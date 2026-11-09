"""Download daily candles for Binance USDT perpetual futures.

Returns the same daily OHLCV frame as `data.fetch_daily`, so the weekly candles
and charts are built the same way as for stocks. Daily candles open at 00:00 UTC.
"""
import pandas as pd
import requests

from chart_screenshots.data import OHLCV_COLUMNS, DataFetchError, NoDataError

KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
DAILY_INTERVAL = "1d"
MAX_CANDLES_PER_REQUEST = 1500
MS_PER_DAY = 86_400_000
TIMEOUT_SECONDS = 30
INVALID_SYMBOL_CODE = -1121
ERROR_TEXT_LIMIT = 200


def fetch_binance_daily(
    symbol: str,
    start_year: int,
    get=requests.get,
    page_size: int = MAX_CANDLES_PER_REQUEST,
) -> pd.DataFrame:
    """Return daily OHLCV rows for `symbol` from 1 January of `start_year` until today."""
    start_ms = int(pd.Timestamp(f"{start_year}-01-01", tz="UTC").timestamp() * 1000)
    rows = []
    while True:
        page = _get_page(symbol, start_ms, get, page_size)
        rows = [*rows, *page]
        if len(page) < page_size:
            break
        start_ms = page[-1][0] + MS_PER_DAY

    if not rows:
        raise NoDataError(f"No data found for {symbol} on Binance futures since {start_year}.")
    return _to_frame(rows)


def _get_page(symbol: str, start_ms: int, get, page_size: int) -> list[list]:
    params = {
        "symbol": symbol,
        "interval": DAILY_INTERVAL,
        "startTime": start_ms,
        "limit": page_size,
    }
    try:
        response = get(KLINES_URL, params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as error:
        raise DataFetchError(f"Could not download data for {symbol}: {error}") from error

    if response.status_code == 400 and _error_code(response) == INVALID_SYMBOL_CODE:
        raise NoDataError(f"No data found for {symbol}: not a Binance futures symbol.")
    if not response.ok:
        raise DataFetchError(
            f"Binance returned HTTP {response.status_code} for {symbol}: "
            f"{response.text[:ERROR_TEXT_LIMIT]}"
        )
    return response.json()


def _error_code(response) -> int | None:
    try:
        return response.json().get("code")
    except (ValueError, AttributeError):
        return None


def _to_frame(rows: list[list]) -> pd.DataFrame:
    """Klines are [open time ms, open, high, low, close, volume, ...] with prices as text."""
    opened_at = pd.to_datetime([row[0] for row in rows], unit="ms")
    values = [[float(value) for value in row[1:6]] for row in rows]
    return pd.DataFrame(values, index=opened_at, columns=OHLCV_COLUMNS).rename_axis("Date")
