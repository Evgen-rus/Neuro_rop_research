"""Outcome-blind structural and evidence-pointer checks for Stage 4 audits."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PHASES = ("primary", "secondary", "final")
EXPECTED_DEALS = 50


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> tuple[Any, bytes]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), raw


def valid_deal_id(value: Any) -> bool:
    return isinstance(value, str) and value.isdecimal() and int(value) > 0 and str(int(value)) == value


def validate_value(value: Any, spec: Any, path: str, errors: list[str]) -> None:
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return
        for key, child_spec in spec.items():
            if key not in value:
                errors.append(f"{path}.{key}: missing required field")
            else:
                validate_value(value[key], child_spec, f"{path}.{key}", errors)
        for key in value.keys() - spec.keys():
            errors.append(f"{path}.{key}: unexpected field")
        return

    if isinstance(spec, list):
        if not isinstance(value, list):
            errors.append(f"{path}: expected array")
            return
        if spec:
            for index, item in enumerate(value):
                validate_value(item, spec[0], f"{path}[{index}]", errors)
        return

    if isinstance(spec, int) and not isinstance(spec, bool):
        minimum = 0 if spec == 0 else 1
        if type(value) is not int or value < minimum:
            errors.append(f"{path}: expected integer >= {minimum}")
        return

    if isinstance(spec, str):
        choices = spec.split("|")
        type_names = {"string", "boolean", "integer", "number", "null"}
        literals = [choice for choice in choices if choice not in type_names]
        type_ok = any(
            (choice == "string" and isinstance(value, str))
            or (choice == "boolean" and type(value) is bool)
            or (choice == "integer" and type(value) is int)
            or (choice == "number" and type(value) in (int, float))
            or (choice == "null" and value is None)
            for choice in choices
        )
        literal_ok = bool(literals) and isinstance(value, str) and value in literals
        if not type_ok and not literal_ok:
            errors.append(f"{path}: expected {spec}")
        return

    errors.append(f"{path}: unsupported schema rule")


def parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a nonempty string")
    result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return result


def read_view(path: Path, deal_id: str, errors: list[str]) -> tuple[dict[int, dict[str, Any]], bytes]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
    except OSError as exc:
        errors.append(f"view {deal_id}: cannot read ({type(exc).__name__})")
        return {}, b""
    except UnicodeDecodeError:
        errors.append(f"view {deal_id}: invalid UTF-8")
        return {}, raw

    events: dict[int, dict[str, Any]] = {}
    for physical_line, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"view {deal_id}:{physical_line}: invalid JSON")
            continue
        if not isinstance(event, dict):
            errors.append(f"view {deal_id}:{physical_line}: expected object")
            continue
        source_line = event.get("source_line")
        if type(source_line) is not int or source_line < 1:
            errors.append(f"view {deal_id}:{physical_line}: invalid source_line")
            continue
        if source_line in events:
            errors.append(f"view {deal_id}:{physical_line}: duplicate source_line {source_line}")
            continue
        if not isinstance(event.get("event_type"), str) or not event["event_type"]:
            errors.append(f"view {deal_id}:{physical_line}: invalid event_type")
        try:
            parse_timestamp(event.get("timestamp"))
        except (TypeError, ValueError):
            errors.append(f"view {deal_id}:{physical_line}: invalid timestamp")
        if "event_id" in event and event["event_id"] is not None and not isinstance(event["event_id"], str):
            errors.append(f"view {deal_id}:{physical_line}: invalid event_id")
        events[source_line] = event
    return events, raw


def validate_terminal_source_policy(
    root: Path,
    input_freeze: dict[str, Any],
    manifest: dict[str, Any],
    views: dict[str, dict[int, dict[str, Any]]],
    errors: list[str],
) -> None:
    policy_path = root / "terminal_source_policy.json"
    if not policy_path.exists():
        if input_freeze.get("terminal_source_policy_sha256") is not None or manifest.get("terminal_source_policy_sha256") is not None:
            errors.append("terminal source policy pin exists but policy file is missing")
        return
    try:
        policy_raw = policy_path.read_bytes()
        policy = json.loads(policy_raw.decode("utf-8-sig"))
        cohort_raw = (root / "cohort.json").read_bytes()
        proposal_raw = (root / "terminal_source_policy_proposal.json").read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"terminal source policy: cannot load ({type(exc).__name__})")
        return
    if not isinstance(policy, dict) or policy.get("schema_version") != 1 or policy.get("user_approved") is not True:
        errors.append("terminal source policy is not an approved version 1 policy")
        return
    policy_hash = digest(policy_raw)
    if digest(cohort_raw) != policy.get("cohort_sha256"):
        errors.append("cohort hash differs from terminal source policy")
    if digest(proposal_raw) != policy.get("proposal_sha256"):
        errors.append("proposal hash differs from terminal source policy")
    if input_freeze.get("terminal_source_policy_sha256") != policy_hash:
        errors.append("terminal source policy hash differs from input freeze")
    if manifest.get("terminal_source_policy_sha256") != policy_hash:
        errors.append("terminal source policy hash differs from audit manifest")
    if policy.get("expected_affected_deals") != 20 or policy.get("expected_events_removed") != 71:
        errors.append("terminal source policy has unexpected approved counts")

    rows = policy.get("deals")
    if not isinstance(rows, list) or len(rows) != 20:
        errors.append("terminal source policy must contain exactly 20 deals")
        return
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        deal_id = row.get("deal_id") if isinstance(row, dict) else None
        if not valid_deal_id(deal_id) or deal_id in by_id or deal_id not in views:
            errors.append("terminal source policy has an invalid, duplicate, or unknown deal_id")
            continue
        by_id[deal_id] = row
    if len(by_id) != 20:
        return

    removed_total = 0
    for deal_id, row in by_id.items():
        for key in ("expected_prefilter_view_sha256", "expected_canonical_timeline_sha256"):
            if not isinstance(row.get(key), str) or len(row[key]) != 64 or any(char not in "0123456789abcdef" for char in row[key]):
                errors.append(f"terminal source policy {deal_id}: invalid {key}")
        before, removed, after = (row.get(key) for key in ("expected_view_events_before", "expected_events_removed", "expected_events_after"))
        if any(type(value) is not int or value < 0 for value in (before, removed, after)) or before - after != removed:
            errors.append(f"terminal source policy {deal_id}: inconsistent event counts")
            continue
        removed_total += removed
        cutoff_value = row.get("cutoff_inclusive")
        try:
            cutoff = parse_timestamp(cutoff_value) if cutoff_value is not None else None
        except (TypeError, ValueError):
            errors.append(f"terminal source policy {deal_id}: invalid inclusive cutoff")
            continue

        timeline_path = root / "dataset" / "deals" / deal_id / "clean_timeline.jsonl"
        try:
            timeline_raw = timeline_path.read_bytes()
            timeline_text = timeline_raw.decode("utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"terminal source policy {deal_id}: canonical timeline unavailable ({type(exc).__name__})")
            continue
        if digest(timeline_raw) != row.get("expected_canonical_timeline_sha256"):
            errors.append(f"terminal source policy {deal_id}: canonical timeline hash mismatch")
        canonical: dict[int, dict[str, Any]] = {}
        for source_line, line in enumerate(timeline_text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"terminal source policy {deal_id}:{source_line}: invalid canonical JSON")
                continue
            if isinstance(event, dict):
                canonical[source_line] = event

        pins = row.get("source_pins")
        if not isinstance(pins, list):
            errors.append(f"terminal source policy {deal_id}: invalid source pins")
            pins = []
        for pin in pins:
            source_line = pin.get("source_line") if isinstance(pin, dict) else None
            event = canonical.get(source_line) if type(source_line) is int else None
            if (
                not isinstance(pin, dict)
                or pin.get("view_matches_canonical") is not True
                or event is None
                or event.get("event_id") != pin.get("source_id")
                or event.get("timestamp") != pin.get("timestamp")
                or digest(str(event.get("content") or "").encode("utf-8")) != pin.get("content_sha256")
            ):
                errors.append(f"terminal source policy {deal_id}: source pin mismatch at line {source_line!r}")

        banned_ids: set[str] = set()
        quarantine = row.get("quarantine_events")
        if not isinstance(quarantine, list):
            errors.append(f"terminal source policy {deal_id}: invalid quarantine list")
            quarantine = []
        for item in quarantine:
            source_line = item.get("source_line") if isinstance(item, dict) else None
            event = canonical.get(source_line) if type(source_line) is int else None
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("event_id"), str)
                or event is None
                or event.get("event_id") != item.get("event_id")
                or digest(str(event.get("content") or "").encode("utf-8")) != item.get("content_sha256")
            ):
                errors.append(f"terminal source policy {deal_id}: quarantine source mismatch at line {source_line!r}")
            else:
                banned_ids.add(item["event_id"])

        view = views[deal_id]
        if len(view) != after:
            errors.append(f"terminal source policy {deal_id}: filtered view count differs from policy")
        for event in view.values():
            if event.get("event_id") in banned_ids:
                errors.append(f"view {deal_id}: quarantined event remains")
            if cutoff is not None:
                try:
                    if parse_timestamp(event.get("timestamp")) >= cutoff:
                        errors.append(f"view {deal_id}: event at or after approved cutoff remains")
                except (TypeError, ValueError):
                    pass
    if removed_total != 71:
        errors.append("terminal source policy per-deal removed-event counts do not total 71")


def check_evidence(
    deal_id: str,
    audit: dict[str, Any],
    view: dict[int, dict[str, Any]],
    errors: list[str],
) -> None:
    evidence = audit.get("evidence")
    if not isinstance(evidence, list):
        return
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            continue
        source_line = item.get("source_line")
        event = view.get(source_line) if type(source_line) is int else None
        where = f"audit {deal_id}.evidence[{index}]"
        if event is None:
            errors.append(f"{where}: source_line {source_line!r} not in view")
            continue
        try:
            same_time = parse_timestamp(event.get("timestamp")) == parse_timestamp(item.get("timestamp"))
        except (TypeError, ValueError):
            same_time = False
        if not same_time:
            errors.append(f"{where}: timestamp differs from view")
        if item.get("event_type") != event.get("event_type"):
            errors.append(f"{where}: event_type differs from view")
        if item.get("event_id") != event.get("event_id"):
            errors.append(f"{where}: event_id differs from view")


def check_indices(deal_id: str, audit: dict[str, Any], errors: list[str]) -> None:
    evidence = audit.get("evidence")
    if not isinstance(evidence, list):
        return
    claims = [("primary_trajectory_explanation", audit.get("primary_trajectory_explanation"))]
    points = audit.get("turning_points")
    if isinstance(points, list):
        claims.extend((f"turning_points[{i}]", point) for i, point in enumerate(points) if isinstance(point, dict))
    for label, claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("evidence_indices"), list):
            continue
        for index in claim["evidence_indices"]:
            if type(index) is not int or not 0 <= index < len(evidence):
                errors.append(f"audit {deal_id}.{label}: evidence index {index!r} out of bounds")


def validate_audit(
    audit_path: Path,
    deal_id: str,
    required: dict[str, Any],
    view: dict[int, dict[str, Any]],
    errors: list[str],
) -> bytes | None:
    """Validate one arrival-time audit without requiring its cohort peers."""
    if audit_path.stem != deal_id:
        errors.append(f"audit {deal_id}: filename stem differs from deal ID")
    try:
        audit, raw = load_json(audit_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"audit {deal_id}: cannot load ({type(exc).__name__})")
        return None
    if not isinstance(audit, dict):
        errors.append(f"audit {deal_id}: expected object")
        return None
    validate_value(audit, required, f"audit {deal_id}", errors)
    if audit.get("deal_id") != deal_id:
        errors.append(f"audit {deal_id}: deal_id differs from filename")
    check_evidence(deal_id, audit, view, errors)
    check_indices(deal_id, audit, errors)
    return raw


def validate_phase(
    phase: str,
    root: Path = HERE,
    freeze_output: Path | None = None,
    deal_ids: list[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if phase not in PHASES:
        return {"status": "FAIL", "errors": [f"unknown audit phase: {phase}"]}
    files: dict[str, bytes] = {}
    try:
        schema, files["schema"] = load_json(root / "audit_schema.json")
        input_freeze, files["input_freeze"] = load_json(root / "input_freeze.json")
        manifest, files["audit_manifest"] = load_json(root / "audit_manifest.json")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "errors": [f"input metadata: {type(exc).__name__}: {exc}"]}

    if not isinstance(schema, dict) or not isinstance(schema.get("required"), dict):
        return {"status": "FAIL", "errors": ["audit_schema.json has no required object schema"]}
    if schema.get("blind_to_outcome") is not True:
        errors.append("audit_schema.json is not outcome-blind")
    required = schema["required"]
    if not isinstance(input_freeze, dict) or not isinstance(manifest, dict):
        return {"status": "FAIL", "errors": ["input freeze or audit manifest is not an object"]}

    if input_freeze.get("status") != "validation_50_v1_outcome_blind_views_frozen_before_semantic_audit":
        errors.append("input_freeze.json has an unexpected status")
    if input_freeze.get("outcome_blind_views") is not True or input_freeze.get("outcome_labels_separate_from_views") is not True:
        errors.append("input_freeze.json does not assert outcome-blind inputs")
    if input_freeze.get("baseline_overlap_count") != 0 or input_freeze.get("deal_count") != EXPECTED_DEALS:
        errors.append("input_freeze.json has invalid cohort count or baseline overlap")
    if input_freeze.get("audit_schema_sha256") != digest(files["schema"]):
        errors.append("audit_schema.json hash differs from input freeze")
    if input_freeze.get("audit_manifest_sha256") != digest(files["audit_manifest"]):
        errors.append("audit_manifest.json hash differs from input freeze")
    if "worklog_quarantine_policy_sha256" in input_freeze:
        try:
            policy_raw = (root / "worklog_quarantine_policy.json").read_bytes()
        except OSError as exc:
            errors.append(f"worklog quarantine policy: cannot read ({type(exc).__name__})")
        else:
            if digest(policy_raw) != input_freeze["worklog_quarantine_policy_sha256"]:
                errors.append("worklog quarantine policy hash differs from input freeze")
            try:
                policy = json.loads(policy_raw.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                errors.append("worklog quarantine policy is invalid JSON")
            else:
                if not isinstance(policy, dict) or policy.get("user_approved") is not True:
                    errors.append("worklog quarantine policy is not user-approved")

    if manifest.get("complete") is not True or manifest.get("blind_to_outcome") is not True:
        errors.append("audit_manifest.json is not complete and outcome-blind")
    if manifest.get("expected_deal_count") != EXPECTED_DEALS or manifest.get("deal_count") != EXPECTED_DEALS:
        errors.append("audit_manifest.json has an invalid deal count")

    frozen_rows = input_freeze.get("deals")
    manifest_rows = manifest.get("deals")
    if not isinstance(frozen_rows, list) or not isinstance(manifest_rows, list):
        return {"status": "FAIL", "errors": errors + ["input freeze or audit manifest has no deals list"]}

    frozen_by_id: dict[str, dict[str, Any]] = {}
    for row in frozen_rows:
        deal_id = row.get("deal_id") if isinstance(row, dict) else None
        if not valid_deal_id(deal_id) or deal_id in frozen_by_id:
            errors.append("input_freeze.json has an invalid or duplicate deal_id")
        else:
            frozen_by_id[deal_id] = row
    manifest_by_id: dict[str, dict[str, Any]] = {}
    for row in manifest_rows:
        deal_id = row.get("deal_id") if isinstance(row, dict) else None
        if not valid_deal_id(deal_id) or deal_id in manifest_by_id:
            errors.append("audit_manifest.json has an invalid or duplicate deal_id")
        else:
            manifest_by_id[deal_id] = row

    views_dir = root / "views"
    view_paths = sorted(views_dir.glob("*.jsonl"), key=lambda p: int(p.stem) if p.stem.isdecimal() else 0) if views_dir.is_dir() else []
    view_ids = [path.stem for path in view_paths]
    if any(not valid_deal_id(deal_id) for deal_id in view_ids) or len(view_ids) != len(set(view_ids)):
        errors.append("views directory has invalid or duplicate deal filenames")
    expected_ids = set(view_ids)
    if len(view_ids) != EXPECTED_DEALS:
        errors.append(f"expected {EXPECTED_DEALS} view files, found {len(view_ids)}")
    if set(frozen_by_id) != expected_ids:
        errors.append("input freeze deal IDs differ from view filenames")
    if set(manifest_by_id) != expected_ids:
        errors.append("audit manifest deal IDs differ from view filenames")

    if phase == "secondary":
        if deal_ids is None:
            errors.append("secondary requires an explicit 12-15 ID --deal-ids subset")
            selected_ids = expected_ids
        else:
            if not 12 <= len(deal_ids) <= 15:
                errors.append("secondary --deal-ids must contain 12-15 IDs")
            if any(not valid_deal_id(deal_id) for deal_id in deal_ids) or len(deal_ids) != len(set(deal_ids)):
                errors.append("secondary --deal-ids must be unique positive deal IDs")
            selected_ids = set(deal_ids)
            if not selected_ids <= expected_ids:
                errors.append("secondary --deal-ids must come from the frozen view deal list")
    else:
        selected_ids = expected_ids
        if deal_ids is not None:
            errors.append("--deal-ids is allowed only for secondary audits")

    view_events: dict[str, dict[int, dict[str, Any]]] = {}
    view_hashes: dict[str, str] = {}
    quality_hashes: dict[str, str] = {}
    for path in view_paths:
        deal_id = path.stem
        view, raw = read_view(path, deal_id, errors)
        view_events[deal_id] = view
        view_hashes[deal_id] = digest(raw)
        frozen = frozen_by_id.get(deal_id, {})
        if frozen.get("view_sha256") != view_hashes[deal_id]:
            errors.append(f"view {deal_id}: hash differs from input freeze")
        manifest_row = manifest_by_id.get(deal_id, {})
        if manifest_row.get("status") != "ok":
            errors.append(f"view {deal_id}: audit manifest status is not ok")
        view_meta = manifest_row.get("view") if isinstance(manifest_row.get("view"), dict) else {}
        if view_meta.get("path") != f"views/{deal_id}.jsonl" or view_meta.get("sha256") != view_hashes[deal_id]:
            errors.append(f"view {deal_id}: audit manifest path/hash mismatch")

        quality_path = root / "dataset" / "deals" / deal_id / "quality.json"
        try:
            quality, quality_raw = load_json(quality_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"quality {deal_id}: cannot load ({type(exc).__name__})")
            continue
        if not isinstance(quality, dict) or quality.get("deal_id") != deal_id:
            errors.append(f"quality {deal_id}: deal_id mismatch")
        quality_hashes[deal_id] = digest(quality_raw)
        if frozen.get("quality_sha256") != quality_hashes[deal_id]:
            errors.append(f"quality {deal_id}: hash differs from input freeze")

    validate_terminal_source_policy(root, input_freeze, manifest, view_events, errors)

    audit_dir = root / "audits" / phase
    audit_paths = sorted(audit_dir.glob("*.json"), key=lambda p: int(p.stem) if p.stem.isdecimal() else 0) if audit_dir.is_dir() else []
    audit_ids = [path.stem for path in audit_paths]
    if not audit_dir.is_dir():
        errors.append(f"audit directory missing: {audit_dir}")
    if any(not valid_deal_id(deal_id) for deal_id in audit_ids) or len(audit_ids) != len(set(audit_ids)):
        errors.append(f"{phase} audit directory has invalid or duplicate filenames")
    if set(audit_ids) != selected_ids:
        errors.append(f"{phase} audits must contain exactly one JSON for each selected deal")

    audit_hashes: dict[str, str] = {}
    for path in audit_paths:
        deal_id = path.stem
        raw = validate_audit(path, deal_id, required, view_events.get(deal_id, {}), errors)
        if raw is not None:
            audit_hashes[deal_id] = digest(raw)

    result: dict[str, Any] = {
        "status": "PASS" if not errors else "FAIL",
        "phase": phase,
        "deal_count": len(selected_ids),
        "input_deal_count": len(view_ids),
        "errors": errors,
    }
    if errors or freeze_output is None:
        return result

    target = freeze_output if freeze_output.is_absolute() else root / freeze_output
    resolved_root, resolved_target = root.resolve(), target.resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError:
        result["status"] = "FAIL"
        result["errors"] = ["freeze output must be inside validation_50_v1"]
        return result
    try:
        resolved_target.relative_to((root / "audits").resolve())
    except ValueError:
        pass
    else:
        result["status"] = "FAIL"
        result["errors"] = ["freeze output must be outside all audit directories"]
        return result
    freeze = {
        "status": f"validation_50_v1_{phase}_audits_frozen_before_outcome",
        "outcome_revealed": False,
        "phase": phase,
        "deal_count": len(selected_ids),
        "selected_deal_ids": sorted(selected_ids, key=int),
        "audit_schema_sha256": digest(files["schema"]),
        "input_freeze_sha256": digest(files["input_freeze"]),
        "audit_manifest_sha256": digest(files["audit_manifest"]),
        "files": [
            {
                "deal_id": deal_id,
                "audit_path": (root / "audits" / phase / f"{deal_id}.json").relative_to(root).as_posix(),
                "audit_sha256": audit_hashes[deal_id],
                "view_path": f"views/{deal_id}.jsonl",
                "view_sha256": view_hashes[deal_id],
                "quality_path": f"dataset/deals/{deal_id}/quality.json",
                "quality_sha256": quality_hashes[deal_id],
            }
            for deal_id in sorted(selected_ids, key=int)
        ],
    }
    try:
        with target.open("x", encoding="utf-8") as stream:
            json.dump(freeze, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except (FileExistsError, OSError) as exc:
        result["status"] = "FAIL"
        result["errors"] = [f"cannot create fresh freeze output ({type(exc).__name__})"]
        return result
    result["freeze_output"] = str(target)
    return result


def self_check() -> None:
    schema_path = HERE / "audit_schema.json"
    if not schema_path.is_file():
        schema_path = HERE.parent / "deal_audit_v2" / "audit_schema.json"
    schema, schema_raw = load_json(schema_path)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "views").mkdir()
        (root / "dataset" / "deals").mkdir(parents=True)
        (root / "audits" / "primary").mkdir(parents=True)
        ids = [str(value) for value in range(1, EXPECTED_DEALS + 1)]
        frozen_rows, manifest_rows, audit_hashes = [], [], []
        for deal_id in ids:
            event = {"timestamp": "2026-01-01T10:00:00+03:00", "event_type": "comment", "event_id": f"event-{deal_id}", "source_line": 3}
            view_raw = (json.dumps(event) + "\n").encode("utf-8")
            view_path = root / "views" / f"{deal_id}.jsonl"
            view_path.write_bytes(view_raw)
            quality_path = root / "dataset" / "deals" / deal_id / "quality.json"
            quality_path.parent.mkdir(parents=True)
            quality_raw = json.dumps({"deal_id": deal_id}).encode("utf-8")
            quality_path.write_bytes(quality_raw)
            audit = {
                "deal_id": deal_id,
                "deal_summary": "summary",
                "customer_need": {"summary": "need", "confidence": "medium"},
                "deal_dynamics": {"early": "", "middle": "", "late": ""},
                "customer_behavior": {"positive_signals": [], "negative_signals": [], "initiative": "", "decision_process": ""},
                "manager_behavior": {"strong_actions": [], "weak_actions": [], "follow_up_quality": "", "next_step_control": ""},
                "turning_points": [{"timestamp": event["timestamp"], "description": "point", "importance": "medium", "evidence_indices": [0]}],
                "primary_trajectory_explanation": {"category": "unknown", "explanation": "explanation", "controllability": "unknown", "confidence": "low", "evidence_indices": [0]},
                "secondary_factors": [],
                "manager_influence": {"could_materially_improve": None, "what_could_be_done": [], "limits": []},
                "evidence": [{**event, "paraphrase": "event paraphrase"}],
                "uncertainties": [],
            }
            audit_raw = json.dumps(audit, ensure_ascii=False).encode("utf-8")
            (root / "audits" / "primary" / f"{deal_id}.json").write_bytes(audit_raw)
            audit_hashes.append(digest(audit_raw))
            frozen_rows.append({"deal_id": deal_id, "view_sha256": digest(view_raw), "quality_sha256": digest(quality_raw)})
            manifest_rows.append({"deal_id": deal_id, "status": "ok", "view": {"path": f"views/{deal_id}.jsonl", "sha256": digest(view_raw)}})
        manifest = {"complete": True, "blind_to_outcome": True, "expected_deal_count": 50, "deal_count": 50, "deals": manifest_rows}
        cohort_raw, proposal_raw = b"synthetic cohort", b"synthetic proposal"
        (root / "cohort.json").write_bytes(cohort_raw)
        (root / "terminal_source_policy_proposal.json").write_bytes(proposal_raw)
        policy_deals = []
        for index, deal_id in enumerate(ids[:20], start=1):
            removed = 4 if index <= 17 else 1
            cutoff = "2026-01-02T10:00:00+03:00"
            pin_event = {"timestamp": "2026-01-01T09:00:00+03:00", "event_type": "stage_change", "event_id": f"pin-{deal_id}", "source": "crm", "content": "Pinned source", "metadata": {}}
            timeline_events = [pin_event, {"timestamp": "2026-01-01T09:30:00+03:00", "event_type": "stage_change", "event_id": f"stage-{deal_id}", "source": "crm", "content": "Stage", "metadata": {}}]
            view_event = json.loads((root / "views" / f"{deal_id}.jsonl").read_text(encoding="utf-8"))
            timeline_events.append({**view_event, "source": "crm", "content": "Retained", "metadata": {}})
            removed_events = []
            for suffix in range(removed):
                event = {"timestamp": cutoff, "event_type": "comment", "event_id": f"cutoff-{deal_id}-{suffix}", "source": "crm", "content": "At cutoff", "metadata": {}, "source_line": len(timeline_events) + 1}
                timeline_events.append({key: value for key, value in event.items() if key != "source_line"})
                removed_events.append(event)
            timeline_raw = b"".join((json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8") for event in timeline_events)
            timeline_path = root / "dataset" / "deals" / deal_id / "clean_timeline.jsonl"
            timeline_path.write_bytes(timeline_raw)
            prefilter_events = [view_event, *removed_events]
            prefilter_raw = b"".join((json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for event in prefilter_events)
            policy_deals.append({
                "deal_id": deal_id,
                "expected_prefilter_view_sha256": digest(prefilter_raw),
                "expected_canonical_timeline_sha256": digest(timeline_raw),
                "cutoff_inclusive": cutoff,
                "quarantine_events": [],
                "source_pins": [{"source_line": 1, "source_id": pin_event["event_id"], "timestamp": pin_event["timestamp"], "content_sha256": digest(pin_event["content"].encode("utf-8")), "view_matches_canonical": True}],
                "expected_view_events_before": 1 + removed,
                "expected_events_removed": removed,
                "expected_events_after": 1,
            })
        policy = {
            "schema_version": 1,
            "user_approved": True,
            "proposal_sha256": digest(proposal_raw),
            "cohort_sha256": digest(cohort_raw),
            "expected_affected_deals": 20,
            "expected_events_removed": 71,
            "deals": policy_deals,
        }
        policy_raw = json.dumps(policy, ensure_ascii=False, sort_keys=True).encode("utf-8")
        (root / "terminal_source_policy.json").write_bytes(policy_raw)
        manifest["terminal_source_policy_sha256"] = digest(policy_raw)
        manifest_raw = json.dumps(manifest).encode("utf-8")
        (root / "audit_manifest.json").write_bytes(manifest_raw)
        (root / "audit_schema.json").write_bytes(schema_raw)
        input_freeze = {
            "status": "validation_50_v1_outcome_blind_views_frozen_before_semantic_audit",
            "outcome_blind_views": True,
            "outcome_labels_separate_from_views": True,
            "baseline_overlap_count": 0,
            "deal_count": 50,
            "audit_schema_sha256": digest(schema_raw),
            "audit_manifest_sha256": digest(manifest_raw),
            "terminal_source_policy_sha256": digest(policy_raw),
            "deals": frozen_rows,
        }
        (root / "input_freeze.json").write_text(json.dumps(input_freeze), encoding="utf-8")
        policy_raw = json.dumps({"user_approved": True}).encode("utf-8")
        (root / "worklog_quarantine_policy.json").write_bytes(policy_raw)
        input_freeze["worklog_quarantine_policy_sha256"] = digest(policy_raw)
        (root / "input_freeze.json").write_text(json.dumps(input_freeze), encoding="utf-8")
        first_freeze = root / "primary_freeze.json"
        passed = validate_phase("primary", root, first_freeze)
        assert passed["status"] == "PASS", passed["errors"][:3]
        pinned_freeze = json.loads((root / "input_freeze.json").read_text(encoding="utf-8"))
        pinned_manifest = json.loads((root / "audit_manifest.json").read_text(encoding="utf-8"))
        policy_path = root / "terminal_source_policy.json"
        policy_bytes = policy_path.read_bytes()
        missing_pin_freeze = {key: value for key, value in pinned_freeze.items() if key != "terminal_source_policy_sha256"}
        policy_errors: list[str] = []
        validate_terminal_source_policy(root, missing_pin_freeze, pinned_manifest, {}, policy_errors)
        assert any("hash differs from input freeze" in item for item in policy_errors)
        wrong_pin_manifest = {**pinned_manifest, "terminal_source_policy_sha256": "0" * 64}
        policy_errors = []
        validate_terminal_source_policy(root, pinned_freeze, wrong_pin_manifest, {}, policy_errors)
        assert any("hash differs from audit manifest" in item for item in policy_errors)
        policy_path.unlink()
        policy_errors = []
        validate_terminal_source_policy(root, pinned_freeze, pinned_manifest, {}, policy_errors)
        assert any("policy file is missing" in item for item in policy_errors)
        legacy_freeze = {key: value for key, value in pinned_freeze.items() if key != "terminal_source_policy_sha256"}
        legacy_manifest = {key: value for key, value in pinned_manifest.items() if key != "terminal_source_policy_sha256"}
        policy_errors = []
        validate_terminal_source_policy(root, legacy_freeze, legacy_manifest, {}, policy_errors)
        assert not policy_errors
        policy_path.write_bytes(policy_bytes)
        (root / "worklog_quarantine_policy.json").write_text('{"user_approved": false}', encoding="utf-8")
        policy_changed = validate_phase("primary", root)
        assert policy_changed["status"] == "FAIL" and any("worklog quarantine policy hash" in item for item in policy_changed["errors"])
        (root / "worklog_quarantine_policy.json").unlink()
        policy_missing = validate_phase("primary", root)
        assert policy_missing["status"] == "FAIL" and any("worklog quarantine policy: cannot read" in item for item in policy_missing["errors"])
        (root / "worklog_quarantine_policy.json").write_bytes(policy_raw)
        frozen_bytes = first_freeze.read_bytes()
        overwritten = validate_phase("primary", root, first_freeze)
        assert overwritten["status"] == "FAIL" and first_freeze.read_bytes() == frozen_bytes
        audit_path = root / "audits" / "primary" / "1.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["evidence"][0]["event_id"] = "different"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        blocked_freeze = root / "blocked_freeze.json"
        changed = validate_phase("primary", root, blocked_freeze)
        assert changed["status"] == "FAIL" and any("event_id differs" in item for item in changed["errors"])
        assert not blocked_freeze.exists()
        audit["evidence"][0]["event_id"] = "event-1"
        audit["primary_trajectory_explanation"]["evidence_indices"] = [50]
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        changed = validate_phase("primary", root)
        assert changed["status"] == "FAIL" and any("out of bounds" in item for item in changed["errors"])
        audit["primary_trajectory_explanation"]["evidence_indices"] = [0]
        audit_path.write_text(json.dumps(audit), encoding="utf-8")

        secondary_dir = root / "audits" / "secondary"
        secondary_dir.mkdir()
        subset = ids[:12]
        for deal_id in subset:
            source = root / "audits" / "primary" / f"{deal_id}.json"
            (secondary_dir / source.name).write_bytes(source.read_bytes())
        partial_errors: list[str] = []
        sample_id = subset[0]
        sample_audit = secondary_dir / f"{sample_id}.json"
        sample_view, _ = read_view(root / "views" / f"{sample_id}.jsonl", sample_id, partial_errors)
        validate_audit(sample_audit, sample_id, schema["required"], sample_view, partial_errors)
        assert not partial_errors
        secondary_freeze = root / "secondary_freeze.json"
        secondary = validate_phase("secondary", root, secondary_freeze, subset)
        assert secondary["status"] == "PASS" and secondary["deal_count"] == 12 and secondary["input_deal_count"] == 50, secondary["errors"][:3]
        assert len(json.loads(secondary_freeze.read_text(encoding="utf-8"))["files"]) == 12
        assert validate_phase("secondary", root)["status"] == "FAIL"
        assert validate_phase("secondary", root, deal_ids=ids[:11])["status"] == "FAIL"
        assert validate_phase("secondary", root, deal_ids=ids[:16])["status"] == "FAIL"
        assert validate_phase("primary", root, deal_ids=subset)["status"] == "FAIL"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Stage 4 deal audits against frozen outcome-blind views")
    parser.add_argument("phase", nargs="?", choices=PHASES, help="audit directory under audits/: primary, secondary, or final")
    parser.add_argument("--deal-ids", help="comma-separated frozen deal IDs (secondary only; 12-15 unique IDs)")
    parser.add_argument("--freeze-output", type=Path, help="write a fresh audit freeze only after all checks pass")
    parser.add_argument("--self-check", action="store_true", help="run the offline validator self-check")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        print(json.dumps({"status": "PASS", "self_check": True}))
        return 0
    if not args.phase:
        parser.error("phase is required unless --self-check is used")
    deal_ids = [part.strip() for part in args.deal_ids.split(",")] if args.deal_ids is not None else None
    result = validate_phase(args.phase, HERE, args.freeze_output, deal_ids)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
