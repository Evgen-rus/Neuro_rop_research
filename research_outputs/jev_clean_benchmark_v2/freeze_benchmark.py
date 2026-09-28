"""Freeze a source-diverse J01 consensus benchmark before any Jev call."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
EXCLUDE = {
    "J01-f8ada0f740c4",  # forwarded legal text
    "J01-0c9f33a1083d",  # integrator's quoted request
    "J01-8ea4f72d9572",  # seller quote starts in body
    "J01-45bbcd29b323",  # mobile-mail seller quote remains
    "J01-a87ec6c9b044",  # quote-only email
}
HARD = re.compile(r"(?i)технич|характеристик|оборудован|размер|чертеж|этикет|крышк|\bтар[аыуе]\b|бутылк|флакон|канистр|производительност|аппликатор|лини[ияю]|конвейер|датчик|дозир|станок|материал|инженер|фасов|розлив|схем|вакуум|намотк|подач|габарит|\bлитр|\bмм\b|\bсм\b|\bмл\b|\bшт\b")
SKIP = re.compile(r"(?i)отказались от покупки|отбой по всем проектам|\b[\w.+-]+@[\w.-]+\b|https?://|\+7\s?\(?\d{3}|^сообщение$")


def load(path):
    return json.loads((OUT / path).read_text(encoding="utf-8"))


def save(path, value):
    (OUT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256((OUT / path).read_bytes()).hexdigest()


def choose(rows, count):
    """Round-robin deals, prioritizing topical hard negatives."""
    result = []
    for hard in (True, False):
        groups = defaultdict(list)
        for row in rows:
            if bool(HARD.search(row["utterance"])) == hard and row not in result:
                groups[row["source"]["deal_id"]].append(row)
        while groups and len(result) < count:
            for deal in sorted(list(groups)):
                result.append(groups[deal].pop(0))
                if not groups[deal]:
                    del groups[deal]
                if len(result) == count:
                    break
    return result


def main():
    if (OUT / "benchmark_manifest.json").exists():
        raise RuntimeError("Benchmark already frozen")
    pool = load("candidate_pool.json")["examples"]
    ids = [x["example_id"] for x in pool]
    labels = []
    for name in ("A", "B"):
        rows = load(f"labels/labeler_{name}.json")
        if [x["example_id"] for x in rows] != ids or any(x["label"] not in ("YES", "NO") for x in rows):
            raise RuntimeError(f"Invalid labeler {name} file")
        labels.append({x["example_id"]: x["label"] for x in rows})
    eligible = [x for x in pool if x["example_id"] not in EXCLUDE and x["source"]["deal_id"] != "5971" and not SKIP.search(x["utterance"])]
    yes = [x for x in eligible if labels[0][x["example_id"]] == labels[1][x["example_id"]] == "YES"]
    no = [x for x in eligible if labels[0][x["example_id"]] == labels[1][x["example_id"]] == "NO"]
    disputed = [x for x in eligible if labels[0][x["example_id"]] != labels[1][x["example_id"]]]
    if len(yes) < 40 or len(no) < 40:
        print(f"Insufficient consensus: YES={len(yes)} NO={len(no)}; no artificial fill")
    selected = yes + choose(no, min(50, len(no))) + disputed
    selected.sort(key=lambda x: ids.index(x["example_id"]))
    examples = [{"example_id": x["example_id"], "utterance": x["utterance"],
        "reference": labels[0][x["example_id"]] if labels[0][x["example_id"]] == labels[1][x["example_id"]] else "DISPUTED"}
        for x in selected]
    save("clean_benchmark.json", {"classifier_id": "J01", "examples": examples})
    counts = Counter(x["reference"] for x in examples)
    md = ["# Frozen J01 clean benchmark", "", f"{len(examples)} utterances: {counts['YES']} consensus YES, {counts['NO']} consensus NO, {counts['DISPUTED']} disputed.",
          "Source IDs and outcome are withheld from labeler inputs and Jev requests. Disputed rows are excluded from the primary score.", "",
          "| Example | Reference | Utterance |", "|---|---|---|"]
    for x in examples:
        md.append(f"| {x['example_id']} | {x['reference']} | {x['utterance'].replace(chr(10), ' / ').replace('|', chr(92)+'|')} |")
    (OUT / "clean_benchmark.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    contract = load("classifier_contract.json")
    question = {"type": "noul", "instructions": contract["question"],
                "criteria": {"true": contract["yes_rule"], "false": contract["no_rule"]}}
    frozen_files = ["classifier_contract.json", "classifier_contract.md", "preprocessing_rules.md", "candidate_pool.json",
                    "labels/label_input.json", "labels/labeler_A.json", "labels/labeler_B.json", "clean_benchmark.json", "clean_benchmark.md"]
    manifest = {"classifier_id": "J01", "example_ids": [x["example_id"] for x in examples],
      "counts": dict(counts), "exclusions": sorted(EXCLUDE), "selection": "all eligible consensus YES; 50 source-diverse consensus NO prioritizing topical negatives; all eligible disputed",
      "sha256": {name: sha(name) for name in frozen_files},
      "api": {"url": "https://api.typesafe.ai/v1/systemone", "model": "jev-1.13.0", "question": question},
      "thresholds": [0.50, 0.70, 0.80, 0.90],
      "threshold_rule": "YES if p>=t; NO if p<=1-t; otherwise ABSTAIN. At 0.50, p=0.50 is YES.",
      "official_docs": ["https://docs.typesafe.ai/api", "https://docs.typesafe.ai/models"]}
    save("benchmark_manifest.json", manifest)
    save("raw_responses.json", {"status": "not_run", "responses": []})
    save("run_manifest.json", {"status": "frozen_before_live_calls", "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
      "requests_completed": 0, "outcome_used": False, "dataset_modified": False,
      "benchmark_sha256": sha("clean_benchmark.json"), "manifest_sha256": sha("benchmark_manifest.json")})
    print(f"Frozen total={len(examples)} YES={counts['YES']} NO={counts['NO']} DISPUTED={counts['DISPUTED']} hard_NO={sum(bool(HARD.search(x['utterance'])) for x in selected if labels[0][x['example_id']]=='NO' and labels[1][x['example_id']]=='NO')}")


if __name__ == "__main__":
    assert bool(HARD.search("Отправил вам размеры."))
    assert not bool(HARD.search("Посмотрим завтра."))
    main()
