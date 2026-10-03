# Continuation checkpoint — Stage 4, not complete

Latest 2026-10-03: 41/50 primary audits accepted; nine remain. Batches E/F returned7137/6907 and both passed primary review.6811 draft is NOT accepted: view source_line98 manager_worklog:2474611:0 explicitly claims80%payment received. Scope review is checking this missed application of the already approved terminal-source principle; no freeze/reveal until corrected. Fresh batch G owns6955/18385/7619; five other unaudited IDs5293/7567/7217/18283/6791. Secondary0/15. Progress must distinguish accepted drafts from returned drafts; preserve unchanged accepted audits by input hashes.

Latest accepted progress: 38/50 primary audits; 12 remain. Batch D completed; its evidence types and final factual wording were checked/corrected by primary. Batch E retains7035/7137, batch F owns6811/6907. Eight IDs unassigned:6955,5293,7567,18385,7619,7217,18283,6791. Secondary0/15, no phase freeze or reveal. Accepted hashes in `stage4_arrival_qc_v5.json`; earlier counts below are historical.

Latest accepted progress: 35/50 primary audits; 15 remain. Batch C completed and accepted; batch D still owns7307/6841. Fresh batch E owns6999/7035/7137. Ten IDs not yet assigned:6811,6907,6955,5293,7567,18385,7619,7217,18283,6791. Accepted hashes and pre-freeze factual corrections are recorded in `stage4_arrival_qc_v5.json`. No labels revealed, no phase freeze. Earlier progress below is historical.

Latest 2026-10-03: 31/50 primary audits accepted; 19 remain. All eight cases in batches A/B were accepted after schema, evidence-pointer and targeted semantic review. `stage4_arrival_qc_v5.json` pins accepted audit hashes. Fresh batches C (18845,18865,6351) and D (7107,7307,6841) are active; 13 remaining IDs not yet assigned:6999,7035,6811,6907,7137,6955,5293,7567,18385,7619,7217,18283,6791. No primary freeze, secondary audits or outcome reveal yet. 15 secondary audits remain. Earlier counts below are historical.

Current 2026-10-03: user resumed after limits refresh. Actual source-policy rebuild and independent structural QC are PASS: 50 views, 2957 visible events (71 removed from 3028), canonical source timelines retained. There are exactly 23 accepted active primary drafts and 27 remaining primary audits; 15 independent secondary audits remain after primary freeze. No outcomes revealed. Fresh Luna Max batches A (7543,18533,18925,7639) and B (18357,18523,7221,18339) dispatched. Report accepted/remaining counts after each worker batch; reuse unchanged checks by hashes and group small deals to reduce overhead.

Current2026-10-02: user resumed and approved the complete conservative source-policy proposal. Full50 input QC completed; proposed removal71/3028 events across20 deals. Snapshotv5 saved;11 exposed drafts archived with hash index;23 active drafts retained. `terminal_source_policy.json` holds exact approval/cohort/source pins; builder/checker implementation and rebuild QC are in progress. Continue Stage4–6 after input QC; no primary/canonical freeze or outcome reveal yet. The older notes below are historical.

Historical limit checkpoint. User reported limits reset and work resumed; use `run_manifest.json` and actual audit files for current progress. The incomplete-recording quality patch is now implemented and Stage2 regeneration passes; this document's remaining list below records the earlier stop.

Latest checkpoint: 23 primary drafts pass schema/evidence-pointer QC. User explicitly approved quarantining five mutable worklogs with unresolved inferred years (144 entries) and continuing. The exact rule is in `worklog_quarantine_policy.json`; research builder implementation and revised input QC are in progress. Preserve raw, all 50 cohort IDs and other communications; use fresh semantic workers for these five deals. No affected deal has an audit; no primary/canonical freeze or outcome reveal has occurred. After revised input QC, 27 primary audits remain, followed by 12–15 independent reliability audits, canonical freeze and Stage6 analysis. Earlier counts and stop notes below are historical.

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
