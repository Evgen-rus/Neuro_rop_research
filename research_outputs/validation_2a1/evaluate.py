"""Compute blind agreement and temporal checks from frozen classifier outputs."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from derive_state import derive_r01, derive_r02


HERE = Path(__file__).resolve().parent
ATOMIC = ("R01a", "R01b", "R01c", "R03", "R04")
R02_COMPONENTS = ("commitment_exists", "customer_owner", "promised_action", "due_at_or_expected_result",
                  "reported_completion", "reported_reschedule", "replacement_commitment", "explicit_miss")
KINDS = ("D3", "D7", "T25", "T50", "T80")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def values(snapshot):
    labels = {x["id"]: x["value"] for x in snapshot["labels"]}
    labels.update({f"R02.{key}": snapshot["r02"]["component_values"][key] for key in R02_COMPONENTS})
    labels["R01_derived"] = derive_r01(snapshot)
    labels["R02_derived"] = derive_r02(snapshot)
    return labels


def main():
    primary = {}
    for worker in "ABC":
        for deal in read(HERE / "labels" / f"{worker}.json")["deals"]:
            for snap in deal["snapshots"]:
                key = str(deal["deal_id"]), snap["snapshot"]
                assert key not in primary
                primary[key] = snap
    assert len(primary) == 115
    second = {}
    for snap in read(HERE / "reliability" / "second_labels.json")["snapshots"]:
        key = str(snap["deal_id"]), snap["snapshot"]
        assert key in primary and key not in second
        second[key] = snap
    assert len(second) == 30
    metrics = {}
    for fid in (*ATOMIC, *(f"R02.{key}" for key in R02_COMPONENTS), "R01_derived", "R02_derived"):
        pairs = [(values(primary[key])[fid], values(snap)[fid], key) for key, snap in second.items()]
        exact = sum(a == b for a, b, _ in pairs)
        unknown = sum((a == "UNKNOWN") != (b == "UNKNOWN") for a, b, _ in pairs)
        major = sum(a != "UNKNOWN" and b != "UNKNOWN" and a != b for a, b, _ in pairs)
        metrics[fid] = {"n": 30, "exact_agreement_count": exact, "exact_agreement_pct": round(exact * 100 / 30, 1),
                        "unknown_disagreement_count": unknown, "unknown_disagreement_pct": round(unknown * 100 / 30, 1),
                        "major_semantic_disagreement_count": major, "major_semantic_disagreement_pct": round(major * 100 / 30, 1),
                        "pass_threshold": exact / 30 >= .85 and major / 30 <= .10 if fid in ATOMIC or fid.startswith("R02.") else None,
                        "primary_values": dict(Counter(a for a, _, _ in pairs)),
                        "second_values": dict(Counter(b for _, b, _ in pairs)),
                        "disagreements": [{"deal_id": key[0], "snapshot": key[1], "primary": a, "second": b}
                                          for a, b, key in pairs if a != b]}
    (HERE / "reliability" / "metrics.json").write_text(json.dumps({"sample_size": 30, "metrics": metrics}, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = read(HERE.parent / "validation_2a" / "snapshot_manifest.json")
    cutoffs = {(x["deal_id"], x["snapshot"]): datetime.fromisoformat(x["cutoff"]) for x in manifest["snapshots"]}
    temporal = {"R04_yes_reversals": [], "R01_same_gate_yes_to_no": [], "R03_same_task_sufficiency_drop": [],
                "R02_states": {}, "R01_levels": {}, "sequences": []}
    for deal in sorted({x[0] for x in primary}):
        order = sorted(KINDS, key=lambda kind: (cutoffs[deal, kind], KINDS.index(kind)))
        seq = [(kind, primary[deal, kind], values(primary[deal, kind])) for kind in order]
        temporal["sequences"].append({"deal_id": deal, "chronological_order": order,
                                      "states": [{"snapshot": kind, "R01": v["R01_derived"], "R02": v["R02_derived"],
                                                  "R03": v["R03"], "R04": v["R04"]} for kind, _, v in seq]})
        for kind, _, v in seq:
            temporal["R02_states"][v["R02_derived"]] = temporal["R02_states"].get(v["R02_derived"], 0) + 1
            temporal["R01_levels"][v["R01_derived"]] = temporal["R01_levels"].get(v["R01_derived"], 0) + 1
        for (a, left, va), (b, right, vb) in zip(seq, seq[1:]):
            if va["R04"] == "YES" and vb["R04"] != "YES":
                temporal["R04_yes_reversals"].append([deal, a, b, va["R04"], vb["R04"]])
            if left.get("r01_gate_key") and left.get("r01_gate_key") == right.get("r01_gate_key"):
                for fid in ("R01a", "R01b", "R01c"):
                    if va[fid] == "YES" and vb[fid] == "NO":
                        temporal["R01_same_gate_yes_to_no"].append([deal, a, b, fid])
            la = next(x for x in left["labels"] if x["id"] == "R03")
            ra = next(x for x in right["labels"] if x["id"] == "R03")
            if la.get("active_task") and la.get("active_task") == ra.get("active_task") and va["R03"] == "SUFFICIENT_FOR_CURRENT_ASSESSMENT" and vb["R03"] in {"PARTIAL", "INSUFFICIENT"}:
                temporal["R03_same_task_sufficiency_drop"].append([deal, a, b])
    (HERE / "temporal_checks.json").write_text(json.dumps(temporal, ensure_ascii=False, indent=2), encoding="utf-8")
    for fid, m in metrics.items():
        print(fid, m["exact_agreement_pct"], m["unknown_disagreement_count"], m["major_semantic_disagreement_count"], m["pass_threshold"])


if __name__ == "__main__":
    main()
