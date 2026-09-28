"""Frozen E06 A/B/C/D diagnostic. A reuses Jev Benchmark v1; B/C/D are live."""
import argparse
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from dotenv import dotenv_values

OUT = Path(__file__).resolve().parent
BASE = OUT.parent / "jev_benchmark_v1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
import runner as baseline  # Loads the project-root .env; no key value is logged.

IDS = baseline.load(BASE / "benchmark_manifest.json")["example_ids"]
ERROR_IDS = ("E06-075", "E06-078", "E06-179", "E06-192", "E06-193")


def freeze(path, value):
    if path.exists():
        if baseline.load(path) != value:
            raise RuntimeError(f"Frozen file changed: {path.name}")
    else:
        baseline.save(path, value)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_sources():
    examples, reference, question = baseline.inputs()
    manifest = baseline.load(BASE / "benchmark_manifest.json")
    if [x["example_id"] for x in examples] != IDS or manifest["api"]["model"] != baseline.MODEL:
        raise RuntimeError("Baseline benchmark/model mismatch")
    raw_a = baseline.load(BASE / "raw_responses.json")
    if raw_a["status"] != "complete" or len(raw_a["responses"]) != 43 or set(x["example_id"] for x in raw_a["responses"]) != set(IDS):
        raise RuntimeError("Incomplete baseline responses")
    if any(x["response"]["model"] != baseline.MODEL for x in raw_a["responses"]):
        raise RuntimeError("Baseline model differs from pinned model")
    return examples, reference, question


def prepare():
    examples, _, question = check_sources()
    translations = []
    for name in ("A", "B"):
        translations += baseline.load(OUT / f"translations_{name}.json")
    by_id = {x["example_id"]: x for x in translations}
    if len(translations) != 43 or set(by_id) != set(IDS):
        raise RuntimeError("Translation membership is incomplete or duplicated")
    for example in examples:
        row = by_id[example["example_id"]]
        if set(row) != {"example_id", "current_content_en", "previous_content_en"} or not isinstance(row["current_content_en"], str):
            raise RuntimeError(f"Invalid translation record {example['example_id']}")
        if (example["previous_relevant_event"] is None) != (row["previous_content_en"] is None):
            raise RuntimeError(f"Previous context mismatch {example['example_id']}")
    frozen_translations = [by_id[eid] for eid in IDS]
    freeze(OUT / "translations_en.json", frozen_translations)
    variants = {v: [] for v in ("B", "C", "D")}
    for example in examples:
        eid = example["example_id"]
        original = baseline.state(example)
        english = json.loads(json.dumps(original, ensure_ascii=False))
        english["current_event"]["content"] = by_id[eid]["current_content_en"]
        if english["previous_relevant_event"] is not None:
            english["previous_relevant_event"]["content"] = by_id[eid]["previous_content_en"]
        speaker = json.loads(json.dumps(original, ensure_ascii=False))
        for event in (speaker["current_event"], speaker["previous_relevant_event"]):
            if event is not None:
                event["speaker"] = {"incoming": "CUSTOMER", "outgoing": "SELLER"}.get(event["direction"], "UNKNOWN")
        variants["B"].append({"example_id": eid, "state": english})
        variants["C"].append({"example_id": eid, "state": speaker})
        variants["D"].append({"example_id": eid, "state": original})
    for variant, rows in variants.items():
        freeze(OUT / "inputs" / f"{variant}.json", rows)
    choice = {"type": "choice", "instructions": question["instructions"], "criteria": {"A": question["criteria"]["true"], "B": question["criteria"]["false"]}}
    plan = {"model": baseline.MODEL, "endpoint": baseline.URL, "example_ids": IDS,
            "baseline_raw_sha256": sha(BASE / "raw_responses.json"), "benchmark_sha256": baseline.BENCH_SHA,
            "contract_sha256": baseline.CONTRACT_SHA, "translations_sha256": sha(OUT / "translations_en.json"),
            "input_sha256": {v: sha(OUT / "inputs" / f"{v}.json") for v in variants},
            "translation_model_profile": "Luna Max worker class for both disjoint shards; no reference labels supplied",
            "variants": {"A": "saved Russian original state + frozen Noul question; no new calls",
                         "B": "only event content translated to English; frozen Noul question",
                         "C": "only explicit speaker field added from direction; original Russian state and frozen Noul question",
                         "D": "original Russian state; Choice A/B with frozen instructions and true/false criteria text"},
            "noul_question": question, "choice_question": choice, "thresholds": list(baseline.THRESHOLDS),
            "threshold_rule": baseline.load(BASE / "benchmark_manifest.json")["threshold_rule"],
            "choice_rule": "Use returned choice A or B at full coverage; A maps to YES and B to NO. No Noul thresholds applied.",
            "official_docs": ["https://docs.typesafe.ai/api", "https://docs.typesafe.ai/models"]}
    freeze(OUT / "diagnostic_plan.json", plan)
    for v in variants:
        path = OUT / "raw_responses" / f"{v}.json"
        if not path.exists():
            baseline.save(path, {"status": "not_run", "responses": []})
    if not (OUT / "run_manifest.json").exists():
        baseline.save(OUT / "run_manifest.json", {"status": "prepared", "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
                                                   "baseline_reused": True, "completed": {"B": 0, "C": 0, "D": 0},
                                                   "outcome_used": False, "dataset_modified": False})
    print("Frozen 43 translations and B/C/D inputs; A baseline reused without calls.")


def check_frozen():
    examples, reference, question = check_sources()
    plan = baseline.load(OUT / "diagnostic_plan.json")
    paths = {"translations_sha256": OUT / "translations_en.json"}
    if plan["example_ids"] != IDS or plan["model"] != baseline.MODEL or plan["noul_question"] != question:
        raise RuntimeError("Diagnostic plan changed")
    if sha(BASE / "raw_responses.json") != plan["baseline_raw_sha256"]:
        raise RuntimeError("Baseline raw responses changed")
    if sha(paths["translations_sha256"]) != plan["translations_sha256"]:
        raise RuntimeError("Frozen translations changed")
    for v in ("B", "C", "D"):
        if sha(OUT / "inputs" / f"{v}.json") != plan["input_sha256"][v]:
            raise RuntimeError(f"Frozen {v} input changed")
    return examples, reference, plan


def call_one(state, question, key, variant, eid):
    payload = {"state": state, "model": baseline.MODEL, "questions": {"E06": question}}
    request = Request(baseline.URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    for attempt in range(4):
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            if result.get("model") != baseline.MODEL:
                raise RuntimeError("Response model differs from pinned Jev model")
            answer = result["answers"]["E06"]
            if variant == "D":
                probs = answer["probabilities"]
                if answer["type"] != "choice" or answer["choice"] not in ("A", "B") or set(probs) != {"A", "B"}:
                    raise RuntimeError("Invalid Choice answer")
                if any(not isinstance(p, (int, float)) or isinstance(p, bool) or not 0 <= p <= 1 for p in probs.values()):
                    raise RuntimeError("Invalid Choice probabilities")
            else:
                p = answer["noul"]
                if answer["type"] != "noul" or not isinstance(p, (int, float)) or isinstance(p, bool) or not 0 <= p <= 1:
                    raise RuntimeError("Invalid Noul answer")
            return {"example_id": eid, "latency_seconds": time.perf_counter() - started, "response": result}
        except HTTPError as error:
            if error.code not in (429, 529) or attempt == 3:
                raise RuntimeError(f"TypeSafe HTTP {error.code}; response body not stored") from None
            time.sleep(min(2 ** attempt, 8))
        except URLError as error:
            raise RuntimeError(f"TypeSafe transport failure: {type(error.reason).__name__}") from None
    raise RuntimeError("Retries exhausted")


def run(variant):
    _, _, plan = check_frozen()
    key = dotenv_values(OUT.parents[1] / ".env").get("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY is absent")
    question = plan["choice_question"] if variant == "D" else plan["noul_question"]
    rows = baseline.load(OUT / "inputs" / f"{variant}.json")
    path = OUT / "raw_responses" / f"{variant}.json"
    raw = baseline.load(path)
    done = {x["example_id"] for x in raw["responses"]}
    if len(done) != len(raw["responses"]) or not done.issubset(set(IDS)):
        raise RuntimeError("Inconsistent saved responses")
    for item in rows:
        eid = item["example_id"]
        if eid in done:
            continue
        response = call_one(item["state"], question, key, variant, eid)
        raw["responses"].append(response)
        raw["status"] = "complete" if len(raw["responses"]) == 43 else "partial"
        baseline.save(path, raw)
        manifest = baseline.load(OUT / "run_manifest.json")
        manifest["completed"][variant] = len(raw["responses"])
        manifest["status"] = "calls_complete" if all(manifest["completed"][v] == 43 for v in ("B", "C", "D")) else "partial"
        baseline.save(OUT / "run_manifest.json", manifest)
        print(f"{variant} {len(raw['responses'])}/43 {eid}", flush=True)


def percentile_95(values):
    ordered = sorted(values)
    return ordered[40]  # nearest rank ceil(.95 * 43)


def score():
    _, reference, plan = check_frozen()
    baseline_raw = baseline.load(BASE / "raw_responses.json")["responses"]
    raw = {"A": {x["example_id"]: x for x in baseline_raw}}
    for variant in ("B", "C", "D"):
        data = baseline.load(OUT / "raw_responses" / f"{variant}.json")
        if data["status"] != "complete" or len(data["responses"]) != 43:
            raise RuntimeError(f"{variant} requires all 43 calls")
        raw[variant] = {x["example_id"]: x for x in data["responses"]}
    consensus = [eid for eid in IDS if reference[eid] != "DISPUTED_REFERENCE"]

    def probability(row):
        answer = row["response"]["answers"]["E06"]
        return answer["noul"]

    def counts(pred):
        tp = sum(pred[eid] == "YES" and reference[eid] == "YES" for eid in consensus)
        tn = sum(pred[eid] == "NO" and reference[eid] == "NO" for eid in consensus)
        fp = sum(pred[eid] == "YES" and reference[eid] == "NO" for eid in consensus)
        fn = sum(pred[eid] == "NO" and reference[eid] == "YES" for eid in consensus)
        covered = tp + tn + fp + fn
        return {"covered": covered, "coverage": covered / 41, "accuracy_on_covered": (tp + tn) / covered if covered else None,
                "yes_agreement": tp / 31, "no_agreement": tn / 10, "FP": fp, "FN": fn,
                "abstain": 41 - covered, "TP": tp, "TN": tn,
                "errors": [eid for eid in consensus if pred[eid] in ("YES", "NO") and pred[eid] != reference[eid]]}

    metrics = {"reference": {"scored": 41, "YES": 31, "NO": 10, "disputed": 2}, "variants": {}}
    predictions_050 = {}
    for variant in ("A", "B", "C", "D"):
        latencies = [raw[variant][eid]["latency_seconds"] for eid in IDS]
        entry = {"median_latency_seconds": statistics.median(latencies), "p95_latency_seconds": percentile_95(latencies)}
        if variant == "D":
            pred = {eid: "YES" if raw[variant][eid]["response"]["answers"]["E06"]["choice"] == "A" else "NO" for eid in consensus}
            entry["choice_full_coverage"] = counts(pred)
            entry["disputed"] = [{"example_id": eid, "choice": raw[variant][eid]["response"]["answers"]["E06"]["choice"],
                                  "probabilities": raw[variant][eid]["response"]["answers"]["E06"]["probabilities"]} for eid in IDS if reference[eid] == "DISPUTED_REFERENCE"]
        else:
            entry["thresholds"] = {}
            for t in baseline.THRESHOLDS:
                pred = {eid: "YES" if probability(raw[variant][eid]) >= t else "NO" if probability(raw[variant][eid]) <= 1 - t else "ABSTAIN" for eid in consensus}
                entry["thresholds"][f"{t:.2f}"] = counts(pred)
                if t == .5:
                    predictions_050[variant] = pred
            entry["disputed"] = [{"example_id": eid, "probability": probability(raw[variant][eid])} for eid in IDS if reference[eid] == "DISPUTED_REFERENCE"]
        metrics["variants"][variant] = entry
    baseline.save(OUT / "metrics.json", metrics)
    lines = ["# Five baseline errors across variants", "", "A/B/C use p≥0.50 for YES; D uses its returned Choice. Reference labels were withheld from API requests.", "", "| Example | Reference | A | B | C | D | Interpretation |", "|---|---|---|---|---|---|---|"]
    for eid in ERROR_IDS:
        corrected = []
        cells = []
        for variant in ("A", "B", "C", "D"):
            if variant == "D":
                answer = raw[variant][eid]["response"]["answers"]["E06"]
                pred = "YES" if answer["choice"] == "A" else "NO"
                cell = f"{pred} (A={answer['probabilities']['A']:.2f})"
            else:
                p = probability(raw[variant][eid])
                pred = predictions_050[variant][eid]
                cell = f"{pred} ({p:.2f})"
            cells.append(cell)
            if variant != "A" and pred == reference[eid]:
                corrected.append(variant)
        category = {"B": "LANGUAGE", "C": "SPEAKER_ATTRIBUTION", "D": "QUESTION_TYPE"}.get(corrected[0], "NONE") if len(corrected) == 1 else "MIXED" if corrected else "NONE"
        lines.append(f"| {eid} | {reference[eid]} | {' | '.join(cells)} | {category} |")
    lines += ["", "Interpretation labels describe a single paired run; they do not prove causality, especially with N=41 and correlated examples."]
    (OUT / "five_error_matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = baseline.load(OUT / "run_manifest.json")
    manifest.update(status="scored", scored_at_utc=datetime.now(timezone.utc).isoformat())
    baseline.save(OUT / "run_manifest.json", manifest)
    print("Scored A/B/C/D and wrote five-error matrix.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--run", choices=("B", "C", "D"))
    modes.add_argument("--score", action="store_true")
    args = parser.parse_args()
    try:
        if args.prepare:
            prepare()
        elif args.run:
            run(args.run)
        else:
            score()
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")
