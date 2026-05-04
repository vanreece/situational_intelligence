# Detector Catalog

Running list of detector ideas, with status tracking. The catalog is intentionally messy and additive — bad ideas stay here marked as "tested, didn't generalize" so we don't re-derive them. Good ideas graduate to production status.

> **Catalog vs Beads.** This file is the canonical *typology* of detectors — what a given detector asks, what evidence it consumes, where we expect it to generalize. *Runs* of detectors (pre-registrations, experiments, calibration data) are tracked as Beads issues with edges back to `experiment-log.md` entries. Don't double-bookkeep run status here; query bd for "what's currently in flight on detector X."

## Status taxonomy

- **Idea** — described but not implemented
- **Prototype** — implemented and tried on at least one dataset
- **Validated** — works on at least 2 datasets with measured precision/recall
- **Production** — graduated to the production detector set with calibration data
- **Retired** — tried, didn't work or didn't generalize, kept here for negative documentation

Each detector entry should describe: what it asks, why it matters, what evidence it consumes, what it outputs, and what we expect it to generalize to.

## Structural detectors (the boring layer)

These detect violations of explicit constraints in structured data. No LLM reasoning required for the detection itself — though LLMs may be needed to extract the constraints from unstructured sources first.

### resource_double_booking

**Status:** Idea
**Asks:** Is a named resource (team, person, equipment, facility) committed to two non-compatible activities at overlapping times?
**Why it matters:** Highest-leverage boring layer signal. Computable from calendar + roster + project assignments. Catches conflicts humans miss because nobody is checking the intersection across all programs.
**Evidence:** Schedule data, resource rosters, project commitments.
**Output:** Conflict object with both activities, the resource, the overlap window, and confidence.
**Generalization:** Universal across all program types.

### dependency_violation

**Status:** Idea
**Asks:** Is a downstream task scheduled to start before its declared upstream dependency completes?
**Why it matters:** Catches plan-of-record incoherence. Often surfaces silent slips that nobody propagated through the dependency chain.
**Evidence:** Dependency graph, current scheduled dates.
**Output:** Violation with both tasks, the dependency relationship, the gap.
**Generalization:** Universal where dependencies are tracked.

### lead_time_squeeze

**Status:** Idea
**Asks:** Does the time remaining until a milestone fall below the historical lead time required for its critical inputs?
**Why it matters:** Quietly slipping predecessors compress feasibility windows that nobody is watching explicitly.
**Evidence:** Historical lead time data per vendor/process, current schedule.
**Output:** Milestone with squeeze factor, identified critical inputs, recommended action.
**Generalization:** Strong across physical/logistics-heavy programs.

### slack_consumption_drift

**Status:** Idea
**Asks:** Has the cumulative slack on a milestone's predecessor chain been silently consumed below a threshold?
**Why it matters:** Each individual slip is within tolerance; the aggregate isn't. Nobody owns the aggregate.
**Evidence:** Historical baseline plan, current state, per-task variance over time.
**Output:** Milestone with current slack, historical slack, rate of consumption.
**Generalization:** Universal where slack is meaningful.

## Linguistic detectors (text classification)

These detect categories of content in unstructured text. Binary-per-category, designed for the cheap classification tier.

### vendor_status_update

**Status:** Idea
**Asks:** Does this message contain a vendor's report on their work status?
**Why it matters:** Vendor status is the highest-density source of program signal. Identifying it routes to specialized extractors.
**Evidence:** Message text, sender metadata.
**Output:** Boolean + confidence.
**Generalization:** Strong across all multi-vendor programs.

### schedule_change_announcement

**Status:** **Validated (2 corpora)** — promoted 2026-05-04 after v3_elided cleared the decision rule on both Cassandra dev@ 2014 and Hadoop common-dev@ 2014. (Was Prototype 2026-05-02 via si-rrz; cross-corpus test on Hadoop initially failed with v2 in si-2wh, then v3 closed the gap.)
**Asks:** Does this message announce, propose, or imply a change to a previously-stated date or version target for a release, milestone, or planned work? Procedural mechanics (vote retries, vote-period adjustments, +1/-1 votes) explicitly excluded.
**Why it matters:** Schedule changes are the primary input to propagation logic. The rubric specifically targets *substantive* schedule changes — what would change a senior operator's planning picture — rather than every release-process event.
**Evidence:** Message text at quote-depth=2, with quoted line content elided to `[QUOTED]` markers (preserves "this is a thread reply" structure without the cheap-tier anchoring on quoted phrases).
**Output:** Boolean + p_positive (logprob-derived) + evidence_quote (constrained to author's new content) + rationale.
**Generalization:** Validated on **Apache Cassandra dev@ 2014** and **Apache Hadoop common-dev@ 2014** (filtered to remove `jira@apache.org` cross-posts and `*@builds.apache.org` Jenkins traffic).

**Operating point: `v3_elided` (current; adopted 2026-05-04)**
- Cheap-tier model: Qwen3-Coder-30B-A3B-Instruct-gptq-4bit at temperature=0
- v3 system prompt (3,524 chars; hash `57e9f055f0c5639e`)
- Body shape: depth=2 quote filter + `elide_quoted_lines` (each quoted-line content → `[QUOTED]`)
- Pool-direct scorecards (against existing labeled pools):
  - **Cassandra dev@ 2014 (158-label expanded pool):** F1 = 0.6364, precision = 0.7778, recall = 0.5385
  - **Hadoop common-dev@ 2014 (76-label expanded pool, 17 v2-pool + 50 random + 9 v3-pool):** F1 = 0.9583, precision = 0.9583, recall = 0.9583
- Wall-clock: ~42s per 731-message Cassandra corpus, ~75s per 1355-message filtered Hadoop corpus (concurrency=32, --no-logprobs)

**v3 vs v2 deltas:**
- v3 adds a POSITIVE clause for question-form / conditional-form proposals ("How about X by late Jan?", "Would that be better?") with a safety net for clarifying-someone-else's-proposal cases (the safety net the cheap-tier doesn't always honor — accounts for the 2 new Cassandra FPs in the v3 result).
- v3 adds a NEGATIVE clause for JIRA bookkeeping notices ("created version X in JIRA", "target version set to X (rNNNN)") — domain-specific to Apache projects with heavy JIRA rituals.
- Cassandra trade: +2 TPs recovered (Op-9 Sylvain "1.2.18 re-roll", Shuler "1.2.18 re-roll?"), -2 new FPs in `Re: Proposed changes to C* Release Schedule` thread (rhetorical questions misread).
- Hadoop trade: -2 FPs (both JIRA-bookkeeping cases dropped), +1 TP recovered (Arun "How about hadoop-2.8 by late Jan?"); +7 TPs surfaced from previously-unsampled pool. 1 FN remains (Arun "abandon the 2.3rc and re-release as 2.3"); 1 new FP (Subramaniam feature-inclusion request misread as schedule).

**Known failure modes:**
- **Cassandra:** 1 of 3 dropped TPs from the v2_elided era still missed (Ellis "1.2.17 takedown" — declarative not question-form). 2 new FPs in Cassandra are rhetorical questions about *someone else's* proposal — fix 2's safety-net language doesn't always steer the cheap-tier.
- **Hadoop:** 1 conditional-question TP missed ("I can abandon the 2.3rc and re-release as 2.3. Would that be better?" — version-semantics shift inside conditional framing). 1 borderline FP (JIRA target-version retargeting — diagnostic flagged this case as "unsure" boundary).
- **General (cross-corpus):** Cheap-tier `p_positive` distribution at temperature=0 + guided JSON is sharply bimodal (zero items in [0.01, 0.90] across both corpora) — logprob-based borderline triage is structurally unavailable. Cost-tier escalation routing must be content-structural (subject markers, etc.), not confidence-based.

**Calibration data:**
- Logprobs at temperature=0 are deterministic in chosen-token (essentially binary). Useful for hard yes/no, not for confidence intervals.
- Per-run noise floor at depth=2 is F1 ±0.015 (si-pfo, 6-run measurement).
- vLLM occasional parse error (~0.07% rate observed); resumable classifier handles by skip + retry.

**Cost-tier escalation operating points:**
- **Cassandra v2 (validated, si-bm1):** P2 pool (NEG ∩ vote/proposal subject ∩ root-or-body>800) at 33% of corpus reaches F1=0.960 — within 0.003 of full-frontier F1=0.963.
- **Cassandra v3:** not yet measured (would require frontier-v3 on Cassandra; existing frontier predictions are v2-prompt).
- **Hadoop v3:** not yet measured (si-03o, in-flight). Note: with v3 cheap-tier already at F1=0.9583, the headroom for cost-tier escalation is small; the architectural-test value remains but the production-cost-savings argument is weaker.

**Rubric & prompt provenance:**
- v1 rubric frozen in si-qhz commit `7d64413` (F1 = 0.405, deprecated)
- v2 rubric frozen in si-d6m commit `3313c2a` (F1 = 0.727 with v2_strict body shape)
- v2_elided body shape added in si-rrz commit `277d52f` (F1 = 0.769 on 153-item Cassandra pool)
- **v3 rubric (current)** frozen in commit `e48c178` after diagnostic Opus pass on Hadoop failures (`docs/diagnostic-v2-prompt-vs-hadoop.md`). Two narrow clauses: question-form POSITIVE + JIRA-bookkeeping NEGATIVE. Adopted as operating point in commit `9533863`.

### risk_escalation_language

**Status:** Idea
**Asks:** Does this message contain language patterns associated with escalating risk (concern intensifiers, qualifier shifts, hedging changes)?
**Why it matters:** Captures the affective layer — facts may be unchanged but the framing has shifted.
**Evidence:** Message text + recent history from same author for baseline comparison.
**Output:** Boolean + intensity score + comparison to author baseline.
**Generalization:** Cross-domain plausible but needs validation. Likely most useful when combined with author-specific baselines.

### vendor_silence

**Status:** Idea
**Asks:** Has a vendor been silent for longer than their historical pattern?
**Why it matters:** Silence is information. Particularly when contractually obligated communication stops.
**Evidence:** Historical communication frequency, current gap.
**Output:** Vendor + gap duration + historical baseline + significance.
**Generalization:** Universal but requires historical data to establish baseline.

### blame_displacement

**Status:** Idea
**Asks:** Is this message subtly attributing responsibility to a different team/vendor in a way that diverges from previous attribution patterns?
**Why it matters:** Often a precursor to formal vendor disputes. Catches political maneuvering before it surfaces formally.
**Evidence:** Message text, history of attribution patterns.
**Output:** Boolean + parties involved + shift indicator.
**Generalization:** Plausible but politically sensitive — may not always be the right thing to surface.

### stop_work_implication

**Status:** Idea
**Asks:** Does this message imply that work has stopped or will stop, even if not stating so directly?
**Why it matters:** Stop-work events propagate aggressively through schedules and are often understated in initial communications.
**Evidence:** Message text.
**Output:** Boolean + confidence + inferred scope.
**Generalization:** Universal.

## Latent knowledge detectors

These detect cases where information exists somewhere in the system but may not have propagated to where it's needed. The class-three failure category.

### upstream_experience_unconsulted

**Status:** Idea
**Asks:** For a current decision or planning artifact, has anyone in the org touched a relevantly-similar circumstance upstream whose experience hasn't been incorporated?
**Why it matters:** This is the GB300 NPI lab pattern. The data exists but the connection wasn't made.
**Evidence:** Activity history (who touched what when), current decision context, similarity model.
**Output:** Decision context + candidate knowledge holders + similarity reasoning.
**Generalization:** Universal — this is the headline class-three capability.

### contradicting_signal_in_periphery

**Status:** Idea
**Asks:** Does a current planning artifact contradict information present in adjacent but uncited sources within the org?
**Why it matters:** Catches cases where the planner isn't aware of relevant data that exists.
**Evidence:** Plan content, adjacent source content, contradiction detection.
**Output:** Contradiction with both sources cited and gap analysis.
**Generalization:** Universal.

### stale_assumption

**Status:** Idea
**Asks:** Does a current plan rely on assumptions that have been updated or contradicted elsewhere since the plan was created?
**Why it matters:** Plans become stale when their grounding assumptions change but propagation doesn't happen.
**Evidence:** Plan creation timestamp, assumption extraction, subsequent contradicting evidence.
**Output:** Plan + stale assumption + updated information + recommendation.
**Generalization:** Universal.

## Aggregate / cross-cutting detectors

These run across multiple lower-level signals to produce composed judgments. They live at the synthesis layer rather than the classify/extract layers.

### linchpin_identification

**Status:** Idea
**Asks:** Which currently-active tasks have the greatest expected downstream impact if they slip?
**Why it matters:** The headline synthesis output. Tells operators where to focus attention.
**Evidence:** Dependency graph, current state, historical reliability per task type.
**Output:** Ranked list with reasoning per linchpin (longest-path / single-vendor / single-human / permit-gated / etc).
**Generalization:** Universal.

### confidence_interval_drift

**Status:** Idea
**Asks:** For each tracked milestone, has the confidence interval shifted (widened, moved out, moved in) since last evaluation?
**Why it matters:** Interval dynamics are themselves signal. An interval that should be tightening but isn't indicates someone isn't doing the work to reduce uncertainty.
**Evidence:** Historical predictions, current evidence base.
**Output:** Per-milestone interval delta with explanation of what drove the shift.
**Generalization:** Universal.

## Discovery mode detectors

These don't have specific category targets. They run periodically over content that hasn't matched any existing detector, looking for emergent patterns.

### orphaned_signal_clustering

**Status:** Idea
**Asks:** Among items that matched no existing detector, are there clusters that share characteristics? Could a new detector category be promoted?
**Why it matters:** Production detectors get stale as the world generates new patterns. Discovery mode is how the catalog grows.
**Evidence:** "Matched nothing" bucket from production runs.
**Output:** Candidate clusters with sample items, suggested detector definition, priority for review.
**Generalization:** Universal — this is the meta-detector that keeps the system relevant.

### consequence_correlation_mining

**Status:** Idea
**Asks:** Across historical data with known outcomes, which combinations of contemporaneous signals most strongly predict bad outcomes?
**Why it matters:** Discovers consequence-defined categories that don't have obvious linguistic patterns. The struggle/strife detector pattern.
**Evidence:** Historical signals + outcome labels.
**Output:** Candidate detector definitions with predictive power.
**Generalization:** Best when run across multiple datasets to find patterns that persist across domains.

## Retired / negative results

(Empty for now. Will accumulate as experiments run and detectors fail to generalize.)

## How to add to this catalog

When proposing a new detector:

1. Specify what question it asks (must be answerable yes/no for binary detectors, or with structured output for extraction detectors).
2. State why it matters in operational terms — what decision does it inform?
3. Identify what evidence it needs and whether that evidence is reliably available.
4. Predict where it generalizes and where it doesn't.
5. Mark status as Idea until prototyped.

When retiring a detector:

1. Don't delete the entry. Move it to "Retired / negative results" with a note on what was tried and why it didn't work.
2. Negative documentation is valuable — it prevents re-derivation and informs future detector design.
