# Goals

This document captures what this project is trying to learn, organized by priority and by what kind of unknown it's reducing. Goals here are about *learning*, not *building*. The build is in service of the learning.

## Primary unknowns to reduce

### U1: Does consequence-correlated detection generalize across program domains?

**The question.** We can probably build detectors that recognize "vendor silence as warning sign" or "schedule slip language" within a single domain. The interesting question is whether a detector trained on one domain (defense acquisition) fires correctly on another (open-source coordination, construction megaprojects, NASA programs). If yes, the substrate is general. If no, every vertical needs its own work.

**How we'll know.** Train detectors on a subset of datasets, evaluate fire rates and precision against held-out datasets from different domains. A detector that maintains >70% precision and >60% recall across domains is generalizing. One that requires per-domain tuning to get there is domain-specific.

**Why it matters.** Determines whether the eventual product is "TPM intelligence for hyperscaler buildouts" (single vertical, narrower market, easier to ship) or "situational intelligence substrate" (multiple verticals, larger market, longer to mature). The architecture supports either, but the early dataset selection should bias toward answering this.

### U2: Can class-three failures be detected contemporaneously, not just retrospectively?

**The question.** GAO retrospectives identify cases where context existed in the system but didn't propagate to the decision-maker. Can we identify these cases in real-time, *before* the bad decision is made, using only contemporaneous documents?

**How we'll know.** For datasets with rich contemporaneous documentation and known retrospective findings (F-35, JWST, Crossrail, Challenger), build a contemporaneous detector that runs on documents available before the bad decision. Score against the GAO/CAIB/NAO retrospective findings. Hit rate above chance is success; hit rate above 50% is product.

**Why it matters.** This is the headline capability that differentiates from "AI summaries of your project." If it works, it's the value proposition senior operators will pay for. If it doesn't, we fall back on the boring layer (resource conflicts, dependency violations) — still valuable, but a much smaller pitch.

### U3: How small can the cheap classification layer get without losing accuracy?

**The question.** The cost-tier hierarchy assumes that small narrow models can do classification work as well as large models for binary tasks. We need to empirically establish where the cliff is. GPT-4o-class? Llama-3-8B? Even smaller?

**How we'll know.** Run the same classification task across a ladder of models from frontier down to ~1B parameters. Find the point where precision and recall start to degrade meaningfully. That's the floor for production cost optimization.

**Why it matters.** Production economics. The classification layer runs on every input; saving an order of magnitude on its cost compounds enormously. Also future-proofing: if we know that today's small models do this well, we know that tomorrow's small models will do it cheaper.

### U4: What's the actual signal-to-noise ratio in operational text streams?

**The question.** When you ingest a Slack channel, a mailing list, or a project log, what fraction of items contain program-relevant signal? 1%? 10%? 50%? This determines the design of the gating layer and the cost structure of the system.

**How we'll know.** Run the classification layer against several public corpora (Apache mailing lists, IETF working groups, Kubernetes issues, Linux LKML) and measure what fraction of items match any detector. Cross-check with manual sampling.

**Why it matters.** Affects the architecture. If signal density is 1%, aggressive gating is essential and most processing budget goes to filtering. If signal density is 30%, gating matters less and extraction quality dominates.

### U5: Does affective signal extraction work reliably enough to act on?

**The question.** "Reading between the lines" — detecting that a status report's facts are technically fine but the tone suggests escalating concern — is the LLM-distinctive capability. But it might be the kind of thing that demos beautifully and fails in production. We need to know which.

**How we'll know.** Build affective detectors against the ASRS pilot reports (where retrospective severity is documented), Apache mailing list crises, and Enron emails (where collapse is documented). Score predictions against retrospective severity. Look for stability across domains.

**Why it matters.** If affective detection is reliable, the briefing system can flag "X is not saying it directly but is increasingly concerned" as a first-class signal. If it's unreliable, the system has to stick to factual extraction and the value proposition narrows.

## Secondary unknowns

### U6: How much does retrospective bias contaminate the training data?

GAO and similar bodies write with hindsight. Some of what looks like prescient warning identification was obvious-in-retrospect signal that wasn't obvious at the time. The time-boundary split discipline mitigates this but doesn't eliminate it. Worth measuring how much the bias matters and whether it makes contemporaneous prediction harder than retrospective evaluation suggests.

### U7: What does a useful briefing actually look like to a senior operator?

We can't fully answer this without a design partner, but we can develop hypotheses by generating briefings against public datasets and seeing which ones pass our own internal taste test. The point isn't to prove the briefing is right — it's to discover the failure modes (too long, too generic, too hedged, too aggressive) before exposing them to a real human.

### U8: Where does the dependency graph need to be reconstructed vs. maintained?

Some dependencies are explicit (Jira "blocks" relationships, Gantt chart dependencies) and just need to be ingested. Others are implicit and need to be inferred from text. We need to understand the ratio in real datasets to decide how much inference work the system needs to do.

### U9: How brittle is the system to source-format changes?

If a customer changes how they use Slack, or a vendor changes their portal format, does the system gracefully degrade or catastrophically fail? Worth probing this with synthetic format perturbations.

## Anti-unknowns (questions we are deliberately not trying to answer yet)

These are real questions but not load-bearing for the next 90 days:

- **What's the right pricing?** Don't know, don't need to know. Design partner conversations will surface this.
- **What's the right go-to-market motion?** Same.
- **Will hyperscalers eventually build this themselves?** Maybe, but not in the next 12 months, and the answer doesn't change what we should build now.
- **Should we eventually serve defense markets?** Real question, but deferred until commercial validation.
- **What's the right team size and structure?** Premature; it's just me and Claude Code for now.

## How learning compounds

The unknowns above are not independent. Reducing U1 (cross-domain generalization) requires answering U4 (signal density per domain). Answering U2 (class-three contemporaneous detection) requires U6 (retrospective bias quantification). The dataset work and the detector work serve multiple unknowns simultaneously.

This is the right shape. We're not running independent experiments; we're building a coherent learning artifact where each piece informs the others. The experiment-log captures this as it happens.

## Definition of done for this phase

This exploration phase is complete when we can confidently state:

1. Whether the architecture generalizes across at least 4 program domains (yes/no with evidence).
2. Whether class-three contemporaneous detection works above a useful threshold (yes/no with calibration data).
3. Whether the cost-tier hierarchy delivers on its predicted economics (yes/no with measurements).
4. What the pitch is to a real design partner, with concrete examples drawn from public-dataset work.

These four answers determine whether we move from exploration to design-partner engagement, and what the framing for that engagement is.
