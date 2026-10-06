"""Command-line interface for the Software Application Name Normalizer (Phases 1 & 2)."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from app.normalizer import NameNormalizer
from app.deduplicator import DatasetDeduplicator


def cmd_normalize(args) -> int:
    """Handle normalization CLI command."""
    enable_semantic = getattr(args, "verify", False)
    normalizer = NameNormalizer(enable_semantic=enable_semantic)

    # Case 1: Normalize a single string passed as positional argument
    if args.name:
        if args.verbose:
            res = normalizer.normalize_structured(args.name)
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(normalizer.normalize(args.name))
        return 0

    # Case 2: Batch normalize a file (CSV or Excel)
    if args.input:
        in_path = Path(args.input)
        out_path = Path(args.output) if args.output else in_path.with_name(f"{in_path.stem}_normalized{in_path.suffix}")

        import pandas as pd
        print(f"Reading {in_path}...")
        if in_path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(in_path)
        else:
            df = pd.read_csv(in_path)

        col_name = "Name" if "Name" in df.columns else df.columns[0]
        print(f"Normalizing column '{col_name}' ({len(df)} records) with deduplication optimization...")

        dedup = DatasetDeduplicator(normalizer)
        result_df = dedup.process_dataframe(df, name_col=col_name)

        if out_path.suffix.lower() in [".xlsx", ".xls"]:
            result_df.to_excel(out_path, index=False)
        else:
            result_df.to_csv(out_path, index=False)

        print(f"Normalized output saved to: {out_path}")
        return 0

    print("Error: Specify a name to normalize, e.g. python main.py normalize \"Prion 0.3 (Android)\", or specify --input.")
    return 1


def cmd_test(args) -> int:
    """Run automated pytest suite."""
    print("Running automated test suite...")
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    if args.filter:
        cmd.extend(["-k", args.filter])
    result = subprocess.run(cmd)
    return result.returncode


def cmd_analyze(args) -> int:
    """Run dataset pattern analysis tool."""
    from tools.analyze_dataset import main as run_analyze
    sys_args = ["analyze_dataset.py", "--input", args.input]
    if args.output_dir:
        sys_args.extend(["--output-dir", args.output_dir])
    if args.sample_size:
        sys_args.extend(["--sample-size", str(args.sample_size)])
    if args.limit:
        sys_args.extend(["--limit", str(args.limit)])

    sys.argv = sys_args
    run_analyze()
    return 0


def cmd_stats(args) -> int:
    """Show active rules, exceptions, and canonical dictionary statistics."""
    normalizer = NameNormalizer()
    engine = normalizer.rule_engine
    dict_counts = normalizer.dictionary.store.count()

    print("=" * 55)
    print("SOFTWARE APPLICATION NAME NORMALIZER - SYSTEM STATS")
    print("=" * 55)
    print("RULE ENGINE & PRESERVATION CONFIG:")
    print(f"  Prefix Rules:               {len(engine.prefix_rules)}")
    print(f"  Suffix Rules:               {len(engine.suffix_rules)}")
    print(f"  Registration Rules:         {len(engine.registration_rules)}")
    print(f"  OS/Platform Rules:          {len(engine.os_platform_rules)}")
    print(f"  Architecture Rules:         {len(engine.architecture_rules)}")
    print(f"  Version Rules:              {len(engine.version_rules)}")
    print(f"  Contextual Year Rules:      {len(engine.year_rules)}")
    print(f"  Preserved Canonical Names:  {len(engine.preserve_exact)}")
    print(f"  Preserved Protected Tokens: {len(engine.preserve_tokens)}")
    print(f"  Canonical Casing Maps:      {len(engine.canonical_casing)}")
    print("-" * 55)
    print("LOCAL CANONICAL DICTIONARY (SQLite):")
    print(f"  Database Path:              {normalizer.dictionary.store.db_path}")
    print(f"  Total Cached Names:         {dict_counts['total']:,}")
    print(f"  Verified Canonical Names:   {dict_counts['verified']:,}")
    print("=" * 55)
    return 0


def cmd_dict_stats(args) -> int:
    """Show detailed statistics on SQLite canonical dictionary."""
    normalizer = NameNormalizer()
    store = normalizer.dictionary.store
    counts = store.count()
    verified_list = store.get_verified_canonical_names()

    print("=" * 50)
    print("LOCAL CANONICAL DICTIONARY DETAILS")
    print("=" * 50)
    print(f"Store Location:           {store.db_path}")
    print(f"Total Cached Mappings:    {counts['total']:,}")
    print(f"Verified Canonical Names: {counts['verified']:,}")
    print("\nVerified Canonical Sample:")
    for v in verified_list[:15]:
        print(f"  - {v}")
    if len(verified_list) > 15:
        print(f"  ... and {len(verified_list) - 15} more")
    print("=" * 50)
    return 0


def cmd_search(args) -> int:
    """Execute search query using multi-engine fallback layer."""
    from search.manager import SearchManager

    manager = SearchManager()
    print(f"Executing multi-engine search for: '{args.query}'...")
    results = manager.search(args.query, max_results=args.limit)

    if not results:
        print("No search results found from any configured engine.")
        return 0

    print(f"\nFound {len(results)} results via [{results[0].engine.upper()}]:\n")
    for i, res in enumerate(results, 1):
        print(f"{i}. {res.title}")
        print(f"   URL:     {res.url}")
        if res.snippet:
            print(f"   Snippet: {res.snippet[:120]}...")
        print()
    return 0


def cmd_crawl(args) -> int:
    """Execute web crawler and official source extractor."""
    from crawler.crawler import WebCrawler
    from search.manager import SearchManager

    crawler = WebCrawler()
    target = args.target.strip()

    if target.startswith(("http://", "https://")):
        print(f"Crawling URL: {target}...")
        evidence = crawler.crawl_page(target, vendor_hint=args.vendor)
        if not evidence:
            print("Failed to crawl or parse URL (timeout, non-HTML, or network issue).")
            return 1

        if args.verbose:
            print(json.dumps(evidence.to_dict(), indent=2))
        else:
            print("=" * 60)
            print("CRAWL EVIDENCE SUMMARY:")
            print("=" * 60)
            print(f"  URL:             {evidence.url}")
            print(f"  Domain:          {evidence.domain}")
            print(f"  Official Source: {'YES' if evidence.is_official else 'NO'}")
            print(f"  Authority Score: {evidence.authority_score:.2f} / 1.00")
            print(f"  Status Code:     {evidence.status_code}")
            print(f"  Raw Title:       {evidence.raw_title}")
            print(f"  Clean Title:     {evidence.clean_title}")
            if evidence.application_name:
                print(f"  App Name Tag:    {evidence.application_name}")
            if evidence.text_summary:
                print(f"  Summary:         {evidence.text_summary[:160]}...")
            print("=" * 60)
        return 0

    # Otherwise treat as software query: search engines first, then crawl top results
    print(f"Searching and crawling evidence for query: '{target}'...")
    search_manager = SearchManager()
    search_results = search_manager.search(target, max_results=args.limit * 2)

    if not search_results:
        print("No search results found to crawl.")
        return 1

    print(f"Found {len(search_results)} search results. Crawling top official sources...")
    evidences = crawler.crawl_results(search_results, vendor_hint=args.vendor, max_pages=args.limit)

    if not evidences:
        print("Could not retrieve crawl evidence from search results.")
        return 1

    print(f"\nCrawled {len(evidences)} pages successfully:\n")
    for i, ev in enumerate(evidences, 1):
        tag = "[OFFICIAL]" if ev.is_official else "[THIRD-PARTY]"
        print(f"{i}. {tag} {ev.clean_title or ev.raw_title}")
        print(f"   Domain:    {ev.domain} (Authority: {ev.authority_score:.2f})")
        print(f"   URL:       {ev.url}")
        if ev.text_summary:
            print(f"   Summary:   {ev.text_summary[:120]}...")
        print()

    return 0


def cmd_verify(args) -> int:
    """Run end-to-end semantic verification on a raw software name."""
    from semantic.verifier import SemanticVerifier

    raw_name = args.name.strip()
    print(f"Initiating semantic verification cascade for: '{raw_name}'...")
    verifier = SemanticVerifier()
    res = verifier.verify(raw_name)

    if args.verbose:
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print("=" * 60)
        print("SEMANTIC VERIFICATION RESULT:")
        print("=" * 60)
        print(f"  Raw Input:           {res.original_name}")
        print(f"  Canonical Name:      {res.normalized_name}")
        print(f"  Confidence Score:    {res.confidence:.4f}")
        print(f"  Resolution Method:   {res.method}")
        print(f"  Rules Applied:       {', '.join(res.rules_applied)}")
        print(f"  Needs Verification:  {'YES' if res.needs_verification else 'NO'}")
        print("=" * 60)
    return 0


def cmd_process_dataset(args) -> int:
    """Execute high-throughput batch pipeline on large CSV or Excel dataset."""
    from pipeline.batch_runner import BatchPipeline

    pipeline = BatchPipeline(batch_size=args.batch_size)
    in_path = Path(args.input)
    out_path = Path(args.output) if args.output else None

    print("=" * 60)
    print("LARGE DATASET NORMALIZATION PIPELINE (Phase 6)")
    print("=" * 60)
    print(f"Input:       {in_path}")
    print(f"Batch Size:  {args.batch_size}")
    print(f"Fresh Start: {args.fresh}")
    print("=" * 60)

    pipeline.process_file(
        input_path=in_path,
        output_path=out_path,
        name_col=args.col,
        fresh=args.fresh,
    )
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Core Software Application Name Normalizer CLI (Phases 1, 2, 3, 4, 5 & 6)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Normalize command
    norm_parser = subparsers.add_parser("normalize", help="Normalize a software name or file")
    norm_parser.add_argument("name", nargs="?", help="Raw software name string")
    norm_parser.add_argument("--input", "-i", help="Input file path (CSV or XLSX)")
    norm_parser.add_argument("--output", "-o", help="Output file path (CSV or XLSX)")
    norm_parser.add_argument("--verify", action="store_true", help="Enable LLM verification for uncertain records")
    norm_parser.add_argument("--verbose", "-v", action="store_true", help="Output full structured JSON")
    norm_parser.set_defaults(func=cmd_normalize)

    # Process Dataset command (Phase 6)
    proc_parser = subparsers.add_parser("process-dataset", help="High-throughput batch normalization for 907k+ datasets")
    proc_parser.add_argument("--input", "-i", required=True, help="Input CSV or Excel file")
    proc_parser.add_argument("--output", "-o", help="Output CSV or Excel file (defaults to *_normalized.*)")
    proc_parser.add_argument("--col", "-c", default="Name", help="Column name to normalize (default: Name)")
    proc_parser.add_argument("--batch-size", "-b", type=int, default=5000, help="Batch chunk size (default: 5000)")
    proc_parser.add_argument("--fresh", action="store_true", help="Reset checkpoint and start from scratch")
    proc_parser.set_defaults(func=cmd_process_dataset)

    # Verify command (Phase 5)
    verify_parser = subparsers.add_parser("verify", help="Execute search, crawl, and LLM verification on ambiguous name")
    verify_parser.add_argument("name", help="Raw software application name string")
    verify_parser.add_argument("--verbose", "-v", action="store_true", help="Output full structured JSON")
    verify_parser.set_defaults(func=cmd_verify)

    # Search command (Phase 3)
    search_parser = subparsers.add_parser("search", help="Query search engines via fallback cascade")
    search_parser.add_argument("query", help="Software name or query string")
    search_parser.add_argument("--limit", "-l", type=int, default=5, help="Maximum results to return")
    search_parser.set_defaults(func=cmd_search)

    # Crawl command (Phase 4)
    crawl_parser = subparsers.add_parser("crawl", help="Crawl web page or search results for canonical evidence")
    crawl_parser.add_argument("target", help="URL or software name query")
    crawl_parser.add_argument("--vendor", "-V", help="Optional vendor hint (e.g. Autodesk)")
    crawl_parser.add_argument("--limit", "-l", type=int, default=3, help="Maximum pages to crawl")
    crawl_parser.add_argument("--verbose", "-v", action="store_true", help="Output full structured JSON")
    crawl_parser.set_defaults(func=cmd_crawl)

    # Test command
    test_parser = subparsers.add_parser("test", help="Run automated test suite")
    test_parser.add_argument("-k", "--filter", help="Filter tests by keyword")
    test_parser.set_defaults(func=cmd_test)

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze dataset patterns")
    analyze_parser.add_argument("--input", "-i", required=True, help="Input Excel or CSV dataset")
    analyze_parser.add_argument("--output-dir", "-o", default="output", help="Output directory")
    analyze_parser.add_argument("--sample-size", type=int, default=1000, help="Representative corpus size")
    analyze_parser.add_argument("--limit", type=int, default=None, help="Limit number of rows read")
    analyze_parser.set_defaults(func=cmd_analyze)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show system rules and dictionary statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # Dict stats command
    dict_parser = subparsers.add_parser("dict-stats", help="Show SQLite canonical dictionary details")
    dict_parser.set_defaults(func=cmd_dict_stats)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
