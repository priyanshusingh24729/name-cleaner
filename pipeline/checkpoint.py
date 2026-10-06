"""Checkpoint manager for state persistence and interruption resume (Section 21)."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile


class CheckpointManager:
    """Manages intermediate pipeline state, allowing safe resume after interruptions."""

    def __init__(self, checkpoint_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.checkpoint_path = checkpoint_path or base_dir / "output" / "pipeline_checkpoint.json"

    def exists(self) -> bool:
        """Check if a valid checkpoint file exists."""
        return self.checkpoint_path.exists() and self.checkpoint_path.stat().st_size > 0

    def load(self) -> Dict[str, Any]:
        """Load checkpoint state containing processed mappings."""
        if not self.exists():
            return {
                "total_unique": 0,
                "processed_count": 0,
                "mappings": {},
            }

        try:
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "total_unique": data.get("total_unique", 0),
                    "processed_count": len(data.get("mappings", {})),
                    "mappings": data.get("mappings", {}),
                }
        except Exception:
            return {
                "total_unique": 0,
                "processed_count": 0,
                "mappings": {},
            }

    def save(self, mappings: Dict[str, str], total_unique: int) -> None:
        """Atomically persist checkpoint state to avoid corrupting file on sudden shutdown."""
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "total_unique": total_unique,
            "processed_count": len(mappings),
            "mappings": mappings,
        }

        # Write to temporary file first, then atomic replace
        temp_dir = self.checkpoint_path.parent
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf)
            temp_name = tf.name

        os.replace(temp_name, self.checkpoint_path)

    def reset(self) -> None:
        """Remove checkpoint file to start processing from scratch."""
        if self.checkpoint_path.exists():
            try:
                self.checkpoint_path.unlink()
            except OSError:
                pass
