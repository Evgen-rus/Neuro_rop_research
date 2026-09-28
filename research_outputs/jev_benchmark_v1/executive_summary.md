# Jev Benchmark v1 — E06

One live run of the official TypeSafe `jev-1.13.0` Noul API completed for all 43 frozen E06 examples. The scored consensus subset is 41 examples: 31 reference YES and 10 reference NO. The two Luna-disputed examples were called but excluded from the main score. The E06 contract, examples, IDs and thresholds were unchanged.

The threshold rule was fixed before calls: YES when `p >= t`, NO when `p <= 1-t`, otherwise abstain. Class agreement below uses **all** examples of that reference class as denominator, so abstentions reduce it. Accuracy uses only decided examples.

| Threshold | Decided / coverage | Accuracy on decided | YES agreement | NO agreement | FP / FN | Abstained |
|---|---:|---:|---:|---:|---:|---:|
| 0.50 | 41/41 · 100% | 87.8% | 93.5% | 70.0% | 3 / 2 | 0 |
| 0.70 | 32/41 · 78.0% | 93.8% | 77.4% | 60.0% | 0 / 2 | 9 |
| 0.80 | 29/41 · 70.7% | 96.6% | 71.0% | 60.0% | 0 / 1 | 12 |
| 0.90 | 18/41 · 43.9% | 100% | 51.6% | 20.0% | 0 / 0 | 23 |

At 0.50, the five errors are `E06-075` and `E06-078` (customer technical fragments judged NO), plus `E06-179` (sample logistics) and `E06-192`/`E06-193` (technical content authored by the seller) judged YES. This is a substantive boundary issue around who states a requirement and whether technical context alone suffices. See `error_analysis.md` for event evidence. Disputed `E06-076` and `E06-077` received probabilities 0.20 and 0.24, without contributing to accuracy.

Probability range on the 41 scored examples: 0.03–0.96, median 0.81. End-to-end request latency across 43 calls: median 0.612 s, nearest-rank p95 7.905 s, maximum 9.181 s. API usage: 57,671 input and 946 output tokens. The API response did not report a billed amount; at the [published input price](https://docs.typesafe.ai/models) of $0.042 per million tokens, input usage corresponds to about $0.00242 before any account-specific terms.

**Verdict: E06 is not ready for the next stage as an autonomous classifier.** The desired ≥90% agreement for both reference classes is not met: NO agreement is 70% at full coverage, while higher thresholds abstain on many NO examples. Revise the customer-source and technical-context boundary, then run a separately frozen benchmark; do not choose a threshold from this run and present it as preselected. This result measures event-level agreement on a curated set, not prediction of deal outcomes.
