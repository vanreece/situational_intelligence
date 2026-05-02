"""si-pfo: analyze 5 reruns + run-0 of schedule_change_announcement at depth=2.

Quantifies the per-run noise floor on classifier scorecards at temperature=0
with the homelab vLLM deployment. Pre-registered in docs/experiment-log.md
under "Quantify vLLM non-determinism at the prediction level".

Inputs:
  --run-0    Existing depth=2 predictions (the si-fnw winner).
  --reruns   Glob for the 5 fresh runs.
  --labels   Hand-labeled JSONL.
  --out      Output JSON (the durable summary).

Outputs (printed + written):
  - Per-run scorecard (precision, recall, F1, Brier) using pool_and_extrapolate.
  - F1 spread (max - min, stddev) across the 6 runs.
  - Per-message flip count distribution (out of 6 votes).
  - Cross-tab: flip count vs run-0 p_positive bin (borderline hypothesis).
  - Pairwise prediction agreement / Hamming distance matrix.
  - Flip direction asymmetry over all 15 pairwise comparisons.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

from src.evaluate.pool_and_extrapolate import evaluate, load_jsonl


def run_label_from_path(path: Path) -> str:
    m = re.search(r"run-(\d+)", path.name)
    if m:
        return f"run-{m.group(1)}"
    return path.stem


def per_message_predictions(run_files: list[tuple[str, Path]]) -> dict[str, dict[str, dict]]:
    """Returns {id: {run_label: {prediction, p_positive}}}."""
    table: dict[str, dict[str, dict]] = {}
    for label, path in run_files:
        for rec in load_jsonl(path):
            mid = rec["id"]
            table.setdefault(mid, {})[label] = {
                "prediction": bool(rec["prediction"]),
                "p_positive": float(rec.get("p_positive", 0.0)),
            }
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-0", type=Path, required=True)
    ap.add_argument("--reruns-dir", type=Path, required=True,
                    help="Directory containing cassandra-2014-predictions-depth-2-run-{1..5}.jsonl")
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--corpus-size", type=int, default=731)
    ap.add_argument("--random-sample-size", type=int, default=100)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rerun_paths = sorted(args.reruns_dir.glob("cassandra-2014-predictions-depth-2-run-*.jsonl"),
                         key=lambda p: int(re.search(r"run-(\d+)", p.name).group(1)))
    if not rerun_paths:
        raise SystemExit(f"No reruns matched in {args.reruns_dir}")

    run_files: list[tuple[str, Path]] = [("run-0", args.run_0)]
    run_files += [(run_label_from_path(p), p) for p in rerun_paths]
    run_labels = [lbl for lbl, _ in run_files]
    n_runs = len(run_files)

    # 1) Per-run scorecards
    labels = load_jsonl(args.labels)
    scorecards: dict[str, dict] = {}
    for label, path in run_files:
        preds = load_jsonl(path)
        sc = evaluate(
            predictions=preds,
            labels=labels,
            corpus_size=args.corpus_size,
            random_sample_size=args.random_sample_size,
            predictions_path=str(path),
            labels_path=str(args.labels),
        )
        scorecards[label] = sc

    # 2) F1 / precision / recall / Brier spreads
    f1s = [scorecards[l]["f1"] for l in run_labels if scorecards[l]["f1"] is not None]
    precisions = [scorecards[l]["precision_pool"]["precision"] for l in run_labels
                  if scorecards[l]["precision_pool"]["precision"] is not None]
    recalls = [scorecards[l]["recall_extrapolated"]["recall"] for l in run_labels
               if scorecards[l]["recall_extrapolated"]["recall"] is not None]
    briers = [scorecards[l]["brier_score"]["value"] for l in run_labels
              if scorecards[l]["brier_score"]["value"] is not None]
    model_pos = [scorecards[l]["prediction_summary"]["model_positives"] for l in run_labels]

    def spread(vals):
        if len(vals) < 2:
            return {"n": len(vals), "min": vals[0] if vals else None, "max": vals[0] if vals else None,
                    "mean": vals[0] if vals else None, "spread": 0.0, "stddev": 0.0}
        return {
            "n": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": statistics.mean(vals),
            "spread": max(vals) - min(vals),
            "stddev": statistics.stdev(vals) if len(vals) >= 2 else 0.0,
        }

    spreads = {
        "f1": spread(f1s),
        "precision": spread(precisions),
        "recall": spread(recalls),
        "brier": spread(briers),
        "model_positives": spread([float(x) for x in model_pos]),
    }

    # 3) Per-message flip count distribution
    table = per_message_predictions(run_files)
    flip_dist = Counter()  # k positive votes (0..n_runs) -> count of messages
    unstable_ids: list[dict] = []
    for mid, votes in table.items():
        if len(votes) != n_runs:
            # missing predictions in some runs (shouldn't happen but guard)
            continue
        n_pos = sum(1 for v in votes.values() if v["prediction"])
        flip_dist[n_pos] += 1
        if 0 < n_pos < n_runs:
            unstable_ids.append({
                "id": mid,
                "positive_votes": n_pos,
                "run_0_p_positive": votes.get("run-0", {}).get("p_positive"),
                "votes": {lbl: votes[lbl]["prediction"] for lbl in run_labels},
            })

    # 4) Borderline hypothesis: bin run-0 p_positive vs flip count
    # bins of 0.1 width
    flip_by_p_bin: dict[str, dict] = {}
    for rec in table.values():
        if len(rec) != n_runs:
            continue
        p = rec.get("run-0", {}).get("p_positive", 0.0)
        n_pos = sum(1 for v in rec.values() if v["prediction"])
        bin_idx = min(int(p * 10), 9)
        bin_key = f"[{bin_idx/10:.1f},{(bin_idx+1)/10:.1f})"
        d = flip_by_p_bin.setdefault(bin_key, {"total": 0, "stable_neg": 0, "stable_pos": 0, "unstable": 0})
        d["total"] += 1
        if n_pos == 0:
            d["stable_neg"] += 1
        elif n_pos == n_runs:
            d["stable_pos"] += 1
        else:
            d["unstable"] += 1

    # 5) Pairwise prediction agreement (Hamming distance)
    pairwise = []
    for i in range(n_runs):
        for j in range(i + 1, n_runs):
            li, lj = run_labels[i], run_labels[j]
            disagree = 0
            pos_to_neg = 0  # i positive, j negative
            neg_to_pos = 0  # i negative, j positive
            n_compared = 0
            for rec in table.values():
                if li not in rec or lj not in rec:
                    continue
                n_compared += 1
                pi, pj = rec[li]["prediction"], rec[lj]["prediction"]
                if pi != pj:
                    disagree += 1
                    if pi and not pj:
                        pos_to_neg += 1
                    else:
                        neg_to_pos += 1
            pairwise.append({
                "run_i": li, "run_j": lj,
                "n_compared": n_compared,
                "disagree": disagree,
                "disagree_pct": (disagree / n_compared * 100) if n_compared else 0.0,
                "i_pos_j_neg": pos_to_neg,
                "i_neg_j_pos": neg_to_pos,
            })

    # 6) Flip direction symmetry across all pairwise comparisons
    total_pos_to_neg = sum(p["i_pos_j_neg"] for p in pairwise)
    total_neg_to_pos = sum(p["i_neg_j_pos"] for p in pairwise)
    total_flips = total_pos_to_neg + total_neg_to_pos
    asymmetry = {
        "total_flips_across_15_pairs": total_flips,
        "pos_to_neg": total_pos_to_neg,
        "neg_to_pos": total_neg_to_pos,
        "pos_to_neg_pct": (total_pos_to_neg / total_flips * 100) if total_flips else 0.0,
    }

    summary = {
        "n_runs": n_runs,
        "run_labels": run_labels,
        "corpus_size": args.corpus_size,
        "labels_path": str(args.labels),
        "per_run_metrics": {
            l: {
                "f1": scorecards[l]["f1"],
                "precision": scorecards[l]["precision_pool"]["precision"],
                "recall": scorecards[l]["recall_extrapolated"]["recall"],
                "brier": scorecards[l]["brier_score"]["value"],
                "model_positives": scorecards[l]["prediction_summary"]["model_positives"],
                "tp": scorecards[l]["precision_pool"]["tp"],
                "fp": scorecards[l]["precision_pool"]["fp"],
            } for l in run_labels
        },
        "spreads": spreads,
        "flip_count_distribution": {str(k): flip_dist[k] for k in sorted(flip_dist.keys())},
        "n_unstable_messages": sum(1 for k, v in flip_dist.items() if 0 < k < n_runs for _ in range(v)),
        "unstable_messages": sorted(unstable_ids, key=lambda r: -(r.get("run_0_p_positive") or 0)),
        "flip_by_p_bin_run_0": flip_by_p_bin,
        "pairwise": pairwise,
        "flip_asymmetry": asymmetry,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Pretty-print summary table
    print("=" * 96)
    print(f"si-pfo: vLLM non-determinism quantification ({n_runs} runs at depth=2)")
    print("=" * 96)
    print(f"{'run':>8}  {'model+':>7}  {'TP':>3}  {'FP':>3}  {'precision':>9}  {'recall':>7}  {'F1':>6}  {'Brier':>6}")
    print("-" * 96)
    for l in run_labels:
        m = summary["per_run_metrics"][l]
        print(f"{l:>8}  {m['model_positives']:>7}  {m['tp']:>3}  {m['fp']:>3}  "
              f"{m['precision']:>9.3f}  {m['recall']:>7.3f}  {m['f1']:>6.3f}  {m['brier']:>6.3f}")
    print("-" * 96)
    s = summary["spreads"]
    print(f"F1: min={s['f1']['min']:.3f} max={s['f1']['max']:.3f} "
          f"spread={s['f1']['spread']:.3f} mean={s['f1']['mean']:.3f} stddev={s['f1']['stddev']:.4f}")
    print(f"precision: spread={s['precision']['spread']:.3f} stddev={s['precision']['stddev']:.4f}")
    print(f"recall: spread={s['recall']['spread']:.3f} stddev={s['recall']['stddev']:.4f}")
    print(f"Brier: spread={s['brier']['spread']:.3f}")
    print(f"model-positives: min={int(s['model_positives']['min'])} max={int(s['model_positives']['max'])} "
          f"spread={int(s['model_positives']['spread'])}")
    print()
    print("Per-message flip count distribution (votes_pos / 6 across 731 messages):")
    for k in sorted(int(x) for x in summary["flip_count_distribution"]):
        n = summary["flip_count_distribution"][str(k)]
        marker = "  ← stable-neg" if k == 0 else ("  ← stable-pos" if k == n_runs else "  ← unstable")
        print(f"  {k}/{n_runs}: {n:>4} messages{marker}")
    print()
    n_unstable = sum(v for k, v in flip_dist.items() if 0 < k < n_runs)
    print(f"Unstable messages (flipped at least once): {n_unstable}")
    print()
    print(f"Flip direction asymmetry: pos→neg={asymmetry['pos_to_neg']} "
          f"neg→pos={asymmetry['neg_to_pos']} ({asymmetry['pos_to_neg_pct']:.1f}% pos→neg)")
    print()
    print("Pairwise prediction disagreement (out of 731):")
    print(f"{'i':>8}  {'j':>8}  {'disagree':>8}  {'pct':>5}  {'pos→neg':>7}  {'neg→pos':>7}")
    for p in pairwise:
        print(f"{p['run_i']:>8}  {p['run_j']:>8}  {p['disagree']:>8}  "
              f"{p['disagree_pct']:>5.1f}  {p['i_pos_j_neg']:>7}  {p['i_neg_j_pos']:>7}")
    print()
    print(f"Borderline hypothesis test (run-0 p_positive bins vs stability):")
    print(f"{'bin':>13}  {'total':>5}  {'stable-':5}  {'stable+':5}  {'unstable':>8}  {'%unstable':>9}")
    for bin_key in sorted(flip_by_p_bin.keys()):
        b = flip_by_p_bin[bin_key]
        pct = (b["unstable"] / b["total"] * 100) if b["total"] else 0.0
        print(f"{bin_key:>13}  {b['total']:>5}  {b['stable_neg']:>7}  {b['stable_pos']:>7}  "
              f"{b['unstable']:>8}  {pct:>8.1f}%")
    print()
    print(f"Summary written to: {args.out}")


if __name__ == "__main__":
    main()
