"""Run and score the frozen J01 benchmark; never sends labels or source metadata."""
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

from dotenv import load_dotenv

OUT = Path(__file__).resolve().parent
load_dotenv(OUT.parents[1] / ".env")
URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
THRESHOLDS = (0.50, 0.70, 0.80, 0.90)


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(name):
    return hashlib.sha256((OUT / name).read_bytes()).hexdigest()


def frozen():
    manifest = read("benchmark_manifest.json")
    for name, expected in manifest["sha256"].items():
        if sha(name) != expected:
            raise RuntimeError(f"Frozen file changed: {name}")
    if manifest["api"]["url"] != URL or manifest["api"]["model"] != MODEL or manifest["thresholds"] != list(THRESHOLDS):
        raise RuntimeError("Frozen API/model/threshold settings changed")
    rows = read("clean_benchmark.json")["examples"]
    if [x["example_id"] for x in rows] != manifest["example_ids"]:
        raise RuntimeError("Frozen benchmark membership changed")
    return rows, manifest


def request(utterance, question, key):
    payload = {"state": utterance, "model": MODEL, "questions": {"J01": question}}
    req = Request(URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    for attempt in range(4):
        start = time.perf_counter()
        try:
            with urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
            answer = body["answers"]["J01"]
            p = answer["noul"]
            if body.get("model") != MODEL or answer.get("type") != "noul" or isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1:
                raise RuntimeError("Unexpected Jev model or Noul response")
            return p, time.perf_counter() - start, body
        except HTTPError as error:
            if error.code not in (429, 529) or attempt == 3:
                raise RuntimeError(f"TypeSafe HTTP {error.code}; body withheld") from None
            time.sleep(min(2 ** attempt, 8))
        except URLError as error:
            raise RuntimeError(f"TypeSafe transport failure: {type(error.reason).__name__}") from None
    raise RuntimeError("Retries exhausted")


def run():
    rows, manifest = frozen()
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY absent; no live calls")
    raw = read("raw_responses.json")
    done = {x["example_id"] for x in raw["responses"]}
    if len(done) != len(raw["responses"]) or not done.issubset(set(manifest["example_ids"])):
        raise RuntimeError("Inconsistent saved responses")
    for row in rows:
        if row["example_id"] in done:
            continue
        p, latency, response = request(row["utterance"], manifest["api"]["question"], key)
        raw["responses"].append({"example_id": row["example_id"], "probability": p,
                                 "latency_seconds": latency, "response": response})
        raw["status"] = "complete" if len(raw["responses"]) == len(rows) else "partial"
        write("raw_responses.json", raw)
        progress = read("run_manifest.json")
        progress.update(status=raw["status"], requests_completed=len(raw["responses"]), last_call_utc=datetime.now(timezone.utc).isoformat())
        write("run_manifest.json", progress)
        print(f"{len(raw['responses'])}/{len(rows)} {row['example_id']}")


def score():
    rows, _ = frozen()
    raw = read("raw_responses.json")
    responses = {x["example_id"]: x for x in raw["responses"]}
    if len(responses) != len(rows) or set(responses) != {x["example_id"] for x in rows}:
        raise RuntimeError("All frozen examples need responses before scoring")
    reference = {x["example_id"]: x["reference"] for x in rows}
    consensus = [x["example_id"] for x in rows if x["reference"] in ("YES", "NO")]
    yes = sum(reference[x] == "YES" for x in consensus)
    no = sum(reference[x] == "NO" for x in consensus)
    results = {}
    for t in THRESHOLDS:
        pred = {x: "YES" if responses[x]["probability"] >= t else "NO" if responses[x]["probability"] <= 1-t else "ABSTAIN" for x in consensus}
        tp = sum(reference[x] == "YES" and pred[x] == "YES" for x in consensus)
        tn = sum(reference[x] == "NO" and pred[x] == "NO" for x in consensus)
        fp = sum(reference[x] == "NO" and pred[x] == "YES" for x in consensus)
        fn = sum(reference[x] == "YES" and pred[x] == "NO" for x in consensus)
        covered = tp+tn+fp+fn
        results[f"{t:.2f}"] = {"covered": covered, "coverage": covered/len(consensus) if consensus else None,
          "overall_agreement_on_covered": (tp+tn)/covered if covered else None,
          "yes_agreement_all_reference_yes": tp/yes if yes else None,
          "no_agreement_all_reference_no": tn/no if no else None,
          "false_positive": fp, "false_negative": fn, "abstain": len(consensus)-covered,
          "true_positive": tp, "true_negative": tn,
          "error_ids": [x for x in consensus if pred[x] in ("YES", "NO") and pred[x] != reference[x]],
          "abstain_ids": [x for x in consensus if pred[x] == "ABSTAIN"]}
    latencies = [responses[x["example_id"]]["latency_seconds"] for x in rows]
    latency_sorted = sorted(latencies)
    usage = [responses[x["example_id"]]["response"].get("usage", {}) for x in rows]
    distribution = {k: sorted(responses[x]["probability"] for x in consensus if reference[x] == k) for k in ("YES", "NO")}
    verdict = "passes" if yes >= 40 and no >= 40 and results["0.50"]["yes_agreement_all_reference_yes"] >= .9 and results["0.50"]["no_agreement_all_reference_no"] >= .9 else "does_not_pass"
    write("metrics.json", {"reference_examples": len(consensus), "reference_yes": yes, "reference_no": no,
      "disputed": [{"example_id": x["example_id"], "probability": responses[x["example_id"]]["probability"]} for x in rows if x["reference"] == "DISPUTED"],
      "thresholds": results, "probability_distribution": distribution,
      "latency_seconds": {"median": statistics.median(latencies), "p95_nearest_rank": latency_sorted[max(0, int(.95*len(latency_sorted)+.999999)-1)]},
      "usage": {"input_tokens": sum(u.get("input_tokens", 0) for u in usage), "output_tokens": sum(u.get("output_tokens", 0) for u in usage), "missing": sum(not u for u in usage)},
      "verdict": verdict})
    progress = read("run_manifest.json")
    progress.update(status="scored", scored_at_utc=datetime.now(timezone.utc).isoformat())
    write("run_manifest.json", progress)
    print(f"Scored {len(rows)} frozen examples; verdict={verdict}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    for mode in ("self-check", "run", "score"):
        modes.add_argument(f"--{mode}", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_check:
            rows, manifest = frozen()
            assert all(isinstance(x["utterance"], str) and x["utterance"] for x in rows)
            assert manifest["api"]["question"]["type"] == "noul"
            print(f"Frozen benchmark and request shape verified: {len(rows)} examples")
        elif args.run:
            run()
        else:
            score()
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")
