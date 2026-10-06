"""Audit logger writing separate normalization_audit.csv per Section 20."""

import csv
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.result import NormalizationResult


AUDIT_COLUMNS = [
    "raw_name",
    "normalized_name",
    "confidence",
    "method",
    "rule_applied",
    "search_engine",
    "source_url",
    "verified",
]


class AuditWriter:
    """Writes detailed normalization diagnostic records to normalization_audit.csv."""

    def __init__(self, audit_path: Optional[Path] = None, overwrite: bool = False):
        base_dir = Path(__file__).resolve().parent.parent
        self.audit_path = audit_path or base_dir / "output" / "normalization_audit.csv"
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize CSV header if file does not exist or overwrite requested
        file_exists = self.audit_path.exists() and self.audit_path.stat().st_size > 0
        if overwrite or not file_exists:
            with open(self.audit_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(AUDIT_COLUMNS)

    def write_record(
        self,
        res: NormalizationResult,
        search_engine: str = "",
        source_url: str = "",
    ) -> None:
        """Append a single audit record to the CSV."""
        rules_str = ";".join(res.rules_applied) if res.rules_applied else ""
        row = [
            res.original_name,
            res.normalized_name,
            f"{res.confidence:.4f}",
            res.method,
            rules_str,
            search_engine,
            source_url,
            "1" if (res.confidence >= 0.95 and not res.needs_verification) else "0",
        ]
        with open(self.audit_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def write_batch(self, records: List[Dict[str, Any]]) -> None:
        """Batch append multiple audit records for high throughput."""
        if not records:
            return

        rows = []
        for r in records:
            res = r.get("result")
            if isinstance(res, NormalizationResult):
                rules_str = ";".join(res.rules_applied) if res.rules_applied else ""
                rows.append([
                    res.original_name,
                    res.normalized_name,
                    f"{res.confidence:.4f}",
                    res.method,
                    rules_str,
                    r.get("search_engine", ""),
                    r.get("source_url", ""),
                    "1" if (res.confidence >= 0.95 and not res.needs_verification) else "0",
                ])
            else:
                # Raw dict format
                rows.append([
                    r.get("raw_name", ""),
                    r.get("normalized_name", ""),
                    r.get("confidence", "1.0000"),
                    r.get("method", "deterministic"),
                    r.get("rule_applied", ""),
                    r.get("search_engine", ""),
                    r.get("source_url", ""),
                    r.get("verified", "0"),
                ])

        with open(self.audit_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
