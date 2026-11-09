"""Borsa Istanbul stocks: the members of the BIST ALL SHARES (XUTUM) index."""
import io
from typing import Callable

import pandas as pd

from chart_screenshots.symbol_sources.http import download

INDEX_CONSTITUENTS_URL = "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"
ALL_SHARES_INDEX = "XUTUM"
ENGLISH_HEADER_ROW = [1]  # the file repeats its header in English on the second line


def parse_bist(content: bytes) -> list[str]:
    frame = pd.read_csv(
        io.BytesIO(content), sep=";", skiprows=ENGLISH_HEADER_ROW, dtype=str, encoding="latin-1"
    )
    members = frame.loc[frame["ENDEKS KODU"].str.strip() == ALL_SHARES_INDEX, "BILESEN KODU"]
    # Constituent codes look like THYAO.E; Yahoo uses THYAO.IS.
    return [f"{code.strip().split('.')[0]}.IS" for code in members.dropna()]


def fetch_bist(download: Callable[..., bytes] = download) -> list[str]:
    return parse_bist(download(INDEX_CONSTITUENTS_URL))
