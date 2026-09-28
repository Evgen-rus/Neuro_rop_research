# Jev Diagnostic v1 — E06

The saved Jev Benchmark v1 run is A; no A calls were repeated. B translated only event content to English, C added only an explicit speaker field derived from event direction, and D kept the original Russian state while changing Noul to a two-option Choice. All variants used the same 43 IDs and pinned `jev-1.13.0`. The scored subset was 41 Luna-consensus examples (31 YES, 10 NO); two disputed examples were called and reported separately.

## Full-coverage comparison

| Variant | Decision | Coverage | Agreement | YES agreement | NO agreement | FP | FN | Median / p95 latency, s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A — Russian + Noul | p ≥ 0.50 | 41/41 | 36/41 · 87.8% | 29/31 · 93.5% | 7/10 · 70.0% | 3 | 2 | 0.612 / 7.905 |
| B — English + Noul | p ≥ 0.50 | 41/41 | 35/41 · 85.4% | 28/31 · 90.3% | 7/10 · 70.0% | 3 | 3 | 0.495 / 0.709 |
| C — Russian + speaker + Noul | p ≥ 0.50 | 41/41 | 37/41 · 90.2% | 29/31 · 93.5% | 8/10 · 80.0% | 2 | 2 | 0.476 / 0.543 |
| D — Russian + Choice | returned A/B | 41/41 | 36/41 · 87.8% | 29/31 · 93.5% | 7/10 · 70.0% | 3 | 2 | 0.514 / 0.629 |

For A/B/C, the predeclared symmetric bands at 0.70, 0.80 and 0.90 raise accuracy **among decided examples** but lower coverage. For example, at 0.90 A decides 18/41 (100% accurate), B 19/41 (94.7%), and C 16/41 (100%). D is scored by the returned categorical choice at full coverage, without forcing Noul thresholds onto Choice probabilities. `metrics.json` contains coverage, accuracy, class agreement, FP/FN, abstentions, median and p95 latency for every threshold and variant.

## Interpretation

- **Language:** B is one example worse than A at full coverage and retains all five A errors while adding `E06-067`. This run does not support Russian input as the main cause. Translation fidelity was checked before freezing, but translated wording remains a possible confound.
- **Speaker attribution:** C fixes one seller-authored technical email (`E06-193`) without adding a new full-coverage error. NO agreement rises from 70% to 80%, still below the desired 90%. The one-example gain in N=41 is suggestive only; event direction cannot reliably identify speakers inside quoted email threads or multi-turn calls.
- **Question type:** D makes exactly the same five full-coverage errors as A. This run gives no evidence that Noul representation alone explains the boundary.
- **Likely boundary:** The stubborn errors concern short customer technical fragments versus seller-authored technical content and sample logistics. No single tested factor substantially resolves that boundary. This is a small, selected benchmark with only ten consensus NO examples; one NO example changes NO agreement by ten percentage points. These paired results are diagnostic observations, not causal estimates or predictive validation.

The five baseline errors and the single corrected case are in `five_error_matrix.md`; source-grounded analysis is in `error_analysis.md`. Disputed `E06-076`/`E06-077` remain outside the main score. The official [TypeSafe API reference](https://docs.typesafe.ai/api) documents both Noul and Choice, and the [model page](https://docs.typesafe.ai/models) lists the pinned model version. No outcome labels, holdout, dataset edits or production integration were involved. Work stops after A/B/C/D.
