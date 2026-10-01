# Continuation checkpoint — Stage 4, not complete

Historical limit checkpoint. User reported limits reset and work resumed; use `run_manifest.json` and actual audit files for current progress. The incomplete-recording quality patch is now implemented and Stage2 regeneration passes; this document's remaining list below records the earlier stop.

Latest checkpoint: 23 primary drafts pass schema/evidence-pointer QC. Semantic work is paused on a different, real gate: five mutable manager worklogs have unresolved inferred years (144 entries). Local snapshots/SQLite provide no historical proof. See `source_chronology_review.md/json` for the exact sources and an unapplied five-worklog quarantine proposal. No affected deal has an audit; no primary/canonical freeze or outcome reveal has occurred.

All three active Luna agents failed with `usage limit`; their error suggested retry at 7:20 PM without a timezone. Desktop usage tool returned contradictory 0% usage. No reset credit or purchase was used. Do not replace the required Luna blind method silently.

## Completed

- Cohort frozen: 50, 25/25, baseline overlap 0.
- Stage2: 470 measured recordings >=36 seconds, all 470 linked nonempty transcripts; 396 unknown durations, 401 audio-unavailable entries. Counts overlap; missing sources are limitations.
- First corrected Stage3 input QC passed. Original leaking build preserved in `stage3_pre_qc_v1/`; two mutable terminal task snapshots excluded.
- Sixteen primary drafts saved; schema and exact evidence-pointer QC pass. No audit-set freeze or outcome reveal.
- Baseline integrity: 296 files unchanged.

Primary draft IDs: 18357, 18533, 18639, 6573, 6589, 6691, 6741, 6813, 6941, 7031, 7043, 7221, 7543, 7565, 7623, 7639.

## Source-quality correction before further freeze

Native manifests flag nine incomplete recordings across **six** deals. Each is a 61,361-byte, 3-second fragment. The CRM spans below are metadata, not measured complete recordings:

| Deal | Activity | CRM span, seconds |
|---|---|---:|
| 5293 | 516303 | 67 |
| 5293 | 516429 | 20 |
| 5293 | 516447 | 43 |
| 6351 | 514215 | 25 |
| 6351 | 516351 | 125 |
| 6589 | 512487 | 800 |
| 6665 | 516249 | 40 |
| 6693 | 519595 | 63 |
| 6695 | 516441 | 340 |

One exact-ID native refresh completed; none grew. No new eligible transcript appeared. Private sanitized results and pre-refresh metadata are under `_private/logs/targeted_audio_recovery_2026-10-01*`. The incomplete-quality correction was proposed but **not implemented** when the worker hit its limit. Existing short-file counts must not be read as proof of short conversations/no-answer.

Next: add explicit incomplete flags/count/limitations in `stage2.py`; keep ANY measured audio >=36 seconds transcript-required. Regenerate completeness; preserve the current Stage3 snapshot in a new version, rebuild/freeze inputs, compare every draft's view/neutral/quality bytes. Update the 6589 draft's duration caveat from unresolved contradiction to documented source incompleteness, preserving its prior version. Other unaffected drafts require hash proof for reuse. Private call manifests changed during refresh, so current input provenance hashes require revalidation.

## Remaining

1. Source-quality correction and revised input QC.
2. 34 primary audits, semantic QC of all 50, primary freeze.
3. Outcome-blind sample of 12–15, fresh independent secondary audits, reconciliation and canonical freeze.
4. Reveal outcomes; T1–T5, open discovery, manager robustness, baseline comparison, final reports and final integrity checks.
5. Commit/push finished research; stop after Stage6.

Remaining canonical views are about 3.88 million UTF-8 byte/4 proxy tokens, dominated by repeated email quotations. Current email text plus non-email content is about 0.65 million byte/4 proxy tokens before metadata and relevant full quotes. These are size proxies, not actual model usage. Two Luna Max semantic workers run in parallel; a separate bounded Luna worker handled native recording refresh. Primary owns gates, evidence QC and integration.
