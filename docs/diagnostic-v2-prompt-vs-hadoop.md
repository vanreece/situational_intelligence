# Diagnostic: v2_elided prompt vs Hadoop common-dev@ 2014

Run identifier: si-2wh predictions (`hadoop-common-dev-2014-predictions-v2-elided.jsonl`)
Label set: `hadoop-common-dev-2014-labels-v2.jsonl` (17-message pool + 50 random_sample)
Confusion (this label set):
- Pool (17): TP=15, FP=2, FN=0, TN=0
- Random_sample (50): TP=0, FP=0, FN=2, TN=48

Pool was constructed by sampling cheap-tier model-positives, so by construction it has no negatives that the model already rejected — only ground-truth-confirming TPs and ground-truth-disconfirming FPs. The random_sample stratum is the more honest precision/recall estimator. The discussion below treats both strata together.

---

## 1. Per-FP analysis

### FP-1: `99B9A325-BBFE-46A4-B1EE-A90C654C9A5E@hortonworks.com` — "Re: Thinking ahead to 2.4" (Arun, 2014-02-18)

**Cheap-tier rationale:** "The author is announcing a change to the version target for planned work by creating a new version '2.5.0' and indicating that most things will now commit to that version, which represents a shift from previous version targets."

**Author's actual NEW content:**
> Forgot to add… Committers: I've created version "2.5.0" in jira with the expectation that most things will now commit to that version.

**Diagnosis: (b) vocabulary-fixable, with a (c) prompt-engineering tail.** This is a JIRA-bookkeeping idiom that doesn't exist in the same form on the Cassandra dev@ list. "Created version 'X' in JIRA" is purely administrative — it just makes the version selectable in JIRA's drop-down so contributors can tag tickets. It does not announce a date, shift a target, or change scope. The cheap-tier is anchoring on the phrase "most things will now commit to that version" and reading it as a substantive target shift, when in Hadoop convention the parent message has already announced 2.5 and this is the JIRA registrar following up.

**Proposed NEGATIVE clause (Hadoop-aware):**
> "JIRA bookkeeping notices — 'I've created version X in JIRA', 'JIRA version X.Y.Z is now available', 'target version set to X' on a single ticket — are administrative metadata changes, not schedule changes. The release exists in JIRA so contributors can tag work; the schedule is set elsewhere in the thread."

**Risk:** none significant for Cassandra precision; could very mildly suppress true positives that happen to phrase a real schedule change in JIRA-creation language, but those are rare and usually accompanied by a date.

### FP-2: `CAFiYk=quX_bnWgUKU8qfcHA6sqCa4Q+CSWL=9wgNgkEpHZ-Y1g@mail.gmail.com` — "Re: Next releases" (Arpit, 2014-01-07)

**Cheap-tier rationale:** "The author is explicitly stating that the target version has been set to 2.4.0, which represents a change to a previously-stated version target for the release, based on the new content provided in this message."

**Author's actual NEW content:**
> This merge to branch-2 is complete. The changes have been merged to branch-2 and target version set to 2.4.0 (r1556076).

**Diagnosis: (b) vocabulary-fixable, sharing a class with FP-1.** This is the same JIRA bookkeeping shape: "target version set to X" is the JIRA-field-update language used after a merge to record which release the change went into. It is the OPPOSITE of a schedule change — the work is already done; the field update is purely descriptive of what just happened. The cheap-tier reads "target version set to 2.4.0" as evidence of a target shift; in Hadoop convention it is shipping notification.

**Proposed NEGATIVE clause:** Same as FP-1 — the JIRA bookkeeping clause covers this exactly. Optional reinforcement: "Status updates that a merge has completed and a JIRA target-version field was updated to reflect the merge are post-hoc descriptive notices, not forward-looking schedule changes."

**Risk:** very low. "target version set to X" in Hadoop is ~entirely procedural; in Cassandra the phrase is rare to begin with.

**Class summary for FPs:** Both FPs are in the **JIRA-bookkeeping class** — Hadoop's release process makes heavy use of JIRA "target version" fields and per-version registration that the v2 rubric (Cassandra-shaped) doesn't acknowledge. This is a single rubric gap covered by one well-targeted NEGATIVE clause.

---

## 2. Per-FN analysis

### FN-1: `4E0B02FE-AEFC-4EF8-8AA6-F66C111E8DDA@hortonworks.com` — "Re: Thinking ahead to hadoop-2.7" (Arun, 2014-12-03)

**Cheap-tier rationale:** "This message is proposing a potential timeline for a future release (hadoop-2.8) but does not announce or imply a change to a previously-stated date or version target for a release, milestone, or planned work."

**Author's actual NEW content (full body, depth-0):**
> Sangjin/Karthik,
>  How about planning on hadoop-2.8 by late Jan? Thoughts?

The thread context: this is a reply in "Thinking ahead to hadoop-2.7", with parent messages discussing 2.7's timing. Arun is proposing 2.8 by late January — which is exactly the "Setting a new target date when a previous expectation existed" POSITIVE bullet in v2.

**Diagnosis: (d) prompt-engineering-fixable, with a (b) vocabulary-fixable tail.** This is striking: the message's NEW content is ~15 words, almost a perfect match to a v2 POSITIVE example. The cheap-tier explicitly identified that the message proposes a timeline ("a potential timeline for a future release") but then concluded that a "potential timeline" is not a "change to a previously-stated date or version target."

The model's reasoning collapses two distinct cases the rubric needs to disambiguate:
- "Setting an initial target with no prior expectation" → NEGATIVE
- "Setting a new target date when a previous expectation existed" → POSITIVE

In a thread titled "Thinking ahead to hadoop-2.7", a 2.8 proposal is by definition extending the cadence — there IS a prior expectation (the 2.7 thread). But the cheap-tier with the parent message elided to `[QUOTED]` cannot see that prior expectation, and falls back to its rule for "no prior expectation = NEG."

This is partly capability-ceiling (the model is reasoning soundly given what it sees), but more importantly it's a **rubric-ergonomics issue**: the rubric trusts the model to know that a thread titled "Thinking ahead to X" (a known Hadoop convention) implies a forward-looking schedule conversation where any new version target IS a schedule change. The Cassandra-shaped rubric never had to make that assumption explicit.

**Proposed POSITIVE clarification:** "Proposals of a new release version with a date — 'hadoop-X by late Jan?', 'release X by Q3' — are schedule announcements when the message is part of an ongoing release-cadence discussion, even when phrased as a tentative question."

**Alternative framing (substrate-fixable, would close the gap differently):** Surface the parent message thesis or the thread's earliest message in the user template. The model would then see the prior expectation directly. The v2_elided_tagged variant attempted something adjacent but with version-state, not thread-thesis.

### FN-2: `FA27F268-9AD2-4C96-9669-FAEBD26857F5@hortonworks.com` — "Re: Logistics for releasing 2.4" (Arun, 2014-01-23)

**Cheap-tier rationale:** "The message discusses potential reorganization of release strategy but does not announce, propose, or imply a substantive schedule change such as a new date, version target shift, or release cadence proposal. The author is discussing options for handling an existing release process rather than changing any timeline or version targets."

**Author's actual NEW content:**
> Agree 2.3 is now very stale.
> So, as I understand, your motivation is to get HDFS-2832 & HDFS-4949 out, correct?
> If so, that could be a better option - I can abandon the 2.3rc, and then release current branch-2 as 2.3. Would that be better?

**Diagnosis: (a) rubric-fixable, with a (d) prompt-engineering tail.** This is a substantive version-target shift with two concrete moving parts:
1. Abandon the existing 2.3rc (a vote-in-flight release would be terminated).
2. Re-release current branch-2 as 2.3 (the version label is being remapped to a different code line, with two specific HDFS features as the new contents).

The cheap-tier reads this as "discussing options" and dismisses it. The interrogative framing ("Would that be better?") and the conditional ("If so, that could be a better option") are the trap — the v2 rubric uses "proposes/announces/implies" and the model is treating the question form as merely speculative.

The v2 rubric does say "proposes" generally, but it does not include a clause covering Hadoop-shaped scope reshapes — "abandon the X rc, release current branch-N as X" is a *version semantics change*: the same version label X is being attached to substantially different code. The Cassandra-shaped rubric has "scratch the current 2.3 branch and make … the new 2.3" implicitly captured under the existing TP-15 (CAGB5D2aZtWww...) example because that one was overt in a single TP, but the rubric text doesn't explicitly call this class out.

**Proposed POSITIVE clarification:** "Substantive scope or branch reshapes that re-define which code is shipped under a given version label — 'abandon the X rc and release current branch-N as X', 're-target version X to point at code path B', 'scratch current branch-X and use … as the new X' — are schedule changes (version semantics shifts), even when phrased as questions or conditionals to elicit agreement."

**Risk:** moderate. This clause could accidentally promote some pure technical-rebase discussions to POSITIVE if they use similar verbs ("rebase 2.3 on …"). The mitigation is the requirement that the version label and the released artifact identity are both touched — pure technical rebases of an unreleased branch don't carry that.

**Class summary for FNs:** Both FNs are decision-question-shaped messages where the cheap-tier dismisses interrogative or conditional framing as "discussion" rather than "proposal." The v2 rubric's POSITIVE list uses "proposes" but does not explicitly authorize the model to treat questions like "How about X by Q3?" or "Would that be better?" as proposals. This is a single rubric/prompt-engineering gap covered by clarifying that question-shaped proposals count.

---

## 3. Cross-corpus rubric gap analysis

The v2 rubric is a Cassandra-shaped instrument. Reading it against this Hadoop sample exposes three specific gaps:

### 3.1 Hadoop conventions the v2 rubric doesn't acknowledge

- **"Thinking ahead to hadoop-X.Y"** — recurring subject-line idiom (4 of the 15 TPs are in such threads, plus FN-1). It is the canonical Hadoop convention for opening release-planning discussions: anything that proposes a date or scope inside this thread is a schedule announcement, even when tentative. The rubric never mentions this convention (and shouldn't pretend to know it by name), but the model's lack of awareness creates the FN-1 failure mode.
- **"Logistics for releasing X"** — a Hadoop convention for thread that openly discusses the mechanics of a release. Substantive proposals here (FN-2 lives here, as do TP CAGB5D2YdXR8 and TP CAGB5D2aZtWww) often take question form: "How do we feel about cutting branch-2?", "Would that be better?", "Should we …?". The Cassandra rubric doesn't instruct the model that question-form proposals are still proposals.
- **"Re-swizzle X.Y" / "abandon the rc, release branch-N as X"** — distinctive Hadoop scope-reshape pattern. The TP-15 includes a clean example (`CAGB5D2aZtWww`) and the FN includes a near-twin (`FA27F268`); the model gets one and misses the other, suggesting borderline calibration.
- **JIRA "target version" / "created version X in JIRA" bookkeeping** — Hadoop-specific metadata-update idioms that read as schedule-shifts to a Cassandra-trained rubric. Both FPs live here.
- **"branch cut" / "cut branch-N"** — high-frequency Hadoop verb for the act of forking a release branch. The cheap-tier handles this well in TPs (it correctly fires on "I plan to cut the branch early next week"), so this is not a gap, just a vocabulary note for the rubric author.
- **"rc3?" / "+1 for another rc"** — Hadoop's vote-failure-reroll language matches Cassandra's; the v2 rubric's existing NEGATIVE clause for vote-failure rerolls handles these correctly (the random_sample TN `CAPn_vTv...` is correctly classified).

### 3.2 Cassandra-specific connotations in the POSITIVE clauses

The word "re-roll" does not appear in the v2 POSITIVE list (it appears in NEGATIVE). The v2 POSITIVE clause "Re-rolls that introduce a NEW version not previously planned (e.g., 'let's do a 1.2.18' when 1.2.17 was the last announced)" is Cassandra-flavored, and Hadoop doesn't use "re-roll" the same way — Hadoop uses "another rc" and "abandon the rc and re-release". This isn't actively harmful (the negative direction is preserved), but the *positive* example for that clause uses a Cassandra-version-string and a Cassandra-tone, which gives a slight Cassandra-shaping that the model picks up. The TPs in this sample don't fall through this clause specifically, so it's not the dominant issue.

The other POSITIVE clauses (explicit date changes, version target shifts, release cadence proposals, acknowledgments of unmet timelines, setting a new target when a previous expectation existed) all fire well on Hadoop, evidenced by the high TP rate in the pool.

### 3.3 Missing Hadoop-specific NEGATIVE categories

The v2 NEGATIVE list does not include:

- **JIRA bookkeeping** — FP-1 and FP-2's class. Single biggest gap.
- **Per-ticket "target version" field updates** — adjacent to JIRA bookkeeping. Could be folded into the same clause.
- **Post-hoc merge announcements** ("merged to branch-2; target version set to X") — also adjacent to JIRA bookkeeping; the relevant signal is "describes work already done" not "describes future work."

The existing NEGATIVE clauses (vote-failure rerolls, vote-period adjustments, +1/-1 votes, on-track status, initial schedule with no prior expectation, pure technical) all transfer cleanly.

---

## 4. Hypothesis fixes (what to consider, NOT what to apply)

### Hypothesis fix 1: Add a JIRA-bookkeeping NEGATIVE clause

**Edit:** Append to the NEGATIVE list in v2:

> "JIRA bookkeeping notices — 'I've created version X in JIRA', 'target version set to X (rNNNN)', 'merged to branch-N and target version set to X' — are administrative metadata changes, not schedule changes. They describe work already done or make a version selectable in the issue tracker; the schedule decision happens elsewhere in the thread."

**Predicted effect:** addresses the JIRA-bookkeeping FP class (FP-1, FP-2). Should cleanly drop precision-failures on procedural metadata language without affecting TPs (no TP in this sample uses JIRA-creation or target-version-set framing as its primary evidence).

**Risk:** very low. The phrasing is specific to administrative idiom; non-administrative proposals that incidentally mention JIRA target versions (rare) would still match POSITIVE clauses. Could very mildly under-fire on a Cassandra TP if Cassandra ever had a "created version 4.0 in JIRA = ipso facto a schedule announcement" message, but that pattern was not present in the v2 OpusLabel pool.

**Test:** v3a vs v2_elided on Hadoop labeled pool (target: drop both Hadoop FPs without losing TPs); also run on Cassandra labeled pool (target: no regression on existing Cassandra metrics).

### Hypothesis fix 2: Authorize question-shaped proposals

**Edit:** Append to the POSITIVE list in v2:

> "Question-form or conditional-form proposals — 'How about hadoop-X by late Jan?', 'Should we move to monthly cadence?', 'Would it be better to abandon the rc and re-release as X?' — are still proposals of schedule changes when the question is the author's substantive suggestion (not just clarifying what someone else said). Tentative phrasing ('thoughts?', 'would that be better?') does not downgrade a substantive proposal to discussion."

**Predicted effect:** addresses FN-1 and FN-2 directly. Both are interrogative or conditional substantive proposals that the cheap-tier is dismissing as "discussion."

**Risk:** moderate. Could mildly inflate FPs on messages that ask clarifying questions about someone else's proposal — e.g., "Should we delay 2.6?" asked rhetorically as a discussion-opener rather than a proposal. Mitigation: the clause explicitly says "the author's substantive suggestion (not just clarifying what someone else said)." The model has to make that judgment, and it's well within capability.

**Test:** v3b vs v2_elided on Hadoop labeled pool (target: recover both FNs without inflating FPs); also run on Cassandra labeled pool (target: ≤1 new FP on prior TNs).

### Hypothesis fix 3: Surface "thread context implies prior expectation"

**Edit:** Append a clarifying sentence to the existing v2 POSITIVE bullet "Setting a new target date when a previous expectation existed":

> "A previous expectation can be implicit in the thread title or in the existence of the conversation — e.g., a thread titled 'Thinking ahead to hadoop-X' or 'Logistics for releasing X' establishes an ongoing release-planning expectation, so any new version-and-date proposal in that thread counts as setting a new target where a prior expectation existed."

**Predicted effect:** addresses FN-1 specifically, which is the failure mode where the cheap-tier sees a tentative "How about hadoop-2.8 by late Jan?" with the parent thread elided to `[QUOTED]` and concludes "no prior expectation = initial target = NEG." Subject-line awareness gives it a free disambiguator.

**Risk:** low-to-moderate. Could mildly inflate POSITIVE on threads where the subject is generic ("Re: 2.4") and a comment isn't actually a proposal. Mitigation: the rubric still requires a *new version-and-date proposal*, not any comment, in such threads. Additionally, fix 3 is partially redundant with fix 2 (both address FN-1), so they should be tested separately and possibly only one applied.

**Test:** v3c vs v2_elided. Also test v3b+v3c combined.

### Hypothesis fix 4: Add a version-semantics-shift POSITIVE example

**Edit:** Append a new POSITIVE bullet (or extend the existing "Version target shifts" bullet):

> "Substantive remappings of which code ships under a version label — 'abandon the X rc and release current branch-N as X', 'scratch the current X branch and use … as the new X', 'drop the 2.6 release and pivot to a 3.0-alpha' — are schedule changes (version semantics shifts), regardless of whether the proposal is in declarative, conditional, or interrogative form."

**Predicted effect:** primarily addresses FN-2 (`FA27F268`) and reinforces the correct behavior on `F27FB0BD` (TP, "Drop the 2.6.0 release …") and `CAGB5D2aZtWww` (TP, "scratch the current 2.3 branch and make …").

**Risk:** low-to-moderate. Largely overlaps with the existing "Version target shifts" POSITIVE bullet, so it's mostly clarification rather than expansion. Could mildly fire on technical rebase discussions ("we should rebase X on Y") — mitigation: the clause is specific to version-LABEL remapping, not branch rebase.

**Test:** v3d vs v2_elided. Also test v3a+v3d (the combined precision+recall fix).

---

## 5. Bottom line for the strategic call

**Recommendation: (b) Apply 1-2 narrow rubric fixes BEFORE si-03o, with the specific minimal package being fix 1 (JIRA-bookkeeping NEGATIVE) plus fix 2 (question-form proposals POSITIVE).**

The Hadoop failures cluster cleanly into two classes that each map to a single-clause rubric edit with low risk and a clear predicted effect: the JIRA-bookkeeping FP class is a real Cassandra-vs-Hadoop vocabulary gap that the cheap-tier rubric has no way to know about, and the interrogative-proposal FN class is a small but specific rubric ergonomics issue. Both fixes are ~2 sentences, fully-pre-registrable, and would make si-03o's frontier-on-Hadoop transfer test more informative — without the fixes, si-03o will likely show "frontier model handles JIRA bookkeeping correctly because it has prior knowledge of Apache JIRA conventions" and we'll be unable to distinguish capability-ceiling from rubric-ceiling. With the fixes, si-03o's headroom over the cheap-tier will more cleanly reflect capability gain.

The third and fourth hypothesis fixes (thread-context POSITIVE and version-semantics-shift POSITIVE) are weaker calls — they're partial overlaps and adding all four risks losing the discipline of single-thesis rubric edits. Defer those unless fix 2 fails to recover both FNs.

---

## 6. Non-rubric infrastructure findings

- **Confidence is bimodal.** All 15 TPs report `p_positive=0.999`; both FNs report `p_positive=0.001`; both FPs report `p_positive=0.999`. The cheap-tier under v2_elided is essentially never uncertain. This means we cannot use a probability threshold to surface candidates for escalation — the model's calibration is binary. For si-03o (escalation experiment), the routing signal cannot be the cheap-tier's confidence; it has to be something else (e.g., ALL cheap-tier negatives in random_sample with thread-subject "Thinking ahead to …" or "Logistics for releasing …" go to the frontier model regardless of confidence).
- **Sender concentration.** The pool's positives are dominated by Arun Murthy (Hortonworks, 9 of 17) and Andrew Wang (Cloudera, 6 of 17). Both FNs are also Arun Murthy. This is consistent with these being the two Hadoop release managers in 2014 and is not a model bias — it's a corpus property. But it means the labeled pool may be over-fit to Hortonworks/Cloudera release-manager voice; transfer to other Apache projects should not be assumed without re-labeling.
- **Subject-line as a strong feature.** "Thinking ahead to hadoop-X.Y" / "Logistics for releasing X" / "Re-swizzle X" / "[VOTE] Release …" are the four high-signal subject patterns; together they cover ~all the pool TPs and most of the random_sample FNs. A pre-screen filter on subject lines would meaningfully reduce the cheap-tier's candidate pool for the frontier model, independent of any rubric work. Worth filing as a future experiment.
- **Quoted-text discipline holds.** Every TP's evidence_quote is from the author's NEW content (verified manually for all 15). The CRITICAL quoted-text rule is doing what it was added to do; v2_elided is not the failure mode.
- **Body-length and complexity are not the failure axis.** FN-1's body is 15 words and the model fails. FN-2's body is ~60 words and the model fails. Both FPs have ~25-word author-content. The TPs span 15-450 words. This is not a "the model can't handle long messages" failure — it's a rubric-coverage and rubric-ergonomics failure.
