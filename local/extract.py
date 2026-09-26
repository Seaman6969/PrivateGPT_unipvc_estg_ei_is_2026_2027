from __future__ import annotations

from pathlib import Path

from rag.pdf import extract_text
from utils.errors import Error

from .parts import read_parts_text

__all__ = ["filetypes", "read"]

_PDF_SUFFIX: str = ".pdf"
_TXT_SUFFIX: str = ".txt"
_PARTS_SUFFIXES: frozenset[str] = frozenset({".xlsx", ".csv"})


def filetypes() -> list[tuple[str, str]]:
    return [
        ("Parts spreadsheets", "*.xlsx *.XLSX *.csv *.CSV"),
        ("PDF documents", "*.pdf *.PDF"),
        ("Text files", "*.txt *.TXT"),
    ]

def read(path: str) -> str:
    source = Path(path)
    suffix = source.suffix.lower()

    if suffix in _PARTS_SUFFIXES:
        return read_parts_text(source)

    if suffix == _PDF_SUFFIX:
        result = extract_text(str(source))
        if isinstance(result, Error):
            raise ValueError(str(result))
        return result

    if suffix == _TXT_SUFFIX:
        return source.read_text(encoding="utf-8")

    raise ValueError(f"unsupported file type: {suffix or '<none>'}")
