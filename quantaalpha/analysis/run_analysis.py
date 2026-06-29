#!/usr/bin/env python3
"""
Run correlation / diversification analysis on a factor library JSON.

Examples:
    python -m quantaalpha.analysis.run_analysis -j all_factors_library.json
    python -m quantaalpha.analysis.run_analysis -j all_factors_library.json \\
        --top 20 --max-corr 0.7 --write-subset diversified_top20.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Factor library correlation / diversification analysis",
    )
    parser.add_argument("-j", "--factor-json", type=str, required=True,
                        help="Path to factor library JSON")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output JSON report path")
    parser.add_argument("--cache-dir", type=str, default=None,
                        help="MD5 factor cache dir (env FACTOR_CACHE_DIR by default)")
    parser.add_argument("--top", type=int, default=20,
                        help="Diversified subset size (default 20)")
    parser.add_argument("--max-corr", type=float, default=0.7,
                        help="Max pairwise corr inside the subset (default 0.7)")
    parser.add_argument("--redundancy-threshold", type=float, default=0.9,
                        help="|corr| above which a pair is flagged redundant")
    parser.add_argument("--write-subset", type=str, default=None,
                        help="Optional path to emit a filtered library JSON")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    library_path = Path(args.factor_json)
    if not library_path.exists():
        logger.error("Factor library not found: %s", library_path)
        return 2

    from quantaalpha.analysis.correlation import FactorDiversificationAnalyzer

    analyzer = FactorDiversificationAnalyzer(library_path, cache_dir=args.cache_dir)
    n_with_values = analyzer.load()

    if not analyzer.records:
        logger.error("Factor library is empty")
        return 1
    if n_with_values < 2:
        logger.warning(
            "Only %d factor(s) have cached values, correlation analysis will be empty.",
            n_with_values,
        )

    report = analyzer.report(
        top_n=args.top,
        max_corr=args.max_corr,
        redundancy_threshold=args.redundancy_threshold,
    )

    s = report["summary"]
    print()
    print("Factor diversification report")
    print("=" * 60)
    print(f"  Library:                {library_path}")
    print(f"  Total factors:          {s['total_factors']}")
    print(f"  Factors with values:    {s['factors_with_values']}")
    print(f"  Distinct clusters:      {s['n_clusters']}")
    print(f"  Redundant pairs (>= {args.redundancy_threshold}): {s['redundant_pairs']}")
    print(f"  Diversified subset:     {s['diversified_subset_size']} "
          f"(target {args.top}, max_corr {args.max_corr})")
    print()

    redundant = report["redundant_pairs"][:5]
    if redundant:
        print(f"Top {len(redundant)} most redundant pairs:")
        for p in redundant:
            print(f"  {p['correlation']:+.3f}  "
                  f"{p['factor_a_name']}  vs  {p['factor_b_name']}")
        print()

    subset = report["diversified_subset"]
    if subset:
        print(f"Diversified subset (max pairwise corr {args.max_corr}):")
        for i, r in enumerate(subset, 1):
            print(f"  {i:>3}. score={r['score']:.4f}  rank_ic={r['rank_ic']:+.4f}  "
                  f"max_corr={r['max_corr_with_selected']:.3f}  {r['factor_name']}")
        print()

    output_path = Path(args.output) if args.output else \
        library_path.with_suffix(".diversification.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Wrote full report to %s", output_path)

    if args.write_subset:
        analyzer.write_subset_library(args.write_subset, subset)
        print(f"Diversified subset library: {args.write_subset}")
        print("  python -m quantaalpha.backtest.run_backtest "
              f"-c configs/backtest.yaml --factor-source custom "
              f"--factor-json {args.write_subset}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
