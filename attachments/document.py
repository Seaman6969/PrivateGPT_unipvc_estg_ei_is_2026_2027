from docx import Document


def read(path: str) -> str:
    doc = Document(path)
    return _paragraphs(doc)


def _paragraphs(doc) -> str:
    lines = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(lines)
