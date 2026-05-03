# Session Handoff — Strategy-Session Brief

> Per `docs/orchestration.md`. Structured for the user's strategy session: read top-down, make calls, file new auto-executable beads, leave.

## Last updated: 2026-05-03 (after concurrent-dispatch landed — every detector run is now ~40s)

---

## What landed since last strategy session

**Detector promotion (early in this session):**
- `schedule_change_announcement` promoted to **Prototype** via si-rrz (commit `9a24e9e`). Operating point: v2 rubric + v2_elided body shape (depth=2 quote filter + quoted-line content elision). F1 = 0.769, precision = 1.000, recall = 0.625.

**Parallel batch (the autonomous-execution-pattern proof):**
- **si-2t4** — eval harness stratified-FN fix (`1a23fa4`, `002a020`). Recall extrapolation now agrees with pool-direct counts. v1 baseline F1 corrects from 0.405 → 0.446 (prior estimate was legacy-biased).
- **si-qdf** — typed-tag substrate first foray (`774fdb0`). **REGRESSED:** F1 0.769 → 0.667. Substrate built correct version-state data but cheap-tier *anti-anchored* — read "1.2.17 just passed" as reinforcing the v2 "procedural" frame, making the model MORE confident the messages were procedural fallout. Net −1 TP.
- **si-2z6** — frontier-tier ceiling check (`a64484c`). **F1 = 0.941** with Opus on the same v2_elided prompt. All 3 cheap-tier dropped TPs recovered + 5 unlabeled discoveries (filed as si-e5q to label).

**Orchestration scaffolding (committed `94df370`):**
- `docs/orchestration.md` — bead-as-execution-unit contract; failure-mode taxonomy (systemic / bead-specific / strategic-implications); audit of current ready beads.
- `docs/orchestrator-bead-executor-prompt.md` — versioned cold-start prompt for the executor.
- `bin/orchestrate.sh` — 170-line orchestrator (no LLM in the script itself). Smoke-tested.
- `.gitignore`: `bead-failures/` added.

**Throughput tuning (committed `35223c3`, `d7077c1`):**
- `src/classify/dump_prompts.py` — emits exact vLLM payloads to JSONL for replay/tuning experiments (no inference).
- `src/classify/replay_concurrent.py` — concurrent replay tool (ThreadPoolExecutor wrapping urllib); reports throughput + latency stats.
- `src/classify/schedule_change_announcement.py` updated:
  - **Default concurrency = 32** (was sequential). 731-message v2_elided run: **40s** (was 256s, 6.4× speedup), 0 errors, 731/731 prediction agreement with prior sequential.
  - `--no-logprobs` flag for production runs (response payloads shrink ~98%, p_pos falls back to 0.999/0.001).
  - `--top-logprobs N` (default 10 preserves accurate `extract_p_positive`; 2 is the practical floor).
- Memory `homelab_qwen.md` updated with throughput characterization (saturation at conc=32; auxiliary knobs are zero-throughput levers — they shrink response payloads only).

---

## Strategic implications worth your judgment

### 1. The substrate-demand inference rule is now empirical

si-rrz, si-qdf, si-2z6 worked through the same 3 dropped TPs with three different interventions:

| Intervention | Result |
|--------------|--------|
| Diagnose what the cheap-tier needs (si-rrz) | "Needs version-state context" |
| Add version-state context as substrate tags (si-qdf) | **Regressed** — anti-anchored on procedural frame |
| Apply same prompt with frontier model (si-2z6) | **Worked** — all 3 recovered, F1 = 0.941 |

The lesson: "cheap-tier failed → substrate would help" was wrong as a default rule. Updated `messages_are_not_single_thesis_streams.md` with the revised inference taxonomy: (a) info missing → add substrate; (b) info present but cheap-tier can't extract → frontier escalation or heavy prompt scaffolding; (c) cheap-tier extracts wrong frame → rubric/prompt redesign (NOT substrate).

**For your call:** does this finding change the priority of the substrate work overall? si-jl0 (cross-thread author context) and si-r6h (umbrella) are still idea-stage. The cost-tier escalation pattern (si-bm1, just filed) is now the highest-evidence path forward.

### 2. The 5 frontier discoveries may shift all v2 numbers

si-e5q (just filed) is a P2 auto-executable foray to label the 5 frontier-positives Opus surfaced. They include candidate NEW-version proposals (1.2.15, 1.2.18, 1.2.19) and the Thrift-freeze proposal. If most are true positives, the OpusPositive set expands from 8 → ~13, which would ripple into all prior v2 evaluations:
- cheap-tier-v2_elided's recall would change (from 0.625 to maybe 5/13 = 0.38 if it caught 0 of the 5)
- cheap-tier-v2_strict's recall would similarly shift
- F1 numbers for both would update

**For your call:** want me to run si-e5q now (it's small — 5 items × Opus subagent ≈ 5 min)?

### 3. Cost-tier escalation pattern has its first measured demand

si-bm1 (idea-stage, just filed): the architecture's "narrow models do high-volume; capable models do borderline cases" maps cleanly onto si-2z6's finding. Concrete first foray: define a cheap-tier "borderline" criterion, escalate ~10-30 items per corpus to frontier. F1 lift target: approaching 0.94.

This could materially close the cheap-tier-v2_elided 0.625 recall gap — but it's a real architectural commitment (we'd start escalating in production). Worth a strategic discussion.

---

## Needs attention (failures or under-specified beads)

**None.** No beads in `needs_attention` state. All this session's beads either closed cleanly or surfaced strategic implications via Results blocks.

---

## Next auto-executable (if you green-light orchestrator runs)

**1 bead is currently auto-executable as filed:**
- **si-e5q** — label the 5 frontier discoveries. Small, fast, expands the eval base.

**1 bead is close to auto-executable** (needs ~10 min of pre-reg drafting to be ready):
- **si-kxh** — Platt/isotonic logprob calibration. Algorithm specified, inputs specified, just needs decision rule + thresholds in a pre-reg block.

**No others.** Per `orchestration.md`'s audit, the remaining ready beads (si-r6h, si-jl0, si-z0a, si-t3l) need strategy-session input before they can be auto-executed.

---

## Needs strategy (your input required to convert to executable)

| Bead | What's needed |
|------|---------------|
| **si-t3l** | Pick a corpus. Hadoop dev@ is the strongest candidate per its description. Once picked, I can execute the harvest. |
| **si-z0a** | Concrete hypothesis: "messages with code blocks are 2x more likely to be schedule_change_announcement positives" — testable against existing data. Want me to draft this as a pre-reg? |
| **si-jl0** | Smallest first foray that proves cross-thread author-context against a real detector. No detector currently demands it; would be premature substrate. |
| **si-r6h** | Umbrella idea — re-visit when 2-3 substrate pieces have proven themselves on real detector demand. Don't elaborate yet. |
| **si-bm1** (new, P3) | Cost-tier escalation foray — concrete demand exists (3 TPs recoverable by frontier). Pre-reg + define borderline criterion. |
| **si-q0i** (new, P3) | Few-shot prompt scaffolding for NEW-version disambiguation. Alternative path to closing the cheap-tier gap. |
| **si-kxh** | If you want it auto-executable: confirm whether Platt or isotonic, and whether a Brier improvement of ≥0.05 is the promotion threshold. |

---

## Open architectural questions worth a strategy moment

- **Are we satisfied with one detector promoted, or do we want N before testing cross-domain generalization (U1)?** si-t3l (second corpus) is the higher-leverage move strategically; si-bm1 / si-q0i are higher-resolution moves on the existing detector.
- **Should we adopt the cost-tier escalation pattern in production?** si-2z6's data says yes for `schedule_change_announcement`; whether to generalize is a real architecture decision.
- **First end-to-end orchestrator cycle** — there's currently 1 auto-executable bead (si-e5q). Run it as the proof? Or wait until a few more beads are elaborated and run a longer batch?

---

## Bd state

- 8 ready issues; 0 in_progress; 0 blocked.
- Closed this session: si-pfo, si-clz, si-1lz, si-71f, si-d6m, si-rrz, si-3mg, si-q9m, si-dwi, si-jkr, si-5m8, si-cjc, si-2t4, si-qdf, si-2z6 (15 total).
- Filed this session as new ideas: si-jl0, si-qdf (executed since), si-r6h, si-bm1, si-q0i, si-e5q.

## Git state

- 26 local commits ahead of `origin/main`. **User said they'll handle pushes.**
- Two untracked tarball/zip files (backups), leaving them alone.
- Working tree otherwise clean.

## Memory updates this session

- `labels_are_opus_generated.md` — terminology + epistemic framing
- `messages_are_not_single_thesis_streams.md` — substrate-demand inference rule revised through three rounds (rrz/qdf/2z6)
- `local_temporal_context.md` — heavy structured prompts steer cheap-tier; structural elision beats prompt instructions
- `no_epistemic_downside.md` — autonomous execution principle
- `tactics_vs_strategy_shapes.md` — bead-vs-strategy-artifact distinction
- `homelab_qwen.md` — throughput characterization (saturation at conc=32; auxiliary knobs are zero-throughput)

## Environment notes

- Homelab: stable. **New throughput norm:** 731-message run takes ~40s at default concurrency=32 (was ~256s sequential). Saturation at conc=32-64; beyond that is queueing tax with no throughput gain.
- Two deterministic vLLM/parsing failures fixed earlier (`1f9cdf7`).
- 6 prompt variants in classifier: current_baseline, new_only, new_with_marked_quoted, v2_strict, v2_elided, v2_elided_tagged. Operating point: v2_elided.
- Eval harness now at v0.2.0 with stratified FN (si-2t4 fix).
- Default concurrency = 32; default logprobs = on. Set `--no-logprobs` for production runs (98% smaller predictions).
- `bin/orchestrate.sh` is ready but no beads currently labeled `auto-executable` — the first strategy session move is converting one or more ready ideas into self-contained executable beads.
