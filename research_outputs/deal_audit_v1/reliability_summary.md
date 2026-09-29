# Semantic reliability: paired deal audits

## Scope

Compared all 23 frozen A/B pairs across seven fields (161 comparisons). Ratings allow semantic equivalence without requiring literal wording. The canonical B audit for 19007 is the fresh replacement. No outcomes were accessed or predicted.

| Field | AGREE | PARTIAL | DISAGREE |
|---|---:|---:|---:|
| Primary explanation | 13 | 10 | 0 |
| Controllability | 19 | 4 | 0 |
| Turning point | 5 | 18 | 0 |
| Manager influence | 8 | 15 | 0 |
| Manager weakness | 4 | 13 | 6 |
| Positive customer signal | 12 | 10 | 1 |
| Negative customer signal | 7 | 15 | 1 |

## Interpretation

The runs most often agree on the broad trajectory and controllability. Partial agreement is common for turning points and manager influence because the runs select different late events or apply different thresholds to whether manager action could materially change the path. Manager-weakness judgments are least stable: six pairs disagree, usually because one audit records no weakness while the other identifies a qualified process gap. These are descriptive reproducibility results, not causal or predictive validation.

## Claim and pointer checks

- **18485:** B's primary evidence list repeats e5 and omits e4, the listed counsel-approval event; its external-fund framing is not clear in the cited evidence.
- **18629:** B's primary describes early price as acceptable, but its cited evidence does not clearly record customer acceptance.
- **18635:** A:e14 and B:e5 point to event 627315 on July 22, 2026, but the audit paraphrases differ on payment/document status.
- **18733:** B's positive-signal sentence cites e0/e1/e3 for photos, competitor discussion, and company/legal information; the competitor-comparison email is e2 and the cited paraphrases do not support every detail.
- **18745:** B attributes payment-reminder irritation to a manager worklog; A:e15 is a direct customer request to stop repeated inquiries.
- **18755:** B discusses manager-reported price comparison in its primary explanation but omits the price worklog, B:e7, from the primary evidence indices. No customer price objection is confirmed.
- **18765 and 18773:** Message sender direction differs or is left unknown between the audits; retain uncertainty about who made the statement.
- **18929:** B's positive customer signal uses manager-log status at e1; A distinguishes that from the direct procurement email.
- **6885:** A:e13 and B:e10 cite the same event_id 533935 on February 20, 2026, but give conflicting paraphrases: expected payment versus inability to reach the director.

## Independence and limits

- The A runs for **5971, 6135, and 18485** had prior source-preprocessing exposure, as recorded in the paired freeze; interpret those comparisons cautiously.
- **19007 B** is the fresh replacement audit. The excluded original B audit was not read.
- SHA-256 hashes for the schema and 46 canonical audits matched the paired freeze. Structured evidence indices in primary explanations and turning points were in range.
- This compares audit outputs only. It does not re-check source truth or establish outcome, causal, or predictive claims.
