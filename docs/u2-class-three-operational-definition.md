# U2: Class-three failure — operational definition (draft)

> **Status:** Draft, grounded in the Rogers Commission Challenger case. Not yet validated against a second case. Will need cross-case validation before promotion.
>
> **Beads ref:** si-aa5
>
> **Method:** Reverse-engineered from Rogers Commission Volume I Chapter V ("The Contributing Cause of the Accident") and the Feb 14, 1986 hearing testimony (Volume IV). The Commission's own structural framing of the Challenger class-three failure is unusually explicit; this document distills that framing into detector-buildable terms.

## The framing in the Commission's own words

> "The decision to launch the Challenger was flawed. Those who made that decision were unaware of the recent history of problems concerning the O-rings and the joint and were unaware of the initial written recommendation of the contractor advising against the launch at temperatures below 53 degrees Fahrenheit and the continuing opposition of the engineers at Thiokol after the management reversed its position. They did not have a clear understanding of Rockwell's concern that it was not safe to launch because of ice on the pad. **If the decisionmakers had known all of the facts, it is highly unlikely that they would have decided to launch 51-L on January 28, 1986.**"
> — Rogers Commission, Vol. I Chapter V, ¶1

This is essentially the Commission's operational test: *had the decision-makers known what the rest of the system knew, the decision would have been different.*

## The detection target

A **class-three failure** consists of:

1. A **decision context** — a specific identifiable decision (or class of decision) that requires/required action by a named decision-maker at a knowable time.
2. **Latent context** — information that, at the time of the decision, existed within the organization in some form (memo, conversation, prior briefing, engineering analysis, monitoring signal).
3. **A propagation gap** — that information did *not* reach the decision-maker, or reached them in a form that did not convey its decision-relevance.
4. **Counterfactual relevance** — had the information reached the decision-maker in the right form, the decision would plausibly have been different.

All four must hold. Condition 4 is what distinguishes class-three from "noise that wasn't surfaced and shouldn't have been."

## Axes the Challenger case exposes

The Commission's reconstruction reveals at least four distinguishable axes along which class-three failure can occur. Each is a different shape of detector substrate.

### Axis A: Temporal accumulation
Warnings existed for years and were never aggregated into a load-bearing form. (Boisjoly's July 1985 memo, Ebeling's "Help!" weekly report, the 1977 Leon Ray briefing chart, the criticality-1 reclassification, six consecutive launch-constraint waivers.) None of these individually broke through; the sum should have.

**Detection signature:** repeated low-intensity concerns about a specific risk vector across time, none of which trigger a documented escalation, with no mechanism summing them.

### Axis B: Hierarchical bypass
Information present at one organizational level did not propagate up. Mulloy's testimony — "Everyone, sir" knew — but the Commission found "Neither the launch constraint, the reason for it, or the six consecutive waivers prior to 51-L were known to Moore (Level I) or Aldrich (Level II)."

**Detection signature:** concerns documented at level N do not appear in the artifacts level N+1 reads; the gap is between *acknowledgment within a tier* and *escalation across tiers*.

### Axis C: Channel mismatch
Concerns existed in informal channels (memos, task force notes, weekly activity reports) but did not appear in formal decision channels. "No mention of the O-ring problems...appeared in the Certification of Flight Readiness" — "No mention appears in several inches of paper comprising the entire chain of readiness reviews."

**Detection signature:** content X exists in informal/peripheral channels; the formal decision artifact for the same period does not contain X.

### Axis D: Reversal under pressure
Concerns reached decision-makers, were initially recognized, then were reversed under pressure. Thiokol's pre-launch teleconference: initial recommendation was "do not launch below 53°F"; after a 30-minute off-line caucus, Thiokol management overruled their engineers; the reversal was the basis for the "go" recommendation that propagated upward. The reversal itself was not flagged when the new recommendation was communicated to NASA.

**Detection signature:** a concern is documented, then the documented position changes, with the reversal not surfaced as a load-bearing aspect of the decision record.

## Decomposition into binary-per-category detectors (one option)

The architectural commitment to single-thesis / binary-per-category is an optimization, not a hard rule. But if it works for U2, it preserves the cost-tier hierarchy and per-component eval discipline. A candidate decomposition:

- **D1: concern_raised** — Does this document express a specific risk to a specific decision/event/program with engineering or operational substance? (Boisjoly July 1985 memo: yes. Generic gripe: no.)
- **D2: concern_acknowledged** — In a paired later document, is the prior concern referenced/addressed/resolved? Or is it ignored?
- **D3: concern_in_formal_record** — Does the relevant formal decision artifact (review record, certification, briefing slide) contain the concern in its decision-relevant form?
- **D4: concern_reversal** — When a concern's documented position changes, is the reversal flagged in the new record?
- **D5: concern_audience_match** — Does the concern's communication path actually reach the decision-maker, or only intermediate parties?

Each is a binary-per-document classification. Class-three failure is then a synthesis-tier judgment composed from D1-D5 outputs across a decision context's document set.

**Risk of this decomposition:** D2 and D5 require *cross-document* state (paired with prior concern, paired with audience identification). The architecture has structured intermediate state for exactly this, so it's not blocked — but it pushes more work into the synthesis layer than `schedule_change_announcement`-style detectors do.

## Decomposition as a synthesis-tier task (alternative)

Skip per-document binaries. Treat U2 as: given a decision context + a corpus of documents in its scope, the synthesis-tier model identifies (a) what concerns existed, (b) what their chain of acknowledgment was, (c) whether they reached the decision-maker, (d) what the counterfactual is. This is a multi-step structured inference, not a binary classification.

Trade: more capability per pass, less per-component evaluability, more synthesis-tier cost. May be the right shape if D2/D5 cross-document logic dominates anyway.

**Recommendation: prototype both shapes against the same case and compare.** The cost-tier discipline says decompose where the cheap tier carries it; consolidate where the synthesis tier earns its keep.

## Falsifiers — when something looks like class-three but isn't

1. **Correctly-ignored concern.** A concern was raised, was correctly judged not decision-relevant by someone with appropriate context, and the decision was correct. (Rockwell's ice-on-pad concern is partial example: it reached Aldrich, was discussed, judged manageable; it later turned out not to be the cause of the accident. The Commission flags the *process* as troubling but does not class this as "ignored fatal warning.")
2. **Acknowledged-and-resolved.** Concern raised, formally addressed, resolved with a documented closure that the decision-maker had access to.
3. **No counterfactual relevance.** Concern raised, didn't propagate, but knowing it wouldn't have changed the decision because countervailing facts dominated.
4. **Manufactured-in-retrospect.** A document looks prescient when read post-disaster but in context didn't actually express a load-bearing concern. (This is the retrospective-bias hazard, U6.)

## Methodological hazards

- **Retrospective bias.** Reading Chapter V with the disaster in mind, every prior warning looks load-bearing. The detector must be evaluable on contemporaneous text WITHOUT retrospective access. Pre-registration must specify what the model sees and what it doesn't.
- **Pretraining contamination.** Frontier models have read about Challenger. A "frontier model identifies class-three structure on Challenger transcripts" result is partially case-recognition. Mitigation: anonymize names/dates/programs in test material, OR use a less-famous case (si-2c6) for the actual detection test.
- **Decision-boundary fuzziness.** Challenger has a clean decision boundary (launch on Jan 28). Many real programs have softer boundaries — "the schedule slipped" is a series of micro-decisions rather than one big one. Operational definition needs to handle this.
- **Counterfactual relevance is hard to score.** Condition (4) above requires judging whether known information would have changed the decision. The retrospective is helpful here but contaminates the labeling. For initial work, accept the Commission's own counterfactual claims as the operationalized version.

## Implications for corpus selection

- **Native machine-readable contemporaneous text is required for detection testing.** The Rogers Commission appendices (the most direct primary source) are scanned JPGs, not OCR'd. Either OCR investment is needed, or detection testing happens on a corpus where contemporaneous text is born-digital.
- **For Phase 1 operationalization (this document), the synthesis chapters + hearing testimony are sufficient.** The class-three structure is documented in machine-readable form there; we don't need OCR to *understand* what we're detecting, only to *test detection*.
- **Crossrail NAO, GAO program reports, Apache Incubator retired projects** are corpora to evaluate against this constraint. Each is born-digital. Crossrail and GAO retain the Challenger-shaped structure (formal decision record + pre-decision correspondence + retrospective). Apache Incubator has a different shape (mailing list discussions instead of formal records); class-three structure if present is more diffuse.

## What this document is and is not

This is a **target definition**, not a detector spec or a pre-registration. It says *what we're trying to detect*, not *how we'll evaluate any specific detector or what we predict the results will be*. Each concrete experiment under U2 needs its own pre-registration with predictions, decision rules, and falsifiers per the project's standard discipline.

Concrete experiments this document enables (each its own bd issue + pre-reg when ready):

- **Op-A: Synthesis-tier probe on Challenger** — frontier model reads pre-launch contemporaneous text (from hearings + Volume I narrative reconstruction), identifies candidate class-three structure, output compared to Commission findings. Tests: can the model see the structure at all, and does retrospective contamination dominate?
- **Op-B: D1 (concern_raised) on Apache Incubator dev/private list excerpts** — Phase 1 of the binary decomposition path, on a different corpus, with cleaner native text. Tests: does the operational concept of "concern raised about a specific risk to a specific decision/event" yield consistent labels?
- **Op-C: Retrospective contamination diff** — same model, same corpus, with vs without retrospective context in scope. Quantifies how much pretraining/retrospective contamination is shifting the findings.
- **Op-D: Cross-case generalization of the operational definition** — does the same definition + falsifiers, applied to a second well-documented class-three case (Columbia, Crossrail, OPM data systems), produce coherent labeling without ad-hoc adjustment?

## Open questions for user

1. Is the four-condition test (decision context, latent context, propagation gap, counterfactual relevance) the right operational target, or is this carving up a different problem than what you mean by "situational intelligence"?
2. Is "the Commission's own counterfactual claim" an acceptable proxy for condition 4 in initial work, accepting that we'll need a non-retrospective counterfactual mechanism eventually?
3. Should the first concrete experiment be Op-A (probe Challenger directly, accepting contamination) or Op-B (start binary decomposition on Apache Incubator, lower-stakes baseline)?

These shape what gets pre-registered next.
