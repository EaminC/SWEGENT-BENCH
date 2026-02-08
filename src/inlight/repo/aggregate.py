#!/usr/bin/env python3
"""
Step 3: Aggregate all per-repo test_paths JSONs, keep top-k most frequent paths, write one JSON for downstream.
"""
import json
import sys
from pathlib import Path
from collections import Counter

_REPO_DIR = Path(__file__).resolve().parent
_SRC_DIR = _REPO_DIR.parent

from . import config


def load_all_paths() -> list[str]:
    """Load every test_paths entry from repo_results/*.json."""
    paths = []
    if not config.REPO_RESULTS_DIR.exists():
        return paths
    for p in config.REPO_RESULTS_DIR.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            for x in data.get("test_paths") or []:
                if isinstance(x, str) and x.strip():
                    paths.append(x.strip())
        except Exception:
            continue
    return paths


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aggregate test_paths to top-k, optionally with min count")
    parser.add_argument("top_k", nargs="?", type=int, default=config.DEFAULT_TOP_K,
                        help=f"Top-k most frequent paths (default: {config.DEFAULT_TOP_K})")
    parser.add_argument("--min-count", type=int, default=0, metavar="N",
                        help="Only include paths with count > N (e.g. --min-count 3)")
    args = parser.parse_args()
    top_k = args.top_k
    min_count = args.min_count

    config.ensure_dirs()
    all_paths = load_all_paths()
    if not all_paths:
        print("No paths found in repo_results. Run discover_tests.py first.")
        out = {"top_k": top_k, "min_count": min_count, "paths": [], "counts": {}}
        with open(config.TOP_K_PATTERNS_JSON, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"Wrote empty result to {config.TOP_K_PATTERNS_JSON}")
        return 0

    counter = Counter(all_paths)
    # Filter by min_count then take top_k
    if min_count > 0:
        counter = Counter({p: c for p, c in counter.items() if c > min_count})
    ordered = counter.most_common(top_k)
    top_paths = [p for p, _ in ordered]
    counts = {p: c for p, c in ordered}

    out = {
        "top_k": top_k,
        "min_count": min_count,
        "paths": top_paths,
        "counts": counts,
    }
    with open(config.TOP_K_PATTERNS_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"Aggregated {len(all_paths)} path mentions from {len(list(config.REPO_RESULTS_DIR.glob('*.json')))} repos.")
    print(f"Top-{top_k} paths with count > {min_count} written to {config.TOP_K_PATTERNS_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
