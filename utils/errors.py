from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Error:
    message: str
    code: int | None = None

    def __str__(self) -> str:
        return self.message
