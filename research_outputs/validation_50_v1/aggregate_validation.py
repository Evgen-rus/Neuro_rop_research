"""Join frozen Stage 6 taxonomy memberships to outcomes after all freeze gates pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import check_audits


HERE = Path(__file__).resolve().parent
OUTCOMES = ("WON", "LOST")
MEMBERSHIP_STATUSES = ("PRESENT", "NOT_SHOWN", "UNCERTAIN")
RELIABILITY_RATINGS = {"AGREE", "PARTIAL", "DISAGREE"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(f"required artifact unavailable: {path.name} ({type(exc).__name__})") from exc


def decode_json(raw: bytes, name: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON in {name} ({type(exc).__name__})") from exc


def read_json(path: Path) -> tuple[Any, bytes]:
    raw = read_bytes(path)
    return decode_json(raw, path.name), raw


def require_hash(actual: str, expected: Any, label: str) -> None:
    if not isinstance(expected, str) or actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch")


def check_phase_freeze(
    root: Path,
    freeze: Any,
    phase: str,
    expected_count: int,
    input_sha256: str,
) -> tuple[dict[str, bytes], list[str]]:
    status = f"validation_50_v1_{phase}_audits_frozen_before_outcome"
    if not isinstance(freeze, dict) or freeze.get("status") != status or freeze.get("phase") != phase:
        raise ValueError(f"{phase} audit freeze has unexpected status or phase")
    if freeze.get("outcome_revealed") is not False or freeze.get("deal_count") != expected_count:
        raise ValueError(f"{phase} audit freeze must be outcome-blind with {expected_count} audits")
    require_hash(input_sha256, freeze.get("input_freeze_sha256"), f"{phase} input freeze")
    rows = freeze.get("files")
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise ValueError(f"{phase} audit freeze must list exactly {expected_count} files")

    audits: dict[str, bytes] = {}
    for row in rows:
        deal_id = row.get("deal_id") if isinstance(row, dict) else None
        if not check_audits.valid_deal_id(deal_id) or deal_id in audits:
            raise ValueError(f"{phase} audit freeze has invalid or duplicate deal ID")
        paths = {
            "audit_path": f"audits/{phase}/{deal_id}.json",
            "view_path": f"views/{deal_id}.jsonl",
            "quality_path": f"dataset/deals/{deal_id}/quality.json",
        }
        for path_key, relative in paths.items():
            if row.get(path_key) != relative:
                raise ValueError(f"{phase} freeze {deal_id} has unexpected {path_key}")
        for path_key, hash_key in (("audit_path", "audit_sha256"), ("view_path", "view_sha256"), ("quality_path", "quality_sha256")):
            raw = read_bytes(root / paths[path_key])
            require_hash(digest(raw), row.get(hash_key), f"{phase} {deal_id} {path_key}")
            if path_key == "audit_path":
                audits[deal_id] = raw
    ids = sorted(audits, key=int)
    if len(ids) != expected_count:
        raise ValueError(f"{phase} audit freeze has an unexpected deal set")
    selected = freeze.get("selected_deal_ids")
    if selected is not None and selected != ids:
        raise ValueError(f"{phase} selected deal IDs differ from frozen files")
    return audits, ids


def checked_phase(root: Path, phase: str, deal_ids: list[str] | None = None) -> None:
    try:
        result = check_audits.validate_phase(phase, root, deal_ids=deal_ids)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{phase} audit validator failed ({type(exc).__name__})") from exc
    if result.get("status") != "PASS":
        errors = result.get("errors", [])
        raise ValueError(f"{phase} audit validation failed: {'; '.join(errors[:5])}")


def preflight(root: Path) -> dict[str, Any]:
    """Verify every frozen input; do not parse cohort labels in this function."""
    input_freeze, input_raw = read_json(root / "input_freeze.json")
    if not isinstance(input_freeze, dict):
        raise ValueError("input_freeze.json must be an object")
    if (
        input_freeze.get("status") != "validation_50_v1_outcome_blind_views_frozen_before_semantic_audit"
        or input_freeze.get("outcome_blind_views") is not True
        or input_freeze.get("outcome_labels_separate_from_views") is not True
        or input_freeze.get("deal_count") != 50
        or input_freeze.get("baseline_overlap_count") != 0
    ):
        raise ValueError("input_freeze.json does not pin the expected outcome-blind 50-deal cohort")
    input_hash = digest(input_raw)

    freeze_names = {
        "primary": "primary_audit_freeze.json",
        "secondary": "secondary_audit_freeze.json",
        "final": "final_audit_freeze.json",
    }
    freezes: dict[str, dict[str, Any]] = {}
    freeze_raws: dict[str, bytes] = {}
    for phase, name in freeze_names.items():
        value, raw = read_json(root / name)
        freezes[phase], freeze_raws[phase] = value, raw

    sample, sample_raw = read_json(root / "reliability_sample.json")
    reliability_freeze, reliability_freeze_raw = read_json(root / "reliability_freeze.json")
    reliability, reliability_raw = read_json(root / "reliability.json")
    taxonomy_freeze, taxonomy_freeze_raw = read_json(root / "taxonomy_freeze.json")

    primary_audits, primary_ids = check_phase_freeze(root, freezes["primary"], "primary", 50, input_hash)
    if not isinstance(sample, dict) or sample.get("status") != "reliability_review_sample_selected" or sample.get("outcome_blind") is not True:
        raise ValueError("reliability_sample.json is not a frozen outcome-blind sample")
    selected_ids = sample.get("selected_deal_ids")
    if not isinstance(selected_ids, list) or len(selected_ids) != 15 or len(set(selected_ids)) != 15 or not set(selected_ids) <= set(primary_ids):
        raise ValueError("reliability sample must contain 15 unique primary audit IDs")
    selected_ids = sorted(selected_ids, key=int)
    sample_hashes = sample.get("source_hashes")
    if not isinstance(sample_hashes, dict):
        raise ValueError("reliability sample source hashes are missing")
    require_hash(digest(freeze_raws["primary"]), sample_hashes.get("primary_freeze_sha256"), "reliability sample primary freeze")
    require_hash(input_hash, sample_hashes.get("input_freeze_sha256"), "reliability sample input freeze")
    sample_audit_hashes = sample_hashes.get("primary_audit_sha256")
    if not isinstance(sample_audit_hashes, dict) or set(sample_audit_hashes) != set(primary_ids):
        raise ValueError("reliability sample primary audit hashes do not cover all 50 audits")
    for deal_id, raw in primary_audits.items():
        require_hash(digest(raw), sample_audit_hashes.get(deal_id), f"reliability sample primary audit {deal_id}")

    _, secondary_ids = check_phase_freeze(root, freezes["secondary"], "secondary", 15, input_hash)
    if secondary_ids != selected_ids:
        raise ValueError("secondary audit IDs differ from the frozen reliability sample")
    final_audits, final_ids = check_phase_freeze(root, freezes["final"], "final", 50, input_hash)
    if final_ids != primary_ids:
        raise ValueError("final audit IDs differ from the primary cohort")

    if not isinstance(reliability_freeze, dict) or (
        reliability_freeze.get("status") != "validation_50_v1_reliability_frozen_before_outcome"
        or reliability_freeze.get("outcome_revealed") is not False
    ):
        raise ValueError("reliability_freeze.json has unexpected status or outcome state")
    require_hash(digest(reliability_raw), reliability_freeze.get("reliability_sha256"), "reliability")
    require_hash(digest(sample_raw), reliability_freeze.get("reliability_sample_sha256"), "reliability sample")
    require_hash(digest(freeze_raws["primary"]), reliability_freeze.get("primary_audit_freeze_sha256"), "reliability primary freeze")
    require_hash(digest(freeze_raws["secondary"]), reliability_freeze.get("secondary_audit_freeze_sha256"), "reliability secondary freeze")
    if not isinstance(reliability, dict) or reliability.get("status") != "ACCEPTABLE" or reliability.get("deal_count") != 15:
        raise ValueError("reliability.json must be ACCEPTABLE for exactly 15 deals")
    comparisons = reliability.get("comparisons")
    comparison_ids = [row.get("deal_id") for row in comparisons if isinstance(row, dict)] if isinstance(comparisons, list) else []
    if len(comparison_ids) != 15 or len(set(comparison_ids)) != 15 or set(comparison_ids) != set(selected_ids):
        raise ValueError("reliability comparisons must cover exactly the frozen 15-deal sample")
    required_fields = {"primary_explanation", "controllability", "turning_points", "manager_process_opportunity", "strongest_customer_signals"}
    for row in comparisons:
        fields = row.get("fields")
        if not isinstance(fields, dict) or set(fields) != required_fields or not isinstance(row.get("reconciliation"), dict):
            raise ValueError("reliability comparison has an unexpected schema")
        if any(not isinstance(value, dict) or value.get("rating") not in RELIABILITY_RATINGS or not isinstance(value.get("notes"), str) for value in fields.values()):
            raise ValueError("reliability comparison fields need a valid rating and string notes")

    if not isinstance(taxonomy_freeze, dict) or (
        taxonomy_freeze.get("status") != "validation_50_v1_taxonomy_frozen_before_outcome"
        or taxonomy_freeze.get("outcome_revealed") is not False
    ):
        raise ValueError("taxonomy_freeze.json has unexpected status or outcome state")
    require_hash(digest(freeze_raws["final"]), taxonomy_freeze.get("final_audit_freeze_sha256"), "taxonomy final freeze")
    require_hash(input_hash, taxonomy_freeze.get("input_freeze_sha256"), "taxonomy input freeze")

    # Metadata integrity and quality sidecars are read only as bytes before outcomes are parsed.
    for name, hash_key in (("dataset/manifest.json", "dataset_manifest_sha256"),
                           ("dataset/summary.json", "summary_sha256"),
                           ("dataset/build_quality.json", "build_quality_sha256")):
        require_hash(digest(read_bytes(root / name)), input_freeze.get(hash_key), name)
    quality_rows = input_freeze.get("deals")
    quality_hashes: dict[str, str] = {}
    if not isinstance(quality_rows, list) or len(quality_rows) != 50:
        raise ValueError("input_freeze.json must list 50 quality sidecars")
    for row in quality_rows:
        deal_id = row.get("deal_id") if isinstance(row, dict) else None
        if not check_audits.valid_deal_id(deal_id) or deal_id in quality_hashes:
            raise ValueError("input_freeze.json has invalid or duplicate quality deal IDs")
        quality_hashes[deal_id] = row.get("quality_sha256")
    if set(quality_hashes) != set(primary_ids):
        raise ValueError("input_freeze quality IDs differ from frozen audit IDs")

    taxonomy_raw = read_bytes(root / "taxonomy.json")
    require_hash(digest(taxonomy_raw), taxonomy_freeze.get("taxonomy_sha256"), "taxonomy")
    cohort_raw = read_bytes(root / "cohort.json")
    cohort_hash = digest(cohort_raw)
    require_hash(cohort_hash, taxonomy_freeze.get("cohort_sha256"), "cohort")
    require_hash(cohort_hash, sample_hashes.get("cohort_sha256"), "reliability sample cohort")

    checked_phase(root, "final")

    final_audit_docs = {deal_id: decode_json(raw, f"final audit {deal_id}") for deal_id, raw in final_audits.items()}
    quality_sidecars: dict[str, dict[str, Any]] = {}
    for deal_id, expected_hash in quality_hashes.items():
        path = root / "dataset" / "deals" / deal_id / "quality.json"
        raw = read_bytes(path)
        require_hash(digest(raw), expected_hash, f"quality sidecar {deal_id}")
        value = decode_json(raw, f"quality sidecar {deal_id}")
        if not isinstance(value, dict) or value.get("deal_id") != deal_id:
            raise ValueError(f"quality sidecar {deal_id} has unexpected deal ID")
        quality_sidecars[deal_id] = value
    build_quality_raw = read_bytes(root / "dataset" / "build_quality.json")
    build_quality = decode_json(build_quality_raw, "build_quality.json")
    if not isinstance(build_quality, dict) or build_quality.get("deal_count") != 50 or not isinstance(build_quality.get("deals"), dict) or set(build_quality["deals"]) != set(primary_ids):
        raise ValueError("build_quality.json must contain quality counts for the frozen 50 deals")

    hashes = {
        "input_freeze_sha256": input_hash,
        "cohort_sha256": cohort_hash,
        "primary_audit_freeze_sha256": digest(freeze_raws["primary"]),
        "secondary_audit_freeze_sha256": digest(freeze_raws["secondary"]),
        "final_audit_freeze_sha256": digest(freeze_raws["final"]),
        "reliability_freeze_sha256": digest(reliability_freeze_raw),
        "reliability_sha256": digest(reliability_raw),
        "reliability_sample_sha256": digest(sample_raw),
        "taxonomy_freeze_sha256": digest(taxonomy_freeze_raw),
        "taxonomy_sha256": digest(taxonomy_raw),
        "build_quality_sha256": digest(build_quality_raw),
        "summary_sha256": digest(read_bytes(root / "dataset" / "summary.json")),
        "quality_sidecars_sha256": quality_hashes,
        "final_audit_sha256": {deal_id: digest(raw) for deal_id, raw in final_audits.items()},
    }
    return {
        "cohort_raw": cohort_raw,
        "taxonomy_raw": taxonomy_raw,
        "audit_docs": final_audit_docs,
        "quality_sidecars": quality_sidecars,
        "build_quality": build_quality,
        "hashes": hashes,
        "deal_ids": primary_ids,
    }


def cohort_data(raw: bytes, expected_ids: list[str]) -> dict[str, dict[str, Any]]:
    document = decode_json(raw, "cohort.json")
    rows = document.get("deals") if isinstance(document, dict) else None
    if not isinstance(rows, list) or len(rows) != 50:
        raise ValueError("cohort.json must contain exactly 50 deals")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        deal_id = str(row.get("deal_id") or "") if isinstance(row, dict) else ""
        if not check_audits.valid_deal_id(deal_id) or deal_id in result:
            raise ValueError("cohort has invalid or duplicate deal IDs")
        outcome = row.get("outcome")
        if outcome not in OUTCOMES:
            raise ValueError(f"cohort deal {deal_id} has an invalid outcome")
        result[deal_id] = {
            "outcome": outcome,
            "manager_id": row.get("manager_id"),
            "manager_name": row.get("manager_name"),
            "pipeline_id": row.get("pipeline_id"),
        }
    if len(expected_ids) != 50 or set(result) != set(expected_ids) or Counter(row["outcome"] for row in result.values()) != {"WON": 25, "LOST": 25}:
        raise ValueError("cohort must be the exact 50-deal set with 25 WON and 25 LOST")
    return result


def validate_taxonomy(taxonomy: Any, deal_ids: list[str], audits: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(taxonomy, dict) or not isinstance(taxonomy.get("patterns"), list):
        raise ValueError("taxonomy.json must contain a patterns array")
    patterns, seen_pattern_ids = [], set()
    all_ids = set(deal_ids)
    for pattern in taxonomy["patterns"]:
        if not isinstance(pattern, dict):
            raise ValueError("taxonomy pattern must be an object")
        required = {"pattern_id", "name", "definition", "controllability", "memberships", "data_quality_caveats"}
        if set(pattern) != required:
            raise ValueError("taxonomy pattern fields differ from the frozen schema")
        pattern_id = pattern["pattern_id"]
        if not isinstance(pattern_id, str) or not pattern_id.strip() or pattern_id in seen_pattern_ids:
            raise ValueError("taxonomy has invalid or duplicate pattern_id")
        seen_pattern_ids.add(pattern_id)
        if any(not isinstance(pattern[key], str) for key in ("name", "definition", "controllability")):
            raise ValueError(f"taxonomy pattern {pattern_id} has invalid descriptive fields")
        caveats = pattern["data_quality_caveats"]
        memberships = pattern["memberships"]
        if not isinstance(caveats, list) or any(not isinstance(item, str) for item in caveats):
            raise ValueError(f"taxonomy pattern {pattern_id} has invalid data quality caveats")
        if not isinstance(memberships, list) or len(memberships) != len(all_ids):
            raise ValueError(f"taxonomy pattern {pattern_id} must contain exactly 50 memberships")
        by_id: dict[str, dict[str, Any]] = {}
        for membership in memberships:
            if not isinstance(membership, dict) or set(membership) != {"deal_id", "status", "evidence_indices", "note"}:
                raise ValueError(f"taxonomy pattern {pattern_id} has an invalid membership shape")
            deal_id = membership["deal_id"]
            if not check_audits.valid_deal_id(deal_id) or deal_id in by_id:
                raise ValueError(f"taxonomy pattern {pattern_id} has invalid or duplicate membership deal ID")
            if membership["status"] not in MEMBERSHIP_STATUSES:
                raise ValueError(f"taxonomy pattern {pattern_id} has invalid membership status")
            note, indices = membership["note"], membership["evidence_indices"]
            if not isinstance(note, str) or not isinstance(indices, list):
                raise ValueError(f"taxonomy pattern {pattern_id} has invalid note or evidence_indices")
            if membership["status"] == "PRESENT" and not indices:
                raise ValueError(f"taxonomy pattern {pattern_id} PRESENT membership needs evidence")
            evidence = audits.get(deal_id, {}).get("evidence")
            if not isinstance(evidence, list):
                raise ValueError(f"final audit {deal_id} has no evidence array")
            for index in indices:
                if type(index) is not int or not 0 <= index < len(evidence):
                    raise ValueError(f"taxonomy pattern {pattern_id} has invalid evidence index for {deal_id}")
            by_id[deal_id] = membership
        if set(by_id) != all_ids:
            raise ValueError(f"taxonomy pattern {pattern_id} membership IDs differ from frozen cohort")
        patterns.append({**pattern, "memberships_by_id": by_id})
    return patterns


def norm_manager_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().replace("ё", "е").split())


def manager_groups(cohort: dict[str, dict[str, Any]], manager_id: str | None) -> dict[str, list[str]]:
    primary_ids = []
    for deal_id, row in cohort.items():
        if manager_id is not None:
            match = str(row["manager_id"]) == manager_id
        else:
            match = norm_manager_name(row["manager_name"]) == "пахомов александр"
        if match:
            primary_ids.append(deal_id)
    if len(primary_ids) != 27:
        raise ValueError(f"Pakhomov metadata group must contain 27 deals, found {len(primary_ids)}")
    return {
        "pakhomov": sorted(primary_ids, key=int),
        "others": sorted(set(cohort) - set(primary_ids), key=int),
    }


def pipeline_counts(deal_ids: list[str], cohort: dict[str, dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(cohort[deal_id]["pipeline_id"]) for deal_id in deal_ids).items()))


def membership_record(
    deal_id: str,
    membership: dict[str, Any],
    cohort: dict[str, dict[str, Any]],
    audits: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = cohort[deal_id]
    return {
        "deal_id": deal_id,
        "status": membership["status"],
        "manager_id": row["manager_id"],
        "manager_name": row["manager_name"],
        "pipeline_id": row["pipeline_id"],
        "note": membership["note"],
        "evidence_indices": membership["evidence_indices"],
        "evidence": [
            {key: audits[deal_id]["evidence"][index].get(key) for key in ("timestamp", "event_type", "event_id", "source_line", "paraphrase")}
            for index in membership["evidence_indices"]
        ],
    }


def status_breakdown(
    deal_ids: list[str],
    by_id: dict[str, dict[str, Any]],
    cohort: dict[str, dict[str, Any]],
    audits: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    records = {status: [] for status in MEMBERSHIP_STATUSES}
    for deal_id in deal_ids:
        records[by_id[deal_id]["status"]].append(membership_record(deal_id, by_id[deal_id], cohort, audits))
    return {
        "denominator": len(deal_ids),
        "counts": {status: len(records[status]) for status in MEMBERSHIP_STATUSES},
        "deal_ids": {status: [row["deal_id"] for row in records[status]] for status in MEMBERSHIP_STATUSES},
        "manager_counts": {
            status: dict(sorted(Counter(str(row["manager_name"]) for row in records[status]).items()))
            for status in MEMBERSHIP_STATUSES
        },
        "pipeline_counts": {
            status: dict(sorted(Counter(str(row["pipeline_id"]) for row in records[status]).items()))
            for status in MEMBERSHIP_STATUSES
        },
        "memberships": records,
    }


def status_counts(deal_ids: list[str], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(by_id[deal_id]["status"] for deal_id in deal_ids)
    return {"denominator": len(deal_ids), "counts": {status: counts[status] for status in MEMBERSHIP_STATUSES}}


def aggregate_data(
    cohort: dict[str, dict[str, Any]],
    patterns: list[dict[str, Any]],
    audits: dict[str, dict[str, Any]],
    quality: dict[str, dict[str, Any]],
    build_quality: dict[str, Any],
    hashes: dict[str, Any],
    manager_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if set(cohort) != set(audits):
        raise ValueError("cohort IDs differ from the frozen final audit set")
    groups = manager_groups(cohort, manager_id)
    sample = {
        outcome: {
            "count": sum(row["outcome"] == outcome for row in cohort.values()),
            "deal_ids": sorted((deal_id for deal_id, row in cohort.items() if row["outcome"] == outcome), key=int),
            "pipeline_counts": pipeline_counts([deal_id for deal_id, row in cohort.items() if row["outcome"] == outcome], cohort),
        }
        for outcome in OUTCOMES
    }
    won_patterns = []
    robust_patterns = []
    for pattern in patterns:
        by_id = pattern["memberships_by_id"]
        by_outcome = {
            outcome: status_breakdown(
                sorted((deal_id for deal_id, row in cohort.items() if row["outcome"] == outcome), key=int), by_id, cohort, audits,
            )
            for outcome in OUTCOMES
        }
        won_present = by_outcome["WON"]["memberships"]["PRESENT"]
        lost_present_count = by_outcome["LOST"]["counts"]["PRESENT"]
        won_patterns.append({
            **{key: pattern[key] for key in ("pattern_id", "name", "definition", "controllability", "data_quality_caveats")},
            "by_outcome": by_outcome,
            "counterexample_candidates": won_present if lost_present_count else [],
        })
        robust_patterns.append({
            "pattern_id": pattern["pattern_id"],
            "name": pattern["name"],
            "groups": {
                group_name: {
                    "deal_count": len(ids),
                    "outcome_denominators": {
                        outcome: sum(cohort[deal_id]["outcome"] == outcome for deal_id in ids)
                        for outcome in OUTCOMES
                    },
                    "by_outcome": {
                        outcome: status_breakdown(
                            [deal_id for deal_id in ids if cohort[deal_id]["outcome"] == outcome], by_id, cohort, audits,
                        )
                        for outcome in OUTCOMES
                    },
                }
                for group_name, ids in groups.items()
            },
        })
    quality_payload = {
        "build_quality_global": build_quality.get("global", {}),
        "by_deal": {
            deal_id: {
                "quality_sha256": hashes["quality_sidecars_sha256"][deal_id],
                "sidecar": quality[deal_id],
                "counts": build_quality["deals"][deal_id],
            }
            for deal_id in sorted(quality, key=int)
        },
    }
    limitations = [
        "This is descriptive aggregation of a 50-deal development cohort, not evidence of causal or predictive lift.",
        "Membership status and evidence were fixed in the blinded taxonomy before outcome labels were joined.",
        "Quality limitations come from the frozen outcome-blind sidecars and do not repair missing source data.",
    ]
    return (
        {
            "version": "validation_50_v1",
            "method": "Outcomes were read only after all audit, reliability, taxonomy, input, cohort, and quality hashes were verified.",
            "source_hashes": hashes,
            "sample": sample,
            "patterns": won_patterns,
            "quality": quality_payload,
            "limits": limitations,
        },
        {
            "version": "validation_50_v1",
            "method": "Manager comparison is descriptive and uses frozen manager metadata; it makes no causal or predictive claim.",
            "source_hashes": hashes,
            "manager_group_rule": "manager_id exact match when --manager-id is supplied; otherwise exact normalized name 'Пахомов Александр'.",
            "groups": {
                group_name: {
                    "deal_count": len(ids),
                    "outcome_denominators": {
                        outcome: sum(cohort[deal_id]["outcome"] == outcome for deal_id in ids)
                        for outcome in OUTCOMES
                    },
                    "patterns": [
                        {
                            "pattern_id": pattern["pattern_id"],
                            "name": pattern["name"],
                            "by_outcome": {
                                outcome: status_counts(
                                    [deal_id for deal_id in ids if cohort[deal_id]["outcome"] == outcome], pattern["memberships_by_id"],
                                )
                                for outcome in OUTCOMES
                            },
                        }
                        for pattern in patterns
                    ],
                }
                for group_name, ids in groups.items()
            },
            "quality": quality_payload,
            "limits": limitations,
        },
    )


def write_pair(root: Path, won_vs_lost: dict[str, Any], manager_robustness: dict[str, Any]) -> None:
    targets = [root / "won_vs_lost.json", root / "manager_robustness.json"]
    if any(path.exists() for path in targets):
        raise ValueError("output exists; refusing to overwrite either aggregation file")
    created: list[Path] = []
    streams = []
    try:
        for path in targets:
            streams.append(path.open("x", encoding="utf-8"))
            created.append(path)
        for stream, value in zip(streams, (won_vs_lost, manager_robustness)):
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except Exception:
        for stream in streams:
            stream.close()
        for path in created:
            try:
                path.unlink()
            except OSError:
                pass
        raise
    for stream in streams:
        stream.close()


def join_frozen(verified: dict[str, Any], manager_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    taxonomy = decode_json(verified["taxonomy_raw"], "taxonomy.json")
    patterns = validate_taxonomy(taxonomy, verified["deal_ids"], verified["audit_docs"])
    cohort = cohort_data(verified["cohort_raw"], verified["deal_ids"])
    won_vs_lost, manager_robustness = aggregate_data(
        cohort, patterns, verified["audit_docs"], verified["quality_sidecars"],
        verified["build_quality"], verified["hashes"], manager_id,
    )
    return won_vs_lost, manager_robustness


def run(root: Path = HERE, manager_id: str | None = None) -> dict[str, Any]:
    # Run the complete gate and validate blinded memberships before parsing outcomes.
    verified = preflight(root)
    won_vs_lost, manager_robustness = join_frozen(verified, manager_id)
    write_pair(root, won_vs_lost, manager_robustness)
    return {"status": "PASS", "deal_count": 50, "won": 25, "lost": 25, "outputs": [path.name for path in (root / "won_vs_lost.json", root / "manager_robustness.json")]}


def synthetic_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    ids = [str(1001 + 2 * index) for index in range(50)]
    cohort = {
        deal_id: {
            "outcome": "WON" if index < 25 else "LOST",
            "manager_id": "manager-p" if index < 27 else "manager-other",
            "manager_name": "Пахомов Александр" if index < 27 else f"Менеджер {deal_id}",
            "pipeline_id": f"pipeline-{index % 3}",
        }
        for index, deal_id in enumerate(ids)
    }
    audits = {deal_id: {"evidence": [{"timestamp": "2026-01-01T10:00:00+03:00", "event_type": "comment", "event_id": f"event-{deal_id}", "source_line": 1, "paraphrase": "synthetic"}]} for deal_id in ids}
    memberships = [
        {"deal_id": deal_id, "status": "PRESENT" if index < 10 else "NOT_SHOWN", "evidence_indices": [0] if index < 10 else [], "note": "synthetic"}
        for index, deal_id in enumerate(ids)
    ]
    taxonomy = [{"pattern_id": "T1", "name": "Synthetic", "definition": "Synthetic pattern", "controllability": "unknown", "data_quality_caveats": [], "memberships": memberships}]
    quality = {deal_id: {"deal_id": deal_id, "limitations": []} for deal_id in ids}
    build_quality = {"deal_count": 50, "global": {"calls": 0}, "deals": {deal_id: {"calls": 0} for deal_id in ids}}
    return cohort, audits, taxonomy, quality, build_quality


def self_check() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        # These keys match the outcome-blind input-freeze contract; later missing gates stop label parsing.
        (root / "input_freeze.json").write_text(json.dumps({
            "status": "validation_50_v1_outcome_blind_views_frozen_before_semantic_audit",
            "outcome_blind_views": True,
            "outcome_labels_separate_from_views": True,
            "deal_count": 50,
            "baseline_overlap_count": 0,
        }), encoding="utf-8")
        (root / "cohort.json").write_text("not-json", encoding="utf-8")
        try:
            preflight(root)
        except ValueError as exc:
            assert "primary_audit_freeze.json" in str(exc)
        else:
            raise AssertionError("preflight must reject missing freezes before cohort parsing")

    cohort, audits, taxonomy, quality, build_quality = synthetic_inputs()
    ids = sorted(cohort, key=int)
    cohort_raw = json.dumps({"deals": [{"deal_id": deal_id, **row} for deal_id, row in cohort.items()]}).encode("utf-8")
    verified = {
        "taxonomy_raw": json.dumps({"patterns": taxonomy}).encode("utf-8"),
        "cohort_raw": cohort_raw,
        "deal_ids": ids,
        "audit_docs": audits,
        "quality_sidecars": quality,
        "build_quality": build_quality,
        "hashes": {"quality_sidecars_sha256": {deal_id: "synthetic" for deal_id in cohort}},
    }
    # Taxonomy membership errors must surface before malformed outcomes are parsed.
    invalid = {**verified, "taxonomy_raw": json.dumps({"patterns": [{**taxonomy[0], "memberships": taxonomy[0]["memberships"][:-1]}]}).encode("utf-8"), "cohort_raw": b"not-json"}
    try:
        join_frozen(invalid, "manager-p")
    except ValueError as exc:
        assert "exactly 50" in str(exc)
    else:
        raise AssertionError("blind taxonomy validation must precede outcome parsing")

    won, robust = join_frozen(verified, "manager-p")
    assert won["sample"]["WON"]["count"] == won["sample"]["LOST"]["count"] == 25
    assert robust["groups"]["pakhomov"]["deal_count"] == 27
    assert robust["groups"]["others"]["deal_count"] == 23
    assert sum(robust["groups"]["pakhomov"]["outcome_denominators"].values()) == 27
    assert sum(robust["groups"]["others"]["outcome_denominators"].values()) == 23
    assert set(cohort) == set(ids) and "1" not in cohort

    missing = {"patterns": [{**taxonomy[0], "memberships": taxonomy[0]["memberships"][:-1]}]}
    try:
        validate_taxonomy(missing, ids, audits)
    except ValueError as exc:
        assert "exactly 50" in str(exc)
    else:
        raise AssertionError("incomplete taxonomy membership must fail")
    bad_index = {"patterns": [{**taxonomy[0], "memberships": [{**taxonomy[0]["memberships"][0], "evidence_indices": [1]}, *taxonomy[0]["memberships"][1:]]}]}
    try:
        validate_taxonomy(bad_index, ids, audits)
    except ValueError as exc:
        assert "evidence index" in str(exc)
    else:
        raise AssertionError("unknown evidence index must fail")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager-id", help="explicit manager_id for the Pakhomov comparison group")
    parser.add_argument("--self-check", action="store_true", help="run the synthetic offline self-check")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        print(json.dumps({"status": "PASS", "self_check": True}))
        return 0
    try:
        print(json.dumps(run(HERE, args.manager_id), ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
