"""Summarize blind label coverage, agreement, and chronological transitions."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
KINDS = ("D3", "D7", "T25", "T50", "T80")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    contract = read(HERE / "labeling_contract.json")
    manifest = read(HERE / "snapshot_manifest.json")
    cutoffs = {(x["deal_id"], x["snapshot"]): datetime.fromisoformat(x["cutoff"]) for x in manifest["snapshots"]}
    primary = {}
    for worker in "ABC":
        for deal in read(HERE / "labels" / f"{worker}.json")["deals"]:
            for snap in deal["snapshots"]:
                for label in snap["labels"]:
                    key = (str(deal["deal_id"]), snap["snapshot"], label["feature_id"])
                    assert key not in primary
                    primary[key] = label
    assert len(primary) == 1150
    second = {}
    for snap in read(HERE / "reliability" / "second_labels.json")["snapshots"]:
        for label in snap["labels"]:
            key = (str(snap["deal_id"]), snap["snapshot"], label["feature_id"])
            assert key in primary and key not in second
            second[key] = label
    assert len(second) == 230
    metrics = {}
    transitions = {}
    for f in contract["features"]:
        fid = f["feature_id"]
        known = {kind: sum(primary[(deal, kind, fid)]["value"] != "UNKNOWN" for deal in {k[0] for k in primary}) for kind in KINDS}
        pairs = [(primary[k]["value"], v["value"], k) for k, v in second.items() if k[2] == fid]
        assert len(pairs) == 23
        exact = sum(a == b for a, b, _ in pairs)
        unknown_agree = sum((a == "UNKNOWN") == (b == "UNKNOWN") for a, b, _ in pairs)
        both_unknown = sum(a == b == "UNKNOWN" for a, b, _ in pairs)
        major = [(k[0], k[1], a, b) for a, b, k in pairs if a != "UNKNOWN" and b != "UNKNOWN" and a != b]
        one_unknown = [(k[0], k[1], a, b) for a, b, k in pairs if (a == "UNKNOWN") != (b == "UNKNOWN")]
        metrics[fid] = {"name": f["name"], "known_by_snapshot": known, "exact_agreement_pct": round(100 * exact / 23, 1),
                        "unknown_status_agreement_pct": round(100 * unknown_agree / 23, 1),
                        "both_unknown_count": both_unknown, "major_disagreement_pct": round(100 * len(major) / 23, 1),
                        "major_disagreements": major, "one_unknown_disagreements": one_unknown,
                        "sample_size": 23}
        sequences = []
        first_known = Counter()
        known_to_unknown = []
        for deal in sorted({k[0] for k in primary}):
            order = sorted(KINDS, key=lambda kind: (cutoffs[deal, kind], KINDS.index(kind)))
            values = [primary[(deal, kind, fid)]["value"] for kind in order]
            first = next((kind for kind, value in zip(order, values) if value != "UNKNOWN"), None)
            first_known[first or "never"] += 1
            for before, after, left, right in zip(order, order[1:], values, values[1:]):
                if left != "UNKNOWN" and right == "UNKNOWN":
                    known_to_unknown.append({"deal_id": deal, "from": before, "to": after})
            sequences.append({"deal_id": deal, "chronological_snapshots": order, "values": values, "first_known": first})
        transitions[fid] = {"first_known": dict(first_known), "known_to_unknown": known_to_unknown, "sequences": sequences}
    (HERE / "reliability" / "agreement.json").write_text(json.dumps({"sample_size_snapshots": 23, "metrics": metrics}, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "temporal_data.json").write_text(json.dumps(transitions, ensure_ascii=False, indent=2), encoding="utf-8")
    for fid, m in metrics.items():
        print(fid, list(m["known_by_snapshot"].values()), "exact", m["exact_agreement_pct"], "UNKNOWN", m["unknown_status_agreement_pct"], "major", m["major_disagreement_pct"], "regressions", len(transitions[fid]["known_to_unknown"]))


if __name__ == "__main__":
    main()
