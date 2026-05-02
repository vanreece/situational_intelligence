"""si-clz: analyze prompt-variant runs (current_baseline / new_only / new_with_marked_quoted).

Inputs:
  --baseline    run-0 from si-pfo (current_baseline at depth=2)
  --new-only    variant A predictions
  --marked      variant B predictions
  --labels      OpusLabel JSONL
  --out         summary JSON

Outputs (printed + written):
  - Per-variant scorecards (precision, recall, F1, Brier) using pool_and_extrapolate
  - Per-OpusPositive coverage matrix (which TPs each variant catches)
  - Per-message flip table: id × variant × prediction
  - Variant pairwise disagreement (A vs B vs C)
  - "anchoring fix" check: messages that flipped from C-positive to {A,B}-negative
    AND whose new_content lacks the schedule-keyword (suggests right-for-wrong-reason fix)
  - "regression" check: messages that flipped from C-positive to {A,B}-negative
    AND whose new_content has the schedule-keyword (substrate over-aggressive)
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from src.classify.quote_extractor import extract_message_context
from src.evaluate.pool_and_extrapolate import evaluate, load_jsonl

SCHEDULE_KEYWORDS = re.compile(
    r"\b(re-?roll|re-?start|reroll|postpone|delay|reschedule|push back|"
    r"shorten|extend the vote|release cycle|after 3\.0|too late|moved to|"
    r"slip|push out|next week|until)\b",
    re.IGNORECASE,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--new-only", type=Path, required=True)
    ap.add_argument("--marked", type=Path, required=True)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--corpus-dir", type=Path, required=True)
    ap.add_argument("--corpus-size", type=int, default=731)
    ap.add_argument("--random-sample-size", type=int, default=100)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    files = {"C_baseline": args.baseline, "A_new_only": args.new_only, "B_marked": args.marked}

    # Load predictions
    preds: dict[str, dict[str, dict]] = {}  # variant -> {id: record}
    for v, p in files.items():
        preds[v] = {r["id"]: r for r in load_jsonl(p)}

    # Per-variant scorecards
    labels = load_jsonl(args.labels)
    label_lookup = {r["id"]: r["label"] for r in labels}
    opus_positives = {mid for mid, lbl in label_lookup.items() if lbl == "positive"}
    scorecards = {}
    for v, p in files.items():
        sc = evaluate(
            predictions=load_jsonl(p),
            labels=labels,
            corpus_size=args.corpus_size,
            random_sample_size=args.random_sample_size,
            predictions_path=str(p),
            labels_path=str(args.labels),
        )
        scorecards[v] = sc

    # Per-OpusPositive coverage
    opus_pos_coverage = {}
    for mid in sorted(opus_positives):
        opus_pos_coverage[mid] = {v: preds[v].get(mid, {}).get("prediction") for v in files}

    # Variant disagreement (per pair: how many flips)
    pairwise = {}
    common_ids = set.intersection(*(set(preds[v].keys()) for v in files))
    for v1 in files:
        for v2 in files:
            if v1 >= v2:
                continue
            disagree = 0
            v1_pos_v2_neg = 0
            v1_neg_v2_pos = 0
            for mid in common_ids:
                p1 = preds[v1][mid]["prediction"]
                p2 = preds[v2][mid]["prediction"]
                if p1 != p2:
                    disagree += 1
                    if p1 and not p2:
                        v1_pos_v2_neg += 1
                    else:
                        v1_neg_v2_pos += 1
            pairwise[f"{v1} vs {v2}"] = {
                "n_compared": len(common_ids),
                "disagree": disagree,
                "disagree_pct": disagree / len(common_ids) * 100,
                f"{v1}_pos_{v2}_neg": v1_pos_v2_neg,
                f"{v1}_neg_{v2}_pos": v1_neg_v2_pos,
            }

    # Load message bodies for keyword-presence diagnostics
    msgs = {}
    for f in sorted(args.corpus_dir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            m = json.loads(line)
            msgs[m["id"]] = m

    # Diagnostics for messages that flipped C-positive → {A,B}-negative
    flip_diagnostics = []
    for mid in common_ids:
        c = preds["C_baseline"][mid]["prediction"]
        a = preds["A_new_only"][mid]["prediction"]
        b = preds["B_marked"][mid]["prediction"]
        if c and not (a or b):
            # Lost in BOTH variants — check whether new_content has schedule keyword
            msg = msgs.get(mid, {})
            ctx = extract_message_context(msg.get("body_text", ""))
            new_content = ctx["new_content"]
            kw_match = SCHEDULE_KEYWORDS.search(new_content)
            flip_diagnostics.append({
                "id": mid,
                "label": label_lookup.get(mid, "(unlabeled)"),
                "subject": (msg.get("subject", "") or "")[:60],
                "from": (msg.get("from_raw", "") or "")[:30],
                "new_content_chars": len(new_content),
                "schedule_keyword_in_new_content": kw_match.group(0) if kw_match else None,
                "c_p_pos": preds["C_baseline"][mid]["p_positive"],
                "c_evidence": preds["C_baseline"][mid].get("evidence_quote"),
                "interpretation": (
                    "anchoring fix (no kw in new) — substrate fixed a right-for-wrong-reason"
                    if not kw_match
                    else "regression (kw in new but lost) — substrate over-aggressive on this message"
                ),
            })

    # A vs B comparison: did the structural marker matter?
    a_b_disagree = sum(1 for mid in common_ids if preds["A_new_only"][mid]["prediction"] != preds["B_marked"][mid]["prediction"])
    a_pos = sum(1 for mid in common_ids if preds["A_new_only"][mid]["prediction"])
    b_pos = sum(1 for mid in common_ids if preds["B_marked"][mid]["prediction"])

    summary = {
        "scorecards": {v: {
            "f1": sc["f1"],
            "precision": sc["precision_pool"]["precision"],
            "recall": sc["recall_extrapolated"]["recall"],
            "brier": sc["brier_score"]["value"],
            "model_positives": sc["prediction_summary"]["model_positives"],
            "tp": sc["precision_pool"]["tp"],
            "fp": sc["precision_pool"]["fp"],
        } for v, sc in scorecards.items()},
        "opus_positive_coverage": opus_pos_coverage,
        "pairwise_disagreement": pairwise,
        "c_to_ab_flip_diagnostics": flip_diagnostics,
        "ab_summary": {
            "a_model_positives": a_pos,
            "b_model_positives": b_pos,
            "a_b_disagree": a_b_disagree,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Pretty-print
    print("=" * 100)
    print("si-clz: prompt-variant comparison (substrate first-test)")
    print("=" * 100)
    print(f"{'variant':>20}  {'model+':>7}  {'TP':>3}  {'FP':>3}  {'precision':>9}  {'recall':>7}  {'F1':>6}  {'Brier':>6}")
    print("-" * 100)
    for v in ("C_baseline", "A_new_only", "B_marked"):
        m = summary["scorecards"][v]
        print(f"{v:>20}  {m['model_positives']:>7}  {m['tp']:>3}  {m['fp']:>3}  "
              f"{m['precision']:>9.3f}  {m['recall']:>7.3f}  {m['f1']:>6.3f}  {m['brier']:>6.3f}")

    print(f"\nOpusPositive coverage matrix (14 OpusPositives):")
    print(f"{'#':>2}  {'C':>1}  {'A':>1}  {'B':>1}  id (truncated)")
    for i, mid in enumerate(sorted(opus_positives), 1):
        cov = opus_pos_coverage[mid]
        c = "✓" if cov["C_baseline"] else "✗"
        a = "✓" if cov["A_new_only"] else "✗"
        b = "✓" if cov["B_marked"] else "✗"
        print(f"{i:>2}  {c}  {a}  {b}  {mid[:70]}")

    print(f"\nVariant pairwise disagreement:")
    for pair, d in pairwise.items():
        print(f"  {pair}: {d['disagree']} of {d['n_compared']} ({d['disagree_pct']:.1f}%)")

    print(f"\nC→{{A,B}}-negative flip diagnostics ({len(flip_diagnostics)} messages):")
    for d in flip_diagnostics:
        kw = f" [kw='{d['schedule_keyword_in_new_content']}']" if d['schedule_keyword_in_new_content'] else ""
        print(f"  [{d['label']:>9}] {d['from']} / {d['subject']}")
        print(f"    {d['interpretation']}{kw}")
        if d['c_evidence']:
            print(f"    C anchored on: {d['c_evidence'][:100]}")

    print(f"\nA vs B summary: A model+={a_pos}, B model+={b_pos}, disagree={a_b_disagree} messages")
    print(f"Summary written to: {args.out}")


if __name__ == "__main__":
    main()
