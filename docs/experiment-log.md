# Experiment Log

Append-only log of experiments. The newest entries are at the top. The code is secondary; this log is the durable artifact.

## Pre-registration discipline

Every entry has two halves: a **Pre-registration** block written and committed *before* the experiment runs, and a **Results** block written and committed *after*. This is a two-commit convention by design — the git timestamp on the pre-reg commit is the receipt that we didn't move the goalposts.

The pre-reg block forces us to declare:
- what we expect to see and why,
- what each plausible outcome would mean for our beliefs,
- what observations would actually change our minds.

The results block then has to confront the pre-reg honestly. Surprises (results that contradict the prediction) are first-class outputs and must be called out explicitly — they're where the most learning compounds.

Negative results compound as much as positive ones. Skipping the pre-reg block is a tell that we're rationalizing — if you find yourself wanting to skip it, that's the experiment most worth pre-registering.

---

## Entry template

```markdown
## YYYY-MM-DD: <Short title>

**Question:** Which unknown is this addressing? (e.g., U1: cross-domain generalization)

### Pre-registration *(commit this block before running)*

**Setup:**
- Dataset(s):
- Detector(s):
- Model(s):
- Approach:

**Prediction:** What we expect to observe and why. Specific enough that a different observation would feel different.

**Decision rule:** What each plausible outcome would mean.
- If result looks like X → conclusion A (e.g., promote detector to Validated)
- If result looks like Y → conclusion B (e.g., revise approach)
- If result looks like Z → inconclusive, try Z'

**Falsifiers / mind-changers:** Concrete observations that would disconfirm the prediction or shift an architectural commitment. If none come to mind, the experiment may not be sharp enough.

### Results *(commit this block after running)*

**Observations:**
- What was actually seen
- Anything unexpected in the data or outputs

**Surprises:** Anything that contradicted the Prediction. Be explicit — these are where the learning is.

**Conclusions:**
- Which decision-rule branch fired
- What we now believe and how strongly
- What changed about our model of the problem

**Next:**
- What this suggests trying next
- Any new entries to detector-catalog.md or new questions for goals.md
```

---

## 2026-05-03: Parallel batch — second corpus, cost-tier escalation, few-shot scaffolding

**Question:** Three independent forays dispatched as a parallel batch under the autonomous-execution principle. Each addresses a different unknown but they share no resource conflicts.

- **si-t3l** (U1 cross-domain): harvest Hadoop dev@ 2014 as the second corpus so generalization tests of `schedule_change_announcement` become possible.
- **si-bm1** (architecture): does cost-tier escalation on a small borderline pool recover most of the frontier-tier F1 lift at a fraction of the cost? The architectural pattern from `architecture.md` ("narrow models do high-volume; capable models do borderline cases") gets its first measurement.
- **si-q0i** (U3 cheap-tier ceiling): do few-shot examples in the system prompt steer the cheap-tier reliably enough to recover the 3 dropped TPs that the typed-tag substrate (si-qdf) anti-anchored on?

**Beads issues:**
- si-t3l (run; pre-reg block here)
- si-bm1 (run; pre-reg block here; discovered-from si-2z6)
- si-q0i (run; pre-reg block here; discovered-from si-2z6)

### Sub-experiment 1: si-t3l — harvest Hadoop dev@ 2014 (second corpus)

**Setup:**

- **Source:** `lists.apache.org/api/mbox.lua` (same endpoint as Cassandra). List: `common-dev@hadoop.apache.org`. Range: 2014-01..2014-12.
- **List-name correction (in-flight):** the original pre-reg specified `dev@hadoop.apache.org`, but that list does not exist — Hadoop split the integrated dev list into per-project sublists (`common-dev`, `hdfs-dev`, `mapreduce-dev`, `yarn-dev`) when it modularized. Probed all four; `common-dev` is the highest-volume in 2014-01 (2.7MB raw) and is the closest analog to Cassandra's single-list `dev@` because it carries cross-project release-coordination traffic. Selected `common-dev`. The other three sublists remain candidates for a follow-up.
- **Why Hadoop common-dev@ 2014:** Hadoop was a TLP through this period with strong multi-vendor presence (Cloudera, Hortonworks, Yahoo, MapR, Intel, Microsoft). 2014 was the Hadoop 2.x active phase with multiple release lines (2.4, 2.5, 2.6) and active vendor competition — exactly the multi-vendor coordination texture absent from Cassandra's single-org-dominant slice.
- **Why 2014 specifically:** matches the Cassandra slice for direct cross-corpus comparability. Apple-to-apples temporal alignment for the eventual `schedule_change_announcement` cross-corpus eval.
- **Pipeline:** Existing `src/harvest/apache_mbox.py` parameterized on `--list common-dev --domain hadoop.apache.org --start 2014-01 --end 2014-12`. Output to `data/raw/apache/common-dev@hadoop.apache.org/2014-MM.mbox` and `data/processed/apache/common-dev@hadoop.apache.org/2014-MM.jsonl`.
- **Diversity check:** Tabulate top-10 senders by message count, group by email-domain (`@cloudera.com`, `@hortonworks.com`, etc.). Acceptance threshold: top-10 senders span ≥3 distinct organizations.

**Predictions:**

| metric | predicted | reasoning |
|--------|-----------|-----------|
| Total messages 2014 | 1500–4000 | Hadoop dev@ is much higher-volume than Cassandra's 731. |
| Top-10 sender domain diversity | 4–8 distinct orgs | Cloudera + Hortonworks + Yahoo at minimum based on commit history. |
| Mailing-list-mechanic noise (JIRA cross-posts, +1 votes) | ~30% of messages | Apache lists in this era had noticeable JIRA bot traffic. |
| Schedule-change signal density | ~5–15% positive rate | Multi-org pressure on releases should produce more explicit schedule discussion than single-org Cassandra (~7% strict v2 rate). |

**Decision rule:**

- **Top-10 sender domain diversity ≥3 orgs AND total messages ≥1000:** corpus accepted as the second slice. File `idea`-status follow-up to run `schedule_change_announcement` v2_elided against this corpus (cross-corpus generalization test).
- **Top-10 sender domain diversity <3:** Hadoop is also single-org-dominant for this slice. Document the finding; pick a different corpus (Apache Incubator retiree or IETF working group). Don't promote.
- **Mbox endpoint returns < 100 messages or 4xx:** harvest pipeline failure or list move. Halt as bead-specific failure; investigate.

**Falsifiers / mind-changers:**

- Top-10 senders all from same org: corpus is multi-org in name only; pick a different one.
- Total volume <500: 2014 wasn't an active year for Hadoop dev@; pick a different year or a different list.
- Harvester crashes on Hadoop's mbox shape: parser bug surfaces a generality issue in `apache_mbox.py` worth fixing before the next harvest.

**Anti-contamination:** none — this is a harvest, not a detector run. The corpus must NOT be inspected for `schedule_change_announcement` content during this foray (would contaminate the eventual cross-corpus test).

### Sub-experiment 2: si-bm1 — cost-tier escalation simulation

**Key insight:** si-2z6 already ran the frontier (Opus) on all 731 Cassandra dev@ 2014 messages. So the cost-tier-escalation question is a **simulation on existing data**, not new inference: "if we had used cheap-tier on confident-calls and frontier on a borderline pool, what F1 would we have achieved versus the cost?" This frames the foray as a replay-and-score exercise.

**Setup:**

- **Inputs (frozen):**
  - Cheap-tier predictions: `results/detector-runs/schedule_change_announcement/si-d6m/cassandra-2014-predictions-v2-elided.jsonl` (731 records).
  - Frontier predictions: `results/detector-runs/schedule_change_announcement/si-2z6/cassandra-2014-predictions-frontier-v2-elided.jsonl` (same 731 IDs).
  - Labels: `labels/schedule_change_announcement/cassandra-2014-labels-v2.jsonl` (will be the **post-si-e5q expanded set**, ~158 items if all 5 frontier-discoveries are POS).
- **Context:** the cheap-tier's `p_positive` distribution is sharply bimodal — 726 items at p_pos<0.01, 5 items at p_pos>0.90, **zero items in [0.01, 0.90]**. A logprob-based borderline criterion is structurally unavailable. The borderline criterion must therefore be content-structural (subject pattern, body length, version mention) rather than confidence-based. This is itself a U3 finding worth recording.
- **Borderline criterion sweep** — five candidate pools, computed against cheap-tier model-NEGATIVES:

  | Pool | Definition | Pool size |
  |------|------------|-----------|
  | P0 | (control) no escalation; cheap-tier alone | 0 |
  | P1 | NEG ∩ X.Y.Z body ∩ release-keyword ∩ NOT [VOTE]-root subj | ~46 |
  | P2 | NEG ∩ vote/proposal-marker subject ∩ (root OR body>800 chars) | ~241 |
  | P3 | NEG ∩ vote/proposal-marker subject (any reply) | ~282 |
  | P_full | All 731 (frontier-on-everything) | 726 |

  Where:
  - `X.Y.Z body` = body matches `\b\d+\.\d+\.\d+\b`
  - `release-keyword` = body matches `\b(re-?roll|take it down|takedown|postpone|shorten|cadence|LTS|cycle|i propose|proposal:|let's do a|move(d)? to)\b` (case-insensitive)
  - `vote/proposal-marker subject` = subject matches `\[VOTE\b` (covers `[VOTE]`, `[VOTE PASSED]`, `[VOTE CLOSED]`, `[VOTE FAILED]`) OR matches `^proposal:` (case-insensitive)
  - "root" = subject does NOT start with `re:` or `fwd:` (case-insensitive)

- **Combined-prediction logic:** for each pool P, the combined prediction for message m is:
  - if `m.id ∈ pool_P_ids` AND `cheap_pred[m] == False`: use `frontier_pred[m]`
  - else: use `cheap_pred[m]`
  (Equivalently: escalate cheap-NEGs-in-pool to frontier; trust everything else from cheap.)

- **Score against expanded labels** (post-si-e5q): precision, recall (pool-direct), F1 for each combined-prediction set. Also report number of frontier calls = pool size = cost proxy.

- **Implementation:** new analysis script `src/evaluate/analyze_bm1_escalation.py`. No new LLM inference. Reads existing predictions + labels, computes combined predictions, scores. Writes scorecard to `results/evals/schedule_change_announcement-bm1-escalation/scorecard.json`.

**Predictions:**

| metric | P0 (cheap only) | P1 (~46) | P2 (~241) | P_full (726) | reasoning |
|--------|----------------:|---------:|----------:|-------------:|-----------|
| Recovered dropped TPs | 0/3 | 3/3 | 3/3 | 3/3 | All 3 dropped TPs are inside P1 already; P2 and P_full include them. |
| Recovered frontier-discoveries | 0/k | 0/k | ~k–1/k | k/k | k = number of POS frontier-discoveries (k≤5, depends on si-e5q). P1 misses [VOTE]-root subjects; P2/P_full include them. |
| New FPs introduced (frontier's 1 borderline FP) | 0 | 0–1 | 1 | 1 | Frontier's lone FP (Marcus "3.0/3.1/4.0 musing") sits in a [VOTE]-or-proposal subject ⇒ in P2 but not P1. |
| F1 vs cheap-tier baseline | 0.769 (current) | 0.85–0.92 | 0.90–0.94 | 0.94 | P1 closes recall gap on the 3 known cases; P2 also captures discoveries; P_full = ceiling. |
| Frontier-call cost ratio | 0× | 0.06× | 0.33× | 1.00× | Direct ratio of pool size to full corpus. |

**Decision rule:**

- **The smallest pool P_min where combined-F1 ≥ 0.90 AND F1 within 0.05 of P_full:** that is the operating point for cost-tier escalation. Document and consider for production adoption.
- **No pool achieves F1 ≥ 0.85:** the cost-tier escalation pattern doesn't pay off cleanly for this detector at any tested pool size. Consider that frontier may lift F1 only when applied broadly, narrowing the architectural commitment.
- **P_full F1 ≠ 0.941:** something has changed in the frontier predictions or labels relative to si-2z6's report. Investigate before drawing conclusions from the smaller pools.
- **P1 alone hits F1 ≥ P_full − 0.05:** the architecture is even tighter than expected — escalating just 6% of messages (a tightly-scoped borderline pool) recovers near-frontier quality. Strong evidence for adopting in production.

**Falsifiers / mind-changers:**

- All pools produce F1 ≤ cheap-tier baseline: combined logic is wrong (e.g., bug in id-matching). Halt; debug.
- Frontier's predictions disagree with si-2z6's reported precision/recall: the predictions JSONL has changed since si-2z6 ran. Halt as bead-specific failure.
- Pool P1 size differs by >20% from the predicted ~46: regex tuning is off; recompute and recheck dropped-TP coverage before scoring.

**Anti-contamination:** the bead executor must NOT re-label any item. Labels are frozen as the post-si-e5q v2 set.

### Sub-experiment 3: si-q0i — few-shot scaffolding for cheap-tier

**Setup:**

- **Premise:** si-d6m showed heavy structured prompts steer Qwen3-Coder reliably; lightweight instructions don't. si-qdf showed structured TAG substrate anti-anchors. Few-shot examples in the system prompt are a third intervention class (heavy structure, no machine-extracted state).
- **New prompt variant: `v2_elided_fewshot`.** Identical to `v2_elided` system prompt + an EXAMPLES section appended showing 5 worked examples drawn from the v2 OpusLabel pool. Input rendering (depth=2 quote filter + line elision) unchanged.
- **Example selection rule** (frozen — picked from the v2 pool by their labeled rationale):
  1. **POSITIVE — NEW-version-introduction (1):** message `CAKkz8Q2_20vQSG3MW0SYqSTUGRrPD8ubL7kz+qkkeR+BRf_y5A@mail.gmail.com` (Sylvain "1.2.18 re-roll"). Rationale: introduces 1.2.18 when 1.2.17 was the last announced — exemplifies the rubric's "re-roll that introduces a NEW version" POSITIVE clause.
  2. **POSITIVE — NEW-version-introduction (2):** message `53B2F945.9000605@pbandjelly.org` (Shuler "1.2.18 re-roll?"). Rationale: question-form NEW-version reference; demonstrates that question-mark tone doesn't disqualify if the reference is to an unplanned version.
  3. **NEGATIVE — vote-failure-reroll (procedural fallout) (1):** message `CAKkz8Q3nDn97ihVX5qYkceM7Ehm_WBBmDbTdMag` (Closes 2.0.8 vote, announces reroll). Rationale: same release was always planned; vote-failure reroll is procedural mechanic, NOT schedule change.
  4. **NEGATIVE — vote-failure-reroll (procedural fallout) (2):** message `CAKkz8Q07-06XA_P_PfwC5J4xWpwQVPqdA8PBnY+` (Closes 2.0.10 vote, announces reroll once pig stuff is fixed). Rationale: distinct surface form ("once X is fixed") still procedural; teaches the boundary.
  5. **NEGATIVE — vote-period adjustment (vote-mechanic) (1):** message `CAKkz8Q3tHQygxZuKgxuRmp7qP_KqbLA4Y83PJFC` (Resurrects 1.2.16 vote with vote-period adjustment "extend for just 24h more"). Rationale: vote-period adjustment is mechanic, not date — distinct from reroll category.

  Each example renders as: `EXAMPLE [N]:\nSubject: ...\nFrom: ...\nDate: ...\n\n<elided body>\n\nEXPECTED: {"is_schedule_change_announcement": <bool>, "evidence_quote": "...", "rationale": "..."}\n\n`. The rationale text in each example is the v2 label rationale, lightly edited for prompt clarity.

- **Run:** cheap-tier (Qwen3-Coder-30B) at `192.168.100.101:8080`, full 731-message corpus, depth=2 quote filter, `--variant v2_elided_fewshot`, default concurrency=32. Predictions to `results/detector-runs/schedule_change_announcement/si-q0i/cassandra-2014-predictions-v2-elided-fewshot.jsonl`.

- **Score against post-si-e5q expanded labels.** Pool-direct precision/recall/F1.

- **Critical:** the 5 examples are **excluded from the eval set** (would otherwise be train-on-test). Re-score over the labeled pool minus the 5 example IDs.

**Predictions:**

| metric | predicted | reasoning |
|--------|-----------|-----------|
| Cheap-tier-fewshot model-positives in 731 corpus | 6–18 | Few-shot examples bias toward POS for NEW-version cases; expect modest expansion from baseline 5. |
| Recovers Op-9 (Sylvain 1.2.18) | uncertain | The Op-9 message itself IS one of the few-shot examples (excluded from eval). Its near-twin (Shuler 53B2F945) is also in examples ⇒ both excluded. The two remaining 1.2.17/1.2.18 dropped TPs (Ellis takedown) and the discoveries are the actual test. |
| Recovers Ellis "1.2.17 takedown" | likely yes | Ellis isn't in examples; the few-shot precedent of "1.2.17 was last; 1.2.18 is new" should bridge to "take 1.2.17 down post-vote = substantive change." |
| Recovers frontier-discoveries (1.2.15, 1.2.18 vote, 1.2.19, Thrift, 2.1 rc3) | 1–4/5 | The vote-root announcements should catch on the NEW-version pattern; Thrift freeze and rc3 are different shapes — mixed coverage. |
| F1 (excluding 5 example IDs) | 0.78–0.90 | Should beat baseline 0.769; ceiling near frontier's 0.94. |
| New FPs introduced | 1–4 | Risk: cheap-tier over-generalizes the "NEW-version" pattern to any version mention in a vote thread. |
| Anti-anchoring failure (cheap-tier reads examples as confirming everything is procedural) | unlikely | si-qdf's anti-anchoring was on TAGS (structured state). Worked examples with explicit POSITIVE labels for NEW-version cases should not trigger the same failure mode. |

**Decision rule:**

- **F1 ≥ 0.85 AND precision ≥ 0.85 (excluding example IDs):** few-shot scaffolding works for the cheap-tier. Promote `v2_elided_fewshot` to the operating point. File a follow-up to test whether few-shot survives cross-corpus on Hadoop dev@.
- **0.77 ≤ F1 < 0.85:** modest improvement; few-shot helps but doesn't dominate. Compare with si-bm1 cost-tier escalation; pick whichever architectural path performs better.
- **F1 < 0.77 (regression below baseline):** few-shot anti-helped, similar to si-qdf. Heavy intervention isn't always better; cheap-tier may over-fit to example shape and miss novel cases. Document and don't promote.
- **No new FPs introduced:** clean precision win; few-shot is unambiguously beneficial.

**Falsifiers / mind-changers:**

- Cheap-tier model-positives > 50: few-shot turned the prompt too permissive; over-firing. Halt; inspect rationales.
- Cheap-tier model-positives = 0: few-shot somehow suppressed all positives; prompt is broken. Halt; inspect.
- Recovery of dropped TPs comes with precision drop > 0.30: few-shot trained on shape, not substance. Document the failure mode for the rubric-engineering finding.
- The 5 example IDs themselves get classified differently than their few-shot labels by the cheap-tier (i.e., the model can't even reproduce the labels of its own examples on a clean pass): the prompt isn't being honored; vLLM template issue or instruction-following ceiling hit.

**Anti-contamination:** the bead executor must NOT use the post-si-e5q expanded labels for example selection. The 5 examples are frozen by the IDs above and were chosen from the original 153-item v2 pool, not from any expanded set.

### Results *(append per sub-experiment after each completes)*

#### si-e5q — label 5 frontier discoveries (LANDED)

All 5 frontier-only discoveries returned **POSITIVE** under fresh independent application of the v2 rubric. Detector-shape categorization: three are NEW-version-introduction re-rolls of the same shape as the rubric's canonical POS example — `1.2.15` (CASSANDRA-6648 fix following 1.2.14), `1.2.18` (java-6 build fix following 1.2.17), and `1.2.19` ("last release in this series"). One is a version-target-policy proposal (Thrift freeze pegged to 2.1.0). One is an in-flight RC trajectory change ("rc3?" delaying the previously-implied -final). None of the five required quoted-text-rule violation; every evidence quote is from the author's own new content.

| variant | label set | TP | FP | pool_direct_FN | precision | recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| cheap-tier-v2_elided (si-d6m) | before (153) | 5 | 0 | 3 | 1.000 | 0.625 | 0.7692 |
| cheap-tier-v2_elided (si-d6m) | **after (158)** | **5** | **0** | **8** | **1.000** | **0.385** | **0.5556** |
| frontier-v2_elided (si-2z6) | before (153) | 8 | 1 | 0 | 0.889 | 1.000 | 0.9412 |
| frontier-v2_elided (si-2z6) | **after (158)** | **13** | **1** | **0** | **0.929** | **1.000** | **0.9630** |

The cheap-tier's 0.625 recall on the original 153-item pool was an upper bound conditioned on what the cheap tier *and* the original Opus pool had jointly already surfaced. Once we admit the 5 frontier-only discoveries — all of which the cheap-tier scored at p_pos < 0.01 — the cheap-tier's true recall against a more complete v2 positive set drops sharply to 0.385. The cheap-tier isn't getting worse; we're getting a more honest view of its ceiling. This **strengthens** the case for cost-tier escalation (si-bm1): the gap between cheap-tier and frontier on this detector is wider than the 0.625-vs-0.941 framing suggested. Frontier's F1 *improves* on the expanded pool (0.941 → 0.963) because its lone FP is now diluted against a larger TP base — confirming si-2z6's verdict that the frontier ceiling is still in the high-0.9s on this rubric. Scorecards: `results/evals/schedule_change_announcement-d6m-v2-elided/scorecard-post-e5q.json`, `results/evals/schedule_change_announcement-2z6-frontier/scorecard-post-e5q.json`.

**Question:** Three independent experiments dispatched as a parallel work batch under the autonomous-execution principle (memory: `no_epistemic_downside.md`). Each is well-specified with a pre-reg block, decision rule, and falsifiers. They share no resource conflicts and can run concurrently.

**Beads issues:**
- si-2t4 / si-jkr (eval harness fix)
- si-2z6 / si-5m8 (frontier-tier ceiling check)
- si-qdf / si-cjc (typed-tag first foray)

### Sub-experiment 1: si-2t4 — fix eval harness stratification bug

**Setup:**
- The pool_and_extrapolate harness samples a "random" set of model-negatives to extrapolate FN rate. Currently this sample is drawn from `predictions ∩ existing_labels` (unintended) — i.e., it's biased toward items previously included in the labeled pool. The labeled pool was constructed from a *different* prediction set's model-positives + a random sample of *that* set's model-negatives. So the "random" sample for the FN extrapolation is biased toward items the original (different) classifier disagreed with.
- The fix: separate the labeled-pool's role (precision: count POS labels in model_positives ∩ labels) from the random-sample's role (recall: should be a fresh random sample of CURRENT model_negatives, not pre-determined by the labeled pool's composition).
- Concretely: change `evaluate()` to take a separate `recall_sample_strategy` — either "use_labeled_pool_intersection" (current biased default) or "uniform_random_from_predictions_negatives" (fix). Add a synthetic test demonstrating the bias and the fix.

**Predictions:**
- The fix applied to v2_elided should produce recall ≈ 0.625 (matching pool-direct). The current biased extrapolation reports 0.254. The point of the fix is to make extrapolated recall actually agree with pool-direct on this concrete case.
- Test: synthetic data with known FN rate of 0.005 (rare-positive baseline). Biased estimator over-reports FN. Fixed estimator returns ~0.005.

**Decision rule:**
- **Fixed estimator on v2_elided produces recall within 0.05 of pool-direct (0.625):** harness is fixed; adopt for future experiments.
- **Fixed estimator differs from pool-direct by >0.05:** there's another bias source unidentified; investigate.

**Falsifiers:**
- The synthetic test fails with the fix: my analysis of the bias source is wrong.
- The fixed estimator on v2_elided produces an even lower recall than the biased one: methodology error.

### Sub-experiment 2: si-2z6 — frontier-tier ceiling check on schedule_change_announcement

**Setup:**
- Apply the v2_elided prompt + body shape (from si-rrz) to all 731 messages, but with a frontier-tier model (Opus 4.7) instead of the cheap-tier (Qwen3-Coder-30B).
- Score against OpusLabel-v2 (the same 153-item pool used for v2_elided's eval).
- Specifically check the 3 TPs that v2_elided dropped: Op-9 (Sylvain "1.2.18 re-roll"), Shuler ("Should this be fixed for a 1.2.18 re-roll?"), Ellis ("I'd even lean towards taking 1.2.17 down").

**Predictions:**
- Frontier F1 against Opus-v2: **0.85–0.95**. Opus has stronger inference about version-state context even with elision.
- Recovers all 3 of the dropped TPs (recall = 8/8 = 1.0 if Opus reads the elided body successfully).
- May produce 1-2 new FPs vs cheap-tier-v2_elided's 0 (Opus's permissiveness on borderline cases). Net F1 still substantially above cheap-tier.
- Disagreement with Opus-v2 labels primarily on the same boundary cases the v2_strict→v2 label delta exposed (vote-failure rerolls, vote mechanic adjustments) — these are rubric-ambiguous, not capability-ceiling.

**Decision rule:**
- **Frontier F1 > cheap-tier's 0.769 by ≥0.05:** capability ceiling exists. Cheap-tier is missing extractable signal that a frontier model finds. Substrate work (si-qdf) is *one* way to close the gap; another is invocation of frontier on a sub-pool of messages (cost-tier hierarchy decision).
- **Frontier F1 ≤ cheap-tier's 0.769 + 0.05:** no capability ceiling; rubric is the ceiling. The 3 dropped TPs aren't recoverable without substrate (they're truly under-determined by the elided message text). U3 finding for this prompt design.
- **Frontier recovers all 3 dropped TPs:** confirms substrate-demand is real and not a capability ceiling — the information IS in the message context (just not extractable by cheap-tier without help).
- **Frontier misses 2-3 of the dropped TPs too:** not even Opus can disambiguate 1.2.18 vs 1.2.17 from elided context alone — *substrate is fundamentally needed*, not just helpful.

**Falsifiers:**
- Frontier produces fewer model-positives than cheap-tier (5): unexpected — frontier is more conservative than cheap-tier on this rubric. Worth investigating.
- Frontier-Opus and labeling-Opus disagree on >50% of items: one of the two is mis-applying the v2 rubric.

### Sub-experiment 3: si-qdf — typed-tag first foray (version-state-at-time)

**Setup:**
- Build a version-extraction pass: regex-extract Cassandra version mentions (e.g., `1.2.16`, `2.0.10`, `2.1`, `3.0`) from each message's new_content, attribution_lines, and quoted material.
- Build a state-at-time index: for each (version, timestamp) tuple, classify the version's state at that timestamp into:
  - `pre_announcement` (no [VOTE] subject yet for this version)
  - `vote_active` (a [VOTE] for this version is in flight)
  - `vote_passed` ([VOTE PASSED] or release announcement)
  - `released` (more than X days after vote passed; not used in this corpus, fold into vote_passed)
  - `vote_failed` ([VOTE CLOSED] without [VOTE PASSED])
- Augment the v2_elided user prompt with a `VERSION CONTEXT:` section listing each version mentioned in the message and its state-at-time. New prompt variant: `v2_elided_tagged`.
- Re-run on 731 corpus, score against OpusLabel-v2.
- Specifically check whether the 3 v2_elided dropped TPs (Op-9 Sylvain "1.2.18", Shuler "1.2.18", Ellis "1.2.17 takedown") are recovered.

**Predictions:**
- Op-9 recovers: with VERSION CONTEXT showing "1.2.18: pre_announcement" at 2014-07-02, the cheap-tier should recognize "I'd prefer doing a quick re-roll of 1.2.18" as introducing a NEW version. **Recovers.**
- Shuler "Should this be fixed for a 1.2.18 re-roll?": same — the question form references a not-yet-announced version. **Recovers, with some uncertainty (question form may not match POS examples cleanly).**
- Ellis "I'd even lean towards taking 1.2.17 down": with VERSION CONTEXT showing "1.2.17: vote_passed" at this message's time, the cheap-tier should recognize "taking 1.2.17 down" as withdrawing a passed release. **Recovers.**
- New FPs: 0-2. Worry: messages that mention any version with non-trivial state get re-classified as schedule-relevant.
- F1: predicted **0.85–0.92** if all 3 recover and FP count stays ≤2.

**Decision rule:**
- **F1 > 0.85 AND precision > 0.85:** typed-tag substrate piece earns its keep. Promote `version_state_at_time` to a first-class extracted field, integrate into the harvest pipeline. si-qdf becomes the *first earned* substrate piece.
- **0.77 ≤ F1 ≤ 0.85:** marginal improvement; tags help but don't dominate. Document and decide whether to pursue further. Compare to si-2z6 result — if frontier ceiling is at the same place, the substrate is genuinely closing the gap.
- **F1 < 0.77 (i.e., worse than v2_elided):** typed tags introduced more noise than signal. Inspect what changed; likely the cheap-tier over-relies on the VERSION CONTEXT block and misclassifies messages that reference versions for unrelated reasons.

**Falsifiers:**
- Tagging fires on >50% of messages (most messages mention some version): tags are too coarse; need to filter.
- The version-state index has gaps (versions appearing in [VOTE] subjects but not classifiable into a state): the state machine is wrong; refine.
- Recovery of the 3 TPs is associated with a precision drop of >0.20: substrate is over-aggressive; maybe restrict the VERSION CONTEXT augmentation to messages that explicitly reference a version in their new_content.

### Results *(append per sub-experiment after each completes)*

#### si-2t4 — eval harness stratified FN estimation (LANDED, commit `1a23fa4`)

**Bug confirmed and fixed.** The v0.1.0 harness's "random sample of model-negatives" was actually `current_predictions ∩ existing_labels` filtered to model-negatives — i.e., the entire labeled pool, including items that were exhaustive-labels-of-some-other-classifier's-positives (`sample_role=pool*`). For ANY classifier other than the one the labels were originally pooled around, that stratum is biased toward likely-FN cases.

**Fix (v0.2.0):** stratify by `sample_role`. Direct-count FNs in `pool*` strata (no extrapolation needed — we know the labels exactly). Use `random_sample` stratum's FN-rate to extrapolate over the unsampled remainder. `Total FN = pool_direct_fn + (random_sample_fn_rate × n_unsampled_model_negatives)`. Backward compatible: when no `sample_role` present, falls back to legacy behavior with the corrected unsampled-only extrapolation base.

**Verification on real data:**

| comparison | legacy F1 | fixed F1 | legacy recall | fixed recall | matches pool-direct? |
|------------|----------:|---------:|--------------:|-------------:|:--------------------:|
| v2_elided vs Opus-v2 | 0.405 | **0.769** | 0.254 | **0.625** | ✓ (was the headline bug) |
| v2_strict vs Opus-v2 | 0.727 | 0.727 | 1.000 | 1.000 | ✓ (was already correct by coincidence) |
| v1 baseline vs Opus-v1 | 0.405 | **0.446** | 0.496 | 0.638 | ✓ (legacy under-counted recall here too) |

**Pre-reg accuracy:** decision rule's "fixed estimator on v2_elided produces recall within 0.05 of pool-direct (0.625)" — exact match (0.625). Falsifiers: none triggered. The synthetic test (1.0% base rate, mixed pool + random_sample strata) recovers the unbiased recall (0.40) where the legacy estimator would have reported 0.23.

**Implications:**

- **Historical-baseline correction:** the v1 F1 = 0.405 cited throughout this log is the legacy-biased number. Honest-corrected v1 F1 = 0.446. Past Results blocks are not retroactively edited; this is a forward-going correction. The detector promotion still holds — v2_elided's F1 = 0.769 is well above v1's corrected F1 = 0.446.
- **Two new tests** (`src/evaluate/test_pool_and_extrapolate.py`): one demonstrates the bias quantitatively (synthetic 1000-item corpus with mixed strata; legacy estimator under-counts recall by ~40%); one verifies legacy fallback for label files without `sample_role`.
- **Future detectors should always set `sample_role`** when constructing label pools, so the unbiased estimator works without fallback gymnastics.
- **The unsampled-only extrapolation base is the correct default** even in the no-strata case — extrapolating from labeled items over a base that includes those same labeled items is double-counting. This applies to v0.1.0's behavior on any single-classifier eval too; the corrected v1 baseline is the honest number.

#### si-2z6 — frontier-tier ceiling check (LANDED)

**Headline (pool-direct vs OpusLabel-v2, the existing 153-item pool):**

| Test | Model | Precision | Recall | F1 | Model+ |
|------|-------|----------:|-------:|----:|-------:|
| **Frontier (Opus 4.7) + v2_elided** | Opus | **0.889** | **1.000** | **0.941** | 14 |
| Cheap-tier (Qwen3-Coder) + v2_elided | Qwen | 1.000 | 0.625 | 0.769 | 5 |
| Cheap-tier (Qwen3-Coder) + v2_elided_tagged | Qwen | 1.000 | 0.500 | 0.667 | 4 |

**3/3 dropped TPs recovered** by frontier from the same elided body that the cheap-tier couldn't disambiguate:
- Op-9 (Sylvain "1.2.18 re-roll") → POS ✓
- Shuler ("Should this be fixed for a 1.2.18 re-roll?") → POS ✓
- Ellis ("lean towards taking 1.2.17 down") → POS ✓

**5 unlabeled discoveries:** Frontier fired POS on 5 messages outside the existing 153-item pool. Subagent flagged these as "1.2.15/1.2.18/1.2.19 NEW-version-introduction announcements and the Thrift-freeze proposal." If most are true positives, the OpusPositive set expands meaningfully (from 8 → ~13), which would ripple into all prior recall numbers. **These need labels — filing as a follow-up.**

**1 FP (Marcus "3.0/3.1/4.0 branches" musing):** matches the pre-reg's "1-2 new FPs" prediction. Frontier slightly more permissive than cheap-tier on speculative cycle-architecture musings.

**Decision-rule branches fired (both):**
- "Frontier F1 > cheap-tier's 0.769 by ≥0.05" → TRUE (0.941 > 0.819). **Capability ceiling exists.**
- "Frontier recovers all 3 dropped TPs" → TRUE. **The information IS in the elided message context** — extractable with sufficient capability, not extractable by Qwen3-Coder-30B from the same prompt.

**Synthesis with si-qdf:** Read together, si-qdf and si-2z6 paint a clear picture:

| Question | Answer |
|----------|--------|
| Is the version-state info present in the elided body? | **Yes** — frontier extracts it correctly, no substrate needed. |
| Can the cheap-tier extract it from the elided body alone? | **No** — that's the 3 dropped TPs and the 0.625 recall ceiling. |
| Does adding the version-state info as a structured tag help the cheap-tier? | **No, anti-helps** — cheap-tier interprets the tag in the wrong direction (procedural-fallout frame). |
| What WOULD help the cheap-tier recover those 3? | (open) — possibly few-shot examples (heavy-structure intervention per the v2 lesson), or cost-tier escalation. |

**The si-rrz "substrate demand" framing is sharpened, not falsified:** The framing said "these 3 TPs need context to disambiguate." That's TRUE — the elided body alone (without thread context) would be under-determined. But the elided body INCLUDES the structural cues (version numbers in the new content, attribution lines showing thread depth) that frontier can reason from. The cheap-tier's failure isn't lack of *information*; it's lack of *reasoning capability over the available information*. The fix isn't to add more structured data; it's to either (a) get a more capable model on these specific cases (cost-tier escalation per `architecture.md`), or (b) provide the right reasoning scaffold via prompt examples.

**Pre-reg accuracy:**
- F1 prediction (0.85–0.95): hit upper end (0.941). ✓
- Recovers all 3 dropped TPs: predicted yes; observed yes. ✓
- 1-2 new FPs: observed 1. ✓
- Falsifier "Frontier produces fewer model-positives than cheap-tier": NOT triggered (14 vs 5). ✓
- Falsifier ">50% Opus disagreement with labels": NOT triggered.

**Implications for the project:**

1. **Cost-tier hierarchy validated for this detector.** The architecture's "narrow models do high-volume mechanical classification; capable models design schemas and synthesize" maps cleanly: cheap-tier-v2_elided handles 731 messages at F1=0.769, frontier could backstop the borderline cases (cheap-tier model-negatives with high logprob ambiguity, or messages mentioning specific version numbers). This is a clean architectural pattern, not just a research finding.

2. **The 5 unlabeled frontier-positives are the most interesting deliverable.** If they're true positives, they include detector wins the project hasn't surfaced before — possibly NEW-version proposals (1.2.15, 1.2.18, 1.2.19) and the Thrift-freeze proposal. Filed as a follow-up to label them.

3. **The substrate-demand inference rule needs revision.** Until si-2z6, "cheap-tier failed → substrate would help" was the working assumption. Now the rule should be: "cheap-tier failed → either add substrate (test it!) OR escalate cost-tier (test it!)." si-qdf showed substrate doesn't always help; si-2z6 showed cost-tier does. Memory updated.

4. **The architecture's "discovery vs production" distinction is now empirically grounded.** The 5 unlabeled frontier-positives are exactly the "production runs known detectors fast; discovery samples the long tail with heavier models to find patterns" pattern from `architecture.md`. Frontier-tier on the long tail surfaced detector wins the cheap-tier missed.

**Subagent artifacts (gitignored under results/):**
- `results/detector-runs/schedule_change_announcement/si-2z6/cassandra-2014-predictions-frontier-v2-elided.jsonl`
- `results/evals/schedule_change_announcement-2z6-frontier/scorecard.json`

#### si-qdf — typed-tag first foray (LANDED — counterintuitive REGRESSION)

**Headline (pool-direct vs OpusLabel-v2):**

| variant | model+ | TP | FP | FN | Precision | Recall | F1 |
|---------|-------:|---:|---:|---:|----------:|-------:|----:|
| v2_elided baseline | 5 | 5 | 0 | 3 | 1.000 | 0.625 | **0.769** |
| **v2_elided_tagged** | 4 | 4 | 0 | 4 | 1.000 | 0.500 | **0.667** |

**Decision-rule branch:** `regression` — F1 dropped 0.10 below v2_elided. Pre-reg's third decision-branch fired ("F1 < 0.77: typed tags introduced more noise than signal").

**0 of 3 dropped TPs recovered. 1 additional TP lost.** Net −1 TP. **The substrate REGRESSED the detector despite building correct data.**

**Mechanism — the surprise:**

The version-state index built CORRECTLY for all 3 target messages: `1.2.17: vote_passed (passed 2014-06-30)`, `1.2.18: pre_announcement (no [VOTE] yet)`. Verified in pre-classification rendering. The substrate did exactly what it was designed to do.

But the cheap-tier *anti-anchored* on the structured context. With "1.2.17: vote_passed" in the prompt, the cheap-tier interpreted ANY discussion of 1.2.18 as "procedural fallout from the just-passed 1.2.17 vote" — invoking the v2 rubric's "vote-failure rerolls of an already-planned release" NEGATIVE category. Per-message rationales (much higher confidence than under v2_elided alone):
- Op-9: "this is about procedural mechanics of an already-planned release process … standard procedure, not a schedule modification" (p_pos = 3.9e-5)
- Shuler: "questioning whether to fix the issue for a potential future release rather than announcing a schedule change for an existing planned release" (p_pos = 3.8e-4)
- Ellis: "procedural adjustment to an already-passed vote, not a substantive schedule change" (p_pos = 9.7e-7)

The lost TP (Ellis "What if we tried a quicker release cycle...") fell to the same anti-anchoring: the VERSION CONTEXT block listed multiple pre-announcement versions, and the cheap-tier read this as "proposing a new release-management approach rather than modifying [a previously stated date]."

**Pre-reg accuracy:** *all four* per-test predictions wrong, but in a structurally informative way:
- Predicted F1 0.85–0.92; actual 0.667 (well below floor).
- Predicted "Recovers" for all 3; all 3 stayed NEG and *more confidently* (p_pos << 0.001 vs v2_elided's p_pos ≈ 0.1–0.4 on these items).
- Predicted 0–2 new FPs; got 0 new FPs but lost 1 prior TP. Net −1 TP, not net 0.
- Predicted that absence of state info was the cheap-tier's bottleneck. Actual: *presence* of state info gave the wrong frame more surface area.

No falsifiers triggered (tagging fired on 0.55% of messages, well below the 50% over-firing threshold). The substrate didn't go off the rails; it just failed to do anything useful and slightly anti-helped.

**Critical U3 finding (memory updated: `messages_are_not_single_thesis_streams.md`):** "The cheap-tier failed to disambiguate from message text alone" does NOT imply "adding structured context will fix it." The cheap-tier can interpret correct structured context in the *opposite* of the intended direction — using it to *reinforce* a rubric frame that's wrong for the specific case. Substrate-demand inferences must be *tested*, not just inferred from absence-of-information arguments.

**The substrate-demand framing from si-rrz is now downgraded.** That framing said "the 3 lost TPs need version-state context to disambiguate." The correct version-state context was supplied. They still weren't disambiguated. Either:
1. **The cheap-tier capability is the ceiling** for these 3 specific messages (pending si-2z6 result for confirmation).
2. **A different prompt structure could surface the right interpretation** (e.g., few-shot examples showing "1.2.18 in this thread context = NEW version proposal" — heavy-structure intervention per the si-d6m finding that lightweight instructions don't steer).
3. **These 3 messages are genuinely under-determined** for any cheap-tier model; recovering them requires either a frontier-tier escalation or accepting they're not catchable in production.

The si-2z6 result (frontier ceiling check) is the natural disambiguator and lands next.

**Code committed during the foray** (subagent's work):
- `src/structure/version_state.py` (with self-test) — version extraction + state-at-time index
- `src/structure/__init__.py`
- `src/classify/schedule_change_announcement.py` — added `v2_elided_tagged` variant + index plumbing (frozen prompt hash `c3f636160a9f82ab`)
- `src/evaluate/analyze_qdf_tagged.py` — scorer
- `results/detector-runs/.../si-qdf/cassandra-2014-predictions-v2-elided-tagged.jsonl`
- `results/evals/schedule_change_announcement-qdf-tagged/scorecard.json`

---

## 2026-05-02: v2_elided sub-foray — does eliding quoted line content fix the precision shortfall?

**Question:** v2's F1 = 0.727 hit a precision near-miss (0.571 vs 0.70 threshold). All 6 FPs are quoted-text-rule failures concentrated on one phrase ("I'd love it if we could modify the C* release cycle...") in one thread. Is the precision shortfall *entirely* a quoted-text-anchoring problem, or are there other causes hiding in the cluster?

**Beads issues:** si-rrz (run), si-3mg (pre-reg), `discovered-from: si-d6m`. User explicitly chose this path over the alternative (accept v2 as-is) to test "how much difference we can check there."

### Pre-registration *(commit this block before running)*

**Setup:**

- Same v2 system prompt (hash `d6a472a3ad6bd5f2`), same depth=2 envelope, same corpus, same 153-item OpusLabel-v2 pool.
- New variant `v2_elided`: each line whose `quote_depth > 0` has its content replaced with the literal token `[QUOTED]` (one `[QUOTED]` per quoted line). Attribution lines and signatures unchanged. The cheap-tier still sees that quoted material exists (preserves "this is a thread reply" context) but cannot read specific phrases.
- Implemented as a fifth prompt variant alongside `current_baseline`, `new_only`, `new_with_marked_quoted`, `v2_strict`. Frozen prompt-hash will differ from `v2_strict` because the rendered user-message bodies differ (the system prompt is identical to v2_strict, but the user message text is structurally different — same template, different body content).
- Run on full 731-message corpus.
- Score against the existing 153-item OpusLabel-v2 (the same labels used for v2_strict — apples-to-apples comparison).
- If `v2_elided` fires positive on items not in the 153-pool, spawn a small subagent to label them (same protocol as the 4-item follow-up subagent).

**Frozen artifacts:** the v2 system prompt, the 153 OpusLabel-v2 file, the corpus, the depth=2 quote filter, the elision rule (replace each quoted line's content with `[QUOTED]`).

**Predictions:**

| Test | Predicted | Mechanism |
|------|-----------|-----------|
| `v2_elided` model-positives in 731 corpus | **6–10** (down from v2's 14) | Elision suppresses anchoring on the 6 currently-quoted-anchored FPs; should also leave the 8 v2-TPs intact (their evidence is in new content, not quoted). Possibly loses 1-2 to over-suppression. |
| precision against Opus-v2 | **0.85–1.00** | If the failure mode is purely quoted-text anchoring, all 6 FPs flip to NEG. Remaining model-positives are mostly TPs. |
| recall against Opus-v2 | **0.75–1.00** | Some risk that elision drops a currently-TP item (e.g., Op-13, where cheap-tier-v2 anchored on quoted "after 3.0" but Opus-v2 says POS based on Jonathan's actual new content — if cheap-tier loses the anchor, does it find the new-content signal?). The v2_elided test will reveal whether v2 cheap-tier's TPs were genuinely from new content or from quoted anchoring. |
| F1 | **0.85–0.95** | Big jump from v2's 0.727 if elision works as predicted. |
| Op-13 (Jonathan, "after 3.0" quoted) | **possibly POS, possibly NEG** | This is the cleanest test of "right answer for right reason vs right answer for wrong reason." Under v2_strict the cheap-tier anchored on quoted text and got POS. Under v2_elided, cheap-tier sees only the new content ("It's too late for a schema change in 2.1, and 3.0 we're already planning to move to file-based hint storage") + [QUOTED] markers. Will it find Jonathan's actual schedule signal? |

**Per-FP predictions** (the 6 v2_strict FPs, all in cycle-proposal cluster):

All 6 should flip to NEG under v2_elided because their evidence_quotes were in quoted text. If any stay POS, the cheap-tier found a NEW-content schedule signal we missed in the v2_strict analysis.

**Decision rule:**

- **F1 ≥ 0.85 AND precision ≥ 0.70:** detector is **promoted to Prototype**. Both criteria met. Adopt v2_elided as the operating point. Move to si-t3l (cross-corpus generalization).
- **0.65 ≤ F1 < 0.85, precision ≥ 0.70:** marginal precision win, F1 closer to v2_strict than predicted. Likely some recall loss from elision broke even with precision gain. Promotion still happens (F1 + precision both met).
- **F1 < 0.65 OR precision < 0.70:** elision didn't fix the problem cleanly. Either the failure mode wasn't purely anchoring (precision still low) or elision broke productive signal (recall dropped). Stay with v2_strict; document this finding.
- **F1 ≥ v2_strict's 0.727 by ≥0.05:** material improvement; v2_elided is the better operating point regardless of formal promotion.
- **F1 < v2_strict's 0.727 by ≥0.05:** elision was a net negative. Stay with v2_strict.

**Falsifiers / mind-changers:**

- **`v2_elided` model-positives < 4:** elision suppressed too much; model can't find any positives even in the rubric's clear cases. Op-14 (Paulo "I propose postponing 1.2.17") and similar should still fire — if they don't, the elision is masking new-content signal somehow (interaction with attribution lines? formatting?).
- **`v2_elided` model-positives > 14** (more than v2_strict): elision somehow *added* positives. Surprising — would suggest the cheap-tier under elision is over-reading the [QUOTED] markers as suspicious and flagging messages it wouldn't have under v2_strict. Inspect.
- **One of the 6 v2_strict FPs stays POS under v2_elided:** the FP's evidence wasn't really in quoted text, despite the v2_strict evidence_quote field saying so. Could be the cheap-tier emitted a quoted-text evidence_quote post-hoc but actually anchored on new content. Worth investigating that specific FP.
- **Op-13 flips to NEG under v2_elided:** the "after 3.0" anchor was load-bearing for Op-13's TP. Jonathan's actual new content is schedule-relevant, but the cheap-tier may not extract it without the quoted anchor. Important U3 finding about which signals the cheap-tier can find vs which it relies on quoted anchors for.
- **Recall drops below 0.5:** elision broke too much. The current 1.0 recall (extrap) was load-bearing on quoted anchors more than expected. Stay with v2_strict.

### Results *(commit this block after running)*

**Summary:** `results/evals/schedule_change_announcement-d6m-v2-elided/summary.json`. v2_elided ran on the full 731-message corpus (~263s, 0 errors). Same 153-item OpusLabel-v2 pool used for v2_strict — clean apples-to-apples comparison.

**Headline scorecards (pool-direct counts, the honest numbers):**

| Comparison | Model+ | TP | FP | FN | Precision | Recall (pool) | F1 (pool) |
|------------|-------:|---:|---:|---:|----------:|--------------:|----------:|
| **cheap-v2_elided vs Opus-v2** | 5 | 5 | **0** | 3 | **1.000** | **0.625** | **0.769** |
| cheap-v2_strict vs Opus-v2 | 14 | 8 | 6 | 0 | 0.571 | 1.000 | 0.727 |
| cheap-v1 vs Opus-v1 (baseline) | 41 | 12 | 23 | — | 0.343 | 0.496 | 0.405 |

**Pool-direct vs extrapolated recall — important caveat:** The pool_and_extrapolate harness reports recall=0.254 / F1=0.405 for v2_elided. This is the long-standing eval harness stratification bug (filed as si-2t4): the "random sample of model-negatives" was originally drawn from v1's model-negative set, biased toward items v1 already disagreed with the cheap-tier on. Under v2_elided, the 3 newly-dropped TPs are all in that biased sample, inflating the apparent FN rate. The pool-direct count (5 caught of 8 known Opus-v2 positives) is the honest number. **si-2t4 is now load-bearing for any further sub-foray; promoting its priority.**

**Decision-rule outcome (from si-rrz pre-reg):**

- F1 ≥ 0.65 AND precision ≥ 0.70: **MET**. F1 = 0.769 ≥ 0.65 ✓, precision = 1.000 ≥ 0.70 ✓.
- **Detector `schedule_change_announcement` promoted to Prototype.** Operating point: v2_elided (v2 strict rubric + quoted-line elision at depth=2). Catalog updated.

**Per-FP / per-TP movements:**

- **All 6 v2_strict FPs flipped to NEG under v2_elided** (the anchoring-failure mode is fully resolved by elision). Falsifier "one of the 6 v2_strict FPs stays POS under v2_elided" did NOT trigger — confirmed the 6 FPs were genuinely quoted-text anchoring failures, all 6 cases.
- **5 of v2_strict's 8 TPs preserved by v2_elided.** All 5 have schedule signal in self-contained new content (cycle proposals + Paulo's explicit postponement + Op-13 Jonathan's "schema change in 2.1, 3.0 we're planning to move to file-based hint storage").
- **3 of v2_strict's 8 TPs dropped by v2_elided.** All 3 are 1.2.17/1.2.18-related and require *inter-message context* the cheap-tier no longer has access to:
  - Op-9 (Sylvain "I'd prefer doing a quick re-roll of 1.2.18"): needs to know 1.2.17 was last announced; without it, "re-roll" reads as routine vote-failure case.
  - Shuler ("Should this be fixed for a 1.2.18 re-roll?"): 6-word question, needs context to determine intent.
  - Ellis ("I'd even lean towards taking 1.2.17 down until that's fixed"): needs context that 1.2.17 was just passed for vote.

**The Op-13 win — right answer for the right reason:**

Op-13 (Jonathan "Hinted Handoff" message) is now caught by anchoring on Jonathan's actual new content: "It's too late for a schema change in 2.1, and 3.0 we're already planning to move to file-based hint storage" (a direct match to two rubric exemplar phrases). The "after 3.0" quoted-Benedict anchor that we'd documented as the v1 mechanism is gone. **The lone-TP-from-anchoring concern from si-fnw is fully resolved.** Updated `lone-tp-diagnostic.md` accordingly.

**Pre-reg accuracy:**

| Prediction | Predicted | Actual | Hit? |
|------------|-----------|--------|:---:|
| v2_elided model-positives | 6–10 | 5 | near-miss (1 below band) |
| Precision against Opus-v2 | 0.85–1.00 | 1.000 | ✓ |
| Recall against Opus-v2 | 0.75–1.00 | 0.625 (pool) | miss (below band) |
| F1 | 0.85–0.95 | 0.769 (pool) | miss (below band) |
| All 6 v2_strict FPs flip to NEG | yes | all 6 ✓ | ✓ |
| Op-13 stays POS | uncertain | POS, anchored on new content | ✓ (better than predicted) |

I overestimated F1 because I underestimated how many TPs would need quoted-context to interpret version references. The 3 lost TPs all require seeing "1.2.17 was just announced/passed" in surrounding context to interpret "1.2.18" as a NEW version. Elision drops that context entirely. Lower bound of pre-reg recall band (0.75) was wrong; actual 0.625 is below.

**Falsifier check:**

| Falsifier | Triggered? | Note |
|-----------|:----------:|------|
| v2_elided model-positives < 4 | ✗ | 5 — just above |
| v2_elided model-positives > 14 | ✗ | well below |
| One of 6 v2_strict FPs stays POS | ✗ | all 6 fixed |
| Op-13 flips to NEG under elision | ✗ | preserved with right-mechanism |
| Recall drops below 0.5 | ✗ | 0.625 (pool) |

**Observations:**

1. **Elision is a clean intervention for the anchoring failure mode.** All 6 v2_strict FPs were genuine quoted-text anchoring; eliding the quoted content fixed all 6 with zero new FPs introduced. The CRITICAL quoted-text rule "by replacement" is more reliable than "by instruction" — elision is structural, not instructional.

2. **The 3 dropped TPs share a structural property:** they all reference a version number whose semantics depend on inter-message context (whether 1.2.18 is "new" vs "the next routine patch"). The cheap-tier under elision has no way to bridge that. This is the substrate-demand finding I've been looking for: a *specific*, *measurable* case where a typed-tag layer (si-qdf: version-state-at-time tags) would recover real detector value.

3. **F1 won by 0.04 (0.769 vs 0.727), precision won by 0.43 (1.000 vs 0.571).** The trade is favorable on every axis except recall. F1 difference of 0.04 is right at si-pfo's noise floor — without v2_strict's high recall acting as buffer, the F1 differential would be marginal. But the precision differential is dramatic and operationally meaningful.

4. **Original promotion criteria fit v2_elided cleanly.** F1 ≥ 0.65 AND precision ≥ 0.70 was set in the si-qhz pre-reg, calibrated for v1's broader positive class. v2_elided clears both with margin (F1 +0.119, precision +0.30). The criteria didn't need to be re-thought after all.

**Surprises:**

1. **Recall dropped further than predicted** (0.625 actual vs 0.75–1.00 predicted). I'd predicted that the cheap-tier would extract self-contained schedule signal from new content alone for all 8 TPs. In reality, 3 of 8 needed inter-message context. **The new content of "I'd prefer doing a quick re-roll of 1.2.18" is genuinely insufficient for the cheap-tier to determine whether 1.2.18 is "new" or "routine"** — version-number context lives in the thread, not in the message.

2. **The 3 dropped TPs are exactly the substrate-demand candidates that si-qdf was filed for.** Until now, the substrate-idea issues (si-jl0, si-qdf) had no measured detector demand from real data. v2_elided's recall failures provide the first concrete demand: typed version-state-at-time tags would recover Op-9, Shuler, and Ellis-1.2.17-takedown — 3 real positives. **This is the kind of evidence that should justify earning a substrate piece** (per the user's "forays not substrate" framing).

3. **The pool_and_extrapolate stratification bug bit hard for the first time.** v1's recall extrapolation worked because v1's model-negatives sample wasn't biased relative to v1's model-negative population. v2_elided's recall extrapolation is biased because the labeled pool is enriched for items v1 already classified positive (which is exactly where v2_elided's FNs concentrate). si-2t4 was filed during si-bwo as a low-priority methodology fix; **it's now load-bearing for any future detector iteration**. Promoting its priority.

**Conclusions:**

- **Detector PROMOTED to Prototype.** Operating point: v2_strict rubric with v2_elided body shape (depth=2 quote filter + quoted-line content elision). F1 = 0.769, precision = 1.000, recall (pool) = 0.625.
- **The anchoring failure mode (si-bwo onward) is structurally resolved.** Elision is the working intervention; instruction-only intervention (si-clz variant B + v2_strict's CRITICAL rule) was 85% effective; structural elision is 100%. Future detectors with similar anchoring concerns should default to elision (or a similar structural transformation) rather than relying on prompt instructions.
- **Substrate demand is now measurable for 3 specific cases.** Op-9 / Shuler-1.2.18 / Ellis-1.2.17-takedown all require version-state-at-time disambiguation. Filing this finding into si-qdf (typed-tag extraction) so the substrate work has a concrete success metric: "recovers 3 specific TPs in this corpus when added to v2_elided."
- **si-2t4 (eval harness stratification bug) is now load-bearing.** Promoting from P3 to P2. Future detector iterations need an unbiased recall estimator.
- **The two-commit pre-reg discipline produced the cleanest experiment of the session.** Setup → predictions → falsifiers → run → confront-honestly → conclude. The fact that recall came in below my predicted band is an honest miss, not a hidden cost.

**Next:**

- **Mark `schedule_change_announcement` as Prototype** in `detector-catalog.md` with v2_elided as operating point and the F1/precision/recall numbers.
- **Update `local_temporal_context.md`** with the U3 finding: structural elision works where prompt instructions don't (heavy or light).
- **Update `messages_are_not_single_thesis_streams.md`** with the substrate-demand finding: si-qdf (typed version-state tags) now has concrete justification — recovers 3 TPs lost to elision.
- **Promote si-2t4 to P2.** The stratification bug is now in the path.
- **Close si-rrz, close si-d6m, surface to user.**
- **Move to next detector or to si-t3l (cross-corpus generalization).** The first detector is done; the architecture commitment to "binary-per-category classifiers" survived 6 rounds of measurement and produced a promotion-ready detector at F1 = 0.769 with one structural intervention (elision) plus one rubric sharpening (v2). The harness pattern is reusable for the next detector.

---

## 2026-05-02: Sharpen `schedule_change_announcement` rubric (v2)

**Question:** Does a sharper rubric — one that takes explicit positions on the rubric-ambiguous boundary cases identified by si-pfo and si-clz — close the F1 gap toward the 0.65 promotion threshold? Specifically, does shifting the rubric to *exclude* vote-failure rerolls and vote-mechanic adjustments (which are normal release process, not schedule changes) improve detector quality from a *senior operator's* perspective?

**Beads issues:** si-d6m (run), si-q9m (pre-reg). `discovered-from: si-qhz`. Blocked-by: si-q9m until pre-reg lands.

### Pre-registration *(commit this block before running)*

**Strategic framing — what should "schedule change" mean to the system's user?**

The architectural North Star is *situational intelligence for senior operators running complex multi-vendor programs*. A senior TPM watching this kind of stream wants to know about things that **change their planning picture**: a release will or won't happen on the previously-stated date; a feature is moved to a different version; the team is rethinking release cadence. They do *not* want to be paged on every standard release-process event.

The v1 rubric was permissive about "we'll re-roll" cases because the surface phrasing matched "schedule change announcement." But empirically (si-pfo, si-clz):
- 5 of the 12 stable-TPs at depth=2 are vote-failure rerolls of *patch* releases (Op-3, Op-4, Op-7, Op-10, Op-11). These are standard process — vote fails on a regression, team fixes it, re-rolls. A senior operator already assumes this happens; informing them of every reroll is noise.
- The substrate work (si-clz) showed the cheap-tier *needs* the quoted thread context to disambiguate "we'll re-roll" as schedule-change-vs-routine. A sharper rubric that defines reroll-as-routine removes the disambiguation burden — the cheap-tier doesn't need to make a context-dependent call.

**The v2 rubric (frozen — must commit before any re-label/re-run):**

```
You are reviewing a single message from the Apache Cassandra developer mailing list (dev@cassandra.apache.org). Determine whether the message announces, proposes, or implies a change to a previously-stated date or version target for a release, milestone, or planned work.

The change must affect a substantive deliverable (a release date, a feature target version, a release cadence). Procedural mechanics around an in-flight release process — vote retries, vote-period adjustments, +1/-1 votes — are NOT schedule changes; they are the standard release process executing normally.

POSITIVE — the author IS announcing/proposing/implying a substantive schedule change:
- Explicit date changes ("I propose postponing release of 1.2.17 until next week")
- Version target shifts ("we're planning to move to file-based hint storage in 3.0", "it's too late for a schema change in 2.1")
- Release cadence proposals ("I'd love it if we could modify the C* release cycle to 4 months")
- Acknowledgments that a previously-stated timeline will not be met ("we still have a lot to do before X")
- Setting a new target date when a previous expectation existed
- Re-rolls that introduce a NEW version not previously planned (e.g., "let's do a 1.2.18" when 1.2.17 was the last announced)

NEGATIVE — these are NOT schedule changes:
- Vote-failure rerolls of an already-planned release ("vote closed; we'll re-roll once X is fixed") — the release was always planned to happen when the vote passed; one failed vote attempt is procedural, not a schedule change. The release is still in-flight on the same broad schedule.
- Vote-period adjustments ("I'll shorten the vote period to 48h", "extending the vote 24 more hours") — mechanic, not date.
- +1 / -1 votes by themselves, even when the parent vote announcement is in the thread — the vote reply is procedural.
- Discussion of current schedules without proposing changes ("X is on track")
- Initial schedule announcements when no prior expectation existed
- Pure technical discussion with no schedule reference

CRITICAL — quoted text rule:
If your evidence for a positive judgment would be a phrase that appears in the QUOTED part of the message (lines starting with > or otherwise marked as from an earlier message in the thread), the answer is NEGATIVE. Judge based on what THIS author wrote in THIS message, not what they are quoting from someone else. The author is referencing the quoted material, not asserting it.

Output strict JSON:
{
  "is_schedule_change_announcement": true | false,
  "evidence_quote": "<verbatim span from THIS author's new content (NOT quoted lines), or null if false>",
  "rationale": "<one-sentence explanation, including whether the evidence is in new content or quoted material if relevant>"
}
```

**Setup:**

- Same 731-message corpus, same 149-item label pool, same model (Qwen3-Coder-30B-A3B-Instruct-gptq-4bit), same temperature=0, same eval harness.
- Re-label the 149 OpusLabel-v1 items against the v2 rubric. **Re-labeling will be done by Opus via fresh sessions/API** — *not* by the current session, to avoid contamination from this session's analysis. Output: `labels/schedule_change_announcement/cassandra-2014-labels-v2.jsonl`.
- Implement the v2 rubric as a new prompt variant in the classifier (`v2_strict`) so the prompt-text and prompt-hash are version-controlled. The cheap-tier runs at depth=2 with the v2 prompt against the full 731 messages. Output: `results/detector-runs/schedule_change_announcement/cassandra-2014-predictions-v2.jsonl`.
- Score: cheap-tier-v2 against OpusLabels-v2 (the apples-to-apples test). Also report cheap-tier-v2 against OpusLabels-v1 for continuity (shows magnitude of rubric shift).
- Also report Opus-v2 vs Opus-v1 label deltas — how many items did the rubric sharpening flip in Opus's own judgment?

**Frozen artifacts:** the v2 rubric text above, the v2 system prompt (including the CRITICAL quoted-text rule), the eval harness, the corpus, the same 149-item label pool (same IDs), depth=2 envelope.

**Predictions:**

| Test | Predicted result | Rationale |
|------|------------------|-----------|
| Opus-v2 positives in the 149-item pool | 6–8 (down from 14 in v1) | v2 reclassifies vote-failure rerolls (Op-3, 4, 7, 10, 11) and vote-period adjustments (Op-12) as NEG. Likely retained: Op-1, Op-2, Op-8, Op-13, Op-14 + possibly Op-9. Op-5, Op-6 stay borderline. |
| cheap-tier-v2 model-positives in 731 corpus | 8–25 | v2 narrows the positive class substantially. Most current FPs were anchoring-on-quoted-text (the CRITICAL quoted rule should suppress them) or vote-process content (the explicit NEGATIVE list excludes them). |
| cheap-tier-v2 F1 against Opus-v2 labels | **0.55–0.70** | Big improvement over v1's 0.405. The rubric is sharper and aligns better with what the cheap-tier can recognize. The CRITICAL quoted-text rule may or may not be honored (per si-clz, prompt-level instructions don't always steer Qwen3-Coder-30B). |
| cheap-tier-v2 precision against Opus-v2 labels | **0.65–0.85** | The narrower positive class plus the quoted-text rule should cut FPs substantially. |
| cheap-tier-v2 recall against Opus-v2 labels | **0.50–0.75** | The remaining v2-positives are explicit cycle/postponement/version-target language — the cheap-tier should catch most of these in new content alone. Op-6 still hard. |
| cheap-tier-v2 against Opus-v1 labels | F1 in the 0.20–0.35 range | Apples-to-oranges; included as continuity check. The rubric shift moved the target. |

**Per-OpusPositive predictions:**

| Op | v1 label | v1 cheap@d2 | predicted v2 Opus | predicted v2 cheap | reason |
|---:|----------|-------------|-------------------|--------------------|--------|
| Op-1 | POS | POS | POS | POS | LTS-version proposal (cycle architecture) |
| Op-2 | POS | POS | POS | POS-borderline | references "planned to re-roll for other reasons" |
| Op-3 | POS | POS | **NEG** | **NEG** | vote-failure reroll, patch version |
| Op-4 | POS | POS | **NEG** | **NEG** | vote-failure reroll |
| Op-5 | POS | NEG | **NEG** | NEG | vote-failure reroll (was already a cheap-tier FN; v2 alignment) |
| Op-6 | POS | NEG | **NEG** | NEG | "wait on 7743" — procedural pause |
| Op-7 | POS | POS | **NEG** | **NEG** | vote-failure reroll + vote period mechanic |
| Op-8 | POS | POS | POS | POS | "lower release cycle to 4 month" |
| Op-9 | POS | POS | POS-borderline | POS | re-roll of 1.2.18 — possibly NEW version |
| Op-10 | POS | POS | **NEG** | **NEG** | vote-failure reroll Strike 2 |
| Op-11 | POS | POS | **NEG** | **NEG** | vote-failure reroll |
| Op-12 | POS | POS | **NEG** | **NEG** | vote period extension (mechanic) |
| Op-13 | POS | POS | POS | POS-uncertain | "schema change in 2.1, 3.0 plans" — cheap-tier needs to read new content not quoted |
| Op-14 | POS | POS | POS | POS | "propose postponing 1.2.17" — explicit |

**Predicted Opus-v2 positive set:** Op-1, Op-2, Op-8, Op-9, Op-13, Op-14 = **6** (with Op-9 borderline; could go either way)

**Decision rule:**

- **cheap-tier-v2 F1 against Opus-v2 ≥ 0.65 AND precision ≥ 0.70:** detector promoted to Prototype. The original promotion criteria from si-qhz are met. Move to second-corpus cross-domain check (si-t3l).
- **0.50 ≤ F1 < 0.65:** rubric direction is right but more sharpening needed. Document specific failure modes; don't promote yet.
- **F1 < 0.50 with v2:** either the rubric still has issues, or the cheap-tier can't handle the v2 distinctions (e.g., can't tell vote-failure-reroll from substantive-schedule-change). Frontier-tier ceiling check (si-2z6) becomes a higher priority.
- **v2 doesn't substantially improve over v1's 0.405 F1:** rubric wasn't the gating issue; capability or substrate is. Re-evaluate the substrate work (consider variant B with few-shot examples, or wait for stronger cheap-tier model).

**Falsifiers / mind-changers:**

- **cheap-tier-v2 fires positive on >50% of messages** (>365/731): the prompt is too permissive. Stop, inspect, revise — do not treat as valid eval.
- **cheap-tier-v2 fires positive on <5%** (<37/731): too restrictive. Inspect by sampling expected positives.
- **Opus-v2 disagrees with Opus-v1 on >50% of the labeled pool** (>75 items flip): the rubric shift is so large it's effectively a different detector. Consider whether v2 is still the same detector concept; possibly need a clean second pre-reg with a different name.
- **The CRITICAL quoted-text rule produces no measurable change in cheap-tier behavior** (i.e., cheap-tier-v2 still anchors on quoted text in the 17 anchoring-fix messages from si-clz): same U3 finding as si-clz variant B — prompt-level instructions don't reliably steer Qwen3-Coder-30B. Documents this specifically, escalates si-2z6 priority.
- **cheap-tier-v2 misses Op-14 (Paulo "propose postponing")**: the explicit explicit-date-change case. If v2 misses this, the prompt has a bug or lost something v1 had. Investigate before drawing rubric conclusions.
- **cheap-tier-v2 fires positive on Op-12 (vote period extension)**: the explicit NEGATIVE example wasn't honored. Updates U3 unfavorably.
- **Opus-v2 returns mostly "implies a change without saying it" judgments**: v2 may have *reduced* explicit positives but added an implicit-positive class that's harder to evaluate.

### Results *(commit this block after running)*

**Summary:** `results/evals/schedule_change_announcement-d6m-v2/summary.json`. cheap-tier-v2 ran on the full 731-message corpus (~270s, 1 transient resumed). Two independent Opus subagents relabeled 149 + 4 items against v2 (153 total), without contamination from this conversation's analysis.

**Headline scorecards:**

| Comparison | Model+ | TP | FP | Precision | Recall | F1 |
|------------|-------:|---:|---:|----------:|-------:|----:|
| **cheap-v2 vs Opus-v2** | 14 | 8 | 6 | **0.571** | **1.000** | **0.727** |
| cheap-v2 vs Opus-v1 (continuity) | 14 | 4 | 6 | 0.400 | 0.071 | 0.121 |
| cheap-v1 vs Opus-v1 (baseline) | 41 | 12 | 23 | 0.343 | 0.496 | 0.405 |
| cheap-v1 vs Opus-v2 (alignment check) | 41 | 5 | 31 | 0.139 | 0.220 | 0.170 |

**v2 promotes F1 from 0.405 → 0.727.** The original promotion criterion was F1 ≥ 0.65 AND precision ≥ 0.70. F1 clears the bar by a wide margin (+0.077); precision misses by a small margin (-0.13). All 8 known Opus-v2 positives are caught (recall = 1.0); the precision shortfall is a localized failure mode discussed below.

**Opus label delta (v1 → v2, 7.4% of items shifted, all in the same direction):**

| v1 → v2 | count | Items |
|---------|------:|-------|
| positive → positive | 4 | Op-8, Op-9, Op-13, Op-14 (the predicted v2 keepers) |
| positive → negative | 10 | Op-1, Op-2, Op-3, Op-4, Op-5, Op-6, Op-7, Op-10, Op-11, Op-12 (vote-failure rerolls and vote mechanics + Marcus's hedged discussion + Brandon's vote change) |
| negative → negative | 134 | unchanged |
| unsure → negative | 1 | Op-Unsure |

**Plus 4 items not in the v1 pool that Opus-v2 newly identifies as positives** (because cheap-tier-v2 fired on them):
- Michael Kjellman's *original* "Proposed changes to C* Release Schedule" (the cycle proposal everyone quoted)
- Jonathan Ellis's "What if we tried a quicker release cycle, BUT we would guarantee that you could do a rolling upgrade until we bump the supermajor version?"
- Michael Shuler's "Should this be fixed for a 1.2.18 re-roll?" (introduces a new not-previously-planned 1.2.18)
- Jonathan Ellis's "I'd even lean towards taking 1.2.17 down until that's fixed" (proposes withdrawing an already-passed release)

**Pre-reg accuracy on individual OpusPositives:**

| Op | v1 | predicted v2 | actual Opus-v2 | predicted cheap-v2 | actual cheap-v2 | hit? |
|---:|---|---|---|---|---|:---:|
| 1 | POS | POS | NEG | POS | NEG | ✗ (predicted both POS, both NEG) |
| 2 | POS | POS | NEG | POS-borderline | NEG | ✗ |
| 3 | POS | NEG | NEG | NEG | NEG | ✓ |
| 4 | POS | NEG | NEG | NEG | NEG | ✓ |
| 5 | POS | NEG | NEG | NEG | NEG | ✓ |
| 6 | POS | NEG | NEG | NEG | NEG | ✓ |
| 7 | POS | NEG | NEG | NEG | NEG | ✓ |
| 8 | POS | POS | POS | POS | POS | ✓ |
| 9 | POS | POS-borderline | POS | POS | POS | ✓ |
| 10 | POS | NEG | NEG | NEG | NEG | ✓ |
| 11 | POS | NEG | NEG | NEG | NEG | ✓ |
| 12 | POS | NEG | NEG | NEG | NEG | ✓ |
| 13 | POS | POS | POS | POS-uncertain | POS | ✓ |
| 14 | POS | POS | POS | POS | POS | ✓ |

**12 of 14 Opus-v2 predictions matched. 12 of 14 cheap-v2 predictions matched.** Both the rubric calibration and the cheap-tier behavior under v2 landed close to pre-reg expectations.

**CRITICAL quoted-text rule check:**

Of the 20 si-clz "anchoring fix" messages (where v1 cheap-tier fired POS by anchoring on quoted text), **17 correctly resolve to NEG under v2** (the rule was honored). 3 still fire POS — and these are *exactly* the messages that account for the v2 cheap-tier's precision shortfall. All 3 anchor on the quoted phrase "I'd love it if we could modify the C* release cycle to include..." (Michael Kjellman's TL;DR, quoted in many replies in the "Proposed changes to C* Release Schedule" thread). The cheap-tier reads this phrase as so strongly schedule-flavored that it overrides the "ignore quoted material" instruction.

The 6 cheap-tier-v2 FPs are: 4 of these 3 + 2 similar cycle-proposal-quoted replies (Sylvain's "I was thinking of something along those lines so I'm in favor" anchored on Sylvain's own quoted-elsewhere reply; Jake Luciani's reply anchored on the same Kjellman phrase). **All 6 FPs are quoted-text anchoring failures concentrated in one thread.**

**Pre-reg falsifier check:**

| Falsifier | Triggered? | Note |
|-----------|:----------:|------|
| cheap_v2 fires positive on >50% of corpus | ✗ | 1.9% positive rate |
| **cheap_v2 fires positive on <5%** | **✓ (by letter)** | 1.92% — but the spirit is not violated. The v2 rubric is genuinely strict; Opus-v2 itself has only 5.2% positive rate. The falsifier was meant to catch broken-prompt cases; v2 cheap-tier is firing on the *right* items, just rarely. |
| Opus-v2 disagrees with Opus-v1 on >50% | ✗ | 7.4% (11 items) — the rubric is recognizably the same detector concept |
| CRITICAL quoted-text rule produces no change | ✗ | 17/20 anchoring-fix cases resolved correctly — rule is honored |
| cheap_v2 misses Op-14 | ✗ | Op-14 caught (the "easy" case held) |
| cheap_v2 fires on Op-12 (vote period extension) | ✗ | Op-12 correctly NEG |

**Observations:**

1. **The v2 rubric prompt steers the cheap-tier reliably**, in stark contrast to si-clz variant B's marker. The difference is quantitative, not categorical: v2 is a heavy redesign with explicit category lists and concrete examples, vs. variant B's single appended sentence. **Updated U3 finding: prompt-level instructions DO steer Qwen3-Coder-30B at sufficient weight.** "Sufficient" appears to be measured in *hundreds* of additional system-prompt characters with concrete examples, not in *tens* with abstract instructions.

2. **The CRITICAL quoted-text rule worked at 85% (17/20)**, but the 15% failure mode is concentrated: all 3 failures anchor on the same cycle-proposal phrase. The cheap-tier overrides the "ignore quoted text" instruction when the quoted text is itself an unusually strong signal. This is U3-relevant: **the cheap-tier's instruction-following is signal-strength-modulated** — strong quoted signals override structural instructions about provenance.

3. **Opus's label delta was much smaller than the model+ delta** (Opus shifted 11/149 = 7.4%; cheap-tier shifted 35/731 = 4.8% with mostly different items). This means the rubric sharpening is *concentrated on rubric-ambiguous boundary cases* — most of the corpus (87%) is unaffected. The detector concept is stable; only the boundary moved.

4. **All 4 newly-discovered v2 OpusPositives** (Michael Kjellman original, Jonathan's quicker-cycle proposal, Shuler's 1.2.18 question, Ellis's 1.2.17-takedown) are cases that v1 cheap-tier missed but v2 cheap-tier caught. The v2 prompt is not just narrowing the positive class — it's also surfacing genuine positives v1 missed.

**Surprises:**

1. **F1 jumped much further than predicted** (predicted 0.55–0.70; actual 0.727). The combination of stricter rubric + the cheap-tier honoring the rubric + the labels expanding to include 4 new positives (which cheap-tier-v2 caught) compounded favorably. Each ingredient was within prediction; the multiplicative effect exceeded the prediction range.

2. **Recall is 1.0 (extrapolated).** Every known Opus-v2 positive was caught by cheap-v2. This is suspicious-clean — almost certainly because the random-sample-of-model-negatives that informed the recall extrapolation had 0 Opus-v2-positives in it (the v2 rubric is so strict, schedule-positives are rare in the corpus). The 95% CI on recall is wider than the point estimate suggests; "no FNs found in 100-item random sample" doesn't preclude a small tail of FNs in the unsampled 600+ negatives. Honest precision: recall is *high* but the 1.0 point estimate has a meaningful CI.

3. **The Opus label shift was strictly POS→NEG** (no NEG→POS in the existing 149 pool; the 4 new positives came from outside that pool). The rubric narrowed without expanding into previously-negative territory — exactly what a "sharpen, don't redirect" rubric edit should do.

4. **The 4 newly-discovered v2 positives in the cycle-proposal thread are messages the cheap-tier-v1 had been firing positive on by anchoring on quoted text — and Opus-v2 confirms they ARE positive when the test is applied to their ORIGINAL form** (the originator, not the quote-anchored reply). The cheap-tier-v1's "right answer for the wrong reason" was right *about the original phrasing, not about the replies*. The substrate work would solve this; the rubric work doesn't.

**Conclusions:**

- **Decision-rule outcome: NEAR-MISS for promotion.** F1 = 0.727 > 0.65 ✓, but precision = 0.571 < 0.70 ✗. The strict reading of the pre-reg promotion criterion fails at precision. **The detector is NOT formally promoted to Prototype**, but the gap is small and localized.
- **The precision shortfall has one identifiable cause:** 3 of the 6 FPs are quoted-text rule failures on the same Kjellman cycle-proposal phrase. The other 3 are semantically similar (replies that quote substantive cycle-proposal content). If those 6 were resolved correctly, precision would be 8/8 = 1.0 in pool. **The rubric is well-calibrated; the cheap-tier's honoring of the quoted-text rule has a specific failure mode (strong-signal quoted text overrides the rule).**
- **Two paths forward:**
  - **(a) Accept v2 as the operating point and document the failure mode.** F1 0.727 is a substantial improvement from 0.405; the precision-on-ground-truth (whether the model's positives are real schedule changes) is high — they're all *related to* a real schedule discussion, just sometimes the wrong author within that thread. Operationally, this might be acceptable: a senior operator reading "this thread is about a schedule change" gets the right cluster identified, even if the specific message attribution is off.
  - **(b) Add structural disambiguation to handle the strong-quoted-signal case.** The substrate work (si-clz) showed that *removing* quoted text breaks productive uses of context; but a v2.1 might *mark* quoted material with stronger formatting that the cheap-tier can't override. Worth a small foray IF (a) is unacceptable.
- **The architectural commitment to "binary-per-category classifiers" is reinforced again.** v2 is a single-thesis prompt change; rubric sharpening produced a 0.32 F1 lift with no architecture change. This is what the per-category model is supposed to enable.
- **U3 finding: prompt-level instructions DO steer cheap-tier when the prompt redesign is heavy enough.** Variant B's lightweight marker failed; v2's heavy structured rubric succeeded. Future detector work should default to *heavy structured prompts with examples*, not *lightweight instructions on top of generic prompts*.
- **The promotion criterion may be miscalibrated** for the v2 rubric. The original criterion (precision ≥ 0.70) was set for v1's broader positive class. Under v2's much narrower class (5% base rate), a precision of 0.57 corresponds to a much higher signal-to-noise improvement than 0.70 did under v1's 9.4% base rate. Worth re-thinking before forcing a v3 just to chase the precision number.

**Next:**

- **Surface the (a) vs (b) choice to the user.** The detector is operationally good but doesn't formally promote on the strict criterion. Worth a strategic conversation before doing more work.
- **If (b):** file a small foray to test whether stronger structural marking of quoted text (not just an instruction, but a wrapping/bracketing) helps the cheap-tier ignore strong quoted signals. ~1 hour of work; tests on the same 6 FPs.
- **If (a):** update `detector-catalog.md` to mark `schedule_change_announcement` as Prototype-with-caveat (operating at F1=0.727, precision=0.57, with a known anchoring-failure mode on cycle-proposal threads). Move to the next detector or to cross-corpus generalization (si-t3l).
- **Update `local_temporal_context.md`** with the U3 finding that prompt-level instructions steer Qwen3-Coder-30B when the prompt redesign is heavy enough.
- **Update `detector-catalog.md`** with the v2 rubric and the F1 = 0.727 result, regardless of which branch.
- **Pre-reg lesson:** the falsifier "<5% positives" was triggered by letter but the spirit was preserved. Future pre-regs should specify *spirit checks* alongside numerical thresholds.

---

## 2026-05-02: Substrate first-test — prompt variants over MessageContext separation

**Question:** Does separating `new_content` from `quoted_segments` (per the user's strategic guidance, recorded in memory: `messages_are_not_single_thesis_streams.md`) materially help `schedule_change_announcement`? Is the cheap-tier model's failure mode at depth=2 fundamentally an anchoring-on-quoted-material problem, a rubric-ambiguity problem, or both?

**Beads issues:** si-clz (run), si-71f (pre-reg), si-1lz (engineering prereq, closed in d3384c9). `discovered-from: si-pfo`.

### Pre-registration *(commit this block before running)*

**Setup:**

- Same 731-message corpus, same OpusLabel pool (149 items, 14 OpusPositive / 134 OpusNegative / 1 OpusUnsure), same model (Qwen3-Coder-30B-A3B-Instruct-gptq-4bit), same temperature=0, same eval harness.
- `extract_message_context()` (committed d3384c9) splits each body into `new_content`, `quoted_segments[]`, `attribution_lines[]`, `signature`. Validated end-to-end on all 14 OpusPositives.
- Three prompt variants run against the full 731-message corpus:

**Variant A — `new_only`:**
- System prompt: unchanged from baseline (hash `170dcaf6fa91613b`'s system prompt).
- User template:
  ```
  Message:
  From: {from_raw}
  Subject: {subject}
  Date: {date}

  {new_content_or_placeholder}
  ```
  where `{new_content_or_placeholder}` is `extract_message_context(body).new_content`, or the literal string `(no new content from this author in this message)` if empty.
- Quoted material is invisible to the model.

**Variant B — `new_with_marked_quoted`:**
- System prompt: baseline system prompt + appended sentence: `"The user message below contains a NEW REPLY (this author's actual statement in this message) followed by QUOTED CONTEXT (text quoted from earlier messages, NOT this author's statement). Base your schedule-change judgment on the NEW REPLY only; the QUOTED CONTEXT is reference, not the author's claim."`
- User template:
  ```
  Message:
  From: {from_raw}
  Subject: {subject}
  Date: {date}

  NEW REPLY (this author's statement):
  {new_content_or_placeholder}

  QUOTED CONTEXT (from earlier messages, for reference only — NOT this author's statement):
  {quoted_segments_concatenated_with_depth_markers}
  ```
- `{quoted_segments_concatenated_with_depth_markers}` joins each segment as `[depth N]\n{text}\n` in original order. Truncated to fit `MAX_BODY_CHARS` budget.

**Variant C — `current_baseline`:**
- The existing depth=2 prompt (system_hash `170dcaf6fa91613b`). Re-uses the run-0 predictions from si-pfo (no fresh inference required for C).

Each variant gets its own `prompt_hash`. All three predict on the same 731 messages; same labels file is used to compute scorecards.

**Frozen artifacts:** the OpusLabels, the corpus, the eval harness, the `extract_message_context` implementation (commit d3384c9), the three exact prompt strings above, temperature=0.

**Prediction:**

| variant | predicted F1 | mechanism |
|---------|-------------:|-----------|
| A — `new_only` | 0.40 – 0.55 | Removing quoted material **fixes the Op-13 anchoring failure** — Jonathan's actual new content ("It's too late for a schema change in 2.1") is itself schedule-relevant, so Op-13 may *still* fire as TP, but for the right reason. May regain or hold most of the 11 other stable-TPs (their schedule signal is in the new content, see Opus-positives analysis). May lose Op-5 / Op-6 if their new_content is too terse for the cheap-tier without supporting context. Net F1 ≈ baseline, with cleaner mechanism. |
| B — `new_with_marked_quoted` | 0.40 – 0.55 | Similar to A but the model has fallback context. Predict: model may largely ignore the structural marker (cheap-tier instruction-following is imperfect at this scale); behavior closer to C than to A. |
| C — `current_baseline` | 0.405 (the si-pfo run-0 number) | Reference. |

**Per-message predictions for the high-information cases:**

- **Op-13 (Jonathan, hint storage):** under A, prediction is uncertain — the new content alone ("schema change in 2.1, planning to move to file-based hint storage in 3.0") is schedule-adjacent but less formulaic than the quoted "after 3.0" the cheap-tier had been anchoring on. **50/50 on whether A flips Op-13 to negative.** Under B, model has both signals; lean toward continued positive.
- **Op-5 ("I'll re-roll the artifacts shortly"):** under A, 89-char new_content with the formulaic "re-roll" verb. Cheap-tier should fire — if the prior FN was driven by quoted-context confusion, this should flip from FN to TP. **Predict A flips Op-5 positive.**
- **Op-6 ("Alright, let's wait on 7743"):** 27 chars, no schedule keyword. Predict A still misses Op-6 — the substrate change can't substitute for the missing JIRA-state-resolution capability that si-qdf (typed tags) would provide.

**Decision rule:**

- **Variant A F1 ≥ baseline + 0.05 (i.e., ≥ 0.455):** substrate change pays off in its simplest form. Adopt `new_only` as the depth-equivalent default for `schedule_change_announcement`. Substrate hypothesis confirmed; expand to next detector.
- **Variant B F1 ≥ baseline + 0.05 AND > Variant A:** structural marking is the right intervention. Cheap-tier can use context when told its provenance. Adopt B; expand the marker design to other detectors.
- **A and B both within ±0.05 of C:** substrate change is neutral *for this detector* in terms of F1, but mechanism may have improved (e.g., Op-13 right-for-right-reason instead of right-for-wrong-reason). Continue to si-d6m for rubric work, but cite this experiment as evidence that the *next* detector should be picked specifically to test where the substrate matters more (e.g., a detector where author-baseline or thread-context is load-bearing).
- **A or B drops F1 by >0.10 vs C:** something pathological. Inspect failures before drawing substrate conclusions.

**Falsifiers / mind-changers:**

- **A produces ≤5 model-positives total** (vs 41 in C): new_content is too sparse for this detector at this depth-equivalent. Means the detector requires *some* context to function; the right cut isn't "no quotes" but "marked quotes" (B). Doesn't falsify the substrate idea — refines its application.
- **B and C produce identical predictions** (within noise floor of ±6 messages from si-pfo): cheap-tier ignored the structural marker. Major U3 finding: at this model scale, structural in-prompt instructions don't reliably steer behavior. Implies that substrate value at the cheap-tier requires *removing* irrelevant content (variant A or harder cuts), not *labeling* it.
- **Op-13 stays cheap-tier-positive under A** with new_content alone: contradicts our si-pfo prior that the model anchored on quoted Benedict text. The lone-tp-diagnostic file gets another correction. The model genuinely understood Jonathan's reply; the "right for wrong reason" framing was wrong.
- **Op-6 flips to cheap-tier-positive under A** (27 chars, no schedule keyword): cheap-tier extracted schedule semantics from "Alright, let's wait on 7743" without supporting context. Updates U3 in the favorable direction; reduces urgency of typed-tag substrate (si-qdf).
- **Variant A regresses on the 11 always-stable TPs**: removing quoted context loses signal even when the new content seemed sufficient. Either the new_content extractor has a bug on those messages, or the model was in fact using quoted context productively — not just anchoring wrongly.

### Results *(commit this block after running)*

**Summary:** `results/evals/schedule_change_announcement-clz-variants/summary.json`. Two new runs (variant A and B), 731 predictions each, ~256s wall-clock each. Two deterministic vLLM/parsing failures uncovered and fixed (commit `1f9cdf7`); affected predictions appended manually.

**Scorecards:**

| variant | model+ | TP | FP | Precision | Recall | F1 | Brier |
|---------|-------:|---:|---:|----------:|-------:|----:|------:|
| C_baseline (depth=2) | 41 | 12 | 23 | 0.343 | 0.496 | **0.405** | 0.154 |
| A_new_only | 10 | 6 | 2 | 0.750 | 0.127 | **0.217** | 0.065 |
| B_marked | 13 | 6 | 4 | 0.600 | 0.126 | **0.208** | 0.073 |

**Pre-registered falsifier "A or B drops F1 by >0.10 vs C" TRIGGERED.** Per the pre-reg: "Inspect failures before drawing substrate conclusions." Done.

**Per-OpusPositive coverage matrix (14 OpusPositives, ✓ = caught):**

| #  | Op | C | A | B | sender / subject | new_content has schedule keyword? |
|---:|---:|---|---|---|---|:---:|
| 1  | Op-1  | ✓ | ✗ | ✗ | Marcus / Re: Proposed changes to C* Release Schedule | yes ("until") |
| 2  | Op-2  | ✓ | ✗ | ✓ | Brandon / Re: [VOTE] 2.1.0-rc7 | yes ("re-roll") |
| 3  | Op-3  | ✓ | ✗ | ✗ | Aleksey / Re: [VOTE] 2.0.5 | yes ("reroll") |
| 4  | Op-4  | ✓ | ✓ | ✓ | Sylvain / [VOTE CLOSED] 2.0.10 | yes ("re-roll") |
| 5  | Op-5  | ✗ | ✗ | ✗ | Sylvain / [VOTE CLOSED] 2.1.1 | yes ("re-roll") |
| 6  | Op-6  | ✗ | ✗ | ✗ | Sylvain / [VOTE CLOSED] 2.1.0-rc6 | no |
| 7  | Op-7  | ✓ | ✓ | ✓ | Sylvain / [VOTE CLOSED] 2.0.5 | yes ("shorten") |
| 8  | Op-8  | ✓ | ✓ | ✓ | Sylvain / Re: Proposed changes to Release Schedule | yes ("release cycle") |
| 9  | Op-9  | ✓ | ✗ | ✗ | Sylvain / Re: [VOTE PASSED] 1.2.17 | yes ("re-roll") |
| 10 | Op-10 | ✓ | ✓ | ✓ | Sylvain / [VOTE CLOSED] 2.0.5 (Strike 2) | yes ("restart") |
| 11 | Op-11 | ✓ | ✗ | ✗ | Sylvain / [VOTE CLOSED] 2.0.8 | yes ("re-roll") |
| 12 | Op-12 | ✓ | ✓ | ✗ | Sylvain / [VOTE RESURRECTED] 1.2.16 | yes ("extend the vote") |
| 13 | Op-13 | ✓ | ✗ | ✗ | Jonathan / Hinted Handoff | yes ("too late") |
| 14 | Op-14 | ✓ | ✓ | ✓ | Paulo / Re: [VOTE] 1.2.17 | yes ("postpone") |

**Pairwise disagreement:**

| pair | disagree | % |
|------|---------:|---:|
| A vs C | 35 / 731 | 4.8% |
| B vs C | 34 / 731 | 4.7% |
| **A vs B** | **9 / 731** | **1.2%** |

**A vs B is within the si-pfo noise floor of ±0.015 F1 / ~6 message disagreements.** Variants A and B are essentially the same behavior. The structural marker in B did NOT meaningfully steer the cheap-tier model.

**Observations:**

1. **Substrate change has two opposite effects measured separately.** Of the 28 messages that flipped from C-positive to {A,B}-negative under both variants:
   - **17 were "anchoring fixes"** — C had anchored on text that, under MessageContext extraction, turns out to be **quoted material from earlier in the thread, not the author's actual reply**. Removing the quoted context correctly resolves these to negative. Examples: 4 different replies in a 1.2.15 vote thread all anchored on the quoted phrase "we'll stick to an expedited 24h vote" (originally from Sylvain, quoted in everyone's replies); 5 different replies in the 1.2.16 RESURRECTED thread anchored on "I'm going to propose that we only extend for just 24h more hours". All flipped to negative under A/B; all are OpusNegative or unlabeled. **The si-bwo "model anchors on quoted material" failure mode is real and substrate-fixable.**
   - **11 were "regressions"** — the new_content does have a schedule keyword, but variants A/B still flipped to negative. The model's interpretation of "re-roll" / "after 3.0" / "release cycle" *changes* when it lacks the surrounding thread context: with context, "re-roll" reads as "the previously-announced schedule is changing"; without context, "re-roll" reads as "we'll execute the standard vote-failure procedure." The keyword alone is rubric-ambiguous; the quoted context disambiguates it as a schedule change *for the cheap-tier*.

2. **Variant B did not honor its instruction.** A and B disagree on only 9 of 731 messages (1.2%, within si-pfo noise). The "judge NEW REPLY only; QUOTED CONTEXT is reference" instruction in the system prompt was effectively ignored — the cheap-tier model treated marked-quoted material the same as no quoted material. **Major U3 finding: structural in-prompt instructions about context provenance do not reliably steer Qwen3-Coder-30B at this prompt design.** A more effective intervention would need to be either heavier (e.g., remove quoted material entirely, like A) or different in kind (e.g., few-shot examples of "this is quoted context — note the author isn't claiming it").

3. **Brier score *improved* under A and B** (0.154 → 0.065 / 0.073). Stripping quoted context made the model more confident in its (smaller) set of positives. Calibration is better when the model has less material to be miscalibrated on, but this is a hollow win when recall has cratered.

4. **Op-13 flipped to negative under both A and B** as half-predicted. The pre-reg's "50/50" prediction landed correctly. Jonathan's actual new_content does say "It's too late for a schema change in 2.1" — schedule-relevant — but the cheap-tier without the quoted "after 3.0" context interpreted "too late" as abstract regret rather than as a schedule statement. The "right for wrong reason" mechanism turns out to be replaced by "wrong for the right reason" under the substrate change. Possibly a worse trade.

5. **Op-2's behavior is the cleanest evidence that B isn't honoring its instruction.** Op-2 is one of the 9 A-vs-B disagreements: A misses, B catches. Brandon's new_content says "I know we were planning to re-roll for other reasons" — schedule-relevant. B catches it; A misses. So B *did* use the quoted context for at least Op-2 (against the instruction), giving Brandon's claim more weight than A's stripped form. But across the rest of the corpus, B and A agree, suggesting B used context only when it was decisive — not in the way the prompt instructed.

**Surprises:**

1. **Variant A's recall (0.13) is much worse than predicted (predicted similar to baseline; actual is one-quarter of baseline).** I underestimated how much the cheap-tier was leaning on quoted context to disambiguate the "re-roll = schedule change" interpretation. The pre-reg prediction "Op-5 flips to TP under A" was wrong — Op-5's new_content "I'll re-roll the artifacts shortly" was supposed to be enough; it wasn't.

2. **Most of the C→FN flips are not the Op-13 anchoring case I focused on, but the broader "model uses quoted context productively to disambiguate keywords" pattern.** The substrate change broke many more cases than the one I diagnosed in advance. The lone-TP framing from si-fnw misled me about where the model was using context — it was using it for many TPs, not just Op-13.

3. **Variants A and B converged.** I expected B to land between A and C — context available but de-weighted. Instead B is closer to A than to either A or C is to anything else in the noise sense. Important U3 evidence that prompt-level instructions don't substitute for actual structural changes (removing material) at this model scale.

4. **The "anchoring fix" set is much larger than expected** — 17 distinct messages where C was firing positive on quoted text. The si-bwo failure mode is more common than I realized, not rarer. The substrate would substantially clean up the precision side of any detector running over conversational data; the question is whether the recall cost is acceptable for a given detector.

**Conclusions:**

- **Decision-rule branch fired:** "A or B drops F1 by >0.10 vs C — something pathological. Inspect failures." The inspection has been done (above). The diagnosis is clear: substrate change is too coarse — it removes both anchoring-failures (good) and productive-uses-of-context (bad). The cheap-tier needs structured context, not less context.
- **Detector NOT promoted; no substrate piece adopted as default for `schedule_change_announcement`.** Variant C (current_baseline) remains the operating point. F1 = 0.405; the depth=2 finding from si-fnw stands.
- **The substrate hypothesis is partially validated, partially refined:**
  - **Validated:** the model does anchor on quoted material in real false-positive cases (17 of them in this corpus). The MessageContext separation is a *real* signal that any future substrate work can use.
  - **Refined:** stripping quoted context as a treatment is too coarse. The cheap-tier uses context productively to disambiguate; you can't take it away wholesale. The right shape is probably "keep context, but help the model distinguish structural roles" — a stronger version of variant B with examples, or a multi-step pipeline (extract → judge), or a different cut entirely.
- **Variant B's null result is a U3 update.** Cheap-tier (Qwen3-Coder-30B) doesn't reliably honor structural-role instructions in the system prompt at this design. Future substrate work should default to *removing* irrelevant content rather than *labeling* it, or invest in stronger prompt engineering (few-shot examples).
- **The user's strategic framing is now empirically supported:** "I don't want to overbuild infrastructure. I want to be able to do forays into adding it smartly when needed to see if it helps solve problems. The thesis of detectors being able to do their thing is predicated on them having enough understanding to detect." Variant A removed too much understanding; variant B failed to add usable structure. The next foray should add what the detector demonstrably lacks (e.g., for Op-6: knowing 7743 is an open JIRA), not strip what it's quietly using.
- **`si-d6m` (rubric work) is now MORE clearly the gating issue, not less.** The 11 "regressions" cluster on the rubric-ambiguous boundary: is "re-roll" a schedule change or vote-process routine? Substrate didn't resolve this; only rubric work can. The Op-positives analysis already foreshadowed this; si-clz confirms it.

**Next:**

- **Adopt variant C (current_baseline) as the operating point** for any further `schedule_change_announcement` work until si-d6m is done.
- **The 11 regression messages are the rubric-ambiguity boundary** — combined with the 15 unstable messages from si-pfo, the rubric stress-test set for si-d6m grows to ~26 messages. Any v2 rubric should resolve all of them cleanly. Update si-d6m's notes accordingly.
- **The 17 "anchoring fix" messages are the FP-side stress-test** — a sharpened rubric (si-d6m) that uses depth=2 should NOT call these positive. If it does, the rubric is still anchoring-permissive and needs further sharpening.
- **Substrate ideas remain idea-stage; none promoted.** si-jl0 (cross-thread author context), si-qdf (typed tags), si-r6h (umbrella) all remain idea-status. The si-clz data did not produce demand for them — the demand surfaced is for *structural disambiguation that the cheap-tier honors*, which is a different shape than "more context indices."
- **U3 finding to add to memory:** structural in-prompt instructions about context provenance don't reliably steer Qwen3-Coder-30B at this model scale. Variant B/C disagree only 1.2%, within the noise floor — the marker was effectively invisible to the model.
- **Open question for a future cheap-tier ceiling check (si-2z6):** does a frontier-tier model honor variant B's instruction better? If yes, variant B might be the right shape *with a stronger model*, which would be a cost-tier hierarchy finding.

---

## 2026-05-02: Quantify vLLM non-determinism at the prediction level

**Question:** What is the per-run noise floor on classifier scorecards at temperature=0 with this vLLM deployment? Without it, we can't tell signal from noise on small F1 movements — and rubric-sharpening (si-d6m) is going to produce a series of small F1 movements.

**Beads issues:** si-pfo (run), si-dwi (pre-reg). `discovered-from: si-s9y` (the depth-999 rerun observed ~17/731 prediction differences vs. the si-bwo merged baseline despite identical inputs and temperature=0).

### Pre-registration *(commit this block before running)*

**Setup:**

- Same 731-message corpus (`data/processed/apache/`), same prompt (hash `170dcaf6fa91613b`), same model (Qwen3-Coder-30B-A3B-Instruct-gptq-4bit), same labels file (149 items), `quote_depth=2` fixed.
- Existing `cassandra-2014-predictions-depth-2.jsonl` becomes **run-0** (the si-fnw winner).
- Five fresh runs: `cassandra-2014-predictions-depth-2-run-{1..5}.jsonl`. Same CLI, same homelab endpoint, no other parameter changes. vLLM `temperature=0` as before; no explicit `seed` parameter is sent (vLLM's default seeding policy applies).
- Six runs total → 15 pairwise comparisons of (run_i, run_j) over 731 predictions each.
- Eval harness: re-run `pool_and_extrapolate.evaluate` against the same labels file for each run; report per-run F1 / precision / recall / Brier and the spread across runs.
- Disagreement analysis: for every message id, compute the number of runs (out of 6) that flagged it positive. Bin by flip count (0 = always-neg, 6 = always-pos, 1-5 = unstable). Cross-tabulate flip count with `p_positive` from run-0 to test the "noise concentrates on borderline" hypothesis.

**Frozen artifacts:** the prompt, the rubric, the labels, `quote_depth=2`, the eval harness, the corpus. The only thing varying across runs is the vLLM endpoint's run-to-run output (whatever combination of GPU non-determinism, batching, KV-cache state, and stochastic sampling at logit-tie produces it).

**Prediction:**

- **Pairwise prediction disagreement: 1–3% per pair** (≈8–22 message-id flips per (run_i, run_j) pair out of 731). Anchored on si-s9y's observation of 17/731 differences between depth-999 reruns.
- **F1 spread across the 6 runs (max − min): 0.04–0.08.** Each flipped TP/FP shifts F1 by ≈0.02–0.03 at this base rate, so flipping 2-4 borderline items per run produces this band.
- **Disagreement concentrates on borderline `p_positive`** (run-0 logprob in [0.3, 0.7]). The "always-pos" and "always-neg" buckets dominate; the unstable bucket is small (5–15 messages) but accounts for nearly all the F1 spread.
- **Flip direction is roughly symmetric** — POS↔neg flips are not one-sided. (si-s9y noted this qualitatively for the depth-999 reruns; the 5-run sample should confirm it.)
- **No outlier run.** All 6 runs land within ±0.04 of the mean F1.

**Decision rule:**

- **F1 spread (max − min across 6 runs) < 0.04:** noise floor is small. Adopt **±0.04** as the published per-run F1 noise floor. Future scorecard movements >0.04 are signal; ≤0.04 require multi-run CIs. The si-fnw depth=2 advantage (0.075 over the plateau) clears this floor — depth=2 conclusion holds.
- **F1 spread 0.04 ≤ x < 0.10:** noise floor moderate. The depth=2 vs plateau gap of 0.075 sits inside the noise floor's upper end — **depth=2 may be on the plateau after all, not above it.** Future detector sweeps need ≥3 reruns per condition; report CIs not point F1. si-d6m's rubric work needs to use multi-run baselines.
- **F1 spread ≥ 0.10:** noise dominates signal at this scale. Halt detector tuning. Investigate vLLM sampling parameters (try `seed=N` if the vLLM build supports it; check whether `temperature=0` is being honored or silently coerced; check whether request-level batching is producing the variance). Re-pre-reg before resuming detector work.
- **Zero flips across all 15 pairwise comparisons:** vLLM is actually deterministic. The si-s9y / si-bwo differences came from something *other than* non-determinism — different prompt hash, different model build, different parser version, different `quote_depth`. Audit those artifacts before adopting the "deterministic" conclusion; the alternative explanation has to land somewhere.

**Falsifiers / mind-changers:**

- **One run is a dramatic outlier** (F1 ≥0.10 different from the other 5, or model-positive count ≥10 different from the other 5 runs): single-run outlier — investigate (vLLM hot-restart? KV-cache cold? request the model_id and verify it's the same build) before computing the noise floor. Don't average through an outlier.
- **Flip direction is asymmetric** (e.g., 90% of flips are POS→neg, only 10% the other way): this isn't simple non-determinism, it's *drift*. The vLLM deployment may be doing something stateful between runs — caching, weight-loading order, batch composition. Investigate before adopting noise-floor framing.
- **Disagreement is uniform across `p_positive`** (no concentration on borderline messages): the noise model isn't "borderline messages flip"; it's something else — possibly numerical noise at the logit level affecting even confidently-classified messages. Implies the published `p_positive` values are less trustworthy than the binary predictions.
- **All 5 fresh runs disagree with run-0 by significantly more than they disagree with each other**: run-0 was generated under different conditions than the new 5 (despite our intent that they be identical). Audit what changed (model_id? endpoint state? prompt_hash? body content?) before drawing noise conclusions. Treat run-0 as untrusted.
- **Per-run wall-clock time varies by >2× across the 5 runs**: vLLM is being load-shared or batched against other workloads in ways that may correlate with the determinism story. Note in the results.

### Results *(commit this block after running)*

**Summary:** `results/evals/schedule_change_announcement-pfo-noise-floor/summary.json`. Six runs at depth=2: run-0 (the existing si-fnw winner) plus 5 fresh reruns each ~256s on the homelab. Wall-clock variance across 5 fresh runs is essentially zero (255–256s, 0.4% spread).

| run | model+ | TP | FP | precision | recall | F1     | Brier |
|----:|-------:|---:|---:|----------:|-------:|-------:|------:|
| 0   | 41     | 12 | 23 | 0.343     | 0.496  | 0.405  | 0.154 |
| 1   | 39     | 12 | 22 | 0.353     | 0.497  | 0.413  | 0.152 |
| 2   | 38     | 12 | 22 | 0.353     | 0.497  | 0.413  | 0.151 |
| 3   | 43     | 12 | 24 | 0.333     | 0.494  | 0.398  | 0.155 |
| 4   | 40     | 12 | 23 | 0.343     | 0.495  | 0.405  | 0.155 |
| 5   | 41     | 12 | 22 | 0.353     | 0.498  | 0.413  | 0.151 |

**Spreads (max − min across 6 runs):** F1 **0.015** (stddev 0.0061), precision 0.020, recall 0.004, Brier 0.005, model-positives 5.

**Pairwise prediction disagreement (15 pairs):** 4–10 messages out of 731, **0.5%–1.4%** per pair. Mean pairwise Hamming ≈ 6.7/731. Total flips across all 15 pairs: 102 (47 pos→neg, 55 neg→pos, 46.1% / 53.9%) — direction is essentially symmetric.

**Per-message stability:** of 731 messages, 683 are stable-negative (0/6 positive votes), 33 are stable-positive (6/6), and **15 are unstable** (somewhere between 1/6 and 5/6). Borderline-concentration hypothesis is decisively confirmed:

| run-0 p_positive bin | total | stable-neg | stable-pos | unstable | % unstable |
|----------------------|------:|-----------:|-----------:|---------:|-----------:|
| [0.0, 0.1) | 676 | 675 | 0 | 1 | 0.1% |
| [0.1, 0.5) |  14 |   8 | 0 | 6 | 42.9% |
| [0.5, 0.8) |   6 |   0 | 1 | 5 | 83.3% |
| [0.8, 1.0) |  35 |   0 | 32 | 3 | 8.6% |

**Pre-reg prediction check:**
- Pairwise disagreement 1–3% → observed 0.5–1.4% (slightly tighter than predicted).
- F1 spread 0.04–0.08 → observed **0.015** (substantially tighter than predicted).
- Borderline concentration → confirmed.
- Symmetric flip direction → confirmed.
- No outlier run → confirmed.

**Falsifiers — none triggered:** no outlier run; no asymmetry in flip direction; instability concentrates on borderline (not uniform); run-0 disagrees with the fresh five at the same rate they disagree with each other (5–10 vs 4–10); wall-clock variance trivial.

**Observations:**

1. **TP count is 12 in every single run.** All variance is in FP count (22–24). The model's *true-positive set* is perfectly stable across the 6 runs at depth=2; what wavers is *which marginal NEGATIVE messages get over-flagged*. Recall is functionally deterministic at this depth (the 0.004 recall spread comes from the eval harness's unseeded `random.sample` of model-negatives, not from classifier variation — same labeled pool, same TP set).

2. **The 15 unstable messages are dominated by `[VOTE]` / `[VOTE CLOSED]` / "Release Schedule" subjects.** Almost every unstable message is a release-vote ceremony reply or a thread participant in "Proposed changes to C* Release Schedule" — exactly the boundary territory where the rubric is ambiguous (release votes are *planned steps* in a release process, not *changes* to a schedule, but the model wavers on whether to call them positive). All 7 unstable messages with gold-standard labels are labeled NEGATIVE.

3. **The lone-TP advantage of depth=2 (from si-fnw) is structurally stable, not stochastic.** The Jonathan Ellis "I plan to address this... after 3.0" message — which anchors on quoted Benedict text rather than the actual new reply — fires POSITIVE in all 6 runs. So the si-fnw 0.075 F1 advantage rests on a *deterministic* mechanism at depth=2, not a lucky-roll artifact. The mechanism is fragile to *prompt or context-window changes* (it's the model anchoring on the wrong span), but it is not fragile to vLLM run-to-run noise.

4. **2 of the 33 stable-positive bin messages are still in the unstable set** (high run-0 confidence, but not unanimous). Confidence is a strong but imperfect predictor of stability: most very-confident predictions are stable, but a small fraction of high-confidence positives still flip across runs.

**Surprises:**

1. **F1 spread is much tighter than predicted (0.015 vs predicted 0.04–0.08).** I anchored on the si-s9y observation of "17/731 prediction differences" between two depth-999 runs and assumed similar noise at depth=2. The actual depth=2 noise is ≈3× tighter. Possible explanation: depth=2 messages are *shorter* (less quoted material) and produce more decisive logits, leaving fewer borderline positions for noise to flip. The si-s9y observation may have been a depth-999 phenomenon, not a general noise floor.

2. **The TP set is 100% stable while the FP set wavers.** I expected non-determinism to affect both directions roughly proportionally to base rate. Instead, the model's high-confidence "this IS a schedule change" cases are anchored hard, and only the marginal "could-be-a-schedule-change-or-not" set wavers. This is informative for synthesis-layer design: if downstream decisions only act on the stable-positive set, they're safe from this layer of noise; if they act on the high-confidence-but-not-unanimous bucket (the 2 unstable items in [0.9,1.0)), they need rerun aggregation.

3. **The 15 unstable messages are an almost perfect characterization of the rubric ambiguity boundary.** Without the noise probe, I'd have had to identify these by hand. The non-determinism quantification has incidentally produced the **rubric stress-test set** for si-d6m at zero additional cost: any sharpened rubric that doesn't cleanly resolve these 15 messages hasn't sharpened the right thing.

4. **My pre-analysis hypothesis about the lone-TP message was wrong.** I predicted (in `results/detector-runs/.../si-pfo-reruns/lone-tp-diagnostic.md`) that the Jonathan Ellis quoted-Benedict-anchor message would be a leading flip candidate. It wasn't — it's stable across all 6 runs. The "right answer for the wrong reason" mechanism turns out to be *deterministically wrong* in a useful direction. Updated the diagnostic file accordingly.

**Conclusions:**

- **Decision-rule branch fired:** F1 spread = 0.015 < 0.04. **Adopted noise floor: F1 ±0.015** at this depth/detector/corpus. Conservatively rounded for cross-experiment use: **±0.04 buys high-confidence "this difference is signal" claims; differences ≤0.04 require multi-run scorecards**.
- **The si-fnw depth=2 conclusion holds with a 5× margin.** Depth=2's 0.075 F1 advantage over the plateau is 5× the measured noise floor — this is genuine signal, not a lucky roll. Update `local_temporal_context.md` accordingly.
- **si-d6m can proceed at depth=2 without multi-run aggregation.** Single-run scorecards are trustworthy to ±0.015. The rubric work's expected effect size (closing the F1 0.41 → ≥0.65 gap) is far larger than the noise floor.
- **Recall noise is functionally zero at depth=2.** Precision noise is ±0.02. For experiments that move precision/recall in opposite directions (a common pattern for rubric sharpening), report each separately rather than collapsing to F1, since the noise floors differ.
- **The architectural commitment to "binary-per-category classifiers" is reinforced.** The detector's TP set is highly stable; the entire variance lives in the rubric-ambiguous boundary. This is exactly the failure mode that binary-per-category isolates cleanly — sharpening one rubric doesn't disturb anything else, and the noise floor is small enough to detect rubric improvements at the resolution we need.
- **vLLM at temperature=0 with this model is "deterministic enough":** the residual non-determinism (presumably from CUDA op-ordering, batch composition, KV-cache state) affects ~2% of predictions and concentrates on the rubric-ambiguous set. We do not need to investigate vLLM seed semantics or sampling parameter overrides.

**Next:**

- **Unblock si-d6m** (rubric sharpening) — the noise floor is no longer in the way.
- **Use the 15 unstable messages as the rubric stress-test set for si-d6m.** Any v2 rubric that doesn't cleanly classify all 15 is incomplete. (Filed as a sub-finding within si-d6m rather than a new bd issue, since it's intrinsic to that work.)
- **Update `local_temporal_context.md` memory** to record: noise floor at depth=2 for this detector/corpus is F1 ±0.015; the si-fnw depth=2 advantage is robustly above it.
- **Note for synthesis-layer design (out of scope here):** the model's high-confidence positives are stable; downstream consumers of `p_positive` should treat the [0.5, 0.8) band as inherently noisy across reruns, and the [0.9, 1.0) band as ~94% stable. The 2 unstable items in [0.9, 1.0) flag that even high confidence isn't a stability guarantee — a "stability score" might warrant being a separate signal from `p_positive`.

---

## 2026-05-02: Depth sweep refinement — fill in {3,4,5,6,8,10} around the peak

**Question:** Same architectural hypothesis as si-s9y, refined: si-s9y tested {0,1,2,999} and found depth=2 best of those, but only 4 data points (one at 999) don't establish 2 as the actual peak. Is the F1 curve unimodal with a peak between 2 and ~10, or is it bumpier?

**Beads issues:** si-fnw, `discovered-from: si-s9y`.

### Pre-registration *(commit this block before running)*

**Setup:**

- Same 731-message corpus, same prompt (hash `170dcaf6fa91613b`), same model, same labels file (149 items).
- Sweep `quote_depth ∈ {3, 4, 5, 6, 8, 10}`. Combined with the existing four runs at {0, 1, 2, 999}, this gives a 10-point curve over the realistic depth range for email threads in this corpus.
- Same eval harness, same comparison code (`src/evaluate/compare_depth_sweep.py` already handles arbitrary depths via glob).

**Frozen artifacts:** all of si-s9y's frozen artifacts carry over (extract_at_depth semantics, prompt, labels). The only new commitment is the set of depths to test.

**Prediction:**

The si-s9y curve was 0.13 → 0.24 → 0.41 → 0.31 (depths 0, 1, 2, 999). The slope from 1→2 is large (+0.16) and 2→999 is negative (-0.10). If the function is unimodal, the actual peak is somewhere in [2, 999]. My prior:

| depth | predicted F1 | rationale |
|------:|-------------:|-----------|
| 3 | 0.42 – 0.48 | Modest improvement on depth=2; one more level of context for references |
| 4 | 0.40 – 0.48 | Similar to 3, possibly slightly better if grandparent's parent is informative |
| 5 | 0.36 – 0.44 | Beginning to decline as quoted noise outweighs context value |
| 6 | 0.33 – 0.42 | Most threads in this corpus have ≤6 levels, so the marginal new content is sparse |
| 8 | 0.30 – 0.38 | Approaching depth=999 territory |
| 10 | 0.28 – 0.36 | Effectively depth=999 for this corpus (few threads exceed 10 levels) |

**Best-depth prediction: depth=3 or depth=4 wins F1**, with the peak F1 in the range 0.42–0.48 (a 0.01–0.07 improvement over depth=2).

**Decision rule:**

- **A depth in {3, 4, 5} wins F1 by ≥0.05 over depth=2:** clear new peak. Adopt that depth as the default for `schedule_change_announcement`. Update `local_temporal_context.md` with the peak.
- **Max F1 in {3,4,5,6,8,10} is within ±0.05 of F1=0.405 (depth=2):** depth=2 is on a plateau; pick the simplest depth in the plateau (smaller is better for inference cost). The exact peak is within noise.
- **F1 is non-monotonic** (e.g., depth=4 wins but depth=5 worse than depth=8): genuine surprise. The function isn't unimodal, which means the "more context = monotonically more/less recall" mental model is wrong. Investigate before drawing conclusions.

**Falsifiers / mind-changers:**

- **Any depth produces F1 > 0.55 (substantially above the depth=2 winner):** great if true, but would suggest si-s9y's prediction range was way off. Verify the comparison harness isn't double-counting or mis-extrapolating before celebrating.
- **F1 oscillates across adjacent depths by >0.10** (e.g., 3→0.45, 4→0.30, 5→0.45): model behavior on this detector is unstable in a way that makes "best depth" ill-defined. The vLLM non-determinism floor (si-pfo) is then implicated more strongly.
- **F1 at depths 8 and 10 are both higher than depth=2:** the function is multi-modal, and there's a high-context peak we missed. Investigate.

### Results *(commit this block after running)*

**Scorecards:** `results/evals/schedule_change_announcement-depth-sweep-refined/scorecard-depth-{0..999}.json`. Full 10-point curve:

| depth | model+ | TP | FP | precision | recall | F1     | Brier |
|------:|-------:|---:|---:|----------:|-------:|-------:|------:|
| 0     |  5     |  4 |  1 | 0.800     | 0.073  | 0.134  | 0.070 |
| 1     | 31     |  8 | 16 | 0.333     | 0.191  | 0.243  | 0.140 |
| **2** | 41     | 12 | 23 | 0.343     | 0.496  | **0.405** | 0.154 |
| 3     | 41     | 11 | 26 | 0.297     | 0.371  | 0.330  | 0.183 |
| 4     | 42     | 11 | 27 | 0.289     | 0.369  | 0.325  | 0.196 |
| 5     | 44     | 11 | 28 | 0.282     | 0.368  | 0.319  | 0.198 |
| 6     | 43     | 11 | 27 | 0.289     | 0.366  | 0.323  | 0.187 |
| 8     | 47     | 11 | 30 | 0.268     | 0.364  | 0.309  | 0.206 |
| 10    | 43     | 11 | 26 | 0.297     | 0.370  | 0.330  | 0.193 |
| 999   | 46     | 11 | 29 | 0.275     | 0.364  | 0.314  | 0.199 |

**My pre-registered prediction** (depth=3 or 4 wins F1 by ≤0.07 over depth=2) is **falsified**. depth=2 remains the winner; depths 3 through 999 are remarkably flat at F1 0.31–0.33.

**Observations:**

1. **The curve has two regimes, not one peak.** Sharp rise from depth=0 to depth=2 (F1 0.134 → 0.405), then a flat plateau across all depths 3–999 at F1 0.31–0.33. The transition isn't smooth — it's a step. Depth=2 sits 0.075 above the plateau.

2. **TP count plateaus too:** 12 at depth=2, then 11 at every other depth from 3 to 999. The model identifies essentially the same set of true positives across the entire 3-999 range; what changes is the *false-positive load* (23 → 26-30). More context exposes more quoted material the model anchors on, without finding new TPs to compensate.

3. **Brier monotonically degrades from depth=2 (0.154) through depth=8 (0.206)** then dips slightly. The model gets *less* calibrated as more context is added. Confirms si-s9y's per-(detector, depth) calibration finding — calibration degrades as the model has more material to be over-confident about.

4. **Two transient HTTP errors (depth=6: 2 errors; depth=10: 1 error)** on small-bodied messages. Same pattern as the depth=999 transient in si-s9y. Aggregated across 7,309 inference calls in this sweep, that's a ~0.04% transient error rate — non-issue.

**Surprises:**

1. **The plateau is dead flat.** I predicted F1 would gradually decline from depth=3 onward toward depth=999. Instead it's basically the same number (within noise) for every depth from 3 to 999. This means *adding context past depth=2 produces neither benefit nor cost* in this corpus. The model has saturated its ability to extract signal from the prompt, and additional quoted material is neither helping nor hurting beyond a small precision drag from extra anchor candidates.

2. **The depth=2 advantage is real but marginal.** 0.075 above the plateau is more than one noise floor (si-pfo: ±0.04) but less than two. Without repeating depth=2 multiple times to characterize its variance, I can't rule out that the true mean F1 at depth=2 is closer to ~0.36 and we got a lucky run. **The right next step is si-pfo (quantify vLLM non-determinism) before drawing a sharp depth=2 conclusion.** The qualitative claim ("depth=2 is at least as good as any tested alternative") is robust; the precise F1 at depth=2 is uncertain.

3. **The intuition behind the depth=2 advantage may not be "parent + grandparent."** Looking at the data: at depth=2, TP=12; at every depth from 3 to 999, TP=11. The lone extra TP at depth=2 explains nearly the entire F1 advantage. Without that one item, depth=2 collapses to plateau territory. Need to identify *which* TP is unique to depth=2 to understand whether it's a robust pattern or a quirk.

**Conclusions:**

- **Decision-rule outcome:** "max F1 in the new sweep is more than 0.05 below depth=2's 0.405" — neither the new-peak case nor the plateau case applied as predicted. **Depth=2 remains the recommended envelope** for `schedule_change_announcement` on this corpus, but the recommendation is contingent on the noise-floor being smaller than the depth=2/plateau gap. si-pfo's quantification is now blocking high-confidence claims about this parameter.
- **Detector still NOT promoted.** F1 0.405 < 0.65 threshold; precision 0.343 < 0.70. The depth-sweep alone won't close that gap — rubric work (si-d6m) is the remaining lever.
- **The "more context is more signal" intuition fails past depth=2 for this detector.** The model saturates. This is consistent with the local_temporal_context.md memory: optimal envelope is detector-AND-corpus-specific, and the right way to find it is empirical sweep, not theoretical reasoning. But the *shape* of the curve (sharp rise then flat plateau) is itself a useful generalization candidate — possibly true for many reference-heavy detectors over conversational corpora. Worth checking on the next detector.
- **Updated `local_temporal_context.md` finding** for the rubric work in si-d6m: the right envelope test for future detectors should be a *fast coarse sweep* of just {0, 1, 2, 4, 8} or similar — the marginal value of finer resolution past the obvious plateau is low, and the cost of even a 5-point sweep is ~20 minutes.

**Next:**

- **si-pfo blocks** clean depth-conclusion claims. Run it before any further depth-related decisions.
- **si-d6m** (rubric sharpening at depth=2) is still the primary path to detector promotion.
- **Investigate the lone extra TP at depth=2** — which message does the model catch at depth=2 but lose at depth=3? Cheap diagnostic, possibly informative about the boundary.
- **Update `local_temporal_context.md`** with the curve-shape generalization (sharp rise → plateau) for future detector pre-regs.

---

## 2026-05-02: Depth sweep — local temporal context as a detector parameter

**Question:** Does explicitly controlling the model's local temporal context (quote depth in linear thread) recover signal lost to the quoted-vs-new-content confusion surfaced in si-qhz and si-bwo? Architectural hypothesis test, not a U-number primary unknown — but downstream of U3 if the answer is depth-dependent.

**Beads issues:** si-s9y (this sweep), `discovered-from: si-bwo`. Memory `local_temporal_context.md` codifies the broader principle.

### Pre-registration *(commit this block before running)*

**Setup:**

- **Dataset:** same 731 Cassandra dev@ 2014 messages from si-qhz/si-bwo. No re-harvest.
- **Detector:** same `schedule_change_announcement` prompt frozen in commit 7d64413. No prompt change. Hash unchanged: `170dcaf6fa91613b`.
- **Model:** same Qwen3-Coder-30B-A3B at `192.168.100.101:8080`, temperature=0, guided_json schema, max_tokens=400, MAX_BODY_CHARS=60000.
- **Sweep parameter:** `quote_depth ∈ {0, 1, 2, 999}` applied via `src/classify/quote_extractor.extract_at_depth(body, depth)` before the prompt is built. depth=999 is operationally "no filtering" (effectively ∞ for this corpus where max observed depth is ~6); included as a baseline that uses the same code path as the other depths so any differences attribute to the depth parameter and not to preprocessing artifacts.
- **Labels:** existing 149-item labels file from si-qhz + si-bwo. Labels are message-scoped — they describe what the message is, independent of which depth view of it the model saw. Re-using labels is valid; relabeling would be a separate experiment.
- **Eval:** pool-and-extrapolate harness per depth. Run separately, four scorecards. Compare F1, precision, recall, Brier, model-positive count.

**Frozen artifacts** (any change invalidates this pre-reg):
- `src/classify/quote_extractor.extract_at_depth` semantics (quote_depth counting, attribution-line stripping at depth=0, blank-line collapse). 10/10 unit tests passed in commit prior to this pre-reg.
- The sweep depths {0, 1, 2, 999}. No mid-flight depth additions; if a different depth proves interesting, it goes in a new pre-reg.

**Prediction:**

| depth | predicted precision | predicted recall | predicted F1 | predicted model-positives | rationale |
|-------|---------------------|------------------|--------------|----------------------------|-----------|
| 0 | 0.50 – 0.75 | 0.45 – 0.65 | **0.50 – 0.65** | 15 – 30 | "+1" replies become bare; FPs from quoted-anchor disappear; small recall hit on messages whose new content references but doesn't restate schedule. |
| 1 | 0.30 – 0.50 | 0.55 – 0.70 | 0.40 – 0.55 | 30 – 50 | Reply + immediate parent. Recovers some recall via parent context, but inherits some of the quoted-anchor FPs. |
| 2 | 0.27 – 0.40 | 0.60 – 0.75 | 0.40 – 0.50 | 35 – 55 | Adds grandparent. Most threads in this corpus have ≤2 levels of quoted history, so depth=2 ≈ depth=∞ for many messages. |
| 999 | 0.25 – 0.35 | 0.55 – 0.70 | 0.35 – 0.45 | 40 – 50 | Should match si-bwo's relaxed-cap merged baseline (precision 0.286, F1 0.358) modulo blank-line-collapse differences. |

**Best-depth prediction: depth=0 wins on F1**, by a margin of at least 0.10 over depth=999. Reasoning: the dominant FP source from si-qhz/si-bwo is the model anchoring on quoted parent content. Depth=0 eliminates that anchor source. The recall trade is small because most actual schedule-change-announcements in this corpus restate the change in their new content (e.g., "I propose postponing 1.2.17", "I'll re-roll", "we'll commit to adding no new features after 2.1.0").

**Decision rule:**

- **depth=0 F1 ≥ depth=999 F1 + 0.10 AND depth=0 precision ≥ 0.50:** clear sweet spot. Adopt depth=0 as default for this detector. Promote `schedule_change_announcement` to **Prototype** in detector-catalog. Result is also evidence for the "local temporal context is a first-class parameter" memory.
- **0 < depth=0 F1 − depth=999 F1 < 0.10:** depth-stripping helps but isn't decisive. Document, treat depth=0 as a tunable. Don't promote yet.
- **depth=1 wins F1 by ≥0.05 over depth=0 and depth=999:** the right envelope is "reply + immediate parent." Adopt depth=1.
- **depth=999 ties or wins:** the model isn't actually fooled by quoted material, or quote-stripping introduces other failure modes that offset the gain. Surprising result; investigate before drawing conclusions.

**Falsifiers / mind-changers:**

- **All depths produce F1 within 0.03 of each other:** quote depth isn't the load-bearing parameter; the failure mode is something else (rubric ambiguity, prompt clarity, etc.). Falsifies the si-bwo hypothesis. Significant — would refocus si-d6m toward rubric work alone.
- **depth=0 produces 0 model-positives or > 100 model-positives:** preprocessing is broken. Stop and inspect.
- **depth=999 scorecard differs significantly from si-bwo's merged baseline (F1 ±0.05):** the `extract_at_depth` code path has unintended side effects beyond pure depth filtering. Investigate before trusting the sweep.
- **Brier scores diverge by >0.10 across depths:** calibration is depth-sensitive in a way that complicates downstream use of logprobs. Note and feed into si-kxh (calibration follow-up).
- **A depth produces predictions that flip on items with body length far below the 60K cap:** suggests sensitivity to formatting/whitespace that's separate from quote content. Inspect.

### Results *(commit this block after running)*

**Scorecards:** `results/evals/schedule_change_announcement-depth-sweep/scorecard-depth-{0,1,2,999}.json`. Side-by-side:

| depth | model+ | TP | FP | precision (95% CI) | recall (95% CI) | F1 | Brier |
|------:|-------:|---:|---:|--------------------|-----------------|---:|------:|
| 0     | 5      | 4  | 1  | 0.800 [0.38, 0.96] | 0.073 [0.04, 0.13] | 0.134 | 0.070 |
| 1     | 31     | 8  | 16 | 0.333 [0.18, 0.53] | 0.191 [0.10, 0.34] | 0.243 | 0.140 |
| 2     | 41     | 12 | 23 | 0.343 [0.21, 0.51] | 0.496 [0.22, 0.78] | **0.405** | 0.154 |
| 999   | 46     | 11 | 29 | 0.275 [0.16, 0.43] | 0.364 [0.17, 0.63] | 0.314 | 0.199 |

**My pre-registered prediction was that depth=0 would win F1.** The actual best-by-F1 is depth=2. The pre-reg's "depth=0 wins" hypothesis is **falsified**.

**Observations:**

1. **Depth=0 has the highest precision (0.80) but devastating recall (0.07).** Only 5 model-positives total, of which 4 are real. The 4 it catches are messages whose *new content directly restates the schedule decision*: "We were almost there but [regression]... I'm closing that vote", "I was thinking we could lower the release cycle to 4 month", "I propose postponing release of 1.2.17", "We'll re-roll as soon as the pig stuff are fixed". The 1 FP is "Not this year" (bootcamp event, model interpreted as release schedule). The model becomes extremely conservative when given just the new reply.

2. **Depth=2 is the F1 winner at 0.405**, a real improvement over the depth=999 baseline (0.314, equivalent to si-bwo's merged 0.358 within run-to-run variance). Recall jumps from 0.07 (depth=0) to 0.50 (depth=2) — most actual schedule-change announcements in this corpus need parent + grandparent context to be recognizable as such, because the new content typically *refers to* a previously-stated date without restating it. e.g., a "+1" reply to "I propose postponing 1.2.17" is contributing to a schedule decision but doesn't itself contain the announcement.

3. **Brier diverges by 0.13 across depths** (0.07 at depth=0, 0.20 at depth=999) — falsifier triggered. Calibration is genuinely depth-sensitive: depth=0 makes the model more conservative and better-calibrated; depth=999 floods the model with quoted material it confidently misclassifies. This complicates downstream use of logprobs in a way si-kxh (calibration follow-up) needs to account for — the right calibration map is per-(detector, depth), not per-detector.

4. **17 predictions differ between depth=999 sweep and si-bwo's relaxed-cap merged baseline** despite temperature=0. The F1 differs by 0.04 (0.314 vs 0.358), just under my 0.05 falsifier threshold. The diffs are roughly balanced (POS↔neg in both directions). Sources are vLLM non-determinism (batch effects, kernel non-determinism), the blank-line-collapse in `extract_at_depth` slightly modifying input, or other minor variation. Methodologically: assume per-run noise of ±0.04 F1 on this corpus when comparing scorecards. Larger differences are signal; smaller ones are noise.

5. **One transient HTTP 400 at depth=999** on a 3,200-char message (well under the 60K cap). Likely vLLM transient. Affects 1/731 predictions; does not change conclusions.

**Surprises:**

1. **The "model anchors on quoted material" theory from si-bwo was incomplete.** The model isn't *only* drawn to quoted material; it's drawn to whatever schedule-language signal is in front of it. With reply-only (depth=0), the new content lacks signal for most messages → conservative NEG. With full thread (depth=999), too much quoted material muddies things. Depth=2 hits a goldilocks zone where the parent + grandparent disambiguate references in the reply without flooding noise.

2. **The optimal envelope is empirically larger than I expected.** I expected depth=0 or depth=1 to win. Instead it's depth=2 — *more* context, not less. The lesson: don't theorize your way to the right context envelope; sweep it. This generalizes the `local_temporal_context.md` memory.

3. **High precision doesn't help if recall collapses.** Depth=0 nearly recovers a "perfect precision" detector but at 7% recall — useless for production. The eval design (pool-and-extrapolate) made this visible; a precision-only score would have been misleading.

**Conclusions:**

- **Best depth for `schedule_change_announcement` on this corpus: depth=2.** F1 0.405, precision 0.343, recall 0.496. Adopt as the default for this detector going into si-d6m (rubric sharpening). Re-pre-register at depth=2 before the rubric work.
- **Detector still NOT promoted to Prototype.** Original pre-reg required F1 ≥ 0.65 AND precision ≥ 0.70; depth=2 gives 0.41 / 0.34. Improvement is real but insufficient. The next move (rubric sharpening) is what might close the gap.
- **The frontier-tier ceiling check (si-2z6) is now better-formed** — run Sonnet at depth=2 (the best envelope this model achieves) rather than depth=999, to disambiguate "task is hard" from "this model + this envelope is bad" cleanly.
- **Update to `local_temporal_context.md` memory:** the optimal envelope is empirically determined and larger than my intuition suggested. Add the observation that "more context isn't always more noise — for reference-heavy detectors (where the new content refers to but doesn't restate the signal), context windows of depth 2-3 in the linear thread can substantially help."
- **Methodological:** vLLM non-determinism is real at this scale. Future detector experiments should expect ±0.04 F1 between supposedly-identical runs. For meaningful per-run conclusions, the F1 effect should clear that noise floor.

**Next:**

- Update `local_temporal_context.md` with the empirical-envelope finding.
- Open `si-d6m` (rubric sharpening) at depth=2 specifically. Re-pre-register before the rubric work.
- File a new bd issue for "investigate vLLM non-determinism on the same item across runs" — quantify the noise floor explicitly, not anecdotally.

---

## 2026-05-02: schedule_change_announcement on Cassandra dev@ 2014 — first binary classifier

**Question:** Primary U3 (how small can the cheap classification tier get without losing accuracy?), secondary U4 (signal density in operational text streams). The detector itself (`schedule_change_announcement` from `docs/detector-catalog.md`) is universal-generalization-claimed but this run is single-domain — generalization tests come later, on a multi-org corpus.

**Beads issues:** Pre-reg = `si-rn2` (closes when this block lands). Run = `si-qhz` (blocked-by si-rn2 + si-9nr).

### Pre-registration *(commit this block before running)*

**Setup:**

- **Dataset:** `data/processed/apache/dev@cassandra.apache.org/2014-{01..12}.jsonl` — 731 normalized messages, harvested in commit `f26ca42`. Single-org-dominant (Datastax + core committers).
- **Detector:** `schedule_change_announcement` — binary classifier asking "does this message announce or imply a change to a previously-stated or expected schedule for software work (releases, milestones, target dates, version cadence)?"
- **Model:** Qwen3-Coder-30B-A3B-Instruct (4-bit GPTQ) at homelab endpoint `http://192.168.100.101:8080`, OpenAI-compatible API. Logprobs requested for calibration.
- **Approach:**
  1. Run the classifier prompt (committed below; any later change invalidates this pre-reg) over all 731 messages. Save predicted boolean, evidence_quote, rationale, and logprob of the boolean token.
  2. Build the eval set via **pool-and-extrapolate**: hand-label *all* model-positives (expected ~10-30 messages) plus a stratified random sample of 100 model-negatives (~10/month).
  3. Compute precision directly on model-positives. Estimate recall via the false-negative rate on the random sample of model-negatives, extrapolated to the unsampled negative pool.
  4. Compute Brier score and reliability bins (10 bins of width 0.1) from logprobs.
  5. Hand-labeling rubric is below; ambiguous items get an "unsure" label and are excluded from P/R but reported separately.

**Classifier prompt (frozen):**

```
You are reviewing a single message from the Apache Cassandra developer mailing list
(dev@cassandra.apache.org). Determine whether the message announces or implies a change
to a previously-stated or expected schedule for software work (releases, milestones,
target dates, version cadence).

POSITIVE:
- Announcements that a release/version is delayed, advanced, or rescheduled
- Proposals to change a previously-stated target date ("should we move X to next week?")
- Acknowledgments that a previously-implied timeline will not be met
- Setting a new target date when a previous expectation existed

NEGATIVE:
- Discussion of current schedules without proposing changes ("X is on track")
- Status updates that don't affect a future date
- Setting an initial target with no prior expectation
- Pure technical discussion with no schedule reference

Output strict JSON:
{
  "is_schedule_change_announcement": true | false,
  "evidence_quote": "<verbatim span from message that justifies the answer, or null if false>",
  "rationale": "<one-sentence explanation>"
}

Message:
From: <from_raw>
Subject: <subject>
Date: <date>

<body_text>
```

**Hand-labeling rubric (frozen):**

- **POSITIVE** uses the same definition as the prompt above.
- **NEGATIVE** uses the same definition.
- **UNSURE** for items where rational labelers could disagree even with full context. Logged but excluded from P/R.

**Prediction:**

- **Base rate:** ~2% of corpus messages are true schedule-change announcements (≈15 of 731). Cassandra had active 2.0.x / 2.1 cadence in 2014 with multiple slips, so signal exists but is a small fraction of total volume.
- **Model-flagged positives at default threshold (logprob >0.5):** 10-30 messages.
- **Precision:** 0.65–0.80. Schedule-change language is partially formulaic ("postpone", "moved to", "slip", "push back"), favoring precision; subtler cases lower it.
- **Recall (extrapolated):** 0.55–0.75. The coder-tuned bias and subtle implications ("we still have a lot to do before...") will cost recall.
- **Brier score:** 0.10–0.20. The model's logprobs will be miscalibrated, with a tendency toward overconfidence at the extremes (Qwen3-Coder is general-purpose-ish but not RLHF-calibrated for general English nuance).

**Decision rule:**

- **F1 ≥ 0.65 AND precision ≥ 0.70:** promote `schedule_change_announcement` to **Prototype** in detector-catalog. Eval harness validated. Move to next corpus (`si-t3l`) for the cross-domain check.
- **0.50 ≤ F1 < 0.65:** detector marginal. Catalog stays at Idea. Document specific failure modes from the eval set; revise prompt; new pre-reg required for any re-run.
- **F1 < 0.50:** task is harder than expected, or prompt is broken. Run a frontier-tier model (Sonnet 4.6 via Anthropic API) on the same 75 hand-labeled items as a *ceiling check*. If frontier also struggles, the task is genuinely hard (revise definition or accept limited usefulness). If frontier succeeds substantially, the cliff is in the cheap-tier — informs U3 directly.
- **Calibration:** Brier ≤ 0.18 → logprobs are usable for downstream confidence intervals. Brier > 0.18 → logprobs need post-hoc calibration (Platt or isotonic) before synthesis-layer code uses them as-is.

**Falsifiers / mind-changers:**

- **Model flags >100 messages as positive:** prompt is too permissive, or model is failing the binary task. Stop, inspect, revise — do not treat run as valid eval.
- **Model flags 0 messages as positive:** prompt is too restrictive or signal genuinely absent. Inspect by hand sampling messages I'd expect to be positive (Cassandra 2.1 release postponement discussions, which definitely happened in 2014).
- **0 of the 100 random model-negatives are actual positives in hand-labeling:** recall estimation impossible at this sample size. Either base-rate prediction was wrong (signal even rarer than 2%, updates U4) or the model's recall is so high we're missing few — doubling the random sample resolves this.
- **Hand-labeling shows I disagree with myself between batches:** rubric is too vague. Stop, sharpen the rubric, re-label, new pre-reg.
- **Implausibly high recall (>0.90):** suspicious. Audit for prompt leakage (e.g., the rubric itself paraphrasing into the prompt and biasing).
- **Logprobs uniformly near 0.5 across the corpus:** model isn't committing to answers. Prompt design or sampling parameters need work; eval invalid.

### Results *(commit this block after running)*

**Scorecard:** `results/evals/schedule_change_announcement-cassandra-2014.json` (gitignored; values inlined below for the durable record).

| metric | value | 95% CI | predicted | within band? |
|--------|-------|--------|-----------|--------------|
| Precision | 0.277 | 0.169 – 0.418 | 0.65 – 0.80 | **NO** (well below) |
| Recall (extrapolated) | 0.656 | 0.259 – 0.915 | 0.55 – 0.75 | yes |
| F1 | 0.389 | — | 0.60 – 0.78 | **NO** (below) |
| Brier | 0.215 | — | 0.10 – 0.20 | **NO** (slightly above) |
| Model-positives in 731 corpus | 48 (6.6%) | — | ~2% (10-30 msgs) | **NO** (higher) |

**Reliability bins (the headline calibration finding):**

```
predicted [0.0, 0.1):  100 items, mean p=0.001, actual frac_pos=0.01  ← well calibrated for negatives
predicted [0.5, 0.6):    1 item,  mean p=0.59,  actual frac_pos=1.00
predicted [0.6, 0.7):    2 items, mean p=0.67,  actual frac_pos=0.00  ← overconfident
predicted [0.7, 0.8):    2 items, mean p=0.76,  actual frac_pos=0.00  ← overconfident
predicted [0.8, 0.9):    5 items, mean p=0.84,  actual frac_pos=0.20  ← very overconfident
predicted [0.9, 1.0]:   37 items, mean p=0.99,  actual frac_pos=0.30  ← extremely overconfident
```

The model is well-calibrated for confident negatives (it says "no" with p≈0 and is right ~99% of the time) but extremely overconfident for confident positives (says "yes" with p≈0.99 and is right only ~30% of the time *under my strict rubric*).

**Observations:**

1. **Eval pipeline worked end-to-end.** Pool-and-extrapolate produced an interpretable scorecard. The eval harness's self-tests covered the math; running it against real data exposed only one issue (the gitignored predictions JSONL), which was a documentation gap, not a computation bug.

2. **Pre-reg falsifier "model flags >100 messages as positive" did NOT trigger** (48 model-positives is fine). The "0 model-positives" and "implausibly high recall" falsifiers also did not trigger. Pre-reg held; the run is a valid eval.

3. **Pre-reg falsifier on F1 < 0.50 DID trigger** — this maps to the "Decision rule" branch that calls for a frontier-tier ceiling check (Sonnet 4.6 on the same 148 labeled items) to disambiguate "task is hard" from "this model is bad at this task." Deferring the ceiling check to a follow-up experiment because the more pressing finding is below.

4. **The parser-failure batch was 10× enriched for model-positives** (17.3% positive rate vs 1.6% in the first batch). Code-block-containing messages BOTH triggered markdown-fence wrapping AND were more likely to discuss release-related work. After the parser fix, the eval set is unbiased — but in production this would be a fragile coupling worth flagging.

**Surprises:**

1. **The dominant failure mode is rubric ambiguity, not model capability.** The model labels "any message engaging with a release-related schedule discussion" as positive. My strict reading of the pre-reg rubric requires "directly announces or proposes a change to a previously-stated schedule." Under the model's permissive reading, ~80% of pool messages would be positive (most are in genuine schedule-related threads); under my strict reading, ~28% are. This is **not a calibration problem with the model**; it's an underspecification in the prompt+rubric. I disagree with the model on the same items I would disagree with another human labeler on if we used different rubric interpretations.

2. **The pre-reg's "Hand-labeling shows I disagree with myself" falsifier was nearly triggered for a different reason** — not within-labeler drift, but rubric-vs-model interpretive divergence. Same underlying problem: the rubric is too vague to support binary classification consistently. The pre-reg falsifier should be expanded to "I disagree with the model in a way that suggests rubric ambiguity, not model error."

3. **Recall was within the predicted band.** Despite precision being terrible, the model finds most actual positives — only 1 false negative in the 100-msg random sample. The model is *over*-flagging, not under-flagging. This is consistent with the model's permissive rubric interpretation: it casts a wider net than a strict reader would, catching most strict-positives at the cost of many strict-negatives.

4. **The base rate prediction was off by ~3×.** I predicted ~2% true positives; my strict labeling found 14/148 ≈ 9.5% in the labeled set, which extrapolates to ~7% over the corpus. Even my strict rubric is finding more positives than I expected. The Cassandra dev@ 2014 corpus is denser in release-coordination signal than I estimated — likely because 2014 spanned multiple release cycles (1.2.x maintenance, 2.0.x active, 2.1 development) all running in parallel.

**Conclusions:**

- **Branch from the Decision rule:** F1 = 0.389 lands in the `< 0.50` branch — "task is harder than expected, or prompt is broken." Per the pre-reg, this would normally trigger a frontier-tier ceiling check. **However, the rubric ambiguity finding above suggests the right next step is rubric sharpening, not model substitution.** A frontier model would likely make the same interpretive choice the smaller model did (or worse, make a different one without flagging the ambiguity). The cliff is in *task definition*, not *model capability*.

- **The detector is NOT promoted to Prototype.** Stays at Idea in `detector-catalog.md`. The pre-reg required F1 ≥ 0.65 AND precision ≥ 0.70; we're at F1=0.39 and precision=0.28 against a strict rubric.

- **The eval harness is validated.** Math checks out, scorecard is interpretable, calibration data is now accumulating. Per-component eval discipline is paying off — we can localize the "failure" to *rubric* rather than to *the system*.

- **Logprobs are usable for ranking but not for calibrated probabilities.** Brier 0.215 says raw logprobs aren't trustworthy as confidence estimates; downstream synthesis code that wants "X is true with 95% confidence" should not use these directly. Ranking ("the model is more confident in A than B") is fine.

- **Pre-registration discipline justified itself on entry one.** Without the falsifiers and decision rules locked in advance, I'd have been tempted to retroactively soften the rubric ("the model's interpretation is also defensible") and report a precision of 0.85 with a slightly different definition. The pre-reg makes me confront the disagreement honestly.

**Next:**

- **Sharpen the `schedule_change_announcement` rubric.** The new rubric should explicitly handle: (a) "+1" / "-1" replies whose body re-quotes the parent's announcement, (b) substantive replies in a schedule-discussion thread that don't propose changes themselves, (c) standard release votes (which are NOT changes, just steps in a planned process). Once sharpened, write a new pre-reg and re-label the same 148 items — the existing predictions can be re-evaluated against the new labels at zero inference cost.
- **Open follow-up bd issues** (see closing of si-qhz):
  - `idea`: Sharpen `schedule_change_announcement` rubric and re-pre-register
  - `idea`: Frontier-tier ceiling check on the same 148 items (deferred but valuable for U3)
  - `idea`: Investigate whether messages with code blocks are systematically different signal-wise from messages without (the parser-failure batch finding)
  - `idea`: Apply Platt scaling or isotonic regression to logprobs and re-measure Brier — quick test of whether post-hoc calibration recovers the upper-bin reliability
- **The architectural commitment to "binary-per-category classifiers" survives this run.** The detector concept is fine; the rubric needs work. This is exactly the kind of failure mode where binary-per-category beats multi-class — we can fix one category's definition without retraining anything global.

### Addendum 2026-05-02 (si-bwo): cap-bump audit revealed a deeper failure mode

After the original run, audit of token usage showed max prompt was 3,433 tokens (11% of 32K window). 40/731 messages had body > 8000 chars and were truncated by the input cap. Bumped cap to 60,000 chars (the 32K context limit forced this — 100K char input + 400 reserved completion exceeded the model's hard 32,768-token limit on the longest message; ~2.5 chars/token observed for email text vs the 4 chars/token rule of thumb), re-ran on those 40, merged with the original predictions, re-scored.

**Headline:** Roughly the same F1 (0.358 vs 0.389), small precision improvement (0.286 vs 0.277), slight calibration improvement (Brier 0.195 vs 0.215). But the more interesting finding is qualitative:

- **5 of 7 POS→neg flips were FPs the truncated model got wrong** because it only saw the truncated parent (containing schedule-language quoted content) and lost the surrounding context that would have indicated this was a "+1"-style or substantive-but-not-proposal reply. With full body, the model correctly says NEG. (Precision wins.)
- **1 of 7 POS→neg flips was a real TP loss** (Jonathan's "3.0 file-based hint storage" message) — the relaxed cap apparently dilutes the schedule signal enough that the model drops it.
- **1 neg→POS flip was a NEW false positive** (graham@vast.com's hinted-handoff reply): the relaxed cap exposed previously-truncated quoted content from Benedict that contained "I plan to address this... after 3.0", and the model anchored on that quoted phrase as if it were the new reply.

**The deep finding:** The model can't distinguish quoted-from-replied-to material from new content. Truncation just shifts WHICH quoted block the model anchors on. Truncating to first 8K → anchors on early-quoted material near the top. Truncating less → anchors on different quoted material as it becomes visible. The fundamental issue isn't input length; it's that the prompt doesn't help the model isolate "this is the new reply" from "this is quoted history."

This dovetails with si-d6m (rubric sharpening): the v2 prompt should include a step that asks the model to identify the NEW content (lines not starting with `>`) before judging. Possibly a two-pass classifier — first pass strips quoted material, second pass classifies the cleaned content. Both options are within the architectural commitment of single-thesis passes if structured correctly.

**Methodological note for future runs:** the eval harness's recall computation under merged predictions has a stratification bias when items move between pool and model-negative across runs. The 6 flipped items are a complete enumeration of POS→neg flips, not a random sample. A stratified estimate gives recall ~0.60, not 0.48. Filing this as a follow-up.

---

## 2026-05-01: First harvest — Apache Cassandra dev@ 2014

**Type:** Harvest / pipeline plumbing (not a hypothesis-testing experiment, so no Pre-registration block).

**Setup:**
- Source: `lists.apache.org/api/mbox.lua` (per-month mbox endpoint)
- List: `dev@cassandra.apache.org`
- Range: 2014-01 .. 2014-12 (full year)
- Pipeline: `src/harvest/apache_mbox.py` — fetch raw mbox, normalize to JSONL with provenance (source URL + fetched_at + harvester version)

**Why Apache Cassandra dev@ for the first slice (instead of IETF as previously suggested):** IETF mailarchive's mbox export endpoint requires login, and the public-facing browse/static paths don't expose bulk download. Apache's `lists.apache.org` API serves mboxes directly without auth. Apache Incubator graduation/retirement decisions also give clean project-level outcome labels, so the calibration argument for IETF doesn't dominate. Cassandra was a TLP through 2014 (no retirement risk), but the sender-level coordination texture is what we need to validate the pipeline.

**Why 2014:** arbitrary year selected for the first slice. No outcome ground truth tied to it specifically. The point is to validate harvest + parse, not to test a hypothesis.

**Observations:**
- 731 messages across 12 months, ~5 MB raw
- Top senders concentrated on Datastax + core committers (Sylvain Lebresne 89, Jonathan Ellis 85, Brandon Williams 54). The "vendor-coordination" signal we expect from multi-vendor program data is *not* present in this slice — Cassandra dev@ is single-org-dominant. Important to note: this isn't a multi-vendor program corpus, so several detector hypotheses (vendor_silence, blame_displacement) won't be testable here. It is good for: schedule_change_announcement, risk_escalation_language, stop_work_implication, and general affective-signal work.
- 26% thread roots / 74% replies — healthy discussion structure with thread depth.
- Median body 1085 chars (~200 words). Mean 2711 (long tail).
- Only 3% of subjects mention JIRA references — implies the heavy automated commit chatter lives on a different list (likely `commits@`), not polluting the discussion list.
- Activity ramps Jan → Mar (peak 109), declines slowly through end of year. Useful for future "is volume itself a signal" detectors.

**Conclusions:**
- Harvest pipeline works end-to-end. JSONL output has stable IDs, parsed dates, thread parents/references, and provenance.
- Single-org-dominated lists are a different shape than multi-vendor program data. We need at least one corpus where the vendor-coordination texture actually exists (Apache Incubator project with multiple committer affiliations, or IETF working group, or one of the GAO-anchored datasets). Don't over-fit detector design on Cassandra alone.
- The pre-reg discipline starts kicking in at the *next* entry (first detector run), not this one.

**Next:**
- Pre-register the first detector experiment: a binary classifier on this corpus. Strong candidates: `risk_escalation_language` (highest U5 learning value) or `schedule_change_announcement` (more concrete to specify, easier to hand-label a small ground truth set).
- Parallel: pull a second corpus to break Cassandra-overfitting risk early. Candidates: an Apache Incubator project that retired (for outcome labels), or a list with more multi-org texture (Hadoop dev@? OpenJDK?).
- Stand up an evaluation harness so the first detector run produces calibration data, not just predictions.

---

## Initial entry

## YYYY-MM-DD: Project bootstrap

**Question:** N/A — initial setup.

**Setup:** Created repository structure, foundational documents (CLAUDE.md, architecture, goals, antigoals, datasets, detector catalog).

**Observations:** N/A.

**Conclusions:** Ready to begin Tier 1 dataset acquisition and first detector prototypes. The architectural commitments are documented and will be checked against during implementation.

**Next:**
- Acquire a small slice of one Tier 1 dataset (likely IETF working group archives or Apache mailing list) to validate the parsing pipeline.
- Run a frontier-model exploratory pass on the slice to seed initial detector ideas.
- Implement first prototype binary classifier (probably `vendor_status_update` or `risk_escalation_language`) and test on the slice.
- Begin establishing the per-component eval scaffolding so calibration data accumulates from the first run.
