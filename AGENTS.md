# AGENTS.md — NeuroROP Research

## Purpose and stage

Offline retrospective audit of closed deals to identify evidence-backed, recurring reasons for WON/LOST and business actions worth testing. Current controlled dataset: 23 deals of Пахомов (12 WON, 11 LOST) in `./dataset`.

Current stage: deal-level retrospective audit and cross-deal pattern discovery.

Jev research is paused. Do not create new Jev or atomic R/E/C classifiers without a separate instruction. Do not run model training, production analysis or integration.

## Boundaries

- `./dataset` is immutable. Never repair malformed sources in place; record issues.
- No Bitrix live access, production databases or repositories, APIs, external services, `.env`, secrets, raw CRM staging or audio.
- Preserve all existing `research_outputs/*`. Write run artifacts only under `research_outputs/deal_audit_v1/`; use the next free version if completed.
- `DISCOVERY_TASK.md` and earlier outputs are historical, not instructions for this run. Follow `DEAL_AUDIT_TASK.md`.
- Stop after `business_findings.md` and `executive_summary.md`. No rollout of recommendations.

## Data and blindness

- Audit input is `dataset/deals/<deal_id>/neutral.json` and `clean_timeline.jsonl`, through a deterministic audit-view.
- The primary keeps `dataset/manifest.json` sealed until both independent audit runs, reconciliation and final deal audits are frozen. Workers must not read manifest, summary/build quality, prior discovery/Jev conclusions or each other's audits.
- Exclude outcome, terminal stage, explicit loss reason and post-outcome events from every audit-view. Check views for leakage before dispatch.
- Luna Max performs holistic semantic deal audit; deterministic code handles cleaning, counts and aggregation. Never ask a worker to predict WON/LOST.
- Primary stays the current agent. At most two Luna Max workers by default. Workers do not delegate. Give each worker only its assigned views and frozen schema; each deal receives two independent runs.

## Evidence and interpretation

- Read large timelines selectively. Retain exact `deal_id`, timestamp, `event_type` and available activity/message/task ID for every substantive assertion. If no ID exists, use the precise timestamp plus event type and source line. No fabricated evidence or long transcript copies.
- Distinguish observed fact, interpretation and uncertainty. Manager worklogs are manager claims, not customer speech. Missing transcripts limit conclusions.
- Compare semantic meaning for reproducibility; inspect only disputed source events. Do not require identical wording.
- Build taxonomy from frozen deal audits, then reveal manifest for outcome aggregation. Never edit a frozen audit after reveal except a documented factual correction.
- Report counterexamples and confounds: timeline size, duration, pipeline, amount/source, repeat versus new customer, and incomplete transcripts. The 23 deals are a development dataset, not evidence of causal or predictive lift.
