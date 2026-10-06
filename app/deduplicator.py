"""Deduplication optimizer for large-scale datasets (Section 14)."""

from typing import List, Dict, Any, Union
import pandas as pd
from app.normalizer import NameNormalizer


class DatasetDeduplicator:
    """Optimizes dataset normalization by processing only unique raw strings and re-mapping."""

    def __init__(self, normalizer: NameNormalizer):
        self.normalizer = normalizer

    def process_dataframe(
        self,
        df: pd.DataFrame,
        name_col: str = "Name",
        out_col: str = "Normalized_Application",
    ) -> pd.DataFrame:
        """Normalize a DataFrame by processing only unique names and mapping results back."""
        result_df = df.copy()
        if name_col not in result_df.columns:
            raise KeyError(f"Column '{name_col}' not found in dataframe.")

        raw_series = result_df[name_col].fillna("").astype(str)
        unique_names: List[str] = raw_series.unique().tolist()

        # Normalize unique names only
        unique_mapping: Dict[str, Dict[str, Any]] = {}
        for raw in unique_names:
            struct_res = self.normalizer.normalize_structured(raw)
            unique_mapping[raw] = {
                "normalized_name": struct_res.normalized_name,
                "confidence": struct_res.confidence,
                "changed": struct_res.changed,
                "needs_verification": struct_res.needs_verification,
            }

        # Map results back to all rows
        result_df[out_col] = raw_series.map(lambda r: unique_mapping[r]["normalized_name"])
        return result_df

    def process_name_list(self, names: List[str]) -> List[str]:
        """Normalize a list of names using unique-string deduplication."""
        unique_names = list(dict.fromkeys(names))
        mapping = {u: self.normalizer.normalize(u) for u in unique_names}
        return [mapping[n] for n in names]
