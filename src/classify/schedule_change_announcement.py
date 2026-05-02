"""Binary classifier: schedule_change_announcement.

Pre-registered in commit 7d64413 (docs/experiment-log.md, 2026-05-02 entry).
Prompt and rubric are frozen — any change requires a new pre-reg.

Calls the homelab Qwen3-Coder vLLM endpoint with vLLM-extension guided_json
to force structured output, then extracts p_positive from the token-level
logprob at the boolean field's value position. Resumable: if predictions
JSONL already exists, skips ids that have a prediction recorded.

Output JSONL one record per message:
  {
    "id": "<message-id>",
    "prediction": true|false,
    "p_positive": 0.0..1.0,
    "evidence_quote": "..." | null,
    "rationale": "...",
    "model_id": "...",
    "prompt_hash": "<sha256 of system+user prompt template>",
    "predicted_at": "<ISO8601>",
    "raw_response": {...}     # for diagnostics — contains usage + logprobs preview
  }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from src.classify.quote_extractor import extract_at_depth

ENDPOINT = "http://192.168.100.101:8080/v1/chat/completions"
MODEL_ID = "btbtyler09/Qwen3-Coder-30B-A3B-Instruct-gptq-4bit"

SYSTEM_PROMPT = """You are reviewing a single message from the Apache Cassandra developer mailing list (dev@cassandra.apache.org). Determine whether the message announces or implies a change to a previously-stated or expected schedule for software work (releases, milestones, target dates, version cadence).

POSITIVE:
- Announcements that a release/version is delayed, advanced, or rescheduled
- Proposals to change a previously-stated target date ("should we move X to next week?")
- Acknowledgments that a previously-implied timeline will not be met
- Setting a new target date when a previous expectation existed

NEGATIVE:
- Discussion of current schedules without proposing changes ("X is on track")
- Status updates that don't affect a future date
- Setting an initial target with no prior expectation
- Pure technical discussion with no schedule reference

Output strict JSON:
{
  "is_schedule_change_announcement": true | false,
  "evidence_quote": "<verbatim span from message that justifies the answer, or null if false>",
  "rationale": "<one-sentence explanation>"
}"""

USER_TEMPLATE = """Message:
From: {from_raw}
Subject: {subject}
Date: {date}

{body_text}"""

GUIDED_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_schedule_change_announcement": {"type": "boolean"},
        "evidence_quote": {"type": ["string", "null"]},
        "rationale": {"type": "string"},
    },
    "required": ["is_schedule_change_announcement", "evidence_quote", "rationale"],
    "additionalProperties": False,
}


def prompt_hash() -> str:
    h = hashlib.sha256()
    h.update(SYSTEM_PROMPT.encode("utf-8"))
    h.update(b"\x00")
    h.update(USER_TEMPLATE.encode("utf-8"))
    h.update(b"\x00")
    h.update(json.dumps(GUIDED_JSON_SCHEMA, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:16]


MAX_BODY_CHARS = 60_000  # was 8000; bumped after si-qhz token-usage audit showed
                         # max prompt was 3.4K tokens (11% of 32K window). Empirically,
                         # email text tokenizes at ~2.5 chars/token (denser than 4 chars/token
                         # due to quoted-message syntax), so 60K chars ≈ 24K tokens, leaving
                         # ~8K headroom for system prompt + the 400-tok completion budget.
                         # 100K chars hit the 32K context limit on a 92K-char message.

def build_request(message: dict, quote_depth: int | None = None) -> dict:
    """Build the chat-completions payload.

    If quote_depth is None, the body is passed through as-is (legacy behavior).
    If quote_depth is an int, the body is filtered to lines whose quote-depth
    is <= quote_depth before truncation. This is per docs/experiment-log.md
    si-s9y depth-sweep entry — the sweep parameter, not part of the frozen
    pre-reg of si-qhz.
    """
    body = message.get("body_text", "") or ""
    if quote_depth is not None:
        body = extract_at_depth(body, quote_depth)
    user_msg = USER_TEMPLATE.format(
        from_raw=message.get("from_raw", "") or "",
        subject=message.get("subject", "") or "",
        date=message.get("date", "") or "",
        body_text=body[:MAX_BODY_CHARS],
    )
    return {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0,
        "max_tokens": 400,
        "logprobs": True,
        "top_logprobs": 10,
        "guided_json": GUIDED_JSON_SCHEMA,
    }


def call_endpoint(payload: dict, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def extract_p_positive(response: dict, prediction: bool) -> tuple[float, dict]:
    """Find the token logprobs at the position where the model emitted true|false.

    Returns (p_positive, debug_info). Falls back to a hard 0.999/0.001 if the
    boolean token can't be located in the logprobs trail.
    """
    choices = response.get("choices") or []
    if not choices:
        return (0.999 if prediction else 0.001, {"reason": "no_choices"})
    lp = choices[0].get("logprobs") or {}
    content = lp.get("content") or []
    target_tokens = {"true", "false", " true", " false"}
    for i, tok in enumerate(content):
        token_str = (tok.get("token") or "").strip()
        if token_str in {"true", "false"}:
            chosen_lp = tok["logprob"]
            other_lp = None
            for alt in tok.get("top_logprobs") or []:
                alt_str = (alt.get("token") or "").strip()
                if alt_str in {"true", "false"} and alt_str != token_str:
                    other_lp = alt["logprob"]
                    break
            if other_lp is None:
                # Approximate the unseen alternative as max of (top_logprob[-1], -10).
                seen = [a["logprob"] for a in tok.get("top_logprobs") or []]
                other_lp = (min(seen) - 1.0) if seen else -10.0
            chosen_p = math.exp(chosen_lp)
            other_p = math.exp(other_lp)
            denom = chosen_p + other_p
            if denom == 0:
                return (0.999 if prediction else 0.001, {"reason": "zero_denominator"})
            if token_str == "true":
                p_pos = chosen_p / denom
            else:
                p_pos = other_p / denom
            return (p_pos, {
                "boolean_token_index": i,
                "chosen_token": token_str,
                "chosen_logprob": chosen_lp,
                "other_logprob": other_lp,
                "other_seen_in_top": any(
                    (a.get("token") or "").strip() in {"true", "false"} and (a.get("token") or "").strip() != token_str
                    for a in tok.get("top_logprobs") or []
                ),
            })
    return (0.999 if prediction else 0.001, {"reason": "boolean_token_not_found"})


def parse_message_content(response: dict) -> dict:
    """Parse the JSON content, tolerating markdown code fences.

    vLLM's guided_json is best-effort; on some inputs the model still emits
    ```json ... ``` despite the schema constraint. Strip fences defensively.
    """
    msg = response["choices"][0]["message"]["content"]
    s = msg.strip()
    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1 :]
        if s.endswith("```"):
            s = s[: -3].rstrip()
    return json.loads(s)


def classify_one(message: dict, quote_depth: int | None = None) -> dict:
    payload = build_request(message, quote_depth=quote_depth)
    response = call_endpoint(payload)
    parsed = parse_message_content(response)
    prediction = bool(parsed["is_schedule_change_announcement"])
    p_pos, lp_debug = extract_p_positive(response, prediction)
    return {
        "id": message["id"],
        "prediction": prediction,
        "p_positive": p_pos,
        "evidence_quote": parsed.get("evidence_quote"),
        "rationale": parsed.get("rationale", ""),
        "model_id": response.get("model") or MODEL_ID,
        "prompt_hash": prompt_hash(),
        "quote_depth": quote_depth,
        "predicted_at": datetime.now(timezone.utc).isoformat(),
        "logprob_debug": lp_debug,
        "usage": response.get("usage"),
    }


def already_done_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    done = set()
    for line in out_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            done.add(json.loads(line)["id"])
        except (json.JSONDecodeError, KeyError):
            continue
    return done


def run(corpus_dir: Path, out_path: Path, limit: int | None = None, quote_depth: int | None = None) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(corpus_dir.glob("*.jsonl"))
    done = already_done_ids(out_path)
    if done:
        print(f"Resuming: {len(done)} ids already classified", file=sys.stderr)
    summary = {"processed": 0, "skipped": 0, "errors": 0, "predictions": []}
    with out_path.open("a", encoding="utf-8") as out:
        for f in files:
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                msg = json.loads(line)
                if msg["id"] in done:
                    summary["skipped"] += 1
                    continue
                try:
                    result = classify_one(msg, quote_depth=quote_depth)
                    out.write(json.dumps(result, ensure_ascii=False) + "\n")
                    out.flush()
                    summary["processed"] += 1
                    summary["predictions"].append((msg["id"], result["prediction"], result["p_positive"]))
                    if summary["processed"] % 50 == 0:
                        print(f"  [{summary['processed']}] last id {msg['id']}", file=sys.stderr)
                    if limit and summary["processed"] >= limit:
                        return summary
                except Exception as e:
                    summary["errors"] += 1
                    print(f"  ERROR on {msg['id']}: {e}", file=sys.stderr)
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--limit", type=int, default=None, help="Stop after N predictions (for smoke testing)")
    p.add_argument("--quote-depth", type=int, default=None,
                   help="If set, filter body to lines with quote depth <= N before classifying. "
                        "Use a large value (e.g. 999) to keep everything explicitly. Default: no filtering.")
    args = p.parse_args()
    print(f"Classifying messages from {args.corpus_dir} -> {args.out}", file=sys.stderr)
    print(f"Prompt hash: {prompt_hash()}  quote_depth={args.quote_depth}", file=sys.stderr)
    t0 = time.time()
    summary = run(args.corpus_dir, args.out, limit=args.limit, quote_depth=args.quote_depth)
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Processed: {summary['processed']}, Skipped: {summary['skipped']}, Errors: {summary['errors']}", file=sys.stderr)
    n_pos = sum(1 for _, pred, _ in summary["predictions"] if pred)
    print(f"Model-positives in this run: {n_pos}/{summary['processed']}", file=sys.stderr)


if __name__ == "__main__":
    main()
