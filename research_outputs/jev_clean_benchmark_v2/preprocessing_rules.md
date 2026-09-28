# Deterministic speaker-clean extraction

1. Read `dataset/deals/*/clean_timeline.jsonl` without consulting `manifest.json` or outcome fields. Preserve the source dataset.
2. Admit only events with `direction == incoming` and `event_type` in `message`, `email`. Exclude calls and transcripts because their text has no reliable turn-level speaker markers; also exclude manager notes, outgoing and unknown-direction events.
3. Decode HTML entities, drop HTML tags, normalize line endings, and trim blank lines. For email, cut at the first conventional quote divider, email-header line, dated email-address line, or signature opening. Keep only the preceding new body.
4. Exclude empty text, system notifications, attachment placeholders, standalone filenames and exact duplicate cleaned utterances. Do not reconstruct missing attachment content or use neighboring events to interpret an utterance.
5. Source reference (`deal_id`, line, timestamp, event type) stays in the pool for traceability. Labelers receive only `example_id` and `utterance`; Jev receives only `utterance` as state.

Implementation and its two self-checks: `build_pool.py`. A generated candidate pool is not the benchmark or a gold label. Any remaining uncertain authorship or quotation must be excluded before the benchmark freezes.
