"""Build deterministic, outcome-blind semantic audit views from the frozen dataset."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = OUT_DIR.parents[1]
DEALS_DIR = REPO_ROOT / "dataset" / "deals"
VIEWS_DIR = OUT_DIR / "views"
REMOVED_CATEGORIES = (
    "terminal_marker",
    "post_terminal_suffix",
    "crm_stage_change",
    "metadata_only_call_shell",
    "neutral_lifecycle_event",
)
TOKEN_BYTES = 4  # Coarse, deterministic byte-count proxy; no tokenizer/API used.
EMBEDDED_DATE_RE = re.compile(
    r"(?<!\d)(?:"
    r"(?P<iso_year>20\d{2})-(?P<iso_month>\d{2})-(?P<iso_day>\d{2})|"
    r"(?P<year_day>0?[1-9]|[12]\d|3[01])\.(?P<year_month>0?[1-9]|1[0-2])\.(?P<year_value>\d{2,4})|"
    r"(?P<day>0[1-9]|[12]\d|3[01])\.(?P<month>0[1-9]|1[0-2])"
    r")(?!\d)"
)

# Deliberately limited to explicit closure language. Ordinary objections, risks,
# and deal discussion stay available as pre-outcome evidence.
TERMINAL_RE = re.compile(
    r"\b(?:deal|opportunity|transaction)\s+(?:closed\s+(?:won|lost)|won|lost)\b"
    r"|\bclosed\s+(?:won|lost)\b"
    r"|\bсделк[а-яё]*\s+(?:успешно\s+)?(?:не\s+реализован[а-яё]*|"
    r"закрыт[а-яё]*|заверш[а-яё]*|реализован[а-яё]*|выигран[а-яё]*|проигран[а-яё]*)\b"
    r"|\b(?:закрыт[а-яё]*|заверш[а-яё]*)\s+сделк[а-яё]*\b"
    r"|\b(?:клиент|заказчик|покупатель)\s+(?:отказал[а-яё]*|отказался|отказалась|отказались)\s+"
    r"(?:от\s+)?(?:покупки|сотрудничества|сделки|заключения\s+договора|"
    r"дальнейшей\s+работы|продолжения\s+переговоров|проекта|услуг[а-яё]*)\b"
    r"|\b(?:клиент|заказчик|покупатель)\s+(?:окончательно\s+)?"
    r"(?:отказался|отказалась|отказались)(?=\s*[,;.!?]|\s*$)"
    r"|\b(?:клиент|заказчик|покупатель)\s+(?:решил|решила|решили)\s+не\s+"
    r"(?:покупать|продолжать\s+(?:работу|переговоры|сотрудничество)|заключать\s+договор)\b"
    r"|\b(?:закрыли|завершили)\s+сделк[а-яё]*\b",
    re.IGNORECASE,
)
# Treat "not this time" as terminal only within 300 characters after a clear
# implementation failure, not when the phrase appears in routine scheduling.
REFUSAL_AFTER_INFEASIBILITY_RE = re.compile(
    r"\b(?:не\s+сможет|не\s+получится|невозможно)\b[\s\S]{0,300}"
    r"\b(?:ну[, ]*)?значит[, ]+не\s+в\s+этот\s+раз\b",
    re.IGNORECASE,
)
STAGE_TERMINAL_RE = re.compile(
    r"\b(?:won|lost|closed\s+(?:won|lost)|успешно\s+реализован[а-яё]*|"
    r"не\s+реализован[а-яё]*|реализован[а-яё]*|выигран[а-яё]*|"
    r"проигран[а-яё]*|закрыт[а-яё]*|завершен[а-яё]*|завершена|завершено)\b",
    re.IGNORECASE,
)
TERMINAL_EVENT_TYPE_RE = re.compile(r"(?:^|[_ -])(?:won|lost|closed|terminal|outcome)(?:$|[_ -])", re.I)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def approx_tokens(byte_count: int) -> int:
    return math.ceil(byte_count / TOKEN_BYTES)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def embedded_date(match: re.Match, event_date: date) -> date | None:
    if match.group("iso_year"):
        return date(int(match.group("iso_year")), int(match.group("iso_month")), int(match.group("iso_day")))
    if match.group("year_value"):
        year = int(match.group("year_value"))
        return date(year + 2000 if year < 100 else year, int(match.group("year_month")), int(match.group("year_day")))
    day, month = int(match.group("day")), int(match.group("month"))
    candidates = []
    for year in range(event_date.year - 1, event_date.year + 2):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            pass
    return min(candidates, key=lambda candidate: abs((candidate - event_date).days)) if candidates else None


def trim_future_dated_comment(event: dict, lifecycle_end: date) -> tuple[dict, int]:
    content = event.get("content")
    if event.get("event_type") != "comment" or not isinstance(content, str) or not content:
        return event, 0
    event_date = parse_timestamp(event["timestamp"]).date()
    matches = list(EMBEDDED_DATE_RE.finditer(content))
    spans = []
    for i, match in enumerate(matches):
        parsed = embedded_date(match, event_date)
        if parsed and parsed > lifecycle_end:
            spans.append((match.start(), matches[i + 1].start() if i + 1 < len(matches) else len(content)))
    if not spans:
        return event, 0
    # Keep line breaks so the remaining dated entries retain their layout.
    chars = list(content)
    for start, end in spans:
        for i in range(start, end):
            if chars[i] not in "\r\n":
                chars[i] = ""
    cleaned = "".join(chars)
    result = dict(event)
    result["content"] = cleaned
    return result, len(spans)


def marker_text(event: dict) -> str:
    parts = [event.get("content")]
    metadata = event.get("metadata")

    def collect(value):
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(metadata)
    return " ".join(part for part in parts if isinstance(part, str)).replace("ё", "е").replace("Ё", "Е")


def is_terminal_marker(event: dict) -> bool:
    event_type = str(event.get("event_type", ""))
    if TERMINAL_EVENT_TYPE_RE.search(event_type):
        return True
    text = marker_text(event).strip()
    if TERMINAL_RE.search(text):
        return True
    if REFUSAL_AFTER_INFEASIBILITY_RE.search(text):
        return True
    return event_type == "stage_change" and bool(STAGE_TERMINAL_RE.search(text))


def deal_sort_key(path: Path):
    return (0, int(path.name)) if path.name.isdigit() else (1, path.name)


def read_deal(folder: Path) -> tuple[list[dict], date | None, list[str]]:
    issues = []
    neutral_path = folder / "neutral.json"
    timeline_path = folder / "clean_timeline.jsonl"
    if not neutral_path.is_file():
        issues.append("missing neutral.json")
    if not timeline_path.is_file():
        issues.append("missing clean_timeline.jsonl")
    if issues:
        return [], None, issues

    try:
        neutral = json.loads(neutral_path.read_text(encoding="utf-8"))
        if not isinstance(neutral, dict):
            raise ValueError("neutral.json must be an object")
        if str(neutral.get("deal_id")) != folder.name:
            raise ValueError("neutral.json deal_id does not match directory")
        created_at = parse_timestamp(str(neutral["created_at"])).date()
        life_days = int(neutral["life_days"])
        if life_days < 0:
            raise ValueError("neutral.json life_days must be nonnegative")
        lifecycle_end = created_at + timedelta(days=life_days)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        issues.append(f"neutral.json: {exc}")
        return [], None, issues
    except (KeyError, TypeError) as exc:
        issues.append(f"neutral.json: missing or invalid lifecycle field {exc}")
        return [], None, issues

    events = []
    try:
        with timeline_path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError(f"line {line_number}: event must be an object")
                if not all(key in event for key in ("timestamp", "event_type", "source", "metadata")):
                    raise ValueError(f"line {line_number}: missing required event field")
                if not isinstance(event["metadata"], dict):
                    raise ValueError(f"line {line_number}: metadata must be an object")
                if not isinstance(event["timestamp"], str):
                    raise ValueError(f"line {line_number}: timestamp must be a string")
                try:
                    parse_timestamp(event["timestamp"])
                except ValueError as exc:
                    raise ValueError(f"line {line_number}: invalid timestamp") from exc
                event["source_line"] = line_number
                events.append(event)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        issues.append(f"clean_timeline.jsonl: {exc}")
    return events, lifecycle_end, issues


def build_view(events: list[dict], lifecycle_end: date) -> tuple[list[dict], dict[str, int], list[dict]]:
    removed = dict.fromkeys(REMOVED_CATEGORIES, 0)
    eligible = []
    content_segments = []
    for event in events:
        if parse_timestamp(event["timestamp"]).date() > lifecycle_end:
            removed["neutral_lifecycle_event"] += 1
            continue
        event, count = trim_future_dated_comment(event, lifecycle_end)
        if count:
            content_segments.append({"source_line": event["source_line"], "segment_count": count})
        eligible.append(event)

    cutoff = next((i for i, event in enumerate(eligible) if is_terminal_marker(event)), None)
    kept = []
    for i, event in enumerate(eligible):
        if cutoff is not None and i == cutoff:
            removed["terminal_marker"] += 1
        elif cutoff is not None and i > cutoff:
            removed["post_terminal_suffix"] += 1
        elif event.get("event_type") == "stage_change":
            removed["crm_stage_change"] += 1
        elif event.get("event_type") == "call" and not str(event.get("content") or "").strip():
            removed["metadata_only_call_shell"] += 1
        else:
            kept.append(event)
    return kept, removed, content_segments


def main() -> int:
    VIEWS_DIR.mkdir(parents=True, exist_ok=True)
    folders = sorted((p for p in DEALS_DIR.iterdir() if p.is_dir()), key=deal_sort_key)
    deals = []
    totals = Counter()

    for folder in folders:
        neutral_path = folder / "neutral.json"
        timeline_path = folder / "clean_timeline.jsonl"
        events, lifecycle_end, issues = read_deal(folder)
        entry = {"deal_id": folder.name, "status": "issue" if issues else "ok", "issues": issues}
        input_files = {}
        for name, path in (("neutral.json", neutral_path), ("clean_timeline.jsonl", timeline_path)):
            if path.is_file():
                raw = path.read_bytes()
                input_files[name] = {"sha256": sha256(raw), "bytes": len(raw), "approx_tokens": approx_tokens(len(raw))}
        entry["inputs"] = input_files

        if issues:
            deals.append(entry)
            continue

        view_events, removed, content_segments = build_view(events, lifecycle_end)
        view_path = VIEWS_DIR / f"{folder.name}.jsonl"
        view_bytes = b"".join(
            (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            for event in view_events
        )
        view_path.write_bytes(view_bytes)
        original_bytes = input_files["clean_timeline.jsonl"]["bytes"]
        entry.update({
            "original_event_count": len(events),
            "view_event_count": len(view_events),
            "approx_tokens": {"original": approx_tokens(original_bytes), "view": approx_tokens(len(view_bytes))},
            "removed_categories": removed,
            "removed_content_segments": content_segments,
            "removed_content_segment_count": sum(item["segment_count"] for item in content_segments),
            "view": {"path": f"views/{folder.name}.jsonl", "sha256": sha256(view_bytes), "bytes": len(view_bytes)},
        })
        totals["original_event_count"] += len(events)
        totals["view_event_count"] += len(view_events)
        totals["removed_event_count"] += sum(removed.values())
        totals["removed_content_segment_count"] += sum(item["segment_count"] for item in content_segments)
        totals["original_approx_tokens"] += approx_tokens(original_bytes)
        totals["view_approx_tokens"] += approx_tokens(len(view_bytes))
        for category, count in removed.items():
            totals[f"removed:{category}"] += count
        deals.append(entry)

    manifest = {
        "version": "1.0",
        "blind_to_outcome": True,
        "expected_deal_count": 23,
        "deal_count": len(folders),
        "complete": len(folders) == 23 and all(deal["status"] == "ok" for deal in deals),
        "approx_token_method": f"ceil(UTF-8 bytes / {TOKEN_BYTES}); coarse size proxy, not a model tokenizer",
        "filter_policy": [
            "Use neutral created_at + life_days as a strict calendar end; remove later event rows and later date-stamped comment segments.",
            "Then cut at the first remaining explicit terminal event type, past-tense closure status, or customer refusal to proceed; a 'not this time' reply counts only within 300 characters after a clear implementation failure. Remove later file-order rows.",
            "Remove all structured stage_change events and empty call metadata shells.",
            "Preserve same-day events, other event text, IDs, metadata, and input row order; add 1-based physical source_line.",
        ],
        "totals": dict(sorted(totals.items())),
        "deals": deals,
    }
    (OUT_DIR / "audit_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"deal_count": len(folders), "complete": manifest["complete"], "totals": manifest["totals"]}, ensure_ascii=False))
    return 0 if manifest["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
