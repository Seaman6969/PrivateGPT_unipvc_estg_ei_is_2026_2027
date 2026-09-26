from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .chunker import Chunk, chunk_text

if TYPE_CHECKING:
    import pandas as pd

TEXT_SUFFIXES: frozenset[str] = frozenset({".txt"})
PDF_SUFFIXES: frozenset[str] = frozenset({".pdf"})
SPREADSHEET_SUFFIXES: frozenset[str] = frozenset({".csv", ".xlsx"})
REQUIRED_COLUMNS: tuple[str, ...] = ("Entry Date", "Quantity", "Order Unit", "PN")


def chunks_for(path: str, category: str) -> list[Chunk]:
    suffix = Path(path).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return _text_chunks(path=path, category=category)
    if suffix in PDF_SUFFIXES:
        return _pdf_chunks(path=path, category=category)
    if suffix in SPREADSHEET_SUFFIXES:
        return _spreadsheet_chunks(path=path, category=category)
    raise ValueError(f"unsupported file type: {suffix or '<none>'}")


def _text_chunks(path: str, category: str) -> list[Chunk]:
    text = Path(path).read_text(encoding="utf-8")
    return chunk_text(text=text, source=path, category=category)


def _pdf_chunks(path: str, category: str) -> list[Chunk]:
    from .pdf import extract_text
    from utils.errors import Error

    result = extract_text(path)
    if isinstance(result, Error):
        raise ValueError(str(result))
    return chunk_text(text=result, source=path, category=category)


def _spreadsheet_chunks(path: str, category: str) -> list[Chunk]:
    df = _load_spreadsheet(path=path)
    facts = _consumption_facts(df=df)
    return [
        Chunk(id=f"{path}::{i}", text=fact, source=path, category=category)
        for i, fact in enumerate(facts)
        if fact.strip()
    ]


def _load_spreadsheet(path: str) -> "pd.DataFrame":
    import pandas as pd

    source = Path(path)
    if source.suffix.lower() == ".xlsx":
        from .xlsx import convert as xlsx_to_csv
        source = Path(xlsx_to_csv(str(source)))

    df = pd.read_csv(source, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return _normalise(df=df)


def _normalise(df: "pd.DataFrame") -> "pd.DataFrame":
    import pandas as pd

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"spreadsheet is missing columns: {', '.join(missing)}")

    df["Entry Date"] = pd.to_datetime(df["Entry Date"], errors="coerce")
    df["Year"] = df["Entry Date"].dt.year
    df["PN"] = df["PN"].astype(str).str.strip()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    return df.dropna(subset=["Entry Date", "Quantity", "PN"]).reset_index(drop=True)


def _consumption_facts(df: "pd.DataFrame") -> list[str]:
    import pandas as pd
    from .facts import tier1_pk, tier2_year

    empty_contract = pd.DataFrame(
        columns=["PN", "Year", "Forecast", "Actual",
                 "Price", "Deviation", "FinancialImpact"],
    )
    return tier1_pk(df) + tier2_year(df, empty_contract)
