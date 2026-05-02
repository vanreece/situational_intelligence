"""Quote-aware extraction of email body content by quote depth.

Quote depth is the number of leading '>' characters on a line (allowing
optional whitespace between them: '>', '> >', '>>>' all count as depth>=1).

Filtering at depth N keeps lines whose depth is <= N. depth=0 means
"only the new reply"; depth=1 means "reply plus immediate parent"; etc.

We also strip common attribution lines like:
    "On Mon, Mar 11, 2014 at 12:00 PM, Jonathan Ellis <jbellis@gmail.com> wrote:"
when filtering to depth=0 — without the quoted block they introduce, the
attribution line is dangling noise. At depth >= 1, attribution lines are
kept because they contextualize what follows.

Edge cases handled empirically against the Cassandra dev@ 2014 corpus:
- Mixed '>' / '> >' / '>>>' styles (counted by total leading '>' chars)
- Outlook-style top-posting (new content first, blank line, attribution, quotes)
- Bottom-posting with inline quoting
- Signature blocks (preserved as new content; not classified separately)
- Empty messages (return empty)
"""

from __future__ import annotations

import re

# Lines that introduce a quoted block. Match liberally — these are noise at
# depth=0 since the content they introduce is gone.
ATTRIBUTION_PATTERNS = [
    re.compile(r"^On\b.+\bwrote:\s*$"),
    re.compile(r"^On\b.+,.+wrote:\s*$"),
    re.compile(r"^.+\bwrote\s+on\b.+:\s*$"),
    re.compile(r"^-{3,}\s*Original\s+[Mm]essage\s*-{3,}\s*$"),
    re.compile(r"^From:\s+.+$"),  # Outlook-style; only if part of header block
]


def quote_depth(line: str) -> int:
    """Number of leading '>' characters in a line (with optional whitespace)."""
    s = line.lstrip()
    depth = 0
    while s.startswith(">"):
        depth += 1
        s = s[1:].lstrip()
    return depth


def is_attribution(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return any(p.match(s) for p in ATTRIBUTION_PATTERNS)


# Signature boundary per RFC 3676: "-- " (dash-dash-space) on its own line.
# Some mailers also emit "--" without trailing space; accept both leniently.
_SIG_BOUNDARY = re.compile(r"^--\s*$")


def extract_message_context(body: str) -> dict:
    """Split a message body into structural components for the MessageContext substrate.

    Returns a dict with:
      - new_content (str): lines this author wrote in this message — depth-0 lines,
        attribution scaffolding stripped, signature stripped. Blank lines collapsed.
      - quoted_segments (list of dict): each {depth: int, text: str} — contiguous
        runs of same-depth quoted lines, in order of appearance. Adjacent runs of
        different depth become separate segments (the depth shift is meaningful).
      - attribution_lines (list of str): the "On X, Y wrote:" / "Original Message"
        markers found at depth 0, preserved in order of appearance.
      - signature (str | None): everything from the "-- " boundary to end of body,
        if present. The boundary line itself is NOT included.

    This function does NOT lose information — concatenating attribution_lines (with
    interleaved blank lines), quoted_segments (in order), new_content, and signature
    reconstructs roughly the original body. Designed for the prompt-variant test
    in si-clz: the classifier picks which fields to feed the model.
    """
    if not body:
        return {"new_content": "", "quoted_segments": [], "attribution_lines": [], "signature": None}

    # Split out signature first (RFC 3676 boundary)
    lines = body.splitlines()
    sig_idx = None
    for i, line in enumerate(lines):
        if _SIG_BOUNDARY.match(line):
            sig_idx = i
            break
    if sig_idx is not None:
        body_lines = lines[:sig_idx]
        signature = "\n".join(lines[sig_idx + 1 :]).strip() or None
    else:
        body_lines = lines
        signature = None

    new_lines: list[str] = []
    attribution_lines: list[str] = []
    quoted_segments: list[dict] = []
    current_seg_depth: int | None = None
    current_seg_lines: list[str] = []

    def flush_seg():
        nonlocal current_seg_depth, current_seg_lines
        if current_seg_lines and current_seg_depth is not None:
            text = "\n".join(current_seg_lines).strip()
            if text:
                quoted_segments.append({"depth": current_seg_depth, "text": text})
        current_seg_depth = None
        current_seg_lines = []

    # Attribution lines are sometimes wrapped across 2-3 physical lines by mailers
    # (e.g., "On Wed, ... Smith <\nbelliottsmith@example.com> wrote:"). Look ahead
    # up to 2 lines to combine if the first line starts an "On ..." pattern but
    # doesn't terminate with "wrote:".
    i = 0
    n = len(body_lines)
    while i < n:
        line = body_lines[i]
        d = quote_depth(line)
        if d == 0:
            stripped = line.strip()
            # Try multi-line attribution merge
            if stripped.startswith("On ") and not stripped.endswith("wrote:") and i + 1 < n:
                merged = stripped
                consumed = 0
                for look in range(1, 3):
                    if i + look >= n: break
                    nxt = body_lines[i + look].strip()
                    if not nxt or quote_depth(body_lines[i + look]) > 0:
                        break
                    merged = merged + " " + nxt
                    consumed = look
                    if merged.endswith("wrote:"):
                        break
                if merged.endswith("wrote:") and is_attribution(merged):
                    flush_seg()
                    attribution_lines.append(merged)
                    i += consumed + 1
                    continue
            flush_seg()
            if is_attribution(line):
                attribution_lines.append(line.strip())
            else:
                new_lines.append(line)
        else:
            if current_seg_depth != d:
                flush_seg()
                current_seg_depth = d
            current_seg_lines.append(line)
        i += 1
    flush_seg()

    # Collapse runs of blank lines in new_content; trim leading/trailing blanks
    cleaned: list[str] = []
    blank_run = False
    for line in new_lines:
        if line.strip():
            cleaned.append(line)
            blank_run = False
        else:
            if not blank_run and cleaned:
                cleaned.append("")
            blank_run = True
    new_content = "\n".join(cleaned).rstrip()

    return {
        "new_content": new_content,
        "quoted_segments": quoted_segments,
        "attribution_lines": attribution_lines,
        "signature": signature,
    }


def extract_at_depth(body: str, max_depth: int) -> str:
    """Return body content where every line's quote depth is <= max_depth.

    At max_depth=0, also drops attribution lines whose target is now stripped.
    Multiple consecutive blank lines collapse to a single blank.
    """
    if not body:
        return ""

    out_lines: list[str] = []
    for line in body.splitlines():
        d = quote_depth(line)
        if d > max_depth:
            continue
        if max_depth == 0 and d == 0 and is_attribution(line):
            continue
        out_lines.append(line)

    # Collapse runs of blank lines and trim trailing whitespace
    cleaned: list[str] = []
    blank_run = False
    for line in out_lines:
        if line.strip():
            cleaned.append(line)
            blank_run = False
        else:
            if not blank_run and cleaned:
                cleaned.append("")
            blank_run = True
    return "\n".join(cleaned).rstrip() + ("\n" if cleaned else "")
