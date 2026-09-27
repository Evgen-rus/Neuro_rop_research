# R02 deterministic commitment ledger prototype

`state_prototype.py` consumes adjudicated E01–E04 event labels in chronological order. Every YES event needs an explicit `commitment_id` referring to the same customer-owned action. That link is **not** provided by the current E01–E04 classifier contract, so production automation is not yet supported. Missing or broken links go to `unresolved`; they are not matched by text similarity.

An E01 event creates a commitment with customer owner, action and optional checkpoint. A parseable future checkpoint yields `NOT_DUE`; absent, textual or past checkpoint remains `PROMISED`. Passing time alone never creates `EXPLICITLY_MISSED`. E02 sets `COMPLETED`; E03 sets `RESCHEDULED` and replaces the checkpoint; E04 increments the explicit miss count and sets `EXPLICITLY_MISSED`, then `REPEATEDLY_MISSED` from the second explicit miss. If there is no linked commitment, the default state is `UNKNOWN`. Historical miss count is retained when a commitment is rescheduled.

This is an event-state demonstration, not a validated whole-deal R02 label. Field wording and cross-event entity linking still require a separate contract and validation. The built-in self-check covers future vs elapsed time, explicit misses, reschedule, missing link, and gate aggregation.
