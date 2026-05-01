"""Harvest Apache mailing list archives via lists.apache.org mbox API.

Fetches per-month mbox files for a given list and normalizes them to
JSONL with provenance metadata. Raw mbox files are preserved untouched
under data/raw/; normalized records go to data/processed/.

Usage:
    python -m src.harvest.apache_mbox --list dev --domain cassandra.apache.org \\
        --start 2014-01 --end 2014-12

The lists.apache.org mbox endpoint pattern is:
    https://lists.apache.org/api/mbox.lua?list=<list>&domain=<domain>&d=<YYYY-MM>
"""

from __future__ import annotations

import argparse
import email
import email.policy
import email.utils
import hashlib
import json
import mailbox
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HARVESTER_VERSION = "0.1.0"
USER_AGENT = f"situational-intelligence-harvester/{HARVESTER_VERSION} (research; contact: vanreece@gmail.com)"
MBOX_ENDPOINT = "https://lists.apache.org/api/mbox.lua"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


def month_range(start: str, end: str):
    """Yield 'YYYY-MM' strings inclusive from start to end."""
    s_year, s_month = (int(x) for x in start.split("-"))
    e_year, e_month = (int(x) for x in end.split("-"))
    y, m = s_year, s_month
    while (y, m) <= (e_year, e_month):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            m = 1
            y += 1


def fetch_mbox(list_name: str, domain: str, ym: str, dest: Path, force: bool = False) -> tuple[Path, str]:
    """Download a single month mbox to dest. Returns (path, source_url)."""
    url = f"{MBOX_ENDPOINT}?list={list_name}&domain={domain}&d={ym}"
    if dest.exists() and not force:
        return dest, url
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return dest, url


def _decode_part(part: email.message.Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def get_body_text(msg: email.message.Message) -> str:
    """Extract text/plain body from a (possibly multipart) message.

    Uses the legacy email API (get_payload(decode=True)) because mailbox.mbox
    returns mboxMessage which lacks the modern get_content() helper.
    """
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp.lower():
                text = _decode_part(part)
                if text:
                    return text
        return ""
    if msg.get_content_type() == "text/plain":
        return _decode_part(msg)
    return ""


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def synthesize_id(msg: email.message.Message, body: str) -> str:
    """Fallback stable id when Message-ID is missing."""
    h = hashlib.sha256()
    for key in ("From", "Date", "Subject"):
        h.update((msg.get(key, "") or "").encode("utf-8", errors="replace"))
        h.update(b"\x00")
    h.update(body[:4096].encode("utf-8", errors="replace"))
    return f"synth-{h.hexdigest()[:16]}"


def normalize_message(msg: email.message.Message, list_id: str, source_url: str, fetched_at: str) -> dict:
    body = get_body_text(msg)
    msg_id = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip().strip("<>")
    if not msg_id:
        msg_id = synthesize_id(msg, body)
    from_raw = msg.get("From", "")
    from_name, from_email = email.utils.parseaddr(from_raw)
    refs = [r.strip("<>") for r in (msg.get("References", "") or "").split() if r.strip()]
    in_reply_to = (msg.get("In-Reply-To", "") or "").strip().strip("<>") or None
    return {
        "id": msg_id,
        "list": list_id,
        "date": parse_date(msg.get("Date")),
        "from_name": from_name,
        "from_email": from_email,
        "from_raw": from_raw,
        "subject": msg.get("Subject", ""),
        "in_reply_to": in_reply_to,
        "references": refs,
        "body_text": body,
        "headers": {k: v for k, v in msg.items()},
        "provenance": {
            "source_url": source_url,
            "fetched_at": fetched_at,
            "harvester_version": HARVESTER_VERSION,
        },
    }


def normalize_mbox(mbox_path: Path, jsonl_path: Path, list_id: str, source_url: str) -> int:
    """Parse mbox file and write normalized JSONL. Returns message count."""
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()
    box = mailbox.mbox(str(mbox_path))
    count = 0
    with jsonl_path.open("w", encoding="utf-8") as out:
        for msg in box:
            record = normalize_message(msg, list_id, source_url, fetched_at)
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def harvest(list_name: str, domain: str, start: str, end: str, repo_root: Path, force: bool = False, sleep_s: float = 1.0) -> dict:
    list_id = f"{list_name}@{domain}"
    raw_dir = repo_root / "data" / "raw" / "apache" / list_id
    proc_dir = repo_root / "data" / "processed" / "apache" / list_id
    summary = {"list": list_id, "months": {}, "total_messages": 0}
    for ym in month_range(start, end):
        raw_path = raw_dir / f"{ym}.mbox"
        proc_path = proc_dir / f"{ym}.jsonl"
        try:
            _, source_url = fetch_mbox(list_name, domain, ym, raw_path, force=force)
            n = normalize_mbox(raw_path, proc_path, list_id, source_url)
            summary["months"][ym] = {"messages": n, "raw_bytes": raw_path.stat().st_size}
            summary["total_messages"] += n
            print(f"  {ym}: {n} messages ({raw_path.stat().st_size} bytes)", file=sys.stderr)
        except urllib.error.HTTPError as e:
            summary["months"][ym] = {"error": f"HTTP {e.code}"}
            print(f"  {ym}: HTTP {e.code}", file=sys.stderr)
        except Exception as e:
            summary["months"][ym] = {"error": str(e)}
            print(f"  {ym}: ERROR {e}", file=sys.stderr)
        time.sleep(sleep_s)
    return summary


def main():
    p = argparse.ArgumentParser(description="Harvest Apache mailing list archive via lists.apache.org")
    p.add_argument("--list", required=True, help="List name, e.g. 'dev'")
    p.add_argument("--domain", required=True, help="Domain, e.g. 'cassandra.apache.org'")
    p.add_argument("--start", required=True, help="YYYY-MM (inclusive)")
    p.add_argument("--end", required=True, help="YYYY-MM (inclusive)")
    p.add_argument("--force", action="store_true", help="Re-download even if mbox exists")
    p.add_argument("--sleep", type=float, default=1.0, help="Seconds between requests")
    p.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT), help="Repo root (default: auto)")
    args = p.parse_args()
    print(f"Harvesting {args.list}@{args.domain} {args.start}..{args.end}", file=sys.stderr)
    summary = harvest(args.list, args.domain, args.start, args.end, Path(args.repo_root), force=args.force, sleep_s=args.sleep)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
