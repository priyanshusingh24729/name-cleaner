"""SQLite-based storage for the local canonical dictionary."""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any, Union


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "output" / "canonical_dictionary.db"


class SQLiteDictionaryStore:
    """Manages SQLite persistence for normalized application names."""

    def __init__(self, db_path: Optional[Union[Path, str]] = None):
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        elif isinstance(db_path, str) and db_path == ":memory:":
            self.db_path = db_path
        else:
            self.db_path = Path(db_path)

        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self, "_local"):
            import threading
            self._local = threading.local()

        if getattr(self._local, "conn", None) is None:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            if self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        """Create canonical_dictionary table and indexes if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS canonical_dictionary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_name TEXT NOT NULL UNIQUE,
                    normalized_name TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    method TEXT NOT NULL,
                    rule_applied TEXT DEFAULT '',
                    source_url TEXT DEFAULT '',
                    verified INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_name ON canonical_dictionary(raw_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_normalized_name ON canonical_dictionary(normalized_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_verified ON canonical_dictionary(verified);")
            conn.commit()

    def get(self, raw_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve entry by exact raw_name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM canonical_dictionary WHERE raw_name = ? LIMIT 1;",
                (raw_name,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def upsert(
        self,
        raw_name: str,
        normalized_name: str,
        confidence: float,
        method: str,
        rule_applied: str = "",
        source_url: str = "",
        verified: int = 0,
    ) -> None:
        """Insert or update a normalization mapping."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO canonical_dictionary (
                    raw_name, normalized_name, confidence, method, rule_applied, source_url, verified, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(raw_name) DO UPDATE SET
                    normalized_name = excluded.normalized_name,
                    confidence = excluded.confidence,
                    method = excluded.method,
                    rule_applied = excluded.rule_applied,
                    source_url = excluded.source_url,
                    verified = excluded.verified,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (raw_name, normalized_name, confidence, method, rule_applied, source_url, verified),
            )
            conn.commit()

    def bulk_upsert(self, records: List[Dict[str, Any]]) -> int:
        """Batch upsert normalization records."""
        if not records:
            return 0

        sanitized = []
        for r in records:
            sanitized.append({
                "raw_name": r.get("raw_name", ""),
                "normalized_name": r.get("normalized_name", ""),
                "confidence": float(r.get("confidence", 1.0)),
                "method": r.get("method", "deterministic"),
                "rule_applied": r.get("rule_applied", ""),
                "source_url": r.get("source_url", ""),
                "verified": int(r.get("verified", 0)),
            })

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO canonical_dictionary (
                    raw_name, normalized_name, confidence, method, rule_applied, source_url, verified, updated_at
                )
                VALUES (
                    :raw_name, :normalized_name, :confidence, :method,
                    :rule_applied, :source_url, :verified, CURRENT_TIMESTAMP
                )
                ON CONFLICT(raw_name) DO UPDATE SET
                    normalized_name = excluded.normalized_name,
                    confidence = excluded.confidence,
                    method = excluded.method,
                    rule_applied = excluded.rule_applied,
                    source_url = excluded.source_url,
                    verified = excluded.verified,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                sanitized,
            )
            conn.commit()
            return cursor.rowcount

    def get_verified_canonical_names(self) -> List[str]:
        """Fetch all unique verified canonical product names."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT normalized_name FROM canonical_dictionary WHERE verified = 1 ORDER BY normalized_name;"
            )
            rows = cursor.fetchall()
            return [row["normalized_name"] for row in rows]

    def get_all_canonical_names(self) -> List[str]:
        """Fetch all distinct normalized names currently in the dictionary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT normalized_name FROM canonical_dictionary ORDER BY normalized_name;"
            )
            rows = cursor.fetchall()
            return [row["normalized_name"] for row in rows]

    def count(self) -> Dict[str, int]:
        """Return total and verified record counts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) as verified FROM canonical_dictionary;")
            row = cursor.fetchone()
            total = row["total"] or 0
            verified = row["verified"] or 0
            return {"total": total, "verified": verified}
