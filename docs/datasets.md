# Datasets

This document is the running reference for public datasets we're using or considering. Each entry includes what the dataset is, what unknowns it helps reduce, what shape of signal it contains, and how to acquire it.

The goal is *complementary coverage*, not exhaustive coverage. We want enough breadth across program domains that detectors which generalize stand out from detectors that overfit to one corpus.

## Tier 1: Acquire and ingest first

These four cover the primary axes (formal program documentation with retrospectives, professional technical coordination, affective signal with ground truth) and are sufficient to begin meaningful experiments.

### GAO defense and IT program assessments

**What:** Annual GAO assessments of major DoD weapon systems and major federal IT investments. Decades of reports, each covering specific programs with cost variance, schedule variance, identified risks, and retrospective analysis.

**Unknowns served:** U1 (cross-domain generalization), U2 (class-three contemporaneous detection), U6 (retrospective bias).

**Signal shape:** Highly structured PDF reports written in formal register. Contains both contemporaneous program documentation (referenced extensively) and retrospective synthesis. The GAO's own reasoning chains are themselves a training signal for "what good synthesis looks like."

**Acquisition:** Public via gao.gov. Reports are PDFs; need to be downloaded and parsed. Annual assessments are the most useful — start with the past 5-10 years of "Defense Acquisitions Annual Assessment" and "IT Portfolio."

**Notes:**
- Has the unusual property of containing ground truth alongside contemporaneous signal in a single corpus.
- Watch for retrospective bias — GAO benefits from hindsight in ways our detectors won't have.
- F-35 and Columbia-class submarine appear repeatedly across reports; good candidates for deep dives.

### Apache Software Foundation mailing lists

**What:** Decades of public mailing list archives across hundreds of Apache projects. Covers project coordination, technical disagreements, governance issues, and project lifecycles from incubation through retirement.

**Unknowns served:** U1 (cross-domain generalization — tests whether our detectors work on software coordination), U4 (signal density), U5 (affective signal extraction).

**Signal shape:** Email threads in professional-technical register. Often shows the texture of disagreement, escalation, and consensus-building across organizational boundaries. Includes both successful projects and clearly-failing-in-retrospect projects.

**Acquisition:** Public mbox archives at lists.apache.org/list.html. Per-project archives can be downloaded in mbox format. Apache Incubator lists are particularly useful because they include projects that succeeded and failed at the incubation gate.

**Notes:**
- High volume — useful for stress-testing harvesting and classification at scale.
- Different projects have different cultural registers; good for testing detector portability.
- Outcomes are inferable but not always cleanly labeled (which projects "succeeded"?).

### IETF working group archives

**What:** All RFC process discussions and working group mailing lists since 1986. Multi-vendor technical coordination with commercial interests at stake; consensus-building under conflicting incentives.

**Unknowns served:** U1, U5 (affective signal in professional register), U7 (what useful synthesis looks like in adversarial-ish coordination).

**Signal shape:** Long-form technical mailing list discussions. Vocabulary of formalized disagreement ("I have concerns" / "I object" / "I will not implement") that maps onto affective intensity. Outcomes (RFCs adopted, withdrawn, ignored) are clearly documented.

**Acquisition:** Public archives at mailarchive.ietf.org. Per-working-group archives downloadable. Pair with the RFC index at rfc-editor.org to align discussions with eventual outcomes.

**Notes:**
- Particularly good for detector training because the formal vocabulary partially labels affective intensity.
- TLS, HTTP, and QUIC working groups are interesting because the technical and commercial stakes are high.
- Failed working groups (those that didn't produce RFCs or whose RFCs weren't adopted) are valuable negative examples.

### NASA Aviation Safety Reporting System (ASRS)

**What:** Pilot self-reports of aviation safety incidents, anonymized. Each report describes a situation, what was done, and what happened. Includes severity classification.

**Unknowns served:** U5 (affective signal with calibrated severity), U6 (calibration in a domain with explicit ground truth).

**Signal shape:** Short narrative reports in professional register, written deliberately to convey concern without alarm. Calibrated severity labels make this gold-standard training data for "what does professional understatement of serious situations look like."

**Acquisition:** Public via asrs.arc.nasa.gov. Database includes hundreds of thousands of reports searchable by various criteria. Bulk export available.

**Notes:**
- Smaller per-report than the other corpora but very high signal density.
- The closest available analog to "professionals describing concerning situations in formal register" — register transfers well to program management contexts.
- Severity labels enable calibration in a way that the other corpora don't.

## Tier 2: Add after Tier 1 is yielding results

### NAO (UK National Audit Office) reports on government projects

Crossrail, HS2, large IT projects. Excellent because British oversight produces unusually grounded retrospective analysis with explicit reconstruction of decision chains.

### Aerospace post-mortems

Rogers Commission (Challenger), CAIB (Columbia), 737 MAX investigations. Smaller corpora but extremely high signal density on class-three failures specifically. Each is essentially a labeled training example for "what class-three failure detection should produce."

### Linux Kernel Mailing List (LKML)

High volume, distinctive register (more direct than other technical communities), spans decades. Useful for testing detector robustness across communication styles.

### Major Public Construction Projects

California High-Speed Rail (FOIA-accessible documents and audit reports), Big Dig (extensive published retrospectives), Crossrail (already mentioned). Construction is the domain where critical-path discipline was developed; useful for stress-testing dependency-graph reconstruction.

## Tier 3: Reference / contrast

### Enron email corpus

Iconic for organizational communication research. Worth knowing about and possibly using as a sanity check, but heavily picked-over and email-shaped (transfers less cleanly to chat-shaped operational data than the Apache and IETF corpora).

### Federal IT Dashboard (itdashboard.gov)

Structured project status data for major federal IT investments. Useful as a structured-data complement to the GAO narrative reports — same projects, different format. Good for testing whether our extraction produces results consistent with the structured ground truth.

### USAspending.gov

Federal contract data. Could be useful for vendor-coordination ground truth (which contracts went to which vendors when), but probably overkill for the exploration phase.

## Datasets we are deliberately not using

### Internal/proprietary corpora obtained without consent

Even if we had access to internal Slack archives or Jira instances from companies we know, using them without explicit consent crosses ethical and legal lines. The public-data approach is the right approach.

### Heavily journalistic sources (news articles, magazine retrospectives)

Tempting because they're well-written and accessible, but they're someone else's interpretation rather than primary signal. Training on journalism produces detectors that recognize journalism patterns rather than operational reality.

### Healthcare megaprojects (hospital builds, EHR rollouts)

Real coordination problems but the regulatory environment is so domain-specific that the signal is hard to generalize from. Out of scope for now.

### Customer support and helpdesk corpora

Different problem shape — high volume of similar issues rather than rare high-stakes coordination decisions. Different product category.

## Acquisition workflow

For each Tier 1 dataset:

1. Download a small slice first (single year, single project, single working group) to validate the parsing pipeline.
2. Build a normalizer that produces a common intermediate format — enough structure that detectors can run against it, but lossless enough that we can re-parse if our schema evolves.
3. Run an exploratory pass with a frontier model on a sample to see what kinds of signal are present. Use this to seed the detector catalog.
4. Then bulk-ingest the full dataset.

The temptation will be to bulk-ingest first and explore later. Resist it — exploration on the small slice is what tells us whether the parser is doing the right thing.

## Storage and provenance

All ingested data lives under `data/raw/` (gitignored) with provenance metadata: source URL, retrieval timestamp, license. The processed/normalized form lives under `data/processed/` (also gitignored). Code that does the ingestion lives under `src/harvest/` and is versioned.

Never modify files under `data/raw/`. If a dataset needs cleanup, the cleanup happens during the move to `data/processed/`, leaving the raw form intact for re-derivation.
