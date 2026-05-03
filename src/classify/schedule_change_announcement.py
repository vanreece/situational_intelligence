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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from src.classify.quote_extractor import extract_at_depth, extract_message_context, elide_quoted_lines
from src.structure.version_state import (
    VersionStateIndex,
    build_index_from_corpus,
    render_version_context_block,
)

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

# v2 rubric (si-d6m, frozen in pre-reg commit 3313c2a). Sharpens the boundary cases:
# - vote-failure rerolls of an already-planned release: NEGATIVE (procedural)
# - vote-period adjustments: NEGATIVE (mechanic, not date)
# - +1/-1 votes by themselves: NEGATIVE (procedural reply)
# - CRITICAL quoted-text rule: if evidence is in quoted lines, answer NEGATIVE
SYSTEM_PROMPT_V2 = """You are reviewing a single message from the Apache Cassandra developer mailing list (dev@cassandra.apache.org). Determine whether the message announces, proposes, or implies a change to a previously-stated date or version target for a release, milestone, or planned work.

The change must affect a substantive deliverable (a release date, a feature target version, a release cadence). Procedural mechanics around an in-flight release process — vote retries, vote-period adjustments, +1/-1 votes — are NOT schedule changes; they are the standard release process executing normally.

POSITIVE — the author IS announcing/proposing/implying a substantive schedule change:
- Explicit date changes ("I propose postponing release of 1.2.17 until next week")
- Version target shifts ("we're planning to move to file-based hint storage in 3.0", "it's too late for a schema change in 2.1")
- Release cadence proposals ("I'd love it if we could modify the C* release cycle to 4 months")
- Acknowledgments that a previously-stated timeline will not be met ("we still have a lot to do before X")
- Setting a new target date when a previous expectation existed
- Re-rolls that introduce a NEW version not previously planned (e.g., "let's do a 1.2.18" when 1.2.17 was the last announced)

NEGATIVE — these are NOT schedule changes:
- Vote-failure rerolls of an already-planned release ("vote closed; we'll re-roll once X is fixed") — the release was always planned to happen when the vote passed; one failed vote attempt is procedural, not a schedule change. The release is still in-flight on the same broad schedule.
- Vote-period adjustments ("I'll shorten the vote period to 48h", "extending the vote 24 more hours") — mechanic, not date.
- +1 / -1 votes by themselves, even when the parent vote announcement is in the thread — the vote reply is procedural.
- Discussion of current schedules without proposing changes ("X is on track")
- Initial schedule announcements when no prior expectation existed
- Pure technical discussion with no schedule reference

CRITICAL — quoted text rule:
If your evidence for a positive judgment would be a phrase that appears in the QUOTED part of the message (lines starting with > or otherwise marked as from an earlier message in the thread), the answer is NEGATIVE. Judge based on what THIS author wrote in THIS message, not what they are quoting from someone else. The author is referencing the quoted material, not asserting it.

Output strict JSON:
{
  "is_schedule_change_announcement": true | false,
  "evidence_quote": "<verbatim span from THIS author's new content (NOT quoted lines), or null if false>",
  "rationale": "<one-sentence explanation, including whether the evidence is in new content or quoted material if relevant>"
}"""

USER_TEMPLATE = """Message:
From: {from_raw}
Subject: {subject}
Date: {date}

{body_text}"""

# Variant B (new_with_marked_quoted): system prompt extension and structured user template.
# Frozen in the si-clz pre-reg (commit c364b64). Any change requires a new pre-reg.
SYSTEM_PROMPT_MARKED_SUFFIX = """

The user message below contains a NEW REPLY (this author's actual statement in this message) followed by QUOTED CONTEXT (text quoted from earlier messages, NOT this author's statement). Base your schedule-change judgment on the NEW REPLY only; the QUOTED CONTEXT is reference, not the author's claim."""

USER_TEMPLATE_MARKED = """Message:
From: {from_raw}
Subject: {subject}
Date: {date}

NEW REPLY (this author's statement):
{new_content}

QUOTED CONTEXT (from earlier messages, for reference only — NOT this author's statement):
{quoted_block}"""

EMPTY_NEW_CONTENT_PLACEHOLDER = "(no new content from this author in this message)"
EMPTY_QUOTED_PLACEHOLDER = "(no quoted context in this message)"

# v2_elided_tagged (si-qdf): same as v2_elided, but the user message is augmented
# with a VERSION CONTEXT block listing each version mentioned in this message and
# its release-process state-at-time of the message timestamp. Frozen in si-qdf
# pre-reg (commit c933d89). The version-state extraction is regex+state-machine,
# not LLM — see src/structure/version_state.py.
USER_TEMPLATE_V2_TAGGED = """Message:
From: {from_raw}
Subject: {subject}
Date: {date}

{version_context_block}

{body_text}"""

EMPTY_VERSION_CONTEXT_PLACEHOLDER = "VERSION CONTEXT: (no Cassandra versions mentioned in this message)"

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


PROMPT_VARIANTS = ("current_baseline", "new_only", "new_with_marked_quoted", "v2_strict", "v2_elided", "v2_elided_tagged")


def _system_prompt_for(variant: str) -> str:
    if variant == "new_with_marked_quoted":
        return SYSTEM_PROMPT + SYSTEM_PROMPT_MARKED_SUFFIX
    if variant in ("v2_strict", "v2_elided", "v2_elided_tagged"):
        return SYSTEM_PROMPT_V2
    return SYSTEM_PROMPT


def _user_template_for(variant: str) -> str:
    if variant == "new_with_marked_quoted":
        return USER_TEMPLATE_MARKED
    if variant == "v2_elided_tagged":
        return USER_TEMPLATE_V2_TAGGED
    return USER_TEMPLATE


def prompt_hash(variant: str = "current_baseline") -> str:
    h = hashlib.sha256()
    h.update(_system_prompt_for(variant).encode("utf-8"))
    h.update(b"\x00")
    h.update(_user_template_for(variant).encode("utf-8"))
    h.update(b"\x00")
    h.update(json.dumps(GUIDED_JSON_SCHEMA, sort_keys=True).encode("utf-8"))
    h.update(b"\x00")
    h.update(variant.encode("utf-8"))  # variants without prompt-text changes (new_only) still get a distinct hash
    return h.hexdigest()[:16]


MAX_BODY_CHARS = 60_000  # was 8000; bumped after si-qhz token-usage audit showed
                         # max prompt was 3.4K tokens (11% of 32K window). Empirically,
                         # email text tokenizes at ~2.5 chars/token (denser than 4 chars/token
                         # due to quoted-message syntax), so 60K chars ≈ 24K tokens, leaving
                         # ~8K headroom for system prompt + the 400-tok completion budget.
                         # 100K chars hit the 32K context limit on a 92K-char message.

def build_request(message: dict, quote_depth: int | None = None,
                  prompt_variant: str = "current_baseline",
                  *,
                  logprobs: bool = True,
                  top_logprobs: int = 10,
                  version_state_index: VersionStateIndex | None = None) -> dict:
    """Build the chat-completions payload.

    prompt_variant ∈ PROMPT_VARIANTS.
    Frozen variants per the si-clz pre-reg (commit c364b64) and si-qdf pre-reg
    (commit c933d89, adds v2_elided_tagged).

    For "current_baseline": legacy depth-filtering behavior (quote_depth applies).
    For "new_only": uses extract_message_context().new_content; quote_depth is ignored.
    For "new_with_marked_quoted": structured prompt with NEW REPLY / QUOTED CONTEXT
      sections; quote_depth is ignored.
    For "v2_strict": v2 system prompt + depth-filtered body (matches current_baseline shape).
    For "v2_elided": v2 system prompt + each quoted line content replaced with [QUOTED].
    For "v2_elided_tagged": v2_elided body + augmented user message with VERSION CONTEXT
      block listing each version mentioned in this message and its state-at-time.
      Requires `version_state_index` to be passed (built once per run).
    """
    if prompt_variant not in PROMPT_VARIANTS:
        raise ValueError(f"unknown prompt_variant: {prompt_variant}")

    from_raw = message.get("from_raw", "") or ""
    subject = message.get("subject", "") or ""
    date = message.get("date", "") or ""
    body = message.get("body_text", "") or ""

    if prompt_variant in ("current_baseline", "v2_strict"):
        # v2_strict uses the same body shape as current_baseline (depth-filtered);
        # the difference is the system prompt and the CRITICAL quoted-text rule.
        # The cheap-tier sees quoted material and is told via the rule to ignore it
        # for evidence purposes — this tests whether the rule reliably steers behavior.
        if quote_depth is not None:
            body = extract_at_depth(body, quote_depth)
        user_msg = USER_TEMPLATE.format(
            from_raw=from_raw, subject=subject, date=date,
            body_text=body[:MAX_BODY_CHARS],
        )
    elif prompt_variant == "v2_elided":
        # v2_elided uses the same v2 system prompt as v2_strict, but each quoted
        # line's content is replaced with [QUOTED]. Tests whether the v2 precision
        # shortfall is entirely caused by anchoring on strong quoted text.
        # quote_depth filters lines beyond depth N; surviving quoted lines get elided.
        depth = quote_depth if quote_depth is not None else 999
        body = elide_quoted_lines(body, max_depth=depth)
        user_msg = USER_TEMPLATE.format(
            from_raw=from_raw, subject=subject, date=date,
            body_text=body[:MAX_BODY_CHARS],
        )
    elif prompt_variant == "v2_elided_tagged":
        # si-qdf: v2_elided body shape + VERSION CONTEXT block prepended to body
        # in the user message. Tests whether typed version-state-at-time tags
        # recover the 3 dropped TPs (Op-9, Shuler, Ellis-1.2.17-takedown) lost
        # under v2_elided due to missing inter-message version-disambiguation.
        depth = quote_depth if quote_depth is not None else 999
        body = elide_quoted_lines(body, max_depth=depth)
        if version_state_index is not None:
            vc_block = render_version_context_block(message, version_state_index)
        else:
            vc_block = ""
        if not vc_block:
            vc_block = EMPTY_VERSION_CONTEXT_PLACEHOLDER
        user_msg = USER_TEMPLATE_V2_TAGGED.format(
            from_raw=from_raw, subject=subject, date=date,
            version_context_block=vc_block,
            body_text=body[:MAX_BODY_CHARS],
        )
    elif prompt_variant == "new_only":
        ctx = extract_message_context(body)
        new_content = ctx["new_content"] or EMPTY_NEW_CONTENT_PLACEHOLDER
        user_msg = USER_TEMPLATE.format(
            from_raw=from_raw, subject=subject, date=date,
            body_text=new_content[:MAX_BODY_CHARS],
        )
    else:  # new_with_marked_quoted
        ctx = extract_message_context(body)
        new_content = (ctx["new_content"] or EMPTY_NEW_CONTENT_PLACEHOLDER)[:MAX_BODY_CHARS // 2]
        if ctx["quoted_segments"]:
            quoted_block = "\n\n".join(
                f"[depth {seg['depth']}]\n{seg['text']}" for seg in ctx["quoted_segments"]
            )
        else:
            quoted_block = EMPTY_QUOTED_PLACEHOLDER
        # Budget: split MAX_BODY_CHARS between new_content and quoted_block.
        # new_content already capped at half above; give the rest to quoted_block.
        budget_for_quoted = MAX_BODY_CHARS - len(new_content) - 200  # 200 for template scaffolding
        if budget_for_quoted < 200:
            budget_for_quoted = 200
        quoted_block = quoted_block[:budget_for_quoted]
        user_msg = USER_TEMPLATE_MARKED.format(
            from_raw=from_raw, subject=subject, date=date,
            new_content=new_content,
            quoted_block=quoted_block,
        )

    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": _system_prompt_for(prompt_variant)},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0,
        "max_tokens": 400,
        "guided_json": GUIDED_JSON_SCHEMA,
    }
    if logprobs:
        payload["logprobs"] = True
        payload["top_logprobs"] = top_logprobs
    return payload


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
    """Parse the JSON content, tolerating markdown code fences and unclosed objects.

    vLLM's guided_json is best-effort; on some inputs the model still emits
    ```json ... ``` despite the schema constraint. Strip fences defensively.

    Additionally, vLLM occasionally truncates the closing brace of a guided_json
    output even with finish_reason=stop (observed on Op-10 in si-clz variant B,
    completion_tokens=119, well under the 400 max — vLLM bug, not a real
    truncation). When the JSON is otherwise complete, attempt to repair by
    appending closing braces/quotes.
    """
    msg = response["choices"][0]["message"]["content"]
    s = msg.strip()
    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1 :]
        if s.endswith("```"):
            s = s[: -3].rstrip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Try repairing common truncation: missing closing brace, possibly missing
        # closing quote on the trailing string field. Only attempt if the content
        # looks like an open JSON object that ends mid-value.
        repaired = s
        # If the last non-whitespace char isn't a closing brace, try appending one
        if not repaired.rstrip().endswith("}"):
            # If a string is open (odd number of unescaped quotes after the last colon),
            # close the string first
            try:
                return json.loads(repaired + "}")
            except json.JSONDecodeError:
                try:
                    return json.loads(repaired + '"}')
                except json.JSONDecodeError:
                    pass
        # Re-raise original error if no repair worked
        return json.loads(s)


def classify_one(message: dict, quote_depth: int | None = None,
                 prompt_variant: str = "current_baseline",
                 *,
                 logprobs: bool = True,
                 top_logprobs: int = 10,
                 version_state_index: VersionStateIndex | None = None) -> dict:
    payload = build_request(message, quote_depth=quote_depth, prompt_variant=prompt_variant,
                            logprobs=logprobs, top_logprobs=top_logprobs,
                            version_state_index=version_state_index)
    response = call_endpoint(payload)
    parsed = parse_message_content(response)
    prediction = bool(parsed["is_schedule_change_announcement"])
    if logprobs:
        p_pos, lp_debug = extract_p_positive(response, prediction)
    else:
        # Without logprobs, fall back to a hard 0.999/0.001 derived from the prediction.
        p_pos = 0.999 if prediction else 0.001
        lp_debug = {"reason": "logprobs_disabled"}
    return {
        "id": message["id"],
        "prediction": prediction,
        "p_positive": p_pos,
        "evidence_quote": parsed.get("evidence_quote"),
        "rationale": parsed.get("rationale", ""),
        "model_id": response.get("model") or MODEL_ID,
        "prompt_hash": prompt_hash(prompt_variant),
        "prompt_variant": prompt_variant,
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


def run(corpus_dir: Path, out_path: Path, limit: int | None = None,
        quote_depth: int | None = None,
        prompt_variant: str = "current_baseline",
        *,
        concurrency: int = 1,
        logprobs: bool = True,
        top_logprobs: int = 10) -> dict:
    """Classify all messages in corpus_dir, write predictions to out_path.

    Resumable: skips IDs already present in out_path.
    Concurrent: dispatches up to `concurrency` requests in flight against vLLM.
    `concurrency=1` preserves the original strictly-sequential behavior.

    Output ordering is non-deterministic when concurrency > 1 (whichever thread
    finishes first writes first), but each ID is processed exactly once.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(corpus_dir.glob("*.jsonl"))
    done = already_done_ids(out_path)
    if done:
        print(f"Resuming: {len(done)} ids already classified", file=sys.stderr)

    # Build version-state index once per run when needed.
    vs_index: VersionStateIndex | None = None
    if prompt_variant == "v2_elided_tagged":
        print("Building version-state index over corpus...", file=sys.stderr)
        vs_index = build_index_from_corpus(corpus_dir)
        print(f"  {len(vs_index.known_versions())} known versions indexed", file=sys.stderr)

    # Collect all messages to process up-front so we can dispatch concurrently
    # while still respecting --limit and resumability.
    to_process: list[dict] = []
    n_skipped = 0
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            msg = json.loads(line)
            if msg["id"] in done:
                n_skipped += 1
                continue
            to_process.append(msg)
            if limit and len(to_process) >= limit:
                break
        if limit and len(to_process) >= limit:
            break

    summary = {"processed": 0, "skipped": n_skipped, "errors": 0, "predictions": []}

    if not to_process:
        return summary

    write_lock = Lock()
    progress_lock = Lock()

    def _classify_and_write(msg: dict, out_fh) -> tuple[str, dict | None, Exception | None]:
        try:
            result = classify_one(
                msg, quote_depth=quote_depth, prompt_variant=prompt_variant,
                logprobs=logprobs, top_logprobs=top_logprobs,
                version_state_index=vs_index,
            )
        except Exception as e:
            return (msg["id"], None, e)
        with write_lock:
            out_fh.write(json.dumps(result, ensure_ascii=False) + "\n")
            out_fh.flush()
        return (msg["id"], result, None)

    with out_path.open("a", encoding="utf-8") as out:
        if concurrency == 1:
            # Strictly sequential; preserves the original wall-clock noise model
            # (see si-pfo). No threads, no executor overhead.
            for msg in to_process:
                mid, result, err = _classify_and_write(msg, out)
                with progress_lock:
                    if err is not None:
                        summary["errors"] += 1
                        print(f"  ERROR on {mid}: {err}", file=sys.stderr)
                    else:
                        summary["processed"] += 1
                        summary["predictions"].append((mid, result["prediction"], result["p_positive"]))
                        if summary["processed"] % 50 == 0:
                            print(f"  [{summary['processed']}] last id {mid}", file=sys.stderr)
        else:
            # Concurrent dispatch via thread pool. Each thread does its own
            # classify_one() call and writes its result under write_lock.
            # Saturation ceiling on the homelab is around concurrency=32-64;
            # higher values just add queueing latency without throughput gain.
            with ThreadPoolExecutor(max_workers=concurrency) as ex:
                futures = {ex.submit(_classify_and_write, msg, out): msg for msg in to_process}
                for fut in as_completed(futures):
                    mid, result, err = fut.result()
                    with progress_lock:
                        if err is not None:
                            summary["errors"] += 1
                            print(f"  ERROR on {mid}: {err}", file=sys.stderr)
                        else:
                            summary["processed"] += 1
                            summary["predictions"].append((mid, result["prediction"], result["p_positive"]))
                            if summary["processed"] % 50 == 0:
                                print(f"  [{summary['processed']}/{len(to_process)}] last id {mid}", file=sys.stderr)
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--limit", type=int, default=None, help="Stop after N predictions (for smoke testing)")
    p.add_argument("--quote-depth", type=int, default=None,
                   help="If set, filter body to lines with quote depth <= N before classifying. "
                        "Use a large value (e.g. 999) to keep everything explicitly. Default: no filtering. "
                        "Ignored unless --prompt-variant=current_baseline.")
    p.add_argument("--prompt-variant", choices=PROMPT_VARIANTS, default="current_baseline",
                   help="Frozen variants per the si-clz pre-reg (commit c364b64).")
    p.add_argument("--concurrency", type=int, default=32,
                   help="Number of concurrent in-flight requests to vLLM. Default 32 "
                        "(the homelab saturation point). Set to 1 for strictly sequential "
                        "dispatch (preserves the si-pfo noise model; ~7x slower).")
    p.add_argument("--no-logprobs", dest="logprobs", action="store_false", default=True,
                   help="Disable logprobs entirely. p_positive falls back to 0.999/0.001 "
                        "from the binary prediction. Predictions JSONL becomes ~98%% smaller. "
                        "Use for production runs that don't need calibration data.")
    p.add_argument("--top-logprobs", type=int, default=10,
                   help="Number of top alternative tokens per position when logprobs are on. "
                        "Default 10 preserves the existing extract_p_positive behavior; 2 is "
                        "the practical floor (still finds the alternative true/false token most "
                        "of the time) and shrinks responses ~70%%.")
    args = p.parse_args()
    print(f"Classifying messages from {args.corpus_dir} -> {args.out}", file=sys.stderr)
    print(f"Prompt variant: {args.prompt_variant}  hash: {prompt_hash(args.prompt_variant)}  quote_depth={args.quote_depth}", file=sys.stderr)
    print(f"Concurrency: {args.concurrency}  logprobs: {args.logprobs}  top_logprobs: {args.top_logprobs}", file=sys.stderr)
    t0 = time.time()
    summary = run(args.corpus_dir, args.out, limit=args.limit,
                  quote_depth=args.quote_depth, prompt_variant=args.prompt_variant,
                  concurrency=args.concurrency, logprobs=args.logprobs, top_logprobs=args.top_logprobs)
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Processed: {summary['processed']}, Skipped: {summary['skipped']}, Errors: {summary['errors']}", file=sys.stderr)
    n_pos = sum(1 for _, pred, _ in summary["predictions"] if pred)
    print(f"Model-positives in this run: {n_pos}/{summary['processed']}", file=sys.stderr)


if __name__ == "__main__":
    main()
