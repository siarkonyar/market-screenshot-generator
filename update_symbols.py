"""Download the symbol lists into ./symbols.

Run it now and then to pick up new listings:

    python update_symbols.py            # every market
    python update_symbols.py BIST NYS   # only these markets
"""
import sys

from chart_screenshots.exit_codes import EXIT_FAILURE
from chart_screenshots.markets import SYMBOLS_DIR, select_markets
from chart_screenshots.symbol_files import update_symbol_files


def main(codes: list[str]) -> int:
    try:
        markets = select_markets(codes)
    except ValueError as error:
        print(error)
        return EXIT_FAILURE
    return update_symbol_files(markets, SYMBOLS_DIR)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
