import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
import requests

from ollama import ports
from utils.errors import Error

from .chunker import Chunk

CHROMA_DIR: Path = Path.home() / ".privategpt" / "rag" / "chroma"
COLLECTION_NAME: str = "knowledge"
EMBED_MODEL: str = "nomic-embed-text"
OLLAMA_URL: str = "http://127.0.0.1:11434"
EMBEDDINGS_PATH: str = "/api/embeddings"
EMBED_TIMEOUT_SECONDS: int = 120
DEFAULT_TOP_K: int = 8
ALL_CHUNKS: int = 0 

def _resolve_k_helper(collection: chromadb.Collection, top_k: int) -> int:
    count: int = collection.count()
    if top_k <= 0 or top_k > count:
        return count
    return top_k

_store: VectorStore | None = None


def get_store(port: int | None = None) -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore(port=port)
    elif port is not None:
        _store.set_port(port)
    return _store


def reset_store() -> None:
    global _store
    _store = None


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self, url: str | None = None, model_name: str = EMBED_MODEL, port: int | None = None) -> None:
        self._url = url
        self._port = port
        self._model_name = model_name

    def set_port(self, port: int | None) -> None:
        self._port = port
        if port is not None:
            self._url = f"http://127.0.0.1:{port}"

    def _resolved_url(self) -> str:
        if self._url:
            return self._url
        if self._port:
            return f"http://127.0.0.1:{self._port}"
        live_port = ports.find_ollama()
        if live_port:
            return f"http://127.0.0.1:{live_port}"
        return OLLAMA_URL

    def __call__(self, input: Documents) -> Embeddings:
        embeddings: list[list[float]] = []
        url = self._resolved_url()
        for text in input:
            response = requests.post(
                f"{url}{EMBEDDINGS_PATH}",
                json={"model": self._model_name, "prompt": text},
                timeout=EMBED_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])
        return embeddings

    def embed_query(self, input: Documents) -> Embeddings:
        return self.__call__(input)

    @staticmethod
    def name() -> str:
        return "local-ollama-embedding"


class VectorStore:
    def __init__(self, port: int | None = None, url: str | None = None) -> None:
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._embed = OllamaEmbeddingFunction(url=url, model_name=EMBED_MODEL, port=port)

    def set_port(self, port: int | None) -> None:
        self._embed.set_port(port)

    def collection(self) -> chromadb.Collection:
        return self._client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self._embed,
        )

    def add_chunks(self, chunks: list[Chunk]) -> Error | None:
        if not chunks:
            return None
        return _add_safe_helper(collection=self.collection(), chunks=chunks)

    def deactivate_chunks(self, chunk_ids: list[str]) -> Error | None:
        if not chunk_ids:
            return None
        return _deactivate_safe_helper(collection=self.collection(), chunk_ids=chunk_ids)

    def delete_chunks(self, chunk_ids: list[str]) -> Error | None:
        if not chunk_ids:
            return None
        return _delete_safe_helper(collection=self.collection(), chunk_ids=chunk_ids)

    def query(self, text: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]] | Error:
        return _query_safe_helper(collection=self.collection(), text=text, top_k=top_k)

    def count(self) -> int:
        return self.collection().count()
    

def _add_safe_helper(collection: chromadb.Collection, chunks: list[Chunk]) -> Error | None:
    try:
        collection.add(
            ids=[c.id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[_meta_helper(chunk=c) for c in chunks],
        )
    except Exception as exc:
        return Error(message=str(exc))
    return None


def _meta_helper(chunk: Chunk) -> dict[str, Any]:
    return {"source": chunk.source, "category": chunk.category, "active": True}


def _deactivate_safe_helper(collection: chromadb.Collection, chunk_ids: list[str]) -> Error | None:
    try:
        existing: dict[str, Any] = collection.get(ids=chunk_ids)
        new_metas: list[dict[str, Any]] = [
            {**m, "active": False} for m in existing.get("metadatas", [])
        ]
        collection.update(ids=existing["ids"], metadatas=new_metas)
    except Exception as exc:
        return Error(message=str(exc))
    return None


def _delete_safe_helper(collection: chromadb.Collection, chunk_ids: list[str]) -> Error | None:
    try:
        collection.delete(ids=chunk_ids)
    except Exception as exc:
        return Error(message=str(exc))
    return None


def _extract_identifiers(text: str) -> list[str]:
    tokens = re.findall(r"\b[A-Za-z0-9_-]{4,20}\b", text)
    ids: list[str] = []
    for t in tokens:
        if (any(c.isdigit() for c in t) and any(c.isalpha() for c in t)) or t.upper().startswith("PN"):
            ids.append(t)
    return list(dict.fromkeys(ids))


def _query_safe_helper(collection: chromadb.Collection, text: str, top_k: int) -> list[dict[str, Any]] | Error:
    last: Exception | None = None
    for _ in range(2):
        try:
            count = collection.count()
            if count == 0:
                return []

            exact_matches: list[dict[str, Any]] = []
            seen_texts: set[str] = set()

            # Exact keyword / identifier boost (e.g. PN XF557549)
            candidates = _extract_identifiers(text)
            for code in candidates:
                try:
                    res = collection.get(
                        where_document={"$contains": code},
                        where={"active": True},
                        limit=top_k,
                    )
                    for doc, meta in zip(res.get("documents", []), res.get("metadatas", [])):
                        if doc not in seen_texts:
                            seen_texts.add(doc)
                            exact_matches.append({
                                "text": doc,
                                "source": meta.get("source", ""),
                                "category": meta.get("category", ""),
                            })
                except Exception:
                    pass

            # Dense vector query: query memory chunks and knowledge base chunks
            mem_items: list[dict[str, Any]] = []
            try:
                mem_res = collection.query(
                    query_texts=[text],
                    n_results=min(top_k, count),
                    where={"$and": [{"category": "memory"}, {"active": True}]},
                )
                mem_items = _flatten_with_dist_helper(raw=mem_res)
            except Exception:
                pass

            kb_items: list[dict[str, Any]] = []
            try:
                kb_res = collection.query(
                    query_texts=[text],
                    n_results=min(top_k, count),
                    where={"$and": [{"category": {"$ne": "memory"}}, {"active": True}]},
                )
                kb_items = _flatten_with_dist_helper(raw=kb_res)
            except Exception:
                try:
                    fallback_res = collection.query(
                        query_texts=[text],
                        n_results=min(top_k, count),
                        where={"active": True},
                    )
                    kb_items = _flatten_with_dist_helper(raw=fallback_res)
                except Exception:
                    pass

            vector_matches = sorted(mem_items + kb_items, key=lambda x: x.get("dist", 9999.0))

            combined: list[dict[str, Any]] = list(exact_matches)
            for item in vector_matches:
                if item["text"] not in seen_texts:
                    seen_texts.add(item["text"])
                    combined.append({
                        "text": item["text"],
                        "source": item["source"],
                        "category": item["category"],
                    })

            max_allowed = max(top_k, len(exact_matches))
            return combined[:max_allowed]
        except Exception as exc:
            last = exc
    return Error(message=str(last))


def _flatten_with_dist_helper(raw: dict[str, Any]) -> list[dict[str, Any]]:
    docs = raw.get("documents", [[]])
    metas = raw.get("metadatas", [[]])
    dists = raw.get("distances", [[]])
    if not docs or not docs[0]:
        return []
    doc_list = docs[0]
    meta_list = metas[0] if metas and metas[0] else [{}] * len(doc_list)
    dist_list = dists[0] if dists and dists[0] else [9999.0] * len(doc_list)
    return [
        {
            "text": doc,
            "source": meta.get("source", ""),
            "category": meta.get("category", ""),
            "dist": dist,
        }
        for doc, meta, dist in zip(doc_list, meta_list, dist_list)
    ]


def _flatten_helper(raw: dict[str, Any]) -> list[dict[str, Any]]:
    docs = raw.get("documents", [[]])
    metas = raw.get("metadatas", [[]])
    if not docs or not docs[0]:
        return []
    return [
        {"text": doc, "source": meta.get("source", ""), "category": meta.get("category", "")}
        for doc, meta in zip(docs[0], metas[0])
    ]
