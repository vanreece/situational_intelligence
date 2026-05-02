# Session Handoff

> Per CLAUDE.md "Snapshot transient state at every control edge." This file is overwritten each pause; it captures only the transient mental-model state that wouldn't otherwise survive a fresh session. Durable state lives in git, bd, memory, and `docs/experiment-log.md`.

## Last updated: 2026-05-02 (after si-pfo close)

## Where we are

`schedule_change_announcement` on Cassandra dev@ 2014 has now been through **four** rounds of measurement:

1. `si-qhz` — initial run, F1=0.389. Surfaced rubric ambiguity as the dominant failure mode.
2. `si-bwo` — body-cap audit (8K → 60K). F1≈unchanged. Surfaced model anchoring on quoted material.
3. `si-s9y` + `si-fnw` — quote-depth sweep across {0,1,2,3,4,5,6,8,10,999}. F1 curve is rise-then-plateau: peak at depth=2 (F1=0.405), plateau at 0.31–0.33 from depth 3 onward.
4. **`si-pfo`** (just closed) — vLLM non-determinism at depth=2. F1 spread across 6 runs = **0.015** (5× smaller than the si-fnw depth=2-vs-plateau gap of 0.075). Depth=2 advantage is real signal, not a lucky roll. All 12 TPs are stable across all 6 runs; variance lives entirely in the FP set on borderline `[VOTE]` / "Release Schedule" subjects.

Detector still **NOT promoted** (F1=0.405 < 0.65 threshold; precision=0.343 < 0.70). Rubric work is the remaining lever.

## My recommended next move

**Pick up `si-d6m`** — sharpen the schedule_change_announcement rubric and re-pre-register. It's the highest-priority unblocked issue and now has nothing standing in its way.

### Concrete starting points for si-d6m (already attached as bd notes)

- **Use the 15 unstable messages from si-pfo as the rubric stress-test set.** They're listed in `results/evals/schedule_change_announcement-pfo-noise-floor/summary.json` under `unstable_messages`. Almost all are `[VOTE]` / `[VOTE CLOSED]` / "Proposed changes to C* Release Schedule" subjects. Any v2 rubric that doesn't cleanly classify all 15 hasn't sharpened the right thing.
- **Single-run scorecards are trustworthy at depth=2.** Noise floor is ±0.015; effects ≥0.04 are signal. No need for multi-run aggregation while iterating on rubric.
- **Trade-off to surface in the v2 pre-reg:** the lone-TP advantage at depth=2 (Jonathan Ellis "I plan to address this... after 3.0" message) rests on the model anchoring on *quoted Benedict text*, not Jonathan's actual reply. A rubric edit that instructs the model to ignore quoted lines (or to identify "new content first") will likely lose this TP. The depth=2 advantage shrinks toward the plateau if that change is made. Worth quantifying before committing the rubric direction.
- **Re-evaluate at zero inference cost:** si-d6m can re-label the existing 149 items against a v2 rubric and re-evaluate using the *same* run-0..run-5 prediction files. Only need to re-run inference if the *prompt* changes (which it should, per the trade-off above — but that decision is part of si-d6m's pre-reg).

## Open question for the next session to consider

The 2 unstable messages in the high-confidence bin `[0.9, 1.0)` are interesting outliers: high `p_positive` from the model, but still flip across runs. This is a small data point against treating logprobs as a stability proxy. Probably not worth a separate experiment, but worth noting in si-d6m's pre-reg in case it informs how to use confidence in downstream synthesis.

## Environment notes

- **Homelab is rock-solid right now.** All 5 si-pfo reruns took 255–256s each (0.4% wall-clock spread). Zero HTTP errors across 5 × 731 = 3655 inference calls.
- **Classifier is resumable** — relaunching the same `--out` path skips already-done ids.
- **Corpus path gotcha:** `--corpus-dir` needs to be `data/processed/apache/dev@cassandra.apache.org`, not the parent. The classifier's glob is non-recursive.
- **`python` is not on PATH; use `python3`** when invoking the modules from shell scripts.

## Git state

- 5 local commits ahead of `origin/main`: `92e71da`, `e18ca39`, `a5c57ad`, `d40e2a2`, `0707ce1`. **User said they'll handle pushes**.
- Two untracked files in the working tree (`-home-vanreece-situational-intelligence.tar.gz`, `situational_intelligence.zip`) — backups/exports, leaving them alone.
- Working tree is otherwise clean.

## bd state

- 6 ready issues (one less than last handoff — si-pfo closed).
- 0 in_progress, 0 blocked.
- si-d6m is now the top P2 ready item.

## Memory updates

- `local_temporal_context.md` updated with the si-pfo confirmation that the depth=2 winner is structurally stable (not stochastic) and the per-(detector, corpus) noise floor at depth=2 is F1 ±0.015.
