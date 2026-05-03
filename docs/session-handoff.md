# Session Handoff — Strategy-Session Brief

> Per `docs/orchestration.md`. Structured for the user's strategy session: read top-down, make calls, file new auto-executable beads, leave.

## Last updated: 2026-05-03 (after parallel-batch with cost-tier escalation validation)

---

## What landed since last strategy session

**Parallel batch (4 strategy-fork beads → all closed):**

- **si-e5q** — Labeled the 5 frontier-only discoveries from si-2z6. **All 5 came back POSITIVE** under fresh independent v2-rubric application: three NEW-version-introduction re-rolls (1.2.15, 1.2.18, 1.2.19), a Thrift-freeze policy proposal, and an in-flight RC trajectory change (rc3 inserting a delay before -final). Expanded label pool 153 → 158 items (8 → 13 POS).
- **si-t3l** — Hadoop common-dev@ 2014 harvested (3503 messages). Top-10 sender domains span 4 distinct (`apache.org`, `builds.apache.org`, `cloudera.com`, `hortonworks.com`); broader distribution shows clear Cloudera/Hortonworks/Yahoo/Intel/Oracle/MapR multi-org coordination. **Corpus accepted as the second slice.** List-name correction recorded: original pre-reg said `dev@hadoop.apache.org` (doesn't exist); selected `common-dev@hadoop.apache.org` after probing the four sublists.
- **si-bm1** — Cost-tier escalation simulation **validated**. Pool **P2** (NEG ∩ vote/proposal subject ∩ root-or-body>800 chars; 241 items, **33% of corpus**) reaches **F1 = 0.960** — within 0.003 of full-frontier F1=0.963 — at one-third the inference cost. Pre-reg accuracy mostly hit; P1 narrow underperformed (catches dropped TPs but misses [VOTE]-root discoveries). **The architecture's cost-tier hierarchy is empirically validated for this detector.**
- **si-q0i** — Few-shot scaffolding produced **no F1 lift**. v2_elided_fewshot reached F1=0.625 against same-eval-set baseline 0.625. Composition shifted (recovered 1 frontier-discovery, lost Op-13 to a regression — "shape budget" hypothesis filed as si-dku). Heavy structure steers toward example surface form, not toward underlying rubric concept. Don't promote.

**Two key infrastructure findings recorded as memory updates:**

1. **Cheap-tier `p_positive` distribution is sharply bimodal at temperature=0 + guided JSON.** 726 items at p_pos<0.01, 5 at >0.90, **zero in [0.01, 0.90]**. Logprob-based borderline triage is structurally unavailable in this configuration; use content-structural criteria. (memory: `homelab_qwen.md`)
2. **For closing cheap-tier capability-ceiling gaps, bet architecture over prompt-craft.** Cost-tier escalation (si-bm1: F1+0.40) dominates few-shot scaffolding (si-q0i: F1+0.00). (memory: `messages_are_not_single_thesis_streams.md`)

**Detector status:** `schedule_change_announcement` Prototype operating point is now **two-tier**:
- Cheap-tier-v2_elided handles 67% of corpus (model-NEG outside the P2 pool)
- Frontier-tier-v2_elided triages the 33% in P2 pool (NEG ∩ vote/proposal-marker subject ∩ root-or-body>800)
- Combined F1 = 0.960, precision 1.000, recall 0.923 against the 158-item expanded v2 label set

---

## Strategic implications worth your judgment

### 1. Cost-tier escalation pattern is now project-architectural, not detector-specific

si-bm1 demonstrated that a content-structural borderline criterion (subject markers + body length) closes the cheap-tier-vs-frontier gap on this detector. The pattern itself is corpus-agnostic — the *criterion specifics* (`[VOTE`, `Proposal:`) are project-specific Apache-list conventions. **For your call:** should we promote cost-tier escalation to a first-class architectural commitment in `docs/architecture.md`, or treat it as a per-detector pattern that gets re-derived each time? My read: promote it. The pattern is general; the criteria are detector-tuned.

### 2. Few-shot doesn't substitute for escalation

The si-q0i result is informative both as a negative result and as a sharpening of the "heavy structured prompts steer reliably" lesson. They steer toward the structure's surface form, not toward the underlying concept. **For your call:** worth memorializing in architecture.md as a design principle, or just leave in memory? My read: keep it in memory and the q0i Results block; it's a tactical lesson, not architectural.

### 3. The cross-corpus generalization test (U1) is now unblocked

Hadoop common-dev@ 2014 is in `data/processed/`. The natural next experiment is **si-2wh** (cross-corpus eval of `schedule_change_announcement` v2_elided), now top of the ready queue at P2. Caveat: ~64% of Hadoop common-dev traffic is `jira@apache.org` cross-posts and Jenkins CI noise — needs filtering before classifier runs (filed as si-oew, P3). **For your call:** filter-then-classify, or run on raw and accept the noise dilution? My read: filter first; the filter is trivial (drop messages where `from_email` matches `jira@apache.org` or domain `builds.apache.org`) and Cassandra dev@ didn't have this issue, so apples-to-apples comparison wants the noise gone.

### 4. Operating point on `schedule_change_announcement` is now a two-tier detector

`detector-catalog.md` likely needs an update reflecting the new operating point: cheap-tier-v2_elided + frontier-on-P2-pool. **For your call:** update the catalog now, or wait for cross-corpus confirmation? My read: update with a note that the architecture is validated on Cassandra; cross-corpus is the next test.

---

## Needs attention (failures or under-specified beads)

**None.** All four beads closed cleanly with Results blocks. Six follow-up `idea`-status beads filed.

---

## Next auto-executable (if you green-light orchestrator runs)

The auto-executable label was used as the lock-in mechanism for the four beads run this session. Now that they're closed, the new follow-up beads are `idea`-status and need strategy-session input before becoming auto-executable. The closest-to-ready:

- **si-2wh** (cross-corpus eval, P2): well-specified by its description, just needs a pre-reg block + decision rule + falsifiers committed. Could be elaborated and labeled auto-executable in ~10 minutes.
- **si-oew** (filter Apache JIRA/Jenkins bots, P3): trivial implementation; depends on whether we adopt as a permanent harvest-pipeline preprocessing step or a one-off classifier flag. A small strategy call.
- **si-03o** (run P2 cost-tier escalation on Hadoop common-dev, P3): blocked-by si-2wh logically (need cheap+frontier predictions on Hadoop first).

---

## Needs strategy (your input required to convert to executable)

| Bead | What's needed |
|------|---------------|
| **si-2wh** | Pre-reg block — predicted F1 against Hadoop, decision rule for "did the operating point transfer," falsifiers. Probably the most important next experiment: U1 cross-domain generalization. |
| **si-oew** | Decision: filter as a harvest-pipeline preprocessing step (preferred — applies generally) or as a classifier-side `--exclude-bots` flag (per-detector). |
| **si-03o** | Pre-reg + adapted P2 criterion. The `[VOTE]`/`Proposal:` regex is Apache convention; Hadoop *also* uses `[VOTE]` so transfer should be partial. Ideal: same regex, different distribution. |
| **si-eb5** | Worth pursuing? The "2.1 rc3?" miss is one message in 731. Low-priority; unblock by deferring or by extending P2's regex. |
| **si-dku** | Worth investigating? The "shape budget" hypothesis is interesting but tangential to the production path. |
| **si-cga** | Decision: harvest the other three Hadoop sublists for richer cross-sublist coverage, or stop at common-dev? |
| **si-r6h, si-jl0** | Still umbrella/under-specified — re-visit when 2-3 more substrate pieces have proven themselves. |
| **si-kxh** | Logprob calibration — but si-bm1 just demonstrated logprobs are bimodal at temperature=0. The bead may need re-framing: "calibrate via response self-consistency or temperature>0 sampling, not via Platt on bimodal-degenerate logprobs." |
| **si-z0a** | Code-block bias investigation; lower priority since the operating point on this detector is now two-tier. |

---

## Open architectural questions worth a strategy moment

- **Promote cost-tier escalation to an architectural commitment in `architecture.md`?** The pattern is now empirically validated on one detector (F1=0.960, 33% inference cost vs 99%). Adoption decision is real.
- **Cross-corpus generalization test cadence:** run U1 against Hadoop common-dev now (with bot-filter), or wait for a third corpus to break Cassandra+Hadoop overfitting concerns?
- **Bot-filter as substrate?** The Apache JIRA/Jenkins noise is an Apache-list convention. Adding it to the harvest pipeline encodes a specific convention; making it a classifier flag stays per-detector. Architecture call.

---

## Bd state

- 10 ready issues; 0 in_progress; 0 blocked.
- Closed this session: si-e5q, si-t3l, si-bm1, si-q0i (4 total).
- Filed as `idea`-status follow-ups: si-2wh, si-03o, si-oew, si-dku, si-cga, si-eb5 (6 total).
- The four-bead strategy-fork batch produced six new ideas — natural wavefront expansion at ~1.5x.

## Git state

- Local commits ahead of `origin/main`: ~30+ (user said they'll handle pushes).
- Working tree otherwise clean after this session's commits.

## Memory updates this session

- `homelab_qwen.md` — added the bimodal-logprob finding (zero items in [0.01, 0.90]; logprob-based borderline triage structurally unavailable at temperature=0 + guided JSON).
- `messages_are_not_single_thesis_streams.md` — appended si-bm1 architectural resolution: cost-tier escalation dominates prompt-craft for capability-ceiling cases.

## Environment notes

- Homelab: stable. v2_elided_fewshot run on 731 messages: 58.6s @ concurrency=32 (consistent with prior throughput norm).
- 7 prompt variants in classifier: + `v2_elided_fewshot` (si-q0i, examples loaded from `src/classify/prompts/v2_fewshot_examples.txt`).
- Eval harness now scores against the 158-item expanded v2 label set. `pool_and_extrapolate.py` v0.2.0 still authoritative.
- New analysis scripts: `src/evaluate/analyze_bm1_escalation.py`, `src/evaluate/analyze_q0i_fewshot.py` (both committed).
- New harvest: `data/processed/apache/common-dev@hadoop.apache.org/2014-*.jsonl` (gitignored; reproducible from `src/harvest/apache_mbox.py`).
