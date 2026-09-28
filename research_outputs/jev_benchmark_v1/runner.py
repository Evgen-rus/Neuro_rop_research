"""Frozen E06 Jev benchmark: --prepare, --run, then --score."""
import argparse
import hashlib
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OUT = Path(__file__).resolve().parent
SRC = OUT.parent / "validation_2a2"
BENCH_SHA = "b3e75f873a85d52398726e73d15ae3f2070704a847f3a8e580a870209e473081"
CONTRACT_SHA = "94a9b4c47702ca458031da23d68ab38ca58de5cba086da3a14a4b7346777124a"
URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
THRESHOLDS = (0.50, 0.70, 0.80, 0.90)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    bench_file = SRC / "benchmark_E06.json"
    contract_file = SRC / "event_classifier_contract.json"
    if digest(bench_file) != BENCH_SHA or digest(contract_file) != CONTRACT_SHA:
        raise RuntimeError("Frozen E06 benchmark or classifier contract changed")
    examples = load(bench_file)
    ids = [x["example_id"] for x in examples]
    if len(ids) != 43 or len(set(ids)) != 43 or any(x["classifier_id"] != "E06" for x in examples):
        raise RuntimeError("Unexpected benchmark membership")
    label_sets = []
    for name in ("A", "B"):
        rows = {x["example_id"]: x["value"] for x in load(SRC / f"labels/labeler_{name}.json") if x["classifier_id"] == "E06"}
        if set(rows) != set(ids) or any(v not in ("YES", "NO") for v in rows.values()):
            raise RuntimeError(f"Invalid labeler {name} labels")
        label_sets.append(rows)
    reference = {eid: label_sets[0][eid] if label_sets[0][eid] == label_sets[1][eid] else "DISPUTED_REFERENCE" for eid in ids}
    if [list(reference.values()).count(x) for x in ("YES", "NO", "DISPUTED_REFERENCE")] != [31, 10, 2]:
        raise RuntimeError("Reference counts changed")
    rule = next(x for x in load(contract_file)["classifiers"] if x["id"] == "E06")
    question = {"type": "noul", "instructions": rule["question"], "criteria": {"true": rule["yes_rule"], "false": rule["no_rule"]}}
    return examples, reference, question


def prepare():
    examples, reference, question = inputs()
    manifest = {"source": "../validation_2a2/benchmark_E06.json", "source_sha256": BENCH_SHA, "contract_sha256": CONTRACT_SHA,
                "labeler_A_sha256": digest(SRC / "labels/labeler_A.json"), "labeler_B_sha256": digest(SRC / "labels/labeler_B.json"),
                "example_ids": [x["example_id"] for x in examples], "reference": reference,
                "counts": {"total": 43, "consensus_yes": 31, "consensus_no": 10, "disputed": 2},
                "api": {"url": URL, "model": MODEL, "question_id": "E06", "question": question},
                "thresholds": list(THRESHOLDS),
                "threshold_rule": "YES if p >= t; NO if p <= 1-t; otherwise abstain. At t=0.50, p=0.50 is YES."}
    path = OUT / "benchmark_manifest.json"
    if path.exists() and load(path) != manifest:
        raise RuntimeError("Frozen benchmark manifest differs")
    save(path, manifest)
    defaults = {"raw_responses.json": {"status": "not_run", "responses": []},
                "metrics.json": {"status": "not_run", "thresholds": list(THRESHOLDS), "reason": "No live Jev responses"}}
    for name, value in defaults.items():
        if not (OUT / name).exists():
            save(OUT / name, value)
    for name, content in {"error_analysis.md": "# E06 error analysis\n\nPending live Jev responses.\n",
                          "executive_summary.md": "# Jev Benchmark v1 — E06\n\nPrepared: 43 frozen examples, 41 consensus references and 2 disputed. No live Jev results yet.\n"}.items():
        if not (OUT / name).exists():
            (OUT / name).write_text(content, encoding="utf-8")
    save(OUT / "run_manifest.json", {"status": "prepared_no_live_calls", "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
                                     "official_docs": ["https://docs.typesafe.ai/api", "https://docs.typesafe.ai/models"],
                                     "key_present": bool(os.environ.get("TYPESAFE_API_KEY")), "requests_completed": len(load(OUT / "raw_responses.json")["responses"]),
                                     "outcome_used": False, "dataset_modified": False})
    print("Prepared 43 frozen E06 examples; 31 YES, 10 NO, 2 disputed references.")
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY is absent. Stopped before live calls.")


def state(example):
    def event(value):
        return None if value is None else {k: value.get(k) for k in ("timestamp", "event_type", "direction", "content")}
    return {"current_event": event(example["current_event"]), "previous_relevant_event": event(example["previous_relevant_event"])}


def call(example, question, key):
    payload = {"state": state(example), "model": MODEL, "questions": {"E06": question}}
    request = Request(URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    for attempt in range(4):
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            answer = result["answers"]["E06"]
            p = answer["noul"]
            if answer["type"] != "noul" or isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1:
                raise RuntimeError("Invalid Noul response")
            return {"example_id": example["example_id"], "probability": p, "latency_seconds": time.perf_counter() - started, "response": result}
        except HTTPError as error:
            if error.code not in (429, 529) or attempt == 3:
                raise RuntimeError(f"TypeSafe HTTP {error.code}; response body not saved") from None
            time.sleep(min(2 ** attempt, 8))
        except URLError as error:
            raise RuntimeError(f"TypeSafe transport failure: {type(error.reason).__name__}") from None
    raise RuntimeError("Retries exhausted")


def run():
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY is absent; no live calls made")
    examples, _, question = inputs()
    manifest = load(OUT / "benchmark_manifest.json")
    if manifest["api"]["question"] != question or manifest["example_ids"] != [x["example_id"] for x in examples]:
        raise RuntimeError("Frozen manifest mismatch")
    if any(digest(SRC / f"labels/labeler_{name}.json") != manifest[f"labeler_{name}_sha256"] for name in ("A", "B")):
        raise RuntimeError("Frozen reference label files changed")
    raw = load(OUT / "raw_responses.json")
    done = {x["example_id"] for x in raw["responses"]}
    if len(done) != len(raw["responses"]) or not done.issubset(set(manifest["example_ids"])):
        raise RuntimeError("Raw response file inconsistent")
    for example in examples:
        if example["example_id"] in done:
            continue
        row = call(example, question, key)
        raw["responses"].append(row)
        raw["status"] = "complete" if len(raw["responses"]) == 43 else "partial"
        save(OUT / "raw_responses.json", raw)
        run_manifest = load(OUT / "run_manifest.json")
        run_manifest.update(status=raw["status"], requests_completed=len(raw["responses"]), last_call_utc=datetime.now(timezone.utc).isoformat())
        save(OUT / "run_manifest.json", run_manifest)
        print(f"{len(raw['responses'])}/43 {example['example_id']} p={row['probability']:.4f}")
    print("All calls completed. Run --score separately.")


def score():
    examples, reference, _ = inputs()
    manifest = load(OUT / "benchmark_manifest.json")
    if any(digest(SRC / f"labels/labeler_{name}.json") != manifest[f"labeler_{name}_sha256"] for name in ("A", "B")):
        raise RuntimeError("Frozen reference label files changed")
    ids = [x["example_id"] for x in examples]
    responses = {x["example_id"]: x for x in load(OUT / "raw_responses.json")["responses"]}
    if set(responses) != set(ids) or len(responses) != 43:
        raise RuntimeError("All 43 responses are required before scoring")
    consensus = [eid for eid in ids if reference[eid] != "DISPUTED_REFERENCE"]
    results = {}
    for t in THRESHOLDS:
        prediction = {eid: "YES" if responses[eid]["probability"] >= t else "NO" if responses[eid]["probability"] <= 1 - t else "ABSTAIN" for eid in consensus}
        tp = sum(prediction[eid] == "YES" and reference[eid] == "YES" for eid in consensus)
        tn = sum(prediction[eid] == "NO" and reference[eid] == "NO" for eid in consensus)
        fp = sum(prediction[eid] == "YES" and reference[eid] == "NO" for eid in consensus)
        fn = sum(prediction[eid] == "NO" and reference[eid] == "YES" for eid in consensus)
        covered = tp + tn + fp + fn
        results[f"{t:.2f}"] = {"covered": covered, "coverage": covered / 41, "accuracy_on_covered": (tp + tn) / covered if covered else None,
                                "yes_precision": tp / (tp + fp) if tp + fp else None, "yes_agreement_all_reference_yes": tp / 31,
                                "no_agreement_all_reference_no": tn / 10, "true_positive": tp, "true_negative": tn,
                                "false_positive": fp, "false_negative": fn, "yes_errors": fn, "no_errors": fp,
                                "abstained": 41 - covered, "abstained_ids": [eid for eid in consensus if prediction[eid] == "ABSTAIN"]}
    p = [responses[eid]["probability"] for eid in consensus]
    latencies = [responses[eid]["latency_seconds"] for eid in ids]
    usage = [responses[eid]["response"].get("usage", {}) for eid in ids]
    save(OUT / "metrics.json", {"status": "complete", "reference_examples": 41, "reference_yes": 31, "reference_no": 10,
                                "threshold_rule": load(OUT / "benchmark_manifest.json")["threshold_rule"], "thresholds": results,
                                "probability_distribution": {"min": min(p), "median": statistics.median(p), "max": max(p),
                                                             "by_reference": {k: sorted(responses[eid]["probability"] for eid in consensus if reference[eid] == k) for k in ("YES", "NO")}},
                                "latency_seconds": {"min": min(latencies), "median": statistics.median(latencies), "max": max(latencies)},
                                "usage": {"input_tokens": sum(x.get("input_tokens", 0) for x in usage), "output_tokens": sum(x.get("output_tokens", 0) for x in usage),
                                          "missing_usage_responses": sum(not x for x in usage)}, "cost_reported_by_api": None,
                                "model_ids": sorted({responses[eid]["response"].get("model") for eid in ids}),
                                "disputed": [{"example_id": eid, "probability": responses[eid]["probability"]} for eid in ids if reference[eid] == "DISPUTED_REFERENCE"]})
    run_manifest = load(OUT / "run_manifest.json")
    run_manifest.update(status="scored", requests_completed=43, scored_at_utc=datetime.now(timezone.utc).isoformat())
    save(OUT / "run_manifest.json", run_manifest)
    print("Scored all 43 responses; inspect errors before acceptance.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    for mode in ("prepare", "run", "score", "self-check"):
        modes.add_argument(f"--{mode}", action="store_true")
    args = parser.parse_args()
    try:
        if args.prepare:
            prepare()
        elif args.run:
            run()
        elif args.score:
            score()
        else:
            examples, reference, question = inputs()
            assert len(examples) == 43 and list(reference.values()).count("DISPUTED_REFERENCE") == 2
            assert question["type"] == "noul" and "deal_id" not in state(examples[0])
            print("Frozen inputs and request shape verified")
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")
