from pypdf import PdfReader


def read(path: str) -> str:
    reader = PdfReader(path)
    return _join_pages(reader.pages)


def _join_pages(pages) -> str:
    return "\n\n".join(_page(p) for p in pages)


def _page(page) -> str:
    return page.extract_text() or ""
