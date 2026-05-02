"""Dump exact vLLM chat-completions payloads to JSONL — no inference.

For tuning the homelab vLLM server: replay workloads, profile token/char
budgets, experiment with sampling parameters, etc. Uses the same
build_request() the classifier uses, so the dumped payloads are byte-identical
to what would actually be sent.

Usage:
    python3 -m src.classify.dump_prompts \\
      --corpus-dir 'data/processed/apache/dev@cassandra.apache.org' \\
      --prompt-variant v2_elided \\
      --quote-depth 2 \\
      --out workloads/cassandra-2014-v2_elided.jsonl

Output: one JSON object per line, with fields:
  id              — corpus message ID (for traceability)
  prompt_variant  — the variant used to build the payload
  prompt_hash     — frozen hash of the prompt template + schema
  char_count_user — len(user message content)
  char_count_system — len(system prompt)
  payload         — the literal dict that would be POSTed to vLLM
                    (model, messages, temperature, max_tokens, logprobs,
                     top_logprobs, guided_json)

Replay example:
    while read -r line; do
      payload=$(echo "$line" | jq -c '.payload')
      curl -s -H 'Content-Type: application/json' \\
        -d "$payload" http://192.168.100.101:8080/v1/chat/completions
    done < workloads/cassandra-2014-v2_elided.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.classify.schedule_change_announcement import (
    PROMPT_VARIANTS,
    build_request,
    prompt_hash,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--prompt-variant", choices=PROMPT_VARIANTS, default="v2_elided",
                   help="Frozen variant per the classifier (default: v2_elided, the current operating point).")
    p.add_argument("--quote-depth", type=int, default=2,
                   help="Quote-depth filter applied for variants that use it (default: 2).")
    p.add_argument("--limit", type=int, default=None, help="Stop after N messages (for smoke testing).")
    args = p.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(args.corpus_dir.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"No corpus files matched {args.corpus_dir}")

    ph = prompt_hash(args.prompt_variant)
    print(f"Dumping {args.prompt_variant} payloads (hash {ph}) → {args.out}", file=sys.stderr)

    n_emitted = 0
    total_user_chars = 0
    total_system_chars = 0
    max_user_chars = 0
    max_user_id = None
    with args.out.open("w", encoding="utf-8") as out:
        for f in files:
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                msg = json.loads(line)
                payload = build_request(msg, quote_depth=args.quote_depth, prompt_variant=args.prompt_variant)
                user_content = payload["messages"][1]["content"]
                system_content = payload["messages"][0]["content"]
                record = {
                    "id": msg["id"],
                    "prompt_variant": args.prompt_variant,
                    "prompt_hash": ph,
                    "char_count_user": len(user_content),
                    "char_count_system": len(system_content),
                    "payload": payload,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                n_emitted += 1
                total_user_chars += len(user_content)
                total_system_chars += len(system_content)
                if len(user_content) > max_user_chars:
                    max_user_chars = len(user_content)
                    max_user_id = msg["id"]
                if args.limit and n_emitted >= args.limit:
                    break
            if args.limit and n_emitted >= args.limit:
                break

    print(f"\nDone. Emitted {n_emitted} payloads.", file=sys.stderr)
    print(f"  total user chars:   {total_user_chars:>12,}", file=sys.stderr)
    print(f"  total system chars: {total_system_chars:>12,} ({total_system_chars // n_emitted if n_emitted else 0} per request, identical across rows)", file=sys.stderr)
    print(f"  mean user chars:    {total_user_chars // n_emitted if n_emitted else 0:>12,}", file=sys.stderr)
    print(f"  max user chars:     {max_user_chars:>12,}  ({max_user_id})", file=sys.stderr)
    print(f"  approx tokens (rough ~2.5 char/tok for email): {(total_user_chars + total_system_chars) // (n_emitted * 2 if n_emitted else 1):,} per request", file=sys.stderr)


if __name__ == "__main__":
    main()
