"""Build outcome-blind snapshot inputs from the immutable dataset."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEALS = ROOT / "dataset" / "deals"
FEATURES = ROOT / "research_outputs" / "discovery_v1" / "feature_candidates.json"
KINDS = ("D3", "D7", "T25", "T50", "T80")
RESULT_WORD = re.compile(r"\b(?:WON|LOST)\b", re.IGNORECASE)
# A short deal has a terminal customer decision inside its otherwise full D7 window.
# Exclude that event and later correspondence from the blind input.
BLIND_CONTENT_LIMIT = {"18929": datetime.fromisoformat("2026-08-31T13:37:46+03:00")}
CONTAMINATED_EVENTS = {
    ("18773", "2026-07-28T16:10:00+03:00", "source_ids=2942251"),
    ("6135", "2025-10-17T10:24:29+03:00", "source_ids=2339925"),
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def event_id(row):
    meta = row.get("metadata") or {}
    for key in ("activity_id", "message_id", "task_id", "worklog_id", "email_id", "id"):
        if meta.get(key) is not None:
            return f"{key}={meta[key]}"
    ids = meta.get("source_ids")
    return f"source_ids={','.join(map(str, ids))}" if isinstance(ids, list) and ids else None


def visible_event(row):
    if row.get("event_type") == "stage_change":
        return None
    content = row.get("content")
    if isinstance(content, str):
        content = RESULT_WORD.sub("[REDACTED]", content).replace("✅", "").replace("❌", "")
    return {
        "timestamp": row["timestamp"],
        "event_type": row.get("event_type"),
        "event_id": event_id(row),
        "direction": row.get("direction"),
        "content": content,
        "date_only": bool((row.get("metadata") or {}).get("date_only")),
    }


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    snapshots = OUT / "snapshots"
    snapshots.mkdir(exist_ok=True)
    frozen = read_json(FEATURES)
    contract = {
        "source_catalog": "research_outputs/discovery_v1/feature_candidates.json",
        "instructions": "Classify current state at cutoff using only supplied events. Never infer missing facts. Use UNKNOWN when evidence is insufficient. Do not infer final result.",
        "features": [
            {"feature_id": f["feature_id"], "name": f["name"], "definition": f["definition"],
             "type": f["jev_suitability"]["type"], "question": f["jev_suitability"]["question"],
             "values": f["jev_suitability"]["anchors_or_choices"] + ["UNKNOWN"]}
            for f in frozen["features"]
        ],
        "label_record": {
            "feature_id": "R01..R10", "value": "exact string from values",
            "confidence": "high | medium | low",
            "evidence": [{"timestamp": "ISO timestamp", "event_type": "source event type", "event_id": "source identifier or null", "short_paraphrase": "brief evidence"}],
            "reason_short": "For UNKNOWN, name the missing information."
        },
    }
    (OUT / "labeling_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"version": "validation_2a", "cutoff_method": "D3/D7: created_at plus 3/7 days. T25/T50/T80: created_at plus 25/50/80% of neutral.life_days (integer-day precision). D7 beyond life_days uses recorded pre-decision events within its window; terminal stage, explicit terminal-decision events, and worklogs with later-dated embedded updates are removed.", "blind_content_limits": {k: v.isoformat() for k, v in BLIND_CONTENT_LIMIT.items()}, "excluded_embedded_future_events": [list(x) for x in sorted(CONTAMINATED_EVENTS)], "snapshots": [], "input_issues": []}
    for deal_dir in sorted(DEALS.iterdir(), key=lambda d: int(d.name)):
        if not deal_dir.is_dir():
            continue
        try:
            neutral = read_json(deal_dir / "neutral.json")
            created = datetime.fromisoformat(neutral["created_at"])
            life = int(neutral["life_days"])
            events = []
            for line_no, line in enumerate((deal_dir / "clean_timeline.jsonl").read_text(encoding="utf-8-sig").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    ts = datetime.fromisoformat(row["timestamp"])
                    if ts >= created:
                        event = visible_event(row)
                        if event is not None and (deal_dir.name, event["timestamp"], event["event_id"]) not in CONTAMINATED_EVENTS:
                            events.append((ts, event))
                except (ValueError, KeyError, TypeError) as exc:
                    manifest["input_issues"].append({"deal_id": deal_dir.name, "line": line_no, "issue": str(exc)})
            events.sort(key=lambda pair: pair[0])
            for kind in KINDS:
                if kind.startswith("D"):
                    day = int(kind[1:])
                    full = day > life
                    cutoff = created + timedelta(days=life + 1 if full else day)
                else:
                    full = False
                    cutoff = created + timedelta(days=life * int(kind[1:]) / 100)
                selected = [event for ts, event in events if ts <= cutoff and (deal_dir.name not in BLIND_CONTENT_LIMIT or ts < BLIND_CONTENT_LIMIT[deal_dir.name])]
                path = snapshots / f"{deal_dir.name}_{kind}.json"
                payload = {"deal_id": deal_dir.name, "snapshot": kind, "created_at": neutral["created_at"],
                           "cutoff": cutoff.isoformat(), "history_status": "full_preoutcome_history" if full else "partial_history",
                           "events": selected}
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                manifest["snapshots"].append({"deal_id": deal_dir.name, "snapshot": kind,
                                              "cutoff": cutoff.isoformat(), "history_status": payload["history_status"],
                                              "event_count": len(selected), "file": str(path.relative_to(OUT)).replace("\\", "/")})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            manifest["input_issues"].append({"deal_id": deal_dir.name, "issue": str(exc)})
    (OUT / "snapshot_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    assert len(manifest["snapshots"]) == 115, "Expected 23 deals x 5 snapshots"
    assert all(not RESULT_WORD.search((OUT / x["file"]).read_text(encoding="utf-8")) for x in manifest["snapshots"])


if __name__ == "__main__":
    build()
