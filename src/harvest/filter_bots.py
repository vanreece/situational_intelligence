"""Filter Apache mailing-list bot traffic from a normalized JSONL corpus.

Pure I/O preprocessing — no LLM. Drops messages whose `from_email` is
the JIRA cross-post alias `jira@apache.org` or whose domain is
`builds.apache.org` (Jenkins CI). Other bot-classes can be added with
new --drop-* flags as needed; current default reflects the rule frozen
in si-2wh's pre-reg.

Idempotent: re-running on a corpus dir overwrites the filtered output.

Usage:
    python -m src.harvest.filter_bots \
        --in  data/processed/apache/common-dev@hadoop.apache.org \
        --out data/processed/apache/common-dev@hadoop.apache.org-filtered
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def is_bot(rec: dict) -> bool:
    """Apache-list bot rule: JIRA alias OR Jenkins build domain.

    Frozen in si-2wh pre-reg (commit e3d461c). Any change requires a new pre-reg.
    """
    email = (rec.get("from_email") or "").lower()
    if email == "jira@apache.org":
        return True
    if email.endswith("@builds.apache.org"):
        return True
    return False


def filter_dir(in_dir: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"input_dir": str(in_dir), "output_dir": str(out_dir), "by_month": {}}
    total_in = total_kept = 0
    for src in sorted(in_dir.glob("*.jsonl")):
        dst = out_dir / src.name
        kept = dropped = 0
        with src.open() as f, dst.open("w") as g:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if is_bot(rec):
                    dropped += 1
                    continue
                g.write(json.dumps(rec) + "\n")
                kept += 1
        summary["by_month"][src.stem] = {"in": kept + dropped, "kept": kept, "dropped": dropped}
        total_in += kept + dropped
        total_kept += kept
    summary["total_in"] = total_in
    summary["total_kept"] = total_kept
    summary["total_dropped"] = total_in - total_kept
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_dir", type=Path, required=True)
    p.add_argument("--out", dest="out_dir", type=Path, required=True)
    args = p.parse_args()
    summary = filter_dir(args.in_dir, args.out_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
