# Antigoals

This document captures what this project is *not* trying to be. Antigoals are at least as important as goals — they're how we resist the seductive pull of expanding scope, polishing prematurely, and confusing related-but-different problems with the actual one.

When something feels tempting to add, check it against this list first.

## Architectural antigoals

### Not a general-purpose AI assistant

The system has narrow, well-defined responsibilities: ingest operational signal, classify it, extract structure, synthesize judgment, present to specific operators. It does not chat about arbitrary topics, write marketing copy, debug code, or do anything else outside that pipeline. When tempted to make it more general, remember: generality without specific user feedback produces tools that do many things badly.

### Not a platform (yet)

The architecture is platform-shaped because that's the right architecture, but we are not productizing the platform. We ship vertical products on top of the substrate. Two verticals in production on the same substrate is when we earn the right to talk about platform; one vertical and a generalization claim is just a pitch deck.

**The discipline:** when designing a component, build it as if it were vertical-specific. If it turns out to generalize, that's a happy discovery later. Never assume it generalizes upfront.

### Not a dependency graph manager for agents

Beads exists. Beads is good. We are not building Beads. The persistence model that fits exploration work is logs, not graphs. The persistence model that fits operational work is continuously-reconstructed dependency graphs from heterogeneous sources — a different problem from what Beads solves. Don't let the structural similarity confuse the use cases.

### Not a chatbot UI for project data

The temptation: "wire up a chat interface where the user can ask anything about the program." This is a worse product than an opinionated briefing. Chat interfaces require the user to know what to ask. The whole value proposition is *the system tells you what you should be paying attention to that you didn't know to ask*. A chat surface might be a future feature, but it is not the headline.

### Not RAG over project documents

The temptation: dump all documents into a vector store, retrieve relevant chunks per query, pass to LLM. This is the lazy default and it produces shallow results. The architecture commits to typed extraction with provenance, structured intermediate state, and composable detectors. RAG is a backstop for the on-demand Q&A surface; it is not the substrate.

## Product antigoals

### Not a productivity tool

The pitch is not "save your TPMs time." That pitch gets priced like SaaS. The pitch is "prevent the class of program failures where information existed but didn't propagate to the decision-maker." That pitch gets priced like risk mitigation. The framing is load-bearing.

### Not a replacement for senior judgment

The system surfaces, flags, and recommends. Humans decide. Every output is a candidate for the operator to act on, accept, or reject. The system never says "this is the answer" — it says "here's what I think you should know, here's why, here's the evidence." If we ever build something that decides on behalf of operators, that's a different product and a different conversation.

### Not a dashboard

Dashboards are perpetually-on and perpetually-ignored. The artifact is briefings — things the operator reads with a beginning and an end, that take a position on what matters today. A dashboard might be a secondary interface, but the primary artifact is the briefing.

### Not a status aggregator

The temptation: pull from all sources and show the unified view. This is what existing tools mostly do, and the reason the 160-person sync exists is that the unified view doesn't tell anyone what to do about it. The value is in the synthesis layer, not the aggregation layer. Aggregation is table stakes; synthesis is the product.

### Not "AI summaries"

The temptation: have a capable model read everything and produce a summary. This works in demos and degrades in production because (a) summaries lose the structured information that makes follow-up queries cheap, (b) capable models given long contexts produce confidently-wrong sophisticated summaries, (c) summaries don't accumulate as evals. The composed-pipeline approach is harder to build and dramatically more reliable in production.

## Process antigoals

### Not a research project

The point is not to publish papers about LLM systems (though papers may be a side effect). The point is to learn enough to build a real product for real users. Every experiment serves a learning unknown that maps to a product decision.

### Not a tour of the literature

The temptation when starting a new project is to read everything first. This is a productive-feeling form of avoidance. We will read what's directly load-bearing for what we're building this week, and use parallel external work (Beads, Dolt, etc.) as calibration rather than curriculum.

### Not a complete dataset survey before building

The temptation: ingest all 8 datasets before running any detectors. Don't. Pick 1-2 datasets, build the harness against them, run experiments, learn what works, then add datasets. The breadth across 8 datasets is for stress-testing detectors and validating generalization — not for proving comprehensiveness.

### Not perfect before shipping

The exploration phase is complete when we can answer the four questions in `goals.md` confidently. It is not complete when the system is "polished" or "ready." A scrappy answer to those four questions is more valuable than a beautiful system that doesn't answer them.

### Not a substitute for talking to humans

We can learn a lot from public datasets. We cannot learn whether the briefing artifact lands with a real operator. The exploration work prepares for the conversation with a real design partner; it does not replace it. Don't let the technical work become an excuse to avoid that conversation.

## Scope antigoals

### Not all program types

The eight datasets are deliberately bounded: defense acquisition, public infrastructure, software-coordinated-at-scale, and industrial/operational with classical PM discipline. We are *not* trying to cover healthcare megaprojects, supply chain at retail scale, financial trading desks, or other complex coordination domains. They might be relevant later. They are out of scope now.

### Not all signal types

We focus on: vendor coordination signals, schedule slip language, risk escalation patterns, latent-knowledge proximity, affective register shifts, structural constraints (resource conflicts, dependency violations). We do *not* try to detect: emotional health of team members, code quality, security threats, market signals, or compliance violations. Each of those is a real and valuable detector category, and each is outside our scope right now.

### Not all output formats

We produce: daily briefings (markdown), structured detector outputs (JSON), calibration scorecards (per-detector metrics). We do *not* produce: native integrations with all PM tools, a polished web UI, mobile apps, email notifications, Slack bots. Some of these are obvious eventual-features; none of them are exploration-phase work.

### Not all model providers

We build against Anthropic models (Claude family) for capable-tier work and against open-weight models (Llama, Qwen, smaller specialized models) for narrow-tier work. We are not building a model-agnostic abstraction layer. The architecture is naturally model-agnostic at the component level; the production system can be migrated if needed; but the exploration phase commits to specific models to avoid wasting time on portability.

## When in doubt

If a feature, component, dataset, or capability isn't directly load-bearing for one of the four primary unknowns in `goals.md`, it's probably an antigoal for the current phase. The default answer to "should we add X" is "no, unless it answers a specific question we're already trying to answer."

This is not a permanent posture. It's the right posture for the exploration phase, when scope discipline is the difference between learning something specific and producing a beautiful blob that doesn't answer anything.
