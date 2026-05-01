# Architecture

This document captures the architectural commitments of the project and the reasoning behind them. It's the place to come back to when a design decision feels tempting but might violate a deeper principle.

## The core thesis

**The structure around the model is where the value is.** Foundation model capability is rising for everyone. A product whose value prop is "we wrote a clever prompt" gets eaten by the next model release. A product whose value prop is "we built a structured system of single-purpose passes with clear interfaces, evaluated against real outcomes, with calibration data accumulating over time" gets *better* with model improvements rather than obsolete.

The harness is the product. The model is the engine. The opinion encoded in the harness is the moat.

## Layered architecture

The system has five layers. Each layer has a different job, a different model-capability target, and a different evaluation strategy.

### 1. Harvest layer

**Job:** Pull from heterogeneous sources (Slack, Jira, email, mailing list archives, status documents, transcripts, vendor portals, calendar systems).

**Model capability:** Minimal. Mostly glue code, API integrations, and parsers. No LLM reasoning here.

**Evaluation:** Coverage and freshness. Are we catching everything? Is the lag from source-update to ingested acceptable?

**Discipline:** This layer is mostly solved as a category. It's where every competitor will also do well. We don't differentiate here. We aim for "comprehensive and reliable" and move on.

### 2. Classify layer

**Job:** Decide what kind of thing each ingested item is. Route to appropriate extractors. Filter noise from signal.

**Model capability:** Small, fast, narrow. Per-category binary classifiers. "Is this a vendor status update, yes or no" is a much easier question than "which of these 47 categories is this," and a small model can answer it as accurately as a large one at a fraction of the cost.

**Evaluation:** Per-classifier precision and recall, with operating points tuned per category. Vendor-silence-as-warning wants high recall. Routine-status wants high precision. Each classifier lives at its own optimal point on its own frontier.

**Discipline:**
- Add new categories by adding new binary classifiers, not by retraining a multi-class classifier.
- Track "matched nothing" and "matched many" as first-class signals worth investigating.
- Periodically sample the matched-nothing bucket with a heavier model to discover patterns worth promoting to new detectors.

### 3. Extract layer

**Job:** Pull structured information out of items the classifier flagged as relevant. "What vendor, what milestone, what date, what change" from a status update. "Who is concerned, about what, since when" from a Slack thread.

**Model capability:** Mid-tier. The task requires understanding context but is still narrow enough that a tightly-scoped prompt with a smaller model often outperforms a larger model that "convinces itself" to wander.

**Evaluation:** Field-level accuracy against hand-labeled ground truth. Extraction errors are usually localized — wrong date, missed entity — and are evaluable per-field rather than per-document.

**Discipline:**
- Single-thesis passes only. One pass extracts vendor info; a separate pass extracts schedule info; a separate pass extracts risk language. Never combine.
- Structured output schemas. Free-text outputs are forbidden at this layer.
- Provenance is mandatory. Every extracted field has a pointer to the source span that produced it.

### 4. Synthesize layer

**Job:** Combine extracted signals across sources to produce judgments — linchpin identification, risk ranking, propagation of slips, briefing content.

**Model capability:** Capable models with reasoning. This is where latitude is rewarded, where the work benefits from holding multiple sources in context simultaneously and reasoning about their interactions.

**Evaluation:** Calibration against retrospective ground truth (did the linchpins we identified slip more than the non-linchpins? did our P90 dates hit 90% of the time?). Calibration is the trust mechanism.

**Discipline:**
- Cross-source synthesis only — this layer never re-parses raw text. It works over structured outputs from the extract layer.
- Confidence intervals are first-class. The system reports uncertainty and tracks calibration over time.
- Bidirectional flow: this layer can request additional extraction when a synthesis question requires evidence the system hasn't yet pulled.

### 5. Present layer

**Job:** Surface synthesis outputs to specific human operators in their specific frame. Daily briefings, weekly retros, on-demand Q&A, real-time alerts.

**Model capability:** Capable models for tone and framing. The substantive content comes from the synthesis layer; this layer is making it readable for a specific human.

**Evaluation:** Operator reaction. Voice memos, marked-up briefings, "you missed X" / "you overweighted Y" feedback. This is where the loop closes.

**Discipline:**
- Role-conditioned views over the same underlying data. TPM, VP, ops lead, finance lead all see different surfaces over the same substrate.
- Customization via composable archetypes (Amazon-TPM-style, aerospace-TPM-style, etc.) rather than monolithic personas. Knobs that compose, not sliders that don't.
- The system has no default opinion about what good judgment looks like. Customization is recognition that craft is heterogeneous, not concession to user preference.

## Cross-cutting principles

### Provenance everywhere

Every claim the system makes — every classification, every extraction, every synthesis judgment — traces to specific evidence with timestamps. "Why did the system flag Memphis as the top linchpin yesterday but not today" is a query, not a forensic reconstruction.

### Calibration as compounding asset

Every prediction the system makes is logged in a structured form that lets it be compared against eventual ground truth. Six months in, this is a calibration corpus that no competitor can replicate. The eval scorecard is both an internal improvement tool and an external trust artifact.

### Discovery vs production

Production mode runs known detectors fast and cheap. Discovery mode samples the long tail (matched-nothing, matched-many, surprising-correlations) with heavier models to find patterns worth promoting to new detectors. Both modes run continuously; they're not separate phases.

### Time boundaries, not random splits

Evaluation uses time-bounded splits. Train on documents from before time T, evaluate on documents from after time T. Random splits leak information backward through time and produce misleadingly good results. The production regime is "predict what's forming," and that's only honest to evaluate against future data.

### Affective signal as separate channel

Reading between the lines — detecting that someone is more worried than their words literally state — is a separate detector channel from factual extraction. The factual extractors should be conservative and literal. The affective detectors should run in parallel and produce their own signal type. The synthesis layer combines them.

### Class-three failures as primary value driver

The most valuable thing the system can do is identify decisions being made under information gaps that exist within the organization but haven't propagated to the decision-maker. This is the class-three failure pattern — context available, decision misaligned with available context. The system's primary job is making latent knowledge visible to people who would benefit from it.

## What we deliberately do not do

- **No general-purpose AI assistant.** The system has narrow, well-defined responsibilities. It does not chat about arbitrary topics.
- **No autonomous decisions.** The system surfaces, flags, and recommends. Humans decide.
- **No black-box outputs.** Every claim is interrogable. "Why are you saying this?" always has an answer in structured form.
- **No multi-objective prompts.** Single-thesis discipline is non-negotiable.
- **No prose-as-state.** Structured intermediate representations everywhere. The LLM queries state through tools, not by re-parsing.
- **No cross-tenant data mixing.** Eval corpora are per-customer or per-program. We do not train detectors on customer A's data and serve them to customer B without explicit consent.

## Architectural decisions that are deferred

These are real questions we will need to answer eventually, but not yet:

- **Storage substrate.** Postgres for now. Dolt-style versioning is an option later if cell-level history becomes load-bearing for the audit story.
- **Vector retrieval.** Probably needed eventually for the latent-knowledge-proximity graph. Not needed for v0 — explicit structured queries get us further than people expect.
- **Orchestration framework.** None for now. As the pipeline grows, we may want a real orchestrator. Current default is plain Python with explicit calls.
- **Model selection per layer.** Will be empirically determined by the spaghetti-at-the-wall methodology. No premature commitment.
- **UI / surface for operator interaction.** Briefings as plain text or markdown for now. UI is downstream of having content worth surfacing.
