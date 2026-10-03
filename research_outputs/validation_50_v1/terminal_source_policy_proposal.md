# Terminal source policy proposal

**Status:** complete reviewable proposal; user decision required; nothing applied. Raw source rows remain unchanged.

Approved by the user on2026-10-02: "Применить предложенную обработку и продолжить (рекомендую)". The reviewed JSON remains a historical proposal; approval and executable pins are in `terminal_source_policy.json`. Pre-policy inputs saved in `stage3_pre_source_policy_v5/`;11 exposed drafts archived. Rebuild and validation are in progress.

Dry-run affects20 of50 deals, removes71 of3028 view events, and requires fresh audits for11 of34 active drafts. All28 decision-bearing source pins/content hashes match their canonical rows. The primary recomputed every removed reference from canonical source_line, correcting the appended dry-run's reduced-view physical-line numbering. Source inputs remain unchanged.

## Proposed rule

Keep the raw 50-deal inputs. Propose quarantining a whole mutable comment when later embedded terminal dates/status cannot safely be assigned to its `CREATED` timestamp. The bounded version check covers four cited comments and found no captured update/version timestamp for them; it cannot date the later edit. For a credible terminal claim with no reliable hour, use the start of its claim day (`+03:00`) as the conservative cutoff. This can remove earlier same-day communication or later dates before a precise confirmation; it does not make that communication contradictory. Where a direct, precisely timed confirmation exists, show its timestamp as a separate, less conservative alternative. A pending event on the same date is not by itself a contradiction.

Date-only manager worklogs remain unverified manager claims. A claim that payment was conducted may set a proposed chronology boundary, but it does not prove bank receipt or settled funds. A payment instruction/order alone is not a completed-payment claim. Signature or payment-order evidence alone therefore does not establish completed settlement; retain the signature-only controls.

## Dry-run impact

| Deal | Proposed conservative cutoff / quarantine | Removed | Remaining | Precise alternative |
|---|---|---:|---:|---|
| 18523 | 2026-06-19 00:00+03; quarantine line 3, `crm_timeline_comment:2829363` | 11/24 | 13 | — |
| 18533 | 2026-06-24 00:00+03; quarantine lines 6 and 19, comments `2832051` and `2833523` | 2/15 | 13 | — |
| 18865 | Quarantine line 28, `crm_timeline_comment:2990679`; no cutoff | 1/37 | 36 | Retain line 40 direct call `646059` (deferred purchase, not terminal) |
| 18357 | 2026-06-04 00:00+03; earlier comment `2794179` has uncertain edit timing | 10/36 | 26 | 2026-06-04 14:12:29+03, direct call `595711`: 2 removed, 34 remain |
| 7221 | 2026-04-20 00:00+03; date-only worklog `2553847:0` | 3/34 | 31 | 2026-04-24 13:25:49+03, direct call `562169`: 2 removed, 32 remain |
| 7619 | 2026-05-25 00:00+03; date-only worklog `2685341:0` | 10/89 | 79 | 2026-05-25 16:36:53+03, direct call `586483`: 2 removed, 87 remain |
| 7567 | Exact-row quarantine proposal: canonical source lines 393 and 394 | 2/383 | 381 | Project linkage remains unproved; no deal-wide cutoff |
| 7137 | 2026-04-15 00:00+03; date-only worklog `2533067:0` | 1/76 | 75 | — |
| 7543 | 2026-04-24 00:00+03; date-only worklog `2645149:0` | 1/18 | 17 | — |
| 7639 | 2026-05-07 00:00+03; date-only worklog `2694477:0` | 2/52 | 50 | — |
| 18283 | 2026-06-15 00:00+03; date-only worklog `2742403:0` | 4/70 | 66 | — |
| 18339 | 2026-06-11 00:00+03; date-only worklog `2758835:0` | 4/41 | 37 | — |
| 18385 | 2026-06-16 00:00+03; date-only worklog `2787353:0` | 4/72 | 68 | — |
| 18845 | 2026-09-25 00:00+03; date-only worklog `2980259:0` | 1/88 | 87 | — |
| 18925 | 2026-09-25 00:00+03; date-only worklog `3026977:0` | 1/26 | 25 | — |
| 6791 | 2026-05-14 00:00+03; date-only worklog `2468671:0` | 4/198 | 194 | — |
| 6999 | 2026-03-27 00:00+03; worklog `2507023:0` claims payment action; receipt not established | 4/110 | 106 | — |
| 7035 | 2026-03-02 00:00+03; date-only worklog `2511097:0` | 3/62 | 59 | — |
| 7107 | 2026-03-13 00:00+03; worklog `2527525:0` claims payment action; receipt not established | 1/50 | 49 | — |
| 6351 | 2026-05-28 11:26:04+03; direct whole-project closure call `589631` | 2/60 | 58 | — |

For 18357 and 7619, the conservative date boundary removes eight additional same-day rows compared with the precisely timed call. For 7221, the conservative boundary starts April 20, four days before the exact April 24 call; it removes 3 view rows versus 2 under the precise cutoff and excludes the intervening date interval. These are chronology-policy effects, not proof that earlier communication contradicts the later confirmation. The cited source rows and removed event refs are listed in the JSON.

The conservative dry-run removed references are recorded in the JSON artifact. It gives source-line/event IDs and per-view counts; it does not reproduce narrative text.

## Pending and preserved cases

QC-A's final mechanical report has 20 PASS, 4 REVIEW_REQUIRED, and 1 FAIL; this proposal includes its four date-only payment claims and the direct closure candidate. The eight date-only QC-B items are also included. In 6999 the proposed boundary applies to a manager's claim that payment was conducted; it does not establish bank receipt or settlement. Deal 7567 remains a source-scope exception: only the cited rows 393/394 could be quarantined, after follow-up; no unrelated events or whole-deal cutoff are proposed.

Preserve signature/payment-order sources in5293, signature-only evidence in7417, the terse not-relevant manager claim in6589, and ordinary objections in7009/18729. QC-A marked5293/6589/7009 PASS under the existing input rule; no exception is proposed for them. No cutoff is proposed for these controls.

## Required decision and comparability

The supplied task requires stopping for a methodology change relative to v2 or ambiguity that can materially change the result. This conservative source-boundary/quarantine exception requires approval; the earlier approval for five worklogs does not cover these additional records. Unproved project linkage in7567 is handled by the proposed two-row quarantine, not an invented deal-wide cutoff. Direct18357 callback explicitly refers to the prior request now withdrawn after another purchase; imperfect ASR of the equipment noun does not make the request linkage absent.

Conservative boundaries can remove genuine predecision same-day or intervening-day communications. Audit schema and semantic method remain unchanged, but baseline comparison must disclose unequal source admissibility; baseline datasets and deal_audit_v1/v2 remain untouched. If approved, preserve current inputs, pin the exact source policy, validate the rebuild, archive11 exposed drafts and use fresh workers before continuing Stage4–6. No primary freeze or outcome reveal has occurred.

If approved, re-audit the active primary drafts listed in the JSON by filename. The JSON also lists the cited deal IDs for which no current primary draft filename was present when checked.

## Evidence pins and limits

The JSON lists the cited source line, event ID, timestamp, content SHA-256, and view-to-canonical content match for each decision-bearing row. QC-A and QC-B source claims remain evidence pointers, not a cohort-wide semantic PASS. The proposal is a method decision only; it is unapplied and does not authorize a freeze or downstream audit.
