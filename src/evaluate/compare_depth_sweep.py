"""Run pool-and-extrapolate across all sweep depths, build a comparison table.

Reads predictions-depth-{0,1,2,999}.jsonl, runs the eval harness against the
existing labels for each, and emits a single comparison report (scorecards
inline, plus a side-by-side metrics table).

Usage:
    python -m src.evaluate.compare_depth_sweep \\
        --predictions-glob 'results/detector-runs/schedule_change_announcement/cassandra-2014-predictions-depth-*.jsonl' \\
        --labels labels/schedule_change_announcement/cassandra-2014-labels.jsonl \\
        --corpus-size 731 --random-sample-size 100 \\
        --pre-reg-commit 04c0a5e \\
        --out-dir results/evals/schedule_change_announcement-depth-sweep
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from src.evaluate.pool_and_extrapolate import evaluate, load_jsonl


def depth_from_filename(p: Path) -> int:
    m = re.search(r"depth-(\d+)", p.name)
    return int(m.group(1)) if m else -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions-glob", required=True)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--corpus-size", type=int, required=True)
    ap.add_argument("--random-sample-size", type=int, required=True)
    ap.add_argument("--pre-reg-commit", default=None)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    pred_paths = sorted(Path().glob(args.predictions_glob), key=depth_from_filename)
    if not pred_paths:
        raise SystemExit(f"No predictions matched {args.predictions_glob}")

    labels = load_jsonl(args.labels)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in pred_paths:
        depth = depth_from_filename(path)
        preds = load_jsonl(path)
        sc = evaluate(
            predictions=preds,
            labels=labels,
            corpus_size=args.corpus_size,
            random_sample_size=args.random_sample_size,
            pre_reg_commit=args.pre_reg_commit,
            predictions_path=str(path),
            labels_path=str(args.labels),
        )
        out_path = args.out_dir / f"scorecard-depth-{depth}.json"
        out_path.write_text(json.dumps(sc, indent=2) + "\n", encoding="utf-8")
        p = sc["precision_pool"]
        r = sc["recall_extrapolated"]
        rows.append({
            "depth": depth,
            "model_positives": sc["prediction_summary"]["model_positives"],
            "tp": p["tp"],
            "fp": p["fp"],
            "precision": p["precision"],
            "precision_ci": (p["wilson_95_lower"], p["wilson_95_upper"]),
            "sample_pos": r["random_sample_positives"],
            "sample_n": r["random_sample_size"],
            "recall": r["recall"],
            "recall_ci": (r["recall_95_lower"], r["recall_95_upper"]),
            "f1": sc["f1"],
            "brier": sc["brier_score"]["value"],
            "brier_n": sc["brier_score"]["n_used"],
        })

    # Pretty-print the side-by-side
    print("=" * 100)
    print(f"DEPTH SWEEP COMPARISON  (labels: {args.labels.name})")
    print("=" * 100)
    header = f"{'depth':>5}  {'model+':>6}  {'TP':>3}  {'FP':>3}  {'precision':>20}  {'recall':>20}  {'F1':>6}  {'Brier':>6}"
    print(header)
    print("-" * 100)
    for r in rows:
        depth_label = "999 (∞)" if r["depth"] >= 999 else str(r["depth"])
        prec_str = f"{r['precision']:.3f} [{r['precision_ci'][0]:.2f},{r['precision_ci'][1]:.2f}]" if r['precision'] is not None else "n/a"
        rec_str = f"{r['recall']:.3f} [{r['recall_ci'][0]:.2f},{r['recall_ci'][1]:.2f}]" if r['recall'] is not None else "n/a"
        f1_str = f"{r['f1']:.3f}" if r['f1'] is not None else "n/a"
        br_str = f"{r['brier']:.3f}" if r['brier'] is not None else "n/a"
        print(f"{depth_label:>5}  {r['model_positives']:>6}  {r['tp']:>3}  {r['fp']:>3}  {prec_str:>20}  {rec_str:>20}  {f1_str:>6}  {br_str:>6}")
    print()

    # Identify best depth by F1
    best = max(rows, key=lambda r: (r["f1"] or -1))
    print(f"Best F1: depth={best['depth']} at F1={best['f1']:.3f}")

    # Write a summary JSON
    summary = {"depths": rows, "best_by_f1": best["depth"]}
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nScorecards: {args.out_dir}")


if __name__ == "__main__":
    main()
