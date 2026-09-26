from __future__ import annotations

import os
import stat
from enum import StrEnum
from pathlib import Path

import security

STATE_DIR: Path = Path.home() / ".privategpt"
SESSION_FILE: Path = STATE_DIR / "session.enc"
SESSION_ENCODING: str = "utf-8"
USER_MARK: str = "--- user ---"
ASSISTANT_MARK: str = "--- assistant ---"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


def ensure_dir() -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(STATE_DIR, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    except OSError:
        pass
    return STATE_DIR


def load_session() -> list[dict[str, str]]:
    if not SESSION_FILE.exists() or not security.is_unlocked():
        return []
    try:
        raw_text = SESSION_FILE.read_text(encoding=SESSION_ENCODING)
        try:
            plain_text = security.decrypt_text(raw_text)
        except Exception:
            plain_text = raw_text
        return _parse_helper(text=plain_text)
    except OSError:
        return []


def append_session(role: Role, content: str) -> None:
    if not security.is_unlocked():
        return
    ensure_dir()
    existing: str = ""
    if SESSION_FILE.exists():
        try:
            raw = SESSION_FILE.read_text(encoding=SESSION_ENCODING)
            try:
                existing = security.decrypt_text(raw)
            except Exception:
                existing = raw
        except OSError:
            existing = ""
    updated = existing + _block_helper(role=role, content=content)
    try:
        encrypted = security.encrypt_text(updated)
        SESSION_FILE.write_text(encrypted, encoding=SESSION_ENCODING)
        try:
            os.chmod(SESSION_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
    except Exception as exc:
        print(f"[state] append error: {exc}")


def clear_session() -> None:
    SESSION_FILE.unlink(missing_ok=True)


def _block_helper(role: Role, content: str) -> str:
    return f"{_marker_helper(role=role)}\n{content}\n"


def _marker_helper(role: Role) -> str:
    return USER_MARK if role is Role.USER else ASSISTANT_MARK


def _parse_helper(text: str) -> list[dict[str, str]]:
    return [_message_helper(block=block) for block in _blocks_helper(text=text)]


def _blocks_helper(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        parts, current = _advance_blocks_helper(line=line, parts=parts, current=current)
    parts.extend(_flush_helper(lines=current))
    return parts


def _advance_blocks_helper(
    line: str,
    parts: list[str],
    current: list[str],
) -> tuple[list[str], list[str]]:
    if not _is_marker_helper(line=line):
        current.append(line)
        return parts, current
    parts.extend(_flush_helper(lines=current))
    return parts, [line]


def _flush_helper(lines: list[str]) -> list[str]:
    return ["\n".join(lines)] if lines else []


def _is_marker_helper(line: str) -> bool:
    return line in (USER_MARK, ASSISTANT_MARK)


def _message_helper(block: str) -> dict[str, str]:
    lines: list[str] = block.splitlines()
    return {"role": _role_helper(marker=lines[0]), "content": "\n".join(lines[1:]).rstrip()}


def _role_helper(marker: str) -> str:
    return Role.USER.value if marker == USER_MARK else Role.ASSISTANT.value
