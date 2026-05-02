"""Version-state-at-time index over a corpus of mailing-list messages.

si-qdf typed-tag first foray (pre-registered in commit c933d89, see
docs/experiment-log.md 2026-05-02 sub-experiment 3).

Purpose: for any (version, query_timestamp) pair, classify the version's
"release-process state" as one of:
  - pre_announcement    no [VOTE] for this version yet (at query_timestamp)
  - vote_active         [VOTE] subject seen, but no [VOTE PASSED] / [VOTE CLOSED]
  - vote_passed         [VOTE PASSED] for this version seen
  - vote_failed         [VOTE CLOSED] for this version seen and no later [VOTE PASSED]

The state machine walks the corpus in chronological order once and records,
for each version, the earliest timestamp at which each event occurred.
At query time, comparing query_timestamp to those event timestamps yields
the state.

This is intentionally a tiny, mechanical extraction layer — no LLM, just
regex + a state machine — built so v2_elided_tagged can show the cheap-tier
"1.2.18: pre_announcement" without having to read 100+ messages of context.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

# Cassandra-style version regex.
# Matches: 1.2.16, 2.0.10-rc1, 2.1, 3.0, 1.2.18, 2.1.0-tentative
# Requires word boundary on both sides; allows optional .patch and -suffix.
# Anchored to digit-dot-digit minimum so we don't match e.g. "5.0" in "5.0 GB".
# (False positives are filtered downstream by checking the version against the
# corpus-derived "known versions" set.)
VERSION_RE = re.compile(r"\b(\d\.\d(?:\.\d{1,2})?(?:-[A-Za-z0-9]+)?)\b")

# Subject patterns. Be permissive — the vote subjects in the Cassandra corpus
# are not perfectly consistent ("[VOTE]", "[VOTE] ", "[VOTE]:").
SUBJECT_VOTE_RE = re.compile(r"\[VOTE\]", re.IGNORECASE)
SUBJECT_VOTE_PASSED_RE = re.compile(r"\[VOTE\s*PASSED\]|\[PASSED\s*VOTE\]|\[RESULT\][^a-z]*pass",
                                    re.IGNORECASE)
SUBJECT_VOTE_CLOSED_RE = re.compile(r"\[VOTE\s*CLOSED\]|\[CLOSED\]", re.IGNORECASE)


def extract_versions_from_text(text: str) -> list[str]:
    """Return all version-like substrings in `text`, in order of appearance,
    deduplicated while preserving first-seen order."""
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in VERSION_RE.finditer(text):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def parse_ts(ts_str: str) -> datetime:
    """Parse an ISO timestamp string. Returns timezone-aware UTC."""
    # Python 3.11+ handles "Z" via fromisoformat. Cassandra dump uses "+00:00".
    s = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class VersionEvents:
    """Earliest-timestamp event log for a single version string."""
    first_mention_at: datetime | None = None
    vote_announced_at: datetime | None = None
    vote_passed_at: datetime | None = None
    vote_closed_at: datetime | None = None

    def update_first_mention(self, ts: datetime) -> None:
        if self.first_mention_at is None or ts < self.first_mention_at:
            self.first_mention_at = ts

    def update_event(self, attr: str, ts: datetime) -> None:
        cur = getattr(self, attr)
        if cur is None or ts < cur:
            setattr(self, attr, ts)


@dataclass
class VersionStateIndex:
    """Corpus-wide version event log, queryable by (version, timestamp)."""
    events: dict[str, VersionEvents] = field(default_factory=dict)

    def known_versions(self) -> set[str]:
        return set(self.events.keys())

    def state_at(self, version: str, query_ts: datetime) -> str:
        """Return the state string for `version` at `query_ts`.

        Resolution rules:
          - vote_passed if [VOTE PASSED] seen at or before query_ts
          - vote_failed if [VOTE CLOSED] seen at or before query_ts AND
            no [VOTE PASSED] at or before query_ts
          - vote_active if [VOTE] seen at or before query_ts but no
            [VOTE PASSED] or [VOTE CLOSED] yet at query_ts
          - pre_announcement otherwise (mention without vote, or unknown)
        """
        ev = self.events.get(version)
        if ev is None:
            return "pre_announcement"
        passed = ev.vote_passed_at is not None and ev.vote_passed_at <= query_ts
        closed = ev.vote_closed_at is not None and ev.vote_closed_at <= query_ts
        announced = ev.vote_announced_at is not None and ev.vote_announced_at <= query_ts
        if passed:
            return "vote_passed"
        if closed and not passed:
            return "vote_failed"
        if announced:
            return "vote_active"
        return "pre_announcement"

    def state_detail(self, version: str, query_ts: datetime) -> dict:
        """Return state plus the timestamp evidence underpinning it (for prompt context)."""
        state = self.state_at(version, query_ts)
        ev = self.events.get(version)
        detail = {"state": state, "version": version}
        if ev is None:
            return detail
        if state == "vote_passed" and ev.vote_passed_at is not None:
            detail["passed_at"] = ev.vote_passed_at.date().isoformat()
        elif state == "vote_failed" and ev.vote_closed_at is not None:
            detail["closed_at"] = ev.vote_closed_at.date().isoformat()
        elif state == "vote_active" and ev.vote_announced_at is not None:
            detail["announced_at"] = ev.vote_announced_at.date().isoformat()
        return detail


def _iter_messages(corpus_dir: Path) -> Iterator[dict]:
    """Yield messages from all *.jsonl files in `corpus_dir`."""
    for fpath in sorted(corpus_dir.glob("*.jsonl")):
        for line in fpath.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def build_index(messages: Iterable[dict]) -> VersionStateIndex:
    """Walk all messages chronologically, build version event log.

    Each message contributes:
      - first_mention_at for every version seen anywhere in subject+body
      - vote_announced_at for every version in a [VOTE] subject
      - vote_passed_at  for every version in a [VOTE PASSED] subject
      - vote_closed_at  for every version in a [VOTE CLOSED] subject

    Returns a VersionStateIndex.
    """
    # Materialize and sort by timestamp once. Stability across re-runs matters
    # because earliest-event-wins resolution is timestamp-driven.
    msg_list = []
    for msg in messages:
        date = msg.get("date") or ""
        if not date:
            continue
        try:
            ts = parse_ts(date)
        except ValueError:
            continue
        msg_list.append((ts, msg))
    msg_list.sort(key=lambda x: x[0])

    idx = VersionStateIndex()
    for ts, msg in msg_list:
        subject = msg.get("subject") or ""
        body = msg.get("body_text") or ""
        # Extract versions from subject + body. Subject is the canonical
        # source for vote events; body is fallback for first-mention.
        all_text = subject + "\n" + body
        for v in extract_versions_from_text(all_text):
            ev = idx.events.setdefault(v, VersionEvents())
            ev.update_first_mention(ts)

        # Subject-based event detection.
        is_vote_passed = bool(SUBJECT_VOTE_PASSED_RE.search(subject))
        is_vote_closed = bool(SUBJECT_VOTE_CLOSED_RE.search(subject)) and not is_vote_passed
        # [VOTE PASSED] also matches [VOTE]; treat passed as winning.
        is_vote_announced = bool(SUBJECT_VOTE_RE.search(subject)) and not is_vote_passed and not is_vote_closed

        if is_vote_announced or is_vote_passed or is_vote_closed:
            subj_versions = extract_versions_from_text(subject)
            for v in subj_versions:
                ev = idx.events.setdefault(v, VersionEvents())
                if is_vote_passed:
                    ev.update_event("vote_passed_at", ts)
                elif is_vote_closed:
                    ev.update_event("vote_closed_at", ts)
                elif is_vote_announced:
                    ev.update_event("vote_announced_at", ts)
    return idx


def build_index_from_corpus(corpus_dir: Path) -> VersionStateIndex:
    return build_index(_iter_messages(corpus_dir))


def versions_in_message(message: dict) -> list[str]:
    """Versions mentioned in this message's subject or body, deduped, in-order."""
    subject = message.get("subject") or ""
    body = message.get("body_text") or ""
    return extract_versions_from_text(subject + "\n" + body)


def render_version_context_block(message: dict, index: VersionStateIndex,
                                 known_versions_only: bool = True) -> str:
    """Render a `VERSION CONTEXT:` block for the v2_elided_tagged prompt.

    If `known_versions_only`, drop versions that don't appear in the corpus
    index (likely false-positive matches like '5.6' in '5.6 GB'). For the si-qdf
    foray we want to show the model only versions the corpus has any record of.

    Returns a multi-line string suitable for embedding in the user message,
    or an empty string if no versions to report.
    """
    versions = versions_in_message(message)
    if not versions:
        return ""
    try:
        query_ts = parse_ts(message.get("date") or "")
    except ValueError:
        return ""

    known = index.known_versions() if known_versions_only else None
    lines: list[str] = ["VERSION CONTEXT (state at this message's timestamp):"]
    rendered = 0
    for v in versions:
        if known is not None and v not in known:
            continue
        d = index.state_detail(v, query_ts)
        state = d["state"]
        if state == "vote_passed":
            tag = f"vote_passed (passed {d.get('passed_at', '?')})"
        elif state == "vote_failed":
            tag = f"vote_failed (closed {d.get('closed_at', '?')})"
        elif state == "vote_active":
            tag = f"vote_active (announced {d.get('announced_at', '?')})"
        else:
            tag = "pre_announcement (no [VOTE] yet)"
        lines.append(f"- {v}: {tag}")
        rendered += 1
    if rendered == 0:
        return ""
    return "\n".join(lines)


# ----------------------- self-test -----------------------

def _self_test() -> None:
    """Synthetic 5-message timeline. Exercises all four states."""
    msgs = [
        # 1. Discussion mentioning 1.2.18 — pre_announcement
        {"id": "m1", "date": "2014-06-15T10:00:00+00:00",
         "subject": "Re: thoughts on 1.2.18 cherry-picks",
         "body_text": "I think we should pull in CASSANDRA-1234 before 1.2.18."},
        # 2. [VOTE] for 1.2.17 — vote_active for 1.2.17
        {"id": "m2", "date": "2014-06-20T12:00:00+00:00",
         "subject": "[VOTE] Release Apache Cassandra 1.2.17",
         "body_text": "I propose the following artifacts for release as 1.2.17."},
        # 3. +1 vote — no event, just first_mention again
        {"id": "m3", "date": "2014-06-21T08:00:00+00:00",
         "subject": "Re: [VOTE] Release Apache Cassandra 1.2.17",
         "body_text": "+1"},
        # 4. [VOTE PASSED] for 1.2.17 — vote_passed
        {"id": "m4", "date": "2014-06-30T15:00:00+00:00",
         "subject": "[VOTE PASSED] Release Apache Cassandra 1.2.17",
         "body_text": "Thanks all. 1.2.17 is now released."},
        # 5. [VOTE CLOSED] for 2.0.9 (failed vote) — vote_failed
        {"id": "m5", "date": "2014-07-05T09:00:00+00:00",
         "subject": "[VOTE CLOSED] Release Apache Cassandra 2.0.9",
         "body_text": "Closing the 2.0.9 vote due to a regression."},
    ]
    idx = build_index(msgs)

    # Sanity: index knows about 1.2.17, 1.2.18, 2.0.9.
    assert "1.2.17" in idx.known_versions(), idx.known_versions()
    assert "1.2.18" in idx.known_versions(), idx.known_versions()
    assert "2.0.9" in idx.known_versions(), idx.known_versions()

    # State queries.
    t_early = parse_ts("2014-06-10T00:00:00+00:00")
    t_after_m1 = parse_ts("2014-06-16T00:00:00+00:00")
    t_after_m2 = parse_ts("2014-06-22T00:00:00+00:00")
    t_after_m4 = parse_ts("2014-07-01T00:00:00+00:00")
    t_after_m5 = parse_ts("2014-07-06T00:00:00+00:00")

    # 1.2.18 is mentioned in m1 but never voted on -> always pre_announcement
    assert idx.state_at("1.2.18", t_after_m1) == "pre_announcement", idx.state_at("1.2.18", t_after_m1)
    assert idx.state_at("1.2.18", t_after_m4) == "pre_announcement"

    # 1.2.17 progression
    assert idx.state_at("1.2.17", t_early) == "pre_announcement"
    assert idx.state_at("1.2.17", t_after_m2) == "vote_active", idx.state_at("1.2.17", t_after_m2)
    assert idx.state_at("1.2.17", t_after_m4) == "vote_passed"

    # 2.0.9 closed without passing -> vote_failed at t_after_m5
    assert idx.state_at("2.0.9", t_after_m5) == "vote_failed", idx.state_at("2.0.9", t_after_m5)
    # Before m5, 2.0.9 has never been mentioned -> pre_announcement
    assert idx.state_at("2.0.9", t_after_m4) == "pre_announcement"

    # Unknown version -> pre_announcement
    assert idx.state_at("9.9.9", t_after_m5) == "pre_announcement"

    # Render block: synthetic message at 2014-07-02 mentioning 1.2.17 and 1.2.18.
    test_msg = {
        "id": "test",
        "date": "2014-07-02T10:00:00+00:00",
        "subject": "Re: 1.2.17 follow-up",
        "body_text": "We should re-roll as 1.2.18.",
    }
    block = render_version_context_block(test_msg, idx)
    assert "1.2.17: vote_passed" in block, block
    assert "1.2.18: pre_announcement" in block, block

    print("OK: version_state self-test passed.")
    print("Rendered example block:")
    print(block)


if __name__ == "__main__":
    _self_test()
