# Frozen classifier contract — Validation 2A.1

This document and `refined_classifier_contract.json` are frozen before labeling. Inputs are the outcome-blind snapshots from `validation_2a`. Each answer needs a value, confidence, a short reason, and exact pointers to supporting snapshot events. Silence is `UNKNOWN`, unless the specific `NO` rule below is satisfied.

| ID | Mode | Values | Decision boundary |
|---|---|---|---|
| R01a | CURRENT_STATE | YES / NO / UNKNOWN | Is the customer-side role responsible for the **current** internal decision gate explicitly identified? `NO` only after substantive process discussion without an identified role. |
| R01b | CURRENT_STATE | YES / NO / UNKNOWN | Is a concrete action for that gate stated? Generic “look”, “think” or “decide” is `NO` after substantive discussion. |
| R01c | CURRENT_STATE | YES / NO / UNKNOWN | Is there a bounded date, deadline, event or expected result for that gate's action? A seller callback does not count without an explicit link. |
| R03 | CURRENT_STATE | UNKNOWN / INSUFFICIENT / PARTIAL / SUFFICIENT_FOR_CURRENT_ASSESSMENT | First identify the active technical task. Judge received customer data against the data needed for **that task**. Sufficient means the current check can proceed without critically missing data. |
| R04 | CUMULATIVE_FACT | YES / NO / UNKNOWN | `YES` requires customer-stated, application-specific, checkable technical content. `NO` requires substantive technical discussion without such content. With too little discussion use `UNKNOWN`. A past `YES` remains `YES`. |

R01a/b/c refer to one shared current decision gate, recorded as `r01_gate_key`. The code-derived R01 level is 2 when all three are `YES`, 1 when at least one is `YES` and not all, 0 when all three are `NO` after substantive discussion, and `UNKNOWN` otherwise. Do not combine fragments from different gates.

## R02 event extraction and state

The semantic layer extracts each explicit customer-owned commitment visible by the snapshot cutoff. Each record has `commitment_id`, `agreed_at`, `owner`, `action`, `due_at` or `expected_result`, `replaces_id`, and timestamps of explicit completion, rescheduling or missed-step evidence. `NO_COMMITMENT` is allowed only after substantive discussion without a concrete agreement; otherwise the empty ledger means `UNKNOWN`.

For the latest applicable commitment, also label the categorical presence of `commitment_exists`, `customer_owner`, `promised_action`, `due_at_or_expected_result`, `reported_completion`, `reported_reschedule`, `replacement_commitment` and `explicit_miss` with `YES/NO/UNKNOWN`. A `NO` for completion, rescheduling or miss needs an explicit negative statement; no recorded event means `UNKNOWN`.

Code, using only extracted records dated by cutoff, derives `NO_COMMITMENT`, `NOT_DUE`, `COMPLETED`, `RESCHEDULED_WITH_CONCRETE_REPLACEMENT`, `MISSED`, `REPEATEDLY_MISSED` or `UNKNOWN`. A passed due date without completion evidence is **not** a confirmed miss. Repeatedly missed requires at least two explicitly confirmed missed concrete commitments without normal concrete replacement. A concrete replacement has customer owner, action and bounded date or expected result. Date-only deadlines remain open through the end of their local date.

The machine-readable contract is authoritative for fields, values and rules. Classifiers do not inspect deal results, discovery evidence, older labels or other snapshots beyond their assigned inputs.
