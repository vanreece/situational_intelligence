# Session Handoff — Strategy-Session Brief

> Per `docs/orchestration.md`. Structured for the user's strategy session: read top-down, make calls, file new auto-executable beads, leave.

## Last updated: 2026-05-04 (after si-03o cost-tier escalation transfer test on Hadoop with v3)

---

## Headline

**Cost-tier escalation transfers cross-corpus, but the operating-point doesn't.** On Hadoop common-dev with v3 cheap-tier + frontier-v3 on a 33%-of-corpus borderline pool: F1 lifted 0.6301 → 0.7313 (+0.10), recall went to 1.0, **precision crashed 0.96 → 0.58**. On Cassandra v2 (si-bm1), the same pattern was nearly free. **The architectural commitment holds; the borderline-pool definition needs corpus-specific tightening.**

**Critical correction landed:** the earlier "v3 Hadoop F1 = 0.9583" was undersampled — the 76-label pool didn't include the 25 POS messages v3 missed. The honest cheap-v3 Hadoop F1 is **0.6301**, not 0.96. Same range as Cassandra v3 (0.6364) — a much more believable cross-corpus picture for U1.

---

## What landed since the last strategy session brief (this session)

**Architectural commitments promoted to `architecture.md`:**
- **Cost-tier escalation** as a Classify-layer principle (commit `22cc2dc`). The architectural commitment is the workflow ("define eval, define tolerance, measure, then escalate"), not "always escalate." Empirical-validation discipline encoded.
- **Narrowness over consolidation** (commit `027a96c`). The binary-per-category principle is about *minimum latitude per classifier*, not *minimum classifier count*. Per-corpus rubric variants (and per-corpus borderline pools) are the default when domains diverge — the fork is the default, not the fallback. (This was a user correction to my framing; the principle now reads correctly.)

**Detector promoted to Validated (2 corpora):**
- `schedule_change_announcement` v3_elided is the operating point (commit `b0c51b8`). Cassandra dev@ 2014 + Hadoop common-dev@ 2014 (filtered) both validated.

**Beads closed this session:**
- **si-e5q** — Labeled the 5 frontier-only discoveries from si-2z6. All 5 POS. Expanded Cassandra label pool 153 → 158, 8 → 13 POS.
- **si-t3l** — Hadoop common-dev@ 2014 harvested (3503 messages). Multi-org diversity confirmed (Cloudera/Hortonworks at parity). List-name correction recorded (`dev@hadoop.apache.org` doesn't exist; `common-dev@hadoop.apache.org` selected).
- **si-bm1** — Cost-tier escalation simulation on Cassandra v2: P2 pool (33% of corpus) reaches F1=0.960 vs full-frontier 0.963. Pattern empirically validated for the first time.
- **si-q0i** — Few-shot scaffolding produced no F1 lift. Heavy structure steers toward example surface form, not toward concept.
- **si-2wh** — U1 cross-corpus test of v2_elided on Hadoop. Failed (F1=0.359). Decision-rule branch "over-fit to Cassandra" fired.
- **si-oew** — Apache JIRA/Jenkins bot filter (`src/harvest/filter_bots.py`) implemented during si-2wh.
- **si-03o** — Cost-tier escalation transfer test on Hadoop with v3 cheap-tier. **Pattern transfers, P/R envelope shifts.** Closed after labeling 60 frontier flips for honest scorecard.

**v3 rubric work (no separate bead — diagnostic-driven precursor to si-03o):**
- Diagnostic Opus pass on the v2 prompt + Hadoop samples (`docs/diagnostic-v2-prompt-vs-hadoop.md`) recommended 2 narrow rubric clauses. Implemented as `v3_elided` (prompt-hash `57e9f055f0c5639e`).
- Cassandra F1: 0.5556 → 0.6364 (+0.08); Hadoop F1: 0.359 → 0.6301 (+0.27). Adopted as new operating point.

**Memory updates:**
- `homelab_qwen.md` — bimodal-logprob finding (zero items in [0.01, 0.90] at temperature=0 + guided JSON; logprob-based borderline triage structurally unavailable).
- `messages_are_not_single_thesis_streams.md` — cross-corpus reply-shape weakness confirmation; cost-tier-escalation-dominates-prompt-craft rule (and now Hadoop modifies that to "with corpus-specific calibration").
- `narrowness_over_consolidation.md` (new) — per-corpus variants are the default when domains diverge; rule + reasoning + concrete grounding.

---

## High-level summary of where the project sits

**One detector validated cross-domain at the cheap tier (modest F1).** v3 cheap-tier hits F1≈0.63 on both Cassandra and Hadoop — better than v2 was on either, but not production-grade alone.

**Cost-tier escalation pattern validated as architecturally portable.** It buys recall reliably on both corpora. It bought F1 cleanly on Cassandra v2; it bought F1 with a precision cost on Hadoop v3 because the borderline pool was too permissive.

**The diagnostic Opus pass methodology is now established.** Before spending real money on cost-tier escalation testing, run a small Opus diagnostic on prompt + samples. It distinguishes rubric-shaped failures from capability-shaped failures and saves expensive testing on the wrong hypothesis.

**Architectural picture refined twice this session:**
1. Cost-tier escalation is a tool, not a default — empirical per-detector validation gates production adoption.
2. Narrowness over consolidation — per-corpus rubric variants and per-corpus borderline pools are the default when domains diverge.

**Honest U1 read:** generalization at the cheap tier is real but modest. Same rubric works on both corpora at F1≈0.63. With cost-tier escalation, F1 lifts to 0.73-0.96 depending on corpus and pool calibration. Whether that's "the detector generalizes" depends on the operator's tolerance.

---

## Strategic implications worth your judgment

### 1. The Hadoop borderline pool needs tightening

The current adapted-P2 criterion fires on 33% of corpus. Frontier overshoots on `[VOTE]`-thread procedural traffic — many of those messages aren't real escalation candidates. **Tightening proposal:** drop pure-vote-thread items unless they contain X.Y.Z + release-keyword markers; keep `[DISCUSS]`, `Thinking ahead`, and `Logistics for releasing` as-is. Predicted effect: pool size drops from 450 to ~150–200; combined precision recovers from 0.58 toward 0.85+; F1 likely rises further.

### 2. The 25 cheap-tier-missed-but-rubric-correct POSes on Hadoop suggest a v4

Of the 60 frontier flips, 25 were correct POS. They matched v3 POSITIVE clauses but the cheap-tier still didn't fire on them. That's residual capability-shaped weakness even with v3 rubric. Worth a third diagnostic pass (mirror of v2→v3) to see if there's a v4 set of narrow clauses that helps.

### 3. Per-corpus operating-point clarity

We now know empirically: same v3 rubric, both corpora, but each needs its own borderline-pool calibration. The architecture clarification supports this directly. Worth updating `detector-catalog.md` to record the corpus-specific operating points distinctly when calibration differs (currently it's one entry; might need sub-entries per corpus).

### 4. Pn nomenclature gap (you flagged)

Cost-tier escalation pool labels (P0/P1/P2/...) are defined ad-hoc in each experiment's pre-reg. They don't carry semantics across runs. If escalation becomes a stable architectural pattern, Pn should harden into a documented convention. Right now: Cassandra-v2's P2 ≠ Hadoop-v3's "P2-adapted." Worth a small docs section if/when the pattern repeats.

---

## Bd state

- **9 ready issues, 0 in_progress, 0 blocked.**
- Closed this session: si-e5q, si-t3l, si-bm1, si-q0i, si-2wh, si-oew, si-03o (7 total).
- Filed as `idea`-status follow-ups during this session: si-2wh, si-03o (in earlier sessions), si-dku (Op-13 shape budget), si-cga (Hadoop sublists), si-eb5 (extend cost-tier criterion), si-r6h, si-jl0, si-z0a, si-kxh.
- Next natural auto-executable: a tightened-Hadoop-pool re-run of si-03o (would need a fresh bd issue + pre-reg).

## Git state

- Local commits ahead of `origin/main`: ~15+. **User said they'll handle pushes.**
- Working tree clean.
- 60+ commits since the start of the project's exploration phase.

## Reading order if a fresh session starts here

1. `CLAUDE.md`
2. `docs/goals.md` — for **Un** (primary unknowns U1-U5, secondary U6-U9). The structured exploration framework.
3. `docs/architecture.md` — for the cross-cutting principles, particularly the new cost-tier-escalation and narrowness-over-consolidation sections.
4. This file (session-handoff.md)
5. `docs/experiment-log.md` — for full pre-regs and Results. **Pn** (borderline pools for cost-tier escalation) are defined ad-hoc inside specific experiment entries (si-bm1, si-03o).
6. `docs/detector-catalog.md` — for the current operating point of `schedule_change_announcement`.
7. `bd ready` — current wavefront of ideas.

## Environment notes

- Homelab: stable. Cheap-tier v3_elided runs:
  - Cassandra (731 msg): ~42s @ concurrency=32, no logprobs.
  - Filtered Hadoop common-dev (1355 msg): ~75s @ concurrency=32. ~0.07% parse-error rate observed (vLLM produced extra-text-after-JSON on 1 message; resumable design handled).
- 8 prompt variants in classifier: v3_elided is the new operating point. v2 variants kept for provenance/reproducibility.
- Filtered Hadoop corpus exists at `data/processed/apache/common-dev@hadoop.apache.org-filtered/2014-*.jsonl` (gitignored).
- Hadoop labels at 136 entries: 17 v2-pool + 50 random_sample + 9 v3-pool + 60 si03o-flip.
- New analysis scripts: `src/evaluate/compare_v2_v3.py`, `src/evaluate/analyze_si03o_escalation.py` (both committed).
- New harvest preprocessing: `src/harvest/filter_bots.py` (drops `jira@apache.org` + `*@builds.apache.org`; reusable for any Apache list).
