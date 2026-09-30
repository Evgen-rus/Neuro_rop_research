"""Create dataset_v2 by linking current local practice transcripts to v1 calls."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import types
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parents[2]
PRACTICE = Path(r"D:\My_dev_project\Neuro_rop_practice")
V1 = ROOT / "dataset"
V2 = ROOT / "dataset_v2"
OUT = ROOT / "research_outputs" / "deal_audit_v2"
THRESHOLD = 36.0
NO_AUDIO_STATUSES = {"no_files_check_expired", "no_files_in_crm_activity", "audio_unavailable", "missing_audio"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def practice_duration_reader():
    """Load the practice project's exact manifest parser without its logger/audio stack."""
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(PRACTICE))
    stub = types.ModuleType("openai_api.audio.transcribe_core")
    stub.get_audio_duration_seconds = lambda *_: None
    sys.modules[stub.__name__] = stub
    from openai_api.audio.short_call import load_recording_durations

    return load_recording_durations


def audio_paths(deal_id: str) -> list[Path]:
    return [
        PRACTICE / "reports" / "bitrix_customer_path" / "audio" / f"deal_{deal_id}_call_audio_manifest.json",
        PRACTICE / "reports" / "rop_assistant" / "deals" / f"deal_{deal_id}" / "audio" / f"deal_{deal_id}_call_audio_manifest.json",
    ]


def audio_statuses(paths: list[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        try:
            payload = read_json(path)
        except (OSError, ValueError):
            continue
        rows = payload.get("calls") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("audio_kind") == "max_voice":
                continue
            activity_id = str(row.get("activity_id") or "").strip()
            if activity_id and activity_id not in result:
                result[activity_id] = str(row.get("status") or "unknown")
    return result


def transcript_sources(deal_id: str) -> dict[str, tuple[Path, dict]]:
    folder = PRACTICE / "reports" / "rop_assistant" / "deals" / f"deal_{deal_id}" / "transcripts"
    by_id: dict[str, tuple[Path, dict]] = {}
    if not folder.is_dir():
        return by_id
    for path in sorted(folder.glob("*_transcript.json"), key=lambda item: item.name):
        payload = read_json(path)
        metadata = payload.get("metadata") if isinstance(payload, dict) else None
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("deal_id") or metadata.get("entity_id") or "") != deal_id:
            continue
        activity_id = str(metadata.get("activity_id") or "").strip()
        text = payload.get("text")
        if not activity_id or not isinstance(text, str) or not text.strip():
            continue
        previous = by_id.get(activity_id)
        if previous and previous[1].get("text") != text:
            raise ValueError(f"Conflicting local transcript files: deal {deal_id}, activity {activity_id}")
        by_id[activity_id] = (path, payload)
    return by_id


def event_rows(path: Path) -> tuple[list[dict], list[str], str]:
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    lines = [line for line in raw.decode("utf-8-sig").splitlines() if line.strip()]
    return [json.loads(line) for line in lines], lines, newline


def bind_transcripts(deal_id: str, timeline: Path, source_rows: dict[str, tuple[Path, dict]]) -> dict:
    events, raw_lines, newline = event_rows(timeline)
    call_rows: dict[str, int] = {}
    transcript_rows: dict[str, list[int]] = defaultdict(list)
    for index, event in enumerate(events):
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        activity_id = str(metadata.get("activity_id") or "").strip()
        if event.get("event_type") == "call" and activity_id:
            if activity_id in call_rows:
                raise ValueError(f"Duplicate call activity in v1: deal {deal_id}, activity {activity_id}")
            call_rows[activity_id] = index
        elif event.get("event_type") == "call_transcript" and activity_id:
            transcript_rows[activity_id].append(index)

    updated: list[str] = []
    added: list[str] = []
    unlinked = sorted(set(source_rows) - set(call_rows))
    replacements: dict[int, dict] = {}
    insert_after: dict[int, list[dict]] = defaultdict(list)

    for activity_id, (_, payload) in source_rows.items():
        if activity_id not in call_rows:
            continue
        call_index = call_rows[activity_id]
        call = events[call_index]
        source_meta = payload.get("metadata") or {}
        text = str(payload["text"]).strip()
        call_with_transcript = dict(call)
        call_metadata = dict(call.get("metadata") or {})
        call_metadata["has_transcript"] = True
        call_with_transcript["metadata"] = call_metadata
        replacements[call_index] = call_with_transcript
        for index in transcript_rows.get(activity_id, []):
            current = dict(events[index])
            metadata = dict(current.get("metadata") or {})
            metadata["has_transcript"] = True
            duration = source_meta.get("audio_duration_seconds")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                metadata["audio_duration_seconds"] = duration
            model = source_meta.get("transcription_model")
            if model:
                metadata["transcription_model"] = model
            current["metadata"] = metadata
            current["content"] = text
            replacements[index] = current
            if current != events[index]:
                updated.append(activity_id)

        if not transcript_rows.get(activity_id):
            current = dict(call)
            metadata = dict(call.get("metadata") or {})
            metadata["has_transcript"] = True
            duration = source_meta.get("audio_duration_seconds")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                metadata["audio_duration_seconds"] = duration
            model = source_meta.get("transcription_model")
            if model:
                metadata["transcription_model"] = model
            current["metadata"] = metadata
            current["event_type"] = "call_transcript"
            current["content"] = text
            insert_after[call_index].append(current)
            added.append(activity_id)

    output_lines: list[str] = []
    for index, (event, raw) in enumerate(zip(events, raw_lines)):
        replacement = replacements.get(index)
        output_lines.append(json.dumps(replacement, ensure_ascii=False, separators=(",", ":")) if replacement else raw)
        output_lines.extend(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in insert_after.get(index, []))
    timeline.write_bytes((newline.join(output_lines) + newline).encode("utf-8"))
    return {"added": sorted(set(added)), "updated": sorted(set(updated)), "unlinked": unlinked}


def build_quality(deal_id: str, timeline: Path, durations: dict[str, float], statuses: dict[str, str]) -> dict:
    events, _, _ = event_rows(timeline)
    calls = [event for event in events if event.get("event_type") == "call"]
    ids = [str((event.get("metadata") or {}).get("activity_id") or "").strip() for event in calls]
    if any(not activity_id for activity_id in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"Missing or duplicate call activity_id in deal {deal_id}")
    transcript_ids = {
        str((event.get("metadata") or {}).get("activity_id") or "")
        for event in events if event.get("event_type") == "call_transcript"
    }
    measured = {activity_id: durations[activity_id] for activity_id in ids if activity_id in durations}
    eligible = {activity_id for activity_id, duration in measured.items() if duration >= THRESHOLD}
    unknown_ids = set(ids) - set(measured)
    unavailable = {activity_id for activity_id in unknown_ids if statuses.get(activity_id, "unknown") in NO_AUDIO_STATUSES}
    return {
        "events": len(events),
        "calls": len(calls),
        "transcripts_linked": sum(event.get("event_type") == "call_transcript" and str((event.get("metadata") or {}).get("activity_id") or "") in set(ids) for event in events),
        "total_calls": len(calls),
        "calls_with_measured_audio": len(measured),
        "calls_lt_36": sum(duration < THRESHOLD for duration in measured.values()),
        "eligible_calls_ge_36": len(eligible),
        "eligible_calls_with_transcript": len(eligible & transcript_ids),
        "eligible_calls_without_transcript": len(eligible - transcript_ids),
        "calls_audio_unavailable": len(unavailable),
        "calls_unknown_duration": len(unknown_ids),
        "calls_unknown_audio_availability": len(unknown_ids - unavailable),
        "audio_status_counts": dict(sorted(Counter(statuses.get(activity_id, "unknown") for activity_id in ids).items())),
    }


def approx_tokens(byte_count: int) -> int:
    return math.ceil(byte_count / 4)


def rebuild_summary(dataset: Path, prior: dict, quality: dict[str, dict]) -> dict:
    outcomes = {item["deal_id"]: item["outcome"] for item in prior["deals"]}
    deals = []
    groups: dict[str, list[dict]] = {"WON": [], "LOST": []}
    for folder in sorted((dataset / "deals").iterdir(), key=lambda item: int(item.name)):
        events, _, _ = event_rows(folder / "clean_timeline.jsonl")
        byte_counts = Counter()
        for event in events:
            event_type = event.get("event_type")
            category = "transcript" if event_type == "call_transcript" else event_type if event_type in {"message", "email"} else "other"
            byte_counts[category] += len(str(event.get("content") or "").encode("utf-8"))
        row = {
            "deal_id": folder.name,
            "outcome": outcomes[folder.name],
            "tokens": sum(approx_tokens(byte_counts[key]) for key in ("transcript", "message", "email", "other")),
            "transcript": approx_tokens(byte_counts["transcript"]),
            "message": approx_tokens(byte_counts["message"]),
            "email": approx_tokens(byte_counts["email"]),
            "other": approx_tokens(byte_counts["other"]),
            "events": len(events),
            "calls_ge36_without_transcript": quality[folder.name]["eligible_calls_without_transcript"],
        }
        deals.append(row)
        groups[row["outcome"]].append(row)
    ordered = sorted(row["tokens"] for row in deals)
    totals = {"all": sum(row["tokens"] for row in deals), "median": (ordered[11] + ordered[12]) / 2}
    for outcome, rows in groups.items():
        totals[outcome] = {"n": len(rows), **{key: sum(row[key] for row in rows) for key in ("tokens", "transcript", "message", "email", "other")}}
    return {
        "token_method": "ceil(UTF-8 content bytes / 4), matching the audit-view size proxy; v1 summary tokenizer implementation was not present, so token totals are not directly comparable across versions.",
        "deals": deals,
        "totals": totals,
    }


def build_views_and_diff(changes: dict[str, dict], quality: dict[str, dict]) -> None:
    v1_output = ROOT / "research_outputs" / "deal_audit_v1"
    contract = (v1_output / "input_contract.md").read_text(encoding="utf-8")
    (OUT / "input_contract.md").write_text(contract.replace("dataset/deals/", "dataset_v2/deals/"), encoding="utf-8")
    shutil.copyfile(v1_output / "audit_schema.json", OUT / "audit_schema.json")

    spec = importlib.util.spec_from_file_location("v1_audit_view_builder", v1_output / "build_audit_views.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    module.OUT_DIR = OUT
    module.DEALS_DIR = V2 / "deals"
    module.VIEWS_DIR = OUT / "views"
    if module.main() != 0:
        raise RuntimeError("Outcome-blind audit view build failed")

    v1_views = read_json(v1_output / "audit_manifest.json")
    v2_views = read_json(OUT / "audit_manifest.json")
    previous = {row["deal_id"]: row for row in v1_views["deals"]}
    current = {row["deal_id"]: row for row in v2_views["deals"]}
    dataset_changes = []
    view_changes = []
    for deal_id in sorted(changes, key=int):
        paths = [
            ("neutral.json", V1 / "deals" / deal_id / "neutral.json", V2 / "deals" / deal_id / "neutral.json"),
            ("clean_timeline.jsonl", V1 / "deals" / deal_id / "clean_timeline.jsonl", V2 / "deals" / deal_id / "clean_timeline.jsonl"),
        ]
        hashes = {}
        fields = []
        for label, old_path, new_path in paths:
            old_hash, new_hash = sha256(old_path.read_bytes()), sha256(new_path.read_bytes())
            hashes[label] = {"v1": old_hash, "v2": new_hash}
            if old_hash != new_hash:
                fields.append(label)
        dataset_changes.append({"deal_id": deal_id, "changed": bool(fields), "changed_fields": fields, "sha256": hashes, **changes[deal_id], "build_quality": quality[deal_id]})
        old_hash = previous[deal_id].get("view", {}).get("sha256")
        new_hash = current[deal_id].get("view", {}).get("sha256")
        view_changes.append({"deal_id": deal_id, "changed": old_hash != new_hash, "v1_view_sha256": old_hash, "v2_view_sha256": new_hash})
    changed_dataset_ids = [row["deal_id"] for row in dataset_changes if row["changed"]]
    changed_view_ids = [row["deal_id"] for row in view_changes if row["changed"]]
    diff = {"version": "2.0", "deals": dataset_changes, "changed_deal_ids": changed_dataset_ids, "changed_outcome_blind_view_ids": changed_view_ids}
    (OUT / "dataset_diff.json").write_text(json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    frozen_views = [{"deal_id": deal_id, "path": current[deal_id]["view"]["path"], "sha256": current[deal_id]["view"]["sha256"]} for deal_id in sorted(current, key=int) if current[deal_id].get("view")]
    freeze = {
        "status": "v2_outcome_blind_views_frozen_before_semantic_audit",
        "outcome_revealed": False,
        "deal_count": len(current),
        "audit_schema_sha256": sha256((OUT / "audit_schema.json").read_bytes()),
        "input_contract_sha256": sha256((OUT / "input_contract.md").read_bytes()),
        "audit_manifest_sha256": sha256((OUT / "audit_manifest.json").read_bytes()),
        "views": frozen_views,
    }
    (OUT / "input_freeze.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if (OUT / "audit_manifest.json").exists():
        raise FileExistsError("deal_audit_v2 outputs already exist; refusing overwrite")
    folders = sorted((V1 / "deals").iterdir(), key=lambda item: int(item.name))
    if len(folders) != 23:
        raise ValueError(f"Expected 23 v1 deal folders, found {len(folders)}")
    if V2.exists():
        source_paths = {path.relative_to(V1) for path in V1.rglob("*")}
        target_paths = {path.relative_to(V2) for path in V2.rglob("*")}
        if source_paths != target_paths:
            raise FileExistsError("Existing dataset_v2 contains unexpected paths; refusing to overwrite it")
        shutil.copytree(V1, V2, dirs_exist_ok=True)
    else:
        shutil.copytree(V1, V2)

    load_recording_durations = practice_duration_reader()
    old_quality = read_json(V1 / "build_quality.json")
    old_summary = read_json(V1 / "summary.json")
    changes: dict[str, dict] = {}
    quality: dict[str, dict] = {}

    for folder in folders:
        deal_id = folder.name
        paths = audio_paths(deal_id)
        durations = load_recording_durations(paths)
        statuses = audio_statuses(paths)
        timeline = V2 / "deals" / deal_id / "clean_timeline.jsonl"
        source_rows = transcript_sources(deal_id)

        # Saved transcript metadata records measured source-audio duration when a manifest copy omits it.
        events, _, _ = event_rows(timeline)
        call_ids = {str((event.get("metadata") or {}).get("activity_id") or "") for event in events if event.get("event_type") == "call"}
        for event in events:
            if event.get("event_type") != "call_transcript":
                continue
            metadata = event.get("metadata") or {}
            activity_id = str(metadata.get("activity_id") or "")
            duration = metadata.get("audio_duration_seconds")
            if activity_id in call_ids and activity_id not in durations and isinstance(duration, (int, float)) and not isinstance(duration, bool):
                durations[activity_id] = float(duration)
        for activity_id, (_, payload) in source_rows.items():
            duration = (payload.get("metadata") or {}).get("audio_duration_seconds")
            if activity_id in call_ids and activity_id not in durations and isinstance(duration, (int, float)) and not isinstance(duration, bool):
                durations[activity_id] = float(duration)

        changes[deal_id] = bind_transcripts(deal_id, timeline, source_rows)
        row = dict(old_quality.get(deal_id) or {})
        row.update(build_quality(deal_id, timeline, durations, statuses))
        row["practice_transcripts_unlinked"] = changes[deal_id]["unlinked"]
        quality[deal_id] = row

    totals = {key: sum(row[key] for row in quality.values()) for key in (
        "total_calls", "calls_with_measured_audio", "calls_lt_36", "eligible_calls_ge_36",
        "eligible_calls_with_transcript", "eligible_calls_without_transcript", "calls_audio_unavailable",
        "calls_unknown_duration", "calls_unknown_audio_availability",
    )}
    totals["audio_status_counts"] = dict(sorted(sum((Counter(row["audio_status_counts"]) for row in quality.values()), Counter()).items()))
    totals["ready_for_rebuild"] = totals["eligible_calls_without_transcript"] == 0
    quality["global"] = totals
    (V2 / "build_quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (V2 / "summary.json").write_text(json.dumps(rebuild_summary(V2, old_summary, quality), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not totals["ready_for_rebuild"]:
        print(json.dumps({"ready": False, "global": totals}, ensure_ascii=False))
        return 1
    if (totals["total_calls"], totals["calls_with_measured_audio"], totals["calls_lt_36"], totals["eligible_calls_ge_36"], totals["calls_unknown_duration"]) != (806, 463, 126, 337, 343):
        raise RuntimeError(f"Call completeness totals differ from the verified pre-build state: {totals}")

    build_views_and_diff(changes, quality)
    manifest_unchanged = (V2 / "manifest.json").read_bytes() == (V1 / "manifest.json").read_bytes()
    run = {
        "version": "2.0",
        "source": "v1 dataset plus current local practice transcript JSON linked by activity_id",
        "transcript_source": str(PRACTICE / "reports" / "rop_assistant" / "deals" / "deal_<id>" / "transcripts"),
        "call_duration_rule": "Neuro_rop_practice.openai_api.audio.short_call.load_recording_durations; transcript audio_duration_seconds used only when manifest duration is absent; eligible threshold >=36 seconds",
        "manifest_unchanged": manifest_unchanged,
        "global_call_completeness": totals,
        "transcript_delta": {deal_id: row for deal_id, row in changes.items() if row["added"] or row["updated"] or row["unlinked"]},
        "limitations": ["Calls without measured audio duration remain unknown and are not eligible by default.", "Summary token estimates use UTF-8 bytes/4 because the v1 summary tokenizer source was not present; do not compare token totals across versions."],
    }
    (OUT / "run_manifest.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    diff = read_json(OUT / "dataset_diff.json")
    print(json.dumps({"ready": True, "global": totals, "changed_deal_ids": diff["changed_deal_ids"], "changed_outcome_blind_view_ids": diff["changed_outcome_blind_view_ids"], "manifest_unchanged": manifest_unchanged}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
