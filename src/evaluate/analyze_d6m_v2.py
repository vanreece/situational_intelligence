"""si-d6m: analyze cheap-tier-v2 predictions against OpusLabels-v2 (and v1 for continuity).

Inputs:
  --v2-preds       cheap-tier predictions with v2_strict prompt
  --v2-labels      OpusLabels-v2 (relabeled by independent Opus subagent)
  --v1-labels      OpusLabels-v1 (the original labels)
  --v1-preds       cheap-tier predictions with v1 prompt at depth=2 (the existing run-0)
  --clz-summary    si-clz summary.json (for the 17 anchoring-fix + 11 regression sets)
  --out            output JSON

Outputs:
  - cheap-v2 vs Opus-v2 scorecard (the apples-to-apples test)
  - cheap-v2 vs Opus-v1 scorecard (continuity check)
  - Opus-v1 vs Opus-v2 label delta (how much did the rubric shift Opus's judgments?)
  - cheap-v1 vs cheap-v2 prediction delta (how much did v2 prompt change cheap-tier behavior?)
  - Per-OpusPositive coverage matrix (v1 OpusPositives across both label/prediction versions)
  - Quoted-text rule check: did cheap-v2 stop firing on the 17 si-clz anchoring-fix messages?
  - Falsifier check
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.evaluate.pool_and_extrapolate import evaluate, load_jsonl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-preds", type=Path, required=True)
    ap.add_argument("--v2-labels", type=Path, required=True)
    ap.add_argument("--v1-labels", type=Path, required=True)
    ap.add_argument("--v1-preds", type=Path, required=True)
    ap.add_argument("--clz-summary", type=Path, required=True)
    ap.add_argument("--corpus-size", type=int, default=731)
    ap.add_argument("--random-sample-size", type=int, default=100)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    v2_preds_list = load_jsonl(args.v2_preds)
    v1_preds_list = load_jsonl(args.v1_preds)
    v2_labels_list = load_jsonl(args.v2_labels)
    v1_labels_list = load_jsonl(args.v1_labels)

    v2_preds = {r["id"]: r for r in v2_preds_list}
    v1_preds = {r["id"]: r for r in v1_preds_list}
    v2_labels = {r["id"]: r["label"] for r in v2_labels_list}
    v1_labels = {r["id"]: r["label"] for r in v1_labels_list}

    # --- Scorecards ---
    sc_v2_v2 = evaluate(predictions=v2_preds_list, labels=v2_labels_list,
                        corpus_size=args.corpus_size, random_sample_size=args.random_sample_size,
                        predictions_path=str(args.v2_preds), labels_path=str(args.v2_labels))
    sc_v2_v1 = evaluate(predictions=v2_preds_list, labels=v1_labels_list,
                        corpus_size=args.corpus_size, random_sample_size=args.random_sample_size,
                        predictions_path=str(args.v2_preds), labels_path=str(args.v1_labels))
    sc_v1_v1 = evaluate(predictions=v1_preds_list, labels=v1_labels_list,
                        corpus_size=args.corpus_size, random_sample_size=args.random_sample_size,
                        predictions_path=str(args.v1_preds), labels_path=str(args.v1_labels))
    # Also: v1 cheap-tier scored against v2 labels — shows whether v1 was already aligned with v2 by accident
    sc_v1_v2 = evaluate(predictions=v1_preds_list, labels=v2_labels_list,
                        corpus_size=args.corpus_size, random_sample_size=args.random_sample_size,
                        predictions_path=str(args.v1_preds), labels_path=str(args.v2_labels))

    # --- Opus v1 vs v2 label delta ---
    common_label_ids = set(v1_labels.keys()) & set(v2_labels.keys())
    label_delta = []
    confusion = Counter()
    for mid in common_label_ids:
        confusion[(v1_labels[mid], v2_labels[mid])] += 1
        if v1_labels[mid] != v2_labels[mid]:
            label_delta.append({"id": mid, "v1": v1_labels[mid], "v2": v2_labels[mid]})
    v1_pos_set = {mid for mid, lbl in v1_labels.items() if lbl == "positive"}
    v2_pos_set = {mid for mid, lbl in v2_labels.items() if lbl == "positive"}

    # --- Cheap-tier v1 vs v2 prediction delta ---
    common_pred_ids = set(v1_preds.keys()) & set(v2_preds.keys())
    pred_flips = {"v1pos_v2neg": 0, "v1neg_v2pos": 0, "agree_pos": 0, "agree_neg": 0}
    flipped_pred_ids = []
    for mid in common_pred_ids:
        p1 = v1_preds[mid]["prediction"]
        p2 = v2_preds[mid]["prediction"]
        if p1 and not p2:
            pred_flips["v1pos_v2neg"] += 1
            flipped_pred_ids.append((mid, "v1pos_v2neg"))
        elif not p1 and p2:
            pred_flips["v1neg_v2pos"] += 1
            flipped_pred_ids.append((mid, "v1neg_v2pos"))
        elif p1 and p2:
            pred_flips["agree_pos"] += 1
        else:
            pred_flips["agree_neg"] += 1

    # --- Per-OpusPositive coverage (both v1 and v2 OpusPositives) ---
    all_opus_positives = sorted(v1_pos_set | v2_pos_set)
    coverage = []
    for mid in all_opus_positives:
        coverage.append({
            "id": mid,
            "in_v1_pos": mid in v1_pos_set,
            "in_v2_pos": mid in v2_pos_set,
            "v1_cheap_pred": v1_preds.get(mid, {}).get("prediction"),
            "v2_cheap_pred": v2_preds.get(mid, {}).get("prediction"),
            "v1_cheap_p_pos": v1_preds.get(mid, {}).get("p_positive"),
            "v2_cheap_p_pos": v2_preds.get(mid, {}).get("p_positive"),
        })

    # --- Quoted-text rule check: did cheap-v2 honor the rule on the 17 si-clz anchoring-fix messages? ---
    clz = json.loads(args.clz_summary.read_text())
    anchoring_fix_ids = [d["id"] for d in clz["c_to_ab_flip_diagnostics"]
                         if d["interpretation"].startswith("anchoring fix")]
    quoted_rule_check = []
    for mid in anchoring_fix_ids:
        v1p = v1_preds.get(mid, {})
        v2p = v2_preds.get(mid, {})
        quoted_rule_check.append({
            "id": mid,
            "v1_cheap_pred": v1p.get("prediction"),
            "v2_cheap_pred": v2p.get("prediction"),
            "v1_evidence": v1p.get("evidence_quote"),
            "v2_evidence": v2p.get("evidence_quote"),
            "v2_rationale": (v2p.get("rationale") or "")[:200],
        })
    quoted_rule_fixed = sum(1 for x in quoted_rule_check if x["v1_cheap_pred"] and not x["v2_cheap_pred"])

    # --- Falsifier checks ---
    n_pos_v2 = sum(1 for r in v2_preds_list if r["prediction"])
    n_pos_v2_pct = n_pos_v2 / len(v2_preds_list) * 100
    n_v1_v2_disagree = len(label_delta)
    falsifier_checks = {
        "cheap_v2_too_permissive_>50%": n_pos_v2_pct > 50,
        "cheap_v2_too_restrictive_<5%": n_pos_v2_pct < 5,
        "opus_v1_v2_disagree_>50%": n_v1_v2_disagree > 0.5 * len(common_label_ids),
        "model_positives_v2": n_pos_v2,
        "model_positives_v2_pct": round(n_pos_v2_pct, 2),
        "opus_v1_v2_disagree_count": n_v1_v2_disagree,
        "opus_v1_v2_disagree_pct": round(n_v1_v2_disagree / len(common_label_ids) * 100, 2),
    }

    summary = {
        "scorecards": {
            "cheap_v2_vs_opus_v2": _short_sc(sc_v2_v2),
            "cheap_v2_vs_opus_v1_continuity": _short_sc(sc_v2_v1),
            "cheap_v1_vs_opus_v1_baseline": _short_sc(sc_v1_v1),
            "cheap_v1_vs_opus_v2_alignment_check": _short_sc(sc_v1_v2),
        },
        "opus_label_delta": {
            "n_v1_positives": len(v1_pos_set),
            "n_v2_positives": len(v2_pos_set),
            "intersection": len(v1_pos_set & v2_pos_set),
            "v1_only": sorted(v1_pos_set - v2_pos_set),
            "v2_only": sorted(v2_pos_set - v1_pos_set),
            "confusion": {f"{a}->{b}": c for (a, b), c in confusion.items()},
            "label_changes": label_delta,
        },
        "cheap_pred_delta": {
            "v1_vs_v2_disagreement": {**pred_flips, "n_compared": len(common_pred_ids)},
            "flipped_ids": flipped_pred_ids[:50],  # first 50 for the JSON
        },
        "opus_positive_coverage": coverage,
        "quoted_text_rule_check": {
            "anchoring_fix_messages_from_clz": len(anchoring_fix_ids),
            "v2_correctly_resolves_to_negative": quoted_rule_fixed,
            "v2_still_anchors_positive": len(anchoring_fix_ids) - quoted_rule_fixed,
            "details": quoted_rule_check,
        },
        "falsifier_checks": falsifier_checks,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Pretty-print the headline
    print("=" * 100)
    print("si-d6m: v2 rubric — cheap-tier vs OpusLabels (v1 and v2)")
    print("=" * 100)
    print(f"{'comparison':>40}  {'model+':>7}  {'TP':>3}  {'FP':>3}  {'precision':>9}  {'recall':>7}  {'F1':>6}")
    for k, sc in summary["scorecards"].items():
        print(f"{k:>40}  {sc['model_positives']:>7}  {sc['tp']:>3}  {sc['fp']:>3}  "
              f"{sc['precision']:>9.3f}  {sc['recall']:>7.3f}  {sc['f1']:>6.3f}")

    print(f"\nOpus label delta (v1 → v2):")
    print(f"  v1 positives: {len(v1_pos_set)}")
    print(f"  v2 positives: {len(v2_pos_set)}")
    print(f"  intersection (still positive): {len(v1_pos_set & v2_pos_set)}")
    print(f"  v1-only (lost in v2): {len(v1_pos_set - v2_pos_set)}")
    print(f"  v2-only (gained in v2): {len(v2_pos_set - v1_pos_set)}")
    print(f"  Total label changes: {n_v1_v2_disagree} of {len(common_label_ids)} ({n_v1_v2_disagree / len(common_label_ids) * 100:.1f}%)")
    print(f"  Confusion ({{v1 -> v2}}: count): {dict(confusion)}")

    print(f"\nCheap-tier prediction delta (v1 → v2):")
    print(f"  Agree positive: {pred_flips['agree_pos']}, agree negative: {pred_flips['agree_neg']}")
    print(f"  v1pos→v2neg: {pred_flips['v1pos_v2neg']}, v1neg→v2pos: {pred_flips['v1neg_v2pos']}")

    print(f"\nQuoted-text rule check (17 si-clz anchoring-fix messages):")
    print(f"  v2 correctly resolves to negative: {quoted_rule_fixed}/{len(anchoring_fix_ids)}")
    print(f"  v2 still fires positive (rule ignored): {len(anchoring_fix_ids) - quoted_rule_fixed}")

    print(f"\nFalsifier checks:")
    for k, v in falsifier_checks.items():
        if isinstance(v, bool):
            print(f"  {'!!' if v else '  '} {k}: {v}")
        else:
            print(f"     {k}: {v}")

    print(f"\nSummary written to: {args.out}")


def _short_sc(sc):
    return {
        "f1": sc["f1"],
        "precision": sc["precision_pool"]["precision"],
        "recall": sc["recall_extrapolated"]["recall"],
        "brier": sc["brier_score"]["value"],
        "model_positives": sc["prediction_summary"]["model_positives"],
        "tp": sc["precision_pool"]["tp"],
        "fp": sc["precision_pool"]["fp"],
    }


if __name__ == "__main__":
    main()
