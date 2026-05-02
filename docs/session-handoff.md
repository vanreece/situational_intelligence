# Session Handoff

> Per CLAUDE.md "Snapshot transient state at every control edge." This file is overwritten each pause; it captures only the transient mental-model state that wouldn't otherwise survive a fresh session. Durable state lives in git, bd, memory, and `docs/experiment-log.md`.

## Last updated: 2026-05-02 (after si-rrz close — first detector promoted)

## Where we are

`schedule_change_announcement` on Cassandra dev@ 2014 is **promoted to Prototype**. Operating point: v2 rubric + v2_elided body shape. F1 = 0.769, precision = 1.000, recall (pool) = 0.625.

The full arc this session:

1. `si-pfo` — vLLM noise floor at depth=2 = F1 ±0.015. Depth=2 winner is real signal.
2. `si-clz` — substrate first-test (variants A, B). F1 regressed to 0.21; substrate too coarse. Detected the anchoring-failure FP cluster.
3. `si-d6m` — sharpened rubric (v2_strict). F1 = 0.727 against re-labeled OpusLabel-v2. Promotion near-miss (precision 0.571 < 0.70).
4. `si-rrz` — v2_elided sub-foray (replace quoted line content with `[QUOTED]`). F1 = 0.769, precision = 1.000. **Both promotion criteria met.** Detector promoted.

The user's strategic frame ("forays into infrastructure when needed; don't overbuild") was reinforced by the data: the substrate elision foray solved the precision problem while exposing a *concrete* substrate demand (3 TPs lost to elision all need version-state-at-time tags — first measured demand for si-qdf).

## My recommended next move

Three reasonable paths, ordered by my recommendation:

**(1) `si-t3l` — harvest a second multi-org corpus and test cross-corpus generalization.** This addresses U1 (the most important primary unknown) directly. The current detector was tuned on Cassandra dev@ 2014 (single-org dominated by Sylvain Lebresne). Whether v2_elided generalizes to a multi-vendor corpus is genuinely unknown and is the headline question for the architecture's value prop. Worth pre-registering predictions about which v2 rubric clauses port and which need per-corpus tuning.

**(2) `si-qdf` (typed-tag extraction) — recover the 3 TPs lost to v2_elided.** Now has a concrete success metric: recovers Op-9, Shuler-1.2.18-question, Ellis-1.2.17-takedown without introducing new FPs. Demonstrates a substrate piece earning its keep against measured demand. Smaller scope than si-t3l, more localized signal.

**(3) `si-2t4` — fix the eval harness stratification bug.** Just promoted to P2. Important methodology fix. Not value-creating on its own but unblocks honest recall reporting on future detectors.

My read: **(1) si-t3l** is the higher-leverage move. The architecture has now produced one promotable detector through a clean experimental loop. The next question that actually matters strategically is whether any of this generalizes. (2) and (3) are both reasonable but more incremental.

## Open questions worth a future session

- **Does v2_elided's quoted-line elision generalize to other detectors?** Or is "elide quoted material" specific to detectors with strong-signal anchoring failures? Worth testing on the next detector (whichever you pick).
- **Does the v2_strict heavy-rubric prompt design generalize?** v2's 1,700+ chars of explicit category lists and examples reliably steered the cheap-tier here. Whether the same structure works for `vendor_silence`, `risk_escalation_language`, etc., is open.
- **Is the cycle-proposal phrase failure mode a one-off or a class?** The 3 v2_strict FPs that survived the CRITICAL quoted-text rule all anchored on Michael Kjellman's TL;DR. v2_elided fixed all 3 structurally. But: are there OTHER strong-signal phrases in OTHER threads that would still anchor incorrectly? The cycle thread is one of the highest-density schedule discussions; other threads may not stress-test the same way.

## Environment notes

- Homelab: stable across the session (255–273s wall-clock per 731-message run; ~0.3% transient errors).
- Two deterministic vLLM/parsing failures uncovered and fixed during si-clz (commit `1f9cdf7`).
- Corpus path gotcha: `--corpus-dir` needs `data/processed/apache/dev@cassandra.apache.org`.
- `python3` not `python` in shell scripts.
- 5 prompt variants now in classifier: `current_baseline`, `new_only`, `new_with_marked_quoted`, `v2_strict`, `v2_elided`. v2_elided is the operating point for `schedule_change_announcement`.

## Git state

- 16 local commits ahead of `origin/main`. **User said they'll handle pushes.**
- Two untracked tarball/zip files (backups), leaving them alone.
- Working tree otherwise clean.

## bd state

- 9 ready issues; new top of P2: si-t3l, si-jl0, si-qdf, si-2t4 (newly promoted to P2), si-2z6, si-z0a, si-kxh.
- 0 in_progress, 0 blocked.
- Closed this session: si-pfo, si-clz, si-1lz, si-71f, si-d6m, si-rrz, si-3mg, si-q9m, si-dwi.

## Memory updates this session

- `labels_are_opus_generated.md` — terminology + epistemic framing for labels
- `messages_are_not_single_thesis_streams.md` — substrate-demand finding now empirically grounded (si-rrz)
- `local_temporal_context.md` — heavy structured prompts steer cheap-tier; structural elision beats prompt instructions for anchoring failures
