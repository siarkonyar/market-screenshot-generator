# Weekly Chart Screenshots

A small command-line tool that saves one weekly candlestick chart per year for a
ticker symbol, styled like TradingView's dark theme.

```
$ python main.py
Enter ticker symbol (e.g. AAPL): AAPL
Enter start year (e.g. 2018): 2018
Fetching AAPL daily data since 2018...
Saved .../screenshots/AAPL_from_2018_2026-11-06_16-57-40/AAPL_2018.png
...
Saved .../screenshots/AAPL_from_2018_2026-11-06_16-57-40/AAPL_2026.png
Done. 9 charts saved to .../screenshots/AAPL_from_2018_2026-11-06_16-57-40
```

## Setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

The script asks for:

1. **Ticker symbol** in Yahoo Finance format, for example `AAPL`, `MSFT`,
   `BRK-B`, `BTC-USD`, `^GSPC` or `THYAO.IS`.
2. **Start year**, for example `2018`.

Each run creates its own folder inside `screenshots/`, named after the symbol,
the start year and the time of the request:

```
screenshots/
└── AAPL_from_2018_2026-11-06_16-57-40/
    ├── AAPL_2018.png
    ├── ...
    └── AAPL_2026.png
```

It holds one chart per year from the start year up to the current one, so
earlier runs are never overwritten. The current year's chart shows the weeks
traded so far.

If the symbol only started trading after the start year, earlier years are
skipped and the script says so.

## How the data matches TradingView

- **Source:** daily prices from Yahoo Finance via
  [`yfinance`](https://github.com/ranaroussi/yfinance). No account or API key
  is needed.
- **Weekly candles:** built from daily data. Each candle runs Monday to Friday
  and is labelled with its Monday, like TradingView. Holiday weeks open on the
  first trading day of the week.
- **Year boundaries:** a week belongs to the year its Monday falls in, so the
  week of Monday 29 December 2025 appears on the 2025 chart.
- **Adjustments:** prices are adjusted for stock splits but not for dividends,
  which is TradingView's default.

Prices usually match TradingView to the cent. Volume can differ a little,
because data vendors count trades from different venues.

## Tests

```bash
python -m pytest --cov=chart_screenshots
```
