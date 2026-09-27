# Validation 2A.2 reliability

Two independent Luna Max workers labeled the same 195 frozen event examples using the frozen E01–E06 contract. They received current event plus at most one earlier related event, and no tentative candidate labels or outcome data. Thresholds were declared in `analysis_plan.json` before labeling: overall exact ≥90%, YES agreement ≥85%, NO agreement ≥85%, and at least eight jointly labeled YES plus eight jointly labeled NO examples. YES/NO agreement is 2×joint class matches divided by 2×joint class matches plus split pairs.

| Classifier | N | Both YES | Both NO | Split | Overall | YES agreement | NO agreement | Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| E01 | 34 | 22 | 4 | 8 | 76.5% | 84.6% | 50.0% | Fail |
| E02 | 34 | 9 | 21 | 4 | 88.2% | 81.8% | 91.3% | Fail |
| E03 | 29 | 16 | 10 | 3 | 89.7% | 91.4% | 87.0% | Fail |
| E04 | 24 | 4 | 18 | 2 | 91.7% | 80.0% | 94.7% | Fail: YES coverage and agreement |
| E05 | 31 | 25 | 6 | 0 | 100.0% | 100.0% | 100.0% | Fail: NO coverage |
| E06 | 43 | 31 | 10 | 2 | 95.3% | 96.9% | 90.9% | Pass |

Field comparison among both-YES pairs shows the next bottleneck. Presence agreement was 77.3% for E01 owner, 86.4% for E01 due/result, 92% for E05 role and checkpoint, and 100% for other fields. Exact normalized text agreement among both-present values was E01 action 9.1%, due/result 55.6%; E02 completed action 22.2%; E03 new checkpoint 37.5%; E05 role 82.4%, decision action 16.0%, checkpoint 45.5%. Exact text is a strict proxy, so some differences may be paraphrases; it does demonstrate that the current free-text field contract lacks canonical output rules.

This tests reproducibility of event labeling on a curated benchmark, not prevalence or predictive power across 23 deals. E04 has too few clear YES cases for a reliable positive-class judgment. E05's perfect binary agreement does not establish a reliable NO boundary because only six jointly labeled NO examples were present. One E03 current event appears with two different prior-context events, so those two benchmark records are correlated.
