from __future__ import annotations

import os
import signal
import subprocess
import time

from . import ports

OLLAMA_SERVE_ARGS: tuple[str, str] = ("ollama", "serve")
OLLAMA_HOST_ENV: str = "OLLAMA_HOST"
OLLAMA_HOST_TEMPLATE: str = "127.0.0.1:{port}"
DEFAULT_READY_TIMEOUT_SECONDS: float = 60.0
READY_POLL_INTERVAL_SECONDS: float = 0.5
TERMINATE_TIMEOUT_SECONDS: float = 5.0


def is_running() -> bool:
    return ports.find_ollama() is not None


def current_port() -> int | None:
    return ports.find_ollama()


def start(port: int) -> subprocess.Popen:
    return _spawn_server_helper(port=port)


def stop(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    _signal_terminate_helper(proc=proc)
    _wait_or_kill_helper(proc=proc)


def wait_until_ready(port: int, timeout: float = DEFAULT_READY_TIMEOUT_SECONDS) -> bool:
    deadline: float = time.time() + timeout
    return _poll_until_ready_helper(port=port, deadline=deadline)


def _spawn_server_helper(port: int) -> subprocess.Popen:
    return subprocess.Popen(
        list(OLLAMA_SERVE_ARGS),
        env=_server_env_helper(port=port),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _signal_terminate_helper(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass


def _wait_or_kill_helper(proc: subprocess.Popen) -> None:
    try:
        proc.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _signal_kill_helper(proc=proc)


def _signal_kill_helper(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass


def _server_env_helper(port: int) -> dict[str, str]:
    environment: dict[str, str] = dict(os.environ)
    environment[OLLAMA_HOST_ENV] = OLLAMA_HOST_TEMPLATE.format(port=port)
    return environment


def _poll_until_ready_helper(port: int, deadline: float) -> bool:
    if time.time() >= deadline:
        return False
    if ports.is_ollama_at(port=port):
        return True
    time.sleep(READY_POLL_INTERVAL_SECONDS)
    return _poll_until_ready_helper(port=port, deadline=deadline)
