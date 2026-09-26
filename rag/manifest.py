from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from utils.errors import Error

MANIFEST_FILE: Path = Path.home() / ".privategpt" / "rag" / "manifest.json"
MANIFEST_VERSION: int = 1
MANIFEST_ENCODING: str = "utf-8"


@dataclass
class ManifestEntry:
    path: str
    category: str
    active: bool
    last_hash: str = ""
    chunk_ids: list[str] = field(default_factory=list)
    indexed_at: str = ""


@dataclass
class Manifest:
    entries: dict[str, ManifestEntry] = field(default_factory=dict)
    version: int = MANIFEST_VERSION

    def get(self, path: str) -> ManifestEntry | None:
        return self.entries.get(path)

    def put(self, entry: ManifestEntry) -> None:
        self.entries[entry.path] = entry

    def drop(self, path: str) -> None:
        self.entries.pop(path, None)

    def all(self) -> list[ManifestEntry]:
        return list(self.entries.values())

    def pending_sync(self) -> list[ManifestEntry]:
        return [e for e in self.entries.values() if e.active and not e.last_hash]


def load_manifest(path: Path = MANIFEST_FILE) -> Manifest:
    if not path.exists():
        return Manifest()
    return _parse_helper(raw=_read_text_helper(path=path))


def save_manifest(manifest: Manifest, path: Path = MANIFEST_FILE) -> Error | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = _payload_helper(manifest=manifest)
    return _write_json_helper(path=path, payload=payload)


def _payload_helper(manifest: Manifest) -> dict:
    return {
        "version": manifest.version,
        "entries": {k: asdict(v) for k, v in manifest.entries.items()},
    }


def _read_text_helper(path: Path) -> str:
    try:
        return path.read_text(encoding=MANIFEST_ENCODING)
    except OSError:
        return ""


def _write_json_helper(path: Path, payload: dict) -> Error | None:
    try:
        path.write_text(json.dumps(payload, indent=2), encoding=MANIFEST_ENCODING)
    except OSError as exc:
        return Error(message=str(exc))
    return None


def _parse_helper(raw: str) -> Manifest:
    try:
        return _hydrate_helper(data=json.loads(raw))
    except (json.JSONDecodeError, TypeError, KeyError):
        return Manifest()


def _hydrate_helper(data: dict) -> Manifest:
    entries: dict[str, ManifestEntry] = {
        k: ManifestEntry(**v) for k, v in data.get("entries", {}).items()
    }
    return Manifest(entries=entries, version=data.get("version", MANIFEST_VERSION))
