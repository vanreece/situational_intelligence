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

*(To be appended after the runs complete and the analysis lands.)*

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
