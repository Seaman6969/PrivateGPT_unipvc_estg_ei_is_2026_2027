from __future__ import annotations

from typing import Any

from .manifest import Manifest, load_manifest, save_manifest
from .memory import index_session_memory, remove_session_memory, sync_sessions_memory
from .store import DEFAULT_TOP_K, VectorStore, get_store, reset_store
from .sync import SyncReport, sync_index
from utils.errors import Error

RAG_HEADER: str = "Reference material (retrieved from the knowledge base and memory):"


def build_index(manifest: Manifest | None = None, *, force: bool = False) -> tuple[SyncReport, Manifest]:
    reset_store()  # drop any cached client before rebuilding the index
    loaded: Manifest = manifest if manifest is not None else load_manifest()
    store: VectorStore = VectorStore()
    report: SyncReport = sync_index(manifest=loaded, store=store, force=force)
    save_manifest(manifest=loaded)
    return report, loaded

def retrieve(text: str, top_k: int = DEFAULT_TOP_K, port: int | None = None) -> list[dict[str, Any]]:
    result = get_store(port=port).query(text=text, top_k=top_k)
    if isinstance(result, Error):
        print(f"[rag] retrieval error: {result}")
        return []
    return result if isinstance(result, list) else []

def format_context(chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return ""
    body: str = "\n\n".join(_one_helper(chunk=c, index=i) for i, c in enumerate(chunks, 1))
    return f"{RAG_HEADER}\n{body}"


def _one_helper(chunk: dict[str, Any], index: int) -> str:
    return f"[{index}] ({chunk['category']}) {chunk['source']}\n{chunk['text']}"
