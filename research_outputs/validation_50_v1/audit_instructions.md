# Blind deal audit — validation 50 v1

Read only each assigned deal's `views/<deal_id>.jsonl`, its `neutral.json`, its `quality.json`, and `audit_schema.json`. Write a separate JSON audit for each assigned deal using every required field of the frozen schema. Analyze each deal from its own evidence; do not transfer findings between deals. Do not delegate or read unassigned deals, labels, manifests, earlier findings or other audits.

Audit the visible customer need, chronology, initiative, decision process, turning points, manager actions and limits of influence. Do not predict or infer WON/LOST, closure cause, or terminal stage. Do not force a manager mistake: an opportunity is an action worth considering, not proof it would change the outcome. Empty arrays and unknown/null are valid.

Read all substantive communications in the assigned view; use chunks for large views. Metadata-only activities establish timing, not customer intent. A missing recording/transcript is a limitation, not negative evidence. Direction identifies incoming/outgoing communication but does not diarize transcript speakers. Attribute customer speech only where the text supports it. Manager worklogs remain manager claims unless corroborated by customer-sourced evidence.

For large email chains, inspect the new text of every event and the full relevant quoted chain once; repeated quoted paragraphs are not independent customer signals. Distinguish the current sender from a quoted earlier speaker. Selective chunk reading is permitted, but record uncertainty where substantive content was not inspected. Preserve the canonical source pointers; never invent an earlier event timestamp from quoted text.

Separate observed facts, interpretation and uncertainty. Every substantive assertion needs evidence or explicit uncertainty. Evidence must preserve the exact timestamp, event_type, available event ID and `source_line` from the assigned view. Use concise paraphrases, no long transcript copies. `evidence_indices` are zero-based positions in your own evidence array. Cite the source event itself, not an activity whose content was unavailable.

Use Russian prose. Return only the saved file path, completion status and important input limitations in the handoff. The primary performs evidence QC and freezes the audit before outcome aggregation.
