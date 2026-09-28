from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Iterator
from typing import Any, TypedDict
import threading
import requests

from utils.errors import Error

MAX_ATTACHMENT_BYTES: int = 32 * 1024
DEFAULT_NUM_CTX: int = 32768
CHAT_TIMEOUT_SECONDS: int = 600
PULL_TIMEOUT_SECONDS: int = 7200
LIST_MODELS_TIMEOUT_SECONDS: int = 3
HTTP_OK: int = 200
DEFAULT_HOST: str = "127.0.0.1"
CHAT_PATH: str = "/api/chat"
TAGS_PATH: str = "/api/tags"
PULL_PATH: str = "/api/pull"

StringCallback = Callable[[str], None]


class ChatMessage(TypedDict):
    role: str
    content: str


def base_url(port: int, host: str = DEFAULT_HOST) -> str:
    return f"http://{host}:{port}"


def stream_chat(
    port: int,
    model: str,
    messages: list[ChatMessage],
    on_token: StringCallback | None = None,
    on_thinking: StringCallback | None = None,
    *,
    think: bool = False,
    num_ctx: int = DEFAULT_NUM_CTX,
    stop_event: threading.Event | None = None,
) -> str | Error:
    payload: dict[str, Any] = _chat_payload_helper(
        model=model, messages=messages, think=think, num_ctx=num_ctx,
    )
    return _post_chat_helper(
        port=port, payload=payload, on_token=on_token, on_thinking=on_thinking,
        stop_event=stop_event,
    )

def list_models(port: int) -> list[str] | Error:
    try:
        payload: dict[str, Any] = _get_json_helper(port=port, path=TAGS_PATH)
    except requests.RequestException as exc:
        return Error(message=str(exc))
    return _model_names_helper(payload=payload)


def has_model(port: int, model: str) -> bool | Error:
    names: list[str] | Error = list_models(port=port)
    if isinstance(names, Error):
        return names
    return any(_matches_helper(name=name, target=model) for name in names)


def pull(port, model, on_status=None):
    payload = {"model": model, "name": model, "stream": True}
    return _stream_pull_helper(port=port, payload=payload, on_status=on_status)


def _chat_payload_helper(
    model: str,
    messages: list[ChatMessage],
    think: bool,
    num_ctx: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
    if think:
        payload["think"] = True
    if num_ctx:
        payload["options"] = {"num_ctx": int(num_ctx)}
    return payload


def _post_chat_helper(
    port: int,
    payload: dict[str, Any],
    on_token: StringCallback | None,
    on_thinking: StringCallback | None,
    stop_event: threading.Event | None,
) -> str | Error:
    response: requests.Response | Error = _open_chat_helper(port=port, payload=payload)
    if isinstance(response, Error):
        return response
    return _consume_chat_stream_helper(
        response=response, on_token=on_token, on_thinking=on_thinking,
        stop_event=stop_event,
    )

def _open_chat_helper(port: int, payload: dict[str, Any]) -> requests.Response | Error:
    url: str = f"{base_url(port)}{CHAT_PATH}"
    try:
        return requests.post(url, json=payload, stream=True, timeout=CHAT_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return Error(message=str(exc))


def _consume_chat_stream_helper(
    response: requests.Response,
    on_token: StringCallback | None,
    on_thinking: StringCallback | None,
    stop_event: threading.Event | None,
) -> str | Error:
    if response.status_code != HTTP_OK:
        return Error(message=response.text, code=response.status_code)
    with response:
        return _consume_chat(
            response=response, on_token=on_token, on_thinking=on_thinking,
            stop_event=stop_event,
        )
        
def _consume_chat(
    response: requests.Response,
    on_token: StringCallback | None,
    on_thinking: StringCallback | None,
    stop_event: threading.Event | None,
) -> str:
    collected: list[str] = []
    for chunk in _chat_chunks_helper(response=response, stop_event=stop_event):
        _handle_chunk_helper(
            data=chunk, on_token=on_token, on_thinking=on_thinking, collected=collected,
        )
    return "".join(collected)


def _chat_chunks_helper(
    response: requests.Response,
    stop_event: threading.Event | None,
) -> Iterator[dict[str, Any]]:
    for data in _iter_parsed_helper(lines=response.iter_lines()):
        if stop_event is not None and stop_event.is_set():
            return
        yield data
        if data.get("done"):
            return


def _iter_parsed_helper(lines: Iterable[bytes]) -> Iterator[dict[str, Any]]:
    for line in lines:
        data: dict[str, Any] | None = _parse_json_helper(line=line)
        if data is not None:
            yield data


def _handle_chunk_helper(
    data: dict[str, Any],
    on_token: StringCallback | None,
    on_thinking: StringCallback | None,
    collected: list[str],
) -> None:
    message: dict[str, Any] = data.get("message", {})
    _emit_helper(callback=on_thinking, value=message.get("thinking"))
    _collect_helper(content=message.get("content"), collected=collected, on_token=on_token)


def _collect_helper(
    content: str | None,
    collected: list[str],
    on_token: StringCallback | None,
) -> None:
    if not content:
        return
    collected.append(content)
    _emit_helper(callback=on_token, value=content)


def _emit_helper(callback: StringCallback | None, value: str | None) -> None:
    if value and callback:
        callback(value)


def _parse_json_helper(line: bytes) -> dict[str, Any] | None:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _matches_helper(name: str, target: str) -> bool:
    return name == target or name.startswith(f"{target}:")


def _get_json_helper(port: int, path: str) -> dict[str, Any]:
    url: str = f"{base_url(port)}{path}"
    return requests.get(url, timeout=LIST_MODELS_TIMEOUT_SECONDS).json()


def _model_names_helper(payload: dict[str, Any]) -> list[str]:
    return [model["name"] for model in payload.get("models", [])]


def _stream_pull_helper(
    port: int,
    payload: dict[str, Any],
    on_status: StringCallback | None,
) -> Error | None:
    try:
        _consume_pull_stream_helper(port=port, payload=payload, on_status=on_status)
    except requests.RequestException as exc:
        return Error(message=str(exc))
    return None


def _consume_pull_stream_helper(
    port: int,
    payload: dict[str, Any],
    on_status: StringCallback | None,
) -> None:
    url: str = f"{base_url(port)}{PULL_PATH}"
    with requests.post(url, json=payload, stream=True, timeout=PULL_TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        _consume_pull(response=response, on_status=on_status)


def _consume_pull(response, on_status):
    seen: set[str] = set()
    for line in response.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("error"):
            raise requests.RequestException(data["error"])
        _handle_status_line_helper(line=line, seen=seen, on_status=on_status)


def _handle_status_line_helper(
    line: bytes,
    seen: set[str],
    on_status: StringCallback | None,
) -> None:
    status: str = _parse_status_helper(line=line)
    if status and status not in seen:
        seen.add(status)
        _emit_helper(callback=on_status, value=status)


def _parse_status_helper(line: bytes) -> str:
    try:
        return json.loads(line).get("status", "")
    except json.JSONDecodeError:
        return ""