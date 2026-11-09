"""All-markets mode: save yearly charts for every symbol listed in ./symbols.

Each symbol starts at the later of the requested year and its first year with
data, so a company that listed in 2015 gets charts from 2015 even if the run
starts in 2012. Symbols that fail are skipped and listed in failures.txt.
"""
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from chart_screenshots.charts import render_year_chart
from chart_screenshots.data import DataFetchError, NoDataError, yearly_candles
from chart_screenshots.exit_codes import EXIT_FAILURE, EXIT_OK
from chart_screenshots.markets import MARKETS, SYMBOLS_DIR, Market, symbols_file
from chart_screenshots.symbol_files import read_symbols

REQUEST_DELAY_SECONDS = 0.5  # pause between symbols so the data sources don't throttle the run
RETRY_DELAYS_SECONDS = (30, 120, 300)  # waits before each retry of a temporary download error
FAILURES_FILE = "failures.txt"

Render = Callable[[pd.DataFrame, str, int, Path], Path]


@dataclass(frozen=True)
class BulkRun:
    start_year: int
    out_dir: Path
    render: Render
    sleep: Callable[[float], None]
    write: Callable[[str], None]


@dataclass(frozen=True)
class MarketResult:
    loaded: bool
    charts: int = 0
    failures: tuple[str, ...] = ()


def run_all_markets(
    start_year: int,
    out_dir: Path,
    markets: tuple[Market, ...] = MARKETS,
    symbols_dir: Path = SYMBOLS_DIR,
    render: Render = render_year_chart,
    sleep: Callable[[float], None] = time.sleep,
    write: Callable[[str], None] = print,
) -> int:
    """Save charts into `<out_dir>/<MARKET>/<SYMBOL>/` and return a process exit code."""
    run = BulkRun(start_year, Path(out_dir), render, sleep, write)
    results = [_run_market(market, symbols_dir, run) for market in markets]

    failures = tuple(line for result in results for line in result.failures)
    if failures:
        _save_failures(run.out_dir, failures)
    charts = sum(result.charts for result in results)
    skipped = f" {len(failures)} symbols skipped, see {FAILURES_FILE}." if failures else ""
    write(f"Done. {charts} charts saved to {run.out_dir}.{skipped}")

    return EXIT_OK if any(result.loaded for result in results) else EXIT_FAILURE


def _run_market(market: Market, symbols_dir: Path, run: BulkRun) -> MarketResult:
    path = symbols_file(market, symbols_dir)
    try:
        symbols = read_symbols(path)
    except OSError as error:
        run.write(f"Skipping {market.code}: cannot read {path} ({error}). Run update_symbols.py first.")
        return MarketResult(loaded=False)

    run.write(f"{market.code} ({market.name}): {len(symbols)} symbols")
    outcomes = [
        _run_symbol(market, symbol, f"[{market.code} {position}/{len(symbols)}]", run)
        for position, symbol in enumerate(symbols, start=1)
    ]
    return MarketResult(
        loaded=True,
        charts=sum(charts for charts, _ in outcomes),
        failures=tuple(failure for _, failure in outcomes if failure),
    )


def _run_symbol(market: Market, symbol: str, label: str, run: BulkRun) -> tuple[int, str | None]:
    """Returns (charts saved, failure line or None)."""
    try:
        charts = _save_symbol(market, symbol, run)
    except (DataFetchError, OSError, ValueError) as error:
        run.write(f"{label} {symbol}: skipped ({error})")
        return 0, f"{market.code}\t{symbol}\t{error}"
    finally:
        run.sleep(REQUEST_DELAY_SECONDS)
    run.write(f"{label} {symbol}: {charts} charts")
    return charts, None


def _save_symbol(market: Market, symbol: str, run: BulkRun) -> int:
    years = yearly_candles(_fetch_with_retry(market, symbol, run), run.start_year)
    symbol_dir = run.out_dir / market.code / symbol
    for year, weekly in years.items():
        run.render(weekly, symbol, year, symbol_dir)
    return len(years)


def _fetch_with_retry(market: Market, symbol: str, run: BulkRun) -> pd.DataFrame:
    """Retry temporary errors (e.g. rate limits); a symbol with no data fails at once."""
    for delay in RETRY_DELAYS_SECONDS:
        try:
            return market.fetch_daily(symbol, run.start_year)
        except NoDataError:
            raise
        except DataFetchError as error:
            run.write(f"  {symbol}: {error} Retrying in {delay}s...")
            run.sleep(delay)
    return market.fetch_daily(symbol, run.start_year)


def _save_failures(out_dir: Path, failures: tuple[str, ...]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / FAILURES_FILE).write_text("".join(f"{line}\n" for line in failures))
