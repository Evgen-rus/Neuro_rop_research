"""Deterministic R02 commitment ledger and R01 gate fact aggregation.

Input is already adjudicated event extraction with explicit entity links.
No raw text, outcome, or whole-deal semantic classifier is read here.
"""

from datetime import datetime


def _future(checkpoint, as_of):
    if not checkpoint:
        return False
    try:
        return datetime.fromisoformat(checkpoint) > datetime.fromisoformat(as_of)
    except ValueError:
        return False  # Textual checkpoints remain PROMISED until an explicit event updates them.


def commitment_ledger(events, as_of):
    ledger = {}
    unresolved = []
    for event in events:
        kind = event["classifier_id"]
        if event["value"] != "YES" or kind not in {"E01", "E02", "E03", "E04"}:
            continue
        key = event.get("commitment_id")
        if not key:
            unresolved.append({"event_id": event.get("event_id"), "reason": "missing commitment_id"})
            continue
        if kind == "E01":
            if key in ledger:
                unresolved.append({"event_id": event.get("event_id"), "reason": "duplicate commitment_id"})
                continue
            ledger[key] = {"owner": event.get("owner"), "action": event.get("action"), "checkpoint": event.get("due_at_or_expected_result"), "status": "PROMISED", "explicit_miss_count": 0}
            continue
        if key not in ledger:
            unresolved.append({"event_id": event.get("event_id"), "reason": "prior commitment not linked"})
            continue
        item = ledger[key]
        if kind == "E02":
            item["status"] = "COMPLETED"
        elif kind == "E03":
            item["checkpoint"] = event.get("new_due_at_or_expected_result")
            item["status"] = "RESCHEDULED"
        elif kind == "E04":
            item["explicit_miss_count"] += 1
            item["status"] = "REPEATEDLY_MISSED" if item["explicit_miss_count"] >= 2 else "EXPLICITLY_MISSED"
    for item in ledger.values():
        if item["status"] == "PROMISED" and _future(item["checkpoint"], as_of):
            item["status"] = "NOT_DUE"
    return {"commitments": ledger, "unresolved": unresolved, "default_state": "UNKNOWN" if not ledger else None}


def gate_records(events):
    gates = {}
    unresolved = []
    for event in events:
        if event["classifier_id"] != "E05" or event["value"] != "YES":
            continue
        key = event.get("gate_id")
        if not key:
            unresolved.append({"event_id": event.get("event_id"), "reason": "missing gate_id"})
            continue
        record = gates.setdefault(key, {"customer_role": None, "decision_action": None, "checkpoint": None, "source_event_ids": []})
        for field in ("customer_role", "decision_action", "checkpoint"):
            if event.get(field) is not None:
                record[field] = event[field]
        record["source_event_ids"].append(event.get("event_id"))
    return {"gates": gates, "unresolved": unresolved}


def demo():
    events = [
        {"event_id": "a", "classifier_id": "E01", "value": "YES", "commitment_id": "c1", "owner": "клиент", "action": "прислать фото", "due_at_or_expected_result": "2026-09-26T12:00:00+07:00"},
        {"event_id": "b", "classifier_id": "E04", "value": "YES", "commitment_id": "c1"},
        {"event_id": "c", "classifier_id": "E03", "value": "YES", "commitment_id": "c1", "new_due_at_or_expected_result": "2026-09-28T12:00:00+07:00"},
        {"event_id": "d", "classifier_id": "E04", "value": "YES", "commitment_id": "c1"},
    ]
    initial = commitment_ledger(events[:1], "2026-09-25T12:00:00+07:00")
    assert initial["commitments"]["c1"]["status"] == "NOT_DUE"
    overdue_without_evidence = commitment_ledger(events[:1], "2026-09-27T12:00:00+07:00")
    assert overdue_without_evidence["commitments"]["c1"]["status"] == "PROMISED"
    assert commitment_ledger(events[:2], "2026-09-27T12:00:00+07:00")["commitments"]["c1"]["status"] == "EXPLICITLY_MISSED"
    assert commitment_ledger(events[:3], "2026-09-27T12:00:00+07:00")["commitments"]["c1"]["status"] == "RESCHEDULED"
    assert commitment_ledger(events, "2026-09-29T12:00:00+07:00")["commitments"]["c1"]["status"] == "REPEATEDLY_MISSED"
    assert commitment_ledger([{"event_id": "x", "classifier_id": "E02", "value": "YES", "commitment_id": "missing"}], "2026-09-25T12:00:00+07:00")["unresolved"]
    gate = gate_records([{"event_id": "g1", "classifier_id": "E05", "value": "YES", "gate_id": "gate1", "customer_role": "директор", "decision_action": "утвердить проект", "checkpoint": None}])
    assert gate["gates"]["gate1"]["customer_role"] == "директор"


if __name__ == "__main__":
    demo()
    print("state prototype self-check passed")
