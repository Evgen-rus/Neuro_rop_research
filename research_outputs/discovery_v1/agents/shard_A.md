# Shard A — independent discovery

## Scope

Four WON and four LOST cases from the assigned shard. Outcome labels came from the shard plan and were kept separate from timeline text. Read only each assigned deal’s `neutral.json` and `clean_timeline.jsonl`.

## Findings

The clearest candidate contrast is whether a concrete purchase/technical next step gets completed and the requirement set narrows enough for a decision. Director approval and contract movement appear in WON cases, but neither price acceptance, near-term intent, technical activity, nor customer samples alone separate outcomes. 18615 and 7601 are useful repeat-pipeline counterexamples: both involved extended technical work and alternatives, while only 18615 reached an explicit supplier preference and contract path.

## Candidate catalog

| ID | Candidate | Direction | Jev type | Evidence breadth | Main counterexample / caveat | Leakage |
|---|---|---|---|---|---|---|
| A01 | Explicit decision path with an owner and milestone | more_in_won | ordinal | 3 WON / 2 LOST examples | 18775: Customer calls himself the decision maker, yet the actual purchasing contact remains unnamed and the next step does not materialize. | medium |
| A02 | Customer completes an agreed next step | more_in_won | ordinal | 3 WON / 2 LOST examples | 7601: Customer did ship physical product samples, but the evaluation exposed a two-machine configuration and the project did not progress to a purchase decision. | low |
| A03 | Technical inputs are usable for a specific solution | more_in_won | ordinal | 3 WON / 2 LOST examples | 7601: Customer supplied physical samples, yet the samples revealed a scope/configuration mismatch and did not secure a purchase. | low |
| A04 | Customer raises specific, actionable technical questions | more_in_won | boolean | 3 WON / 2 LOST examples | 7601: Customer sends detailed technical questions and requests printer and table changes, yet the solution remains unacceptable. | low |
| A05 | Customer initiates substantive follow-up | mixed | boolean | 3 WON / 2 LOST examples | 7601: Substantive customer initiative is present in a LOST case. | low |
| A06 | A live product-fit validation is completed | more_in_won | choice | 2 WON / 2 LOST examples | 7601: Receipt of samples alone is not evidence that the customer accepted the test result or the configuration. | medium |
| A07 | The customer and seller converge on a bounded configuration | more_in_won | ordinal | 3 WON / 3 LOST examples | 18615: This WON case also had substantial scope changes; convergence occurred later, so early instability alone should not be labeled negative. | medium |
| A08 | Customer advances contract or procurement paperwork | more_in_won | ordinal | 3 WON / 2 LOST examples | 7601: Printing and discussing a proposal is not equivalent to customer-led contractual progress. | high |
| A09 | Customer states a current preference after comparing alternatives | more_in_won | choice | 2 WON / 1 LOST examples | 18615: This eventual WON case spent weeks awaiting a China comparison and focusing on price; comparison activity itself is not negative. | medium |
| A10 | Repeated postponement without new customer-owned evidence | more_in_lost | ordinal | 2 WON / 2 LOST examples | 18615: A WON project also had long waiting periods; it continued to produce customer-owned technical and management milestones. | low |

## Evidence and labeling notes

### A01 — Explicit decision path with an owner and milestone

The customer identifies who must approve or review the purchase, what that person or group will do, and a concrete expected decision or feedback point.

**Jev question:** Is the next purchase decision step tied to an identified customer role and an expected time or deliverable?  
**Observable:** After qualification, once the customer describes internal approval; classify only from statements made by the snapshot time.  
**Notes:** The usable pattern is an observable process with a responsible role and a dated/actionable milestone, not a generic claim that the customer is the decision maker.

**WON evidence**
- `6885` · `2026-01-30T00:00:00+03:00` · `comment` · `worklog_id=2487593` — Director is the decision maker; customer says they are leaning to this offer and expects to decide that day.
- `5017` · `2025-08-26T00:00:00+03:00` · `comment` · `worklog_id=2189423` — Contract is with the general director for review; customer says it is acceptable and plans to sign.
- `18615` · `2026-07-22T00:00:00+03:00` · `comment` · `worklog_id=2859569` — Only this supplier is under consideration at that point; customer will discuss with the director and report the purchase decision the next day.

**LOST evidence**
- `7601` · `2026-06-09T00:00:00+03:00` · `comment` · `worklog_id=2660309` — The customer has shown the offer to the mechanic but not yet to leadership; the leadership review is deferred.
- `18775` · `2026-08-04T00:00:00+03:00` · `comment` · `worklog_id=2947271` — Customer says procurement will contact the seller but cannot identify which of four buyers or provide a direct contact.

**Counterexamples**
- `18775` · `2026-08-04T00:00:00+03:00` · `comment` · `worklog_id=2947271` — Customer calls himself the decision maker, yet the actual purchasing contact remains unnamed and the next step does not materialize.

**Possible confounds**
- Manager worklogs summarize the customer process and may overstate certainty.
- A short, one-person purchase can have a clear decision path without a named committee.

### A02 — Customer completes an agreed next step

A mutually agreed customer action (visit, review, document, technical answer) occurs or is delivered by the stated checkpoint.

**Jev question:** By the current snapshot, has the customer completed the last specific next step they committed to?  
**Observable:** At each meaningful checkpoint after a customer commitment; distinguish not yet due from overdue.  
**Notes:** Potentially strong if defined around the last customer-owned commitment and not raw follow-up counts.

**WON evidence**
- `5017` · `2025-08-21T00:00:00+03:00` · `comment` · `worklog_id=2189423` — Customer attended the agreed factory visit and completed a product run on the equipment.
- `18615` · `2026-07-17T00:00:00+03:00` · `comment` · `worklog_id=2859569` — Customer supplied visitor names and attended the previously arranged factory visit.
- `18485` · `2026-06-17T00:00:00+03:00` · `comment` · `worklog_id=2820563` — After the agreed offer review, customer returned the completed questionnaire and production approved the specified equipment.

**LOST evidence**
- `18747` · `2026-07-31T00:00:00+03:00` · `comment` · `worklog_id=2940187` — Customer again moves the promised measurements to a later date; on Aug 5 the dimensions are still missing.
- `18765` · `2026-08-17T00:00:00+03:00` · `comment` · `worklog_id=2946247` — Customer asks to return to the proposal the following week; the Aug 25 discussion still has no actionable description of the rejected block.

**Counterexamples**
- `7601` · `2026-05-26T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Customer did ship physical product samples, but the evaluation exposed a two-machine configuration and the project did not progress to a purchase decision.
- `5017` · `2025-08-08T00:00:00+03:00` · `comment` · `worklog_id=2189423` — The customer rescheduled the planned factory visit before later attending; a single moved date should not count as a negative pattern.

**Possible confounds**
- Different action difficulty: a sample shipment or multi-department review takes longer than a simple call.
- Date-only worklogs limit day-level precision.

### A03 — Technical inputs are usable for a specific solution

The customer provides the measurements, samples, or other requirements needed to select a concrete configuration, rather than only a broad description or incomplete images.

**Jev question:** Are the customer-provided technical inputs sufficient to define the proposed configuration at this snapshot?  
**Observable:** During discovery and before a final technical proposal; use only requirements known by the snapshot.  
**Notes:** Define sufficiency against the chosen use case; count of files or samples is not itself a feature.

**WON evidence**
- `18485` · `2026-06-17T00:00:00+03:00` · `comment` · `worklog_id=2820563` — Production approved the equipment after the customer sent the requested product details and the seller resolved open questions.
- `5017` · `2025-08-25T11:41:33+03:00` · `message` · `source_ids=2232225,2232227` — Customer sends a corrected questionnaire/file after the precise missing package height is identified.
- `6885` · `2026-01-27T00:00:00+03:00` · `comment` · `worklog_id=2487593` — Customer supplies container images and dimensions for the requested conveyor and printer configuration.

**LOST evidence**
- `18747` · `2026-07-30T13:17:19+03:00` · `call_transcript` · `activity_id=634319` — Seller explains that the received images lack container and cap dimensions, so production cannot provide a solution.
- `18775` · `2026-07-30T10:42:47+03:00` · `call_transcript` · `activity_id=633993` — Customer resists sending measurements for a broad range of label sizes; the exact data required for a reliable quote remains unresolved.

**Counterexamples**
- `7601` · `2026-05-26T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Customer supplied physical samples, yet the samples revealed a scope/configuration mismatch and did not secure a purchase.
- `18775` · `2026-07-29T14:38:41+03:00` · `message` · `source_ids=2947085,2947087,2947093,2947097,2947105` — Customer quickly sends several images early in the process, but later declines the requested detailed size set.

**Possible confounds**
- Product complexity and number of formats determine how much data is needed.
- The worklog may conflate seller requests with actual customer-supplied artifacts.

### A04 — Customer raises specific, actionable technical questions

The customer names a concrete uncertainty or required change that the seller can answer or reflect in the offer.

**Jev question:** Has the customer raised a specific, answerable technical or commercial question and engaged in resolving it?  
**Observable:** During proposal review and technical scoping.  
**Notes:** The candidate is specificity plus engagement in resolution, not merely the presence or count of questions.

**WON evidence**
- `6885` · `2026-02-03T15:25:39+03:00` · `call_transcript` · `activity_id=528319` — After a director review, the customer asks detailed questions about conveyor length and product separation.
- `18485` · `2026-06-19T11:21:17+03:00` · `call_transcript` · `activity_id=605831` — Customer initiates a call to request adding a printer and two cartridges to the contract specification.
- `18615` · `2026-08-19T13:42:56+03:00` · `message` · `source_ids=3014293,3014295` — Customer asks whether the equipment supports larger caps and whether that capability is included in the configuration.

**LOST evidence**
- `18765` · `2026-08-25T15:06:07+03:00` · `call_transcript` · `activity_id=653181` — Customer says a block is unsuitable but cannot specify which block or the needed change.
- `18747` · `2026-07-30T13:17:19+03:00` · `call_transcript` · `activity_id=634319` — Customer still cannot provide dimensions needed to resolve the equipment fit.

**Counterexamples**
- `7601` · `2026-06-15T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Customer sends detailed technical questions and requests printer and table changes, yet the solution remains unacceptable.

**Possible confounds**
- Question frequency can reflect configuration complexity, not buying intent.
- Manager summaries may selectively log questions.

### A05 — Customer initiates substantive follow-up

Customer independently reopens the discussion with a purchase-related question, requested change, or concrete next action.

**Jev question:** Has the customer initiated a substantive follow-up about the purchase since the last seller contact?  
**Observable:** Any time after initial qualification; exclude acknowledgements, missed-call notices, and file receipts.  
**Notes:** Atomic and labelable, but this shard shows no clear direction; retain only as a validation lead if other shards corroborate.

**WON evidence**
- `6885` · `2026-02-03T15:25:39+03:00` · `call_transcript` · `activity_id=528319` — Customer calls the seller and raises questions from the director meeting.
- `18485` · `2026-06-19T11:21:17+03:00` · `call_transcript` · `activity_id=605831` — Customer calls to request a concrete contract-specification change.
- `18615` · `2026-07-23T10:48:51+03:00` · `message` · `source_ids=2905711,2905713` — Customer asks the seller to call after a missed call while the purchase decision is being discussed.

**LOST evidence**
- `7601` · `2026-05-13T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Customer requests a call with their engineer and shares the contact, but the project later stalls.
- `18775` · `2026-07-29T14:38:41+03:00` · `message` · `source_ids=2947085,2947087,2947093,2947097,2947105` — Customer responds to the initial request with product images, but does not sustain later technical follow-through.

**Counterexamples**
- `7601` · `2026-05-13T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Substantive customer initiative is present in a LOST case.

**Possible confounds**
- Visibility depends on the completeness of message/call capture.
- Customer role and deal complexity affect who initiates contact.

### A06 — A live product-fit validation is completed

Customer participates in a real equipment demonstration or test using the relevant product/container and receives an observable result.

**Jev question:** What is the most advanced completed product-fit check: none, samples sent, test/demo completed, or test accepted?  
**Observable:** After a test or visit has occurred and before a purchase decision.  
**Notes:** Keep the stages separate: a planned visit or shipped samples are not a completed, accepted validation.

**WON evidence**
- `5017` · `2025-08-21T00:00:00+03:00` · `comment` · `worklog_id=2189423` — Customer attended the factory and successfully ran the product on the equipment.
- `18615` · `2026-07-17T00:00:00+03:00` · `comment` · `worklog_id=2859569` — Customer and colleagues completed a factory visit described as successful; follow-up focused on final container changes.

**LOST evidence**
- `7601` · `2026-05-26T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Samples arrived for testing, but the proposed fit required a second machine and did not match the requested universal setup.
- `18775` · `2026-08-14T11:51:50+03:00` · `message` · `source_ids=2998019,2998021` — Seller invites the customer to inspect live equipment, but no visit is recorded in this shard.

**Counterexamples**
- `7601` · `2026-05-26T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Receipt of samples alone is not evidence that the customer accepted the test result or the configuration.

**Possible confounds**
- Only two WON cases in this shard have a recorded in-person validation.
- Higher complexity can make testing more necessary and correlate with longer deal cycles.

### A07 — The customer and seller converge on a bounded configuration

The active use case and machine configuration narrow to a specific set of required formats/features that the customer accepts for evaluation.

**Jev question:** How bounded is the currently accepted configuration: unresolved broad range, narrowed with open exceptions, or explicitly accepted?  
**Observable:** After technical scoping and before commercial close; allow later changes if they are explicit and accepted.  
**Notes:** Score the current accepted scope, not the raw number of requested formats or later implementation changes.

**WON evidence**
- `6885` · `2026-02-04T00:00:00+03:00` · `comment` · `worklog_id=2487593` — Customer receives answers to its questions, a specific divider addition is priced, and payment terms are agreed.
- `18485` · `2026-06-19T00:00:00+03:00` · `comment` · `worklog_id=2820563` — Customer-requested printer and cartridge additions are incorporated into a revised contract specification.
- `18615` · `2026-08-10T13:38:03+03:00` · `call_transcript` · `activity_id=643193` — Customer explicitly narrows the current project to equipment for the screw cap after other container variants remain unresolved.

**LOST evidence**
- `7601` · `2026-06-05T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Customer insists on one universal machine and rejects the two-machine alternative.
- `18747` · `2026-07-28T12:31:48+03:00` · `call_transcript` · `activity_id=631497` — Customer explains that container sizes may change and the relevant format is still unclear.
- `18765` · `2026-08-25T15:06:07+03:00` · `call_transcript` · `activity_id=653181` — Customer says the configuration is unsuitable but does not identify the block or define the required configuration.

**Counterexamples**
- `18615` · `2026-08-10T13:38:03+03:00` · `call_transcript` · `activity_id=643193` — This WON case also had substantial scope changes; convergence occurred later, so early instability alone should not be labeled negative.

**Possible confounds**
- Product range and project complexity drive scope breadth.
- A narrowed scope can be seller-imposed or omit real customer needs unless acceptance is explicit.

### A08 — Customer advances contract or procurement paperwork

The customer reviews, edits, approves, or returns purchase paperwork rather than only receiving a seller-prepared offer.

**Jev question:** What is the customer-side document state: not started, under customer review, customer edits/approvals exchanged, or signed/returned?  
**Observable:** Only after a formal offer or draft agreement exists.  
**Notes:** Jev-labelable, but low priority for early snapshots because paperwork is adjacent to outcome.

**WON evidence**
- `18485` · `2026-06-25T00:00:00+03:00` · `comment` · `worklog_id=2836011` — Customer obtains lawyer approval, requests a tax certificate, and the parties proceed to the electronic contract and invoice.
- `6885` · `2026-02-12T00:00:00+03:00` · `comment` · `worklog_id=2487593` — Customer returns a formal disagreement protocol for specific delivery clauses; revisions are later accepted.
- `5017` · `2025-08-28T13:01:28+03:00` · `message` · `source_ids=2240865` — Customer reports that the contract has been signed and is being scanned.

**LOST evidence**
- `7601` · `2026-06-17T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Offer is printed for internal review, but customer has not moved into contract paperwork.
- `18775` · `2026-08-04T00:00:00+03:00` · `comment` · `worklog_id=2947271` — Project remains at procurement-contact coordination and sample/testing discussion; no contract action is recorded.

**Counterexamples**
- `7601` · `2026-06-17T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Printing and discussing a proposal is not equivalent to customer-led contractual progress.

**Possible confounds**
- This is late-stage and strongly correlated with deal progression; it may be a status marker rather than an early semantic feature.
- Legal, funding, and e-signature procedures differ by customer.

### A09 — Customer states a current preference after comparing alternatives

The customer explicitly says which option they currently prefer and grounds the preference in an identified selection criterion.

**Jev question:** Has the customer stated a current preferred supplier or offer after comparison: none, several remain, this offer leads, or selected?  
**Observable:** After the customer has evaluated or discussed alternatives.  
**Notes:** Measure explicit customer-reported preference, not the presence or absence of competitors.

**WON evidence**
- `6885` · `2026-01-30T11:40:49+03:00` · `call_transcript` · `activity_id=527197` — Customer says the director is considering only this supplier and will report the decision.
- `18615` · `2026-07-22T00:00:00+03:00` · `comment` · `worklog_id=2859569` — Customer says the project is currently considering only this company after prior comparisons.

**LOST evidence**
- `7601` · `2026-06-02T00:00:00+03:00` · `comment` · `worklog_id=2660309` — Customer is still exploring other companies and has not decided whether a universal solution fits.

**Counterexamples**
- `18615` · `2026-05-27T00:00:00+03:00` · `comment` · `worklog_id=2859569` — This eventual WON case spent weeks awaiting a China comparison and focusing on price; comparison activity itself is not negative.
- `18775` · `2026-08-04T00:00:00+03:00` · `comment` · `worklog_id=2947271` — A self-reported decision maker may still depend on an unidentified procurement group; a verbal preference needs a concrete basis.

**Possible confounds**
- Seller worklogs may overstate customer preference.
- A declared preference can be temporary and may precede technical fit or internal approval.

### A10 — Repeated postponement without new customer-owned evidence

The customer repeatedly moves a promised decision or information step while no new artifact, accountable owner, or completed internal review appears.

**Jev question:** How many consecutive customer-owned milestones have been postponed without a new artifact or a named owner/date?  
**Observable:** Across repeated follow-up cycles before outcome; ignore one reschedule when the new commitment is completed.  
**Notes:** Atomic only if based on successive missed commitments and absence of new customer-owned evidence, not elapsed duration or contact counts.

**WON evidence**
- `18615` · `2026-06-05T00:00:00+03:00` · `comment` · `worklog_id=2859569` — Purchase is deferred while waiting for a supplier comparison and the product placement issue; customer gives a future checkpoint and remains technically engaged.
- `5017` · `2025-08-08T00:00:00+03:00` · `comment` · `worklog_id=2189423` — Customer moves the visit date but later completes the visit and test.

**LOST evidence**
- `18747` · `2026-07-31T00:00:00+03:00` · `comment` · `worklog_id=2940187` — Measurements are moved again, after prior promised dates; dimensions remain unavailable on Aug 5.
- `18765` · `2026-08-17T00:00:00+03:00` · `comment` · `worklog_id=2946247` — Customer postpones technical feedback to the next week; by Aug 25 the claimed mismatch is still not specified.

**Counterexamples**
- `18615` · `2026-06-05T00:00:00+03:00` · `comment` · `worklog_id=2859569` — A WON project also had long waiting periods; it continued to produce customer-owned technical and management milestones.

**Possible confounds**
- Long procurement cycles, travel, staff leave, or project urgency can create delays unrelated to intent.
- Must distinguish a postponed but completed milestone from a repeated non-specific deferral.

## Explicit standalone rejections

- **Price acceptance / quoted budget fit:** Appears in early worklogs for WON and LOST cases, including 18747 and 18775; not a standalone separator.
- **Near-term purchase intent:** The same generic near-term wording appears in both outcome groups; 18615 and 7601 show that stated intent can coexist with extended or stalled processes.
- **Technical detail, photos, or samples by themselves:** Present in both groups; 7601 sent extensive samples and 18775 sent many images, yet scope or follow-through remained unresolved.
- **Number of calls/messages, duration, amount, source, pipeline, raw token volume, final stage/reason:** Explicitly excluded as standalone semantic features by task instructions.

## Risks

- Only four deals per outcome in this shard; observations are hypotheses, not effect estimates.
- Most manager_worklog records are date-only and marked year_inferred; pair the date with worklog_id and do not infer within-day order from these entries.
- Some 18615 worklog entries predate its neutral.json created_at; this may reflect pre-opportunity history. Prefer post-creation evidence for snapshot studies and verify the timeline policy during synthesis.
- Sales-manager summaries and call transcription may omit customer context or compress uncertainty.
- Contract movement and expressed supplier preference can be outcome-adjacent; keep late-snapshot leakage risk explicit.

## Files

- `research_outputs/discovery_v1/agents/shard_A.json`
- `research_outputs/discovery_v1/agents/shard_A.md`
