# Validation 2A.2 event benchmark

Frozen before independent labeling. The unit is one current event and at most one earlier related event. Events come from the latest outcome-blind Validation 2A snapshot for each of 23 deals. Candidate curation used two independent balanced shards and exact source pointers; the benchmark contains no tentative label or design bucket.

| Classifier | Examples |
|---|---:|
| E01 | 34 |
| E02 | 34 |
| E03 | 29 |
| E04 | 24 |
| E05 | 31 |
| E06 | 43 |
| **Total** | **195** |

The intended range was roughly 40–60 per classifier if real examples supported it. E01–E05 fell below this range; E04 was especially sparse for likely YES cases. No synthetic positives were added. One E03 current event occurs with two distinct prior-context events; both remain in the frozen benchmark, so those two records are correlated.

Source pointers were resolved to exact events; every supplied prior event precedes its current event in its snapshot. Snapshot sanitization and exclusions are documented in `../validation_2a/snapshot_manifest.json`. The exact classifier rules and the benchmark file hashes are in `event_classifier_contract.json` and `benchmark_manifest.json`.
