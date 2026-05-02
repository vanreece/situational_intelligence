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
