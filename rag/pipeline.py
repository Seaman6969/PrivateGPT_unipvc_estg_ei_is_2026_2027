from __future__ import annotations

from typing import Any

from config.reasoning_settings import ReasoningSettings, load_reasoning_settings

from .manifest import Manifest, load_manifest, save_manifest
from .memory import index_session_memory, remove_session_memory, sync_sessions_memory
from .reasoning import retrieve_with_settings
from .store import DEFAULT_TOP_K, VectorStore, reset_store
from .sync import SyncReport, sync_index

RAG_HEADER: str = "Reference material (retrieved from the knowledge base and memory):"


def build_index(manifest: Manifest | None = None, *, force: bool = False) -> tuple[SyncReport, Manifest]:
    reset_store()
    loaded: Manifest = manifest if manifest is not None else load_manifest()
    store: VectorStore = VectorStore()
    report: SyncReport = sync_index(manifest=loaded, store=store, force=force)
    save_manifest(manifest=loaded)
    return report, loaded


def retrieve(
    text: str,
    top_k: int = DEFAULT_TOP_K,
    port: int | None = None,
    *,
    settings: ReasoningSettings | None = None,
) -> list[dict[str, Any]]:
    resolved = settings if settings is not None else load_reasoning_settings()
    return retrieve_with_settings(text, resolved, top_k=top_k, port=port)


def format_context(chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return ""
    body: str = "\n\n".join(_one_helper(chunk=c, index=i) for i, c in enumerate(chunks, 1))
    return f"{RAG_HEADER}\n{body}"


def _one_helper(chunk: dict[str, Any], index: int) -> str:
    return f"[{index}] ({chunk['category']}) {chunk['source']}\n{chunk['text']}"