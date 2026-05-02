# Session Handoff

> Per CLAUDE.md "Snapshot transient state at every control edge." This file is overwritten each pause; it captures only the transient mental-model state that wouldn't otherwise survive a fresh session. Durable state lives in git, bd, memory, and `docs/experiment-log.md`.

## Last updated: 2026-05-02 (after si-clz close — substrate first-test)

## Where we are

`schedule_change_announcement` on Cassandra dev@ 2014 has now been through **five** rounds:

1. `si-qhz` — F1=0.389. Surfaced rubric ambiguity.
2. `si-bwo` — body-cap audit. Surfaced model anchoring on quoted material.
3. `si-s9y` + `si-fnw` — depth sweep. F1 peaks at depth=2 (0.405) above plateau (0.31–0.33).
4. `si-pfo` — vLLM noise floor at depth=2 is F1 ±0.015. Depth=2 winner is real signal.
5. **`si-clz`** (just closed) — substrate first-test (prompt variants over MessageContext). **Pre-reg falsifier triggered: F1 regressed under both A (0.217) and B (0.208) vs C (0.405).** The substrate change was too coarse — it fixes 17 anchoring-on-quoted-text false positives but breaks 11 cases where the cheap-tier was using quoted context productively. Variants A and B disagree only 1.2% (within si-pfo noise) → the structural marker in B was effectively invisible to Qwen3-Coder-30B. Detector still not promoted; depth=2 baseline remains the operating point. F1 ceiling for this detector is now even more clearly rubric-bound.

## My recommended next move

**`si-d6m` (rubric sharpening) is now unambiguously the right next move.** Three rounds of substrate / context / noise work converged: every remaining lever for this detector is in the rubric, not the inputs.

### Concrete starting points for si-d6m (already attached as bd notes)

- **Combined rubric stress-test set: ~26 boundary messages + 17 should-be-negatives**, located in two JSON files:
  - `results/evals/schedule_change_announcement-pfo-noise-floor/summary.json` → `unstable_messages` (15 boundary messages from si-pfo)
  - `results/evals/schedule_change_announcement-clz-variants/summary.json` → `c_to_ab_flip_diagnostics` filtered by `interpretation` (11 "regression" + 17 "anchoring fix")
- **The core rubric question is "is `we'll re-roll` a schedule change or vote-process routine?"** Both readings are defensible. Pick one and document.
  - **If yes (re-roll = schedule change):** keeps current 12 OpusPositives; need a stronger prompt or multi-step pipeline (extract → judge) to help cheap-tier disambiguate without quoted context.
  - **If no (re-roll = vote routine):** cuts ~6 of the 12 current OpusPositives down to ~6 OpusPositives (the cycle-architecture and explicit-postponement cases). Smaller positive class, but tighter.
- **Single-run scorecards work** (noise floor ±0.015 from si-pfo). No multi-run aggregation needed.
- **Re-evaluate at zero inference cost:** si-d6m can re-label the existing 149 items against a v2 rubric and re-score using the existing run-0 prediction file. Only re-run inference if the *prompt* changes.

### Substrate state (don't pick these up next)

- **si-jl0** (cross-thread author context) — idea, not promoted by si-clz. The data didn't surface demand for it.
- **si-qdf** (typed tags — JIRA refs, version markers) — idea. Op-6 still motivates it but only marginally; defer until a detector demands it.
- **si-r6h** (umbrella MessageContext substrate) — idea. Re-visit only after 2-3 detectors have each demanded one specific piece.

The user's framing from this session is now memory-resident (`messages_are_not_single_thesis_streams.md`): substrate forays add what the detector demonstrably lacks; they don't strip what it's quietly using. The si-clz data validates this.

## Open question worth a future session

**Variant B's null result is a U3 update.** At Qwen3-Coder-30B scale, structural in-prompt instructions about context provenance don't reliably steer behavior. A frontier-tier ceiling check (si-2z6) on variant B specifically would tell us if the cost-tier hierarchy assumption holds for *this kind* of substrate steering, or if the marker would be honored by a stronger model. Worth filing as a sub-question of si-2z6 if/when that gets picked up.

## Environment notes

- **Homelab:** rock-solid across the session (255–256s wall-clock per 731-message run, ~0.3% transient errors).
- **Two deterministic vLLM/parsing failures uncovered and fixed in commit `1f9cdf7`:**
  - vLLM guided_json occasionally truncates the closing `}` even with `finish_reason=stop` (Op-10 in variant B). Defensive parse repair in `parse_message_content` now appends `}` or `"}` and retries.
  - `MAX_BODY_CHARS` budget wasn't bounding `new_content` in variants A and B; one 93K-char body (pasted CQL log) hit HTTP 400. Now bounded.
- **Corpus path gotcha:** `--corpus-dir` needs to be `data/processed/apache/dev@cassandra.apache.org`, not the parent.
- **`python` is not on PATH; use `python3`** in shell scripts.

## Git state

- 11 local commits ahead of `origin/main`. **User said they'll handle pushes.**
- Two untracked tarball/zip files (backups), leaving them alone.
- Working tree otherwise clean.

## bd state

- 9 ready issues; si-d6m at the top (P2). 0 in_progress, 0 blocked.
- New idea-stage substrate issues filed this session: si-1lz (closed, parser), si-71f (closed, pre-reg), si-clz (closed, run); si-jl0, si-qdf, si-r6h still open as ideas.

## Memory updates this session

- `labels_are_opus_generated.md` — labels are Opus-generated, not user-verified. Use OpusPositive/Negative/Unsure. Never call them "verified" or "ground truth."
- `messages_are_not_single_thesis_streams.md` — strategic framing on substrate work; refined twice with si-clz empirical findings.
