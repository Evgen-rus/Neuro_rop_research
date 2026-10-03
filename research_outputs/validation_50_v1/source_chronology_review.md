# Source chronology gate

Native parsed manager worklogs for five deals have a calendar-year conflict. The first yearless note matches the creation month/day of its source comment, but its parsed year is one year earlier. The source comment is mutable; the captured raw data contain creation time and no modification/version time. Customer activity dates corroborate a later calendar anchor, but do not prove the year of every manager entry.

| Deal | Worklog | Entries | Comment created | Native parsed range |
|---|---|---:|---|---|
| 5293 | 2256255 | 51 | 2025-09-08 | 2024-09-08 — 2025-03-20 |
| 6351 | 2385479 | 30 | 2025-11-18 | 2024-11-18 — 2025-05-28 |
| 6673 | 2444709 | 22 | 2025-12-19 | 2024-12-19 — 2025-03-03 |
| 6693 | 2449053 | 26 | 2025-12-01 | 2024-12-01 — 2025-02-04 |
| 6695 | 2449263 | 15 | 2025-12-19 | 2024-12-19 — 2025-01-23 |

Scope: 144 entries in five of the 41 parsed worklogs, across five of the frozen 50 deals. All 23 currently saved primary audits concern other deals; no affected audit was saved or frozen. Workers exposed to potentially terminal entries must not audit these five after an input revision.

The native endpoint-year inference is in `Neuro_rop_practice/bitrix/manager_worklog.py:178-258`; raw fetching calls it at `bitrix/deals/1_fetch_deals_context.py:526`. The research builder consumes inferred dates as midnight event timestamps at `build_validation_dataset.py:292-333`. Baseline v2 explicitly retains same-day notes and manager worklogs, so silently removing these sources would change its retention policy.

A bounded read-only search of existing local snapshots/SQLite is complete. Validation SQLite contains one latest row per worklog; its seen/changed timestamps all equal the bundle import on 2026-10-01. Practice SQLite has no rows for these worklogs. Both databases contain no trajectory events for the five deals, and their exact practice raw context files are absent. No historical version or edit timestamp resolves the years. No years have been rewritten and no source records removed.

The user explicitly approved quarantining these five worklogs and continuing. The approved rule is saved in `worklog_quarantine_policy.json`: retain all raw sources and customer communications, flag unavailable chronology in per-deal quality, rebuild/QC the views, and audit the affected deals with fresh workers. Cohort IDs and baseline stay intact. This documented exception to the baseline v2 retention policy is implemented: 144 entries removed, only the five views/quality files changed, all50 neutral files and23 saved draft inputs byte-identical. Independent revised QC passed all14 checks (`stage3_worklog_quarantine_qc.json`). Previous inputs and exact builder remain under `stage3_pre_worklog_quarantine_v3/`.
