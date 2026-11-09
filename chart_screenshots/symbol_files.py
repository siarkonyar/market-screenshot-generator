"""Read and refresh the per-market symbol lists stored in ./symbols."""
from pathlib import Path
from typing import Callable, Iterable

from chart_screenshots.exit_codes import EXIT_FAILURE, EXIT_OK
from chart_screenshots.markets import Market, symbols_file
from chart_screenshots.symbol_sources.http import SymbolSourceError

# Parsers raise KeyError / ValueError when an exchange changes its file layout.
SOURCE_ERRORS = (SymbolSourceError, KeyError, ValueError, OSError)


def write_symbols(path: Path, symbols: Iterable[str]) -> int:
    """Save symbols one per line, sorted and without duplicates. Returns the count."""
    unique = sorted(set(symbols))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{symbol}\n" for symbol in unique))
    return len(unique)


def read_symbols(path: Path) -> list[str]:
    """Symbols from a list file, ignoring blank lines and # comments."""
    lines = (line.strip() for line in Path(path).read_text().splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def update_symbol_files(
    markets: Iterable[Market],
    symbols_dir: Path,
    write: Callable[[str], None] = print,
) -> int:
    """Download each market's list into `<symbols_dir>/<CODE>.txt`; failures keep the old file."""
    succeeded = [_update_market(market, Path(symbols_dir), write) for market in markets]
    return EXIT_OK if all(succeeded) else EXIT_FAILURE


def _update_market(market: Market, symbols_dir: Path, write: Callable[[str], None]) -> bool:
    path = symbols_file(market, symbols_dir)
    try:
        symbols = market.fetch_symbols()
    except SOURCE_ERRORS as error:
        write(f"{market.code}: failed, keeping the existing list ({error})")
        return False

    if not symbols:
        write(f"{market.code}: the source returned no symbols, keeping the existing list")
        return False

    count = write_symbols(path, symbols)
    write(f"{market.code}: {count} symbols saved to {path}")
    return True
