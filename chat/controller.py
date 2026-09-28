import re
from typing import Any

from ollama import client, ports
from utils.errors import Error
from rag import format_context, retrieve

EMBED_MODEL_KEYWORDS: tuple[str, ...] = (
    "embed", "bge", "e5-", "gte-", "jina-", "mxbai",
)
PREFERRED_CHAT_MODELS: tuple[str, ...] = (
    "llama3.1", "llama3.2", "llama3", "mistral", "qwen2.5", "deepseek-r1",
)

REQUIRED_CHAT_MODEL: str = "deepseek-r1:7b"
REQUIRED_EMBED_MODEL: str = "nomic-embed-text"

SYSTEM_PROMPT: str = (
    "You are LocalGPT, an intelligent local assistant specialized in procurement, data analysis, "
    "and contract evaluation, equipped with long-term memory and access to a verified local knowledge base.\n\n"
    "Guidelines:\n"
    "1. When reference material from the knowledge base or past conversation memory is provided, "
    "use it directly and accurately to answer the user's questions (including exact numbers, part numbers, "
    "statistics, quantities, contract terms, and past discussions).\n"
    "2. If reference material is available, cite or reference the relevant source or session when helpful.\n"
    "3. Maintain conversation continuity and remember context across turns.\n"
    "4. If the requested information is not in the reference material or conversation history, state what is known "
    "and reason based on general knowledge without inventing facts."
)

def ensure_models(port: int, on_status=None) -> Error | None:
    for model in (REQUIRED_CHAT_MODEL, REQUIRED_EMBED_MODEL):
        present = client.has_model(port=port, model=model)
        if isinstance(present, Error):
            return present
        if present:
            continue
        if on_status:
            on_status(f"Downloading {model}...")
        result = client.pull(port=port, model=model, on_status=on_status)
        if isinstance(result, Error):
            return result
    return None

def detect_port() -> int | None:
    return ports.find_ollama()


def default_model(port: int | None) -> str:
    if port is None:
        return ""
    installed: list[str] | Error = client.list_models(port=port)
    if isinstance(installed, Error):
        return ""
    return _pick_chat_model_helper(installed=installed)


def _pick_chat_model_helper(installed: list[str]) -> str:
    chat: list[str] = [name for name in installed if not _is_embedding_helper(name=name)]
    if not chat:
        return ""
    return _preferred_or_first_helper(candidates=chat)


def _is_embedding_helper(name: str) -> bool:
    lowered: str = name.lower()
    return any(keyword in lowered for keyword in EMBED_MODEL_KEYWORDS)


def _preferred_or_first_helper(candidates: list[str]) -> str:
    for name in candidates:
        if name == REQUIRED_CHAT_MODEL:
            return name
        
    for preferred in PREFERRED_CHAT_MODELS:
        for name in candidates:
            if name.startswith(preferred):
                return name
    return candidates[0]


def _contextual_query_helper(prompt: str, history: list[dict[str, str]] | None) -> str:
    if not history:
        return prompt
    recent_messages = history[-4:]
    history_text = " ".join(m.get("content", "") for m in recent_messages if m.get("role") in ("user", "assistant"))
    tokens = re.findall(r"\b[A-Za-z0-9_-]{4,20}\b", history_text)
    identifiers = [
        t for t in tokens
        if (any(c.isdigit() for c in t) and any(c.isalpha() for c in t)) or t.upper().startswith("PN")
    ]
    unique_ids = list(dict.fromkeys(identifiers))
    missing_ids = [code for code in unique_ids if code.lower() not in prompt.lower()]
    if missing_ids:
        return f"{prompt} {' '.join(missing_ids)}"
    return prompt


def send(
    root: Any,
    port: int,
    model: str,
    prompt: str,
    attachments: list[tuple[str, str]],
    modes: set[str],
    on_token,
    on_thinking,
    on_done,
    stop_event=None,
    history: list[dict[str, str]] | None = None,
) -> None:
    augmented: str = _augment_helper(prompt=prompt, attachments=attachments, modes=modes)
    search_query = _contextual_query_helper(prompt=prompt, history=history)
    chunks = retrieve(search_query, port=port)
    context = format_context(chunks)
    if context:
        augmented = f"{context}\n\n{augmented}"

    messages: list[client.ChatMessage] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": augmented})

    think_enabled = "deepthink" in modes
    result: str | Error = client.stream_chat(
        port=port, model=model, messages=messages,
        on_token=on_token, on_thinking=on_thinking,
        think=think_enabled,
        stop_event=stop_event,
    )
    on_done(result)


def _augment_helper(
    prompt: str,
    attachments: list[tuple[str, str]],
    modes: set[str],
) -> str:
    if not attachments:
        return prompt
    blocks: list[str] = [
        f"--- {path} ---\n{content}" for path, content in attachments
    ]
    joined: str = "\n\n".join(blocks)
    return f"{joined}\n\n---\n\n{prompt}"