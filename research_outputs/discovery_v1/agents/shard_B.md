# Shard B — Independent discovery

## Findings

The shard contains strong early buying signals on both sides of the outcome split. LOST deal 7243 had reported general-director approval and price acceptance, and the customer supplied company details for contract preparation. Those signals should not be treated as sufficient indicators on their own.

The clearest candidate for adversarial review is repeated slippage of buyer-owned actions or decisions without a replacement commitment. It appears in LOST 18873 and 7243. WON 18733 also had several postponed internal reviews, so the definition must distinguish missed customer-owned actions from explained review cycles.

Technical fit becoming clear may be useful to track. WON 18635 and 18733 progressed through application-specific clarification; LOST 18873 still lacked a feasible path late in its observed pre-outcome activity. LOST 7243 is a counterexample: production approved a revised option, yet the deal was later lost.

## Candidate catalog

| Candidate | Observed direction | Jev type | Evidence breadth | Main limitation |
|---|---|---:|---:|---|
| Application evidence sufficient to assess fit | Mixed | Boolean | Both groups | Materials were supplied in multiple lost deals |
| Feasible technical path confirmed for requested scope | More in WON | Boolean | 2 WON, 2 LOST | 7243 reached technical approval and still lost |
| Substantive application-specific customer feedback | Mixed | Boolean | Both groups | Questions may indicate fit concerns rather than commitment |
| Buyer-side decision process and stakeholders identified | Mixed | Choice | 2 WON, 1 LOST | 7243 had general-director approval |
| Evidence-backed comparison of alternatives | Mixed | Choice | 1 WON, 2 LOST | Price and scope differences confound the comparison |
| Buyer-owned next action with date and expected result | Mixed | Boolean | 2 WON, 2 LOST | A scheduled call can still fail to produce progress |
| Repeated buyer-owned slippage without replacement commitment | More in LOST | Ordinal | 2 LOST + 2 WON exception checks | Holidays, workload, and technical complexity can mimic it |
| Buyer initiates a substantive follow-up | Mixed | Boolean | 1 WON, 1 LOST | Only two clear examples in this shard |
| Buyer-side formal procurement, legal, or financing step | More in WON | Choice | 2 WON, 1 LOST | Close to outcome; 7243 is a strong counterexample |

Each candidate's definition, Jev question, event-level evidence, counterexamples, confounds, and leakage note are in `shard_B.json`.

## Rejected as standalone signals

- Verbal price acceptance appears in WON and LOST deals.
- A near-term purchase date or urgency appears in both groups and often moves.
- Raw call/message count, duration, deal length, amount, source, pipeline, or token volume.
- Exact dimensions, throughput, and label configuration are structured qualification facts, not semantic classifiers by themselves.

## Evidence handling

I used only the eight shard B deals' `neutral.json` and `clean_timeline.jsonl`, plus the task instructions and shard plan. Terminal stage transitions were used only to bound pre-outcome evidence; I did not use their contents or later events as semantic evidence. Worklog IDs and source activity IDs are supplied for targeted checking.