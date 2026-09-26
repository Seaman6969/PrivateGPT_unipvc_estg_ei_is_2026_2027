from __future__ import annotations

from enum import StrEnum

from rag.manifest import ManifestEntry, load_manifest, save_manifest
from utils.errors import Error
from pathlib import Path

class FileCategory(StrEnum):
    PARTS = "parts"
    PDF = "pdf"
    TEXT = "txt"


CATEGORIES: list[str] = [c.value for c in FileCategory]

_ALLOWED_SUFFIXES: dict[FileCategory, frozenset[str]] = {
    FileCategory.PARTS: frozenset({".xlsx", ".csv"}),
    FileCategory.PDF: frozenset({".pdf"}),
    FileCategory.TEXT: frozenset({".txt"}),
}

_ALLOWED_SUFFIX_LIST: str = ", ".join(
    sorted({suffix for suffixes in _ALLOWED_SUFFIXES.values() for suffix in suffixes})
)


def category_for_path(path: str) -> FileCategory:
    suffix = Path(path).suffix.lower()
    for category, suffixes in _ALLOWED_SUFFIXES.items():
        if suffix in suffixes:
            return category
    raise ValueError(
        f"unsupported file type {suffix or '<none>'}; allowed: {_ALLOWED_SUFFIX_LIST}"
    )


def validate_category(path: str, category: str) -> FileCategory:
    try:
        requested = FileCategory(category)
    except ValueError as exc:
        raise ValueError(f"unknown category: {category}") from exc

    actual = category_for_path(path)
    if requested is not actual:
        raise ValueError(
            f"{Path(path).name} is a {actual.value} file, not {requested.value}"
        )
    return requested


class FileCatalog:
    def __init__(self) -> None:
        self._manifest = load_manifest()

    def entries(self) -> list[ManifestEntry]:
        return sorted(self._manifest.all(), key=lambda e: e.path)

    def add(self, path: str, category: str) -> Error | None:
        if self._manifest.get(path) is not None:
            return Error(message=f"already registered: {path}")
        try:
            validate_category(path=path, category=category)
        except ValueError as exc:
            return Error(message=str(exc))
        self._manifest.put(ManifestEntry(path=path, category=category, active=True))
        return None

    def set_category(self, path: str, category: str) -> Error | None:
        entry: ManifestEntry | None = self._manifest.get(path)
        if entry is None:
            return Error(message=f"not registered: {path}")
        try:
            validate_category(path=path, category=category)
        except ValueError as exc:
            return Error(message=str(exc))
        entry.category = category
        entry.last_hash = ""
        return None

    def activate(self, path: str) -> Error | None:
        return self._set_active_helper(path=path, active=True)

    def deactivate(self, path: str) -> Error | None:
        return self._set_active_helper(path=path, active=False)

    def remove(self, path: str) -> Error | None:
        entry: ManifestEntry | None = self._manifest.get(path)
        if entry is None:
            return Error(message=f"not registered: {path}")
        entry.active = False
        entry.last_hash = ""
        self._manifest.drop(path)
        return None

    def save(self) -> Error | None:
        return save_manifest(manifest=self._manifest)

    def _set_active_helper(self, path: str, active: bool) -> Error | None:
        entry: ManifestEntry | None = self._manifest.get(path)
        if entry is None:
            return Error(message=f"not registered: {path}")
        entry.active = active
        return None
