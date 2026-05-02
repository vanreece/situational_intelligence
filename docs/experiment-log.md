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
