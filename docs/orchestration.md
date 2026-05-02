# Orchestration

How autonomous bead execution works in this project. The goal is to decouple tactical work (mechanical bead execution) from strategic work (direction-setting), so the queue keeps moving even when the user is not present. Strategy sessions are infrequent; execution is continuous.

## The three layers

1. **Beads as units of execution.** Each bead self-contains everything a fresh Claude instance needs to execute it: pre-reg block (or commit-hash pointer), input paths, output paths, decision rule, falsifiers, halt criteria. A fresh agent should be able to read the bead and do the full cycle without prior context.

2. **Orchestrator as a script.** `bin/orchestrate.sh` (small, no LLM). Picks the next auto-executable bead from `bd ready`, spawns a Claude instance to execute it, handles failure modes, picks the next. Halts only on systemic problems.

3. **Strategy sessions** (decoupled cadence). User reviews accumulated outputs (the strategy-session brief = `docs/session-handoff.md`), sets direction, converts ideas into executable beads, leaves. The orchestrator keeps consuming.

## What makes a bead auto-executable

A bead is **auto-executable** if it satisfies the cold-start contract:

- **Has a frozen pre-reg block** in `docs/experiment-log.md` (or this bead IS the pre-reg). The pre-reg specifies setup, predictions, decision rule, and falsifiers.
- **Names all inputs** by file path or query (e.g., "labels file at X", "predictions file at Y", "corpus dir at Z").
- **Names the output path** for predictions / scorecards / labels / etc.
- **Has a decision rule** keyed on observable outputs (F1 thresholds, label counts, etc.).
- **Has falsifiers** that the executor can check mechanically.
- **Has anti-contamination instructions** if applicable (which files NOT to read).

A bead **needs strategy** if any of:
- The setup is open ("which corpus?", "which algorithm?", "what should the rubric say?")
- Outputs aren't pre-specified
- Decision rule requires user adjudication ("is this worth promoting?")
- It's an umbrella issue tracking a broader lattice

**Mark with the label `auto-executable`:** `bd update <id> --labels auto-executable`. The orchestrator filters for this.

## The three failure modes

Failure handling is **per-mode**, not uniform:

### Systemic failure (halt the train)

Examples: homelab vLLM endpoint unreachable, Claude rate-limit hit, disk full, git push rejected with merge conflict requiring manual resolution.

Response: orchestrator halts, notifies (logs + optional push notification), exits non-zero. User intervenes. After resolution, manually restart the orchestrator.

### Bead-specific failure (mark and skip)

Examples: bead's spec is ambiguous on closer reading, an input file referenced doesn't exist, the experiment hit a transient API error, the executor agent decided it couldn't make safe progress.

Response: bead is **not** closed (close means done). Mark it: `bd update <id> --labels needs_attention --remove-labels auto-executable`. Add a note describing the failure. The orchestrator continues with the next bead. Strategy session triages.

### Result has strategic implications (close and surface)

Examples: pre-reg falsifier triggered with methodology implications, decision-rule outcome lands in an uncovered branch, surprising finding warrants reframing the question, contested promotion criteria.

Response: bead **closes normally** with an honest Results block written to `experiment-log.md`. The findings populate the next strategy-session brief. The orchestrator continues. The user adjudicates at the next strategy session.

This is the most common case for productive work — almost every interesting result has strategic implications. The bead executed correctly; the *result* needs strategy review. The queue keeps moving because the bead is mechanically done.

## Orchestrator algorithm

Pseudocode:

```
while true:
  if not systemic_health_ok(): halt
  bead = bd ready --label auto-executable --limit 1
  if bead is None:
    sleep N minutes, continue  # queue empty, wait for new beads to be filed
  result = spawn_claude_bead_executor(bead.id)
  case result:
    success           → continue (bead handled its own commits and close)
    bead_specific     → bd update bead.id --labels needs_attention --remove-labels auto-executable
                       → continue
    transient_retry   → continue (will be re-attempted next cycle)
    systemic          → halt
```

Health checks:
- `curl -sf http://192.168.100.101:8080/v1/models > /dev/null` (homelab)
- Disk free > 1 GB (avoids accidental fill from large prediction files)
- `git status` clean before starting a new bead (avoids stomping in-progress changes)

Conflict avoidance (later refinement, not v1): if two auto-executable beads both modify the same file, serialize them. v1 just runs one bead at a time.

## The bead-executor contract

The Claude instance spawned by the orchestrator receives a prompt like:

```
You are executing bead {ID}. Read its bd description and the linked pre-reg
block in docs/experiment-log.md. Do the full cycle:
1. If a pre-reg block exists, follow it. If not, the bead description IS the spec.
2. Run the experiment per the spec.
3. Write the Results block to docs/experiment-log.md (under the corresponding entry).
4. Commit your code changes, the predictions, the labels (if you generated any), 
   the experiment-log update, and any analysis scripts.
5. Close the bead with `bd close {ID} --reason "..."` referencing the commit hash.
6. File any follow-ups as `idea`-status bd issues with `discovered-from:{ID}`.

Halt and signal failure if:
- The bead spec is ambiguous in a way that affects what to compute
- A pre-reg falsifier triggers AND the result implies a methodology problem
- An input file is missing and you can't reasonably proceed
- You'd otherwise need user judgment that isn't covered by the pre-reg
- The homelab endpoint returns 5xx repeatedly (signal: systemic, not bead-specific)

Failure signal: write a JSON file to bead-failures/{ID}.json with structured
diagnostic info. The orchestrator reads this to decide between bead-specific
mark-and-skip and systemic halt.
```

The exact prompt is versioned in `docs/orchestrator-bead-executor-prompt.md` so the orchestrator reads from a known source rather than inlining the prompt.

## Strategy-session brief

After each orchestrator cycle (or on a fixed cadence), regenerate `docs/session-handoff.md` with structured sections:

- **What landed** — beads closed cleanly, with one-line summaries
- **Strategic implications** — close-but-warrant-attention items (decision-rule outcomes, surprises)
- **Needs attention** — beads marked needs_attention, with the diagnostic info
- **Next auto-executable** — the queue's top N
- **Needs strategy** — non-executable ideas waiting for elaboration

The user's strategy session = read brief, make calls, file new beads as auto-executable, leave.

## Current status (2026-05-02)

- The cold-start contract works in practice: today's session demonstrated it three times (labeling subagent, follow-up labels, si-qdf execution, si-2z6 execution). All four were spawned with self-contained prompts and produced clean results.
- The two-commit pre-reg discipline already produces auto-executable run-beads (the Run issue becomes auto-executable once its Pre-register sub-issue closes).
- bd labels are not yet used to mark auto-executable; this doc proposes adopting `auto-executable` as the convention.
- `bin/orchestrate.sh` doesn't exist yet; will be added when the prototype is run end-to-end.
- The strategy-session brief format (`docs/session-handoff.md`) is currently 80% there but not formally structured — the sections above will tighten it.

## Audit of current ready beads (2026-05-02)

| Bead | Auto-executable? | What's missing |
|------|:----------------:|----------------|
| si-r6h MessageContext substrate (umbrella) | NO | Umbrella idea; no specific experiment |
| si-jl0 Cross-thread author context | NO | Open design ("storage substrate is open"); needs concrete first-foray spec |
| si-kxh Logprob calibration | **YES** (after light pre-reg) | Algorithm and inputs are specific; needs decision rule + thresholds |
| si-z0a Code-block bias investigation | NO | "Investigate" is open-ended; needs a concrete hypothesis + decision rule |
| si-t3l Harvest second corpus | NO | Explicitly "UNDER-SPECIFIED: which corpus?" |

**Pattern:** 1 of 5 ready beads is close to auto-executable. The other 4 need strategy-session work to convert idea → executable. This is the natural ratio: most strategy-session work is bead-elaboration.

## Open questions for the user (next strategy session)

- Which corpus for si-t3l? Hadoop dev@ is the strongest candidate per its bd description.
- For si-jl0, what's the smallest first foray that proves the concept against a real detector? (No detector yet demands cross-thread context.)
- For si-z0a, what concrete hypothesis to test? (e.g., "messages with code blocks are 2x more likely to be schedule_change_announcement positives" → can be tested with existing data.)
- Should si-kxh be auto-executed now? It's the closest to ready.
