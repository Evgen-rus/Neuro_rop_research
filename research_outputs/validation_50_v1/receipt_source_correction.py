"""Apply the previously approved receipt cutoff to one missed, pinned record."""
import hashlib
import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main():
    view = ROOT / "views/6811.jsonl"
    quality = ROOT / "dataset/deals/6811/quality.json"
    canonical = ROOT / "dataset/deals/6811/clean_timeline.jsonl"
    freeze_path = ROOT / "input_freeze.json"
    manifest_path = ROOT / "audit_manifest.json"
    before = view.read_bytes()
    assert sha(before) == "1ef4d15f02c9626ed641904df959632aa2de7b834ee400894a866908a0069900"
    assert sha(canonical.read_bytes()) == "b3bedd4b86bd2f7c3f3976b19ddeb5a0dfc476255ccbac654f6c7904dd258ba5"
    lines = before.splitlines(keepends=True)
    removed = [line for line in lines if json.loads(line)["timestamp"] >= "2026-02-24T00:00:00+03:00"]
    assert len(removed) == 1
    event = json.loads(removed[0])
    assert (event["source_line"], event["event_id"], event["content"]) == (98, "manager_worklog:2474611:0", "получена оплата 80%")
    after = b"".join(line for line in lines if line not in removed)
    frozen = json.loads(freeze_path.read_bytes())
    manifest = json.loads(manifest_path.read_bytes())
    unchanged = {}
    for row in frozen["deals"]:
        d = str(row["deal_id"])
        if d == "6811":
            continue
        unchanged[d] = {}
        for name, path, key in [("view", ROOT / f"views/{d}.jsonl", "view_sha256"), ("quality", ROOT / f"dataset/deals/{d}/quality.json", "quality_sha256"), ("neutral", ROOT / f"dataset/deals/{d}/neutral.json", "neutral_sha256")]:
            h = sha(path.read_bytes())
            assert h == row[key], (d, name)
            unchanged[d][name] = h
    q = json.loads(quality.read_bytes())
    q["limitations"].append("Some source records excluded under approved chronology/source-admissibility constraints; genuine predecision same-day/intervening-day communications may be missing.")
    qraw = encode(q)
    policy = {"status": "MISSED_APPLICATION_CORRECTED", "methodology_change": False, "basis": "Previously approved conservative completed-payment source rule; one missed receipt claim. No new terminal category.", "deal_id": "6811", "cutoff_inclusive": "2026-02-24T00:00:00+03:00", "excluded_event_id": event["event_id"], "excluded_source_line": 98, "events_removed": 1, "before_view_sha256": sha(before), "after_view_sha256": sha(after), "canonical_sha256": sha(canonical.read_bytes()), "after_quality_sha256": sha(qraw), "unchanged_input_sets": unchanged, "previous_input_freeze_sha256": sha(freeze_path.read_bytes()), "outcomes_revealed": False}
    policy_raw = encode(policy)
    manifest["receipt_source_correction_sha256"] = sha(policy_raw)
    m = next(r for r in manifest["deals"] if str(r["deal_id"]) == "6811")
    m["view"].update(sha256=sha(after), bytes=len(after))
    m["view_event_count"] -= 1
    m["removed_categories"]["receipt_source_correction"] = 1
    m["approx_tokens"]["view"] = math.ceil(len(after.decode("utf-8")) / 4)
    manifest["totals"]["view_event_count"] -= 1
    manifest["totals"]["removed_event_count"] += 1
    manifest["totals"]["removed:receipt_source_correction"] = 1
    manifest["totals"]["view_approx_tokens"] = sum(r["approx_tokens"]["view"] for r in manifest["deals"])
    manifest["filter_policy"].append("One missed completed-payment claim in6811 excluded by the previously approved day-start rule; exact correction is pinned separately. Raw/canonical retained.")
    mraw = encode(manifest)
    f = next(r for r in frozen["deals"] if str(r["deal_id"]) == "6811")
    f.update(view_sha256=sha(after), quality_sha256=sha(qraw))
    frozen.update(audit_manifest_sha256=sha(mraw), receipt_source_correction_sha256=sha(policy_raw))
    snapshot = ROOT / "stage3_pre_receipt_correction_v6"
    archive = ROOT / "audit_revisions/receipt_correction_v6"
    assert not snapshot.exists() and not archive.exists()
    snapshot.mkdir()
    for path in [view, quality, freeze_path, manifest_path]:
        target = snapshot / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    archive.mkdir()
    draft = ROOT / "audits/primary/6811.json"
    assert draft.resolve().is_relative_to(ROOT) and archive.resolve().is_relative_to(ROOT)
    if draft.exists():
        audit_raw = draft.read_bytes()
        draft.rename(archive / "6811.json")
        (archive / "index.json").write_bytes(encode({"deal_id": "6811", "audit_sha256": sha(audit_raw), "reason": "Exposed to excluded completed-payment claim; fresh audit required", "before_view_sha256": sha(before)}))
    view.write_bytes(after)
    quality.write_bytes(qraw)
    manifest_path.write_bytes(mraw)
    (ROOT / "receipt_source_correction.json").write_bytes(policy_raw)
    freeze_path.write_bytes(encode(frozen))
    print("PASS: one event removed;49 other input sets unchanged;6811 exposed draft archived; fresh audit required")


def correct_explicit_terminal_5293():
    """Exclude one missed explicit victory marker; preserve its original bytes."""
    view = ROOT / "views/5293.jsonl"
    quality = ROOT / "dataset/deals/5293/quality.json"
    freeze_path, manifest_path = ROOT / "input_freeze.json", ROOT / "audit_manifest.json"
    policy_path = ROOT / "receipt_source_correction.json"
    frozen, manifest, policy = [json.loads(p.read_bytes()) for p in [freeze_path, manifest_path, policy_path]]
    assert "explicit_terminal_5293" not in policy
    f = next(r for r in frozen["deals"] if str(r["deal_id"]) == "5293")
    before = view.read_bytes()
    assert sha(before) == f["view_sha256"] and sha(quality.read_bytes()) == f["quality_sha256"]
    lines = before.splitlines(keepends=True)
    removed = [line for line in lines if json.loads(line)["source_line"] >= 219]
    assert len(removed) == 1
    event = json.loads(removed[0])
    assert event["event_id"] == "crm_activity:543849" and event["timestamp"] == "2026-03-20T11:52:39+03:00"
    assert "УРАААА!!! ПОБЕДА!!!" in event["content"]
    assert not (ROOT / "audits/primary/5293.json").exists()
    after = b"".join(line for line in lines if line not in removed)
    snapshot = ROOT / "stage3_pre_explicit_terminal_v7"
    assert not snapshot.exists()
    snapshot.mkdir()
    for path in [view, quality, freeze_path, manifest_path, policy_path]:
        target = snapshot / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    q = json.loads(quality.read_bytes())
    q["limitations"].append("Some explicit terminal source records were excluded from the blind view; raw and canonical sources retained.")
    qraw = encode(q)
    policy["explicit_terminal_5293"] = {"events_removed": 1, "event_id": event["event_id"], "source_line": 219, "timestamp": event["timestamp"], "before_view_sha256": sha(before), "after_view_sha256": sha(after), "after_quality_sha256": sha(qraw), "canonical_sha256": f["clean_timeline_sha256"], "basis": "Existing outcome-blind rule excludes explicit terminal victory language; no new semantic category."}
    policy_raw = encode(policy)
    m = next(r for r in manifest["deals"] if str(r["deal_id"]) == "5293")
    m["view"].update(sha256=sha(after), bytes=len(after))
    m["view_event_count"] -= 1
    m["removed_categories"]["explicit_terminal_correction"] = 1
    m["approx_tokens"]["view"] = math.ceil(len(after.decode("utf-8")) / 4)
    manifest["totals"]["view_event_count"] -= 1
    manifest["totals"]["removed_event_count"] += 1
    manifest["totals"]["removed:explicit_terminal_correction"] = 1
    manifest["totals"]["view_approx_tokens"] = sum(r["approx_tokens"]["view"] for r in manifest["deals"])
    manifest["receipt_source_correction_sha256"] = sha(policy_raw)
    manifest["filter_policy"].append("One missed explicit victory marker in5293 excluded; original sources preserved in snapshotv7 and canonical timeline.")
    mraw = encode(manifest)
    f.update(view_sha256=sha(after), quality_sha256=sha(qraw))
    frozen.update(audit_manifest_sha256=sha(mraw), receipt_source_correction_sha256=sha(policy_raw))
    for path, raw in [(view, after), (quality, qraw), (manifest_path, mraw), (policy_path, policy_raw), (freeze_path, encode(frozen))]:
        path.write_bytes(raw)
    print("PASS:5293 explicit terminal marker removed; one event; fresh audit required")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--explicit-terminal-5293"]:
        correct_explicit_terminal_5293()
    else:
        assert not sys.argv[1:]
        main()
