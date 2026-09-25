# DISCOVERY_TASK.md — Controlled Feature Discovery v1

## Objective

Analyze the 23-deal controlled dataset for Пахомов and discover semantic candidate features that may distinguish WON from LOST **before final outcome**.

This is hypothesis generation, not proof.

## Phase 0 — Lightweight inspection

Read first:

- `AGENTS.md`
- `dataset/manifest.json`
- `dataset/summary.json`
- `dataset/build_quality.json`

Do not begin by reading all timelines.

Create:

```text
research_outputs/discovery_v1/
```

If that run is already completed, create the next version.

## Phase 1 — Build balanced shards

Create 3 independent shards covering all 23 deals once:

- A: 4 WON + 4 LOST
- B: 4 WON + 4 LOST
- C: 4 WON + 3 LOST

Balance approximate token volume first, while reasonably spreading:
- pipeline;
- amount;
- source;
- short/medium/long durations.

Write:

```text
research_outputs/discovery_v1/shard_plan.json
```

Include:
- deal_id
- outcome
- token estimate
- shard

Outcome remains a separate label and must never be injected into timeline text.

## Phase 2 — Independent Luna Max discovery

Use Luna Max workers for the 3 independent shard analyses.

Run up to 3 concurrently only if the Codex environment supports this safely; otherwise run 2 then the third.

Each worker gets only its shard and reads:

```text
dataset/deals/<id>/neutral.json
dataset/deals/<id>/clean_timeline.jsonl
```

Each worker knows outcome labels for its assigned deals separately.

### Worker goal

Compare WON vs LOST from the same manager and find semantic differences visible before outcome.

Look across, but do not force findings in every category:

1. customer intent / buying signals
2. qualification quality
3. decision-maker / stakeholders
4. next-step quality
5. objections
6. price/value discussion
7. manager control
8. client initiative
9. urgency/timing
10. competitor comparison
11. follow-up behavior
12. clarity of requirements
13. internal customer decision process
14. commitment strength
15. momentum loss / postponement
16. communication quality

### For each candidate

Return:

- `feature_name`
- `short_definition`
- `jev_type`: boolean | ordinal | choice | not_suitable
- `jev_question`
- `when_observable`
- `direction_observed`: more_in_won | more_in_lost | mixed
- `won_evidence`
- `lost_evidence`
- `counterexamples`
- `possible_confounds`
- `leakage_risk`: low | medium | high
- `notes`

Evidence must use:
- `deal_id`
- timestamp
- `event_type`
- `event_id` / `activity_id` / another available event identifier
- short paraphrase

If the source has no event identifier, use the most precise available combination: `deal_id` + timestamp + `event_type`. This lets the critic and primary check the specific evidence without rereading the entire deal. Do not paste long quotes or a full transcript.

Explicitly reject as standalone semantic features:
- number of calls/messages
- duration
- amount
- source
- pipeline
- token volume
- anything only visible after outcome

Each worker writes:

```text
research_outputs/discovery_v1/agents/shard_A.json
research_outputs/discovery_v1/agents/shard_A.md
```

(and B/C).

Target roughly 10–20 plausible features per shard, fewer if evidence is weak.

Do not inflate the list.

## Phase 3 — Adversarial critic

After all shard outputs exist, use a fresh Luna Max worker as critic.

Initially it reads only:
- `shard_plan.json`
- shard A/B/C JSON outputs

It should attack the candidate list.

For each recurring/important candidate ask:

1. Is this just deal length?
2. Is this just amount/source/pipeline?
3. Is this leakage?
4. Is it too vague for consistent classification?
5. Is it supported by only one unusual deal?
6. Is another shard contradicting it?
7. Is it a consequence of an already-lost deal rather than an early signal?
8. Can it become an atomic Jev question?

The critic may inspect only a small number of raw timelines to resolve specific contradictions.

Write:

```text
research_outputs/discovery_v1/critic.json
research_outputs/discovery_v1/critic.md
```

Verdict per candidate:

- keep
- revise
- merge
- reject

## Phase 4 — Primary synthesis

The current primary agent now reads:
- shard outputs
- critic outputs
- lightweight metadata

Do not reread all 23 timelines.

Cluster duplicates and produce a canonical feature catalog.

Prefer atomic features.

Bad:
> Manager worked well.

Good:
> A concrete next step with date/time and responsible party was mutually agreed.

Bad:
> Client was interested.

Good:
> Client independently initiated at least one substantive follow-up about the purchase.

## Final outputs

### `feature_candidates.json`

Follow `FEATURE_CANDIDATE_SCHEMA.json`.

Aim for roughly 15–30 high-value candidates.
Do not keep weak candidates to hit a target.

### `feature_candidates.md`

Human-readable table:

- ID
- feature
- observed direction
- Jev type
- evidence breadth
- main confound
- critic verdict
- validation priority

Priority:
- high
- medium
- low

This is validation priority, not predictive score.

### `executive_summary.md`

Under ~1000 words.

Include:
- dataset analyzed
- shard design
- 5–10 most interesting candidates
- surprising observations
- major confounds
- what must NOT yet be concluded
- recommended validation step

### `run_manifest.json`

Record:
- run version
- primary model actually selected
- worker class/reasoning actually used
- shard deal IDs
- outputs produced
- worker failures/fallbacks
- whether primary inspected any raw timeline
- timestamp

## Interpretation rule

Do not say:

> Feature X predicts WON.

Say:

> Feature X repeatedly appeared as a candidate difference and should be validated.

## Stop

After final outputs are written, stop.

Do not run validation yet.
