# Detector Catalog

Running list of detector ideas, with status tracking. The catalog is intentionally messy and additive — bad ideas stay here marked as "tested, didn't generalize" so we don't re-derive them. Good ideas graduate to production status.

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

**Status:** Idea
**Asks:** Does this message announce or imply a change to a scheduled date?
**Why it matters:** Schedule changes are the primary input to propagation logic.
**Evidence:** Message text.
**Output:** Boolean + confidence + (if true) extracted previous and new dates.
**Generalization:** Universal.

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
