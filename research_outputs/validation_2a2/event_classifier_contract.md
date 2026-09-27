# Frozen event classifier contract — Validation 2A.2

Unit: one real semantic event. A single preceding related event may be supplied to resolve a reference or an earlier customer commitment. No full deal history or later event is given. Each classifier returns `YES` or `NO`; fields are extracted only when the current event satisfies `YES`. Lack of explicit evidence is `NO`, never an inferred whole-deal state.

| ID | YES means | Hard negative |
|---|---|---|
| E01 CUSTOMER_COMMITMENT | Customer-side person/team explicitly undertakes a concrete future action. Extract owner, action and stated deadline/expected result. | Seller promises to call; customer merely says “посмотрим”, “подумаем”, “возможно” or “попробуем” without a concrete owned action. |
| E02 COMMITMENT_COMPLETION | Customer explicitly reports completing a previously agreed customer-side action. Extract completed action. | Seller completed their task; action is only planned; a file exists without an attributable completion report. |
| E03 COMMITMENT_RESCHEDULE | Customer explicitly moves a previously agreed action to a **new stated** date, event or expected checkpoint. Extract new checkpoint. | Seller moves their call; vague delay has no new checkpoint; new unrelated plan. |
| E04 EXPLICIT_MISS | Event explicitly establishes noncompletion of an identifiable agreed customer-side action. | Deadline passed, customer silent, record absent or seller merely guesses. |
| E05 DECISION_GATE_FACT | Event states a fact tied to a particular internal customer decision gate. Extract role, action and checkpoint independently; each may be null. | Generic “решим” without an identifiable internal gate, or a seller's step. |
| E06 CHECKABLE_TECHNICAL_REQUIREMENT | Customer states an application-specific technical requirement, constraint or answerable question. | General interest, seller's suggestion or generic equipment category. |

Fields are short source-grounded normalized phrases. For E05, do not compose role, action and checkpoint from different gates. E02–E04 may use the one supplied previous related event as an anchor; the current event must establish completion, rescheduling or a miss. Neither model chooses current whole-deal status, overdue status, repeated-miss count, or R01/R02 levels. Deterministic code handles those after labeling.

The JSON contract is authoritative and is frozen before benchmark selection and double labeling.
