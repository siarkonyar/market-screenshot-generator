"""Render a year of weekly candles to a PNG in a TradingView-like dark theme."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files only, never open a window

import matplotlib.pyplot as plt  # noqa: E402
import mplfinance as mpf  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

UP_COLOR = "#26a69a"
DOWN_COLOR = "#ef5350"
BACKGROUND_COLOR = "#131722"
GRID_COLOR = "#2a2e39"
TEXT_COLOR = "#d1d4dc"
FIGURE_SIZE = (16, 9)
DPI = 150
PAD_INCHES = 0.3
VOLUME_AXIS_INDEX = 2  # mplfinance returns [price, price twin, volume, volume twin]
VOLUME_UNITS = ((1e9, "B"), (1e6, "M"), (1e3, "K"))

MARKET_COLORS = mpf.make_marketcolors(
    up=UP_COLOR,
    down=DOWN_COLOR,
    edge="inherit",
    wick="inherit",
    volume="inherit",
)

CHART_STYLE = mpf.make_mpf_style(
    base_mpf_style="nightclouds",
    marketcolors=MARKET_COLORS,
    facecolor=BACKGROUND_COLOR,
    figcolor=BACKGROUND_COLOR,
    edgecolor=GRID_COLOR,
    gridcolor=GRID_COLOR,
    gridstyle="-",
    y_on_right=True,
    rc={
        "axes.labelcolor": TEXT_COLOR,
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
        "text.color": TEXT_COLOR,
    },
)


def format_volume(value: float, _position: int | None = None) -> str:
    """Format a volume tick as 250M / 1.25B instead of matplotlib's scientific offset."""
    for size, suffix in VOLUME_UNITS:
        if abs(value) >= size:
            return f"{value / size:g}{suffix}"
    return f"{value:g}"


def render_year_chart(weekly: pd.DataFrame, symbol: str, year: int, out_dir: Path) -> Path:
    """Save `weekly` as `<out_dir>/<symbol>_<year>.png` and return the file path."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"{symbol}_{year}.png"

    figure, axes = mpf.plot(
        weekly,
        type="candle",
        volume=True,
        style=CHART_STYLE,
        title={"title": f"{symbol} — {year} (Weekly)", "weight": "bold"},
        ylabel="Price",
        ylabel_lower="Volume",
        volume_exponent=0,  # format_volume adds K/M/B units instead
        figsize=FIGURE_SIZE,
        datetime_format="%b %d",
        xrotation=0,
        tight_layout=True,
        returnfig=True,
    )
    axes[VOLUME_AXIS_INDEX].yaxis.set_major_formatter(FuncFormatter(format_volume))
    try:
        figure.savefig(
            file_path,
            dpi=DPI,
            facecolor=BACKGROUND_COLOR,
            bbox_inches="tight",
            pad_inches=PAD_INCHES,
        )
    finally:
        plt.close(figure)
    return file_path
