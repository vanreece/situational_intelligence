"""Concurrent replay of a dumped vLLM workload — for tuning experiments.

Reads a workload JSONL (produced by dump_prompts.py) and POSTs the payloads
concurrently to the vLLM endpoint, measuring latency and throughput.

Uses ThreadPoolExecutor wrapping stdlib urllib — no aiohttp/httpx dependency.
For I/O-bound HTTP work, threads are effectively concurrent; the GIL doesn't
matter here.

Usage:
    python3 -m src.classify.replay_concurrent \\
      --workload workloads/cassandra-2014-v2_elided.jsonl \\
      --concurrency 32

    # Optionally write responses for comparison with the sequential run:
    python3 -m src.classify.replay_concurrent \\
      --workload workloads/cassandra-2014-v2_elided.jsonl \\
      --concurrency 32 \\
      --responses-out /tmp/replay-responses.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ENDPOINT = "http://192.168.100.101:8080/v1/chat/completions"


def post_one(record: dict, timeout: float) -> dict:
    """POST a single payload, return diagnostics."""
    payload = record["payload"]
    started = time.monotonic()
    try:
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
        elapsed = time.monotonic() - started
        # Parse response for token usage if available
        try:
            parsed = json.loads(body)
            usage = parsed.get("usage", {})
        except Exception:
            usage = {}
        return {
            "id": record["id"],
            "ok": True,
            "status": status,
            "elapsed_s": elapsed,
            "response_bytes": len(body),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "raw_body": body if False else None,  # don't keep by default; pass through if needed
        }
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - started
        return {"id": record["id"], "ok": False, "status": e.code, "elapsed_s": elapsed,
                "error": f"HTTPError: {e.code} {e.reason}"}
    except Exception as e:
        elapsed = time.monotonic() - started
        return {"id": record["id"], "ok": False, "status": None, "elapsed_s": elapsed,
                "error": f"{type(e).__name__}: {e}"}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p / 100 * (len(s) - 1)))))
    return s[k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workload", type=Path, required=True)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None, help="Stop after N requests (for smoke testing)")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--responses-out", type=Path, default=None,
                    help="Optional path to write per-request response records (JSONL)")
    ap.add_argument("--progress-every", type=int, default=50)
    args = ap.parse_args()

    records = [json.loads(l) for l in args.workload.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        records = records[:args.limit]
    n_total = len(records)
    print(f"workload: {args.workload}  records: {n_total}  concurrency: {args.concurrency}", file=sys.stderr)

    out_fh = None
    out_lock = Lock()
    if args.responses_out:
        args.responses_out.parent.mkdir(parents=True, exist_ok=True)
        out_fh = args.responses_out.open("w", encoding="utf-8")

    results: list[dict] = []
    progress_lock = Lock()
    n_done = [0]
    n_err = [0]

    overall_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(post_one, rec, args.timeout): rec for rec in records}
        for fut in as_completed(futures):
            r = fut.result()
            results.append(r)
            with progress_lock:
                n_done[0] += 1
                if not r["ok"]:
                    n_err[0] += 1
                if n_done[0] % args.progress_every == 0:
                    elapsed = time.monotonic() - overall_start
                    rate = n_done[0] / elapsed
                    print(f"  [{n_done[0]}/{n_total}] elapsed={elapsed:.1f}s  rate={rate:.2f} req/s  errors={n_err[0]}",
                          file=sys.stderr)
            if out_fh is not None:
                with out_lock:
                    out_fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                    out_fh.flush()
    overall_elapsed = time.monotonic() - overall_start

    if out_fh is not None:
        out_fh.close()

    # Stats
    ok_results = [r for r in results if r["ok"]]
    latencies = [r["elapsed_s"] for r in ok_results]
    response_bytes = [r["response_bytes"] for r in ok_results if r.get("response_bytes")]
    prompt_tokens = [r["prompt_tokens"] for r in ok_results if r.get("prompt_tokens")]
    completion_tokens = [r["completion_tokens"] for r in ok_results if r.get("completion_tokens")]

    print(f"\n=== concurrent replay summary ===", file=sys.stderr)
    print(f"  records:            {n_total}", file=sys.stderr)
    print(f"  successful:         {len(ok_results)}", file=sys.stderr)
    print(f"  errors:             {n_err[0]}", file=sys.stderr)
    print(f"  concurrency:        {args.concurrency}", file=sys.stderr)
    print(f"  total wall clock:   {overall_elapsed:.2f}s", file=sys.stderr)
    print(f"  throughput:         {n_total / overall_elapsed:.2f} req/s", file=sys.stderr)
    if latencies:
        print(f"  per-request latency (s):", file=sys.stderr)
        print(f"    mean    {statistics.mean(latencies):.3f}", file=sys.stderr)
        print(f"    median  {statistics.median(latencies):.3f}", file=sys.stderr)
        print(f"    p50     {percentile(latencies, 50):.3f}", file=sys.stderr)
        print(f"    p90     {percentile(latencies, 90):.3f}", file=sys.stderr)
        print(f"    p99     {percentile(latencies, 99):.3f}", file=sys.stderr)
        print(f"    max     {max(latencies):.3f}", file=sys.stderr)
    if response_bytes:
        print(f"  response size (bytes): mean {int(statistics.mean(response_bytes)):,}, max {max(response_bytes):,}", file=sys.stderr)
    if prompt_tokens:
        print(f"  prompt_tokens (vLLM-reported): mean {int(statistics.mean(prompt_tokens)):,}, max {max(prompt_tokens):,}", file=sys.stderr)
    if completion_tokens:
        print(f"  completion_tokens (vLLM-reported): mean {int(statistics.mean(completion_tokens)):,}, max {max(completion_tokens):,}", file=sys.stderr)

    # Error breakdown
    errors_by_type: dict[str, int] = {}
    for r in results:
        if not r["ok"]:
            errors_by_type[r.get("error", "unknown")] = errors_by_type.get(r.get("error", "unknown"), 0) + 1
    if errors_by_type:
        print(f"\n  error breakdown:", file=sys.stderr)
        for err, n in sorted(errors_by_type.items(), key=lambda x: -x[1])[:5]:
            print(f"    {n:>4}  {err[:100]}", file=sys.stderr)


if __name__ == "__main__":
    main()
