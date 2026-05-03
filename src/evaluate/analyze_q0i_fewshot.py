"""Score si-q0i v2_elided_fewshot against post-si-e5q expanded labels.

Excludes the 5 frozen example IDs from the eval pool (would be train-on-test).
Reports pool-direct precision/recall/F1 and per-target recovery for the 8
known frontier-positives.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

PRED   = REPO / "results/detector-runs/schedule_change_announcement/si-q0i/cassandra-2014-predictions-v2-elided-fewshot.jsonl"
LABELS = REPO / "labels/schedule_change_announcement/cassandra-2014-labels-v2.jsonl"
OUT    = REPO / "results/evals/schedule_change_announcement-q0i-fewshot/scorecard.json"

# Frozen example IDs (must be excluded from eval — train-on-test otherwise)
EXAMPLE_IDS = {
    "CAKkz8Q2_20vQSG3MW0SYqSTUGRrPD8ubL7kz+qkkeR+BRf_y5A@mail.gmail.com",
    "53B2F945.9000605@pbandjelly.org",
    "CAKkz8Q3nDn97ihVX5qYkceM7Ehm_WBBmDbTdMagxZkNK6Cz_zQ@mail.gmail.com",
    "CAKkz8Q07-06XA_P_PfwC5J4xWpwQVPqdA8PBnY+UshZE6KORhg@mail.gmail.com",
    "CAKkz8Q3tHQygxZuKgxuRmp7qP_KqbLA4Y83PJFCM5_C+Y2BV3Q@mail.gmail.com",
}

# 8 known frontier-positives (from si-2z6) — for per-target recovery analysis
TARGETS = {
    # 3 cheap-tier dropped TPs
    "CAKkz8Q2_20vQSG3MW0SYqSTUGRrPD8ubL7kz+qkkeR+BRf_y5A@mail.gmail.com": "Op-9 Sylvain 1.2.18 reroll",
    "53B2F945.9000605@pbandjelly.org":                                   "Shuler 1.2.18?",
    "CALdd-zhjaG1vrBvjXJPLA9Td5+Tq6Q15qE0xRgHBp3ES8aoTtg@mail.gmail.com":"Ellis 1.2.17 takedown",
    # 5 frontier discoveries (post-si-e5q labels)
    "CAKkz8Q1-HW5RnLhd+r2+vqLFPETnEQLLo8Rz7aYu2HMcCmr3Gw@mail.gmail.com":"1.2.15 announce",
    "CALdd-zim6kNmR7f_zcPVPqk0B2G919tTTATHiUofNvLZTAwm7A@mail.gmail.com":"Thrift freeze 2.1.0",
    "CAKkz8Q0tq-PTwRirY6Qmq27efDwRPEQfT37VMfssbvxC5_0x_g@mail.gmail.com":"1.2.18 vote announce",
    "CALdd-zjZ2MZu0bV9GMdO-u0RO4UN30P1TzY01s_BJFWY5NOZAg@mail.gmail.com":"2.1 rc3?",
    "CALamADKeQgPE28xJ39KWrFvR3YeRPL3A7n=X3TsEukHYbF2wBw@mail.gmail.com":"1.2.19 announce (last in series)",
}


def main():
    preds = {r["id"]: bool(r.get("prediction")) for r in (json.loads(l) for l in PRED.read_text().splitlines() if l.strip())}
    labels = [json.loads(l) for l in LABELS.read_text().splitlines() if l.strip()]

    n_examples_in_labels = sum(1 for l in labels if l["id"] in EXAMPLE_IDS)
    eval_labels = [l for l in labels if l["id"] not in EXAMPLE_IDS and l["label"] in ("positive", "negative")]

    tp = fp = fn = tn = 0
    tp_ids, fp_ids, fn_ids = [], [], []
    for l in eval_labels:
        pred = preds.get(l["id"])
        if pred is None: continue
        if l["label"] == "positive" and pred:
            tp += 1; tp_ids.append(l["id"])
        elif l["label"] == "positive" and not pred:
            fn += 1; fn_ids.append(l["id"])
        elif l["label"] == "negative" and pred:
            fp += 1; fp_ids.append(l["id"])
        elif l["label"] == "negative" and not pred:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # Per-target recovery
    target_status = {}
    for tid, name in TARGETS.items():
        if tid in EXAMPLE_IDS:
            target_status[tid] = {"name": name, "in_examples": True, "predicted": None}
        else:
            target_status[tid] = {
                "name": name,
                "in_examples": False,
                "predicted": preds.get(tid),
                "label": next((l["label"] for l in labels if l["id"] == tid), None),
            }

    n_model_pos = sum(1 for v in preds.values() if v)

    out = {
        "n_predictions": len(preds),
        "n_model_positives_total": n_model_pos,
        "n_labels_total": len(labels),
        "n_example_ids_in_labels": n_examples_in_labels,
        "n_eval_labels": len(eval_labels),
        "n_eval_pos": sum(1 for l in eval_labels if l["label"] == "positive"),
        "n_eval_neg": sum(1 for l in eval_labels if l["label"] == "negative"),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "tp_ids": tp_ids,
        "fp_ids": fp_ids,
        "fn_ids": fn_ids,
        "target_status": target_status,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print(f"Total predictions:           {out['n_predictions']}")
    print(f"Model-positives total:       {n_model_pos}")
    print(f"Labels total:                {out['n_labels_total']}")
    print(f"Example IDs in labels:       {n_examples_in_labels} (excluded from eval)")
    print(f"Eval labels:                 {out['n_eval_labels']} ({out['n_eval_pos']} POS / {out['n_eval_neg']} NEG)")
    print()
    print(f"TP: {tp}  FP: {fp}  FN: {fn}  TN: {tn}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1:        {f1:.4f}")
    print()
    print("Per-target recovery (known frontier-positives):")
    for tid, info in target_status.items():
        if info["in_examples"]:
            print(f"  [example, excluded from eval]  {info['name']}")
        else:
            mark = "✓" if info["predicted"] else "✗"
            print(f"  {mark} {info['name']:<35}  predicted={info['predicted']}, label={info['label']}")

    if fp_ids:
        print()
        print(f"FP ids (precision drops):")
        for fid in fp_ids:
            pred = next((r for r in (json.loads(l) for l in PRED.read_text().splitlines() if l.strip()) if r["id"] == fid), None)
            if pred:
                print(f"  {fid[:50]}: {pred.get('rationale','')[:140]}")


if __name__ == "__main__":
    main()
