from __future__ import annotations

from typing import Any

import requests

from config.reasoning_settings import ReasoningSettings
from utils.errors import Error

from .store import DEFAULT_TOP_K, get_store

REASONING_OLLAMA_URL: str = "http://127.0.0.1:11434"
REASONING_GENERATE_PATH: str = "/api/generate"
REASONING_GENERATE_TIMEOUT: int = 120
HTTP_OK: int = 200


def _resolve_url(port: int | None) -> str:
    if port is not None:
        return f"http://127.0.0.1:{port}"
    try:
        from ollama import ports

        live = ports.find_ollama()
        if live:
            return f"http://127.0.0.1:{live}"
    except Exception:
        pass
    return REASONING_OLLAMA_URL


def _ask_llm(prompt: str, model: str, port: int | None) -> str | Error:
    url = f"{_resolve_url(port)}{REASONING_GENERATE_PATH}"
    try:
        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=REASONING_GENERATE_TIMEOUT,
        )
    except requests.RequestException as exc:
        return Error(message=str(exc))
    if response.status_code != HTTP_OK:
        return Error(message=response.text, code=response.status_code)
    try:
        return response.json().get("response", "")
    except ValueError as exc:
        return Error(message=str(exc))


def _parse_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip().lstrip("0123456789.)-*• ").strip()
        if len(line) >= 4:
            out.append(line)
    return out


def decompose(
    query: str,
    *,
    model: str,
    port: int | None = None,
    max_n: int = 4,
) -> list[str]:
    prompt = (
        "You help a retrieval system. Break the question below into 2 to "
        f"{max_n} short, focused sub-questions that together cover everything "
        "needed to answer it. Return ONE sub-question per line. No numbering, "
        f"no preamble.\n\nQuestion: {query}\n\nSub-questions:"
    )
    raw = _ask_llm(prompt, model=model, port=port)
    if isinstance(raw, Error):
        return [query]
    return _parse_lines(raw)[:max_n] or [query]


def expand(
    query: str,
    *,
    breadth: int,
    model: str,
    port: int | None = None,
) -> list[str]:
    prompt = (
        f"Reformulate the question below in {breadth} diverse, equivalent ways. "
        "Use different vocabulary, synonyms and specificity. Return ONE "
        f"reformulation per line. No numbering, no preamble.\n\n"
        f"Question: {query}\n\nReformulations:"
    )
    raw = _ask_llm(prompt, model=model, port=port)
    if isinstance(raw, Error):
        return [query]
    variants = _parse_lines(raw)[:breadth]
    return [query, *variants]


def _plain_query(text: str, top_k: int, port: int | None) -> list[dict[str, Any]]:
    result = get_store(port=port).query(text=text, top_k=top_k)
    if isinstance(result, Error):
        return []
    return result if isinstance(result, list) else []


def _merge(batches: list[list[dict[str, Any]]], top_k: int) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    votes: dict[str, int] = {}
    for batch in batches:
        for item in batch:
            key = item.get("text", "")
            if not key:
                continue
            if key not in seen:
                seen[key] = item
                votes[key] = 0
            votes[key] += 1
    ordered = sorted(seen.values(), key=lambda x: -votes.get(x.get("text", ""), 0))
    return ordered[:top_k]


def retrieve_with_settings(
    text: str,
    settings: ReasoningSettings,
    top_k: int = DEFAULT_TOP_K,
    port: int | None = None,
) -> list[dict[str, Any]]:
    if not settings.use_cot and not settings.use_tot:
        return _plain_query(text, top_k, port)

    if settings.use_cot:
        sub_queries = decompose(
            text,
            model=settings.reasoning_model,
            port=port,
            max_n=settings.cot_max_subqueries,
        )
        if text not in sub_queries:
            sub_queries = [text, *sub_queries]
    else:
        sub_queries = [text]

    batches: list[list[dict[str, Any]]] = []
    for sq in sub_queries:
        if settings.use_tot:
            branches = expand(
                sq,
                breadth=settings.tot_breadth,
                model=settings.reasoning_model,
                port=port,
            )
            for branch in branches:
                batches.append(_plain_query(branch, top_k, port))
        else:
            batches.append(_plain_query(sq, top_k, port))

    return _merge(batches, top_k=top_k)