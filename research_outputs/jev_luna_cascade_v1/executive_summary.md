# Jev → Luna Cascade Benchmark v1

## Frozen setup

J01 `CHECKABLE_CUSTOMER_TECH_FACT` was evaluated on the 92 consensus utterances from Jev Clean Benchmark v2 (42 YES, 50 NO). Six disputed references were excluded. The J01 contract and membership stayed fixed. Saved `jev-1.13.0` probabilities were reused; no new Jev calls were made. One fresh, independent Luna Max worker labeled the 21-example union of fallback sets while seeing only the customer utterance and frozen J01 contract. Its labels were then used for both modes. The primary mode was fixed at YES ≥0.70, NO ≤0.30 before the Luna run. The secondary mode was YES ≥0.80, NO ≤0.20.

## Results

| Mode | Overall | YES | NO | TP / TN / FP / FN | Jev / Luna routed | LLM calls avoided | Jev / Luna errors | Original Jev errors saved | Oracle ceiling |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 0.70 / 0.30 primary | 89/92 = 96.7% | 39/42 = 92.9% | 50/50 = 100% | 39 / 50 / 0 / 3 | 76 / 16 | 76/92 = 82.6% | 3 / 0 | 11 | 89/92 = 96.7% |
| 0.80 / 0.20 secondary | 90/92 = 97.8% | 40/42 = 95.2% | 50/50 = 100% | 40 / 50 / 0 / 2 | 71 / 21 | 71/92 = 77.2% | 2 / 0 | 12 | 90/92 = 97.8% |

Both modes cover all 92 examples with a final YES/NO answer. The main mode meets the predeclared ≥95% overall, ≥90% YES, ≥90% NO, and ≥60% LLM-call-reduction gates. The secondary mode is a comparison, not a retrospectively selected replacement.

## Baselines and cost

Jev alone at 0.50 agreed on 78/92 (84.8%). The prior two Luna Max labelers agreed on the 92 selected consensus examples and disputed six other selected examples. That agreement informed the reference subset; it is **not** a 92-call Luna-only production benchmark or an independent accuracy estimate against external truth. No 92-call Luna-only run was commissioned.

The primary cascade would require 92 Jev decisions plus 16 Luna calls, compared with 92 Luna calls for a Luna-only route: 76 Luna calls avoided (82.6%). The secondary route uses 21 Luna calls and avoids 71 (77.2%). The saved Jev run actually made 98 calls including six disputed examples; the 92-call figures above describe the scored subset and a prospective route. Median observed Jev latency in the saved run was 0.474 s. Luna fallback latency and reliable monetary prices were unavailable, so end-to-end latency and currency savings are not estimated.

## Error boundary and verdict

The primary mode has three false negatives, all confident Jev NO decisions; Luna cannot repair them. They concern a viscosity range (`p=0.30`), an applicator arrangement question (`p=0.18`), and an elliptical description of complex oval shapes (`p=0.10`). The latter two remain errors in the secondary mode. No Luna fallback errors were observed in this small selected set. The oracle ceilings equal actual agreement here because the fallback labels matched the consensus references on every routed example.

**Verdict: practically promising on this frozen J01 benchmark under the predefined acceptance gate.** This is a selected, consensus-only utterance benchmark with 42 YES and 50 NO; it does not establish production readiness, predictive value, prevalence, or monetary savings. Confident Jev false negatives remain the limiting failure mode. No outcome labels, holdout, threshold fitting, prompt experiments, or production integration were used.
