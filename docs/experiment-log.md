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
