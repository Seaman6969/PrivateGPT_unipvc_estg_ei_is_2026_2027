from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from utils.errors import Error

from . import document, pdf, spreadsheet, text

MAX_ATTACHMENT_BYTES: int = 32 * 1024

Handler = Callable[[str], str]

HANDLERS: dict[str, Handler] = {
    ".pdf": pdf.read,
    ".docx": document.read,
    ".xlsx": spreadsheet.read_xlsx,
    ".xls": spreadsheet.read_xlsx,
    ".csv": spreadsheet.read_csv,
    ".txt": text.read,
    ".md": text.read,
}


def read(path: str) -> str | Error:
    handler: Handler | Error = _pick_helper(path=path)
    if isinstance(handler, Error):
        return handler
    try:
        raw: str = handler(path)
    except Exception as exc:
        return Error(message=f"{path}: {exc}")
    return _cap_helper(content=raw, name=path)


def extensions() -> tuple[str, ...]:
    return tuple(HANDLERS.keys())


def filetypes() -> list[tuple[str, str]]:
    return [("Supported files", _pattern_helper()), ("All files", "*.*")]


def _pick_helper(path: str) -> Handler | Error:
    ext: str = Path(path).suffix.lower()
    handler: Handler | None = HANDLERS.get(ext)
    if handler is None:
        return Error(message=f"unsupported file type: {ext}")
    return handler


def _cap_helper(content: str, name: str) -> str:
    if len(content) <= MAX_ATTACHMENT_BYTES:
        return content
    head: str = content[:MAX_ATTACHMENT_BYTES]
    return (
        f"{head}\n\n[truncated: showing first {MAX_ATTACHMENT_BYTES} "
        f"of {len(content)} characters from {name}]"
    )


def _pattern_helper() -> str:
    return " ".join(f"*{ext}" for ext in extensions())
