"""Cost-tier escalation transfer test (si-03o) analysis.

Combines cheap-v3 predictions (full Hadoop common-dev filtered corpus) with
frontier-v3 predictions (450-item borderline pool) into the cost-tier
escalated combined prediction set, scored against the 76-label Hadoop pool.

Borderline criterion (adapted-P2 for Hadoop): cheap-v3 model-NEG ∩
subject contains [VOTE | [DISCUSS | thinking ahead | logistics for releasing
| proposal (case-insensitive, anywhere in subject).

Outputs:
  results/evals/schedule_change_announcement-si03o-escalation/scorecard.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Set

REPO = Path(__file__).resolve().parents[2]

CHEAP_PRED   = REPO / "results/detector-runs/schedule_change_announcement/v3/hadoop-common-dev-2014-predictions-v3-elided.jsonl"
FRONT_PRED   = REPO / "results/detector-runs/schedule_change_announcement/si-03o/hadoop-borderline-frontier-v3-elided.jsonl"
POOL_IDS     = REPO / "results/detector-runs/schedule_change_announcement/si-03o/borderline_pool_ids.json"
LABELS       = REPO / "labels/schedule_change_announcement/hadoop-common-dev-2014-labels-v2.jsonl"
CORPUS_DIR   = REPO / "data/processed/apache/common-dev@hadoop.apache.org-filtered"
OUT_DIR      = REPO / "results/evals/schedule_change_announcement-si03o-escalation"

VOTE_MARKER     = re.compile(r"\[VOTE\b", re.I)
DISCUSS_MARKER  = re.compile(r"\[DISCUSS\b", re.I)
THINKING_AHEAD  = re.compile(r"\bthinking ahead\b", re.I)
LOGISTICS       = re.compile(r"\blogistics for releasing\b", re.I)
PROPOSAL_SUBJ   = re.compile(r"\bproposal\b", re.I)


def load_jsonl(p: Path) -> List[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def load_corpus_subjects() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in sorted(CORPUS_DIR.glob("2014-*.jsonl")):
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            out[r["id"]] = (r.get("subject") or "").strip()
    return out


def is_borderline_subject(subject: str) -> bool:
    return bool(
        VOTE_MARKER.search(subject) or
        DISCUSS_MARKER.search(subject) or
        THINKING_AHEAD.search(subject) or
        LOGISTICS.search(subject) or
        PROPOSAL_SUBJ.search(subject)
    )


def score(combined_pred: Dict[str, bool], labels: List[dict]) -> dict:
    label_map = {l["id"]: l["label"] for l in labels if l["label"] in ("positive", "negative")}
    tp = fp = fn = tn = 0
    tp_ids: List[str] = []; fp_ids: List[str] = []; fn_ids: List[str] = []
    for lid, lab in label_map.items():
        pred = combined_pred.get(lid)
        if pred is None:
            continue
        if lab == "positive" and pred: tp += 1; tp_ids.append(lid)
        elif lab == "positive" and not pred: fn += 1; fn_ids.append(lid)
        elif lab == "negative" and pred: fp += 1; fp_ids.append(lid)
        elif lab == "negative" and not pred: tn += 1
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return dict(
        tp=tp, fp=fp, fn=fn, tn=tn,
        precision=round(p, 4), recall=round(r, 4), f1=round(f1, 4),
        tp_ids=tp_ids, fp_ids=fp_ids, fn_ids=fn_ids,
    )


def main() -> None:
    cheap_recs    = load_jsonl(CHEAP_PRED)
    front_recs    = load_jsonl(FRONT_PRED)
    labels        = load_jsonl(LABELS)
    pool_ids: Set[str] = set(json.loads(POOL_IDS.read_text()))
    subjects      = load_corpus_subjects()

    cheap     = {r["id"]: bool(r.get("prediction")) for r in cheap_recs}
    frontier  = {r["id"]: bool(r.get("prediction")) for r in front_recs}

    print(f"Cheap predictions:    {len(cheap)}")
    print(f"Frontier predictions: {len(frontier)} / {len(pool_ids)} pool items "
          f"({len(frontier)/len(pool_ids)*100:.1f}% complete)")
    print(f"Pool size:            {len(pool_ids)}")
    print(f"Labels:               {len(labels)} ({sum(1 for l in labels if l['label']=='positive')} POS / {sum(1 for l in labels if l['label']=='negative')} NEG)")
    print()

    # Build combined prediction: cheap-v3 by default; if id is in borderline pool AND frontier predicted, use frontier
    combined: Dict[str, bool] = {}
    for cid, c_pred in cheap.items():
        if cid in pool_ids and cid in frontier:
            combined[cid] = frontier[cid]
        else:
            combined[cid] = c_pred

    # Three scorecards
    cheap_only_score    = score(cheap, labels)
    combined_score      = score(combined, labels)
    # Frontier-on-pool only over labeled items in the pool (precision sanity)
    pool_only_combined: Dict[str, bool] = {cid: frontier[cid] for cid in frontier}
    frontier_pool_score = score(pool_only_combined, labels)

    # How many labeled items are in the pool?
    label_ids = {l["id"] for l in labels if l["label"] in ("positive", "negative")}
    labeled_in_pool = label_ids & pool_ids
    labeled_pos_in_pool = {l["id"] for l in labels if l["label"] == "positive"} & pool_ids

    # New POSes the combined predictor produces vs cheap-only (these are frontier overrides on cheap-NEG-in-pool)
    cheap_pos_ids    = {cid for cid, v in cheap.items() if v}
    combined_pos_ids = {cid for cid, v in combined.items() if v}
    new_combined_pos = combined_pos_ids - cheap_pos_ids
    lost_combined_pos = cheap_pos_ids - combined_pos_ids  # frontier overriding cheap-POS-in-pool? shouldn't happen because pool is cheap-NEGs
    new_combined_pos_unlabeled = sorted(new_combined_pos - label_ids)
    new_combined_pos_labeled = sorted(new_combined_pos & label_ids)

    out = {
        "n_cheap_predictions":    len(cheap),
        "n_frontier_predictions": len(frontier),
        "n_pool":                 len(pool_ids),
        "n_labels":               len(labels),
        "n_labeled_in_pool":      len(labeled_in_pool),
        "n_labeled_pos_in_pool":  len(labeled_pos_in_pool),
        "frontier_completeness":  round(len(frontier) / len(pool_ids), 4),
        "scores": {
            "cheap_v3_only":  cheap_only_score,
            "combined_cheap_v3_plus_frontier_v3_on_borderline": combined_score,
            "frontier_v3_on_borderline_only_score": frontier_pool_score,
        },
        "movement": {
            "new_combined_pos_total":      len(new_combined_pos),
            "new_combined_pos_labeled":    new_combined_pos_labeled,
            "new_combined_pos_unlabeled":  new_combined_pos_unlabeled,
            "lost_combined_pos":           sorted(lost_combined_pos),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "scorecard.json").write_text(json.dumps(out, indent=2))

    # Pretty print
    print(f"=== Hadoop common-dev: cheap-v3 only vs cheap-v3 + frontier-v3 escalation ===")
    print()
    print(f"{'metric':<14} {'cheap-only':>12} {'combined':>12} {'delta':>10}")
    for k in ("tp", "fp", "fn", "tn"):
        d = combined_score[k] - cheap_only_score[k]
        sign = "+" if d > 0 else ""
        print(f"{k:<14} {cheap_only_score[k]:>12} {combined_score[k]:>12} {sign}{d:>9}")
    for k in ("precision", "recall", "f1"):
        d = combined_score[k] - cheap_only_score[k]
        sign = "+" if d > 0 else ""
        print(f"{k:<14} {cheap_only_score[k]:>12.4f} {combined_score[k]:>12.4f} {sign}{d:>9.4f}")
    print()
    print(f"Pool fraction:  {len(pool_ids)/len(cheap)*100:.1f}% of corpus (frontier called on this many)")
    print(f"Labeled in pool: {len(labeled_in_pool)} of {len(label_ids)} labels ({len(labeled_pos_in_pool)} POS in pool)")
    print()
    print(f"Frontier overrides cheap-NEG → combined-POS:")
    print(f"  total: {len(new_combined_pos)}")
    print(f"  labeled: {new_combined_pos_labeled}")
    print(f"  unlabeled: {len(new_combined_pos_unlabeled)} (would need labeling for full eval)")

    # Movement detail: what does frontier disagree with cheap on, in pool?
    frontier_disagrees_in_pool = []
    for cid in pool_ids:
        if cid not in frontier:
            continue
        # cheap is NEG by pool construction; frontier flips to POS
        if frontier[cid]:
            frontier_disagrees_in_pool.append(cid)
    print(f"\nFrontier flipped {len(frontier_disagrees_in_pool)} pool items NEG→POS (out of {len(frontier)} frontier predictions on pool)")


if __name__ == "__main__":
    main()
