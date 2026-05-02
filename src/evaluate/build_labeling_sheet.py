"""Construct the pool-and-extrapolate labeling sheet.

For a given predictions JSONL and corpus dir, produces a sheet containing:
  - All model-positives (the pool — exhaustively labeled)
  - A random sample of model-negatives (seed-fixed for reproducibility)

Sheet entries include the message body so labels can be applied without
chasing across files. Output is JSON Lines, one record per candidate,
with a 'sample_role' field ("pool" | "random_sample").
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def load_predictions(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_corpus(corpus_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in sorted(corpus_dir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                msg = json.loads(line)
                out[msg["id"]] = msg
    return out


def build(predictions_path: Path, corpus_dir: Path, sample_size: int, seed: int, out_path: Path) -> dict:
    preds = load_predictions(predictions_path)
    corpus = load_corpus(corpus_dir)

    pool = [p for p in preds if p["prediction"]]
    negs = [p for p in preds if not p["prediction"]]

    rng = random.Random(seed)
    sample = rng.sample(negs, min(sample_size, len(negs)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as out:
        for role, items in [("pool", pool), ("random_sample", sample)]:
            for p in items:
                msg = corpus.get(p["id"], {})
                record = {
                    "sample_role": role,
                    "id": p["id"],
                    "prediction": p["prediction"],
                    "p_positive": p["p_positive"],
                    "model_evidence_quote": p.get("evidence_quote"),
                    "model_rationale": p.get("rationale"),
                    "from_raw": msg.get("from_raw", ""),
                    "subject": msg.get("subject", ""),
                    "date": msg.get("date", ""),
                    "body_text": msg.get("body_text", ""),
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                n += 1
    return {"pool_size": len(pool), "sample_size": len(sample), "total_to_label": n, "seed": seed}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--predictions", type=Path, required=True)
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--sample-size", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    summary = build(args.predictions, args.corpus_dir, args.sample_size, args.seed, args.out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
