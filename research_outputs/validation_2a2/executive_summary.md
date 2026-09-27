# Validation 2A.2 — event-level extraction

## Result

Six frozen event-level contracts were tested on 195 real, outcome-blind event packets from 23 deals. Two independent Luna Max labelers saw the same current event and at most one previous relevant event. E06 checkable technical requirement alone met the predeclared reliability threshold: 95.3% overall exact, 96.9% YES agreement, 90.9% NO agreement, with 31 jointly YES and 10 jointly NO. Its verdict is `READY_FOR_JEV_TEST`, meaning a bounded Jev classifier test may be designed; this is not predictive validation or integration approval.

E01–E04 need revised source-attribution, prior-action linkage, checkpoint and field normalization rules. E05 had perfect binary agreement on 31 packets, but only six jointly NO cases and weak literal agreement for decision-action/checkpoint fields, so it also needs revision. E04 had only four jointly YES cases. The target of 40–60 examples per classifier could not be reached for E01–E05 from the curated, context-checkable events without padding; the frozen sizes are 34, 34, 29, 24, 31, 43 respectively.

## R02 and R01 prototypes

`state_prototype.py` demonstrates deterministic R02 state transitions from adjudicated E01–E04 events and R01 gate-fact aggregation from adjudicated E05 events. It requires explicit `commitment_id` / `gate_id` links, which the current classifiers do not extract. Missing links remain unresolved. Elapsed time never creates an explicit miss. The self-check passes, but neither prototype is ready for automated whole-deal publication.

## Limits and stop

This benchmark measures annotator agreement on selected packets. It does not estimate class prevalence, causal effects or prediction of WON/LOST. The disagreement audit flags several worklog summaries, multi-action calls and thin-context events; E06's pass is conditional on a cleaner follow-up benchmark. No outcome labels, holdout, CRM, external service, Jev runtime, production repository or model training were used. Dataset files were not changed. R03 and R05–R10 remain deferred. Work stops here after this event-level report and prototypes.

See `event_classifier_contract.md`, `event_benchmark.md`, `reliability_summary.md`, `reliability/disagreement_audit.md`, `r02_state_machine.md`, `r01_gate_state.md`, and `jev_ready.md` for details.
