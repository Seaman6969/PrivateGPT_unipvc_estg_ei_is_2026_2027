from __future__ import annotations

from dataclasses import dataclass

CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 100
MIN_CHUNK_LENGTH: int = 40


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source: str
    category: str


def chunk_text(text: str, source: str, category: str) -> list[Chunk]:
    step: int = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    return _build_helper(text=text, source=source, category=category, step=step)


def _build_helper(text: str, source: str, category: str, step: int) -> list[Chunk]:
    # was: return [_one_helper(...) for offset in range(...)]
    # that kept the None entries _one_helper returns for short trailing
    # pieces, which crashed store.add_chunks() (ids=[c.id for c in chunks])
    # and made the WHOLE document fail to index, not just the short piece.
    chunks = [
        _one_helper(text=text, source=source, category=category, offset=offset)
        for offset in range(0, len(text), step)
    ]
    return [c for c in chunks if c is not None]


def _one_helper(text: str, source: str, category: str, offset: int) -> Chunk | None:
    piece: str = text[offset:offset + CHUNK_SIZE].strip()
    if len(piece) < MIN_CHUNK_LENGTH:
        return None
    return Chunk(id=f"{source}:{offset}", text=piece, source=source, category=category)
