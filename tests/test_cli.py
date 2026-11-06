from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from chart_screenshots import cli
from chart_screenshots.data import NoDataError


@pytest.mark.parametrize("raw, expected", [
    ("aapl", "AAPL"),
    ("  msft ", "MSFT"),
    ("brk-b", "BRK-B"),
    ("^gspc", "^GSPC"),
    ("btc-usd", "BTC-USD"),
    ("thyao.is", "THYAO.IS"),
])
def test_parse_symbol_accepts_and_normalizes_valid_tickers(raw, expected):
    assert cli.parse_symbol(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "AA PL", "AAPL;rm", "A" * 21])
def test_parse_symbol_rejects_invalid_tickers(raw):
    with pytest.raises(ValueError):
        cli.parse_symbol(raw)


def test_parse_start_year_accepts_year_in_range():
    assert cli.parse_start_year(" 2018 ", current_year=2026) == 2018
    assert cli.parse_start_year("2026", current_year=2026) == 2026


@pytest.mark.parametrize("raw", ["", "abc", "20.5", "2027", "1899"])
def test_parse_start_year_rejects_invalid_years(raw):
    with pytest.raises(ValueError):
        cli.parse_start_year(raw, current_year=2026)


def test_prompt_until_valid_retries_after_bad_input():
    # Arrange
    answers = iter(["", "aapl"])
    messages = []

    # Act
    result = cli.prompt_until_valid(
        "Symbol: ",
        cli.parse_symbol,
        read=lambda prompt: next(answers),
        write=messages.append,
    )

    # Assert
    assert result == "AAPL"
    assert len(messages) == 1


def weekly_frame(dates):
    return pd.DataFrame(
        {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 10},
        index=pd.DatetimeIndex(dates),
    )


def test_run_saves_one_chart_per_year(tmp_path):
    # Arrange
    daily = weekly_frame(["2024-06-03", "2025-06-02"])
    rendered = []

    def fake_render(weekly, symbol, year, out_dir):
        path = Path(out_dir) / f"{symbol}_{year}.png"
        rendered.append((symbol, year, len(weekly)))
        return path

    # Act
    exit_code = cli.run(
        "AAPL", 2024, tmp_path,
        fetch=lambda symbol, year: daily,
        render=fake_render,
        write=lambda message: None,
    )

    # Assert
    assert exit_code == 0
    assert rendered == [("AAPL", 2024, 1), ("AAPL", 2025, 1)]


def test_run_reports_fetch_errors_and_returns_failure(tmp_path):
    # Arrange
    messages = []

    def failing_fetch(symbol, year):
        raise NoDataError("No data found for NOPE.")

    # Act
    exit_code = cli.run(
        "NOPE", 2024, tmp_path,
        fetch=failing_fetch,
        render=lambda *args: None,
        write=messages.append,
    )

    # Assert
    assert exit_code == 1
    assert "No data found for NOPE." in messages[-1]


def test_build_run_dir_names_folder_after_symbol_start_year_and_request_time(tmp_path):
    # Arrange
    requested_at = datetime(2026, 11, 6, 16, 53, 7)

    # Act
    run_dir = cli.build_run_dir(tmp_path, "AAPL", 2019, requested_at)

    # Assert
    assert run_dir == tmp_path / "AAPL_from_2019_2026-11-06_16-53-07"


def test_main_saves_charts_into_a_folder_for_this_request(monkeypatch, tmp_path):
    # Arrange
    answers = iter(["aapl", "2020"])
    calls = []
    monkeypatch.setattr(cli, "run", lambda *args: calls.append(args) or 0)
    requested_at = datetime(2026, 11, 6, 9, 5, 0)

    # Act
    exit_code = cli.main(
        tmp_path,
        read=lambda prompt: next(answers),
        now=lambda: requested_at,
    )

    # Assert
    assert exit_code == 0
    assert calls == [("AAPL", 2020, tmp_path / "AAPL_from_2020_2026-11-06_09-05-00")]


def test_main_exits_cleanly_on_ctrl_c(tmp_path):
    # Arrange
    def interrupted(prompt):
        raise KeyboardInterrupt

    # Act
    exit_code = cli.main(tmp_path, read=interrupted)

    # Assert
    assert exit_code == cli.EXIT_CANCELLED


def test_run_tells_user_when_data_starts_after_requested_year(tmp_path):
    # Arrange
    messages = []
    daily = weekly_frame(["2025-06-02"])

    # Act
    cli.run(
        "NEW", 2020, tmp_path,
        fetch=lambda symbol, year: daily,
        render=lambda weekly, symbol, year, out_dir: Path(out_dir) / "x.png",
        write=messages.append,
    )

    # Assert
    assert any("starts in 2025" in message for message in messages)
