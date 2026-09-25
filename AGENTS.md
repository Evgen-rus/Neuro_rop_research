# AGENTS.md — NeuroROP Research

## Purpose

Offline research workspace for discovering repeatable semantic patterns that distinguish WON and LOST sales deals.

Current controlled dataset:
- manager: Пахомов
- 12 WON
- 11 LOST
- 23 deals total
- dataset path: `./dataset`

Current stage: **feature discovery only**.

Do not perform final validation, Jev integration, production changes, CRM access, or model training.

## Hard boundaries

1. Treat `./dataset` as immutable input.
2. Do not edit, rename, delete, normalize in place, or rewrite dataset files.
3. Do not access Bitrix, production databases, production repositories, APIs, `.env`, secrets, raw CRM staging, audio, or external services.
4. Do not run FULL/MINI production analysis.
5. Write all outputs only under `./research_outputs/`.
6. If an input is missing or malformed, record the issue; do not repair the source dataset.

## Data contract

Expected structure:

```text
dataset/
├── manifest.json
├── summary.json
├── build_quality.json
└── deals/<deal_id>/
    ├── neutral.json
    └── clean_timeline.jsonl
```

- `manifest.json` contains true outcome labels (`WON` / `LOST`).
- `clean_timeline.jsonl` is the only semantic timeline to analyze.
- `neutral.json` contains neutral metadata.
- Do not reconstruct outcome from anything outside `manifest.json`.

## Orchestration

Follow the same model-routing principles as Neuro_rop_practice:

- **Primary agent is always the current agent selected by the user in the thread.**
- Do not create a separate Sol/orchestrator/lead agent.
- In Codex, use **Luna workers** for bounded heavy analysis.
- Prefer **Luna Max** for deep semantic analysis of deal timelines.
- Luna Low is only for simple reading/checking/routine work and is not needed unless clearly useful.
- `code_mapper` is not needed for this research unless code mapping becomes relevant.
- Workers do not delegate further.
- By default use up to 2 workers concurrently; up to 3 is allowed only for independent workstreams and real acceleration.
- The primary agent integrates results, resolves conflicts, and performs final acceptance.
- Do not hardcode a concrete Luna model ID if the current Codex environment exposes routing by worker class/reasoning profile instead.

## Context efficiency

Primary should avoid reading all 23 raw timelines.

Primary should:
1. read lightweight metadata;
2. build balanced shards;
3. delegate raw-timeline analysis to Luna Max workers;
4. receive compact structured handoffs;
5. synthesize results;
6. inspect raw deals only for disputed evidence if necessary.

Workers should receive fresh context when available and only the files needed for their shard.

Read large `clean_timeline.jsonl` files selectively, only as needed for the current shard. Do not reread a deal's entire timeline without a reason. For disputed evidence, workers must return the exact `deal_id` and the most precise available event identifier: timestamp, `event_type`, `activity_id`/`message_id`/`task_id`, or another event ID. The primary checks only the corresponding event or section, not the whole timeline.

Do not send chain-of-thought, full transcripts, or huge logs back to primary.

Research handoff format:

```text
FINDINGS: main observations
CANDIDATES: candidate features
EVIDENCE: deal IDs + timestamps + short paraphrases
COUNTEREXAMPLES: contradictions / exceptions
CONFOUNDS: likely alternative explanations
RISKS: leakage / ambiguity / weak support
FILES: outputs written
```

## Research principle

We are looking for **observable pre-outcome semantic features**, not retrospective explanations.

Good examples:
- customer explicitly compares alternatives;
- a concrete next step is mutually agreed;
- client initiates a substantive follow-up;
- decision-maker is identified;
- repeated postponement occurs without a committed date.

Bad standalone features:
- deal duration;
- number of calls/messages;
- amount/source/pipeline;
- raw token volume;
- final stage/reason;
- any information only visible after the outcome.

Structured numeric/process facts that can be computed exactly should not become Jev semantic classifiers unless semantic interpretation is necessary.

## Confounds

Even with one manager, confounds remain:
- WON timelines are larger on average than LOST;
- deal duration differs;
- amount/source/pipeline may differ;
- a few long deals can dominate;
- two long LOST deals have incomplete early-call transcripts.

Do not confuse these with semantic success patterns.

## Evidence standard

Prefer candidates that have:
- evidence in at least 2 deals;
- at least one counterexample check;
- a clear pre-outcome definition;
- a plausible snapshot-time classifier;
- low leakage risk.

Do not claim causality or predictive power at this stage.

Use language such as:
- candidate pattern;
- appears more often in;
- worth validating;
- possible confound.

## Jev suitability

A candidate is Jev-suitable if it can become an atomic:
- boolean;
- small categorical choice;
- ordinal score with explicit anchors.

Not suitable if it:
- requires broad strategic reasoning;
- depends on future outcome;
- is deterministic from structured data;
- is too vague to label consistently.

## Output location

All outputs for this run:

```text
research_outputs/discovery_v1/
```

If a completed run already exists, create the next version.

## Stop condition

Stop after:
- independent discovery;
- adversarial critique;
- deduplication;
- final candidate feature catalog.

Do not yet:
- score every feature across all 23 deals;
- run blind validation;
- train a predictive model;
- integrate Jev;
- modify NeuroROP.
