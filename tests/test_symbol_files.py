from chart_screenshots.markets import Market
from chart_screenshots.symbol_files import read_symbols, update_symbol_files, write_symbols
from chart_screenshots.symbol_sources.http import SymbolSourceError


def unused_fetch(symbol, start_year):
    raise AssertionError("price data is not needed here")


def test_write_symbols_sorts_and_removes_duplicates(tmp_path):
    # Arrange
    path = tmp_path / "symbols" / "BIST.txt"

    # Act
    count = write_symbols(path, ["THYAO.IS", "AEFES.IS", "THYAO.IS"])

    # Assert
    assert count == 2
    assert path.read_text() == "AEFES.IS\nTHYAO.IS\n"


def test_read_symbols_skips_blank_lines_and_comments(tmp_path):
    # Arrange
    path = tmp_path / "NYS.txt"
    path.write_text("# NYSE common stocks\nIBM\n\n  BRK-B  \n")

    # Act / Assert
    assert read_symbols(path) == ["IBM", "BRK-B"]


def test_update_symbol_files_writes_one_file_per_market(tmp_path):
    # Arrange
    markets = (
        Market("NYS", "New York", lambda: ["IBM", "A"], unused_fetch),
        Market("BIST", "Istanbul", lambda: ["THYAO.IS"], unused_fetch),
    )
    messages = []

    # Act
    exit_code = update_symbol_files(markets, tmp_path, write=messages.append)

    # Assert
    assert exit_code == 0
    assert read_symbols(tmp_path / "NYS.txt") == ["A", "IBM"]
    assert read_symbols(tmp_path / "BIST.txt") == ["THYAO.IS"]


def test_update_symbol_files_keeps_old_file_when_a_source_fails(tmp_path):
    # Arrange
    (tmp_path / "LSE.txt").write_text("VOD.L\n")

    def broken_source():
        raise SymbolSourceError("LSE is down")

    markets = (
        Market("LSE", "London", broken_source, unused_fetch),
        Market("TSE", "Tokyo", lambda: ["7203.T"], unused_fetch),
    )
    messages = []

    # Act
    exit_code = update_symbol_files(markets, tmp_path, write=messages.append)

    # Assert
    assert exit_code == 1
    assert read_symbols(tmp_path / "LSE.txt") == ["VOD.L"]
    assert read_symbols(tmp_path / "TSE.txt") == ["7203.T"]
    assert any("LSE is down" in message for message in messages)


def test_update_symbol_files_refuses_to_write_an_empty_list(tmp_path):
    # Arrange
    markets = (Market("KRX", "Korea", lambda: [], unused_fetch),)

    # Act
    exit_code = update_symbol_files(markets, tmp_path, write=lambda message: None)

    # Assert
    assert exit_code == 1
    assert not (tmp_path / "KRX.txt").exists()
