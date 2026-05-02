# Bead Executor Prompt Template (Versioned)

This is the prompt the orchestrator (`bin/orchestrate.sh`) passes to a Claude instance for executing a single bead. Versioned here so the orchestrator reads from a known source, not from inlined config.

## Variables substituted at invocation

- `{BEAD_ID}` — the bd issue ID (e.g., `si-kxh`)

## The prompt

```
You are executing bead {BEAD_ID} for the situational_intelligence project.
This is autonomous bead execution per docs/orchestration.md. You have NO prior
context for this bead — read it cold and execute the full cycle.

## Read first

1. `bd show {BEAD_ID}` for the bead's description and any acceptance criteria.
2. `bd dep tree {BEAD_ID}` to verify all dependencies are closed (they should be,
   or you wouldn't have been picked).
3. The pre-reg block in `docs/experiment-log.md`. Search for "{BEAD_ID}" or
   the corresponding entry. The pre-reg is the frozen spec — follow it exactly.
4. `CLAUDE.md` for project conventions if you haven't seen them recently.
5. Any files the bead description names by path.

## Project conventions you must respect

- Two-commit pre-reg discipline: pre-reg blocks commit BEFORE results blocks.
  If this bead is a Run issue and its Pre-register sub-issue is closed, the
  pre-reg is already committed and you can proceed.
- Append to `docs/experiment-log.md` (newest entries at top). Do NOT edit
  prior entries.
- bd is the source of truth for work tracking. Do NOT use TaskCreate or
  markdown TODO lists.
- Use `python3` not `python` in shell scripts.
- Corpus path for Cassandra is `data/processed/apache/dev@cassandra.apache.org`.
- Memory files are at `~/.claude/projects/-home-vanreece-situational-intelligence/memory/`.

## Anti-contamination

If the bead requires fresh-judgment work (e.g., labeling, frontier ceiling check),
spawn a sub-subagent with explicit anti-contamination rules. Do NOT do
contamination-sensitive work yourself in this conversation.

## Execute the bead

1. **Verify the bead is auto-executable.** If the description is ambiguous,
   inputs are missing, or the decision rule cannot be applied mechanically:
   STOP. Write a structured failure to `bead-failures/{BEAD_ID}.json` with:
   ```json
   {"bead_id": "{BEAD_ID}", "failure_type": "bead_specific",
    "reason": "<one sentence>", "needs_strategy": true}
   ```
   Then exit. Do not attempt partial execution.

2. **Run the experiment** per the pre-reg's Setup section. Use the homelab
   for cheap-tier inference; spawn subagents for fresh-judgment work.

3. **Apply the decision rule** to the results. If the outcome lands in a
   covered branch of the decision rule, proceed to step 4. If it lands in
   an uncovered branch (e.g., F1 ≥ threshold but precision below), record
   that the bead has strategic implications but PROCEED — close the bead
   normally, the strategy session will adjudicate.

4. **Write the Results block** to `docs/experiment-log.md` under the
   corresponding entry. Be honest about pre-reg accuracy and surprises.

5. **Commit** all changed files with a descriptive message. Include the
   Co-Authored-By line per project convention.

6. **Close the bead**: `bd close {BEAD_ID} --reason "Results committed in
   <hash>. <one-sentence summary>."`

7. **File follow-ups** as `idea`-status bd issues with `discovered-from:{BEAD_ID}`.
   Do NOT promote them to higher status — that's strategy work.

8. **Update `docs/session-handoff.md`** with what landed (just append to
   the "What landed since last strategy session" section; do not overwrite).

## Failure modes

Write `bead-failures/{BEAD_ID}.json` with:

- `failure_type`: one of
  - `systemic` — homelab unreachable, Claude rate-limited, disk full, etc.
    The orchestrator will halt the train.
  - `bead_specific` — bead spec ambiguous, input missing, can't make safe
    progress. Orchestrator marks the bead `needs_attention` and continues.
  - `transient_retry` — failed once but should retry next cycle. Orchestrator
    leaves the bead in its current state and continues; will pick up next pass.
- `reason`: one sentence
- `details`: free-form, optional
- `needs_strategy`: true/false (does the user need to look at this?)

If you complete successfully, do NOT write a failure file. The orchestrator
treats absence of the file as success.

## Reporting back

Your final tool result should be under 150 words and include:
- Whether the bead closed successfully or wrote a failure file
- One-sentence summary of what was found / done
- The commit hash (if successful)

Begin by running `bd show {BEAD_ID}` and `bd dep tree {BEAD_ID}`.
```

## Notes on this template

- It assumes the bead's pre-reg is already committed (two-commit discipline).
  Pre-register sub-issues are themselves auto-executable beads (their work is
  drafting the pre-reg block + committing it + closing themselves), but they
  produce strategy-shape outputs (a pre-reg is part-strategy, part-spec). For
  v1, pre-register sub-issues are NOT auto-executable; the user drafts pre-regs
  in strategy sessions. Run sub-issues become auto-executable once their
  pre-reg lands.
- `spawn sub-subagent` for fresh-judgment work uses the same Agent tool the
  parent uses. Anti-contamination instructions in the sub-subagent prompt.
- `bead-failures/` is gitignored; it's runtime state for the orchestrator to
  consume.
