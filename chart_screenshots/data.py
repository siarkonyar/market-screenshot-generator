"""Download daily prices and build TradingView-style weekly candles.

Weekly bars are built from daily data instead of using Yahoo's own weekly
interval, so that every bar runs Monday to Friday and is labelled with its
Monday date, the same way TradingView draws weekly candles. Prices are
split-adjusted but not dividend-adjusted, which matches TradingView's default.
"""
import logging
from typing import Callable

import pandas as pd
import yfinance as yf

# yfinance logs raw HTTP errors for unknown symbols; NoDataError explains them instead.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
PRICE_COLUMNS = ["Open", "High", "Low", "Close"]
WEEKLY_AGGREGATION = {
    "Open": "first",
    "High": "max",
    "Low": "min",
    "Close": "last",
    "Volume": "sum",
}


class DataFetchError(Exception):
    """Raised when price data cannot be downloaded."""


class NoDataError(DataFetchError):
    """Raised when the data source returns no rows for a symbol."""


def fetch_daily(
    symbol: str,
    start_year: int,
    ticker_factory: Callable[[str], yf.Ticker] = yf.Ticker,
) -> pd.DataFrame:
    """Return daily OHLCV rows for `symbol` from 1 January of `start_year` until today."""
    try:
        raw = ticker_factory(symbol).history(
            start=f"{start_year}-01-01",
            interval="1d",
            auto_adjust=False,
            actions=False,
        )
    except Exception as error:  # yfinance raises many unrelated error types
        raise DataFetchError(f"Could not download data for {symbol}: {error}") from error

    if raw is None or raw.empty:
        raise NoDataError(
            f"No data found for {symbol} since {start_year}. "
            "Check the symbol (Yahoo Finance format, e.g. AAPL, BTC-USD, THYAO.IS)."
        )

    daily = raw[OHLCV_COLUMNS].dropna(subset=PRICE_COLUMNS)
    if daily.index.tz is None:
        return daily
    return daily.set_axis(daily.index.tz_localize(None), axis=0)


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Group daily rows into Monday-labelled weekly candles."""
    week_start = daily.index.normalize() - pd.to_timedelta(daily.index.day_of_week, unit="D")
    return daily.groupby(week_start).agg(WEEKLY_AGGREGATION).rename_axis("Date")


def split_by_year(weekly: pd.DataFrame, start_year: int) -> dict[int, pd.DataFrame]:
    """Split weekly candles by the year of each candle's Monday, from `start_year` on."""
    years = weekly.index.year
    return {
        int(year): weekly[years == year]
        for year in sorted(set(years))
        if year >= start_year
    }
