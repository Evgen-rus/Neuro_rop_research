# Validation 2A.2 disagreement audit

Scope: frozen contract, aggregate metrics, disagreement records, and only the cited benchmark examples. This is an audit of disagreement causes, not a relabeling.

## E01 — future customer action

8 of 34 examples split (22 both YES, 4 both NO). The disagreements cluster around what counts as a concrete customer commitment:

- **Speaker/action attribution:** `E01-002` contains a salesperson's promise to send the information; the customer refers to that promise. The correct distinction is seller action versus customer action. `E01-086` has multiple customer actions in one call: a payment plan and a hedged promise to send a company card. B's explanation focuses on the card and overlooks the payment plan, so the example/reason is multi-action and selectively scoped.
- **Availability versus customer work:** `E01-005` and `E01-016` commit only to being free at a stated time. `E01-013` confirms a follow-up call while expecting an evaluation by then. These expose a boundary in whether availability or an expected internal assessment counts as the customer's own action; the call itself is seller-owned.
- **Hedged action wording:** `E01-099` (try to send photos by end of day) and `E01-100` (try to sign this week) pair “try” with a concrete action and deadline. The contract excludes vague “try” language *without* a concrete customer-owned action, so these examples do not cleanly resolve how much hedging alone should count.
- **Unspecified object:** `E01-097` commits to send “everything” after a check, but the object is not identified in the supplied local context.

## E02 — customer reports completed action

4 of 34 examples split (9 both YES, 21 both NO). Main causes are attribution and the threshold for prior agreement:

- `E02-021` says “we entered information” but the message direction is unknown, and the previous event is the seller sending a questionnaire. This is an attribution ambiguity; a seller-completed form is not customer completion.
- `E02-017` reports photos attached after a seller request, and `E02-117` says the company card had already been sent without a supplied prior request/commitment. Both test whether a request or current assertion alone establishes the contract's required prior agreed action.
- `E02-104` answers a seller's request by listing selected container types. The split is whether an answer that performs the requested selection itself establishes completion, despite no explicit “done” statement or customer commitment in the prior event.

## E03 — customer moves an agreed action to a new checkpoint

3 of 29 examples split (16 both YES, 10 both NO). The disagreements concern whether a checkpoint actually changed and which action in a multi-topic event is being judged:

- `E03-036` changes an “today” promise to “after lunch,” which can be read as a more specific checkpoint or merely a restatement of the same day.
- `E03-039` refers to sending a video tomorrow both before and after the cited event; the current note also says preparation was not completed that day. It is unclear from the packet whether the due checkpoint moved or was simply reaffirmed.
- `E03-122` discusses a new conveyor but also says payment is being made today and the first tranche will be this week, earlier than the previous “next week” plan. The payment update is easy to miss when the call is read mainly as a conveyor discussion.

## E04 — customer explicitly missed a promised action

2 of 24 examples split (4 both YES, 18 both NO), with limited YES examples in this sample.

- `E04-046` uses a prior Monday-or-Tuesday meeting window and a current note saying there was no meeting/no information. The packet does not cleanly distinguish missing the meeting from missing the separate promise to report whether it occurred on Monday.
- `E04-137` has no previous event supplied. The current call refers to a Friday discussion about sending photos; the seller says they were not received, and the customer explains the weekend delay. This may establish the miss locally, but it relies on a seller's account of the earlier agreement and the customer's response rather than a supplied prior event.

## E05 field literal agreement

The aggregate metrics show no E05 class-value splits, but literal field agreement is lower: `decision_action` is present in both outputs for 25/25 examples and matches literally in 4/25 (16%); `checkpoint` is present in both for 22 examples and matches in 10/22 (45%); `customer_role` is present in both for 17 and matches in 14/17 (82%). This points to substantial field normalization or specificity drift, especially for action and checkpoint. The permitted inputs do not include per-labeler E05 values, so I cannot determine whether individual differences are wording-only or semantic.

## Benchmark quality flags

- `E03-036`, `E03-039`, and `E04-046` use `comment` events identified by `worklog_id`. Their evidence is an internal worklog summary rather than a customer-sourced event. The summaries already interpret promises and misses, which risks testing agreement with the manager's paraphrase instead of the contract's source-attribution rule. These should be treated as provenance/benchmark-quality concerns, not evidence of outcome leakage.
- `E01-002` is a long multi-turn call where the promised action belongs to the seller; `E01-086` and `E03-122` each bundle multiple customer actions/topics. These packets invite annotators to select different targets unless the relevant action is explicit in the example locator.
- `E02-021` has unknown message direction, and `E04-137` omits the prior event despite relying on a previous agreement. Both limit source attribution or local-context checking.
- `E06-076` is the isolated one-word reply “цилиндрическая” with no previous event. The application/object is not recoverable from the supplied example, so the technical-requirement decision is under-contextualized. `E06-077` is a real boundary case: a statement that labels are applied the same way to all buckets may be checkable, but does not state a specific placement/geometry constraint.

No labels or benchmark records were changed. No deal outcomes or dataset files were consulted.
