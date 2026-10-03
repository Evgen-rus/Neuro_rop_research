# Stage 3 input revision

The first build is preserved under `stage3_pre_qc_v1/` and is quarantined. Its initial automated QC was superseded by the independent task-title review.

Two mutable task snapshots were removed before the baseline view filter:

- 6941, task 31977: explicit customer refusal status in the current task title.
- 7107, task 34271: exact terminal milestone title with completed status and matching close, status-change and update timestamps. Completion occurred one second before the terminal transition. The snapshot is excluded; its title is not used as proof of payment.

Other dated predecision events remain. The baseline v1 terminal-marker/suffix policy and all baseline files remain unchanged. At this historical revision, deal 6351's project-bankruptcy/inactive-procurement worklog remained a manager claim; the later approved chronology quarantine below supersedes that retention decision.

The corrected build has 50 deals, 3,673 normalized events and 3,174 view events. Neutral metadata, quality sidecars and views for the existing drafts 6691, 6741 and 6813 are byte-identical to the quarantined inputs. Their drafts passed schema and exact evidence-pointer checks against the corrected inputs. The exposed 6941 worker stopped before writing an audit; a fresh worker is required.

Pre-freeze draft corrections: 6741 had two extra top-level headers removed mechanically; 6813 was corrected after the worker read the explicit absolute neutral/quality paths. No outcome labels were used in these corrections.

Small assigned sets may share a worker dispatch, but every deal receives its own audit from its own evidence. This changes dispatch granularity only; schema and semantic method are unchanged. Independent reliability workers receive no primary audits.

Independent corrected-input QC: PASS. All 50 input sets, top-level and per-deal hashes, source-row pointers, strict pre-cutoff chronology, absence of earlier terminal-stage rows, two task exclusions and forbidden metadata checks passed. Apparent checker mismatches were corrected assumptions (the input contract is the baseline contract; transcripts and call shells have separate source rows), not data defects. Stage2 separately verifies activity/transcript linkage. The 296 baseline source/output hashes are unchanged.

Later source-quality revision: nine native incomplete files across six deals were refreshed once and remained 3 seconds. Explicit measured-file-vs-CRM-span limitations were added. The prior inputs are preserved under `stage3_pre_audio_qc_v2/`. All50 views/neutral remain byte-identical; quality changes only for 5293, 6351, 6589, 6665, 6693, 6695. Nineteen active drafts have unchanged assigned inputs; 6589 is preserved in `audit_revisions/` for a fresh blind redo. Independent revision QC passed and is recorded in `stage3_quality_revision_qc.json`.

Additional pre-freeze draft QC corrections: 18533's material-improvement boolean changed to null because the available evidence supports an optional continuation of the scheduled demo, not a material counterfactual effect; 18925's unlinked-lead wording was corrected to absence of a linked source lead. No outcome labels were used.

Pre-freeze factual correction, 18729: the handoff gap concerned a departed supplier employee, not a change inside the customer's company. Corrected the weak-action wording from the manager's email (activity628637, source_line26) and the customer's resubmission (629437, source_line27); the manager's stated cause remains attributed. No labels used.

Approved chronology revision: the user authorized excluding only five mutable manager worklogs (5293/2256255, 6351/2385479, 6673/2444709, 6693/2449053, 6695/2449263; 144 entries) whose inferred calendar years and edit history cannot be verified. Exact source hashes are pinned in `worklog_quarantine_policy.json`. Raw sources, cohort and other communications remain. Previous inputs and builder are preserved in `stage3_pre_worklog_quarantine_v3/`. This is an explicit exception to v2 worklog retention, recorded as a source-quality limitation. Rebuild/QC is in progress; fresh workers are required for those five deals.

Approved chronology rebuild QC completed: PASS in `stage3_worklog_quarantine_qc.json`. Exactly144 entries removed; all other normalized events byte-preserved, zero residual quarantined IDs, 3,030 source pointers/cutoffs checked, 200 per-deal hashes and all top hashes verified, all50 neutral and23 prior draft input sets unchanged. Stage2 remains470/470; all296 baseline hashes match. New pre-freeze pointer corrections in6673/6695 copied exact canonical timestamps; no labels used.

Terminal-refusal guard revision: the explicit phrase "от нашего варианта/предложения отказались" now uses the existing terminal-marker/suffix rule, with negation protection. Previous inputs and exact builder are preserved in `stage3_pre_terminal_guard_v4/`. Only6841 view changed: source_lines39/40 removed; its exposed draft is preserved in `audit_revisions/6841_pre_terminal_guard.json` and needs a fresh audit. Independent `stage3_terminal_guard_qc.json` confirms all50 neutral/quality/timelines unchanged, all34 active draft input sets unchanged, 3,028 source pointers valid, baseline296 hashes unchanged and Stage2 PASS470/470. This structural PASS does not establish semantic source admissibility.

Resumed2026-10-02: `draft_arrival_qc.json` validates34 active primary drafts and302 exact evidence pointers, with zero errors. Full50 semantic input QC is underway; further audit dispatch, primary freeze and outcome reveal wait for the terminal/source-chronology gate. Signature alone and ordinary configuration objections or temporary project pauses remain nonterminal under the existing v2 contract.
# Approved source-policy rebuild — 2026-10-03

Independent structural verification passed: 50 canonical timelines and neutral files unchanged; exactly 20 views changed, removing 71 events (3028 to 2957); 30 views unchanged. Twenty quality files append only the same generic admissibility limitation. Twenty-three retained primary drafts have identical view/quality inputs. Eleven exposed drafts are preserved in `audit_revisions/source_policy_v5/` and require fresh audits. All 296 baseline file hashes and the 470/470 transcription gate are unchanged. Source-policy reasons remain outside semantic worker inputs. The conservative exclusion may omit genuine predecision communications and must be disclosed in the comparison with v2.
