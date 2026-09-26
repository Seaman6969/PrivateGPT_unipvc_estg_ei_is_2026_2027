from __future__ import annotations

import requests

PORT_START: int = 11434
PORT_END: int = 11550
PROBE_TIMEOUT_SECONDS: float = 0.3
TAGS_PATH: str = "/api/tags"
DEFAULT_HOST: str = "127.0.0.1"
HTTP_OK: int = 200


def is_ollama_at(port: int, host: str = DEFAULT_HOST) -> bool:
    return _probe_ollama_helper(port=port, host=host)


def find_ollama(start: int = PORT_START, end: int = PORT_END) -> int | None:
    return _first_live_port_helper(candidates=range(start, end))


def _probe_ollama_helper(port: int, host: str) -> bool:
    url: str = f"http://{host}:{port}{TAGS_PATH}"
    try:
        status: int = requests.get(url, timeout=PROBE_TIMEOUT_SECONDS).status_code
        return status == HTTP_OK
    except requests.RequestException:
        return False


def _first_live_port_helper(candidates: range) -> int | None:
    for port in candidates:
        if is_ollama_at(port=port):
            return port
    return None
