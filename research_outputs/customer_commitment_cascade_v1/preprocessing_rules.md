# Clean customer utterances

1. Reuse the outcome-blind, speaker-clean extraction in `research_outputs/jev_clean_benchmark_v2/build_pool.py`; its source is incoming `message` or `email` events in `dataset/deals/*/clean_timeline.jsonl`. The original pool is an intermediate source, not a J01-labeled benchmark.
2. Admit only cleaned incoming customer text. The extraction drops empty/system/attachment text, exact duplicates, HTML tags, email signatures, and conventional quoted threads. Calls and unsegmented transcripts, outgoing seller messages, manager worklogs, and uncertain speaker fragments remain excluded.
3. Exclude five previously audited quote-contaminated IDs, the prior uncertain-source deal `5971`, email/phone/URL-bearing text, and explicit outcome-containing text before labeling. These exclusions are specified in `build_pool.py` and recorded in the pool.
4. Keep source coordinates only in `candidate_pool.json`. Independent labelers and Jev receive only `example_id` and the cleaned utterance; Jev receives the utterance alone as `state`. Fallback receives only utterance and this frozen C01 contract.
5. Do not split a customer message into invented sentences to increase counts. If fewer than 50 consensus YES and 50 consensus NO are available, report the shortfall rather than synthesize examples.
