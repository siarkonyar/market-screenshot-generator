# Changelog

All notable changes to this project are listed here.
Versions follow [semantic versioning](https://semver.org).

## [0.1.0] - 2026-11-09

First release.

### Added

- `python main.py` asks for a ticker and a start year and saves one weekly candlestick chart per year, styled like TradingView.
- Weekly candles are built from daily prices the way TradingView builds them: Monday to Friday, labelled with the Monday, split-adjusted but not dividend-adjusted.
- Every run saves into its own folder, named after the ticker, the start year and the time of the request.
- All markets mode: an empty ticker charts every symbol on NYSE, Nasdaq, LSE, TSE, Frankfurt, Euronext Paris, KRX and Borsa Istanbul, plus Binance USDT perpetual futures. Each symbol starts at its first year with data, temporary errors are retried, and skipped symbols are listed in `failures.txt`.
- `python update_symbols.py` refreshes the per-market symbol lists in `symbols/` from each exchange's official source.
- Binance futures prices come from the Binance API, stock prices from Yahoo Finance.

[0.1.0]: https://github.com/siarkonyar/market-screenshot-generator/releases/tag/v0.1.0
