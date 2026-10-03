"""Build outcome-blind validation inputs from the saved 50-deal raw bundle."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research_outputs" / "validation_50_v1"
WORKLOG_QUARANTINE_POLICY = OUT / "worklog_quarantine_policy.json"
TERMINAL_SOURCE_POLICY = OUT / "terminal_source_policy.json"
TERMINAL_SOURCE_PROPOSAL = OUT / "terminal_source_policy_proposal.json"
TERMINAL_SOURCE_LIMITATION = "Some source records excluded under approved chronology/source-admissibility constraints; genuine predecision same-day/intervening-day communications may be missing."
RAW_DIR = OUT / "_private" / "raw"
PRIVATE_AUDIO_DIR = OUT / "_private" / "audio"
DATASET_DIR = OUT / "dataset"
DEALS_DIR = DATASET_DIR / "deals"
VIEWS_DIR = OUT / "views"
PRACTICE = Path(r"D:\My_dev_project\Neuro_rop_practice")
WORKSPACES = OUT / "_private" / "workspaces"
V1_VIEW_BUILDER = ROOT / "research_outputs" / "deal_audit_v1" / "build_audit_views.py"
SCHEMA = ROOT / "research_outputs" / "deal_audit_v2" / "audit_schema.json"
SCHEMA_COPY = OUT / "audit_schema.json"
CONTRACT = ROOT / "research_outputs" / "deal_audit_v2" / "input_contract.md"
COMPLETENESS = OUT / "completeness.json"
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+7|8)[\s().-]*\d[\d\s().-]{7,}\d(?!\w)")
CUSTOMER_REFUSAL_STATUS_RE = re.compile(
    r"\bклиент\b"
    r"(?P<between>[^.!?;\n]{0,120}?)"
    r"уш(?:[её]л|ла|ли)\s+в\s+отказ\b",
    re.IGNORECASE,
)
NEGATED_CUSTOMER_REFUSAL_RE = re.compile(
    r"\b(?:не|никогда\s+не|так\s+и\s+не)"
    r"(?:\s+(?:сразу|совсем|вовсе|окончательно))?\s*$",
    re.IGNORECASE,
)
TERMINAL_MILESTONE_TASK_TITLE = "подписанный договор и оплата"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_worklog_quarantine_policy() -> tuple[dict[str, dict[str, str]], str]:
    raw = WORKLOG_QUARANTINE_POLICY.read_bytes()
    policy = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(policy, dict):
        raise ValueError("worklog quarantine policy must be an object")
    sources = policy.get("sources")
    if policy.get("version") != 1 or policy.get("user_approved") is not True or not isinstance(sources, list) or len(sources) != 5:
        raise ValueError("worklog quarantine policy is missing approval or does not contain exactly five sources")
    by_deal, seen_worklog_ids = {}, set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"deal_id", "worklog_id", "raw_context_sha256"}:
            raise ValueError("worklog quarantine policy source schema is invalid")
        deal_id, worklog_id, raw_hash = (source[key] for key in ("deal_id", "worklog_id", "raw_context_sha256"))
        if not isinstance(deal_id, str) or not deal_id.isdigit() or not isinstance(worklog_id, str) or not worklog_id.isdigit() or not isinstance(raw_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_hash):
            raise ValueError("worklog quarantine policy contains an invalid deal, worklog, or raw hash")
        if deal_id in by_deal or worklog_id in seen_worklog_ids:
            raise ValueError("worklog quarantine policy contains duplicate source identities")
        by_deal[deal_id] = {worklog_id: raw_hash}
        seen_worklog_ids.add(worklog_id)
    return by_deal, sha256(raw)


def validate_worklog_quarantine(raw: dict, deal_id: str, raw_context_sha256: str, sources: dict[str, str]) -> set[str]:
    if not sources:
        return set()
    if any(expected_hash != raw_context_sha256 for expected_hash in sources.values()):
        raise ValueError(f"raw context hash does not match worklog quarantine policy for deal {deal_id}")
    rows = raw.get("manager_worklogs")
    if not isinstance(rows, list):
        raise ValueError("manager_worklogs must be a list")
    for worklog_id in sources:
        matches = [row for row in rows if isinstance(row, dict) and str(row.get("comment_id") or "").strip() == worklog_id]
        if len(matches) != 1 or not isinstance(matches[0].get("entries"), list) or not matches[0]["entries"]:
            raise ValueError(f"quarantined manager worklog {worklog_id} is missing or ambiguous in deal {deal_id}")
    return set(sources)


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing timestamp")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone-naive timestamp cannot preserve chronology")
    return parsed


def before_cutoff(value: str, cutoff: datetime) -> bool:
    return parse_timestamp(value) < cutoff


def scrub_text(value) -> str:
    text = str(value or "")
    text = URL_RE.sub("[URL REDACTED]", text)
    text = EMAIL_RE.sub("[EMAIL REDACTED]", text)

    def hide_phone(match):
        digits = sum(char.isdigit() for char in match.group())
        return "[PHONE REDACTED]" if 10 <= digits <= 12 else match.group()

    return PHONE_RE.sub(hide_phone, text)


def has_customer_refusal_status(text: str) -> bool:
    for match in CUSTOMER_REFUSAL_STATUS_RE.finditer(text):
        clause_start = max(text.rfind(mark, 0, match.start()) for mark in ".!?;\n") + 1
        if re.search(r"\bне\s*$", text[clause_start:match.start()], re.IGNORECASE):
            continue
        if NEGATED_CUSTOMER_REFUSAL_RE.search(match.group("between")):
            continue
        return True
    return False


def is_completed_terminal_milestone_task(task: dict, title: str) -> bool:
    normalized = " ".join(str(title or "").casefold().split()).strip(" .")
    completed_at = task.get("closedDate")
    return (
        normalized == TERMINAL_MILESTONE_TASK_TITLE
        and str(task.get("status") or "") == "5"
        and bool(completed_at)
        and completed_at == task.get("statusChangedDate") == task.get("changedDate")
    )


def cohort_records() -> tuple[list[str], dict[str, str]]:
    cohort_path = OUT / "cohort.json"
    cohort = read_json(cohort_path)
    rows = cohort.get("deals") if isinstance(cohort, dict) else None
    if not isinstance(rows, list) or len(rows) != 50:
        raise ValueError("cohort.json must contain exactly 50 deal rows")
    ids = [str(row.get("deal_id") or "").strip() for row in rows if isinstance(row, dict)]
    if len(ids) != 50 or any(not value.isdigit() for value in ids) or len(set(ids)) != 50:
        raise ValueError("cohort deal ids must be 50 unique numeric strings")
    labels = {str(row["deal_id"]): str(row["outcome"]).strip().upper() for row in rows}
    if set(labels) != set(ids) or any(label not in {"WON", "LOST"} for label in labels.values()):
        raise ValueError("cohort outcomes must be explicit WON/LOST labels")
    return ids, labels


def deal_item(raw: dict) -> dict:
    item = ((raw.get("deal") or {}).get("item"))
    if not isinstance(item, dict):
        raise ValueError("raw context has no deal item")
    return item


def history_items(raw: dict) -> list[dict]:
    history = raw.get("stage_history")
    if not isinstance(history, dict) or not history.get("ok") or not isinstance(history.get("items"), list):
        raise ValueError("stage history is missing or unsuccessful")
    return [row for row in history["items"] if isinstance(row, dict)]


def lifecycle_boundary(raw: dict) -> tuple[str, datetime, int, list[dict], int, bool]:
    item = deal_item(raw)
    created_at = item.get("DATE_CREATE")
    created = parse_timestamp(created_at)
    history = history_items(raw)
    terminal = [
        (parse_timestamp(row.get("CREATED_TIME")), row)
        for row in history
        if str(row.get("STAGE_SEMANTIC_ID") or "").strip().upper() in {"S", "F"}
    ]
    if not terminal:
        raise ValueError("no explicit terminal stage-history timestamp; cannot bound post-outcome events")
    first_terminal = min(timestamp for timestamp, _ in terminal)
    cutoff = max(timestamp for timestamp, _ in terminal)
    if sum(timestamp == cutoff for timestamp, _ in terminal) != 1:
        raise ValueError("terminal stage history has an ambiguous final timestamp")
    life_days = (cutoff.date() - created.date()).days
    if life_days < 0:
        raise ValueError("terminal stage precedes deal creation")
    reopened = any(
        first_terminal < parse_timestamp(row.get("CREATED_TIME")) < cutoff
        and str(row.get("STAGE_SEMANTIC_ID") or "").strip().upper() not in {"S", "F"}
        for row in history
    )
    return created_at, cutoff, life_days, history, len(terminal), reopened


def load_communication_normalizer():
    sys.path.insert(0, str(PRACTICE))
    import bitrix.customer_history as normalizer

    return normalizer


def raw_source_maps(raw: dict, normalizer) -> tuple[dict[str, dict], dict[str, dict]]:
    activities: dict[str, dict] = {}
    comments: dict[str, dict] = {}
    source_lead = raw.get("source_lead") if isinstance(raw.get("source_lead"), dict) else {}
    histories = (
        {
            "activities": raw.get("activities"),
            "activity_details": raw.get("activity_details"),
            "timeline_comments": raw.get("timeline_comments"),
        },
        source_lead,
    )
    for history in histories:
        details = history.get("activity_details") if isinstance(history.get("activity_details"), dict) else {}
        for row in normalizer.result_items(history.get("activities")):
            merged = normalizer.merge_activity_detail(row, details)
            source_id = str(merged.get("ID") or "").strip()
            if source_id:
                previous = activities.get(source_id)
                identity_fields = ("DESCRIPTION", "SUBJECT", "TYPE_ID", "DIRECTION", "START_TIME", "CREATED")
                if previous and tuple(previous.get(key) for key in identity_fields) != tuple(merged.get(key) for key in identity_fields):
                    raise ValueError(f"conflicting raw activity sources for activity {source_id}")
                activities[source_id] = merged
        for row in normalizer.timeline_comment_items(history):
            source_id = str(row.get("ID") or "").strip()
            if source_id:
                previous = comments.get(source_id)
                if previous and (previous.get("COMMENT"), previous.get("CREATED")) != (row.get("COMMENT"), row.get("CREATED")):
                    raise ValueError(f"conflicting raw timeline-comment sources for comment {source_id}")
                comments[source_id] = row
    return activities, comments


def communication_event(row: dict, activities: dict, comments: dict, normalizer, worklog_ids: set[str], quarantined_worklog_ids: set[str] | None = None) -> dict | None:
    source_type = str(row.get("source_type") or "")
    channel = str(row.get("channel") or "").lower()
    if source_type == "crm_activity" and channel in {"call", "email", "message", "task"}:
        event_type = channel
        provenance = "crm.activity.list"
    elif source_type == "crm_timeline_comment":
        event_type = "message" if channel in {"whatsapp", "max", "telegram", "message"} else "comment"
        provenance = "crm.timeline.comment.list"
    else:
        return None

    source_values = row.get("source_ids") if isinstance(row.get("source_ids"), list) else []
    source_ids = list(dict.fromkeys(str(value).strip() for value in source_values if str(value).strip()))
    if source_type == "crm_timeline_comment" and quarantined_worklog_ids:
        quarantined_ids = set(source_ids) & quarantined_worklog_ids
        if quarantined_ids and len(quarantined_ids) != len(source_ids):
            raise ValueError("normalized timeline comment merges a quarantined worklog with other source records")
        if quarantined_ids:
            return None
    source_id = source_ids[0] if source_ids else ""
    if not source_id:
        raise ValueError("normalized communication has no source record id")
    if source_type == "crm_timeline_comment" and source_id in worklog_ids:
        return None
    event_id = str(row.get("event_id") or f"{source_type}:{source_id}").strip()
    timestamp = row.get("occurred_at")
    parse_timestamp(timestamp)
    if source_type == "crm_activity":
        raw_record = activities.get(source_id)
        if not raw_record:
            raise ValueError(f"normalized activity {source_id} has no original CRM row")
        subject = normalizer.clean_text(raw_record.get("SUBJECT"))
        body = normalizer.clean_text(raw_record.get("DESCRIPTION"))
        content = scrub_text("\n".join(part for part in (subject, body) if part))
    else:
        raw_record = comments.get(source_id)
        if not raw_record:
            raise ValueError(f"normalized timeline comment {source_id} has no original CRM row")
        content = normalizer.clean_text(raw_record.get("COMMENT") or raw_record.get("TEXT") or raw_record.get("DESCRIPTION"))
        if channel in {"whatsapp", "max", "telegram"}:
            _, content = normalizer._parse_mirrored_message(content)
        content = scrub_text(content)
    metadata = {
        "source_record_id": source_id or None,
        "source_record_ids": source_ids,
        "source_type": source_type,
        "entity_type": row.get("entity_type"),
        "entity_id": row.get("entity_id"),
        "channel": channel,
    }
    if event_type in {"call", "email", "message", "task"} and source_id:
        metadata["activity_id"] = source_id
    direction = row.get("direction") if row.get("direction") in {"incoming", "outgoing"} else None
    if row.get("duration_seconds") is not None and event_type == "call":
        metadata["duration_seconds"] = row["duration_seconds"]
    return {
        "timestamp": timestamp,
        "event_type": event_type,
        "source": provenance,
        "direction": direction,
        "event_id": event_id or None,
        "content": content,
        "metadata": metadata,
    }


def timeline_event_for_comment(events: list[dict], comment_id: str) -> dict | None:
    for event in events:
        if event.get("source") != "crm.timeline.comment.list":
            continue
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        source_ids = metadata.get("source_record_ids")
        if not isinstance(source_ids, list):
            source_ids = [metadata.get("source_record_id")]
        if comment_id in {str(value).strip() for value in source_ids if value not in (None, "")}:
            return event
    return None


def wrapped_items(value) -> list[dict]:
    if isinstance(value, list):
        rows = []
        for row in value:
            if not isinstance(row, dict):
                continue
            rows.extend([item for item in row["items"] if isinstance(item, dict)] if isinstance(row.get("items"), list) else [row])
        return rows
    if isinstance(value, dict):
        if isinstance(value.get("items"), list):
            return [row for row in value["items"] if isinstance(row, dict)]
        result = (value.get("response") or {}).get("result") if isinstance(value.get("response"), dict) else None
        if isinstance(result, list):
            return [row for row in result if isinstance(row, dict)]
    return []


def manager_worklog_events(raw: dict, normalizer, cutoff: datetime, quarantined_worklog_ids: set[str] | None = None) -> tuple[list[dict], set[str], int, set[str], int]:
    rows = raw.get("manager_worklogs") or []
    if not isinstance(rows, list):
        raise ValueError("manager_worklogs must be a list")
    quarantined_worklog_ids = quarantined_worklog_ids or set()
    output, ids, post_terminal, quarantined_ids = [], set(), 0, set()
    quarantined_entries = 0
    for worklog in rows:
        if not isinstance(worklog, dict) or not isinstance(worklog.get("entries"), list):
            raise ValueError("manager worklog does not match the saved parser schema")
        comment_id = str(worklog.get("comment_id") or "").strip()
        recorded_at = worklog.get("bitrix_created_at")
        parse_timestamp(recorded_at)
        if not comment_id:
            raise ValueError("manager worklog is missing its source comment id")
        ids.add(comment_id)
        if comment_id in quarantined_worklog_ids:
            if comment_id in quarantined_ids:
                raise ValueError(f"manager worklog {comment_id} appears more than once")
            quarantined_ids.add(comment_id)
            quarantined_entries += len(worklog["entries"])
            continue
        if not before_cutoff(recorded_at, cutoff):
            post_terminal += 1
            continue
        for index, entry in enumerate(worklog["entries"]):
            if not isinstance(entry, dict):
                raise ValueError(f"manager worklog {comment_id} has an invalid entry")
            entry_date = str(entry.get("entry_date") or "")
            timestamp = f"{entry_date}T00:00:00+03:00"
            parse_timestamp(timestamp)
            output.append({
                "timestamp": timestamp,
                "event_type": "comment",
                "source": "manager_worklog",
                "event_id": f"manager_worklog:{comment_id}:{index}",
                "direction": None,
                "content": scrub_text(normalizer.clean_text(entry.get("text"))),
                "metadata": {
                    "worklog_id": comment_id,
                    "source_entry_index": index,
                    "date_raw": entry.get("date_raw"),
                    "date_only": True,
                    "year_inferred": bool(entry.get("year_inferred")),
                    "worklog_recorded_at": recorded_at,
                    "author_id": worklog.get("author_id"),
                    "evidence_class": "manager_claim",
                },
            })
    if quarantined_ids != quarantined_worklog_ids:
        missing = sorted(quarantined_worklog_ids - quarantined_ids)
        raise ValueError(f"quarantined manager worklogs were not found: {', '.join(missing)}")
    return output, ids, post_terminal, quarantined_ids, quarantined_entries


def task_records(raw: dict):
    tasks = raw.get("bitrix_tasks")
    if not isinstance(tasks, dict):
        return []
    output = []
    for key, wrapper in tasks.items():
        response = wrapper.get("response") if isinstance(wrapper, dict) else None
        result = response.get("result") if isinstance(response, dict) else None
        task = result.get("task") if isinstance(result, dict) else None
        if isinstance(task, dict):
            output.append((str(task.get("id") or key), task))
        else:
            raise ValueError(f"task snapshot {key} has no successful task record")
    return output


def task_event(task_id: str, task: dict, cutoff: datetime, normalizer) -> tuple[dict | None, bool, bool]:
    created_at = task.get("createdDate") or task.get("created_date")
    created = parse_timestamp(created_at)
    if not task.get("changedDate"):
        raise ValueError(f"task {task_id} has no update timestamp for post-outcome screening")
    edited_values = [task.get(key) for key in ("changedDate", "statusChangedDate", "closedDate") if task.get(key)]
    edited = [parse_timestamp(value) for value in edited_values]
    if not before_cutoff(created_at, cutoff) or any(value >= cutoff for value in edited):
        return None, True, False
    title = normalizer.clean_text(task.get("title"))
    if has_customer_refusal_status(str(title or "")) or is_completed_terminal_milestone_task(task, str(title or "")):
        return None, False, True
    description = normalizer.clean_text(task.get("description"))
    content = "\n".join(part for part in (str(title or "").strip(), str(description or "").strip()) if part)
    actual_id = str(task.get("id") or task_id)
    return {
        "timestamp": created_at,
        "event_type": "task",
        "source": "tasks.task.get",
        "event_id": f"bitrix_task:{actual_id}",
        "direction": None,
        "content": scrub_text(content),
        "metadata": {
            "source_record_id": actual_id,
            "task_id": actual_id,
            "created_by_id": task.get("createdBy"),
            "responsible_id": task.get("responsibleId"),
            "changed_at": task.get("changedDate"),
        },
    }, False, False


def task_chat_rows(value, task_id: str):
    """Read common saved message containers; do not infer a speaker from text."""
    text_keys = ("POST_MESSAGE", "MESSAGE", "message", "TEXT", "text", "COMMENT", "comment", "body")
    id_keys = ("ID", "id", "MESSAGE_ID", "message_id", "POST_ID", "post_id")
    time_keys = ("POST_DATE", "DATE_CREATE", "CREATED", "created_at", "timestamp", "DATE", "date")
    children = ("items", "messages", "result", "response", "data", "chat", "discussion", "posts")
    seen = set()

    def walk(node):
        if isinstance(node, list):
            for child in node:
                yield from walk(child)
        elif isinstance(node, dict):
            text = next((node.get(key) for key in text_keys if isinstance(node.get(key), str) and node.get(key).strip()), None)
            source_id = next((str(node.get(key)).strip() for key in id_keys if node.get(key) not in (None, "")), "")
            timestamp = next((node.get(key) for key in time_keys if node.get(key)), None)
            if text is not None and timestamp:
                signature = (source_id, str(timestamp), text)
                if signature not in seen:
                    seen.add(signature)
                    yield task_id, node, source_id, timestamp, text
                return
            for key in children:
                if key in node:
                    yield from walk(node[key])

    yield from walk(value)


def task_chat_events(raw: dict) -> list[dict]:
    chats = raw.get("bitrix_task_chats")
    if not isinstance(chats, dict):
        return []
    output, unparsed = [], 0
    for task_id, bundle in chats.items():
        rows = list(task_chat_rows(bundle, str(task_id)))
        if not rows:
            response = bundle.get("response") if isinstance(bundle, dict) else None
            result = response.get("result") if isinstance(response, dict) else None
            if isinstance(result, dict) and isinstance(result.get("messages"), list) and not result["messages"]:
                continue
            unparsed += 1
            continue
        for task_id, row, source_id, timestamp, content in rows:
            parse_timestamp(timestamp)
            if not source_id:
                raise ValueError(f"task chat for task {task_id} has no message ID")
            output.append({
                "timestamp": timestamp,
                "event_type": "task_chat",
                "source": "bitrix.task_chat",
                "event_id": f"task_chat:{task_id}:{source_id}" if source_id else None,
                "direction": row.get("direction") if row.get("direction") in {"incoming", "outgoing"} else None,
                "content": scrub_text(content),
                "metadata": {
                    "source_record_id": source_id or None,
                    "task_id": task_id,
                    "chat_id": row.get("CHAT_ID") or row.get("chat_id"),
                    "author_id": row.get("AUTHOR_ID") or row.get("CREATED_BY") or row.get("sender_id") or row.get("author_id"),
                },
            })
    if unparsed:
        raise ValueError(f"{unparsed} nonempty task-chat bundle(s) have no recognized message rows")
    return output


def stage_events(history: list[dict], cutoff: datetime) -> list[dict]:
    output = []
    for row in history:
        timestamp = row.get("CREATED_TIME")
        if not before_cutoff(timestamp, cutoff):
            continue
        source_id = str(row.get("ID") or "").strip()
        semantic = str(row.get("STAGE_SEMANTIC_ID") or "").strip().upper()
        output.append({
            "timestamp": timestamp,
            "event_type": "stage_change",
            "source": "crm.deal.history",
            "event_id": f"stage_history:{source_id}" if source_id else None,
            "direction": None,
            "content": "Pipeline stage transition recorded.",
            "metadata": {
                "source_record_id": source_id or None,
                "stage_id": row.get("STAGE_ID") if semantic not in {"S", "F"} else None,
                "category_id": row.get("CATEGORY_ID"),
            },
        })
    return output


def transcript_sources(deal_id: str) -> dict[str, dict]:
    roots = (
        (WORKSPACES / f"deal_{deal_id}" / "transcripts", "validation_workspace"),
        (PRACTICE / "reports" / "rop_assistant" / "deals" / f"deal_{deal_id}" / "transcripts", "practice_cache"),
    )
    result: dict[str, dict] = {}
    for folder, origin in roots:
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*_transcript.json"), key=lambda item: item.name):
            raw_bytes = path.read_bytes()
            payload = json.loads(raw_bytes.decode("utf-8-sig"))
            metadata = payload.get("metadata") if isinstance(payload, dict) else None
            if not isinstance(metadata, dict):
                raise ValueError(f"transcript metadata missing for {path.name}")
            source_deal = str(metadata.get("deal_id") or metadata.get("entity_id") or "").strip()
            activity_id = str(metadata.get("activity_id") or "").strip()
            text = payload.get("text")
            if source_deal != deal_id or not activity_id or not isinstance(text, str) or not text.strip():
                raise ValueError(f"invalid transcript identity or text in {path.name}")
            previous = result.get(activity_id)
            if previous and previous["text"] != text:
                raise ValueError(f"conflicting local transcripts for deal {deal_id}, activity {activity_id}")
            if previous:
                previous["origins"].append(origin)
            else:
                result[activity_id] = {
                    "text": text.strip(),
                    "sha256": sha256(raw_bytes),
                    "origin": origin,
                    "origins": [origin],
                    "audio_duration_seconds": metadata.get("audio_duration_seconds"),
                    "transcription_model": metadata.get("transcription_model"),
                }
    return result


def max_voice_sources(deal_id: str, raw: dict, raw_context_sha256: str, comments: dict, comment_owners: dict) -> tuple[dict[str, dict], str | None]:
    path = PRIVATE_AUDIO_DIR / f"deal_{deal_id}_call_audio_manifest.json"
    if not path.is_file():
        return {}, None
    raw_bytes = path.read_bytes()
    manifest = json.loads(raw_bytes.decode("utf-8-sig"))
    if not isinstance(manifest, dict) or str(manifest.get("deal_id") or "") != deal_id:
        raise ValueError(f"audio manifest identity mismatch for deal {deal_id}")
    calls = manifest.get("calls")
    if not isinstance(calls, list):
        raise ValueError(f"audio manifest calls missing for deal {deal_id}")
    scan = manifest.get("stage2_voice_scan")
    if not isinstance(scan, dict) or scan.get("checked") is not True or scan.get("raw_context_sha256") != raw_context_sha256:
        raise ValueError(f"max voice manifest is not checked against the current raw context for deal {deal_id}")
    allowed_owners = {("deal", deal_id)}
    source_lead = raw.get("source_lead") if isinstance(raw.get("source_lead"), dict) else {}
    lead_id = str(source_lead.get("lead_id") or "").strip()
    if lead_id:
        allowed_owners.add(("lead", lead_id))
    output = {}
    for row in calls:
        if not isinstance(row, dict) or row.get("audio_kind") != "max_voice":
            continue
        activity_id = str(row.get("activity_id") or "").strip()
        comment_id = str(row.get("timeline_comment_id") or "").strip()
        owner_id = str(row.get("owner_id") or "").strip()
        owner = comment_owners.get(comment_id)
        if not activity_id or not comment_id or not owner_id or comment_id not in comments:
            raise ValueError(f"max voice row has no exact raw source comment for deal {deal_id}")
        if owner not in allowed_owners or owner[1] != owner_id:
            raise ValueError(f"max voice row owner does not match the raw source comment for deal {deal_id}")
        if activity_id in output:
            previous = output[activity_id]
            if (previous["timeline_comment_id"], previous["owner_id"], previous["direction"]) != (comment_id, owner_id, row.get("direction")):
                raise ValueError(f"max voice activity {activity_id} maps to conflicting source comments or direction")
            continue
        output[activity_id] = {
            "timeline_comment_id": comment_id,
            "owner_id": owner_id,
            "direction": row.get("direction"),
        }
    return output, sha256(raw_bytes)


def max_voice_transcript_event(activity_id: str, source: dict, voice: dict, message: dict | None, source_comment: dict | None) -> dict:
    if message is None or source_comment is None:
        raise ValueError(f"max voice transcript {activity_id} has no matched raw source event")
    comment_id = voice["timeline_comment_id"]
    if str(source_comment.get("ID") or "").strip() != comment_id:
        raise ValueError(f"max voice transcript {activity_id} has a mismatched raw source comment")
    timestamp = source_comment.get("CREATED")
    parse_timestamp(timestamp)
    normalized_direction = message.get("direction") if message.get("direction") in {"incoming", "outgoing"} else None
    manifest_direction = voice.get("direction") if voice.get("direction") in {"incoming", "outgoing"} else None
    if normalized_direction and manifest_direction and normalized_direction != manifest_direction:
        raise ValueError(f"max voice direction conflicts with matched source event {activity_id}")
    direction = normalized_direction or manifest_direction
    metadata = {
        "activity_id": activity_id,
        "source_record_id": comment_id,
        "owner_id": voice["owner_id"],
        "source_type": "crm_timeline_comment",
        "timeline_comment_id": comment_id,
        "transcript_sha256": source["sha256"],
        "transcript_sources": source["origins"],
        "channel": "max",
    }
    if message and message.get("event_id"):
        metadata["source_event_id"] = message["event_id"]
    if isinstance(source.get("audio_duration_seconds"), (int, float)) and not isinstance(source.get("audio_duration_seconds"), bool):
        metadata["audio_duration_seconds"] = source["audio_duration_seconds"]
    if source.get("transcription_model"):
        metadata["transcription_model"] = source["transcription_model"]
    return {
        "timestamp": timestamp,
        "event_type": "voice_transcript",
        "source": "practice.transcript_cache",
        "event_id": f"voice_transcript:{activity_id}",
        "direction": direction,
        "content": scrub_text(source["text"]),
        "metadata": metadata,
    }


def prepare_deal(deal_id: str, raw_path: Path, normalizer, quarantine_sources: dict[str, str] | None = None) -> tuple[dict, list[dict], dict]:
    raw_bytes = raw_path.read_bytes()
    raw = json.loads(raw_bytes.decode("utf-8-sig"))
    if str(raw.get("deal_id") or "") != deal_id:
        raise ValueError("raw context deal_id does not match cohort")
    item = deal_item(raw)
    created_at, cutoff, life_days, history, terminal_count, reopened = lifecycle_boundary(raw)
    activities, comments = raw_source_maps(raw, normalizer)
    quarantined_worklog_ids = validate_worklog_quarantine(raw, deal_id, sha256(raw_bytes), quarantine_sources or {})
    worklogs, worklog_ids, post_terminal_worklogs, quarantined_ids, quarantined_entries = manager_worklog_events(
        raw, normalizer, cutoff, quarantined_worklog_ids,
    )
    events = list(worklogs)
    calls = {}
    normalized_communications = normalizer.build_deal_normalized_communications(raw)
    comment_owners = {}

    for row in normalized_communications:
        if row.get("source_type") == "crm_timeline_comment":
            owner = (str(row.get("entity_type") or ""), str(row.get("entity_id") or ""))
            for source_id in row.get("source_ids") if isinstance(row.get("source_ids"), list) else []:
                comment_id = str(source_id).strip()
                if comment_id:
                    previous = comment_owners.get(comment_id)
                    if previous and previous != owner:
                        raise ValueError(f"conflicting owner for source timeline comment {comment_id}")
                    comment_owners[comment_id] = owner
        event = communication_event(row, activities, comments, normalizer, worklog_ids, quarantined_ids)
        if event is None:
            continue
        events.append(event)
        if event["event_type"] == "call" and event["metadata"].get("activity_id"):
            calls[event["metadata"]["activity_id"]] = event

    voices, voice_manifest_hash = max_voice_sources(deal_id, raw, sha256(raw_bytes), comments, comment_owners)

    events.extend(stage_events(history, cutoff))
    task_snapshots_excluded = 0
    task_status_snapshots_excluded = 0
    for task_id, task in task_records(raw):
        event, excluded, status_excluded = task_event(task_id, task, cutoff, normalizer)
        task_snapshots_excluded += int(excluded)
        task_status_snapshots_excluded += int(status_excluded)
        if event:
            events.append(event)
    chats = task_chat_events(raw)
    events.extend(chats)

    voice_messages = {}
    for activity_id, voice in voices.items():
        comment_id = voice["timeline_comment_id"]
        message = timeline_event_for_comment(events, comment_id)
        if message is None:
            raise ValueError(f"max voice activity {activity_id} has no matched raw timeline event")
        source_comment = comments.get(comment_id)
        if source_comment is None:
            raise ValueError(f"max voice activity {activity_id} has no matched raw timeline comment")
        timestamp = source_comment.get("CREATED")
        parse_timestamp(timestamp)
        if before_cutoff(timestamp, cutoff):
            voice_messages[activity_id] = (voice, message, source_comment)

    transcripts = transcript_sources(deal_id)
    unlinked = set(transcripts) - set(calls) - set(voices)
    if unlinked:
        raise ValueError(f"unlinked transcript activity ids for deal {deal_id}")
    for activity_id, source in transcripts.items():
        call = calls.get(activity_id)
        if call is None:
            if activity_id not in voice_messages:
                continue
            voice, message, source_comment = voice_messages[activity_id]
            events.append(max_voice_transcript_event(activity_id, source, voice, message, source_comment))
            continue
        metadata = {
            "activity_id": activity_id,
            "source_record_id": activity_id,
            "transcript_sha256": source["sha256"],
            "transcript_sources": source["origins"],
        }
        if isinstance(source.get("audio_duration_seconds"), (int, float)) and not isinstance(source.get("audio_duration_seconds"), bool):
            metadata["audio_duration_seconds"] = source["audio_duration_seconds"]
        if source.get("transcription_model"):
            metadata["transcription_model"] = source["transcription_model"]
        events.append({
            "timestamp": call["timestamp"],
            "event_type": "call_transcript",
            "source": "practice.transcript_cache",
            "event_id": f"call_transcript:{activity_id}",
            "direction": call["direction"] if call.get("direction") in {"incoming", "outgoing"} else None,
            "content": scrub_text(source["text"]),
            "metadata": metadata,
        })

    kept, post_terminal = [], 0
    for event in events:
        if not before_cutoff(event["timestamp"], cutoff):
            post_terminal += 1
            continue
        event["content"] = scrub_text(event.get("content"))
        kept.append(event)
    kept.sort(key=lambda event: (parse_timestamp(event["timestamp"]), str(event.get("source") or ""), str(event.get("event_id") or "")))
    ids = [event["event_id"] for event in kept if event.get("event_id")]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate source event IDs in deal {deal_id}")

    neutral = {
        "deal_id": deal_id,
        "created_at": created_at,
        "life_days": life_days,
        "pipeline_id": item.get("CATEGORY_ID"),
        "amount": item.get("OPPORTUNITY"),
        "currency": item.get("CURRENCY_ID"),
        "source_id": item.get("SOURCE_ID"),
        "source_description": scrub_text(item.get("SOURCE_DESCRIPTION")),
        "repeat_customer": item.get("IS_RETURN_CUSTOMER"),
        "repeated_approach": item.get("IS_REPEATED_APPROACH"),
    }
    quality = {
        "raw_context_sha256": sha256(raw_bytes),
        "terminal_cutoff_used": "final_terminal_stage_history_timestamp_then_v1_view_filter",
        "terminal_transition_count": terminal_count,
        "terminal_history_requires_review": terminal_count > 1 or reopened,
        "nonterminal_stage_after_first_terminal": reopened,
        "post_terminal_events_excluded": post_terminal,
        "post_terminal_worklogs_excluded": post_terminal_worklogs,
        "post_terminal_task_snapshots_excluded": task_snapshots_excluded,
        "task_status_snapshots_excluded": task_status_snapshots_excluded,
        "transcripts_linked": len(transcripts),
        "max_voice_manifest_available": voice_manifest_hash is not None,
        "max_voice_messages_in_scope": len(voice_messages),
        "max_voice_transcripts_linked": sum(activity_id in transcripts for activity_id in voice_messages),
        "max_voice_without_transcript": len(set(voice_messages) - set(transcripts)),
        "max_voice_manifest_sha256": voice_manifest_hash,
        "event_count": len(kept),
        "event_type_counts": dict(sorted(Counter(event["event_type"] for event in kept).items())),
    }
    if quarantined_ids:
        quality["manager_worklog_quarantine"] = {
            "worklog_ids": sorted(quarantined_ids, key=int),
            "entries_excluded": quarantined_entries,
            "limitation": "Chronology-conflicted mutable manager worklog excluded; inferred year is unverified and no captured edit/version history exists. Raw source retained.",
        }
    return neutral, kept, quality


def output_exists() -> bool:
    return any(path.exists() for path in (
        OUT / "dataset", VIEWS_DIR, OUT / "audit_manifest.json", OUT / "input_freeze.json", SCHEMA_COPY,
    ))


def verify_gate() -> bytes:
    if not COMPLETENESS.is_file():
        raise RuntimeError("completeness.json is missing; build is gated until stage2 reports PASS")
    raw = COMPLETENESS.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict) or data.get("status") != "PASS":
        raise RuntimeError("completeness.json status is not PASS; no dataset outputs were written")
    return raw


def deal_quality_record(deal_id: str, completeness: dict, source_quality: dict | None = None, terminal_source_limited: bool = False) -> dict:
    rows = completeness.get("deals") if isinstance(completeness, dict) else None
    if not isinstance(rows, list):
        raise ValueError("completeness deals must be a list")
    matches = [row for row in rows if isinstance(row, dict) and str(row.get("deal_id") or "") == deal_id]
    if len(matches) != 1:
        raise ValueError(f"expected one completeness row for deal {deal_id}, found {len(matches)}")
    row = matches[0]
    calls = row.get("calls")
    max_voice = row.get("max_voice")
    limitations = row.get("limitations")
    call_limitations = row.get("call_data_limitations")
    voice_limitations = row.get("max_voice_data_limitations")
    sources = row.get("sources")
    if not isinstance(calls, dict) or not isinstance(sources, dict):
        raise ValueError(f"completeness calls/source status missing for deal {deal_id}")
    result = {
        "deal_id": deal_id,
        "calls": calls,
        "limitations": list(limitations) if isinstance(limitations, list) else [],
        "call_data_limitations": call_limitations if isinstance(call_limitations, list) else [],
        "data_quality": row.get("data_quality"),
        "sources": sources,
    }
    if max_voice is not None:
        if not isinstance(max_voice, dict):
            raise ValueError(f"completeness max_voice must be an object for deal {deal_id}")
        result["max_voice"] = max_voice
    if voice_limitations is not None:
        if not isinstance(voice_limitations, list):
            raise ValueError(f"completeness max_voice_data_limitations must be a list for deal {deal_id}")
        result["max_voice_data_limitations"] = voice_limitations
    quarantine = (source_quality or {}).get("manager_worklog_quarantine")
    if quarantine:
        result["manager_worklog_quarantine"] = quarantine
        result["limitations"].append(quarantine["limitation"])
    if terminal_source_limited:
        result["limitations"].append(TERMINAL_SOURCE_LIMITATION)
    return result


def filter_terminal_source_events(events: list[dict], deal_policy: dict) -> list[dict]:
    quarantine_ids = {row["event_id"] for row in deal_policy["quarantine_events"]}
    cutoff_value = deal_policy.get("cutoff_inclusive")
    cutoff = parse_timestamp(cutoff_value) if cutoff_value else None
    return [
        event for event in events
        if event.get("event_id") not in quarantine_ids
        and (cutoff is None or parse_timestamp(event["timestamp"]) < cutoff)
    ]


def validate_terminal_source_deal(deal_policy: dict, neutral: dict, events: list[dict], builder) -> tuple[bytes, list[dict]]:
    deal_id = deal_policy["deal_id"]
    canonical = [{**event, "source_line": line} for line, event in enumerate(events, start=1)]
    timeline_bytes = b"".join(
        (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        for event in events
    )
    if sha256(timeline_bytes) != deal_policy["expected_canonical_timeline_sha256"]:
        raise ValueError(f"canonical timeline hash differs from terminal source policy for deal {deal_id}")

    by_line = {event["source_line"]: event for event in canonical}
    for pin in deal_policy["source_pins"]:
        event = by_line.get(pin["source_line"])
        if (
            not pin.get("view_matches_canonical")
            or event is None
            or event.get("event_id") != pin.get("source_id")
            or event.get("timestamp") != pin.get("timestamp")
            or sha256(str(event.get("content") or "").encode("utf-8")) != pin.get("content_sha256")
        ):
            raise ValueError(f"source pin differs from canonical timeline for deal {deal_id} line {pin.get('source_line')}")

    for row in deal_policy["quarantine_events"]:
        event = by_line.get(row["source_line"])
        if (
            event is None
            or event.get("event_id") != row.get("event_id")
            or sha256(str(event.get("content") or "").encode("utf-8")) != row.get("content_sha256")
        ):
            raise ValueError(f"quarantine event differs from canonical timeline for deal {deal_id}")

    end = parse_timestamp(neutral["created_at"]).date() + timedelta(days=int(neutral["life_days"]))
    prefilter, _, _ = builder.build_view(copy.deepcopy(canonical), end)
    prefilter_bytes = b"".join(
        (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for event in prefilter
    )
    if sha256(prefilter_bytes) != deal_policy["expected_prefilter_view_sha256"]:
        raise ValueError(f"prefilter view hash differs from terminal source policy for deal {deal_id}")
    if len(prefilter) != deal_policy["expected_view_events_before"]:
        raise ValueError(f"prefilter view count differs from terminal source policy for deal {deal_id}")

    kept = filter_terminal_source_events(prefilter, deal_policy)
    if len(prefilter) - len(kept) != deal_policy["expected_events_removed"] or len(kept) != deal_policy["expected_events_after"]:
        raise ValueError(f"filtered view counts differ from terminal source policy for deal {deal_id}")
    return prefilter_bytes, kept


def load_terminal_source_policy(ids: list[str]) -> tuple[dict[str, dict], str, str]:
    raw = TERMINAL_SOURCE_POLICY.read_bytes()
    policy = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(policy, dict) or policy.get("schema_version") != 1 or policy.get("user_approved") is not True:
        raise ValueError("terminal source policy is missing approval or has an unsupported version")
    if sha256((OUT / "cohort.json").read_bytes()) != policy.get("cohort_sha256"):
        raise ValueError("cohort hash differs from terminal source policy")
    if sha256(TERMINAL_SOURCE_PROPOSAL.read_bytes()) != policy.get("proposal_sha256"):
        raise ValueError("proposal hash differs from terminal source policy")
    if policy.get("expected_affected_deals") != 20 or policy.get("expected_events_removed") != 71:
        raise ValueError("terminal source policy has unexpected approved counts")
    limitation = policy.get("limitation")
    if not isinstance(limitation, str) or not limitation.strip():
        raise ValueError("terminal source policy has no approved limitation")

    rows = policy.get("deals")
    if not isinstance(rows, list) or len(rows) != 20:
        raise ValueError("terminal source policy must contain exactly 20 deals")
    by_id = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("deal_id"), str) or row["deal_id"] not in ids or row["deal_id"] in by_id:
            raise ValueError("terminal source policy has an invalid or duplicate deal")
        for key in ("expected_prefilter_view_sha256", "expected_canonical_timeline_sha256"):
            if not isinstance(row.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", row[key]):
                raise ValueError(f"terminal source policy has an invalid {key}")
        if not isinstance(row.get("source_pins"), list) or not isinstance(row.get("quarantine_events"), list):
            raise ValueError("terminal source policy has invalid source pins or quarantine events")
        if type(row.get("expected_events_removed")) is not int or type(row.get("expected_view_events_before")) is not int or type(row.get("expected_events_after")) is not int:
            raise ValueError("terminal source policy has invalid event counts")
        if row["expected_view_events_before"] - row["expected_events_after"] != row["expected_events_removed"]:
            raise ValueError("terminal source policy per-deal counts do not reconcile")
        if row.get("cutoff_inclusive") is not None:
            parse_timestamp(row["cutoff_inclusive"])
        by_id[row["deal_id"]] = row
    if sum(row["expected_events_removed"] for row in rows) != 71:
        raise ValueError("terminal source policy removed-event total is not 71")
    return by_id, sha256(raw), limitation


def apply_terminal_source_policy(policy_by_id: dict[str, dict], policy_sha256: str, limitation: str) -> None:
    manifest_path = OUT / "audit_manifest.json"
    manifest = read_json(manifest_path)
    manifest_rows = {row["deal_id"]: row for row in manifest["deals"]}
    removed_total = 0
    filtered_views = {}
    for deal_id, row in policy_by_id.items():
        view_path = VIEWS_DIR / f"{deal_id}.jsonl"
        original = view_path.read_bytes()
        if sha256(original) != row["expected_prefilter_view_sha256"]:
            raise ValueError(f"written prefilter view hash differs from terminal source policy for deal {deal_id}")
        events = [json.loads(line) for line in original.decode("utf-8-sig").splitlines() if line.strip()]
        kept = filter_terminal_source_events(events, row)
        if len(events) != row["expected_view_events_before"] or len(events) - len(kept) != row["expected_events_removed"] or len(kept) != row["expected_events_after"]:
            raise ValueError(f"written prefilter view count differs from terminal source policy for deal {deal_id}")
        filtered_bytes = b"".join(
            (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            for event in kept
        )
        entry = manifest_rows[deal_id]
        if entry.get("view_event_count") != len(events):
            raise ValueError(f"manifest prefilter view count differs from terminal source policy for deal {deal_id}")
        filtered_views[deal_id] = (view_path, filtered_bytes, len(kept), len(events) - len(kept))
        removed_total += len(events) - len(kept)
    if len(policy_by_id) != 20 or removed_total != 71:
        raise ValueError("terminal source policy affected counts differ from approval")
    for deal_id, (view_path, filtered_bytes, kept_count, removed_count) in filtered_views.items():
        view_path.write_bytes(filtered_bytes)
        entry = manifest_rows[deal_id]
        entry["view_event_count"] = kept_count
        entry["view"]["sha256"] = sha256(filtered_bytes)
        entry["view"]["bytes"] = len(filtered_bytes)
        entry["approx_tokens"]["view"] = math.ceil(len(filtered_bytes) / 4)
        entry["removed_categories"]["terminal_source_policy"] = removed_count
    manifest["totals"]["view_event_count"] -= removed_total
    manifest["totals"]["removed_event_count"] += removed_total
    manifest["totals"]["removed:terminal_source_policy"] = removed_total
    manifest["totals"]["view_approx_tokens"] = sum(row["approx_tokens"]["view"] for row in manifest["deals"] if row.get("status") == "ok")
    manifest["terminal_source_policy_sha256"] = policy_sha256
    manifest["filter_policy"].append(
        f"Approved terminal source policy (sha256 {policy_sha256}) filters blind views only; it removes 71 events across 20 deals. Canonical timelines and source_line pointers are unchanged. Limitation: {limitation}"
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_view_builder():
    spec = importlib.util.spec_from_file_location("validation_v1_audit_view_builder", V1_VIEW_BUILDER)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load v1 audit-view builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_terminal_marker = module.is_terminal_marker
    subjectless_refusal = re.compile(r"\bот\s+нашего\s+(?:варианта|предложения)\s+отказались\b", re.I)

    def terminal_marker(event):
        if original_terminal_marker(event):
            return True
        text = str(event.get("content") or "")
        return any(not re.search(r"\bне\s*$", text[:match.start()], re.I) for match in subjectless_refusal.finditer(text))

    module.is_terminal_marker = terminal_marker
    module.OUT_DIR = OUT
    module.DEALS_DIR = DEALS_DIR
    module.VIEWS_DIR = VIEWS_DIR
    return module


def build_summary(prepared: dict) -> dict:
    deals, totals = [], Counter()
    for deal_id, (_, events, _) in prepared.items():
        content_bytes = sum(len(str(event.get("content") or "").encode("utf-8")) for event in events)
        row = {
            "deal_id": deal_id,
            "events": len(events),
            "content_bytes": content_bytes,
            "approx_tokens": math.ceil(content_bytes / 4),
            "event_types": dict(sorted(Counter(event["event_type"] for event in events).items())),
        }
        deals.append(row)
        totals["events"] += row["events"]
        totals["content_bytes"] += content_bytes
        totals["approx_tokens"] += row["approx_tokens"]
    return {
        "token_method": "ceil(UTF-8 content bytes / 4); coarse size proxy, not a model tokenizer",
        "deal_count": len(deals),
        "totals": dict(sorted(totals.items())),
        "deals": deals,
    }


def build_quality(prepared: dict) -> dict:
    rows, totals = {}, Counter()
    for deal_id, (_, events, source_quality) in prepared.items():
        calls = {str(event["metadata"].get("activity_id")) for event in events if event["event_type"] == "call"}
        transcripts = {str(event["metadata"].get("activity_id")) for event in events if event["event_type"] == "call_transcript"}
        row = {
            **source_quality,
            "calls": len(calls),
            "calls_with_transcript": len(calls & transcripts),
            "calls_without_transcript": len(calls - transcripts),
            "manager_worklog_entries": sum(event["source"] == "manager_worklog" for event in events),
            "tasks": sum(event["event_type"] == "task" for event in events),
            "task_chat_messages": sum(event["event_type"] == "task_chat" for event in events),
        }
        rows[deal_id] = row
        for key in ("calls", "calls_with_transcript", "calls_without_transcript", "transcripts_linked", "max_voice_manifest_available", "max_voice_messages_in_scope", "max_voice_transcripts_linked", "max_voice_without_transcript", "post_terminal_events_excluded", "post_terminal_task_snapshots_excluded", "task_status_snapshots_excluded"):
            totals[key] += row.get(key, 0)
    return {"deal_count": len(rows), "global": dict(sorted(totals.items())), "deals": rows}


def main() -> int:
    gate_bytes = verify_gate()
    completeness_data = json.loads(gate_bytes.decode("utf-8-sig"))
    if output_exists():
        raise FileExistsError("validation outputs already exist; refusing overwrite")
    for path in (V1_VIEW_BUILDER, SCHEMA, CONTRACT):
        if not path.is_file():
            raise FileNotFoundError(f"required audit artifact is missing: {path.name}")
    schema_bytes, contract_bytes, view_builder_bytes = SCHEMA.read_bytes(), CONTRACT.read_bytes(), V1_VIEW_BUILDER.read_bytes()
    ids, labels = cohort_records()
    quarantine_sources, quarantine_policy_sha256 = load_worklog_quarantine_policy()
    if set(quarantine_sources) - set(ids):
        raise ValueError("worklog quarantine policy names deals outside the validation cohort")
    baseline_dir = ROOT / "dataset" / "deals"
    if not baseline_dir.is_dir():
        raise FileNotFoundError("baseline deal directory is unavailable for overlap check")
    baseline_ids = {path.name for path in baseline_dir.iterdir() if path.is_dir()}
    overlap = sorted(set(ids) & baseline_ids)
    if overlap:
        raise ValueError("validation cohort overlaps the existing baseline deal set")

    source_paths = {deal_id: RAW_DIR / f"deal_{deal_id}_context.json" for deal_id in ids}
    missing = [str(path) for path in source_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"raw cohort contexts are incomplete: {len(missing)} file(s) missing")

    normalizer = load_communication_normalizer()
    prepared = {
        deal_id: prepare_deal(deal_id, source_paths[deal_id], normalizer, quarantine_sources.get(deal_id))
        for deal_id in ids
    }
    builder = load_view_builder()
    terminal_policy_by_id, terminal_policy_sha256, terminal_policy_limitation = load_terminal_source_policy(ids)
    for deal_id, deal_policy in terminal_policy_by_id.items():
        neutral, events, _ = prepared[deal_id]
        validate_terminal_source_deal(deal_policy, neutral, events, builder)
    builder_source_bytes = Path(__file__).read_bytes()

    for deal_id, (neutral, events, source_quality) in prepared.items():
        folder = DEALS_DIR / deal_id
        folder.mkdir(parents=True)
        (folder / "neutral.json").write_text(json.dumps(neutral, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        quality = deal_quality_record(deal_id, completeness_data, source_quality, deal_id in terminal_policy_by_id)
        (folder / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        timeline = b"".join(
            (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            for event in events
        )
        (folder / "clean_timeline.jsonl").write_bytes(timeline)

    builder.main()
    apply_terminal_source_policy(terminal_policy_by_id, terminal_policy_sha256, terminal_policy_limitation)
    SCHEMA_COPY.write_bytes(schema_bytes)
    manifest_path = OUT / "audit_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("deal_count") != 50 or len(manifest.get("deals", [])) != 50 or any(row.get("status") != "ok" for row in manifest["deals"]):
        raise RuntimeError("v1 audit-view builder did not produce 50 valid views")
    manifest["expected_deal_count"] = 50
    manifest["complete"] = True
    manifest["blind_to_outcome"] = True
    manifest["filter_policy"].append("Validation source events at or after the final terminal stage timestamp were excluded before writing clean_timeline.jsonl.")
    manifest["filter_policy"].append("Mutable task snapshots whose title explicitly states 'клиент ушел в отказ' (including ё spelling and ушла/ушли forms), or the exact 'подписанный договор и оплата' milestone title with completed status and matching close/status-change/update timestamps, are excluded as task events before view filtering. Negated wording, ordinary budget or technical objections, open milestone tasks, and customer communications are not excluded. Other dated events and the existing v1 terminal/suffix filter are unchanged.")
    manifest["filter_policy"].append("Validation views also cut at the exact subjectless phrase 'от нашего варианта отказались' or 'от нашего предложения отказались'; the negated forms 'от нашего варианта не отказались' and 'не от нашего варианта отказались' do not trigger the cutoff. Existing terminal-marker and post-terminal-suffix handling is unchanged.")
    manifest["filter_policy"].append(f"The five chronology-conflicted mutable manager worklogs in {WORKLOG_QUARANTINE_POLICY.name} (sha256 {quarantine_policy_sha256}) are excluded by exact deal/worklog ID and raw-context SHA-256. Their parsed entries and normalized copies of their source comments are excluded; raw sources and unrelated communications are retained.")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    dataset_manifest_path = DATASET_DIR / "manifest.json"
    dataset_manifest = {
        "version": "validation_50_v1",
        "deal_count": len(ids),
        "baseline_overlap_count": 0,
        "labels_separate_from_blind_inputs": True,
        "deals": [{"deal_id": deal_id, "outcome": labels[deal_id]} for deal_id in sorted(ids, key=int)],
    }
    dataset_manifest_path.write_text(json.dumps(dataset_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path = DATASET_DIR / "summary.json"
    summary_path.write_text(json.dumps(build_summary(prepared), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    quality_path = DATASET_DIR / "build_quality.json"
    quality_path.write_text(json.dumps(build_quality(prepared), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    frozen_deals = []
    manifest_deals = {row["deal_id"]: row for row in manifest["deals"]}
    for deal_id in ids:
        folder = DEALS_DIR / deal_id
        view = manifest_deals[deal_id]["view"]
        frozen_deals.append({
            "deal_id": deal_id,
            "neutral_sha256": sha256((folder / "neutral.json").read_bytes()),
            "clean_timeline_sha256": sha256((folder / "clean_timeline.jsonl").read_bytes()),
            "quality_sha256": sha256((folder / "quality.json").read_bytes()),
            "view_sha256": view["sha256"],
            **prepared[deal_id][2],
        })

    freeze = {
        "status": "validation_50_v1_outcome_blind_views_frozen_before_semantic_audit",
        "outcome_blind_views": True,
        "outcome_labels_separate_from_views": True,
        "deal_count": len(ids),
        "baseline_overlap_count": 0,
        "completeness_sha256": sha256(gate_bytes),
        "worklog_quarantine_policy_sha256": quarantine_policy_sha256,
        "terminal_source_policy_sha256": terminal_policy_sha256,
        "dataset_manifest_sha256": sha256(dataset_manifest_path.read_bytes()),
        "summary_sha256": sha256(summary_path.read_bytes()),
        "build_quality_sha256": sha256(quality_path.read_bytes()),
        "builder_sha256": sha256(builder_source_bytes),
        "view_builder_sha256": sha256(view_builder_bytes),
        "audit_schema_copy": SCHEMA_COPY.name,
        "audit_schema_sha256": sha256(SCHEMA_COPY.read_bytes()),
        "input_contract_sha256": sha256(contract_bytes),
        "audit_manifest_sha256": sha256(manifest_path.read_bytes()),
        "deals": frozen_deals,
    }
    (OUT / "input_freeze.json").write_text(json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"deal_count": len(ids), "views_complete": True, "baseline_overlap_count": 0}, ensure_ascii=False))
    return 0


def self_check() -> None:
    class Normalizer:
        @staticmethod
        def clean_text(value):
            return str(value or "")

        @staticmethod
        def _parse_mirrored_message(value):
            first, _, rest = value.partition("\n")
            return first.partition(":")[0], first.partition(":")[2].strip() + ("\n" + rest if rest else "")

    normalizer = Normalizer()
    sample = communication_event({
        "event_id": "crm_activity:12",
        "source_ids": ["12"],
        "occurred_at": "2026-01-01T10:00:00+03:00",
        "source_type": "crm_activity",
        "channel": "call",
        "direction": "incoming",
    }, {"12": {"SUBJECT": "Call", "DESCRIPTION": "+7 999 123-45-67 https://private.example/file " + "x" * 1300}}, {}, normalizer, set())
    assert sample["metadata"]["activity_id"] == "12"
    assert sample["direction"] == "incoming"
    assert "[PHONE REDACTED]" in sample["content"] and "https://" not in sample["content"]
    assert len(sample["content"]) > 1200
    comment = communication_event({
        "event_id": "crm_timeline_comment:99",
        "source_ids": ["98", "99"],
        "occurred_at": "2026-01-01T11:00:00+03:00",
        "source_type": "crm_timeline_comment",
        "channel": "whatsapp",
    }, {}, {"98": {"COMMENT": "Person name: full customer message\ncontinued"}}, normalizer, set())
    assert comment["content"] == "full customer message\ncontinued"
    assert comment["direction"] is None
    assert comment["metadata"]["source_record_id"] == "98"
    assert comment["metadata"]["source_record_ids"] == ["98", "99"]
    assert timeline_event_for_comment([comment], "99") is comment

    max_voice = max_voice_transcript_event("max-99", {
        "text": "Undiarized transcript", "sha256": "hash", "origins": ["validation_workspace"],
    }, {
        "timeline_comment_id": "99", "owner_id": "123", "direction": "unknown",
    }, {
        "timestamp": "2026-01-01T11:00:00+03:00", "event_id": "crm_mirror:grouped", "direction": None,
    }, {"ID": "99", "CREATED": "2026-01-01T11:02:00+03:00"})
    assert max_voice["timestamp"] == "2026-01-01T11:02:00+03:00"
    assert max_voice["direction"] is None
    assert max_voice["metadata"]["source_record_id"] == "99"
    assert max_voice["metadata"]["source_event_id"] == "crm_mirror:grouped"
    assert "speaker" not in max_voice["metadata"]
    try:
        max_voice_transcript_event("max-99", {"text": "x", "sha256": "hash", "origins": []}, {
            "timeline_comment_id": "99", "owner_id": "123", "direction": "unknown",
        }, None, None)
    except ValueError:
        pass
    else:
        raise AssertionError("unlinked Max voice transcript must fail closed")

    chat = task_chat_events({"bitrix_task_chats": {"41": {
        "ok": True,
        "response": {"result": {"messages": [{
            "id": "msg-8", "date": "2026-01-01T12:00:00+03:00", "text": "Task chat message", "author_id": "6",
        }] }},
    }}})
    assert len(chat) == 1 and chat[0]["event_id"] == "task_chat:41:msg-8"
    assert chat[0]["metadata"]["author_id"] == "6" and chat[0]["direction"] is None

    completeness_row = {
        "deal_id": "123", "calls": {"eligible_calls_ge_36": 2},
        "limitations": ["missing transcript"], "call_data_limitations": [],
        "data_quality": "partial", "sources": {"call_audio_manifest": "ok", "max_voice_manifest": "ok"},
        "max_voice": {"total_messages": 3, "messages_with_transcript": 1},
        "max_voice_data_limitations": ["2 unavailable messages"],
        "outcome": "WON", "stage_semantic_id": "S", "close_date": "2026-01-02",
    }
    quarantine_quality = {"worklog_ids": ["44"], "entries_excluded": 1, "limitation": "Chronology-conflicted worklog excluded"}
    quality = deal_quality_record("123", {"deals": [completeness_row]}, {"manager_worklog_quarantine": quarantine_quality})
    assert quality["max_voice"] == {"total_messages": 3, "messages_with_transcript": 1}
    assert quality["max_voice_data_limitations"] == ["2 unavailable messages"]
    assert quality["sources"]["max_voice_manifest"] == "ok"
    assert quality["manager_worklog_quarantine"] == quarantine_quality
    assert quality["limitations"] == ["missing transcript", "Chronology-conflicted worklog excluded"]
    assert completeness_row["limitations"] == ["missing transcript"]
    assert "max_voice" not in quality["calls"]
    assert set(quality) == {"deal_id", "calls", "limitations", "call_data_limitations", "data_quality", "sources", "max_voice", "max_voice_data_limitations", "manager_worklog_quarantine"}
    assert "outcome" not in quality and "stage_semantic_id" not in quality and "close_date" not in quality

    cutoff = parse_timestamp("2026-01-02T10:00:00+03:00")
    raw = {"manager_worklogs": [{
        "comment_id": "44", "bitrix_created_at": "2026-01-01T12:00:00+03:00", "author_id": "8",
        "entries": [{"entry_date": "2026-01-01", "date_raw": "01.01", "year_inferred": True, "text": "Manager claim"}],
    }]}
    worklogs, ids, post_cutoff, quarantined_ids, quarantined_entries = manager_worklog_events(raw, normalizer, cutoff)
    assert ids == {"44"} and post_cutoff == 0
    assert quarantined_ids == set() and quarantined_entries == 0
    assert worklogs[0]["event_type"] == "comment" and worklogs[0]["source"] == "manager_worklog"
    assert worklogs[0]["timestamp"] == "2026-01-01T00:00:00+03:00"
    assert worklogs[0]["metadata"]["worklog_recorded_at"] == raw["manager_worklogs"][0]["bitrix_created_at"]
    raw_hash = sha256(json.dumps(raw, separators=(",", ":")).encode("utf-8"))
    assert validate_worklog_quarantine(raw, "123", raw_hash, {"44": raw_hash}) == {"44"}
    quarantined, excluded_ids, post_cutoff, quarantined_ids, quarantined_entries = manager_worklog_events(raw, normalizer, cutoff, {"44"})
    assert not quarantined and excluded_ids == {"44"} and post_cutoff == 0
    assert quarantined_ids == {"44"} and quarantined_entries == 1
    try:
        validate_worklog_quarantine(raw, "123", raw_hash + "0", {"44": raw_hash})
    except ValueError:
        pass
    else:
        raise AssertionError("quarantine must fail closed when the raw-context hash changes")
    try:
        validate_worklog_quarantine(raw, "123", raw_hash, {"45": raw_hash})
    except ValueError:
        pass
    else:
        raise AssertionError("quarantine must fail closed when the source worklog ID is absent")

    try:
        communication_event({
            "event_id": "crm_timeline_comment:98", "source_ids": ["98", "44"],
            "occurred_at": "2026-01-01T11:00:00+03:00", "source_type": "crm_timeline_comment", "channel": "message",
        }, {}, {"98": {"COMMENT": "Other communication"}, "44": {"COMMENT": "Quarantined manager comment"}}, normalizer, {"44"}, {"44"})
    except ValueError:
        pass
    else:
        raise AssertionError("mixed normalized source IDs must fail closed")
    assert communication_event({
        "event_id": "crm_timeline_comment:44", "source_ids": ["44"],
        "occurred_at": "2026-01-01T11:00:00+03:00", "source_type": "crm_timeline_comment", "channel": "message",
    }, {}, {"44": {"COMMENT": "Quarantined manager comment"}}, normalizer, {"44"}, {"44"}) is None

    raw = {
        "deal": {"item": {"DATE_CREATE": "2026-01-01T10:00:00+03:00"}},
        "stage_history": {"ok": True, "items": [
            {"CREATED_TIME": "2026-01-02T10:00:00+03:00", "STAGE_SEMANTIC_ID": "P"},
            {"CREATED_TIME": "2026-01-03T10:00:00+03:00", "STAGE_SEMANTIC_ID": "F"},
        ]},
    }
    created, stage_cutoff, life_days, _, terminal_count, reopened = lifecycle_boundary(raw)
    assert created == raw["deal"]["item"]["DATE_CREATE"] and life_days == 2 and terminal_count == 1 and not reopened
    assert before_cutoff("2026-01-02T10:00:00+03:00", stage_cutoff)
    assert not before_cutoff("2026-01-03T10:00:00+03:00", stage_cutoff)

    assert has_customer_refusal_status("CRM: проверка квала. Клиент ушёл в отказ")
    assert has_customer_refusal_status("CRM: проверка квала. Клиент ушел в отказ")
    assert has_customer_refusal_status("CRM: проверка квала. Клиент ушла в отказ")
    assert has_customer_refusal_status("CRM: проверка квала. Клиент ушли в отказ")
    assert not has_customer_refusal_status("CRM: проверка квала. Клиент не ушёл в отказ")
    assert not has_customer_refusal_status("Не клиент ушёл в отказ")
    assert not has_customer_refusal_status("CRM: уточнить бюджет и сроки интеграции")
    cutoff = parse_timestamp("2026-02-05T00:00:00+07:00")
    def task(title, created="2026-01-29T12:59:23+07:00", changed="2026-02-04T20:29:29+07:00"):
        return {"id": "31977", "title": title, "description": "", "status": "5", "createdDate": created,
                "changedDate": changed, "statusChangedDate": changed, "closedDate": changed}
    status_event, post_cutoff, status_excluded = task_event("31977", task("CRM: проверка квала. Клиент ушел в отказ"), cutoff, normalizer)
    assert status_event is None and not post_cutoff and status_excluded
    for title in ("Клиент не ушёл в отказ", "Не клиент ушёл в отказ", "Уточнить бюджет и сроки интеграции"):
        event, post_cutoff, status_excluded = task_event("31977", task(title), cutoff, normalizer)
        assert event is not None and not post_cutoff and not status_excluded
    later_event, post_cutoff, status_excluded = task_event(
        "31978", task("Уточнить детали встречи", "2026-02-01T10:00:00+07:00", "2026-02-02T10:00:00+07:00"), cutoff, normalizer,
    )
    assert later_event is not None and later_event["timestamp"] == "2026-02-01T10:00:00+07:00"
    assert not post_cutoff and not status_excluded
    completed_milestone = task(TERMINAL_MILESTONE_TASK_TITLE, "2026-02-01T10:00:00+07:00", "2026-02-02T10:00:00+07:00")
    milestone_event, post_cutoff, status_excluded = task_event("34271", completed_milestone, cutoff, normalizer)
    assert milestone_event is None and not post_cutoff and status_excluded
    open_milestone = {**completed_milestone, "status": "2", "closedDate": None}
    milestone_event, post_cutoff, status_excluded = task_event("34271", open_milestone, cutoff, normalizer)
    assert milestone_event is not None and not post_cutoff and not status_excluded
    customer_message = communication_event({
        "event_id": "crm_timeline_comment:777", "source_ids": ["777"],
        "occurred_at": "2026-02-02T12:00:00+07:00", "source_type": "crm_timeline_comment", "channel": "message",
    }, {}, {"777": {"COMMENT": "Подписанный договор и оплата"}}, normalizer, set())
    assert customer_message is not None and customer_message["content"] == "Подписанный договор и оплата"

    view_builder = load_view_builder()
    terminal = lambda text: view_builder.is_terminal_marker({"event_type": "comment", "content": text, "metadata": {}})
    assert terminal("от нашего варианта отказались")
    assert terminal("От нашего предложения отказались")
    assert not terminal("от нашего варианта не отказались")
    assert not terminal("не от нашего варианта отказались")
    assert not terminal("не  от нашего варианта отказались")
    assert not terminal("не\tот нашего предложения отказались")
    assert not terminal("техническая схема требует доработки")
    kept, removed, _ = view_builder.build_view([
        {"timestamp": "2026-01-01T10:00:00+03:00", "event_type": "comment", "content": "До отказа", "metadata": {}, "source_line": 1},
        {"timestamp": "2026-01-01T11:00:00+03:00", "event_type": "comment", "content": "от нашего варианта отказались", "metadata": {}, "source_line": 2},
        {"timestamp": "2026-01-01T12:00:00+03:00", "event_type": "comment", "content": "Позднее уточнение", "metadata": {}, "source_line": 3},
    ], datetime(2026, 1, 2).date())
    assert [event["source_line"] for event in kept] == [1]
    assert removed["terminal_marker"] == 1 and removed["post_terminal_suffix"] == 1

    terminal_cutoff = "2026-01-02T10:00:00+03:00"
    source_events = [
        {"timestamp": "2026-01-01T09:00:00+03:00", "event_type": "comment", "event_id": "keep", "content": "Keep", "source": "crm", "metadata": {}},
        {"timestamp": terminal_cutoff, "event_type": "comment", "event_id": "boundary", "content": "Boundary", "source": "crm", "metadata": {}},
        {"timestamp": "2026-01-01T11:00:00+03:00", "event_type": "comment", "event_id": "negative", "content": "от нашего варианта не отказались", "source": "crm", "metadata": {}},
        {"timestamp": "2026-01-01T12:00:00+03:00", "event_type": "comment", "event_id": "quarantine", "content": "Pinned quarantine row", "source": "crm", "metadata": {}},
    ]
    canonical = [{**event, "source_line": line} for line, event in enumerate(source_events, start=1)]
    timeline_bytes = b"".join((json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8") for event in source_events)
    sample_neutral = {"created_at": "2026-01-01T00:00:00+03:00", "life_days": 2}
    prefilter, _, _ = view_builder.build_view(copy.deepcopy(canonical), parse_timestamp("2026-01-03T00:00:00+03:00").date())
    prefilter_bytes = b"".join((json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for event in prefilter)
    pin = {"source_line": 3, "source_id": "negative", "timestamp": source_events[2]["timestamp"], "content_sha256": sha256(source_events[2]["content"].encode("utf-8")), "view_matches_canonical": True}
    source_policy_deal = {
        "deal_id": "123", "expected_canonical_timeline_sha256": sha256(timeline_bytes),
        "expected_prefilter_view_sha256": sha256(prefilter_bytes), "expected_view_events_before": 4,
        "expected_events_removed": 2, "expected_events_after": 2, "cutoff_inclusive": terminal_cutoff,
        "source_pins": [pin], "quarantine_events": [{"source_line": 4, "event_id": "quarantine", "content_sha256": sha256(source_events[3]["content"].encode("utf-8"))}],
    }
    _, source_kept = validate_terminal_source_deal(source_policy_deal, sample_neutral, source_events, view_builder)
    assert [event["event_id"] for event in source_kept] == ["keep", "negative"]
    assert len(filter_terminal_source_events(source_kept, {"quarantine_events": [], "cutoff_inclusive": None})) == 2
    bad_source_policy = {**source_policy_deal, "source_pins": [{**pin, "content_sha256": "0" * 64}]}
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "must-not-be-written"
        try:
            validate_terminal_source_deal(bad_source_policy, sample_neutral, source_events, view_builder)
            output.write_text("unexpected", encoding="utf-8")
        except ValueError:
            pass
        assert not output.exists()

    with tempfile.TemporaryDirectory() as directory:
        temp_root = Path(directory)
        temp_views = temp_root / "views"
        temp_views.mkdir()
        old_out, old_views = OUT, VIEWS_DIR
        try:
            globals()["OUT"], globals()["VIEWS_DIR"] = temp_root, temp_views
            policy_rows, manifest_rows = {}, []
            prefilter_count = removed_total = 0
            for index in range(1, 21):
                deal_id = str(index)
                removed = 4 if index <= 17 else 1
                cutoff = "2026-01-02T10:00:00+03:00"
                events = [{"timestamp": "2026-01-01T10:00:00+03:00", "event_type": "comment", "event_id": f"keep-{deal_id}", "source_line": 1}]
                events.extend({"timestamp": cutoff, "event_type": "comment", "event_id": f"drop-{deal_id}-{n}", "source_line": n + 2} for n in range(removed))
                original = b"".join((json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for event in events)
                (temp_views / f"{deal_id}.jsonl").write_bytes(original)
                policy_rows[deal_id] = {
                    "expected_prefilter_view_sha256": sha256(original), "expected_view_events_before": len(events),
                    "expected_events_removed": removed, "expected_events_after": 1,
                    "cutoff_inclusive": cutoff, "quarantine_events": [],
                }
                view_summary = {"sha256": sha256(original), "bytes": len(original)}
                manifest_rows.append({"deal_id": deal_id, "status": "ok", "view_event_count": len(events), "view": view_summary, "approx_tokens": {"view": math.ceil(len(original) / 4)}, "removed_categories": {}})
                prefilter_count += len(events)
                removed_total += removed
            synthetic_manifest = {"deals": manifest_rows, "totals": {"view_event_count": prefilter_count, "removed_event_count": 0, "view_approx_tokens": 0}, "filter_policy": []}
            (temp_root / "audit_manifest.json").write_text(json.dumps(synthetic_manifest), encoding="utf-8")
            apply_terminal_source_policy(policy_rows, "a" * 64, "synthetic limitation")
            updated_manifest = json.loads((temp_root / "audit_manifest.json").read_text(encoding="utf-8"))
            assert updated_manifest["totals"]["view_event_count"] == 20
            assert updated_manifest["totals"]["removed_event_count"] == 71 == removed_total
            assert updated_manifest["terminal_source_policy_sha256"] == "a" * 64
            for row in updated_manifest["deals"]:
                written = (temp_views / f"{row['deal_id']}.jsonl").read_bytes()
                assert row["view_event_count"] == 1 and row["view"]["sha256"] == sha256(written)
                assert row["removed_categories"]["terminal_source_policy"] == policy_rows[row["deal_id"]]["expected_events_removed"]
        finally:
            globals()["OUT"], globals()["VIEWS_DIR"] = old_out, old_views
    print("validation builder self-check: PASS")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-check"]:
        self_check()
    elif sys.argv[1:]:
        raise SystemExit("usage: build_validation_dataset.py [--self-check]")
    else:
        raise SystemExit(main())
