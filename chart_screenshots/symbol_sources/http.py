"""HTTP and spreadsheet helpers shared by the symbol list sources."""
import io
import warnings

import pandas as pd
import requests

# Some exchange sites reject requests that don't look like a browser.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TIMEOUT_SECONDS = 120


class SymbolSourceError(Exception):
    """Raised when a symbol list cannot be downloaded or has an unexpected format."""


def download(url: str, *, data: dict[str, str] | None = None) -> bytes:
    """GET `url` (or POST `data` to it) and return the response body."""
    method = "POST" if data is not None else "GET"
    try:
        response = requests.request(
            method,
            url,
            data=data,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise SymbolSourceError(f"Could not download {url}: {error}") from error
    return response.content


def read_excel(content: bytes, **kwargs) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Read an .xlsx file from bytes with every cell as text."""
    with warnings.catch_warnings():
        # Exchange spreadsheets often lack a default style; openpyxl warns but reads them fine.
        warnings.filterwarnings("ignore", message="Workbook contains no default style")
        return pd.read_excel(io.BytesIO(content), dtype=str, **kwargs)


def table_below_header(raw: pd.DataFrame, first_header: str) -> pd.DataFrame:
    """Return the rows under the row whose first cell is `first_header`, named by that row."""
    first_column = raw.iloc[:, 0].astype(str).str.strip()
    header_rows = first_column.index[first_column == first_header]
    if header_rows.empty:
        raise SymbolSourceError(f"Could not find a '{first_header}' header row in the spreadsheet.")
    header_position = raw.index.get_loc(header_rows[0])
    columns = [str(name).strip() for name in raw.iloc[header_position]]
    return raw.iloc[header_position + 1:].set_axis(columns, axis=1).reset_index(drop=True)
