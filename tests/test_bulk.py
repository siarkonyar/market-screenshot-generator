from pathlib import Path

import pandas as pd

from chart_screenshots.bulk import FAILURES_FILE, run_all_markets
from chart_screenshots.data import DataFetchError, NoDataError
from chart_screenshots.markets import Market


def daily_frame(dates):
    return pd.DataFrame(
        {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 10.0},
        index=pd.DatetimeIndex(dates),
    )


def no_symbols():
    return []


class Recorder:
    """Collects render calls, sleeps and messages from a bulk run."""

    def __init__(self):
        self.rendered = []
        self.sleeps = []
        self.messages = []

    def render(self, weekly, symbol, year, out_dir):
        self.rendered.append((symbol, year, Path(out_dir)))
        return Path(out_dir) / f"{symbol}_{year}.png"

    def kwargs(self):
        return {"render": self.render, "sleep": self.sleeps.append, "write": self.messages.append}


def write_symbol_file(symbols_dir, code, symbols):
    symbols_dir.mkdir(parents=True, exist_ok=True)
    (symbols_dir / f"{code}.txt").write_text("\n".join(symbols) + "\n")


def test_run_all_markets_starts_each_symbol_at_its_first_year_with_data(tmp_path):
    # Arrange
    symbols_dir = tmp_path / "symbols"
    write_symbol_file(symbols_dir, "NYS", ["OLD", "NEW"])
    history = {
        "OLD": daily_frame(["2012-06-04", "2013-06-03"]),
        "NEW": daily_frame(["2015-06-01"]),
    }
    market = Market("NYS", "New York", no_symbols, lambda symbol, year: history[symbol])
    recorder = Recorder()
    out_dir = tmp_path / "run"

    # Act
    exit_code = run_all_markets(2012, out_dir, markets=(market,), symbols_dir=symbols_dir, **recorder.kwargs())

    # Assert
    assert exit_code == 0
    assert recorder.rendered == [
        ("OLD", 2012, out_dir / "NYS" / "OLD"),
        ("OLD", 2013, out_dir / "NYS" / "OLD"),
        ("NEW", 2015, out_dir / "NYS" / "NEW"),
    ]


def test_run_all_markets_uses_each_markets_own_data_source(tmp_path):
    # Arrange
    symbols_dir = tmp_path / "symbols"
    write_symbol_file(symbols_dir, "BIST", ["THYAO.IS"])
    write_symbol_file(symbols_dir, "BINANCE", ["BTCUSDT"])
    seen = []

    def yahoo(symbol, year):
        seen.append(("yahoo", symbol))
        return daily_frame(["2020-06-01"])

    def binance(symbol, year):
        seen.append(("binance", symbol))
        return daily_frame(["2020-06-01"])

    markets = (Market("BIST", "Istanbul", no_symbols, yahoo), Market("BINANCE", "Binance", no_symbols, binance))

    # Act
    run_all_markets(2020, tmp_path / "run", markets=markets, symbols_dir=symbols_dir, **Recorder().kwargs())

    # Assert
    assert seen == [("yahoo", "THYAO.IS"), ("binance", "BTCUSDT")]


def test_run_all_markets_skips_symbols_without_data_and_lists_them(tmp_path):
    # Arrange
    symbols_dir = tmp_path / "symbols"
    write_symbol_file(symbols_dir, "LSE", ["GONE.L", "VOD.L"])

    def fetch(symbol, year):
        if symbol == "GONE.L":
            raise NoDataError("No data found for GONE.L since 2020.")
        return daily_frame(["2020-06-01"])

    market = Market("LSE", "London", no_symbols, fetch)
    recorder = Recorder()
    out_dir = tmp_path / "run"

    # Act
    exit_code = run_all_markets(2020, out_dir, markets=(market,), symbols_dir=symbols_dir, **recorder.kwargs())

    # Assert
    assert exit_code == 0
    assert [symbol for symbol, _, _ in recorder.rendered] == ["VOD.L"]
    assert (out_dir / FAILURES_FILE).read_text() == "LSE\tGONE.L\tNo data found for GONE.L since 2020.\n"


def test_run_all_markets_retries_temporary_errors_with_waits(tmp_path):
    # Arrange
    symbols_dir = tmp_path / "symbols"
    write_symbol_file(symbols_dir, "TSE", ["7203.T"])
    attempts = []

    def flaky(symbol, year):
        attempts.append(symbol)
        if len(attempts) < 3:
            raise DataFetchError("Too many requests")
        return daily_frame(["2020-06-01"])

    market = Market("TSE", "Tokyo", no_symbols, flaky)
    recorder = Recorder()

    # Act
    run_all_markets(2020, tmp_path / "run", markets=(market,), symbols_dir=symbols_dir, **recorder.kwargs())

    # Assert
    assert len(attempts) == 3
    assert recorder.rendered == [("7203.T", 2020, tmp_path / "run" / "TSE" / "7203.T")]
    assert recorder.sleeps[:2] == [30, 120]


def test_run_all_markets_gives_up_after_the_last_retry(tmp_path):
    # Arrange
    symbols_dir = tmp_path / "symbols"
    write_symbol_file(symbols_dir, "KRX", ["005930.KS"])

    def always_failing(symbol, year):
        raise DataFetchError("Too many requests")

    market = Market("KRX", "Korea", no_symbols, always_failing)
    out_dir = tmp_path / "run"

    # Act
    run_all_markets(2020, out_dir, markets=(market,), symbols_dir=symbols_dir, **Recorder().kwargs())

    # Assert
    assert "KRX\t005930.KS\tToo many requests" in (out_dir / FAILURES_FILE).read_text()


def test_run_all_markets_skips_market_without_symbol_file(tmp_path):
    # Arrange
    market = Market("FWB", "Frankfurt", no_symbols, lambda symbol, year: daily_frame(["2020-06-01"]))
    recorder = Recorder()

    # Act
    exit_code = run_all_markets(2020, tmp_path / "run", markets=(market,), symbols_dir=tmp_path, **recorder.kwargs())

    # Assert
    assert exit_code == 1
    assert recorder.rendered == []
    assert any("update_symbols.py" in message for message in recorder.messages)
