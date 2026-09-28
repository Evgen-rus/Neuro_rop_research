# E06 error analysis

This is one completed `jev-1.13.0` run. The frozen reference has 41 scored examples (31 YES, 10 NO); two disputed examples are excluded. At threshold 0.50, 36/41 agree (87.8%): two false negatives and three false positives. These observations describe this run only.

## Threshold 0.50 mismatches

| Example | Reference → prediction (`p`) | Event evidence | Error boundary |
|---|---|---|---|
| `E06-075` | YES → NO (`0.18`) | Incoming message, `2026-07-30T16:32:10+07:00`, `source_ids=2951187,2951189`: “Крышка 48” (“cap 48”). | A customer technical datum, but the unit, meaning of 48, and link to solution fit are unstated in this event. A false negative if the fragment is accepted as a checkable requirement; conservative NO is also understandable under the event-only rule. |
| `E06-078` | YES → NO (`0.26`) | Incoming email, `2026-07-23T14:13:23+07:00`, `source_ids=627657`: lists 10 L canister K15, cap P55, and a 5 L canister/cap. | Specific, checkable packaging information, but presented as manufacturer documentation rather than an explicit constraint or question. This is the other undercall on customer-provided technical data. |
| `E06-179` | NO → YES (`0.69`) | Incoming call transcript, `2026-02-06T17:01:32+07:00`, `activity_id=529553`: customer and seller discuss sending bottle samples with caps, quantities, and dimensions already available from photos. | Technical context appears, but the exchange is about sample and contract logistics; it states no application-specific requirement or technical question about the proposed solution. |
| `E06-192` | NO → YES (`0.58`) | Outgoing email, `2026-05-06T13:54:41+07:00`, `source_ids=569903`: seller asks which three more bottles and their dimensions to send for equipment costing. The embedded customer line says only “Это второй тоже точно нужен” (“the second one is definitely needed too”). | Technical terms and a customer reply are present, but the customer line identifies a needed bottle, not a checkable technical requirement. The request for dimensions is seller-authored. |
| `E06-193` | NO → YES (`0.51`) | Outgoing email, `2026-04-30T16:28:31+07:00`, `source_ids=566445`: seller says production needs each container’s dimensions and bottom photos for the auger divider, cites changeover equipment, and limits trial to five container types. | The visible technical constraints are seller-stated. The quoted email is truncated after its header, so the packet does not establish a customer-stated requirement; the visible evidence supports NO under E06. |

The errors cluster semantically around “technical context” versus a customer-stated, solution-checkable requirement. The two undercalls are terse customer technical details; two overcalls are outgoing seller emails from the same deal (`7601`), and the third is sample logistics. Their probabilities span `0.18–0.69`, so this is not one narrow score band. The shared deal and single run limit how much to infer from the pattern.

## Abstention thresholds

| Threshold | Decided / coverage | Accuracy on decided | Abstentions | Remaining errors |
|---|---:|---:|---:|---|
| `0.70` | 32/41 (78.0%) | 93.8% | 9 | `E06-075`, `E06-078` (both false negatives) |
| `0.80` | 29/41 (70.7%) | 96.6% | 12 | `E06-075` (false negative) |
| `0.90` | 18/41 (43.9%) | 100% | 23 | none among decided examples |

At `0.90`, only 2 of the 10 reference NO examples receive a decided NO; the other eight abstain. The perfect accuracy is therefore based on 18 decisions, not full benchmark coverage.

## Disputed references (not scored)

- `E06-076`, `p=0.20`: incoming message, `2026-07-30T16:52:23+07:00`, `source_ids=2951359,2951361`, says only “цилиндрическая” (“cylindrical”). With no previous related event, this gives shape but no clear requirement or technical question; NO is plausible, while a missing referent could change the interpretation.
- `E06-077`, `p=0.24`: incoming email, `2026-07-30T17:37:58+07:00`, `source_ids=634383`, says “На всех ведрах так приклеены этикетки” (“labels are attached this way on all buckets”). The text refers to “this way,” but the packet has no previous related event or referenced visual. It may describe a relevant application condition, yet the checkable constraint cannot be recovered here.

Both remain disputed as supplied and do not contribute to the threshold metrics.
