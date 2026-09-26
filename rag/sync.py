from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from utils.errors import Error

from .manifest import Manifest, ManifestEntry
from .sources import chunks_for
from .store import VectorStore


@dataclass
class SyncReport:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0
    removed: int = 0
    memories: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        base = (
            f"{self.added} added, {self.updated} updated, "
            f"{self.unchanged} unchanged, {self.deactivated} deactivated, "
            f"{self.removed} removed"
        )
        if self.memories:
            base += f", {self.memories} memories synced"
        return base


def sync_index(manifest: Manifest, store: VectorStore, *, force: bool = False, sync_memories: bool = True) -> SyncReport:
    report: SyncReport = SyncReport()
    for entry in manifest.all():
        _sync_one_helper(entry=entry, store=store, report=report, force=force)
    if sync_memories:
        try:
            from .memory import sync_sessions_memory
            report.memories = sync_sessions_memory(store=store, force=force)
        except Exception as exc:
            report.errors.append(f"memory sync failed: {exc}")
    return report


def _sync_one_helper(entry: ManifestEntry, store: VectorStore, report: SyncReport, *, force: bool) -> None:
    if not entry.active:
        _deactivate_helper(entry=entry, store=store, report=report)
        return
    _refresh_helper(entry=entry, store=store, report=report, force=force)


def _deactivate_helper(entry: ManifestEntry, store: VectorStore, report: SyncReport) -> None:
    if not entry.chunk_ids:
        return
    _guard_helper(result=store.deactivate_chunks(entry.chunk_ids), report=report)
    report.deactivated += 1


def _refresh_helper(entry: ManifestEntry, store: VectorStore, report: SyncReport, *, force: bool = False) -> None:
    current_hash: str = _hash_file_helper(path=entry.path)
    if not force and current_hash == entry.last_hash and entry.chunk_ids:
        report.unchanged += 1
        return

    status: str = "updated" if entry.chunk_ids else "added"
    try:
        _reindex_helper(entry=entry, store=store, current_hash=current_hash)
    except Exception as exc:
        report.errors.append(f"{entry.path}: {exc}")
        return

    _bump_helper(report=report, status=status)

def _reindex_helper(entry: ManifestEntry, store: VectorStore, current_hash: str) -> None:
    chunks = chunks_for(path=entry.path, category=entry.category)

    if entry.chunk_ids:
        result = store.delete_chunks(entry.chunk_ids)
        if isinstance(result, Error):
            raise RuntimeError(f"delete failed: {result}")

    result = store.add_chunks(chunks)
    if isinstance(result, Error):
        raise RuntimeError(f"embed failed: {result}")

    entry.chunk_ids = [c.id for c in chunks]
    entry.last_hash = current_hash
    entry.indexed_at = datetime.now(tz=timezone.utc).isoformat()



def _bump_helper(report: SyncReport, status: str) -> None:
    if status == "added":
        report.added += 1
    else:
        report.updated += 1


def _guard_helper(result: Error | None, report: SyncReport) -> None:
    if isinstance(result, Error):
        report.errors.append(str(result))


def _hash_file_helper(path: str) -> str:
    try:
        with open(path, "rb") as handle:
            return "sha256:" + hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return ""
