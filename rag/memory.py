from __future__ import annotations

from typing import TYPE_CHECKING
# pyrefly: ignore [missing-import]
from utils.errors import Error

from .chunker import Chunk
from .store import VectorStore, get_store

if TYPE_CHECKING:
    from config.sessions import Session


def session_to_chunks(session: "Session") -> list[Chunk]:
    chunks: list[Chunk] = []
    messages = session.messages
    if not messages:
        return chunks

    title = session.meta.title or "Conversation"
    date_str = session.meta.created_at[:10] if session.meta.created_at else ""
    session_id = session.meta.id

    turn_idx = 0
    i = 0
    while i < len(messages):
        msg = messages[i]
        if msg.get("role") == "user":
            user_text = msg.get("content", "").strip()
            asst_text = ""
            if i + 1 < len(messages) and messages[i + 1].get("role") == "assistant":
                asst_text = messages[i + 1].get("content", "").strip()
                i += 2
            else:
                i += 1

            if not user_text and not asst_text:
                continue

            lines = [f"Session '{title}' ({date_str}):"]
            if user_text:
                lines.append(f"User: {user_text}")
            if asst_text:
                # Keep first 1200 chars of assistant response to keep memory focused
                clipped_asst = asst_text[:1200]
                lines.append(f"Assistant: {clipped_asst}")

            chunk_text = "\n".join(lines)
            chunk_id = f"memory:session:{session_id}:{turn_idx}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    source=f"Session: {title}",
                    category="memory",
                )
            )
            turn_idx += 1
        else:
            i += 1

    return chunks


def index_session_memory(session: "Session", store: VectorStore | None = None) -> Error | None:
    target_store = store if store is not None else get_store()
    chunks = session_to_chunks(session)
    if not chunks:
        return None
    return target_store.add_chunks(chunks)


def remove_session_memory(session_id: str, store: VectorStore | None = None) -> Error | None:
    target_store = store if store is not None else get_store()
    try:
        coll = target_store.collection()
        existing = coll.get(where={"category": "memory"})
        matching_ids = [
            cid for cid in existing.get("ids", [])
            if cid.startswith(f"memory:session:{session_id}:")
        ]
        if matching_ids:
            return target_store.delete_chunks(matching_ids)
    except Exception as exc:
        return Error(message=str(exc))
    return None


def sync_sessions_memory(store: VectorStore | None = None, force: bool = False) -> int:
    target_store = store if store is not None else get_store()
    from config.sessions import list_sessions, load_session

    total_chunks = 0
    all_chunks: list[Chunk] = []

    for meta in list_sessions():
        session = load_session(meta.id)
        if isinstance(session, Error):
            continue
        chunks = session_to_chunks(session)
        all_chunks.extend(chunks)

    if all_chunks:
        result = target_store.add_chunks(all_chunks)
        if not isinstance(result, Error):
            total_chunks = len(all_chunks)

    return total_chunks

