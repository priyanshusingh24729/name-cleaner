"""Hybrid in-memory (L1) and SQLite (L2) cache layer."""

from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any, Union

from storage.sqlite import SQLiteDictionaryStore


class HybridCache:
    """Fast thread-safe in-memory cache backed by persistent SQLite storage."""

    def __init__(
        self,
        db_path_or_store: Union[Path, SQLiteDictionaryStore, str, None] = None,
        max_memory_entries: int = 500000,
        batch_flush_size: int = 1,
    ):
        if isinstance(db_path_or_store, SQLiteDictionaryStore):
            self.store = db_path_or_store
        else:
            self.store = SQLiteDictionaryStore(db_path_or_store)
        self.max_memory_entries = max_memory_entries
        self.batch_flush_size = batch_flush_size
        self._l1_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._pending_writes: list[Dict[str, Any]] = []
        self._lock = Lock()

    def get(self, raw_name: str) -> Optional[Dict[str, Any]]:
        """Lookup in L1 memory cache, then fall back to L2 SQLite database."""
        with self._lock:
            # Check L1 memory cache
            if raw_name in self._l1_cache:
                # Move to end (MRU)
                self._l1_cache.move_to_end(raw_name)
                return self._l1_cache[raw_name]

        # Check L2 SQLite
        entry = self.store.get(raw_name)
        if entry:
            with self._lock:
                self._l1_cache[raw_name] = entry
                if len(self._l1_cache) > self.max_memory_entries:
                    self._l1_cache.popitem(last=False)
            return entry

        return None

    def set(
        self,
        raw_name: str,
        normalized_name: str,
        confidence: float,
        method: str,
        rule_applied: str = "",
        source_url: str = "",
        verified: int = 0,
    ) -> None:
        """Insert or update entry in L1 memory cache and queue for batch SQLite write."""
        entry = {
            "raw_name": raw_name,
            "normalized_name": normalized_name,
            "confidence": confidence,
            "method": method,
            "rule_applied": rule_applied,
            "source_url": source_url,
            "verified": verified,
        }

        to_flush = None
        with self._lock:
            self._l1_cache[raw_name] = entry
            self._l1_cache.move_to_end(raw_name)
            if len(self._l1_cache) > self.max_memory_entries:
                self._l1_cache.popitem(last=False)

            self._pending_writes.append(entry)
            if len(self._pending_writes) >= self.batch_flush_size:
                to_flush = self._pending_writes
                self._pending_writes = []

        if to_flush:
            self.store.bulk_upsert(to_flush)

    def flush(self) -> None:
        """Flush any pending buffered writes to SQLite."""
        to_flush = None
        with self._lock:
            if self._pending_writes:
                to_flush = self._pending_writes
                self._pending_writes = []

        if to_flush:
            self.store.bulk_upsert(to_flush)

    def clear_memory(self) -> None:
        """Clear L1 memory cache without dropping SQLite data."""
        self.flush()
        with self._lock:
            self._l1_cache.clear()
