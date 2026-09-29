# Deal Audit v1

## Objective

Audit all 23 historical closed deals as whole trajectories, blind to final outcome, then compare frozen audits across WON and LOST to identify recurring objective and controllable business patterns. Do not analyze a live deal or recommend automatic rollout.

## Execution order

1. Build and inspect a deterministic, outcome-blind audit-view for every deal. Freeze `input_contract.md`, `audit_schema.json`, and `audit_manifest.json` before semantic work. Keep timestamps, order, speaker/source when reliable, substantive transcripts, messages, emails, tasks, comments and necessary process events. Preserve precise evidence pointers. Record original/view events, estimated tokens, reduction and removal reasons. Record missing or malformed input without repairing it.
2. Assign each deal to two independent Luna Max runs, A and B. Each receives the same frozen view and schema, with no label, prior research conclusion or other run's answer. Save one valid JSON per deal in `audits/run_A/` and `audits/run_B/`.
3. Have a separate critic compare the paired audits semantically on primary explanation, controllability, turning point, manager influence, strongest weakness, and strongest positive/negative customer signals. Mark AGREE, PARTIAL or DISAGREE with reasons. The primary checks only disputed source events. Save `reliability.json` and `reliability_summary.md`.
4. Reconcile to one evidence-grounded audit per deal in `audits/final/`. Freeze files and hashes. Only then read `dataset/manifest.json`. Any later factual correction requires an audit trail and must not be guided by label.
5. Derive a taxonomy from observed frozen audits. Compare WON and LOST, count deal-level occurrences, identify counterexamples, and separate manager, company, customer and external factors. Use deterministic code for counts. Save `taxonomy.json` and `won_vs_lost.json`.
6. Write `business_findings.md` and `executive_summary.md` for the owner/РОП. For each useful pattern give deals and evidence, counterexamples, estimated controllability, business consequence, concrete process change and how to measure it. Distinguish objective losses and wins despite weaknesses. Record run versions, hashes, worker routing, issues and limitations in `run_manifest.json`.

## Audit rules

- Audit state and trajectory, not predicted outcome. The primary explanation describes the visible trajectory, with uncertainty where closing cause is unknowable.
- Never treat a customer statement alone as proof that a factor was objective. Seek corroboration and report alternatives.
- Do not equate activity volume, duration, amount, source or pipeline with semantic performance.
- No scoring all deals on old atomic features, Jev work, model training, live CRM access or production changes.
- Stop when both business reports are complete. The user and primary will conduct a separate manual business review.
