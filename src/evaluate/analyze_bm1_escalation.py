"""Cost-tier escalation simulation (si-bm1).

Replay-on-data: combine cheap-tier predictions on confident calls with
frontier predictions on a borderline pool. Sweep multiple borderline
criteria (P0..P_full) and score each combined-prediction set against
the post-si-e5q expanded labels.

No LLM inference — purely a logical combination of existing prediction
files.

Outputs:
  results/evals/schedule_change_announcement-bm1-escalation/scorecard.json
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Set

REPO = Path(__file__).resolve().parents[2]

CHEAP_PRED  = REPO / "results/detector-runs/schedule_change_announcement/si-d6m/cassandra-2014-predictions-v2-elided.jsonl"
FRONT_PRED  = REPO / "results/detector-runs/schedule_change_announcement/si-2z6/cassandra-2014-predictions-frontier-v2-elided.jsonl"
LABELS      = REPO / "labels/schedule_change_announcement/cassandra-2014-labels-v2.jsonl"
CORPUS_DIR  = REPO / "data/processed/apache/dev@cassandra.apache.org"
OUT_DIR     = REPO / "results/evals/schedule_change_announcement-bm1-escalation"

VOTE_MARKER  = re.compile(r"\[VOTE\b", re.I)
PROPOSAL_SUBJ = re.compile(r"^proposal", re.I)
VER_XYZ      = re.compile(r"\b\d+\.\d+\.\d+\b")
RELEASE_KW   = re.compile(
    r"\b(re-?roll|take it down|takedown|postpone|shorten|cadence|LTS|cycle|i propose|proposal:|let's do a|move(d)? to)\b",
    re.I,
)


def load_jsonl(p: Path) -> List[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def load_corpus() -> Dict[str, dict]:
    out = {}
    for p in sorted(CORPUS_DIR.glob("2014-*.jsonl")):
        for line in p.read_text().splitlines():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def is_root(msg: dict) -> bool:
    s = (msg.get("subject") or "").lower()
    return not (s.startswith("re:") or s.startswith("fwd:"))


def define_pools(
    corpus: Dict[str, dict],
    cheap_neg_ids: Set[str],
) -> Dict[str, Set[str]]:
    """Return {pool_name: set of ids} for each borderline criterion."""
    pools: Dict[str, Set[str]] = {
        "P0_no_escalation": set(),
        "P1_narrow":        set(),
        "P2_substantive":   set(),
        "P3_broad":         set(),
        "P_full":           set(cheap_neg_ids),
    }
    for mid, m in corpus.items():
        if mid not in cheap_neg_ids:
            continue
        body = m.get("body_text", "") or ""
        subj = m.get("subject", "") or ""
        has_xyz = bool(VER_XYZ.search(body))
        has_kw  = bool(RELEASE_KW.search(body))
        is_vote_subj = bool(VOTE_MARKER.search(subj) or PROPOSAL_SUBJ.search(subj))
        # Vote-root literal: subject containing the literal "[VOTE]" tag (not [VOTE PASSED]/[VOTE CLOSED]/[VOTE FAILED])
        is_vote_root_literal = "[VOTE]" in subj.upper().replace("[VOTE PASSED]", "").replace("[VOTE CLOSED]", "").replace("[VOTE FAILED]", "")

        # P1: narrow — version + release-keyword in body, but NOT a literal [VOTE] thread root
        if has_xyz and has_kw and not is_vote_root_literal:
            pools["P1_narrow"].add(mid)
        # P2: substantive — vote/proposal subject + (root or body>800)
        if is_vote_subj and (is_root(m) or len(body) > 800):
            pools["P2_substantive"].add(mid)
        # P3: broad — any reply or root with vote/proposal subject
        if is_vote_subj:
            pools["P3_broad"].add(mid)
    return pools


def score(combined_pred: Dict[str, bool], labels: List[dict]) -> dict:
    """Pool-direct precision/recall/F1. Counts only labeled items."""
    label_map = {l["id"]: l["label"] for l in labels if l["label"] in ("positive", "negative")}
    tp = fp = fn = tn = 0
    tps, fps, fns = [], [], []
    for lid, lab in label_map.items():
        pred = combined_pred.get(lid)
        if pred is None:
            continue  # no prediction (shouldn't happen)
        if lab == "positive" and pred:
            tp += 1; tps.append(lid)
        elif lab == "positive" and not pred:
            fn += 1; fns.append(lid)
        elif lab == "negative" and pred:
            fp += 1; fps.append(lid)
        elif lab == "negative" and not pred:
            tn += 1
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return dict(
        tp=tp, fp=fp, fn=fn, tn=tn,
        precision=round(p, 4), recall=round(r, 4), f1=round(f1, 4),
        tp_ids=tps, fp_ids=fps, fn_ids=fns,
    )


def combine(cheap: Dict[str, dict], frontier: Dict[str, dict], pool_ids: Set[str]) -> Dict[str, bool]:
    out = {}
    for mid, c in cheap.items():
        c_pred = bool(c.get("prediction"))
        if mid in pool_ids and not c_pred:  # escalate cheap-NEG-in-pool to frontier
            f = frontier.get(mid)
            out[mid] = bool(f.get("prediction")) if f else c_pred
        else:
            out[mid] = c_pred
    return out


def main():
    cheap_recs    = load_jsonl(CHEAP_PRED)
    frontier_recs = load_jsonl(FRONT_PRED)
    labels        = load_jsonl(LABELS)
    corpus        = load_corpus()

    cheap     = {r["id"]: r for r in cheap_recs}
    frontier  = {r["id"]: r for r in frontier_recs}
    cheap_neg_ids = {mid for mid, r in cheap.items() if not r.get("prediction")}

    pools = define_pools(corpus, cheap_neg_ids)

    # Sanity: confidence-band check (key U3 finding to record)
    pp_dist = {"<0.01": 0, "0.01-0.10": 0, "0.10-0.50": 0, "0.50-0.90": 0, ">0.90": 0}
    for r in cheap_recs:
        pp = r.get("p_positive", 0)
        if pp < 0.01:    pp_dist["<0.01"] += 1
        elif pp < 0.10:  pp_dist["0.01-0.10"] += 1
        elif pp < 0.50:  pp_dist["0.10-0.50"] += 1
        elif pp < 0.90:  pp_dist["0.50-0.90"] += 1
        else:            pp_dist[">0.90"] += 1

    # Frontier baseline (no cheap involvement) — as reported by si-2z6
    frontier_pred_only = {mid: bool(r.get("prediction")) for mid, r in frontier.items()}
    frontier_score = score(frontier_pred_only, labels)

    # Cheap baseline (P0)
    cheap_pred_only = {mid: bool(r.get("prediction")) for mid, r in cheap.items()}
    cheap_score = score(cheap_pred_only, labels)

    # Sweep pools
    pool_results = {}
    target_ids = [
        # 3 known dropped TPs
        "CAKkz8Q2_20vQSG3MW0SYqSTUGRrPD8ubL7kz+qkkeR+BRf_y5A@mail.gmail.com",
        "53B2F945.9000605@pbandjelly.org",
        "CALdd-zhjaG1vrBvjXJPLA9Td5+Tq6Q15qE0xRgHBp3ES8aoTtg@mail.gmail.com",
        # 5 frontier discoveries
        "CAKkz8Q1-HW5RnLhd+r2+vqLFPETnEQLLo8Rz7aYu2HMcCmr3Gw@mail.gmail.com",
        "CALdd-zim6kNmR7f_zcPVPqk0B2G919tTTATHiUofNvLZTAwm7A@mail.gmail.com",
        "CAKkz8Q0tq-PTwRirY6Qmq27efDwRPEQfT37VMfssbvxC5_0x_g@mail.gmail.com",
        "CALdd-zjZ2MZu0bV9GMdO-u0RO4UN30P1TzY01s_BJFWY5NOZAg@mail.gmail.com",
        "CALamADKeQgPE28xJ39KWrFvR3YeRPL3A7n=X3TsEukHYbF2wBw@mail.gmail.com",
    ]
    for pname, pids in pools.items():
        combined = combine(cheap, frontier, pids)
        s = score(combined, labels)
        s["pool_name"] = pname
        s["pool_size"] = len(pids)
        s["frontier_calls_pct"] = round(100.0 * len(pids) / len(cheap), 2)
        s["targets_in_pool"] = sum(1 for t in target_ids if t in pids)
        s["targets_total"] = len(target_ids)
        pool_results[pname] = s

    out = {
        "n_cheap_predictions": len(cheap),
        "n_frontier_predictions": len(frontier),
        "n_labels_total": len(labels),
        "n_labels_pos":   sum(1 for l in labels if l["label"] == "positive"),
        "n_labels_neg":   sum(1 for l in labels if l["label"] == "negative"),
        "cheap_p_positive_distribution": pp_dist,
        "cheap_baseline_score": cheap_score,
        "frontier_baseline_score": frontier_score,
        "pool_results": pool_results,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "scorecard.json").write_text(json.dumps(out, indent=2))

    # Print summary table
    print(f"Labels: {out['n_labels_pos']} POS / {out['n_labels_neg']} NEG / {out['n_labels_total']} total")
    print()
    print(f"Cheap (P0 baseline):     P={cheap_score['precision']:.3f} R={cheap_score['recall']:.3f} F1={cheap_score['f1']:.3f}  [TP={cheap_score['tp']} FP={cheap_score['fp']} FN={cheap_score['fn']}]")
    print(f"Frontier (P_ceiling):    P={frontier_score['precision']:.3f} R={frontier_score['recall']:.3f} F1={frontier_score['f1']:.3f}  [TP={frontier_score['tp']} FP={frontier_score['fp']} FN={frontier_score['fn']}]")
    print()
    print(f"{'pool':<20}  {'size':>5}  {'%front':>7}  {'P':>5}  {'R':>5}  {'F1':>5}  {'TP/8 in pool':>14}")
    for pname in ["P0_no_escalation", "P1_narrow", "P2_substantive", "P3_broad", "P_full"]:
        r = pool_results[pname]
        print(f"{pname:<20}  {r['pool_size']:>5}  {r['frontier_calls_pct']:>6.2f}%  {r['precision']:>5.3f}  {r['recall']:>5.3f}  {r['f1']:>5.3f}  {r['targets_in_pool']:>3}/{r['targets_total']:>3}")


if __name__ == "__main__":
    main()
