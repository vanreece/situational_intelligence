"""si-qdf: analyze cheap-tier-v2_elided_tagged predictions vs OpusLabel-v2.

Mirrors src/evaluate/analyze_d6m_v2.py's structure but is scoped to the si-qdf
sub-experiment: a single new variant (v2_elided_tagged) compared against the
OpusLabel-v2 pool, with explicit attention to the 3 dropped TPs the variant
was designed to recover (Op-9 Sylvain "1.2.18", Shuler "1.2.18",
Ellis "1.2.17 takedown").

Outputs a scorecard JSON with:
  - pool-direct precision/recall/F1 (the honest numbers per si-d6m)
  - pool_and_extrapolate scorecard (for continuity with prior runs)
  - per-TP recovery analysis for the 3 named candidates
  - new-FP enumeration (model-positive in v2_elided_tagged that's labeled negative)
  - flips vs v2_elided baseline (pos↔neg deltas)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.evaluate.pool_and_extrapolate import evaluate, load_jsonl


# The 3 TPs the substrate is supposed to recover (per si-rrz Results).
TARGET_RECOVERIES = [
    {
        "id": "CAKkz8Q2_20vQSG3MW0SYqSTUGRrPD8ubL7kz+qkkeR+BRf_y5A@mail.gmail.com",
        "name": "Op-9 (Sylvain, 1.2.18 re-roll)",
    },
    {
        "id": "53B2F945.9000605@pbandjelly.org",
        "name": "Shuler (1.2.18 re-roll question)",
    },
    {
        "id": "CALdd-zhjaG1vrBvjXJPLA9Td5+Tq6Q15qE0xRgHBp3ES8aoTtg@mail.gmail.com",
        "name": "Ellis (1.2.17 takedown)",
    },
]


def pool_direct(predictions, labels):
    """Headline numbers, pool-direct only (no extrapolation).

    Recall here is tp / (tp + pool_fn), where pool_fn = labeled-positive items
    that the model classified negative. This matches the "honest pool" reading
    used in si-d6m / si-rrz. It's a *lower* bound on recall that's tight when
    the labeled pool overlaps the union of any-classifier model-positives well.
    """
    pred_by_id = {r["id"]: r for r in predictions}
    label_by_id = {r["id"]: r["label"] for r in labels}

    model_pos = {pid for pid, r in pred_by_id.items() if r["prediction"]}

    tp = 0
    fp = 0
    fn = 0
    tp_ids: list[str] = []
    fp_ids: list[str] = []
    fn_ids: list[str] = []
    for lid, lab in label_by_id.items():
        if lid not in pred_by_id:
            continue
        if lab not in ("positive", "negative"):
            continue
        is_pred_pos = pred_by_id[lid]["prediction"]
        if lab == "positive" and is_pred_pos:
            tp += 1
            tp_ids.append(lid)
        elif lab == "positive" and not is_pred_pos:
            fn += 1
            fn_ids.append(lid)
        elif lab == "negative" and is_pred_pos:
            fp += 1
            fp_ids.append(lid)

    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    if precision is None or recall is None or precision != precision or recall != recall:
        f1 = float("nan")
    elif (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    return {
        "model_positives_total": len(model_pos),
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "tp_ids": sorted(tp_ids),
        "fp_ids": sorted(fp_ids),
        "fn_ids": sorted(fn_ids),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tagged-preds", type=Path, required=True,
                    help="v2_elided_tagged predictions JSONL")
    ap.add_argument("--elided-preds", type=Path, required=True,
                    help="v2_elided baseline predictions JSONL (for flip diff)")
    ap.add_argument("--v2-labels", type=Path, required=True,
                    help="OpusLabel-v2 JSONL")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--corpus-size", type=int, default=731)
    ap.add_argument("--random-sample-size", type=int, default=100)
    args = ap.parse_args()

    tagged_preds_list = load_jsonl(args.tagged_preds)
    elided_preds_list = load_jsonl(args.elided_preds)
    v2_labels_list = load_jsonl(args.v2_labels)

    tagged_by_id = {r["id"]: r for r in tagged_preds_list}
    elided_by_id = {r["id"]: r for r in elided_preds_list}
    label_by_id = {r["id"]: r["label"] for r in v2_labels_list}

    # ---- Pool-direct (the honest headline) ----
    pd = pool_direct(tagged_preds_list, v2_labels_list)
    pd_elided = pool_direct(elided_preds_list, v2_labels_list)

    # ---- pool_and_extrapolate (for continuity with prior runs) ----
    sc_full = evaluate(
        predictions=tagged_preds_list, labels=v2_labels_list,
        corpus_size=args.corpus_size, random_sample_size=args.random_sample_size,
        predictions_path=str(args.tagged_preds), labels_path=str(args.v2_labels),
    )

    # ---- Target-recovery analysis ----
    recoveries = []
    for tgt in TARGET_RECOVERIES:
        rec = {"id": tgt["id"], "name": tgt["name"]}
        tagged = tagged_by_id.get(tgt["id"])
        elided = elided_by_id.get(tgt["id"])
        rec["v2_elided_pred"] = elided["prediction"] if elided else None
        rec["tagged_pred"] = tagged["prediction"] if tagged else None
        rec["tagged_p_pos"] = tagged.get("p_positive") if tagged else None
        rec["tagged_evidence_quote"] = tagged.get("evidence_quote") if tagged else None
        rec["tagged_rationale"] = (tagged.get("rationale") or "")[:400] if tagged else None
        rec["recovered"] = bool(tagged and tagged["prediction"]) and not (elided and elided["prediction"])
        rec["label_in_v2"] = label_by_id.get(tgt["id"])
        recoveries.append(rec)

    # ---- New FPs (positive in tagged + labeled negative + NOT positive in elided) ----
    new_fps = []
    new_pos = []  # positive in tagged that wasn't positive in elided
    for pid, r in tagged_by_id.items():
        if not r["prediction"]:
            continue
        elided = elided_by_id.get(pid)
        if elided and elided["prediction"]:
            continue  # not new
        new_pos.append({
            "id": pid,
            "evidence_quote": r.get("evidence_quote"),
            "rationale": (r.get("rationale") or "")[:300],
            "p_positive": r.get("p_positive"),
            "label_in_v2": label_by_id.get(pid),
        })
        if label_by_id.get(pid) == "negative":
            new_fps.append(new_pos[-1])

    # ---- Lost positives (positive in elided, negative in tagged) ----
    lost_pos = []
    for pid, r in elided_by_id.items():
        if not r["prediction"]:
            continue
        tagged = tagged_by_id.get(pid)
        if tagged and tagged["prediction"]:
            continue
        lost_pos.append({
            "id": pid,
            "elided_evidence_quote": r.get("evidence_quote"),
            "elided_rationale": (r.get("rationale") or "")[:300],
            "tagged_rationale": (tagged.get("rationale") or "")[:300] if tagged else None,
            "label_in_v2": label_by_id.get(pid),
        })

    # ---- Flip counts ----
    common_ids = set(tagged_by_id.keys()) & set(elided_by_id.keys())
    flips = {"agree_pos": 0, "agree_neg": 0, "elided_pos_tagged_neg": 0, "elided_neg_tagged_pos": 0}
    for pid in common_ids:
        ep = elided_by_id[pid]["prediction"]
        tp = tagged_by_id[pid]["prediction"]
        if ep and tp: flips["agree_pos"] += 1
        elif not ep and not tp: flips["agree_neg"] += 1
        elif ep and not tp: flips["elided_pos_tagged_neg"] += 1
        else: flips["elided_neg_tagged_pos"] += 1

    # ---- Decision-rule branch (per pre-reg) ----
    f1 = pd["f1"]
    prec = pd["precision"]
    if f1 > 0.85 and prec > 0.85:
        branch = "promote: F1 > 0.85 AND precision > 0.85 — typed-tag substrate earns its keep"
    elif 0.77 <= f1 <= 0.85:
        branch = "marginal: 0.77 <= F1 <= 0.85 — tags help but don't dominate"
    elif f1 < 0.77:
        branch = "regress: F1 < 0.77 — typed tags introduced more noise than signal"
    else:
        branch = "promote-precision-shortfall: F1 > 0.85 but precision <= 0.85"

    # ---- Falsifier checks ----
    n_tagged_pos = pd["model_positives_total"]
    n_total = len(tagged_preds_list)
    pct_pos = n_tagged_pos / n_total * 100
    falsifiers = {
        "tagged_fires_on_>50%": pct_pos > 50,
        "model_positives_pct": round(pct_pos, 2),
        "model_positives_count": n_tagged_pos,
        # We can't easily measure "version-state index has gaps" without ground truth
        # over the index itself, but we report known_versions count as a sanity hint.
        "n_known_versions_in_index": None,  # filled below if available from any pred record
        "recovery_with_precision_drop_>0.20": (
            sum(1 for r in recoveries if r["recovered"]) >= 1
            and (pd_elided["precision"] - pd["precision"]) > 0.20
        ),
    }

    summary = {
        "headline_pool_direct": {
            "model_positives": pd["model_positives_total"],
            "tp": pd["tp"], "fp": pd["fp"], "fn": pd["fn"],
            "precision": pd["precision"],
            "recall_pool": pd["recall"],
            "f1_pool": pd["f1"],
        },
        "headline_v2_elided_baseline": {
            "model_positives": pd_elided["model_positives_total"],
            "tp": pd_elided["tp"], "fp": pd_elided["fp"], "fn": pd_elided["fn"],
            "precision": pd_elided["precision"],
            "recall_pool": pd_elided["recall"],
            "f1_pool": pd_elided["f1"],
        },
        "decision_rule_branch": branch,
        "target_recoveries": recoveries,
        "n_recovered_of_3": sum(1 for r in recoveries if r["recovered"]),
        "new_positives_vs_v2_elided": new_pos,
        "new_fps_vs_v2_elided": new_fps,
        "lost_positives_vs_v2_elided": lost_pos,
        "flip_counts_vs_v2_elided": flips,
        "falsifier_checks": falsifiers,
        "pool_and_extrapolate_full": {
            "precision_pool": sc_full["precision_pool"],
            "recall_extrapolated": sc_full["recall_extrapolated"],
            "f1": sc_full["f1"],
            "brier_score": sc_full["brier_score"],
            "prediction_summary": sc_full["prediction_summary"],
        },
        "pool_direct_id_lists": {
            "tp_ids": pd["tp_ids"],
            "fp_ids": pd["fp_ids"],
            "fn_ids": pd["fn_ids"],
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Pretty headline
    print("=" * 90)
    print("si-qdf: v2_elided_tagged vs OpusLabel-v2 (pool-direct headline)")
    print("=" * 90)
    print(f"  model_positives: {pd['model_positives_total']}")
    print(f"  TP={pd['tp']}  FP={pd['fp']}  FN={pd['fn']}")
    print(f"  precision={pd['precision']:.3f}  recall={pd['recall']:.3f}  F1={pd['f1']:.3f}")
    print()
    print(f"v2_elided baseline (for comparison):")
    print(f"  TP={pd_elided['tp']}  FP={pd_elided['fp']}  FN={pd_elided['fn']}")
    print(f"  precision={pd_elided['precision']:.3f}  recall={pd_elided['recall']:.3f}  F1={pd_elided['f1']:.3f}")
    print()
    print(f"Decision-rule branch: {branch}")
    print()
    print(f"Target recoveries (3 dropped TPs):")
    for r in recoveries:
        recov = "RECOVERED" if r["recovered"] else "NOT recovered"
        print(f"  [{recov}] {r['name']}")
        print(f"      tagged_pred={r['tagged_pred']}  v2_elided_pred={r['v2_elided_pred']}  label={r['label_in_v2']}")
        if r["tagged_evidence_quote"]:
            print(f"      evidence: {r['tagged_evidence_quote'][:200]!r}")
        if r["tagged_rationale"]:
            print(f"      rationale: {r['tagged_rationale'][:200]}")
    print()
    print(f"Flips vs v2_elided: {flips}")
    print(f"New positives vs v2_elided: {len(new_pos)}  (new FPs: {len(new_fps)})")
    print(f"Lost positives vs v2_elided: {len(lost_pos)}")
    print()
    print(f"Falsifier checks:")
    for k, v in falsifiers.items():
        print(f"  {k}: {v}")
    print()
    print(f"Scorecard written to: {args.out}")


if __name__ == "__main__":
    main()
