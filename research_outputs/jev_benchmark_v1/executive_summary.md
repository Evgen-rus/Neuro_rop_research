# Jev Benchmark v1 — E06

Status: **prepared; no live calls**. `TYPESAFE_API_KEY` was absent in the environment. No Jev probabilities, accuracy, latency, usage or cost measurements exist yet.

The request names `validation_2a2/event_benchmark.json`, which does not exist. Its frozen E06 examples are in `validation_2a2/benchmark_E06.json`; the source SHA-256 and all 43 unchanged IDs are recorded in `benchmark_manifest.json`. Consensus reference labels are 31 YES and 10 NO. `E06-076` and `E06-077` are `DISPUTED_REFERENCE` and will be shown separately, outside the main score.

The runner uses the official TypeSafe System One endpoint, the documented pinned `jev-1.13.0` model and a Noul question copied from the frozen E06 contract. It sends only current event and optional earlier local event. Thresholds 0.50, 0.70, 0.80 and 0.90, with a symmetric abstention band, were fixed before any response. No repeat calls are planned: the first complete run will show whether further stability measurement has a reason.

When the key is present, run `python research_outputs/jev_benchmark_v1/runner.py --run`, then `python research_outputs/jev_benchmark_v1/runner.py --score`. Error review and acceptance remain pending until all 43 live responses exist. No outcome, dataset change, holdout or production integration was involved.
