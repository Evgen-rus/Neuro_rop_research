# Customer Commitment Cascade v1

## Frozen experiment

C01 asks whether one clean customer utterance explicitly commits a customer-side owner to a concrete future action. The binary contract and `p ≥ 0.70 → YES`, `p ≤ 0.30 → NO`, otherwise Luna Max routing were fixed before Jev calls. No owner/action/deadline extraction was attempted. The source was the audited outcome-blind incoming-message/email pool used in J01, with quote-contaminated, uncertain-source, contact-bearing, and outcome-bearing text excluded. Two independent Luna Max labelers saw only utterances and the C01 contract; a third, fresh Luna Max worker handled the blind fallback.

The clean pool contained 191 utterances. The two reference labelers agreed on 12 YES and 177 NO, with 2 splits. The frozen benchmark contains all 12 consensus YES, 50 source-diverse consensus NO with commitment-boundary wording prioritized, and both disputed utterances. Disputed examples received Jev probabilities but are excluded from the primary score. **The target of at least 50 consensus YES was not met.** No artificial positives or unreliable mixed-speaker call fragments were added.

## Results on 62 consensus examples

| Mode | Overall | YES | NO | TP / TN / FP / FN | Jev / Luna routed | Luna calls avoided |
|---|---:|---:|---:|---|---:|---:|
| Jev-only at 0.50 | 59/62 = 95.2% | 11/12 = 91.7% | 48/50 = 96.0% | 11 / 48 / 2 / 1 | 62 / 0 | — |
| Frozen cascade 0.70 / 0.30 | 60/62 = 96.8% | 11/12 = 91.7% | 49/50 = 98.0% | 11 / 49 / 1 / 1 | 55 / 7 | 55/62 = 88.7% |

The cascade made one confident Jev error and one Luna fallback error. Fallback rescued one original Jev error. With a perfect fallback, confident Jev routing would cap agreement at 61/62 = 98.4%. All 62 consensus examples receive a final YES/NO answer. Median Jev latency across all 64 frozen calls was 0.474 s. API usage reported 29,628 input and 1,408 output tokens; no Luna latency or comparable monetary charge was measured.

## Verdict

The cascade **passes the predeclared numerical metric gates** (overall ≥95%, YES ≥90%, NO ≥90%, Luna-call reduction ≥60%) on this frozen subset. It **does not satisfy the benchmark size target**: only 12 independent consensus YES examples were available, far below 50. One positive case changes YES agreement by 8.3 percentage points. The two final errors also involve utterances near the commitment-versus-plan/decision boundary. Therefore C01 is **provisionally encouraging, not established as a practically reliable sensor**. A larger clean positive set and fresh frozen evaluation would be needed before a stronger conclusion. This study did not use outcomes, test predictive power, build R02, or change production.
