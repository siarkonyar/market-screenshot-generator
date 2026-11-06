import pandas as pd
import pytest

from chart_screenshots.charts import format_volume, render_year_chart

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("value, expected", [
    (0, "0"),
    (950, "950"),
    (2_500, "2.5K"),
    (250_000_000, "250M"),
    (1_250_000_000, "1.25B"),
])
def test_format_volume_uses_short_units(value, expected):
    assert format_volume(value) == expected


def test_render_year_chart_writes_png_named_after_symbol_and_year(tmp_path):
    # Arrange
    index = pd.date_range("2024-01-01", periods=10, freq="W-MON")
    weekly = pd.DataFrame(
        {"Open": range(10, 20), "High": range(12, 22), "Low": range(8, 18),
         "Close": range(11, 21), "Volume": range(100, 110)},
        index=index,
        dtype=float,
    )
    out_dir = tmp_path / "screenshots"

    # Act
    path = render_year_chart(weekly, "AAPL", 2024, out_dir)

    # Assert
    assert path == out_dir / "AAPL_2024.png"
    assert path.read_bytes().startswith(PNG_SIGNATURE)
