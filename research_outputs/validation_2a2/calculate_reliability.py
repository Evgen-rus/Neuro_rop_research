import json
from collections import Counter
from pathlib import Path


OUT = Path(__file__).resolve().parent
contract = json.loads((OUT / "event_classifier_contract.json").read_text(encoding="utf-8"))
rules = {c["id"]: c for c in contract["classifiers"]}
benchmark = {r["example_id"]: r for n in range(1, 7) for r in json.loads((OUT / f"benchmark_E{n:02d}.json").read_text(encoding="utf-8"))}
sets = []
for name in ("A", "B"):
    rows = json.loads((OUT / "labels" / f"labeler_{name}.json").read_text(encoding="utf-8"))
    assert len(rows) == len(benchmark)
    by_id = {r["example_id"]: r for r in rows}
    assert len(by_id) == len(rows) and set(by_id) == set(benchmark)
    for eid, row in by_id.items():
        classifier = benchmark[eid]["classifier_id"]
        assert row["classifier_id"] == classifier and row["value"] in ("YES", "NO"), eid
        fields = rules[classifier].get("fields_if_yes", [])
        assert set(row["fields"]) == set(fields), eid
        assert all(v is None or isinstance(v, str) for v in row["fields"].values()), eid
        assert row["confidence"] in ("high", "medium", "low"), eid
    sets.append(by_id)

def norm(value):
    return " ".join(value.lower().split()) if value is not None else None

report = {}
disagreements = []
for classifier in rules:
    ids = [eid for eid, row in benchmark.items() if row["classifier_id"] == classifier]
    pairs = [(eid, sets[0][eid], sets[1][eid]) for eid in ids]
    counts = Counter((a["value"], b["value"]) for _, a, b in pairs)
    yy, nn = counts["YES", "YES"], counts["NO", "NO"]
    split = len(pairs) - yy - nn
    field_metrics = {}
    for field in rules[classifier].get("fields_if_yes", []):
        both_yes = [(a["fields"][field], b["fields"][field]) for _, a, b in pairs if a["value"] == b["value"] == "YES"]
        presence_agree = sum((x is None) == (y is None) for x, y in both_yes)
        both_present = [(x, y) for x, y in both_yes if x is not None and y is not None]
        literal_agree = sum(norm(x) == norm(y) for x, y in both_present)
        field_metrics[field] = {"both_yes": len(both_yes), "presence_agree": presence_agree, "presence_rate": presence_agree / len(both_yes) if both_yes else None, "both_present": len(both_present), "literal_agree": literal_agree, "literal_rate": literal_agree / len(both_present) if both_present else None}
    overall = (yy + nn) / len(pairs)
    yes_agreement = 2 * yy / (2 * yy + split) if (2 * yy + split) else None
    no_agreement = 2 * nn / (2 * nn + split) if (2 * nn + split) else None
    accepted = overall >= .9 and yes_agreement is not None and yes_agreement >= .85 and no_agreement is not None and no_agreement >= .85 and yy >= 8 and nn >= 8
    report[classifier] = {"n": len(pairs), "both_yes": yy, "both_no": nn, "split": split, "overall_exact": overall, "yes_agreement": yes_agreement, "no_agreement": no_agreement, "class_coverage_min_8_each": yy >= 8 and nn >= 8, "numeric_acceptance": accepted, "fields": field_metrics}
    disagreements.extend({"example_id": eid, "classifier_id": classifier, "A": a, "B": b} for eid, a, b in pairs if a["value"] != b["value"])
(OUT / "reliability" / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OUT / "reliability" / "disagreements.json").write_text(json.dumps(disagreements, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for classifier, r in report.items():
    print(classifier, r["n"], r["both_yes"], r["both_no"], r["split"], round(r["overall_exact"], 3), r["numeric_acceptance"])
