# Software Application Name Normalizer — Complete 6-Phase Pipeline

A production-grade **Software Application Name Normalizer** combining:
- **Phase 1**: Deterministic rule engine, safe Unicode/whitespace preprocessing, conservative year handling, and preservation exceptions.
- **Phase 2**: Persistent Local Canonical Dictionary (SQLite), hybrid in-memory/disk caching, candidate generation, RapidFuzz matching, and dataset deduplication.
- **Phase 3**: Multi-Engine Search Fallback Layer (SearXNG ➔ YaCy ➔ DuckDuckGo).
- **Phase 4**: Web Crawler, Content Extractor & Official Source Authority Detector.
- **Phase 5**: Semantic Reasoning & LLM Verification Layer (Section 18 & Section 12).
- **Phase 6**: High-Throughput Dataset Pipeline with Checkpointing, Section 19 Clean Dataset Export & Section 20 Audit Logging.

> **PRIMARY PRINCIPLE**:
> This is a **Software Product Canonical Name Resolver**, NOT a generic text cleaner. The biggest risk is **over-normalization**. Information is removed ONLY when there is strong, definitive evidence that it is metadata. If uncertain, information is strictly preserved and marked for downstream verification.

---

## Architecture (Phases 1–6)

```
Name cleaner/
├── app/
│   ├── __init__.py               # Core package exports
│   ├── result.py                 # NormalizationResult dataclass
│   ├── text_cleaner.py           # Safe Unicode, whitespace, quotation & dash cleaner
│   ├── rules.py                  # YAML rule loader & regex pattern compiler
│   ├── version_detector.py       # Dotted, v-prefixed, keyword, and trailing version detector
│   ├── metadata_detector.py      # OS/platform, license, registration, packaging detector
│   ├── candidates.py             # Multi-hypothesis candidate generator
│   ├── dictionary.py             # Canonical dictionary & conservative RapidFuzz matching
│   ├── deduplicator.py           # Large dataset deduplication and row re-mapper
│   └── normalizer.py             # Multi-tier normalization pipeline with semantic hooks
├── storage/
│   ├── __init__.py               # Storage package exports
│   ├── sqlite.py                 # SQLite database schema, CRUD, and bulk upsert operations
│   └── cache.py                  # Thread-safe hybrid L1 (in-memory) / L2 (SQLite) cache
├── search/
│   ├── __init__.py               # Search package exports
│   ├── base.py                   # SearchResult model and BaseSearchClient
│   ├── searxng.py                # SearXNG JSON API client with timeout & retry
│   ├── yacy.py                   # YaCy peer-to-peer JSON API client
│   ├── duckduckgo.py             # DuckDuckGo fallback client (HTTP + BeautifulSoup)
│   └── manager.py                # SearchManager: cascade fallback, query caching & query formatting
├── crawler/
│   ├── __init__.py               # Crawler package exports
│   ├── official_source.py        # OfficialSourceDetector: domain credibility & authority scoring
│   ├── extractor.py              # ContentExtractor: HTML title, app metadata, summary extraction
│   └── crawler.py                # WebCrawler: authority-prioritized page retrieval & CrawlEvidence
├── semantic/
│   ├── __init__.py               # Semantic reasoning package exports
│   ├── prompt.py                 # PromptBuilder: Section 18 structured prompt generator
│   ├── guards.py                 # AntiHallucinationGuard: output sanitization & token ground check
│   ├── client.py                 # BaseLLMClient, OpenAICompatibleClient (Ollama/vLLM), MockLLMClient
│   └── verifier.py               # SemanticVerifier orchestrator (Search ➔ Crawl ➔ LLM ➔ Cache)
├── pipeline/
│   ├── __init__.py               # Pipeline package exports
│   ├── checkpoint.py             # CheckpointManager: atomic state saving and interruption resume
│   ├── audit.py                  # AuditWriter: Section 20 normalization_audit.csv writer
│   └── batch_runner.py           # BatchPipeline: unique extraction, chunked execution, mapping
├── config/
│   ├── semantic.yaml             # LLM provider, model, temperature, confidence thresholds
│   ├── official_domains.yaml     # Official vendor domains, package repos & authority weights
│   ├── search.yaml               # Search engine endpoints, timeouts, and fallback order
│   ├── normalization_rules.yaml  # Configurable regex patterns for rules
│   └── exceptions.yaml           # Explicit preservation rules and canonical casing mappings
├── tests/
│   ├── test_normalizer.py        # Core specification positive examples
│   ├── test_over_normalization.py# Negative tests against over-cleaning
│   ├── test_versions.py          # Version formats and numeric preservation
│   ├── test_years.py             # Conservative year handling & contextual removal
│   ├── test_os.py                # OS metadata vs product name preservation
│   ├── test_license.py           # License & registration metadata removal
│   ├── test_prefixes.py          # TS- and Games: prefixes vs legitimate product names
│   ├── test_exceptions.py        # Exception handling and canonical casing
│   ├── test_text_cleaner.py      # Unicode, dashes, and whitespace normalization
│   ├── test_edge_cases.py        # Complex multi-token combinations
│   ├── test_sqlite.py            # SQLite schema, migrations, CRUD, and transaction tests
│   ├── test_cache.py             # Hybrid cache L1/L2 hits, misses, and persistence
│   ├── test_candidates.py        # Multi-hypothesis candidate generation tests
│   ├── test_fuzzy.py             # RapidFuzz candidate matching and anti-conflation tests
│   ├── test_deduplicator.py      # Dataset deduplication and mapping fidelity
│   ├── test_searxng.py           # SearXNG client unit tests
│   ├── test_yacy.py              # YaCy client unit tests
│   ├── test_duckduckgo.py        # DuckDuckGo fallback client unit tests
│   ├── test_search_fallback.py   # Multi-engine cascading fallback and query caching
│   ├── test_official_source.py   # Domain classification and authority scoring tests
│   ├── test_extractor.py         # SEO boilerplate stripping & HTML metadata parsing
│   ├── test_crawler.py           # WebCrawler prioritized retrieval & mock HTTP tests
│   ├── test_semantic_prompt.py   # Section 18 prompt building & constraints tests
│   ├── test_semantic_guards.py   # Anti-hallucination validation and sanitization tests
│   ├── test_semantic_client.py   # LLM client implementations & mock provider tests
│   ├── test_semantic_pipeline.py # End-to-end Search ➔ Crawl ➔ LLM verification & SQLite caching tests
│   ├── test_pipeline_checkpoint.py # Checkpoint saving, loading, and recovery tests
│   ├── test_pipeline_audit.py    # Section 20 normalization_audit.csv writer tests
│   └── test_pipeline_batch.py    # End-to-end batch runner and Section 19 clean dataset tests
├── tools/
│   └── analyze_dataset.py        # Pattern discovery, corpus generator & baseline comparator
├── input/                        # Input directory
├── output/
│   ├── canonical_dictionary.db   # SQLite persistent canonical database
│   ├── normalization_audit.csv   # Section 20 diagnostic audit log
│   ├── pattern_analysis_report.json # Dataset pattern statistics
│   └── representative_corpus.csv    # 1,000-record stratified corpus with comparison
├── requirements.txt              # Minimal project dependencies
├── README.md                     # Documentation
└── main.py                       # CLI entry point
```

---

## 5-Stage Verification Cascade (Section 10 & 18)

```
Raw Application Name
        ↓
1. Local Canonical Dictionary (Exact Cache Hit ➔ Instant Return)
        ↓ (Cache Miss)
2. Deterministic Rule Normalization (Safe Regex & Contextual Rules)
        ↓ (If Unchanged / High Confidence ➔ Cache & Return)
3. RapidFuzz Candidate Matching (Match Against Verified Canonical Index)
        ↓ (If Uncertain / needs_verification=True)
4. Multi-Engine Search Fallback Cascade:
        ┌─────────────┐
        │   SearXNG   │ (Preferred local meta-search)
        └──────┬──────┘
               │ (if unavailable or 0 results)
        ┌──────▼──────┐
        │    YaCy     │ (Peer-to-peer fallback)
        └──────┬──────┘
               │ (if unavailable or 0 results)
        ┌──────▼──────┐
        │ DuckDuckGo  │ (Reliable public fallback)
        └─────────────┘
        ↓
5. Web Crawler & Official Source Authority Detector:
        ┌──────────────────────────────────────────────┐
        │ Official Vendor Domain? (Score: 1.0)         │
        │ Package Repository? (Score: 0.95)             │
        │ Reputable Aggregator? (Score: 0.70)          │
        │ Clean Product Title & Meta Extracted         │
        └──────────────────────┬───────────────────────┘
                               ↓
6. Semantic Reasoning & LLM Verification (Section 18):
        ┌──────────────────────────────────────────────┐
        │ Structured Section 18 Prompt                 │
        │ Strict Constraints: No invention, keep years │
        │ Anti-Hallucination & Token Grounding Guard   │
        │ Confidence Scoring (0.90 vendor, 0.78 search)│
        │ Persists to Canonical Dictionary (SQLite)    │
        └──────────────────────────────────────────────┘
```

---

## CLI Usage

### 1. Large-Scale Dataset Processing (Phase 6)
Process hundreds of thousands of records with automatic deduplication, checkpointing, and separate audit logging:
```bash
python main.py process-dataset --input "path/to/dataset.xlsx" --output "output/dataset_normalized.xlsx"
```
Options:
- `--col`: Column name containing application strings (default: `Name`).
- `--batch-size`: Number of unique names per checkpoint (default: `5000`).
- `--fresh`: Reset checkpoint to start processing from scratch.

### 2. Normalize a Single Application Name
```bash
python main.py normalize "Prion 0.3 (Android)"
# Output: Prion
```

Verbose JSON audit output:
```bash
python main.py normalize "Prion 0.3 (Android)" --verbose
```

With semantic verification enabled for uncertain records:
```bash
python main.py normalize "TS-H2OMAP Water 7" --verify
```

### 3. End-to-End Semantic Verification (Phase 5)
Resolve ambiguous application names using the full search + crawl + LLM verification cascade:
```bash
python main.py verify "TS-LogRhythm Web Console 6"
```

### 4. Multi-Engine Search Fallback (Phase 3)
```bash
python main.py search "Liquid XML Studio"
```

### 5. Crawl & Official Source Authority Inspection (Phase 4)
```bash
python main.py crawl "https://www.liquid-technologies.com/xml-studio"
```

### 6. Run Automated Tests
```bash
python main.py test
```
All **184 automated unit tests** across Phases 1, 2, 3, 4, 5, and 6 pass (100% green).

### 7. Canonical Dictionary & System Statistics
```bash
python main.py dict-stats
python main.py stats
```

---

## Complete Project Roadmap

- [x] **Phase 1 (Complete)**: Deterministic core rules, regex engine, exceptions, test suite, dataset analyzer.
- [x] **Phase 2 (Complete)**: Local Canonical Dictionary (SQLite), hybrid caching, candidate generator, RapidFuzz matching, deduplicator.
- [x] **Phase 3 (Complete)**: Multi-Engine Search Fallback Layer (SearXNG ➔ YaCy ➔ DuckDuckGo).
- [x] **Phase 4 (Complete)**: Web Crawler, Content Extractor & Official Source Authority Detector.
- [x] **Phase 5 (Complete)**: Semantic Reasoning & LLM Verification Layer (Section 18 & Section 12).
- [x] **Phase 6 (Complete)**: High-throughput 907k batch processing pipeline with checkpointing, Section 19 clean output, and Section 20 audit logging.
