# Adversarial critique — discovery_v1

## Verdict

The three shards repeatedly found buyer-owned milestones, decision gates, technical evidence, and customer-led interaction. Many names describe the same construct. Their apparent direction is not consistent enough to call any pattern predictive: 7243 reached reported executive approval, price acceptance, technical review, and contract preparation but was LOST; 18733 WON after internal dates moved; LOST cases 18731 and 18629 still supplied detailed technical information and accepted the quoted price.

Consolidate the 29 shard entries into ten snapshot candidates in critic.json. The strongest Jev shapes are anchored states for a buyer-owned milestone, decision-gate clarity, application-input sufficiency, and actionable technical specificity. Treat them as descriptive candidates pending broader validation.

## Main attacks

- **Decision path:** A01/B04/C01/C08 overlap. Merely naming an approver or gate is weak: 7243 reports executive approval before loss; 18731 and 18929 have review processes with little access or control. Score owner, concrete action, and bounded checkpoint together.
- **Next steps and delay:** A02/A10/B06/B07/C02 overlap. A date or scheduled call occurs on both sides. Separate not-yet-due from overdue; count repeated slippage only when a buyer-owned checkpoint was actually missed without a concrete replacement. Do not substitute deal age or contact volume.
- **Technical information:** A03/B01/C03 overlap, but receipt of photos or samples is not sufficiency. Score whether customer-provided inputs support assessment of the stated application. Technical specificity (A04/B03/C07/C10) is a separate quality dimension and can be high in LOST cases.
- **Technical fit and proof:** A06/B02/C06 are related but not interchangeable. A requested demonstration is not validation; production review is not a customer test. A combined state must distinguish unresolved feasibility from a review-supported or tested result. Deal 7243 is a clear warning that a feasible proposal does not ensure purchase.
- **Alternatives and preference:** B05/C05 describe comparison and are mixed. A09 is different: an explicit current preference is more specific, but seller worklogs can overstate it and it has only one-shard support.
- **Stage leakage:** A08/B09 track legal, finance, or contract work close to purchase. Keep only as a buyer-side process state and do not claim early-snapshot value. Do not score signed, paid, or final-stage facts.
- **Initiative and capture:** A05/B08/C09 are atomic but mixed. A callback after a seller call is weaker than an independently initiated buying step; channel and worklog coverage affect whether it is observed.
- **Price response:** Reject C04 as an outcome-discriminating candidate. It is mixed in shard C, and A also found price acceptance alone in both outcomes.

## Confounds and chronology

The handoff evidence references 21 deals across pipelines 15 and 17, with recorded amounts from 650,000 to 8,304,000 RUB and lifetimes from 6 to 189 days. Sharding balanced metadata approximately, but candidate examples are not matched by amount, source, pipeline, duration, stage, or activity coverage. Technical detail and procurement progress can therefore track project scope or maturity; customer-initiated contact can track channel capture.

I compared every timestamped candidate evidence/counterexample row with manifest closed_at. None falls after its deal's recorded close. Some summaries mention that a deal was “later lost”; that is retrospective framing and must not enter a snapshot classifier. I did not reopen raw timelines because the handoffs supplied event pointers and no disputed event required adjudication.

## Candidate-level verdicts

| ID | Verdict | Target | Critique |
|---|---|---|---|
| A01 | keep | R01 | Anchor for decision-gate clarity; an approver name alone is insufficient. |
| A02 | keep | R02 | Keep only as the state of the latest buyer-owned milestone. |
| A03 | keep | R03 | Judge application-specific sufficiency, not file count. |
| A04 | keep | R04 | Specificity is labelable; it is not buying intent. |
| A05 | keep | R07 | Atomic but mixed; separate independent initiation from prompted response. |
| A06 | merge | R05 | Live test is one technical validation route. |
| A07 | revise | R06 | Require explicit customer acceptance of bounded scope; one-shard only. |
| A08 | keep | R09 | Merge with buyer-side formal procurement; late-stage only. |
| A09 | revise | R10 | Keep explicit current preference distinct from competitor comparison. |
| A10 | merge | R02 | Repeated slippage is the overdue state of a buyer-owned milestone. |
| B01 | merge | R03 | Duplicate of application-input sufficiency. |
| B02 | keep | R05 | Feasibility status is useful, but 7243 shows it is not sufficient for purchase. |
| B03 | merge | R04 | Fold into actionable technical specificity. |
| B04 | merge | R01 | Duplicate decision-process formulation; 7243 contradicts sufficiency. |
| B05 | keep | R08 | Anchor for comparison on an explicit criterion; mixed direction. |
| B06 | merge | R02 | A dated action belongs in the latest milestone state. |
| B07 | merge | R02 | Keep only repeated missed buyer checkpoints without replacement. |
| B08 | merge | R07 | Duplicate substantive customer initiation; sparse evidence. |
| B09 | merge | R09 | Duplicate formal procurement state; stage-adjacent. |
| C01 | merge | R01 | Duplicate decision-gate clarity; access and timing matter. |
| C02 | merge | R02 | A dated next step is not proof of completion. |
| C03 | merge | R03 | Submission alone is weaker than input sufficiency. |
| C04 | reject | — | Price response is mixed and contradicted in LOST cases. |
| C05 | merge | R08 | Duplicate comparison feature; occurs on both sides. |
| C06 | merge | R05 | Proof request is context; score whether a relevant path resolves fit. |
| C07 | merge | R04 | Specific operating constraints are technical content, not intent. |
| C08 | merge | R01 | External gate status overlaps decision-path clarity. |
| C09 | merge | R07 | Duplicate customer-initiated interaction; capture confound. |
| C10 | merge | R04 | Concrete co-design request overlaps actionable technical content. |

The JSON records the consolidated definitions, Jev anchors, risks, chronology check, and per-entry rationale.
