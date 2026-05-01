# Project: Situational Intelligence Substrate

## What this project is

An exploration toward a system that surfaces **situational intelligence** — the right context, in the right form, to the right human, at the moment they need to make a decision — for senior operators running complex multi-vendor programs.

This repo is the exploratory phase. The goal is **not** to build the production system yet. The goal is to understand the problem space empirically by ingesting public datasets, building lightweight detector and synthesis pipelines against them, and learning what works before committing to a product shape.

## What I'm trying to learn (in priority order)

1. **What signals are reliably extractable from messy heterogeneous program data using composed-LLM systems?** Especially: vendor silence, schedule slip language, risk escalation framing, affective register shifts, latent-knowledge proximity (who has touched what circumstances).
2. **Which signals correlate with downstream outcomes when evaluated against ground truth retrospectives?** Use GAO reports, NAO reports, aerospace post-mortems, and similar as outcome anchors.
3. **What's the minimum viable detector architecture that produces useful output across multiple program domains?** Test for generalization across at least 4-6 datasets covering different program types.
4. **Where are the class-three failures** — situations where context existed in the system but didn't propagate to the decision-maker — and can they be detected contemporaneously, not just retrospectively?

## Architectural commitments

These are not implementation details — they're the discipline that makes the system worth building. Read `docs/architecture.md` for the full reasoning.

- **Single-thesis LLM passes only.** No multi-objective prompts. Each LLM call does one thing, has structured input, produces structured output, and is independently evaluable.
- **Binary-per-category classifiers, not multi-class.** Each detector asks "is this X, yes or no" independently. Categories don't compete; the system grows additively.
- **Cost-tier hierarchy.** Capable models design schemas and synthesize over narrow-model outputs. Narrow models do high-volume mechanical classification and extraction. Each layer uses the model whose capability matches the latitude the task allows.
- **Structured intermediate state, never prose blobs.** Detector outputs are typed JSON. Dependency graphs are queryable structures. The LLM queries structured state through tools rather than re-parsing markdown each session.
- **Provenance is first-class.** Every claim the system makes traces to specific evidence with timestamps. Confidence intervals are reported and calibrated against outcomes.
- **Discovery and production modes are separate.** Production runs known detectors fast. Discovery samples the "matched nothing" bucket with heavier models to find patterns worth promoting to new detectors.
- **Calibration tracking from day one.** Every prediction is logged with provenance so its eventual ground-truth comparison is a query, not a custom logging project.

## What this project is NOT

See `docs/antigoals.md` for the full list. The most important ones:

- **Not a productivity tool.** Time savings is a side effect, not the value prop.
- **Not a generic LLM platform.** Domain-agnostic substrate is built as a *consequence* of solving specific verticals well, not as a primary product.
- **Not a replacement for senior judgment.** The system amplifies senior operators by removing information chase work; it does not make decisions.
- **Not a dashboard.** Dashboards are perpetually-on and perpetually-ignored. The artifact is opinionated briefings that take positions.
- **Not trying to be exhaustive.** Iteratively better than the current state (Smartsheets + 160-person sync) is the floor. Perfect is the enemy of shipping.

## Repository layout

```
docs/                    Design documents, read these first
  architecture.md        The architectural thesis in detail
  goals.md               What we're trying to learn, organized
  antigoals.md           What this project is NOT
  datasets.md            Public datasets and what each is good for
  detector-catalog.md    Running list of detector ideas with status
  experiment-log.md      Append-only log of what was tried and what was learned

src/                     Code (to be created)
  harvest/               Per-source data ingestion
  classify/              Binary-per-category classifiers
  extract/               Single-thesis extraction passes
  synthesize/            Capable-model synthesis layer
  evaluate/              Calibration tracking and per-component evals

data/                    Datasets (gitignored; see datasets.md for download instructions)
  raw/                   As-acquired
  processed/             After parsing/normalization

results/                 Outputs from experiments
  briefings/             Generated briefings against datasets
  detector-runs/         Per-detector outputs with provenance
  evals/                 Calibration scorecards
```

## Working agreements with Claude Code

- **Bias toward the boring layer.** Resource conflict detection, dependency violation flagging, and constraint satisfaction over structured data is the floor. Build that confidently before reaching for sophisticated capability.
- **Cheap experiments, fast iteration.** Throw spaghetti at the wall with small models across broad cross-sections of data. Find the local maximum on quality before optimizing for cost or capability.
- **Per-component evals over end-to-end evals.** When something breaks, the failure should localize to a specific detector or synthesis step, not to "the system."
- **Hold-out splits along time boundaries.** For datasets with temporal structure, train/develop on earlier periods and validate on later periods. Random splits are misleading for this kind of work because the production regime is "predict what's forming, not what already happened."
- **Append to experiment-log.md after every meaningful run.** What was tried, what was observed, what surprised, what to try next. This is the durable artifact; the code is secondary.
- **Don't merge classification and extraction into one pass** even when the latest model could do both. The architectural separation is the moat.
- **No cargo-cult dependency graphs.** Beads is great for coding-agent workflows where the plan is durable. Exploration work is OODA-shaped: the plan is mutable, the observations are durable. Use logs, not graphs, until a graph earns its place.

## Reading order for new sessions

1. This file (CLAUDE.md)
2. `docs/goals.md` — what we're trying to learn right now
3. `docs/experiment-log.md` — what was tried recently
4. Whatever specific doc is relevant to the current task

## Known unknowns

The honest list of things this project is set up to discover, not assume:

- Whether consequence-correlated detectors actually generalize across program domains, or whether each domain needs its own.
- Whether affective signal detection (reading between the lines) is reliable enough to act on, or whether it's interesting in demos but unreliable in production.
- Whether the class-three failure detector is buildable contemporaneously or only retrospectively.
- Whether public dataset retrospectives are too retrospectively-biased to train on (the GAO benefits from hindsight in ways that contemporaneous detection won't).
- Whether the architectural overhead pays off at single-vertical scale, or only when multiple verticals are running on shared substrate.
