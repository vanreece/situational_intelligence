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
  direction-log.md       The user's voice: strategic guidance, decisions, redirections
  infrastructure.md      Compute resources (homelab models, API access)

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

.beads/                  Beads issue tracker state (Dolt-backed, JSONL-exported)
AGENTS.md                Bd-installed agent instructions (see CLAUDE.md for project-specific overrides)
```

## Working agreements with Claude Code

- **Bias toward the boring layer.** Resource conflict detection, dependency violation flagging, and constraint satisfaction over structured data is the floor. Build that confidently before reaching for sophisticated capability.
- **Cheap experiments, fast iteration.** Throw spaghetti at the wall with small models across broad cross-sections of data. Find the local maximum on quality before optimizing for cost or capability.
- **Per-component evals over end-to-end evals.** When something breaks, the failure should localize to a specific detector or synthesis step, not to "the system."
- **Hold-out splits along time boundaries.** For datasets with temporal structure, train/develop on earlier periods and validate on later periods. Random splits are misleading for this kind of work because the production regime is "predict what's forming, not what already happened."
- **Append to experiment-log.md after every meaningful run.** What was tried, what was observed, what surprised, what to try next. This is the durable artifact; the code is secondary.
- **Pre-register experiments before running them.** Each `experiment-log.md` entry is committed in two stages: the **Pre-registration** block (Setup, Prediction, Decision rule, Falsifiers) commits *before* the experiment runs; **Results** commit afterward. The git timestamp on the pre-reg commit is the receipt that we didn't move the goalposts. Wanting to skip the pre-reg block is the strongest signal that we're rationalizing — that's the experiment most worth pre-registering.
- **The direction log is the user's voice.** `docs/direction-log.md` captures strategic guidance, decisions, and redirections from the user. Read it for context, never edit/summarize/condense/move its contents, and don't fold it into other docs. When you want to surface analysis, use conversation or `experiment-log.md`.
- **Don't merge classification and extraction into one pass** even when the latest model could do both. The architectural separation is the moat.
- **Beads holds intent; markdown holds record.** `bd` (Beads) tracks candidate experiments, engineering prerequisites, and the dependency lattice between them — the *expanding wavefront* of work we know about. Pre-registrations, observations, surprises, conclusions, and the user's strategic direction stay in the markdown logs (`docs/experiment-log.md`, `docs/direction-log.md`, `docs/goals.md`). bd captures *what we might do and what depends on what*; markdown captures *what we found and what we believe*. Don't fold one into the other.
- **Pre-registration is its own bd issue, not just a status on the experiment issue.** Each experiment has a precursor `Pre-register: <experiment>` issue that closes when the pre-reg block is committed to `experiment-log.md`. The Run issue is blocked-by the Pre-register issue, so structurally it cannot become ready until the pre-reg lands. The closing note on the Pre-register issue carries the commit hash as the receipt — that's the structural enforcement of the two-commit pre-reg discipline.
- **Use `bd ready` at session start to surface the wavefront, but don't just pick "any" ready node.** The graph supports cost-aware prioritization: `bd dep tree <id>` shows upstream cost; `bd blocked` shows downstream impact. The right pick is usually a ready node whose closure unblocks the most downstream work, or whose unresolved upstream is cheap.
- **Idea-stage issues with under-specified inputs are first-class.** When an experiment surfaces a follow-up that depends on something we haven't built or decided yet, record both — the candidate experiment AND the unresolved prerequisite — as `idea`-status bd issues with `discovered-from` edges. The wavefront accumulates with provenance; staleness becomes a queryable triage signal rather than a buried bullet in `Next` sections.
- **Reconciling with bd-installed conventions.** The bd integration block at the bottom of this file (between `<!-- BEGIN BEADS INTEGRATION -->` markers) is bd-managed and may be regenerated. Where its prescriptions conflict with this project's discipline, the working agreements above win:
  - **`TaskCreate` is fine** for session-internal task tracking — it's ephemeral, orthogonal to bd's cross-session work. bd holds durable work; `TaskCreate` holds within-session organization.
  - **Auto memory at `~/.claude/projects/-home-vanreece-situational-intelligence/memory/` continues to apply** — these are cross-conversation user/project/reference facts, not work items, and don't fit bd's issue shape.
  - **Do not push to remote without explicit user instruction.** bd's mandatory-push rule is overridden by our general project discipline. Push when the user asks, not automatically.
- **Snapshot transient state at every control edge.** Whenever the conversation hits a pause point — waiting on the user, waiting on an external signal (homelab coming up, a long-running job, a model run), or about to hand off — write the transient state down before going idle. This protects against context being cleared or compacted mid-pause: a fresh session can resume cleanly from what's on disk. Concretely:
  - **Issue-scoped pauses:** append a `[paused YYYY-MM-DD] ...` note to the relevant bd issue with resume instructions and pointer commits. `bd update <id> --append-notes "..."`
  - **Cross-issue or non-issue state:** overwrite `docs/session-handoff.md` and commit it. The file is a single-page snapshot: what we just did, what's pending, the next concrete move, any environment quirks. It is *not* append-only — each pause overwrites.
  - **Don't duplicate state that's already durable.** Git commits, bd issue state, and memory files survive context clears already. Only capture the *transient* context (mental model in flight, mid-stream decisions, "we paused at step 3 of 6") that would otherwise live only in conversation history.
  - The trigger is event-based, not quantity-based. Don't try to estimate context usage — trigger on every "standing by" moment instead.

## Reading order for new sessions

1. This file (CLAUDE.md)
2. `bd ready` — the current wavefront of unblocked work; `bd blocked` for what's gated and on what
3. `docs/direction-log.md` — recent strategic guidance from the user (read; do not edit)
4. `docs/goals.md` — what we're trying to learn right now
5. `docs/experiment-log.md` — what was tried recently
6. Whatever specific doc is relevant to the current task

## Known unknowns

The honest list of things this project is set up to discover, not assume:

- Whether consequence-correlated detectors actually generalize across program domains, or whether each domain needs its own.
- Whether affective signal detection (reading between the lines) is reliable enough to act on, or whether it's interesting in demos but unreliable in production.
- Whether the class-three failure detector is buildable contemporaneously or only retrospectively.
- Whether public dataset retrospectives are too retrospectively-biased to train on (the GAO benefits from hindsight in ways that contemporaneous detection won't).
- Whether the architectural overhead pays off at single-vertical scale, or only when multiple verticals are running on shared substrate.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
