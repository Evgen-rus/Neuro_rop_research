# Jev Clean Benchmark v2 — J01

## Setup

J01 asks whether one clean customer utterance contains a concrete, checkable technical parameter, constraint, requirement, or question. Two independent Luna Max labelers reviewed 217 source-derived utterances without deal IDs, outcomes, or Jev results. The frozen benchmark contains 42 consensus YES, 50 consensus NO, and 6 disputed references; disputed rows are excluded from agreement. Nineteen selected NO rows contain topical technical wording. All 98 examples were sent once to the official TypeSafe Noul endpoint with only the utterance as `state`, using pinned `jev-1.13.0`. No threshold, label, contract, or membership changed after calls began.

## Results

Agreement for YES and NO below uses the full respective reference-class denominator, so abstentions reduce class agreement. Overall agreement is calculated on covered examples.

| Threshold | Coverage | Overall agreement on covered | YES agreement | NO agreement | FP | FN | Abstain |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 92/92 = 100% | 78/92 = 84.8% | 28/42 = 66.7% | 50/50 = 100% | 0 | 14 | 0 |
| 0.70 | 76/92 = 82.6% | 73/76 = 96.1% | 24/42 = 57.1% | 49/50 = 98.0% | 0 | 3 | 16 |
| 0.80 | 70/92 = 76.1% | 68/70 = 97.1% | 22/42 = 52.4% | 46/50 = 92.0% | 0 | 2 | 22 |
| 0.90 | 51/92 = 55.4% | 51/51 = 100% | 15/42 = 35.7% | 36/50 = 72.0% | 0 | 0 | 41 |

Median latency was 0.474 s; nearest-rank p95 was 0.622 s across all 98 calls. API usage reported 48,366 input tokens and 2,156 output tokens; the response did not report monetary cost. All 98 responses identify model `jev-1.13.0`.

At the full-coverage 0.50 threshold, all 14 errors are false negatives. Six are short or context-dependent consensus YES utterances whose reference boundary is itself debatable; the other eight include concrete constraints or answerable technical questions. The fixed reference labels were not changed after seeing Jev results. See `error_analysis.md` for each utterance, probability, and error type.

## Verdict

**J01 does not pass the predeclared acceptance gate**: YES agreement is 66.7%, below the required 90%, despite 100% NO agreement and at least 40 examples per class. Raising the threshold increases covered-answer agreement by abstaining on many examples and does not establish full-coverage suitability. J01 should not be used as an autonomous semantic sensor on this input contract. This result says nothing about WON/LOST or predictive value.

The local source dataset was read only. No production integration or other Jev classifiers were run.
