import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
plan = json.loads((OUT / "source_plan.json").read_text(encoding="utf-8"))
rows = []
design = []
seen = set()
for shard in ("A", "B"):
    source = {str(x["deal_id"]): json.loads((ROOT / x["file"]).read_text(encoding="utf-8"))["events"] for x in plan["shards"][shard]}
    candidates = json.loads((OUT / "candidates" / f"{shard}.json").read_text(encoding="utf-8"))["candidates"]
    for candidate in candidates:
        events = source[str(candidate["deal_id"])]
        def lookup(pointer):
            matches = [(i, event) for i, event in enumerate(events) if all(event[k] == pointer[k] for k in ("timestamp", "event_type", "event_id"))]
            assert len(matches) == 1, (shard, candidate["deal_id"], pointer, len(matches))
            return matches[0]
        index, current = lookup(candidate["current"])
        previous = None
        if candidate.get("previous"):
            previous_index, previous = lookup(candidate["previous"])
            assert previous_index < index, (candidate["deal_id"], candidate["classifier_id"])
        key = (candidate["classifier_id"], candidate["deal_id"], current["event_id"], previous["event_id"] if previous else None)
        if key in seen:
            continue
        seen.add(key)
        example_id = f"{candidate['classifier_id']}-{len(rows)+1:03d}"
        rows.append({"example_id": example_id, "classifier_id": candidate["classifier_id"], "deal_id": str(candidate["deal_id"]), "current_event": current, "previous_relevant_event": previous})
        design.append({"example_id": example_id, "shard": shard, "design_bucket": candidate["design_bucket"], "why_short": candidate["why_short"]})

for classifier in (f"E{i:02d}" for i in range(1, 7)):
    subset = [row for row in rows if row["classifier_id"] == classifier]
    target = OUT / f"benchmark_{classifier}.json"
    target.write_text(json.dumps(subset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(classifier, len(subset), target.stat().st_size)
(OUT / "benchmark_design.json").write_text(json.dumps(design, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
manifest = {"contract_sha256": plan["contract_sha256"], "examples": len(rows), "counts": dict(Counter(row["classifier_id"] for row in rows)), "files": {f"benchmark_E{i:02d}.json": hashlib.sha256((OUT / f"benchmark_E{i:02d}.json").read_bytes()).hexdigest() for i in range(1, 7)}}
(OUT / "benchmark_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
