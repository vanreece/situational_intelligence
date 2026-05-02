"""Eval harness for binary classifiers using pool-and-extrapolate sampling.

The pre-registered eval design for rare-positive binary classifiers
(see docs/experiment-log.md, schedule_change_announcement entry):

  1. Run classifier over the full corpus, save predictions + p_positive.
  2. Hand-label *every* model-positive (the "pool"), giving exact precision.
  3. Hand-label a random sample of model-negatives, extrapolating the
     false-negative rate to the unsampled negatives to estimate recall.

Inputs:
  predictions.jsonl  — one record per *all* corpus messages, fields:
                       id, prediction (bool), p_positive (float in [0,1]),
                       model_id, prompt_hash, predicted_at
  labels.jsonl       — one record per *labeled* message, fields:
                       id, label ("positive"|"negative"|"unsure"), notes (optional)

Output:
  scorecard.json     — direct precision, extrapolated recall, F1, Brier,
                       reliability bins, plus provenance.

The classifier function itself is not invoked here — this module operates
on already-saved predictions. Keeps the harness independent of which
model produced the predictions, and lets the same predictions be
re-evaluated against revised labels without re-running inference.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HARNESS_VERSION = "0.2.0"  # si-2t4: stratified FN estimation by sample_role


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion. Returns (lower, upper)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def f1_score(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def reliability_table(items: list[tuple[float, int]], n_bins: int = 10) -> list[dict]:
    """Bin (p_positive, label_int) pairs and report mean predicted vs actual frac per bin."""
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for p, y in items:
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, y))
    out = []
    for i, bin_items in enumerate(bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins
        if bin_items:
            mean_p = sum(p for p, _ in bin_items) / len(bin_items)
            frac_pos = sum(y for _, y in bin_items) / len(bin_items)
            out.append({
                "bin_lower": round(lo, 3),
                "bin_upper": round(hi, 3),
                "n": len(bin_items),
                "mean_predicted": round(mean_p, 4),
                "frac_positive": round(frac_pos, 4),
            })
        else:
            out.append({"bin_lower": round(lo, 3), "bin_upper": round(hi, 3), "n": 0})
    return out


def evaluate(
    predictions: list[dict],
    labels: list[dict],
    corpus_size: int,
    random_sample_size: int,
    pre_reg_commit: str | None = None,
    predictions_path: str | None = None,
    labels_path: str | None = None,
) -> dict:
    """Run the pool-and-extrapolate eval. Returns a scorecard dict."""
    pred_by_id = {r["id"]: r for r in predictions}
    label_by_id = {r["id"]: r for r in labels}

    # Sanity: labels referencing unknown predictions
    orphan_labels = [lid for lid in label_by_id if lid not in pred_by_id]
    if orphan_labels:
        print(f"WARN: {len(orphan_labels)} labels reference IDs not in predictions; skipping them", file=sys.stderr)

    # Bookkeeping
    model_positive_ids = {pid for pid, r in pred_by_id.items() if r["prediction"]}
    model_negative_ids = set(pred_by_id) - model_positive_ids

    labeled_pos = sum(1 for r in labels if r["label"] == "positive" and r["id"] in pred_by_id)
    labeled_neg = sum(1 for r in labels if r["label"] == "negative" and r["id"] in pred_by_id)
    labeled_unsure = sum(1 for r in labels if r["label"] == "unsure" and r["id"] in pred_by_id)

    # Direct precision over the model-positive pool
    pool_labels = [
        label_by_id[pid]["label"]
        for pid in model_positive_ids
        if pid in label_by_id and label_by_id[pid]["label"] in ("positive", "negative")
    ]
    tp = sum(1 for v in pool_labels if v == "positive")
    fp = sum(1 for v in pool_labels if v == "negative")
    pool_total = tp + fp
    if pool_total > 0:
        precision = tp / pool_total
        prec_lo, prec_hi = wilson_interval(tp, pool_total)
    else:
        precision, prec_lo, prec_hi = float("nan"), 0.0, 1.0

    # Stratified recall extrapolation (si-2t4 fix).
    #
    # Background on the bug:
    #   The original v0.1.0 harness counted FNs across ALL labeled items that
    #   intersected the current model_negative_ids. But the labeled pool was
    #   constructed in two strata (per the labels file's `sample_role` field):
    #     - `pool` / `pool_v2` / `pool_*`: exhaustive labeling of SOME classifier's
    #       model-positives. For ANY OTHER classifier, this stratum is biased
    #       (enriched for items the classifiers disagree on, hence enriched for
    #       likely-FN cases).
    #     - `random_sample`: uniform random sample of SOME classifier's model-
    #       negatives. This is the unbiased stratum for FN-rate estimation.
    #
    # Fix: count direct FNs in the pool stratum (we know the labels exactly),
    # and extrapolate FNs for the unlabeled remainder using the random_sample
    # stratum's FN-rate. Total FN = pool_direct_FN + extrapolated_unsampled_FN.
    # If a labels file has no sample_role, treat all labels as random_sample
    # (legacy behavior; matches v0.1.0 in that limit).
    pool_roles_prefixes = ("pool",)  # matches "pool", "pool_v2", "pool_relaxed_cap"
    random_role = "random_sample"

    def is_pool(role: str | None) -> bool:
        return role is not None and any(role.startswith(p) for p in pool_roles_prefixes)

    # Direct FN count: positives in the pool stratum that are model-negatives
    pool_fn = 0
    pool_labeled_negatives_in_model_neg = 0  # for diagnostics
    pool_role_present = False
    for lab in labels:
        role = lab.get("sample_role")
        if not is_pool(role):
            continue
        pool_role_present = True
        if lab["id"] not in model_negative_ids:
            continue
        if lab["label"] == "positive":
            pool_fn += 1
        elif lab["label"] == "negative":
            pool_labeled_negatives_in_model_neg += 1

    # Random-sample FN rate
    random_sample_labels = [
        lab["label"]
        for lab in labels
        if lab.get("sample_role") == random_role
        and lab["id"] in model_negative_ids
        and lab["label"] in ("positive", "negative")
    ]
    random_role_present = len(random_sample_labels) > 0

    # Legacy fallback: if NO sample_role metadata is present, treat all labeled
    # model-negatives as random_sample (matches v0.1.0 behavior).
    if not pool_role_present and not random_role_present:
        random_sample_labels = [
            label_by_id[mid]["label"]
            for mid in model_negative_ids
            if mid in label_by_id and label_by_id[mid]["label"] in ("positive", "negative")
        ]

    sample_n = len(random_sample_labels)
    sample_pos = sum(1 for v in random_sample_labels if v == "positive")
    if sample_n > 0:
        fn_rate = sample_pos / sample_n
        fn_lo, fn_hi = wilson_interval(sample_pos, sample_n)
    else:
        fn_rate, fn_lo, fn_hi = 0.0, 0.0, 1.0  # if no random sample, assume 0 unsampled FN (conservative for recall but at least defined)

    # Items in model_negatives that have NO label at all = unlabeled remainder
    n_model_negatives = len(model_negative_ids)
    n_labeled_model_negatives = sum(
        1 for mid in model_negative_ids
        if mid in label_by_id and label_by_id[mid]["label"] in ("positive", "negative", "unsure")
    )
    n_unsampled_model_negatives = n_model_negatives - n_labeled_model_negatives

    extrapolated_unsampled_fn = fn_rate * n_unsampled_model_negatives
    estimated_total_fn = pool_fn + extrapolated_unsampled_fn

    if not math.isnan(precision) and (tp + estimated_total_fn) > 0:
        recall = tp / (tp + estimated_total_fn)
        # CIs on recall now compose: pool_fn is exact (no uncertainty), random sample fn_rate has Wilson CI
        recall_lo = tp / (tp + pool_fn + fn_hi * n_unsampled_model_negatives) if (tp + pool_fn + fn_hi * n_unsampled_model_negatives) > 0 else 1.0
        recall_hi = tp / (tp + pool_fn + fn_lo * n_unsampled_model_negatives) if (tp + pool_fn + fn_lo * n_unsampled_model_negatives) > 0 else 1.0
        f1 = f1_score(precision, recall)
    else:
        recall, recall_lo, recall_hi, f1 = float("nan"), 0.0, 1.0, float("nan")

    # Brier + reliability over all labeled items with usable probabilities
    brier_items: list[tuple[float, int]] = []
    for lab in labels:
        if lab["id"] not in pred_by_id:
            continue
        if lab["label"] not in ("positive", "negative"):
            continue
        p = pred_by_id[lab["id"]].get("p_positive")
        if p is None:
            continue
        y = 1 if lab["label"] == "positive" else 0
        brier_items.append((float(p), y))
    if brier_items:
        brier = sum((p - y) ** 2 for p, y in brier_items) / len(brier_items)
    else:
        brier = float("nan")

    # Provenance from predictions metadata (assume consistent across rows)
    sample_pred = predictions[0] if predictions else {}
    return {
        "scorecard_version": HARNESS_VERSION,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "predictions_path": predictions_path,
        "labels_path": labels_path,
        "config": {
            "eval_type": "pool_and_extrapolate",
            "corpus_size": corpus_size,
            "random_sample_size": random_sample_size,
            "pre_reg_commit": pre_reg_commit,
        },
        "model": {
            "model_id": sample_pred.get("model_id"),
            "prompt_hash": sample_pred.get("prompt_hash"),
        },
        "label_summary": {
            "labeled_total": labeled_pos + labeled_neg + labeled_unsure,
            "labeled_positive": labeled_pos,
            "labeled_negative": labeled_neg,
            "labeled_unsure": labeled_unsure,
            "orphan_labels": len(orphan_labels),
        },
        "prediction_summary": {
            "total": len(predictions),
            "model_positives": len(model_positive_ids),
            "model_negatives": n_model_negatives,
        },
        "precision_pool": {
            "tp": tp,
            "fp": fp,
            "pool_labeled_total": pool_total,
            "pool_unlabeled": len(model_positive_ids) - pool_total,
            "precision": _round_or_nan(precision),
            "wilson_95_lower": round(prec_lo, 4),
            "wilson_95_upper": round(prec_hi, 4),
        },
        "recall_extrapolated": {
            "stratification": {
                "pool_role_present": pool_role_present,
                "random_role_present": random_role_present,
                "n_labeled_model_negatives": n_labeled_model_negatives,
                "n_unsampled_model_negatives": n_unsampled_model_negatives,
            },
            "pool_direct_fn": pool_fn,
            "random_sample_size": sample_n,
            "random_sample_positives": sample_pos,
            "fn_rate_in_unsampled": _round_or_nan(fn_rate),
            "fn_rate_wilson_95_lower": round(fn_lo, 4),
            "fn_rate_wilson_95_upper": round(fn_hi, 4),
            "extrapolated_unsampled_fn": _round_or_nan(extrapolated_unsampled_fn),
            "estimated_total_fn": _round_or_nan(estimated_total_fn),
            "recall": _round_or_nan(recall),
            "recall_95_lower": round(recall_lo, 4),
            "recall_95_upper": round(recall_hi, 4),
        },
        "f1": _round_or_nan(f1),
        "brier_score": {
            "value": _round_or_nan(brier),
            "n_used": len(brier_items),
        },
        "reliability_table": reliability_table(brier_items),
    }


def _round_or_nan(x: float, n: int = 4):
    return None if (isinstance(x, float) and math.isnan(x)) else round(x, n)


def main():
    p = argparse.ArgumentParser(description="Pool-and-extrapolate eval for binary classifiers")
    p.add_argument("--predictions", required=True, type=Path)
    p.add_argument("--labels", required=True, type=Path)
    p.add_argument("--corpus-size", required=True, type=int)
    p.add_argument("--random-sample-size", required=True, type=int)
    p.add_argument("--pre-reg-commit", default=None)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    predictions = load_jsonl(args.predictions)
    labels = load_jsonl(args.labels)
    scorecard = evaluate(
        predictions=predictions,
        labels=labels,
        corpus_size=args.corpus_size,
        random_sample_size=args.random_sample_size,
        pre_reg_commit=args.pre_reg_commit,
        predictions_path=str(args.predictions),
        labels_path=str(args.labels),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(scorecard, indent=2))


if __name__ == "__main__":
    main()
