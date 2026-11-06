import pandas as pd

from chart_screenshots import charts
from chart_screenshots.charts import render_year_chart

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def make_weekly():
    index = pd.date_range("2024-01-01", periods=10, freq="W-MON")
    return pd.DataFrame(
        {"Open": range(10, 20), "High": range(12, 22), "Low": range(8, 18),
         "Close": range(11, 21), "Volume": range(100, 110)},
        index=index,
        dtype=float,
    )


def test_render_year_chart_draws_candles_without_volume_panel(monkeypatch, tmp_path):
    # Arrange
    real_plot = charts.mpf.plot
    captured = {}

    def spy_plot(data, **kwargs):
        captured.update(kwargs)
        return real_plot(data, **kwargs)

    monkeypatch.setattr(charts.mpf, "plot", spy_plot)

    # Act
    render_year_chart(make_weekly(), "AAPL", 2024, tmp_path)

    # Assert
    assert captured["type"] == "candle"
    assert captured.get("volume", False) is False


def test_render_year_chart_writes_png_named_after_symbol_and_year(tmp_path):
    # Arrange
    weekly = make_weekly()
    out_dir = tmp_path / "screenshots"

    # Act
    path = render_year_chart(weekly, "AAPL", 2024, out_dir)

    # Assert
    assert path == out_dir / "AAPL_2024.png"
    assert path.read_bytes().startswith(PNG_SIGNATURE)
