import pandas as pd
import pytest

from chart_screenshots.data import (
    DataFetchError,
    NoDataError,
    fetch_daily,
    split_by_year,
    to_weekly,
)


def make_daily(rows):
    """Build a daily OHLCV frame from (date, open, high, low, close, volume) tuples."""
    index = pd.DatetimeIndex([row[0] for row in rows], name="Date")
    return pd.DataFrame(
        [row[1:] for row in rows],
        index=index,
        columns=["Open", "High", "Low", "Close", "Volume"],
    )


def test_to_weekly_aggregates_monday_to_friday_into_one_bar():
    # Arrange
    daily = make_daily([
        ("2024-01-08", 10, 12, 9, 11, 100),
        ("2024-01-09", 11, 15, 10, 14, 200),
        ("2024-01-10", 14, 14, 8, 9, 300),
        ("2024-01-11", 9, 10, 7, 8, 400),
        ("2024-01-12", 8, 13, 8, 12, 500),
    ])

    # Act
    weekly = to_weekly(daily)

    # Assert
    assert list(weekly.index) == [pd.Timestamp("2024-01-08")]
    bar = weekly.iloc[0]
    assert (bar.Open, bar.High, bar.Low, bar.Close, bar.Volume) == (10, 15, 7, 12, 1500)


def test_to_weekly_labels_holiday_week_by_its_monday_and_opens_on_first_trading_day():
    # Arrange: Monday 2026-01-19 is Martin Luther King Jr. Day, market closed
    daily = make_daily([
        ("2026-01-20", 20, 21, 19, 20, 10),
        ("2026-01-23", 22, 25, 22, 24, 30),
    ])

    # Act
    weekly = to_weekly(daily)

    # Assert
    assert list(weekly.index) == [pd.Timestamp("2026-01-19")]
    assert weekly.iloc[0].Open == 20
    assert weekly.iloc[0].Close == 24


def test_to_weekly_does_not_mutate_input():
    # Arrange
    daily = make_daily([("2024-01-08", 10, 12, 9, 11, 100)])
    snapshot = daily.copy()

    # Act
    to_weekly(daily)

    # Assert
    pd.testing.assert_frame_equal(daily, snapshot)


def test_split_by_year_assigns_week_crossing_new_year_to_the_year_of_its_monday():
    # Arrange: week of Monday 2025-12-29 also contains 2026-01-02
    daily = make_daily([
        ("2025-12-22", 1, 2, 1, 2, 1),
        ("2025-12-29", 2, 3, 2, 3, 1),
        ("2026-01-02", 3, 4, 3, 4, 1),
        ("2026-01-05", 4, 5, 4, 5, 1),
    ])
    weekly = to_weekly(daily)

    # Act
    years = split_by_year(weekly, start_year=2025)

    # Assert
    assert list(years) == [2025, 2026]
    assert list(years[2025].index) == [pd.Timestamp("2025-12-22"), pd.Timestamp("2025-12-29")]
    assert years[2025].iloc[-1].Close == 4
    assert list(years[2026].index) == [pd.Timestamp("2026-01-05")]


def test_split_by_year_skips_years_before_start_year():
    # Arrange
    weekly = to_weekly(make_daily([
        ("2023-06-05", 1, 1, 1, 1, 1),
        ("2024-06-03", 1, 1, 1, 1, 1),
    ]))

    # Act
    years = split_by_year(weekly, start_year=2024)

    # Assert
    assert list(years) == [2024]


class FakeTicker:
    def __init__(self, frame=None, error=None):
        self._frame = frame
        self._error = error
        self.calls = []

    def history(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._frame


def test_fetch_daily_requests_split_adjusted_daily_data_and_drops_timezone():
    # Arrange
    index = pd.DatetimeIndex(["2024-01-08"], tz="America/New_York")
    frame = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5],
         "Adj Close": [1.4], "Volume": [10], "Dividends": [0.0], "Stock Splits": [0.0]},
        index=index,
    )
    ticker = FakeTicker(frame=frame)

    # Act
    daily = fetch_daily("AAPL", 2024, ticker_factory=lambda symbol: ticker)

    # Assert
    assert ticker.calls[0]["start"] == "2024-01-01"
    assert ticker.calls[0]["interval"] == "1d"
    assert ticker.calls[0]["auto_adjust"] is False
    assert list(daily.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert daily.index.tz is None


def test_fetch_daily_raises_no_data_error_for_unknown_symbol():
    # Arrange
    ticker = FakeTicker(frame=pd.DataFrame())

    # Act / Assert
    with pytest.raises(NoDataError, match="NOPE"):
        fetch_daily("NOPE", 2024, ticker_factory=lambda symbol: ticker)


def test_fetch_daily_wraps_network_errors():
    # Arrange
    ticker = FakeTicker(error=ConnectionError("offline"))

    # Act / Assert
    with pytest.raises(DataFetchError, match="offline"):
        fetch_daily("AAPL", 2024, ticker_factory=lambda symbol: ticker)
