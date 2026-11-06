"""Interactive command line: ask for a symbol and a start year, then save the charts."""
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, TypeVar

import pandas as pd

from chart_screenshots.charts import render_year_chart
from chart_screenshots.data import DataFetchError, fetch_daily, split_by_year, to_weekly

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.^=\-]{1,20}$")
MIN_START_YEAR = 1900
RUN_DIR_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_CANCELLED = 130

T = TypeVar("T")
Fetch = Callable[[str, int], pd.DataFrame]
Render = Callable[[pd.DataFrame, str, int, Path], Path]


def parse_symbol(raw: str) -> str:
    """Normalize a ticker symbol to upper case and reject anything that is not a ticker."""
    symbol = raw.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise ValueError(
            "Symbol must be 1-20 characters using letters, digits, '.', '-', '^' or '='."
        )
    return symbol


def parse_start_year(raw: str, current_year: int) -> int:
    """Parse a four-digit start year between MIN_START_YEAR and `current_year`."""
    text = raw.strip()
    if not text.isdigit():
        raise ValueError("Start year must be a whole number, for example 2018.")
    year = int(text)
    if not MIN_START_YEAR <= year <= current_year:
        raise ValueError(f"Start year must be between {MIN_START_YEAR} and {current_year}.")
    return year


def build_run_dir(base_dir: Path, symbol: str, start_year: int, requested_at: datetime) -> Path:
    """Return the folder for one request, e.g. `AAPL_from_2019_2026-11-06_16-53-07`."""
    timestamp = requested_at.strftime(RUN_DIR_TIMESTAMP_FORMAT)
    return Path(base_dir) / f"{symbol}_from_{start_year}_{timestamp}"


def prompt_until_valid(
    prompt: str,
    parse: Callable[[str], T],
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> T:
    """Keep asking until `parse` accepts the answer."""
    while True:
        try:
            return parse(read(prompt))
        except ValueError as error:
            write(f"  {error}")


def run(
    symbol: str,
    start_year: int,
    out_dir: Path,
    fetch: Fetch = fetch_daily,
    render: Render = render_year_chart,
    write: Callable[[str], None] = print,
) -> int:
    """Fetch data, save one chart per year and return a process exit code."""
    write(f"Fetching {symbol} daily data since {start_year}...")
    try:
        daily = fetch(symbol, start_year)
    except DataFetchError as error:
        write(f"Error: {error}")
        return EXIT_FAILURE

    years = split_by_year(to_weekly(daily), start_year)
    if not years:
        write(f"Error: no weekly candles found for {symbol} since {start_year}.")
        return EXIT_FAILURE

    first_year = min(years)
    if first_year > start_year:
        write(f"Note: data for {symbol} starts in {first_year}, so earlier years are skipped.")

    for year, weekly in years.items():
        try:
            saved_path = render(weekly, symbol, year, out_dir)
        except (OSError, ValueError) as error:
            write(f"Error: could not save the {year} chart: {error}")
            return EXIT_FAILURE
        write(f"Saved {saved_path}")

    write(f"Done. {len(years)} charts saved to {out_dir}")
    return EXIT_OK


def main(
    out_dir: Path,
    read: Callable[[str], str] = input,
    now: Callable[[], datetime] = datetime.now,
) -> int:
    """Ask for the symbol and start year, then save the charts into a new folder in `out_dir`."""
    current_year = now().year
    try:
        symbol = prompt_until_valid("Enter ticker symbol (e.g. AAPL): ", parse_symbol, read=read)
        start_year = prompt_until_valid(
            "Enter start year (e.g. 2018): ",
            lambda raw: parse_start_year(raw, current_year),
            read=read,
        )
        run_dir = build_run_dir(out_dir, symbol, start_year, requested_at=now())
        return run(symbol, start_year, run_dir)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return EXIT_CANCELLED
