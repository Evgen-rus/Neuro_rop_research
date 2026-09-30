# Outcome-blind audit views

`build_audit_views.py` reads only `dataset_v2/deals/*/neutral.json` and each matching `clean_timeline.jsonl`. It checks that `neutral.json.deal_id` matches the folder name and uses only `created_at` plus `life_days` to compute a calendar end date. It hashes the complete neutral file and does not copy neutral fields or the computed date into semantic views. It does not open `manifest.json`, `summary.json`, `build_quality.json`, or other research outputs.

Each successful deal produces `views/<deal_id>.jsonl`. Kept event objects retain their original fields, identifiers, and file order, with an added `source_line` containing the 1-based physical input line. JSON is compacted with sorted object keys; event order is unchanged. Source files are read-only.

Events dated after `created_at + life_days` are removed. On `comment` events, zero-padded `DD.MM`, year-bearing `D.M.YY[YY]`, or ISO `YYYY-MM-DD` segments after that end date are removed up to the next recognized date entry; yearless dates use the year nearest the comment timestamp. Same-day dates are kept. A one-day offset in `life_days` may exclude a real next-day interaction, which is reported as a possible false exclusion. Same-day content cannot be separated from an outcome solely by this rule.

The first remaining event with an explicit terminal event type, past-tense closure phrase, or customer refusal to proceed is removed along with every later row in file order. A reply such as “not this time” is treated as refusal only when it occurs within 300 characters after a clear statement that the requested implementation is infeasible. Ordinary objections about price, a proposal, or a feature remain. All `stage_change` records and empty `call` metadata shells are removed as CRM/process noise. Other records, including manager worklogs, stay source-tagged. Removed-event and removed-segment counts are recorded by category; no outcome label is produced.

`audit_manifest.json` records per-deal input/view SHA-256 hashes, byte sizes, original/view event counts, approximate token counts, and removal counts. Token counts use `ceil(UTF-8 bytes / 4)` as a reproducible size proxy, not a model tokenizer. No clock, network, model, or external service is used.

## Limits

Terminal detection is intentionally narrow and lexical. It can miss implied or differently worded closure and can flag an explicit closure phrase quoted in an earlier discussion; review the removed-count boundary before semantic interpretation. The contextual “not this time” cue requires an implementation-failure statement within 300 characters and may still misread unusual quoted dialogue. Embedded date parsing does not recognize every date format, and segment boundaries assume each recognized date begins a separate note. Rows are never sorted. Empty call shells are removed, so call volume and duration are not available in the view. Manager worklog text remains a manager claim and should not be treated as customer-confirmed evidence without corroboration.

Malformed or missing input is recorded as an issue in the manifest and that deal gets no newly written view. The builder does not repair source data or delete unrelated output files.
