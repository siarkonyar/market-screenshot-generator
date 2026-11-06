"""Render a year of weekly candles to a PNG in a TradingView-like dark theme."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files only, never open a window

import matplotlib.pyplot as plt  # noqa: E402
import mplfinance as mpf  # noqa: E402
import pandas as pd  # noqa: E402

UP_COLOR = "#26a69a"
DOWN_COLOR = "#ef5350"
BACKGROUND_COLOR = "#131722"
GRID_COLOR = "#2a2e39"
TEXT_COLOR = "#d1d4dc"
FIGURE_SIZE = (16, 9)
DPI = 150
PAD_INCHES = 0.3

MARKET_COLORS = mpf.make_marketcolors(
    up=UP_COLOR,
    down=DOWN_COLOR,
    edge="inherit",
    wick="inherit",
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


def render_year_chart(weekly: pd.DataFrame, symbol: str, year: int, out_dir: Path) -> Path:
    """Save `weekly` as `<out_dir>/<symbol>_<year>.png` and return the file path."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"{symbol}_{year}.png"

    figure, _ = mpf.plot(
        weekly,
        type="candle",
        style=CHART_STYLE,
        title={"title": f"{symbol} — {year} (Weekly)", "weight": "bold"},
        ylabel="Price",
        figsize=FIGURE_SIZE,
        datetime_format="%b %d",
        xrotation=0,
        tight_layout=True,
        returnfig=True,
    )
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
