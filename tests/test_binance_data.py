import pandas as pd
import pytest
import requests

from chart_screenshots.binance_data import fetch_binance_daily
from chart_screenshots.data import DataFetchError, NoDataError

DAY_MS = 86_400_000
JAN_1_2024_MS = 1_704_067_200_000


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.ok = status_code < 400
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def kline(day):
    open_time = JAN_1_2024_MS + day * DAY_MS
    return [open_time, "10.0", "12.0", "9.0", "11.0", "100.5", open_time + DAY_MS - 1]


def test_fetch_binance_daily_pages_through_klines_until_a_short_page():
    # Arrange
    pages = [[kline(0), kline(1)], [kline(2)]]
    calls = []

    def get(url, params, timeout):
        calls.append(params)
        return FakeResponse(200, pages[len(calls) - 1])

    # Act
    daily = fetch_binance_daily("BTCUSDT", 2024, get=get, page_size=2)

    # Assert
    assert calls[0]["symbol"] == "BTCUSDT"
    assert calls[0]["interval"] == "1d"
    assert calls[0]["startTime"] == JAN_1_2024_MS
    assert calls[1]["startTime"] == JAN_1_2024_MS + 2 * DAY_MS
    assert list(daily.index) == list(pd.date_range("2024-01-01", periods=3, freq="D"))
    assert list(daily.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert daily.iloc[0].tolist() == [10.0, 12.0, 9.0, 11.0, 100.5]


def test_fetch_binance_daily_raises_no_data_error_for_unknown_symbol():
    def get(url, params, timeout):
        return FakeResponse(400, {"code": -1121, "msg": "Invalid symbol."})

    with pytest.raises(NoDataError, match="NOPEUSDT"):
        fetch_binance_daily("NOPEUSDT", 2024, get=get)


def test_fetch_binance_daily_raises_no_data_error_when_no_candles_since_start_year():
    def get(url, params, timeout):
        return FakeResponse(200, [])

    with pytest.raises(NoDataError):
        fetch_binance_daily("NEWUSDT", 2024, get=get)


def test_fetch_binance_daily_wraps_http_errors():
    def get(url, params, timeout):
        return FakeResponse(429, {"code": -1003, "msg": "Too many requests."})

    with pytest.raises(DataFetchError, match="429"):
        fetch_binance_daily("BTCUSDT", 2024, get=get)


def test_fetch_binance_daily_wraps_network_errors():
    def get(url, params, timeout):
        raise requests.ConnectionError("offline")

    with pytest.raises(DataFetchError, match="offline"):
        fetch_binance_daily("BTCUSDT", 2024, get=get)
