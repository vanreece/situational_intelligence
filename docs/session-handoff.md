# Session Handoff

> Per CLAUDE.md "Snapshot transient state at every control edge." This file is overwritten each pause; it captures only the transient mental-model state that wouldn't otherwise survive a fresh session. Durable state lives in git, bd, memory, and `docs/experiment-log.md`.

## Last updated: 2026-05-02 (handoff for context clear)

## Where we are

The first detector (`schedule_change_announcement` on Cassandra dev@ 2014) has gone through three rounds of measurement:

1. **`si-qhz`** — initial run, F1=0.389 against my strict labels. Surfaced rubric ambiguity as the dominant failure mode.
2. **`si-bwo`** — body-cap audit (8K → 60K). F1≈unchanged. Surfaced that the model anchors on whatever quoted material is in front of it.
3. **`si-s9y`** + **`si-fnw`** — quote-depth sweep across {0,1,2,3,4,5,6,8,10,999}. F1 curve is rise-then-plateau: 0.13 → 0.24 → 0.405 (depth=2 winner) → flat at 0.31–0.33 from depth 3 onward.

Detector still NOT promoted (F1 0.405 < 0.65 threshold).

## My recommended next move (with reasoning that's not in bd)

**Pick up `si-pfo` before `si-d6m`**, even though si-d6m is P2 and si-pfo is P3.

The reason isn't in the issue priorities: si-pfo (quantify vLLM non-determinism) **blocks confident interpretation of any future scorecard differences**. We've already seen ~17 prediction differences between supposedly-identical depth=999 runs (temperature=0). The depth=2 advantage in `si-fnw` is 0.075 above the plateau, which is more than one suspected noise floor (~±0.04) but less than two. Without quantifying the noise floor, we can't tell signal from noise on small F1 movements — and rubric sharpening (si-d6m) is going to produce a series of small F1 movements.

Concrete approach for si-pfo: run the same 731 messages through the classifier 5 times at depth=2, measure cross-run prediction agreement and F1 spread. ~20 minutes on the homelab. Output: a calibrated noise floor (e.g., "F1 ±0.04 is within run-to-run noise"). Then si-d6m's measurements have meaningful confidence intervals.

After si-pfo, proceed with si-d6m at depth=2.

## Open question I noted in the si-fnw Results that's worth investigating

**Which lone TP is unique to depth=2?** All depths 3–999 hit 11 TPs; depth=2 hits 12. That single item is the entire F1 advantage. Is it a robust pattern (some specific message format that benefits from exactly the parent + grandparent envelope) or a noise quirk? Cheap diagnostic: diff the predictions between depth=2 and depth=3 over the labeled pool, find the one item that flips, look at its body. Fits naturally into si-pfo or as a quick si-d6m precursor.

## Environment notes

- **Homelab can go down** (it did once during this session). The classifier is resumable — relaunching the same `--out` path skips already-done ids.
- **vLLM occasionally returns HTTP 400 on individual requests** even for normal-sized inputs. Aggregate error rate ~0.04% across this session. Ignore unless it concentrates on specific message types.

## Git state

- 3 local commits ahead of `origin/main` (`d40e2a2`, `0707ce1`, `447b83f`). Push when convenient; not blocking.
- Two untracked files in the working tree (`-home-vanreece-situational-intelligence.tar.gz`, `situational_intelligence.zip`) — appear to be backups/exports, leaving them alone.
- Working tree is otherwise clean.

## bd state

- 7 ready issues, 0 in_progress, no blocked.
- All recent work closed cleanly with receipt commit hashes in close notes.
- See `bd ready` for the current wavefront.
