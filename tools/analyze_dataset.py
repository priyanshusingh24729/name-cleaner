"""Dataset pattern analyzer and representative test corpus generator.

Processes software application datasets, extracts pattern frequencies,
generates stratified representative samples, and compares Phase 1 normalization against
existing baseline values.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Dict, Any, List

import pandas as pd
from app.normalizer import NameNormalizer

# Common pattern recognizers for dataset scanning
RE_TS_PREFIX = re.compile(r"^TS\s*[-_:]", re.IGNORECASE)
RE_GAMES_PREFIX = re.compile(r"^Games\s*[-_:]", re.IGNORECASE)
RE_PARENTHETICAL = re.compile(r"\(([^)]+)\)")
RE_DOTTED_VER = re.compile(r"\b\d+(?:\.\d+)+\b")
RE_V_PREFIX_VER = re.compile(r"\bv\d+(?:\.\d+)*\b", re.IGNORECASE)
RE_YEAR = re.compile(r"\b(19\d{2}|20[0-4]\d)\b")
RE_LICENSE = re.compile(r"\b(?:Network\s+Licen[sc]e|Standalone\s+Licen[sc]e|Concurrent\s+Licen[sc]e|trial|demo|evaluation)\b", re.IGNORECASE)
RE_REGISTRATION = re.compile(r"\b(?:reg|reg\.|registered|registration)\b", re.IGNORECASE)
RE_OS = re.compile(r"\b(?:Windows(?:\s*\d+)?|Mac|macOS|OS\s*X|Linux|Ubuntu|Android|iOS|Unix)\b", re.IGNORECASE)


def load_dataset(input_path: Path, limit: int = None) -> pd.DataFrame:
    """Load application dataset from Excel or CSV file."""
    print(f"Loading dataset from: {input_path}...")
    ext = input_path.suffix.lower()

    if ext in [".xlsx", ".xlsm", ".xls"]:
        df = pd.read_excel(input_path, usecols=["Name", "Normalized_Application"], nrows=limit)
    elif ext == ".csv":
        df = pd.read_csv(input_path, usecols=["Name", "Normalized_Application"], nrows=limit)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    df = df.dropna(subset=["Name"])
    df["Name"] = df["Name"].astype(str)
    if "Normalized_Application" in df.columns:
        df["Normalized_Application"] = df["Normalized_Application"].fillna("").astype(str)
    else:
        df["Normalized_Application"] = ""

    print(f"Loaded {len(df):,} rows.")
    return df


def analyze_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Extract and summarize pattern occurrences across the dataset."""
    total_rows = len(df)
    unique_names = df["Name"].nunique()
    unique_normalized = df["Normalized_Application"].nunique()

    prefixes_counter = Counter()
    parenthetical_counter = Counter()
    license_counter = Counter()
    year_counter = Counter()
    version_types = Counter()

    for name in df["Name"].drop_duplicates():
        # Prefixes
        if RE_TS_PREFIX.search(name):
            prefixes_counter["TS- prefix"] += 1
        if RE_GAMES_PREFIX.search(name):
            prefixes_counter["Games prefix"] += 1

        # Parentheticals
        for paren in RE_PARENTHETICAL.findall(name):
            paren_clean = paren.strip()
            if len(paren_clean) < 30:
                parenthetical_counter[paren_clean] += 1

        # License
        lic_match = RE_LICENSE.findall(name)
        for lic in lic_match:
            license_counter[lic.title()] += 1

        # Years
        years = RE_YEAR.findall(name)
        for yr in years:
            year_counter[yr] += 1

        # Versions
        if RE_DOTTED_VER.search(name):
            version_types["Dotted Semantic Version"] += 1
        if RE_V_PREFIX_VER.search(name):
            version_types["v-prefixed Version"] += 1

    return {
        "total_rows": total_rows,
        "unique_raw_names": unique_names,
        "unique_existing_normalized": unique_normalized,
        "prefixes": dict(prefixes_counter.most_common(10)),
        "common_parentheticals": dict(parenthetical_counter.most_common(20)),
        "licenses": dict(license_counter.most_common(10)),
        "frequent_years": dict(year_counter.most_common(15)),
        "version_patterns": dict(version_types),
    }


def generate_representative_corpus(df: pd.DataFrame, sample_size: int = 1000) -> pd.DataFrame:
    """Select a stratified representative sample covering all major patterns."""
    unique_df = df.drop_duplicates(subset=["Name"]).copy()

    buckets = {
        "ts_prefix": unique_df[unique_df["Name"].str.contains(r"^TS[-_ :]", regex=True, case=False, na=False)],
        "games_prefix": unique_df[unique_df["Name"].str.contains(r"^Games[-_ :]", regex=True, case=False, na=False)],
        "parenthetical_os": unique_df[unique_df["Name"].str.contains(r"\((Android|iOS|Linux|Mac|Windows)", regex=True, case=False, na=False)],
        "registration": unique_df[unique_df["Name"].str.contains(r"\((reg|registered)", regex=True, case=False, na=False)],
        "license": unique_df[unique_df["Name"].str.contains(r"Network Licen[sc]e|trial|demo|evaluation", regex=True, case=False, na=False)],
        "v_prefix_version": unique_df[unique_df["Name"].str.contains(r"\bv\d+", regex=True, case=False, na=False)],
        "dotted_version": unique_df[unique_df["Name"].str.contains(r"\b\d+\.\d+", regex=True, na=False)],
        "years": unique_df[unique_df["Name"].str.contains(r"\b(19\d{2}|20\d{2})\b", regex=True, na=False)],
        "general": unique_df,
    }

    per_bucket = max(sample_size // len(buckets), 50)
    samples = []

    for category, b_df in buckets.items():
        n_take = min(len(b_df), per_bucket)
        if n_take > 0:
            sample_part = b_df.sample(n=n_take, random_state=42).copy()
            sample_part["Pattern_Category"] = category
            samples.append(sample_part)

    combined = pd.concat(samples).drop_duplicates(subset=["Name"]).head(sample_size)
    return combined


def compare_and_evaluate(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """Run Phase 1 Normalizer on representative corpus and compare against baseline."""
    normalizer = NameNormalizer()

    results = []
    for _, row in corpus_df.iterrows():
        raw_name = row["Name"]
        existing = row["Normalized_Application"]
        cat = row.get("Pattern_Category", "General")

        struct_res = normalizer.normalize_structured(raw_name)
        phase1_norm = struct_res.normalized_name

        match = (existing.strip().lower() == phase1_norm.strip().lower())
        results.append({
            "Raw_Name": raw_name,
            "Existing_Normalized": existing,
            "Phase1_Normalized": phase1_norm,
            "Agreement": match,
            "Confidence": struct_res.confidence,
            "Rules_Applied": ", ".join(struct_res.rules_applied),
            "Needs_Verification": struct_res.needs_verification,
            "Pattern_Category": cat,
        })

    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Analyze application name dataset patterns.")
    parser.add_argument("--input", required=True, help="Path to input Excel or CSV file")
    parser.add_argument("--output-dir", default="output", help="Directory to save analysis artifacts")
    parser.add_argument("--sample-size", type=int, default=1000, help="Size of representative corpus")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows loaded (optional)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(input_path, limit=args.limit)

    # 1. Analyze patterns
    print("Analyzing dataset patterns...")
    stats = analyze_patterns(df)

    report_path = output_dir / "pattern_analysis_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Pattern analysis report saved to: {report_path}")

    # 2. Generate representative corpus
    print(f"Extracting representative corpus of up to {args.sample_size} records...")
    corpus = generate_representative_corpus(df, sample_size=args.sample_size)

    # 3. Compare with Phase 1 Normalizer
    print("Evaluating Phase 1 normalizer on representative corpus...")
    eval_df = compare_and_evaluate(corpus)

    corpus_output_path = output_dir / "representative_corpus.csv"
    eval_df.to_csv(corpus_output_path, index=False, encoding="utf-8")
    print(f"Representative corpus with comparison saved to: {corpus_output_path}")

    agreement_rate = (eval_df["Agreement"].sum() / len(eval_df)) * 100
    needs_verif_count = eval_df["Needs_Verification"].sum()

    print("\n" + "=" * 50)
    print("DATASET ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Total Rows:                   {stats['total_rows']:,}")
    print(f"Unique Raw Names:             {stats['unique_raw_names']:,}")
    print(f"Unique Existing Normalized:   {stats['unique_existing_normalized']:,}")
    print(f"Representative Corpus Tested: {len(eval_df):,}")
    print(f"Phase 1 Agreement with Base:  {agreement_rate:.2f}%")
    print(f"Flagged for Verification:     {needs_verif_count}")
    print("=" * 50)


if __name__ == "__main__":
    main()
