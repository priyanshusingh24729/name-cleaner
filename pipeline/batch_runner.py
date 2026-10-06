"""High-throughput batch pipeline runner with checkpointing and Section 19/20 output separation."""

import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import pandas as pd

from app.normalizer import NameNormalizer
from pipeline.checkpoint import CheckpointManager
from pipeline.audit import AuditWriter


class BatchPipeline:
    """Orchestrates large-scale dataset normalization with deduplication, checkpointing, and audit logging."""

    def __init__(
        self,
        normalizer: Optional[NameNormalizer] = None,
        checkpoint_path: Optional[Path] = None,
        audit_path: Optional[Path] = None,
        batch_size: int = 5000,
    ):
        self.normalizer = normalizer or NameNormalizer()
        self.checkpoint_mgr = CheckpointManager(checkpoint_path)
        self.audit_writer = AuditWriter(audit_path)
        self.batch_size = batch_size

    def process_file(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        name_col: str = "Name",
        fresh: bool = False,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> Dict[str, Any]:
        """Process large CSV or Excel file through deduplicated batch pipeline."""
        in_p = Path(input_path)
        out_p = output_path or in_p.with_name(f"{in_p.stem}_normalized{in_p.suffix}")
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if fresh:
            self.checkpoint_mgr.reset()

        # Enable high-throughput batch write buffering
        if hasattr(self.normalizer, "dictionary") and hasattr(self.normalizer.dictionary, "cache"):
            self.normalizer.dictionary.cache.batch_flush_size = 2000

        start_time = time.time()
        print(f"Loading dataset: {in_p}...")
        ext = in_p.suffix.lower()
        if ext in [".xlsx", ".xls", ".xlsm"]:
            df = pd.read_excel(in_p)
        else:
            df = pd.read_csv(in_p)

        total_rows = len(df)
        if name_col not in df.columns:
            # Fallback to first column if specified column is missing
            name_col = df.columns[0]

        # 1. Deduplication Optimization (Section 14)
        raw_unique = df[name_col].dropna().astype(str).unique().tolist()
        total_unique = len(raw_unique)
        reduction_pct = (1.0 - (total_unique / total_rows)) * 100 if total_rows > 0 else 0.0

        print(f"Total Rows:       {total_rows:,}")
        print(f"Unique Names:     {total_unique:,} ({reduction_pct:.1f}% reduction via Section 14)")

        # 2. Load Checkpoint (Section 21)
        checkpoint_data = self.checkpoint_mgr.load()
        completed_mappings: Dict[str, str] = checkpoint_data.get("mappings", {})

        if completed_mappings:
            print(f"Resuming from checkpoint: {len(completed_mappings):,} already normalized.")

        remaining = [n for n in raw_unique if n not in completed_mappings]
        print(f"Remaining to Process: {len(remaining):,}")

        # 3. Process Remaining in Batches
        batch_audit_records = []
        for i, raw_name in enumerate(remaining, 1):
            res = self.normalizer.normalize_structured(raw_name)
            completed_mappings[raw_name] = res.normalized_name
            batch_audit_records.append({
                "result": res,
                "search_engine": "",
                "source_url": "",
            })

            # Flush audit log periodically
            if i % self.batch_size == 0 or i == len(remaining):
                self.audit_writer.write_batch(batch_audit_records)
                batch_audit_records.clear()

            # Save checkpoint state periodically (every 25k items or at end)
            if i % 25000 == 0 or i == len(remaining):
                self.normalizer.flush()
                self.checkpoint_mgr.save(completed_mappings, total_unique)

                processed_so_far = len(completed_mappings)
                pct = (processed_so_far / total_unique) * 100 if total_unique > 0 else 100.0
                elapsed = time.time() - start_time
                print(f"Progress: {processed_so_far:,} / {total_unique:,} unique names ({pct:.1f}%) in {elapsed:.1f}s")
                if progress_callback:
                    progress_callback(processed_so_far, total_unique, pct)

        self.normalizer.flush()

        # 4. Re-map onto DataFrame and Export (Section 19)
        print("Re-mapping canonical names onto full dataset...")
        df["Normalized_Application"] = df[name_col].astype(str).map(completed_mappings).fillna(df[name_col])

        # Validate Section 19: Only Normalized_Application column added, no internal audit fields
        diagnostic_fields = {"confidence", "method", "rules_applied", "rule_applied", "needs_verification"}
        assert not diagnostic_fields.intersection(set(df.columns)), "Diagnostic fields must not contaminate primary dataset!"

        print(f"Writing primary output: {out_p}...")
        if out_p.suffix.lower() in [".xlsx", ".xls"]:
            df.to_excel(out_p, index=False)
        else:
            df.to_csv(out_p, index=False)

        # Clean up checkpoint on complete success
        self.checkpoint_mgr.reset()

        duration = time.time() - start_time
        print(f"Successfully processed {total_rows:,} rows ({total_unique:,} unique) in {duration:.2f}s.")
        print(f"Primary Output: {out_p}")
        print(f"Audit Log:      {self.audit_writer.audit_path}")

        return {
            "total_rows": total_rows,
            "total_unique": total_unique,
            "duration_seconds": round(duration, 2),
            "output_path": str(out_p),
            "audit_path": str(self.audit_writer.audit_path),
        }
