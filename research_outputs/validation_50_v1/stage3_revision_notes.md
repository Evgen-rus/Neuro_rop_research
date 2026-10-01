# Stage 3 input revision

The first build is preserved under `stage3_pre_qc_v1/` and is quarantined. Its initial automated QC was superseded by the independent task-title review.

Two mutable task snapshots were removed before the baseline view filter:

- 6941, task 31977: explicit customer refusal status in the current task title.
- 7107, task 34271: exact terminal milestone title with completed status and matching close, status-change and update timestamps. Completion occurred one second before the terminal transition. The snapshot is excluded; its title is not used as proof of payment.

Other dated predecision events remain. The baseline v1 terminal-marker/suffix policy and all baseline files remain unchanged. Deal 6351's project-bankruptcy/inactive-procurement worklog remains a manager claim with its inferred entry date and original recorded timestamp.

The corrected build has 50 deals, 3,673 normalized events and 3,174 view events. Neutral metadata, quality sidecars and views for the existing drafts 6691, 6741 and 6813 are byte-identical to the quarantined inputs. Their drafts passed schema and exact evidence-pointer checks against the corrected inputs. The exposed 6941 worker stopped before writing an audit; a fresh worker is required.

Pre-freeze draft corrections: 6741 had two extra top-level headers removed mechanically; 6813 was corrected after the worker read the explicit absolute neutral/quality paths. No outcome labels were used in these corrections.

Small assigned sets may share a worker dispatch, but every deal receives its own audit from its own evidence. This changes dispatch granularity only; schema and semantic method are unchanged. Independent reliability workers receive no primary audits.

Independent corrected-input QC: PASS. All 50 input sets, top-level and per-deal hashes, source-row pointers, strict pre-cutoff chronology, absence of earlier terminal-stage rows, two task exclusions and forbidden metadata checks passed. Apparent checker mismatches were corrected assumptions (the input contract is the baseline contract; transcripts and call shells have separate source rows), not data defects. Stage2 separately verifies activity/transcript linkage. The 296 baseline source/output hashes are unchanged.
