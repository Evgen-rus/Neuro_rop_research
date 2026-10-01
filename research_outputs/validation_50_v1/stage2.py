"""Resumable, cohort-bounded Stage 2 runner. Raw inputs and transcripts stay private."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "_private"
DEFAULT_PRACTICE = Path(r"D:\My_dev_project\Neuro_rop_practice")
RAW_DIR = PRIVATE / "raw"
AUDIO_DIR = PRIVATE / "audio"
DB_PATH = PRIVATE / "crm.sqlite"
WORKSPACES_DIR = PRIVATE / "workspaces"
COMPLETENESS_PATH = HERE / "completeness.json"
ACTION_LOG = PRIVATE / "logs" / "stage2_actions.jsonl"


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def cohort_ids(path: Path) -> list[str]:
    frozen = read_json(HERE / "run_manifest.json")
    expected = (frozen or {}).get("cohort_sha256")
    if not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("cohort bytes differ from the frozen Stage 1 artifact")
    data = read_json(path)
    rows = data.get("deals") if data else None
    if not isinstance(rows, list):
        raise ValueError("cohort.json has no deals list")
    ids = [str(row.get("deal_id") or "").strip() for row in rows if isinstance(row, dict)]
    if len(ids) != 50 or any(not value.isdecimal() or int(value) <= 0 for value in ids) or len(set(ids)) != 50:
        raise ValueError("cohort.json must contain exactly 50 unique positive deal IDs")
    return ids


def prepare_practice_imports(practice: Path) -> None:
    practice_path = str(practice)
    if practice_path not in sys.path:
        sys.path.insert(0, practice_path)
    import setup

    # Practice helpers initialize file loggers at import time; Stage 2 keeps its diagnostics private.
    for name in ("openai", "download_deals_call_audio"):
        logger = logging.getLogger(f"leads_to_b24.{name}")
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        logger.propagate = False


def practice_helpers(practice: Path) -> tuple[Any, Any, Any, Any]:
    prepare_practice_imports(practice)
    from bitrix.customer_history import build_deal_normalized_communications
    from bitrix.deals.download_deals_call_audio import call_activities
    from openai_api.audio.short_call import SHORT_CALL_MAX_SECONDS
    from openai_api.audio.transcribe_core import get_audio_duration_seconds

    return build_deal_normalized_communications, call_activities, SHORT_CALL_MAX_SECONDS, get_audio_duration_seconds


def practice_voice_helpers(practice: Path) -> tuple[Any, Any, Any, Any, Any, Any]:
    prepare_practice_imports(practice)
    from bitrix.context_sync import atomic_json
    from bitrix.customer_history import build_history_sections
    from bitrix.deals.download_deals_call_audio import (
        existing_downloads_by_activity,
        existing_transcriptions_by_activity,
        max_voice_messages,
        process_max_voice,
    )

    return build_history_sections, max_voice_messages, process_max_voice, existing_downloads_by_activity, existing_transcriptions_by_activity, atomic_json


def root_source_voice_messages(
    deal_id: str,
    bundle: dict[str, Any],
    build_communications: Any,
    build_history_sections: Any,
    max_voice_messages: Any,
) -> list[dict[str, Any]]:
    deal = bundle.get("deal") or {}
    source_lead = bundle.get("source_lead") or {}
    lead_id = str(source_lead.get("lead_id") or "")
    histories: dict[str, Any] = {
        f"deal:{deal_id}": {
            "entity_type": "deal",
            "entity_id": deal_id,
            "activities": bundle.get("activities") or {},
            "activity_details": bundle.get("activity_details") or {},
            "timeline_comments": bundle.get("timeline_comments") or [],
        }
    }
    if lead_id:
        histories[f"lead:{lead_id}"] = {**source_lead, "entity_type": "lead", "entity_id": lead_id}
    adapted = {
        "root_entity": {"type": "deal", "id": deal_id},
        "deal": deal,
        "lead": source_lead.get("lead"),
        "activities_by_entity": histories,
    }
    adapted.update(build_history_sections(adapted))
    history = {
        "internal_context": adapted.get("internal_context") or [],
        "normalized_communications": build_communications(bundle),
    }
    allowed = {("deal", deal_id)}
    if lead_id:
        allowed.add(("lead", lead_id))
    return [
        message for message in max_voice_messages(history, lookback_days=3650)
        if (str(message.get("entity_type") or ""), str(message.get("entity_id") or "")) in allowed
    ]


def voice_sources_complete(bundle: dict[str, Any]) -> bool:
    deal = bundle.get("deal") or {}
    if not response_ok(deal.get("response")):
        return False
    if not any(response_ok(row) for row in bundle.get("timeline_comments") or [] if isinstance(row, dict)):
        return False
    source_lead = bundle.get("source_lead")
    if isinstance(source_lead, dict) and source_lead.get("lead_id"):
        return bool(source_lead.get("activity_fetch_ok")) and response_ok((source_lead.get("lead") or {}).get("response")) and any(
            response_ok(row) for row in source_lead.get("timeline_comments") or [] if isinstance(row, dict)
        )
    return True


def voice_row_matches(row: dict[str, Any], deal_id: str, message: dict[str, Any]) -> bool:
    entity_type = str(message.get("entity_type") or "")
    owner_id = str(message.get("entity_id") or "")
    allowed = {deal_id}
    if entity_type == "lead":
        allowed.add(owner_id)
    return (
        entity_type in {"deal", "lead"}
        and owner_id in allowed
        and row.get("audio_kind") == "max_voice"
        and str(row.get("activity_id") or "") == str(message.get("activity_id") or "")
        and str(row.get("owner_id") or "") == owner_id
        and str(row.get("timeline_comment_id") or "") == str(message.get("timeline_comment_id") or "")
        and str(row.get("url_fingerprint") or "") == str(message.get("url_fingerprint") or "")
    )


def voice_manifest_rows(
    paths: list[Path], deal_id: str, messages: list[dict[str, Any]]
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    expected = {str(message.get("activity_id") or ""): message for message in messages}
    result: dict[str, list[dict[str, Any]]] = {}
    invalid: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        data = read_json(path)
        if not data or str(data.get("deal_id") or "") != deal_id or not isinstance(data.get("calls"), list):
            invalid.append(path.name)
            continue
        for row in data["calls"]:
            if not isinstance(row, dict) or row.get("audio_kind") != "max_voice":
                continue
            activity_id = str(row.get("activity_id") or "")
            message = expected.get(activity_id)
            if message and voice_row_matches(row, deal_id, message):
                result.setdefault(activity_id, []).append(row)
    return result, invalid


def voice_facts(
    deal_id: str,
    messages: list[dict[str, Any]],
    manifest_rows: dict[str, list[dict[str, Any]]],
    workspace_roots: list[Path],
    transcription_diagnostics: dict[str, str] | None = None,
) -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    counts = Counter()
    residual: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []
    for message in messages:
        activity_id = str(message.get("activity_id") or "")
        rows = manifest_rows.get(activity_id, [])
        audio_available = any(
            isinstance(download, dict)
            and download.get("ok")
            and download.get("local_path")
            and Path(str(download["local_path"])).is_file()
            for row in rows
            for download in row.get("downloads") or []
        )
        has_transcript = bool(activity_id) and transcript_files(deal_id, activity_id, workspace_roots, rows)
        counts["voice_message_count"] += 1
        counts["with_transcript"] += int(has_transcript)
        counts["audio_unavailable"] += int(not audio_available)
        counts["decoding_failed"] += int(
            not has_transcript and (transcription_diagnostics or {}).get(activity_id) == "conversion_error"
        )
        if audio_available and not has_transcript:
            counts["missing_available_transcript"] += 1
            residual.append({"activity_id": activity_id, "reason": "transcript_missing", "audio_available": True})
            limitations.append({"activity_id": activity_id, "issue": "transcript_missing", "has_transcript": False})
        elif not audio_available:
            counts["unavailable"] += int(not has_transcript)
            limitations.append({"activity_id": activity_id, "issue": "audio_unavailable", "has_transcript": has_transcript})
            if not has_transcript:
                residual.append({"activity_id": activity_id, "reason": "audio_unavailable", "audio_available": False})
        if not activity_id:
            counts["missing_activity_id"] += 1
            residual.append({"activity_id": None, "reason": "missing_activity_id", "audio_available": audio_available})
    for name in (
        "voice_message_count", "with_transcript", "missing_available_transcript", "unavailable",
        "audio_unavailable", "missing_activity_id", "decoding_failed",
    ):
        counts.setdefault(name, 0)
    return dict(counts), residual, limitations


def voice_scan_complete(
    scan: dict[str, Any], raw_path: Path, messages: list[dict[str, Any]], voice_rows: dict[str, list[dict[str, Any]]]
) -> bool:
    try:
        raw_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    except OSError:
        return False
    expected_ids = {str(message.get("activity_id") or "") for message in messages}
    return (
        scan.get("checked") is True
        and scan.get("source_complete") is True
        and scan.get("lookback_days") == 3650
        and scan.get("discovered_messages") == len(messages)
        and scan.get("processed_messages") == len(messages)
        and scan.get("raw_context_sha256") == raw_sha256
        and expected_ids <= set(voice_rows)
    )


def voice_audio_path(rows: list[dict[str, Any]]) -> Path | None:
    for row in rows:
        for download in row.get("downloads") or []:
            if isinstance(download, dict) and download.get("ok") and download.get("local_path"):
                path = Path(str(download["local_path"]))
                if path.is_file():
                    return path
    return None


def private_manifest_base(path: Path, deal_id: str) -> dict[str, Any]:
    if not path.exists():
        return {"deal_id": deal_id, "calls": []}
    data = read_json(path)
    if not data or str(data.get("deal_id") or "") != deal_id or not isinstance(data.get("calls"), list):
        raise ValueError("private audio manifest is invalid or belongs to another deal")
    return data


def run_voices(
    ids: list[str],
    practice: Path,
    communication_helpers: tuple[Any, Any, Any, Any],
    voice_helpers: tuple[Any, Any, Any, Any, Any, Any],
) -> tuple[int, int]:
    build_communications = communication_helpers[0]
    build_history_sections, max_voice_messages, process_max_voice = voice_helpers[:3]
    existing_downloads_by_activity, existing_transcriptions_by_activity, atomic_json = voice_helpers[3:]
    practice_audio = practice / "reports" / "bitrix_customer_path" / "audio"
    practice_workspaces = practice / "reports" / "rop_assistant" / "deals"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["BITRIX_DENY_WRITE_METHODS"] = "1"
    os.environ.update({key: env[key] for key in ("PYTHONDONTWRITEBYTECODE", "BITRIX_DENY_WRITE_METHODS")})
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    succeeded = failures = 0
    for deal_id in ids:
        raw_path = RAW_DIR / f"deal_{deal_id}_context.json"
        raw = read_json(raw_path)
        if not raw:
            failures += 1
            print(json.dumps({"action": "voices", "deal_id": deal_id, "status": "missing_raw_context"}), flush=True)
            continue
        messages = root_source_voice_messages(deal_id, raw, build_communications, build_history_sections, max_voice_messages)
        raw_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        source_complete = voice_sources_complete(raw) and not (raw.get("sync") or {}).get("retry_required")
        private_manifest = AUDIO_DIR / f"deal_{deal_id}_call_audio_manifest.json"
        try:
            base = private_manifest_base(private_manifest, deal_id)
        except ValueError:
            failures += 1
            log_action("voices", [{"deal_id": deal_id}], 1, "invalid_private_manifest")
            print(json.dumps({"action": "voices", "deal_id": deal_id, "status": "invalid_private_manifest"}), flush=True)
            continue

        non_voice_rows = [row for row in base["calls"] if not isinstance(row, dict) or row.get("audio_kind") != "max_voice"]
        cached_rows, invalid = voice_manifest_rows([private_manifest, practice_audio / private_manifest.name], deal_id, messages)
        cache_ids = {activity_id: rows for activity_id, rows in cached_rows.items()}
        processed: dict[str, dict[str, Any]] = {}
        process_failures = 0

        def save(checked: bool) -> None:
            base["calls"] = non_voice_rows + list(processed.values())
            base["stage2_voice_scan"] = {
                "checked": checked,
                "source_complete": source_complete,
                "lookback_days": 3650,
                "discovered_messages": len(messages),
                "processed_messages": len(processed),
                "processing_failures": process_failures,
                "raw_context_sha256": raw_sha256,
            }
            atomic_json(private_manifest, base)

        save(False)
        for message in messages:
            activity_id = str(message.get("activity_id") or "")
            cached = cache_ids.get(activity_id, [])
            cached_transcriptions = existing_transcriptions_by_activity({"calls": cached})
            transcription = cached_transcriptions.get(activity_id)
            if transcription and not transcript_files(
                deal_id, activity_id, [WORKSPACES_DIR, practice_workspaces], cached
            ):
                transcription = None
            downloads = existing_downloads_by_activity({"calls": cached}).get(activity_id)
            try:
                row = process_max_voice(
                    AUDIO_DIR / f"deal_{deal_id}",
                    message,
                    existing_downloads=downloads,
                    existing_transcription=transcription,
                    missing_only=True,
                )
                if not voice_row_matches(row, deal_id, message):
                    raise ValueError("practice voice row linkage mismatch")
                processed[activity_id] = row
                available = voice_audio_path([row]) is not None
                transcribed = transcript_files(deal_id, activity_id, [WORKSPACES_DIR, practice_workspaces], [row])
                log_action(
                    "voices",
                    [{"deal_id": deal_id, "activity_id": activity_id}],
                    0 if available or transcribed else 1,
                    "audio_available" if available else "transcribed_audio_purged" if transcribed else "audio_unavailable",
                )
            except Exception as error:
                process_failures += 1
                processed[activity_id] = {
                    "activity_id": activity_id,
                    "audio_kind": "max_voice",
                    "channel": "max",
                    "owner_type_id": "2",
                    "owner_id": str(message.get("entity_id") or ""),
                    "timeline_comment_id": str(message.get("timeline_comment_id") or ""),
                    "url_fingerprint": str(message.get("url_fingerprint") or ""),
                    "status": "process_error",
                    "downloads": [{"ok": False, "status": "process_error"}],
                }
                log_action("voices", [{"deal_id": deal_id, "activity_id": activity_id}], 1, type(error).__name__)
            save(False)
        checked = source_complete and len(processed) == len(messages)
        save(checked)
        voice_counts, _, _ = voice_facts(
            deal_id,
            messages,
            {activity_id: [row] for activity_id, row in processed.items()},
            [WORKSPACES_DIR, practice_workspaces],
        )
        succeeded += int(checked and process_failures == 0 and not invalid)
        failures += int(not checked or process_failures > 0 or bool(invalid))
        log_action("voices", [{"deal_id": deal_id}], 0 if checked and process_failures == 0 else 1, "completed" if checked and process_failures == 0 else "incomplete")
        print(json.dumps({
            "action": "voices",
            "deal_id": deal_id,
            "status": "checked" if checked else "incomplete",
            "voice_message_count": len(messages),
            "processed": len(processed),
            "processing_failures": process_failures,
            "invalid_cached_manifests": len(invalid),
            "with_transcript": voice_counts["with_transcript"],
            "missing_available_transcript": voice_counts["missing_available_transcript"],
            "unavailable": voice_counts["unavailable"],
        }), flush=True)
    return succeeded, failures


def local_call_ids(bundle: dict[str, Any], call_activities: Any) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for index, call in enumerate(call_activities(bundle)):
        activity_id = str(call.get("ID") or "").strip()
        if not activity_id:
            rows[f"missing-id-{index + 1}"] = {**call, "_missing_activity_id": True}
            continue
        if activity_id not in rows:
            rows[activity_id] = dict(call)
        else:
            rows[activity_id].setdefault("_sources", set()).add(str(call.get("_source") or "unknown"))
    return list(rows.values())


def manifest_calls(paths: list[Path]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    result: dict[str, list[dict[str, Any]]] = {}
    invalid: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        data = read_json(path)
        if not data or not isinstance(data.get("calls"), list):
            invalid.append(path.name)
            continue
        for row in data["calls"]:
            if not isinstance(row, dict) or row.get("audio_kind") == "max_voice":
                continue
            activity_id = str(row.get("activity_id") or "").strip()
            if activity_id:
                result.setdefault(activity_id, []).append(row)
    return result, invalid


def transcript_files(
    deal_id: str,
    activity_id: str,
    workspace_roots: list[Path],
    manifest_rows: list[dict[str, Any]],
) -> bool:
    for row in manifest_rows:
        transcription = row.get("transcription")
        path = Path(str((transcription or {}).get("transcript_json_path") or "")) if isinstance(transcription, dict) else None
        if (
            isinstance(transcription, dict)
            and transcription.get("status") == "transcribed_and_purged"
            and path
            and valid_transcript(path, deal_id, activity_id)
        ):
            return True
    for root in workspace_roots:
        transcript_dir = root / f"deal_{deal_id}" / "transcripts"
        if not transcript_dir.is_dir():
            continue
        # The existing transcriber names bundles call_<activity_id>_*.json.
        prefix = f"call_{activity_id}_"
        for metadata_path in transcript_dir.glob(prefix + "*.json"):
            stem = metadata_path.with_suffix("")
            if valid_transcript(metadata_path, deal_id, activity_id) and stem.with_suffix(".txt").is_file() and stem.with_suffix(".md").is_file():
                return True
    return False


def valid_transcript(path: Path, deal_id: str, activity_id: str) -> bool:
    data = read_json(path)
    metadata = data.get("metadata") if data else None
    if not isinstance(metadata, dict):
        return False
    linked_deal = str(metadata.get("deal_id") or metadata.get("entity_id") or "")
    return (
        str(metadata.get("entity_type") or "deal") == "deal"
        and linked_deal == deal_id
        and str(metadata.get("activity_id") or "") == activity_id
        and isinstance(data.get("text"), str)
        and bool(data["text"].strip())
    )


def call_facts(
    *,
    deal_id: str,
    calls: list[dict[str, Any]],
    manifest_rows: dict[str, list[dict[str, Any]]],
    workspace_roots: list[Path],
    threshold: float,
    get_audio_duration_seconds: Any,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for call in calls:
        activity_id = str(call.get("ID") or "").strip()
        rows = manifest_rows.get(activity_id, [])
        durations: list[tuple[float, bool]] = []
        audio_candidates: list[tuple[float, bool, Path]] = []
        audio_path: Path | None = None
        recording_incomplete = False
        expected_durations: list[float] = []
        for manifest_call in rows:
            call_is_short = manifest_call.get("call_quality") == "short_no_answer"
            recording_incomplete = recording_incomplete or manifest_call.get("call_quality") == "recording_incomplete"
            transcription = manifest_call.get("transcription")
            if isinstance(transcription, dict):
                value = transcription.get("source_duration_seconds")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    durations.append((float(value), call_is_short))
            for download in manifest_call.get("downloads") or []:
                if not isinstance(download, dict) or not download.get("ok") or not download.get("local_path"):
                    continue
                candidate = Path(str(download["local_path"]))
                if not candidate.is_file():
                    continue
                if audio_path is None:
                    audio_path = candidate
                expected = download.get("expected_call_duration_seconds")
                if isinstance(expected, (int, float)) and not isinstance(expected, bool):
                    expected_durations.append(float(expected))
                download_incomplete = download.get("recording_stability_status") == "duration_incomplete"
                recording_incomplete = recording_incomplete or download_incomplete
                duration = download.get("duration_seconds")
                short = (bool(download.get("is_short_no_answer")) or call_is_short) and not download_incomplete
                if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                    durations.append((float(duration), short))
                    audio_candidates.append((float(duration), short, candidate))
                elif duration is None:
                    measured = get_audio_duration_seconds(candidate)
                    if isinstance(measured, (int, float)):
                        durations.append((float(measured), False))
                        audio_candidates.append((float(measured), False, candidate))
        if recording_incomplete:
            durations = [(value, False) for value, _ in durations]
            audio_candidates = [(value, False, path) for value, _, path in audio_candidates]
        duration: float | None = None
        is_short = False
        if durations:
            eligible_durations = [value for value, short in durations if value >= threshold and not short]
            if eligible_durations:
                duration = max(eligible_durations)
            else:
                duration, is_short = max(durations, key=lambda item: item[0])
                # The standard pipeline rounds to 0.1s; keep its pre-rounding flag.
        eligible_audio = [row for row in audio_candidates if not row[1] and row[0] >= threshold]
        if eligible_audio:
            audio_path = max(eligible_audio, key=lambda item: item[0])[2]
        has_transcript = bool(activity_id) and transcript_files(deal_id, activity_id, workspace_roots, rows)
        facts.append({
            "activity_id": activity_id or None,
            "source": str(call.get("_source") or "deal"),
            "call_start": str(call.get("START_TIME") or call.get("CREATED") or ""),
            "subject": str(call.get("SUBJECT") or ""),
            "audio_available": audio_path is not None,
            "audio_path": audio_path,
            "duration_seconds": duration,
            "is_short_no_answer": is_short,
            "recording_incomplete": recording_incomplete,
            "expected_call_duration_seconds": max(expected_durations) if expected_durations else None,
            "has_transcript": has_transcript,
        })
    return facts


def summarize_calls(facts: list[dict[str, Any]], threshold: float) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts = Counter()
    residual: list[dict[str, Any]] = []
    for call in facts:
        counts["total_calls"] += 1
        if call.get("recording_incomplete"):
            counts["calls_recording_incomplete"] += 1
        duration = call["duration_seconds"]
        if not call["audio_available"]:
            counts["calls_audio_unavailable"] += 1
        if duration is None:
            counts["calls_unknown_duration"] += 1
        else:
            counts["calls_with_measured_audio"] += 1
            if call["is_short_no_answer"] or duration < threshold:
                counts["calls_lt_36"] += 1
                if call.get("recording_incomplete") and duration < threshold:
                    counts["calls_lt36_incomplete"] += 1
            else:
                counts["eligible_calls_ge_36"] += 1
                if call["has_transcript"]:
                    counts["eligible_calls_with_transcript"] += 1
                else:
                    counts["eligible_calls_without_transcript"] += 1
                    residual.append({
                        "activity_id": call["activity_id"],
                        "reason": "transcript_missing" if call["audio_available"] else "eligible_audio_unavailable_and_transcript_missing",
                        "audio_available": call["audio_available"],
                    })
        if not call["activity_id"]:
            residual.append({"activity_id": None, "reason": "missing_activity_id", "audio_available": call["audio_available"]})
    for name in (
        "total_calls", "calls_with_measured_audio", "calls_lt_36", "eligible_calls_ge_36",
        "eligible_calls_with_transcript", "eligible_calls_without_transcript",
        "calls_audio_unavailable", "calls_unknown_duration",
    ):
        counts.setdefault(name, 0)
    return dict(counts), residual


def response_ok(value: Any) -> bool:
    return isinstance(value, dict) and value.get("ok") is True


def deal_quality(
    deal_id: str,
    raw_path: Path,
    private_manifest: Path,
    practice_manifest: Path,
    private_workspaces: Path,
    practice_workspaces: Path,
    helpers: tuple[Any, Any, float, Any],
    voice_helpers: tuple[Any, Any, Any, Any, Any, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    build_communications, call_activities, threshold, get_audio_duration_seconds = helpers
    failures: list[dict[str, str]] = []
    limitations: list[str] = []
    bundle = read_json(raw_path)
    if not bundle:
        return ({
            "deal_id": deal_id,
            "sources": {"raw_context": "missing_or_invalid"},
            "calls": {name: 0 for name in (
                "total_calls", "calls_with_measured_audio", "calls_lt_36", "eligible_calls_ge_36",
                "eligible_calls_with_transcript", "eligible_calls_without_transcript",
                "calls_audio_unavailable", "calls_unknown_duration",
            )},
            "max_voice": {
                "voice_message_count": 0,
                "with_transcript": 0,
                "missing_available_transcript": 0,
                "unavailable": 0,
                "audio_unavailable": 0,
                "scan_status": "not_checked",
            },
            "data_quality": "incomplete",
        }, [{"deal_id": deal_id, "source": "raw_context", "reason": "missing_or_invalid"}], [])

    deal = bundle.get("deal") or {}
    if (bundle.get("sync") or {}).get("retry_required"):
        failures.append({"deal_id": deal_id, "source": "crm_context_sync", "reason": "retry_required"})
    card_ok = response_ok(deal.get("response")) and str((deal.get("item") or {}).get("ID") or "") == deal_id
    activities = bundle.get("activities") or {}
    stage = bundle.get("stage_history") or {}
    timeline = bundle.get("timeline_comments") or []
    timeline_ok = any(response_ok(row) for row in timeline if isinstance(row, dict))
    source_lead = bundle.get("source_lead")
    lead_status = "not_linked"
    if isinstance(source_lead, dict) and source_lead.get("lead_id"):
        lead_ok = bool(source_lead.get("activity_fetch_ok")) and response_ok((source_lead.get("lead") or {}).get("response"))
        lead_timeline = source_lead.get("timeline_comments") or []
        lead_ok = lead_ok and any(response_ok(row) for row in lead_timeline if isinstance(row, dict))
        lead_status = "ok" if lead_ok else "failed"
        if not lead_ok:
            failures.append({"deal_id": deal_id, "source": "source_lead.crm.activity.list_or_crm.timeline.comment.list", "reason": "source_not_ok"})

    task_map = bundle.get("bitrix_tasks") or {}
    activities_list = activities.get("items") if isinstance(activities.get("items"), list) else []
    task_ids = {
        str(item.get("ASSOCIATED_ENTITY_ID"))
        for item in activities_list
        if isinstance(item, dict) and str(item.get("PROVIDER_ID") or "").upper() == "CRM_TASKS_TASK" and item.get("ASSOCIATED_ENTITY_ID")
    }
    task_failures = [task_id for task_id in task_ids if not response_ok(task_map.get(task_id))]
    if task_failures:
        failures.append({"deal_id": deal_id, "source": "tasks.task.get", "reason": "source_not_ok"})

    for source, ok in (
        ("crm.deal.get", card_ok),
        ("crm.activity.list", response_ok(activities)),
        ("crm.stagehistory.list", response_ok(stage)),
        ("crm.timeline.comment.list", timeline_ok),
    ):
        if not ok:
            failures.append({"deal_id": deal_id, "source": source, "reason": "source_not_ok"})

    manifests, invalid_manifests = manifest_calls([private_manifest, practice_manifest])
    if invalid_manifests:
        failures.append({"deal_id": deal_id, "source": "call_audio_manifest", "reason": "invalid_json"})
    calls = local_call_ids(bundle, call_activities)
    unchecked_calls = [str(call.get("ID") or "") for call in calls if str(call.get("ID") or "") not in manifests]
    if unchecked_calls:
        failures.append({"deal_id": deal_id, "source": "call_audio_manifest", "reason": "activities_not_checked", "activity_ids": unchecked_calls})
    facts = call_facts(
        deal_id=deal_id,
        calls=calls,
        manifest_rows=manifests,
        workspace_roots=[private_workspaces, practice_workspaces],
        threshold=float(threshold),
        get_audio_duration_seconds=get_audio_duration_seconds,
    )
    if any(not fact["activity_id"] for fact in facts):
        failures.append({"deal_id": deal_id, "source": "crm.activity.list", "reason": "call_activity_id_missing"})
    call_counts, residual = summarize_calls(facts, float(threshold))
    call_diagnostics = latest_transcription_diagnostics(
        deal_id, [str(row.get("activity_id") or "") for row in residual]
    )
    for row in residual:
        activity_id = str(row.get("activity_id") or "")
        row["latest_transcription_diagnostic"] = call_diagnostics.get(activity_id, "unknown")
    call_data_limitations = [
        {"activity_id": fact["activity_id"], "issue": issue, "has_transcript": fact["has_transcript"]}
        for fact in facts
        for issue, applies in (
            ("audio_unavailable", not fact["audio_available"]),
            ("duration_unknown", fact["duration_seconds"] is None),
        )
        if applies
    ]
    call_data_limitations.extend({
        "activity_id": fact["activity_id"],
        "issue": "recording_incomplete",
        "has_transcript": fact["has_transcript"],
        "measured_duration_seconds": fact["duration_seconds"],
        "expected_call_duration_seconds": fact["expected_call_duration_seconds"],
    } for fact in facts if fact["recording_incomplete"])
    call_data_limitations.extend({
        "activity_id": row.get("activity_id"),
        "issue": "transcript_missing",
        "has_transcript": False,
        "latest_transcription_diagnostic": row["latest_transcription_diagnostic"],
    } for row in residual if row.get("reason") in (
        "transcript_missing", "eligible_audio_unavailable_and_transcript_missing"
    ))
    has_audio_manifest = any(path.is_file() and read_json(path) is not None for path in (private_manifest, practice_manifest))
    if call_counts["total_calls"] and not has_audio_manifest:
        failures.append({"deal_id": deal_id, "source": "call_audio_manifest", "reason": "not_checked"})
    build_history_sections, max_voice_messages = voice_helpers[:2]
    messages = root_source_voice_messages(deal_id, bundle, build_communications, build_history_sections, max_voice_messages)
    voice_rows, invalid_voice_manifests = voice_manifest_rows([private_manifest, practice_manifest], deal_id, messages)
    for _name in invalid_voice_manifests:
        failures.append({"deal_id": deal_id, "source": "max_voice_manifest", "reason": "invalid_json_or_owner"})
    voice_scan = (read_json(private_manifest) or {}).get("stage2_voice_scan") or {}
    scan_ok = voice_scan_complete(voice_scan, raw_path, messages, voice_rows)
    if not scan_ok:
        failures.append({"deal_id": deal_id, "source": "max_voice_manifest", "reason": "not_checked_or_incomplete"})
    voice_diagnostics = latest_transcription_diagnostics(
        deal_id, [str(message.get("activity_id") or "") for message in messages]
    )
    voice_counts, voice_residual, voice_data_limitations = voice_facts(
        deal_id,
        messages,
        voice_rows,
        [private_workspaces, practice_workspaces],
        transcription_diagnostics=voice_diagnostics,
    )
    for row in voice_residual:
        activity_id = str(row.get("activity_id") or "")
        row["latest_transcription_diagnostic"] = voice_diagnostics.get(activity_id, "unknown")
    for row in voice_data_limitations:
        if row.get("issue") == "transcript_missing":
            activity_id = str(row.get("activity_id") or "")
            row["latest_transcription_diagnostic"] = voice_diagnostics.get(activity_id, "unknown")
    if voice_counts["missing_activity_id"]:
        failures.append({"deal_id": deal_id, "source": "max_voice_context", "reason": "activity_id_missing"})
    normalized = build_communications(bundle)
    channels = Counter(str(row.get("channel") or "unknown") for row in normalized if isinstance(row, dict))
    if not any(path.exists() for path in (private_manifest, practice_manifest)):
        limitations.append("call_audio_manifest_missing")
    if call_counts["calls_audio_unavailable"]:
        limitations.append("call_audio_unavailable")
    if call_counts["calls_unknown_duration"]:
        limitations.append("call_audio_duration_unknown")
    if voice_counts["audio_unavailable"]:
        limitations.append("max_voice_audio_unavailable")
    if voice_counts["missing_available_transcript"]:
        limitations.append("max_voice_available_transcript_missing")
    limitations.append("separate_customer_chat_history_not_collected")
    if not source_lead:
        lead_status = "not_linked"

    source_status = {
        "raw_context": "ok",
        "deal_card": "ok" if card_ok else "failed",
        "deal_activities": "ok" if response_ok(activities) else "failed",
        "stage_history": "ok" if response_ok(stage) else "failed",
        "timeline_comments": "ok" if timeline_ok else "failed",
        "tasks": "ok" if not task_failures else "failed",
        "source_lead": lead_status,
        "call_audio_manifest": "ok" if has_audio_manifest else "missing",
        "max_voice_manifest": "ok" if scan_ok else "not_checked_or_incomplete",
        "normalized_root_and_source_lead_channels": dict(channels),
        "separate_customer_chat_history": "not_collected",
    }
    return ({
        "deal_id": deal_id,
        "sources": source_status,
        "calls": call_counts,
        "max_voice": {**voice_counts, "scan_status": "checked" if scan_ok else "not_checked_or_incomplete"},
        "call_data_limitations": call_data_limitations,
        "max_voice_data_limitations": voice_data_limitations,
        "data_quality": "incomplete" if failures else "limited" if limitations else "complete",
        "limitations": sorted(set(limitations)),
        "source_failures": failures,
    }, [{"deal_id": deal_id, **row} for row in residual], [{"deal_id": deal_id, **row} for row in voice_residual])


def build_completeness(cohort_path: Path, practice: Path) -> dict[str, Any]:
    ids = cohort_ids(cohort_path)
    helpers = practice_helpers(practice)
    voice_helpers = practice_voice_helpers(practice)
    deals, residual, voice_residual, failures = [], [], [], []
    for deal_id in ids:
        row, call_residual, deal_voice_residual = deal_quality(
            deal_id,
            RAW_DIR / f"deal_{deal_id}_context.json",
            AUDIO_DIR / f"deal_{deal_id}_call_audio_manifest.json",
            practice / "reports" / "bitrix_customer_path" / "audio" / f"deal_{deal_id}_call_audio_manifest.json",
            WORKSPACES_DIR,
            practice / "reports" / "rop_assistant" / "deals",
            helpers,
            voice_helpers,
        )
        deals.append(row)
        residual.extend(call_residual)
        voice_residual.extend(deal_voice_residual)
        failures.extend(row.get("source_failures") or [])
    totals = Counter()
    for row in deals:
        totals.update(row.get("calls") or {})
    voice_totals = Counter()
    for row in deals:
        voice_totals.update({name: count for name, count in (row.get("max_voice") or {}).items() if name != "scan_status"})
    raw_complete = len(deals) == 50 and all(row.get("sources", {}).get("raw_context") == "ok" for row in deals)
    call_gate = totals.get("eligible_calls_without_transcript", 0) == 0
    gate = call_gate
    status = "PASS" if raw_complete and not failures and gate else "BLOCKED" if raw_complete and not call_gate else "INCOMPLETE"
    return {
        "schema_version": 1,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cohort_count": len(ids),
        "call_threshold_seconds": helpers[2],
        "eligible_calls_without_transcript": totals.get("eligible_calls_without_transcript", 0),
        "voice_messages_missing_available_transcript": voice_totals.get("missing_available_transcript", 0),
        "gate": "PASS" if status == "PASS" else "eligible_calls_without_transcript_nonzero" if not call_gate else "required_source_failures_or_missing_context",
        "call_gate": "PASS" if call_gate else "BLOCKED",
        "voice_transcription_status": "complete_for_available_audio" if voice_totals.get("missing_available_transcript", 0) == 0 else "available_audio_missing_transcripts",
        "totals": {name: totals.get(name, 0) for name in (
            "total_calls", "calls_with_measured_audio", "calls_lt_36", "eligible_calls_ge_36",
            "eligible_calls_with_transcript", "eligible_calls_without_transcript",
            "calls_audio_unavailable", "calls_unknown_duration", "calls_recording_incomplete",
            "calls_lt36_incomplete",
        )},
        "voice_totals": {name: voice_totals.get(name, 0) for name in (
            "voice_message_count", "with_transcript", "missing_available_transcript", "unavailable",
            "audio_unavailable", "decoding_failed",
        )},
        "source_failures": failures,
        "residual_calls": residual,
        "residual_max_voice_messages": voice_residual,
        "deals": deals,
        "scope_limitations": [
            "Per-deal customer-history channels are derived from the saved deal and explicit source-lead context only.",
            "Separate customer chat history is not collected by the existing deal fetch command.",
            "Unavailable audio and unknown duration remain missing-data limitations, not negative evidence.",
            "Audio-unavailable and unknown-duration counts can overlap; an audio file purged after a linked transcript still counts as unavailable.",
            "Max voice messages are bounded to root-deal and explicit source-lead comments in the saved raw context over 3650 days; no contact expansion is performed.",
            "Max voice counts are separate from CRM call totals and the 36-second call gate; local file presence does not establish decodable audio, and unresolved conversion failures are counted separately.",
        ],
        "metric_note": "Audio availability means a local file is present, not that it is decodable. Unresolved Max voice conversion errors are counted separately in max_voice.decoding_failed; audio availability, measured duration, and transcript linkage remain independent dimensions.",
    }


TRANSCRIPTION_DIAGNOSTICS = frozenset((
    "completed",
    "conversion_error",
    "reported_error_without_transcript",
    "exit_zero_without_valid_transcript",
    "reported_error_in_output",
    "timeout",
    "rate_limited",
    "authentication_error",
    "access_denied",
    "source_not_found",
    "network_error",
    "process_error",
))


def latest_transcription_diagnostics(
    deal_id: str,
    activity_ids: list[str],
    action_log_path: Path = ACTION_LOG,
) -> dict[str, str]:
    wanted = {str(activity_id) for activity_id in activity_ids if activity_id}
    result = {activity_id: "unknown" for activity_id in wanted}
    if not wanted or not action_log_path.is_file():
        return result
    try:
        lines = action_log_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return result
    for line in reversed(lines):
        if not wanted:
            break
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(entry, dict) or entry.get("action") != "transcribe":
            continue
        if str(entry.get("deal_id") or "") != deal_id:
            continue
        activity_id = str(entry.get("activity_id") or "")
        if activity_id not in wanted:
            continue
        diagnostic = entry.get("diagnostic")
        result[activity_id] = diagnostic if isinstance(diagnostic, str) and diagnostic in TRANSCRIPTION_DIAGNOSTICS else "unknown"
        wanted.remove(activity_id)
    return result


def diagnostic_kind(output: str, exit_code: int) -> str:
    if exit_code == 0:
        return "completed"
    sample = output.lower()
    for needles, label in (
        (("timeout", "timed out"), "timeout"),
        (("429", "rate limit"), "rate_limited"),
        (("401", "unauthorized", "invalid api key"), "authentication_error"),
        (("403", "forbidden", "access denied"), "access_denied"),
        (("404", "not found"), "source_not_found"),
        (("connection", "network"), "network_error"),
    ):
        if any(needle in sample for needle in needles):
            return label
    return "process_error"


def transcribe_outcome(exit_code: int, output: str, transcript_ok: bool) -> tuple[int, str]:
    sample = output.lower()
    conversion_error = any(term in sample for term in (
        "ffmpeg", "decode error", "decoder error", "conversion error", "failed to convert", "конверт", "декод"
    ))
    reported_error = any(term in sample for term in ("error", "exception", "traceback", "failed", "failure"))
    if exit_code == 0 and not transcript_ok:
        diagnostic = "conversion_error" if conversion_error else "reported_error_without_transcript" if reported_error else "exit_zero_without_valid_transcript"
        return 1, diagnostic
    if exit_code != 0:
        return exit_code, "conversion_error" if conversion_error else diagnostic_kind(output, exit_code)
    return 0, "reported_error_in_output" if reported_error else "completed"


def save_transcription_output(
    deal_id: str, activity_id: str, exit_code: int, transcript_ok: bool, stdout: str, stderr: str
) -> None:
    safe_id = "".join(char for char in activity_id if char.isalnum() or char in "_-")
    if not safe_id or safe_id != activity_id:
        safe_id = hashlib.sha256(activity_id.encode("utf-8")).hexdigest()[:20]
    path = PRIVATE / "logs" / "transcribe" / f"deal_{deal_id}" / f"activity_{safe_id}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            f"\n--- {datetime.now(timezone.utc).isoformat(timespec='seconds')} ---\n"
            f"exit_code={exit_code}\n"
            f"transcript_check={'valid_linked_bundle' if transcript_ok else 'missing_or_invalid'}\n"
            f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n"
        )


def log_action(action: str, targets: list[dict[str, Any]], code: int, diagnostic: str) -> None:
    PRIVATE.joinpath("logs").mkdir(parents=True, exist_ok=True)
    with ACTION_LOG.open("a", encoding="utf-8") as stream:
        for target in targets:
            stream.write(json.dumps({
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "action": action,
                **target,
                "exit_code": code,
                "diagnostic": diagnostic,
            }, ensure_ascii=False) + "\n")


def run_practice(action: str, script: Path, args: list[str], practice: Path, targets: list[str]) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["BITRIX_DENY_WRITE_METHODS"] = "1"
    result = subprocess.run(
        [str(practice / "venv" / "Scripts" / "python.exe"), "-B", str(script), *args],
        cwd=practice,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    diagnostic = diagnostic_kind(result.stdout + "\n" + result.stderr, result.returncode)
    log_action(action, [{"deal_id": deal_id} for deal_id in targets], result.returncode, diagnostic)
    return result.returncode, diagnostic


def ids_needing_fetch(ids: list[str]) -> list[str]:
    result = []
    for deal_id in ids:
        data = read_json(RAW_DIR / f"deal_{deal_id}_context.json")
        deal = (data or {}).get("deal") or {}
        valid = bool(data) and str(data.get("deal_id") or "") == deal_id
        valid = valid and response_ok(deal.get("response")) and not (data.get("sync") or {}).get("retry_required")
        if not valid:
            result.append(deal_id)
    return result


def self_check() -> None:
    counts, residual = summarize_calls([
        {"activity_id": "short-rounds-to-36", "audio_available": True, "duration_seconds": 36.0, "is_short_no_answer": True, "has_transcript": False},
        {"activity_id": "eligible", "audio_available": True, "duration_seconds": 36.0, "is_short_no_answer": False, "has_transcript": True},
        {"activity_id": "missing", "audio_available": False, "duration_seconds": None, "is_short_no_answer": False, "has_transcript": False},
    ], 36.0)
    assert counts["calls_lt_36"] == 1
    assert counts["eligible_calls_with_transcript"] == 1
    assert counts["eligible_calls_without_transcript"] == 0
    assert counts["calls_audio_unavailable"] == 1
    assert not residual
    counts, _ = summarize_calls([
        {"activity_id": "purged", "audio_available": False, "duration_seconds": 41.2, "is_short_no_answer": False, "has_transcript": True},
        {"activity_id": "unknown", "audio_available": False, "duration_seconds": None, "is_short_no_answer": False, "has_transcript": False},
    ], 36.0)
    assert counts["eligible_calls_ge_36"] == 1
    assert counts["eligible_calls_with_transcript"] == 1
    assert counts["calls_audio_unavailable"] == 2
    assert counts["calls_unknown_duration"] == 1
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        bundle = root / "call_17_transcript.json"
        bundle.write_text(json.dumps({"metadata": {"entity_type": "deal", "entity_id": "12", "activity_id": "17"}, "text": "ok"}), encoding="utf-8")
        assert valid_transcript(bundle, "12", "17")
        assert not valid_transcript(bundle, "13", "17")
        empty_bundle = root / "call_18_transcript.json"
        empty_bundle.write_text(json.dumps({"metadata": {"entity_type": "deal", "entity_id": "12", "activity_id": "18"}, "text": "  "}), encoding="utf-8")
        assert not valid_transcript(empty_bundle, "12", "18")
        assert transcribe_outcome(0, "", valid_transcript(empty_bundle, "12", "18")) == (
            1, "exit_zero_without_valid_transcript"
        )
        assert transcribe_outcome(0, "Ошибка при конвертации аудио через ffmpeg", False) == (
            1, "conversion_error"
        )
        assert transcribe_outcome(0, "transcribed", valid_transcript(bundle, "12", "17")) == (
            0, "completed"
        )
        action_log = root / "actions.jsonl"
        action_log.write_text("\n".join(json.dumps(row) for row in (
            {"action": "transcribe", "deal_id": "12", "activity_id": "17", "diagnostic": "completed"},
            {"action": "transcribe", "deal_id": "13", "activity_id": "18", "diagnostic": "conversion_error"},
            {"action": "transcribe", "deal_id": "12", "activity_id": "17", "diagnostic": "conversion_error"},
            {"action": "transcribe", "deal_id": "12", "activity_id": "18", "diagnostic": "D:/private/secret-url-token"},
        )) + "\n", encoding="utf-8")
        assert latest_transcription_diagnostics("12", ["17", "18", "19"], action_log) == {
            "17": "conversion_error", "18": "unknown", "19": "unknown"
        }
        audio = root / "call.mp3"
        audio.write_bytes(b"sample")
        facts = call_facts(
            deal_id="12",
            calls=[{"ID": "17"}],
            manifest_rows={"17": [
                {"call_quality": "ok", "downloads": [{"ok": True, "local_path": str(audio), "duration_seconds": 36.0, "is_short_no_answer": False}]},
                {"call_quality": "short_no_answer", "downloads": [{"ok": True, "local_path": str(audio), "duration_seconds": 36.0, "is_short_no_answer": True}]},
            ]},
            workspace_roots=[],
            threshold=36.0,
            get_audio_duration_seconds=lambda _path: None,
        )
        assert facts[0]["duration_seconds"] == 36.0 and not facts[0]["is_short_no_answer"]
        incomplete = call_facts(
            deal_id="12",
            calls=[{"ID": "17"}],
            manifest_rows={"17": [{
                "call_quality": "recording_incomplete",
                "downloads": [{
                    "ok": True, "local_path": str(audio), "duration_seconds": 3.0,
                    "expected_call_duration_seconds": 67.0, "is_short_no_answer": True,
                    "recording_stability_status": "duration_incomplete",
                    "recording_ready_for_transcription": False,
                }],
            }]},
            workspace_roots=[],
            threshold=36.0,
            get_audio_duration_seconds=lambda _path: None,
        )[0]
        assert incomplete["recording_incomplete"] and not incomplete["is_short_no_answer"]
        assert incomplete["duration_seconds"] == 3.0 and incomplete["expected_call_duration_seconds"] == 67.0
        counts, residual = summarize_calls([incomplete], 36.0)
        assert counts["calls_lt_36"] == counts["calls_lt36_incomplete"] == counts["calls_recording_incomplete"] == 1
        assert counts["eligible_calls_ge_36"] == 0 and not residual
        incomplete["duration_seconds"] = 36.0
        counts, residual = summarize_calls([incomplete], 36.0)
        assert counts["eligible_calls_ge_36"] == counts["eligible_calls_without_transcript"] == 1
        assert counts["calls_lt_36"] == 0 and residual[0]["reason"] == "transcript_missing"
        awaiting = call_facts(
            deal_id="12",
            calls=[{"ID": "17"}],
            manifest_rows={"17": [{
                "call_quality": "ok",
                "downloads": [{
                    "ok": True, "local_path": str(audio), "duration_seconds": 3.0,
                    "recording_stability_status": "awaiting_second_size_observation",
                    "recording_ready_for_transcription": False,
                }],
            }]},
            workspace_roots=[],
            threshold=36.0,
            get_audio_duration_seconds=lambda _path: None,
        )[0]
        assert not awaiting["recording_incomplete"]
        transcript = root / "call_max_2_fingerprint_transcript.json"
        transcript.write_text(json.dumps({"metadata": {"entity_type": "deal", "entity_id": "12", "activity_id": "max_2_fingerprint"}, "text": "voice"}), encoding="utf-8")
        voice_counts, voice_residual, voice_limitations = voice_facts(
            "12",
            [
                {"activity_id": "max_1_fingerprint", "duration_seconds": 4.2},
                {"activity_id": "max_2_fingerprint"},
            ],
            {
                "max_1_fingerprint": [{"downloads": [{"ok": True, "local_path": str(audio)}]}],
                "max_2_fingerprint": [{"transcription": {"status": "transcribed_and_purged", "transcript_json_path": str(transcript)}}],
            },
            [],
            transcription_diagnostics={
                "max_1_fingerprint": "conversion_error",
                "max_2_fingerprint": "completed",
            },
        )
        assert voice_counts["voice_message_count"] == 2
        assert voice_counts["with_transcript"] == 1
        assert voice_counts["missing_available_transcript"] == 1
        assert voice_counts["decoding_failed"] == 1
        assert voice_counts["unavailable"] == 0 and voice_counts["audio_unavailable"] == 1
        assert len(voice_residual) == 1 and voice_residual[0]["reason"] == "transcript_missing"
        assert {row["issue"] for row in voice_limitations} == {"transcript_missing", "audio_unavailable"}
        source_message = {
            "activity_id": "max_99_fingerprint",
            "entity_type": "lead",
            "entity_id": "23",
            "timeline_comment_id": "99",
            "url_fingerprint": "fingerprint",
        }
        linked_row = {
            "activity_id": "max_99_fingerprint",
            "audio_kind": "max_voice",
            "owner_id": "23",
            "timeline_comment_id": "99",
            "url_fingerprint": "fingerprint",
        }
        assert voice_row_matches(linked_row, "12", source_message)
        assert not voice_row_matches({**linked_row, "owner_id": "44"}, "12", source_message)
        raw_snapshot = root / "raw.json"
        raw_snapshot.write_text("raw", encoding="utf-8")
        scan = {
            "checked": True,
            "source_complete": True,
            "lookback_days": 3650,
            "discovered_messages": 1,
            "processed_messages": 1,
            "raw_context_sha256": hashlib.sha256(b"raw").hexdigest(),
        }
        assert voice_scan_complete(scan, raw_snapshot, [source_message], {"max_99_fingerprint": [linked_row]})
        assert not voice_scan_complete(scan, raw_snapshot, [source_message], {})
        raw_snapshot.write_text("changed", encoding="utf-8")
        assert not voice_scan_complete(scan, raw_snapshot, [source_message], {"max_99_fingerprint": [linked_row]})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cohort-bounded validation_50 Stage 2 actions")
    parser.add_argument("action", choices=("inventory", "fetch", "audio", "voices", "transcribe", "quality", "self-check"))
    parser.add_argument("--cohort", type=Path, default=HERE / "cohort.json")
    parser.add_argument("--practice-root", type=Path, default=DEFAULT_PRACTICE)
    args = parser.parse_args()

    if args.action == "self-check":
        self_check()
        print(json.dumps({"action": "self-check", "status": "PASS"}))
        return

    ids = cohort_ids(args.cohort)
    if args.action == "inventory":
        counts = Counter()
        for deal_id in ids:
            counts["raw_contexts"] += int((RAW_DIR / f"deal_{deal_id}_context.json").is_file())
            manifest = read_json(AUDIO_DIR / f"deal_{deal_id}_call_audio_manifest.json")
            counts["audio_manifests"] += int(manifest is not None)
            counts["voice_scans_checked"] += int(bool((manifest or {}).get("stage2_voice_scan", {}).get("checked")))
        print(json.dumps({"action": "inventory", "cohort_count": len(ids), **counts}, ensure_ascii=False))
        return

    if args.action == "fetch":
        missing = ids_needing_fetch(ids)
        if not missing:
            print(json.dumps({"action": "fetch", "status": "already_complete", "deals": 0}))
            return
        code, diagnostic = run_practice(
            "fetch",
            args.practice_root / "bitrix" / "deals" / "1_fetch_deals_context.py",
            ["--deal-ids", *missing, "--output-dir", str(RAW_DIR), "--db-path", str(DB_PATH)],
            args.practice_root,
            missing,
        )
        print(json.dumps({"action": "fetch", "status": "ok" if code == 0 else "failed", "diagnostic": diagnostic, "deals": len(missing), "exit_code": code}))
        return

    if args.action == "audio":
        ready = [deal_id for deal_id in ids if (RAW_DIR / f"deal_{deal_id}_context.json").is_file()]
        if not ready:
            print(json.dumps({"action": "audio", "status": "no_raw_contexts", "deals": 0}))
            return
        code, diagnostic = run_practice(
            "audio",
            args.practice_root / "bitrix" / "deals" / "download_deals_call_audio.py",
            ["--deal-ids", *ready, "--raw-dir", str(RAW_DIR), "--audio-dir", str(AUDIO_DIR), "--db-path", str(DB_PATH)],
            args.practice_root,
            ready,
        )
        print(json.dumps({"action": "audio", "status": "ok" if code == 0 else "failed", "diagnostic": diagnostic, "deals": len(ready), "exit_code": code}))
        return

    if args.action == "voices":
        succeeded, failures = run_voices(ids, args.practice_root, practice_helpers(args.practice_root), practice_voice_helpers(args.practice_root))
        print(json.dumps({"action": "voices", "status": "checked" if failures == 0 else "incomplete", "deals_checked": succeeded, "deals_incomplete": failures}, ensure_ascii=False))
        return

    if args.action == "transcribe":
        helpers = practice_helpers(args.practice_root)
        voice_helpers = practice_voice_helpers(args.practice_root)
        _, call_activities, threshold, _ = helpers
        build_history_sections, max_voice_messages = voice_helpers[:2]
        candidates: list[dict[str, Any]] = []
        practice_audio = args.practice_root / "reports" / "bitrix_customer_path" / "audio"
        practice_workspaces = args.practice_root / "reports" / "rop_assistant" / "deals"
        for deal_id in ids:
            raw = read_json(RAW_DIR / f"deal_{deal_id}_context.json")
            if not raw:
                continue
            manifests, _ = manifest_calls([
                AUDIO_DIR / f"deal_{deal_id}_call_audio_manifest.json",
                practice_audio / f"deal_{deal_id}_call_audio_manifest.json",
            ])
            for fact in call_facts(
                deal_id=deal_id,
                calls=local_call_ids(raw, call_activities),
                manifest_rows=manifests,
                workspace_roots=[WORKSPACES_DIR, practice_workspaces],
                threshold=float(threshold),
                get_audio_duration_seconds=helpers[3],
            ):
                duration = fact["duration_seconds"]
                if fact["activity_id"] and duration is not None and duration >= float(threshold) and not fact["is_short_no_answer"] and not fact["has_transcript"] and fact["audio_available"]:
                    candidates.append({"deal_id": deal_id, "media_kind": "call", **fact})
            messages = root_source_voice_messages(deal_id, raw, helpers[0], build_history_sections, max_voice_messages)
            voice_rows, _ = voice_manifest_rows([
                AUDIO_DIR / f"deal_{deal_id}_call_audio_manifest.json",
                practice_audio / f"deal_{deal_id}_call_audio_manifest.json",
            ], deal_id, messages)
            for message in messages:
                activity_id = str(message.get("activity_id") or "")
                rows = voice_rows.get(activity_id, [])
                audio_path = voice_audio_path(rows)
                if activity_id and audio_path and not transcript_files(
                    deal_id, activity_id, [WORKSPACES_DIR, practice_workspaces], rows
                ):
                    candidates.append({
                        "deal_id": deal_id,
                        "media_kind": "max_voice",
                        "activity_id": activity_id,
                        "audio_path": audio_path,
                        "call_start": str(message.get("start_time") or ""),
                        "subject": "Голосовое сообщение Max",
                    })
        by_deal: dict[str, list[dict[str, Any]]] = {}
        for item in candidates:
            by_deal.setdefault(item["deal_id"], []).append(item)
        progress_lock = threading.Lock()
        progress = {"completed": 0}

        def transcribe_deal(deal_id: str, media_items: list[dict[str, Any]]) -> list[int]:
            codes = []
            for media in media_items:
                activity_id = str(media["activity_id"])
                cmd = [
                    str(args.practice_root / "openai_api" / "audio" / "local_file_transcribe.py"),
                    "--deal-id", deal_id,
                    "--audio", str(media["audio_path"]),
                    "--activity-id", activity_id,
                    "--workspace-root", str(WORKSPACES_DIR),
                    "--no-copy-audio",
                ]
                if media.get("call_start"):
                    cmd.extend(("--call-start", media["call_start"]))
                if media.get("subject"):
                    cmd.extend(("--subject", media["subject"]))
                env = os.environ.copy()
                env["PYTHONDONTWRITEBYTECODE"] = "1"
                env["BITRIX_DENY_WRITE_METHODS"] = "1"
                result = subprocess.run(
                    [str(args.practice_root / "venv" / "Scripts" / "python.exe"), "-B", *cmd],
                    cwd=args.practice_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                output = result.stdout + "\n" + result.stderr
                transcript_ok = transcript_files(
                    deal_id, activity_id, [WORKSPACES_DIR, practice_workspaces], []
                )
                save_transcription_output(
                    deal_id, activity_id, result.returncode, transcript_ok, result.stdout, result.stderr
                )
                effective_code, diagnostic = transcribe_outcome(
                    result.returncode, output, transcript_ok
                )
                transcript_check = "valid_linked_bundle" if transcript_ok else "missing_or_invalid"
                log_action("transcribe", [{
                    "deal_id": deal_id,
                    "activity_id": activity_id,
                    "media_kind": media["media_kind"],
                    "transcript_check": transcript_check,
                }], effective_code, diagnostic)
                codes.append(effective_code)
                with progress_lock:
                    progress["completed"] += 1
                    print(json.dumps({
                        "action": "transcribe",
                        "completed": progress["completed"],
                        "total": len(candidates),
                        "deal_id": deal_id,
                        "activity_id": activity_id,
                        "media_kind": media["media_kind"],
                        "transcript_check": transcript_check,
                        "diagnostic": diagnostic,
                        "status": "ok" if effective_code == 0 else "failed",
                    }), flush=True)
            return codes

        results: list[int] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(transcribe_deal, deal_id, media_items) for deal_id, media_items in by_deal.items()]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
        call_candidates = sum(item["media_kind"] == "call" for item in candidates)
        voice_candidates = len(candidates) - call_candidates
        print(json.dumps({"action": "transcribe", "eligible_call_missing_with_audio": call_candidates, "max_voice_missing_with_audio": voice_candidates, "succeeded": sum(code == 0 for code in results), "failed": sum(code != 0 for code in results)}))
        return

    completeness = build_completeness(args.cohort, args.practice_root)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    COMPLETENESS_PATH.write_text(json.dumps(completeness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    totals = completeness["totals"]
    print(json.dumps({"action": "quality", "status": completeness["status"], "gate": completeness["gate"], **totals}, ensure_ascii=False))


if __name__ == "__main__":
    main()
