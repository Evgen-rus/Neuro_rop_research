"""Deterministic state calculations for the frozen 2A.1 contract."""

from datetime import datetime, time


def as_time(value, cutoff):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if len(value) == 10:
        parsed = datetime.combine(parsed.date(), time.max, cutoff.tzinfo)
    elif parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=cutoff.tzinfo)
    return parsed


def derive_r01(snapshot):
    values = {x["id"]: x["value"] for x in snapshot["labels"]}
    trio = [values[key] for key in ("R01a", "R01b", "R01c")]
    if all(x == "YES" for x in trio) and snapshot.get("r01_gate_key"):
        return "2"
    if any(x == "YES" for x in trio):
        return "1"
    if all(x == "NO" for x in trio):
        return "0"
    return "UNKNOWN"


def concrete(commitment):
    return bool(commitment.get("owner") and commitment.get("action") and
                (commitment.get("due_at") or commitment.get("expected_result")))


def derive_r02(snapshot):
    cutoff = datetime.fromisoformat(snapshot["cutoff"])
    r02 = snapshot["r02"]
    commitments = [x for x in r02["commitments"] if as_time(x["agreed_at"], cutoff) <= cutoff]
    if not commitments:
        return "NO_COMMITMENT" if r02["absence_status"] == "NO_COMMITMENT" else "UNKNOWN"
    commitments.sort(key=lambda x: as_time(x["agreed_at"], cutoff))
    current = commitments[-1]
    if not concrete(current):
        return "UNKNOWN"
    if as_time(current.get("completion_evidence_at"), cutoff) and as_time(current["completion_evidence_at"], cutoff) <= cutoff:
        return "COMPLETED"
    if as_time(current.get("explicit_missed_at"), cutoff) and as_time(current["explicit_missed_at"], cutoff) <= cutoff:
        replacements = {x.get("replaces_id") for x in commitments if concrete(x)}
        misses = sum(bool(x.get("explicit_missed_at") and concrete(x) and
                          as_time(x["explicit_missed_at"], cutoff) <= cutoff and x["commitment_id"] not in replacements)
                     for x in commitments)
        return "REPEATEDLY_MISSED" if misses >= 2 else "MISSED"
    prior = next((x for x in commitments if x["commitment_id"] == current.get("replaces_id")), None)
    if prior and prior.get("reschedule_evidence_at") and as_time(prior["reschedule_evidence_at"], cutoff) <= cutoff:
        return "RESCHEDULED_WITH_CONCRETE_REPLACEMENT"
    due = as_time(current.get("due_at"), cutoff)
    if due and due > cutoff:
        return "NOT_DUE"
    return "UNKNOWN"


if __name__ == "__main__":
    base = {"cutoff": "2026-09-25T12:00:00+03:00", "r02": {"absence_status": "UNKNOWN", "commitments": [
        {"commitment_id": "x", "agreed_at": "2026-09-24T12:00:00+03:00", "owner": "buyer", "action": "send sample", "due_at": "2026-09-25T10:00:00+03:00", "expected_result": None, "replaces_id": None, "completion_evidence_at": None, "reschedule_evidence_at": None, "explicit_missed_at": None}]}}
    assert derive_r02(base) == "UNKNOWN"  # Passing a deadline without evidence is not a confirmed miss.
    base["r02"]["commitments"][0]["explicit_missed_at"] = "2026-09-25T11:00:00+03:00"
    assert derive_r02(base) == "MISSED"
