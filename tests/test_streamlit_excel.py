"""Unit tests for Excel file reading and exporting in the normalizer workflow."""

import io
import pandas as pd
import pytest
from app.normalizer import NameNormalizer


def test_excel_file_read_and_process():
    # 1. Create in-memory Excel workbook
    test_data = {
        "Software": [
            "Prion 0.3 (Android)",
            "BMC Performance Manager (HP-UX)",
            "Microsoft 365",
            "AutoCAD (LT)",
        ]
    }
    input_df = pd.DataFrame(test_data)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        input_df.to_excel(writer, index=False, sheet_name="Applications")
    excel_buffer.seek(0)

    # 2. Simulate reading Excel with sheet detection
    excel_obj = pd.ExcelFile(excel_buffer)
    assert "Applications" in excel_obj.sheet_names
    df = pd.read_excel(excel_obj, sheet_name="Applications")
    assert len(df) == 4

    # 3. Normalize
    normalizer = NameNormalizer(use_cache=False, use_fuzzy=False, enable_semantic=False)
    results = [normalizer.normalize_structured(name).normalized_name for name in df["Software"]]

    assert results == [
        "Prion",
        "BMC Performance Manager",
        "Microsoft 365",
        "AutoCAD (LT)",
    ]

    # 4. Simulate Excel Export
    df["Normalized_Application"] = results
    export_buffer = io.BytesIO()
    with pd.ExcelWriter(export_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Normalized Data")
    export_buffer.seek(0)

    # 5. Read back exported Excel to verify integrity
    exported_df = pd.read_excel(export_buffer, sheet_name="Normalized Data")
    assert "Normalized_Application" in exported_df.columns
    assert exported_df["Normalized_Application"].tolist() == results
