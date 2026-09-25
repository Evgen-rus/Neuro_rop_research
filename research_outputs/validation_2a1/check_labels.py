"""Check frozen values, snapshot membership, and time bounds without deal results."""

import json
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
SNAPS = HERE.parent / "validation_2a" / "snapshots"
IDS = {"R01a", "R01b", "R01c", "R03", "R04"}
COMPONENTS = {"commitment_exists", "customer_owner", "promised_action", "due_at_or_expected_result",
              "reported_completion", "reported_reschedule", "replacement_commitment", "explicit_miss"}
FIELDS = {"commitment_id", "agreed_at", "owner", "action", "due_at", "expected_result", "replaces_id",
          "completion_evidence_at", "reschedule_evidence_at", "explicit_missed_at", "evidence"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check_record(deal, snap, legal):
    issues = []
    path = SNAPS / f"{deal}_{snap['snapshot']}.json"
    source = read(path)
    cutoff = datetime.fromisoformat(source["cutoff"])
    valid_events = {(datetime.fromisoformat(e["timestamp"]), e["event_type"], e["event_id"]) for e in source["events"]}
    if datetime.fromisoformat(snap["cutoff"]) != cutoff:
        issues.append("cutoff mismatch")
    labels = snap["labels"]
    if len(labels) != 5 or {x["id"] for x in labels} != IDS:
        issues.append("wrong classifier set")

    def evidence(rows, where):
        for e in rows:
            try:
                timestamp = datetime.fromisoformat(e["timestamp"])
                key = timestamp, e["event_type"], e["event_id"]
                if timestamp > cutoff or key not in valid_events:
                    issues.append(f"{where}: evidence outside snapshot")
            except (KeyError, TypeError, ValueError):
                issues.append(f"{where}: malformed evidence")

    for label in labels:
        fid = label["id"]
        if label["value"] not in legal[fid]:
            issues.append(f"{fid}: invalid value")
        if label.get("confidence") not in {"high", "medium", "low"}:
            issues.append(f"{fid}: invalid confidence")
        if fid == "R03" and label["value"] != "UNKNOWN" and not label.get("active_task"):
            issues.append("R03: missing active task")
        evidence(label.get("evidence", []), fid)
    r02 = snap["r02"]
    if r02["absence_status"] not in {"NO_COMMITMENT", "UNKNOWN"}:
        issues.append("R02: invalid absence_status")
    if set(r02["component_values"]) != COMPONENTS:
        issues.append("R02: missing components")
    for key, value in r02["component_values"].items():
        if value not in {"YES", "NO", "UNKNOWN"}:
            issues.append(f"R02 {key}: invalid value")
        evidence(r02.get("component_evidence", {}).get(key, []), f"R02 {key}")
    if r02["absence_status"] == "NO_COMMITMENT" and r02["commitments"]:
        issues.append("R02: nonempty ledger with NO_COMMITMENT")
    for c in r02["commitments"]:
        if not FIELDS <= set(c):
            issues.append("R02: missing commitment fields")
            continue
        for key in ("agreed_at", "completion_evidence_at", "reschedule_evidence_at", "explicit_missed_at"):
            if c[key] and datetime.fromisoformat(c[key]) > cutoff:
                issues.append(f"R02: future {key}")
        evidence(c["evidence"], "R02 commitment")
    return issues


if __name__ == "__main__":
    contract = read(HERE / "refined_classifier_contract.json")
    legal = {x["id"]: set(x["values"]) for x in contract["classifiers"]}
    for worker in "ABC":
        file = HERE / "labels" / f"{worker}.json"
        if not file.exists():
            continue
        data = read(file)
        issues = [(str(deal["deal_id"]), snap["snapshot"], issue)
                  for deal in data["deals"] for snap in deal["snapshots"]
                  for issue in check_record(str(deal["deal_id"]), snap, legal)]
        count = sum(len(deal["snapshots"]) for deal in data["deals"])
        print(worker, "snapshots", count, "issues", len(issues), issues[:12])
