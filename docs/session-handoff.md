# Session Handoff — Strategy-Session Brief

> Per `docs/orchestration.md`. Structured for the user's strategy session: read top-down, make calls, file new auto-executable beads, leave.

## Last updated: 2026-05-03 (after U1 first cross-corpus test landed)

---

## Headline this session

**U1 first data point: schedule_change_announcement does NOT generalize zero-shot to Hadoop common-dev at the cheap tier.** Pre-reg falsifier triggered cleanly:

| metric | Cassandra cheap-tier | Hadoop cheap-tier (filtered) |
|--------|---------------------:|-----------------------------:|
| F1 | 0.5556 | **0.359** |
| Precision (pool-direct) | 1.000 | 0.882 |
| Recall (extrapolated) | 0.385 | 0.226 |
| Model-positive rate | 6.6% | 1.3% |

Decision-rule branch: **over-fit to Cassandra**. Per the pre-reg, no rubric retuning in this bead — failure modes documented, follow-ups filed.

The architectural commitment to cost-tier escalation (just promoted to `architecture.md` 2026-05-03) gets its first stress test: **the Cassandra-tuned operating point can't be assumed to work on Hadoop.** Each new corpus needs its own labeled-eval validation. That's exactly the discipline the architectural commitment encodes.

---

## What landed since last strategy session (this session)

**Architectural commitment promoted (commit `22cc2dc`):**
- Cost-tier escalation added as a cross-cutting principle in `architecture.md`, with the workflow ("define eval, define tolerance, measure, then escalate") as the commitment, not "always escalate." Per-detector tolerance setting documented.
- Negative principle in "What we deliberately do not do": no escalation in production without labeled-eval comparison establishing acceptable loss.
- U3 finding from si-bm1 encoded: borderline-pool rules default to content-structural cues (subject patterns, body shape) rather than logprob bands, because temperature=0 + guided-JSON yields bimodal-degenerate logprobs.

**si-2wh (cross-corpus generalization test, U1) — closed (commits `e3d461c`, `7093cd9`, `3767d34`):**
- Hadoop common-dev@ 2014 corpus filtered (`src/harvest/filter_bots.py`, drops `jira@apache.org` + `*@builds.apache.org`): 3503 → 1355 messages.
- Cheap-tier v2_elided run on filtered corpus: 17 model-positives (1.3% rate vs Cassandra's 6.6%).
- Opus subagent labeled all 17 model-positives + 50 random model-negatives via clean anti-contamination protocol.
- F1 = 0.359, precision 0.882, extrapolated recall 0.226. Below the [0.46, 0.66] pre-reg band.

**Two failure modes found in Hadoop:**
1. **Domain-specific FPs:** Hadoop has JIRA per-issue version-target rituals ("target version set to 2.4.0", "I've created version 2.5.0 in jira") that don't exist in Cassandra. The cheap-tier reads them as version-target shifts. The v2 rubric needs anti-anchor language for this class.
2. **Domain-general FNs:** short reply-form proposals like "How about planning on hadoop-2.8 by late Jan?" and "I can abandon the 2.3rc, and then release current branch-2 as 2.3. Would that be better?" The cheap-tier's thread-context blindness is **the same shape as Cassandra's dropped TPs** — confirming this is a cross-domain weakness, not a Cassandra peculiarity.

**Subject-marker conventions (informs si-03o):**
- `[VOTE]` transfers (287 occurrences in Hadoop, similar role to Cassandra)
- `Proposal:` does **not** transfer (0 occurrences in Hadoop)
- Hadoop analogs: `[DISCUSS]` (66 occurrences), `Thinking ahead` (62 occurrences)

**si-oew (filter Apache JIRA/Jenkins) closed** as part of si-2wh; `src/harvest/filter_bots.py` is reusable for any future Apache-list harvest.

**Memory updates:**
- `messages_are_not_single_thesis_streams.md` — appended cross-corpus confirmation that the cheap-tier's reply-shape weakness is project-level, not Cassandra-specific. Substrate-demand rule sharpened: case (b) "information in prompt but cheap-tier can't extract" is the dominant cross-domain failure mode for any reply-message-disambiguation detector.

---

## Strategic implications worth your judgment

### 1. The detector is NOT promoted to "Validated (two corpora)"

`schedule_change_announcement` stays at **Prototype (Cassandra-only)** in `detector-catalog.md`. Cross-corpus generalization at the cheap tier is the test that just failed.

### 2. The cost-tier-escalation architectural commitment is intact and tightened

The architectural promotion we did this session passes its first stress test correctly: the per-detector empirical-validation discipline is exactly what's needed when an operating point doesn't transfer. The commitment doesn't say "Cassandra's tuning works everywhere"; it says "validate per-detector, per-corpus, before adopting." Hadoop is now a corpus where the operating point hasn't been validated. That's the system working as designed.

### 3. The domain-general reply-shape weakness is a real architectural finding

Both Cassandra's 3 dropped TPs and Hadoop's 2 sampled FNs share the same shape: short reply-form proposals where the schedule-change semantics depend on the parent-message thesis. The cheap-tier doesn't reach back into thread context. **Any future detector that depends on this shape should plan for cost-tier escalation OR a context-injection substrate from day one.** Filed in memory; worth surfacing to the architecture document if a second detector confirms.

### 4. The strategic fork (your call)

The U1 result opens four possible next moves. Listed in roughly increasing scope:

**A) Run si-03o — frontier-on-Hadoop + cost-tier escalation transfer test.** This tests whether the architectural pattern (cheap + frontier-on-borderline) recovers F1 even when the cheap tier baseline is poor. Cost: real Anthropic API spend, ~1355 Hadoop messages × Opus inference ≈ rough order $40–80 depending on prompt token counts. Most informative single test for the architectural commitment.

**B) Refine the v2 rubric for Hadoop's JIRA-bookkeeping FPs and reply-shape FNs, then re-run.** Risk: rubric-engineering treadmill — chasing per-corpus FP shapes contradicts the project's "binary-per-category classifiers, additive growth" architectural principle. Not recommended.

**C) Triangulate with a third corpus.** A second sublist (e.g., Hadoop hdfs-dev or yarn-dev — already filed as si-cga) or a non-Apache project would tell us whether the failure is Cassandra-Hadoop pair-specific or detector-general. Lower cost than A; less direct architectural-test signal.

**D) Pivot to a different detector.** One detector failing to generalize is one data point. Trying a different binary classifier on the same two corpora would broaden U1's evidence base. New detector-catalog work.

**My read:** A is the highest-leverage single move because it answers the *architectural* question directly. B is anti-architectural. C and D both broaden evidence at the cost of postponing the architectural verdict.

The cost question for A is real but measurable — and the result settles whether the cost-tier escalation pattern holds when cheap-tier baseline is weak. If escalation works on Hadoop too, the architectural commitment is much stronger. If escalation also fails on Hadoop, the commitment is much narrower than we thought.

---

## Needs strategy (your input required to convert to executable)

| Bead | What's needed |
|------|---------------|
| **si-03o** (cost-tier escalation on Hadoop) | Decision: run? (~$40–80 in Anthropic API spend.) Adapted P2 criterion: drop `Proposal:`, substitute `[DISCUSS]` and/or `Thinking ahead`, OR redefine at higher abstraction (project-specific marker sets). |
| **si-cga** (other Hadoop sublists) | Decision: harvest, or focus the available time on si-03o's architectural test? |
| **si-z0a** (code-block bias) | Lower priority since the operating point on this detector is now in flux. |
| **si-r6h, si-jl0** | Still umbrella/under-specified. |
| **si-kxh** (logprob calibration) | Re-frame: bimodal-degenerate logprobs from si-bm1 finding mean Platt/isotonic on chosen-token logprobs is degenerate. Bead needs new direction. |
| **si-eb5** | Defer until Hadoop direction settles. |
| **si-dku** (Op-13 shape-budget) | Defer; tangential. |

---

## Bd state

- 9 ready issues; 0 in_progress; 0 blocked.
- Closed this session: si-2wh, si-oew (2 total — plus the 4 from earlier today).
- This session's chain: si-2wh pre-reg → harvest filter → cheap-tier run → Opus pool labeling → score → close. Two-commit pre-reg discipline held end-to-end.

## Git state

- Local commits ahead of `origin/main`: now ~9+. User said they'll handle pushes.
- Working tree otherwise clean.

## Environment notes

- Homelab: stable. Cheap-tier v2_elided on 1355-msg filtered Hadoop ran in ~71s @ concurrency=32.
- Filtered Hadoop corpus exists at `data/processed/apache/common-dev@hadoop.apache.org-filtered/2014-*.jsonl` (gitignored).
- Hadoop labels at `labels/schedule_change_announcement/hadoop-common-dev-2014-labels-v2.jsonl` (committed; 67 entries: 17 pool + 50 random_sample).
- `src/harvest/filter_bots.py` is reusable for any future Apache-list harvest.
