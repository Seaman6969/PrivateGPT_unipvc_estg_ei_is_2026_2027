from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from utils.errors import Error

PDF_SUFFIX: str = ".pdf"
PAGE_SEPARATOR: str = "\n\n"


def extract_text(path: str) -> str | Error:
    return _extract_helper(path=Path(path))


def is_pdf(path: str) -> bool:
    return Path(path).suffix.lower() == PDF_SUFFIX


def _extract_helper(path: Path) -> str | Error:
    if not path.exists():
        return Error(message=f"pdf not found: {path}")
    reader: PdfReader | Error = _reader_helper(path=path)
    if isinstance(reader, Error):
        return reader
    return _join_pages_helper(reader=reader)


def _reader_helper(path: Path) -> PdfReader | Error:
    try:
        return PdfReader(str(path))
    except (OSError, PdfReadError) as exc:
        return Error(message=str(exc))


def _join_pages_helper(reader: PdfReader) -> str:
    pages: list[str] = [_page_text_helper(page=page) for page in reader.pages]
    return PAGE_SEPARATOR.join(page for page in pages if page)


def _page_text_helper(page: object) -> str:
    try:
        return (page.extract_text() or "").strip()
    except Exception:
        return ""
