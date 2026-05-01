# Experiment Log

Append-only log of experiments. The newest entries are at the top. The code is secondary; this log is the durable artifact.

Each entry should capture:
- **Date** of the experiment
- **Question** it was trying to answer (which unknown from goals.md)
- **Setup** — datasets, detectors, models used
- **Observations** — what was seen, including surprises
- **Conclusions** — what we now believe more or less strongly
- **Next** — what this suggests trying next

Be honest about what didn't work. Negative results compound as much as positive ones — they prevent re-running failed experiments and they shape what to try next.

---

## Entry template

```markdown
## YYYY-MM-DD: <Short title>

**Question:** Which unknown is this addressing? (e.g., U1: cross-domain generalization)

**Setup:**
- Dataset(s):
- Detector(s):
- Model(s):
- Approach:

**Observations:**
- What was seen
- Surprises
- Anything unexpected in the data or outputs

**Conclusions:**
- What we now believe
- What changed about our model of the problem

**Next:**
- What this suggests trying next
- Any new entries to detector-catalog.md or new questions for goals.md
```

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
