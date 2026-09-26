from __future__ import annotations

from typing import Any

import requests

from utils.errors import Error

EMBED_PATH: str = "/api/embeddings"
EMBED_TIMEOUT_SECONDS: int = 120
EMBED_HOST: str = "127.0.0.1"
HTTP_OK: int = 200


def embed_text(port: int, model: str, text: str) -> list[float] | Error:
    response: requests.Response | Error = _post_helper(port=port, model=model, text=text)
    if isinstance(response, Error):
        return response
    return _extract_helper(response=response)


def _post_helper(port: int, model: str, text: str) -> requests.Response | Error:
    url: str = f"http://{EMBED_HOST}:{port}{EMBED_PATH}"
    try:
        return requests.post(url, json={"model": model, "prompt": text}, timeout=EMBED_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return Error(message=str(exc))


def _extract_helper(response: requests.Response) -> list[float] | Error:
    if response.status_code != HTTP_OK:
        return Error(message=response.text, code=response.status_code)
    vector: Any = response.json().get("embedding")
    if not isinstance(vector, list):
        return Error(message="Ollama did not return an embedding vector")
    return [float(v) for v in vector]
