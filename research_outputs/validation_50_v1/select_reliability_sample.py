"""Outcome-blind, reproducible selection of 15 audits for reliability review."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import check_audits


HERE = Path(__file__).resolve().parent
FREEZE = HERE / "primary_audit_freeze.json"
COHORT = HERE / "cohort.json"
OUTPUT = HERE / "reliability_sample.json"
SEED = 20261002
COHORT_SHA256 = "3d88386d431a0a56552e22cc3fd1fff30a96a7827052ee089ac9796aa8182154"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def select(audits: dict[str, dict[str, Any]], metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ids = sorted(audits, key=int)
    if len(ids) != 50 or set(ids) != set(metadata):
        raise ValueError("expected matching 50 audit and cohort IDs")
    rng = random.Random(SEED)
    random_ids = sorted(rng.sample(ids, 6), key=int)
    chosen = list(random_ids)
    records = {deal_id: {"deal_id": deal_id, "reason": "seeded_random", "proxies": {"seed": SEED}}
               for deal_id in random_ids}
    remaining = [deal_id for deal_id in ids if deal_id not in chosen]

    def confidence_rank(deal_id: str) -> tuple[int, int, int]:
        audit = audits[deal_id]
        confidence = audit["primary_trajectory_explanation"]["confidence"]
        uncertainty_count = len(audit["uncertainties"])
        return ({"low": 0, "medium": 1, "high": 2}[confidence], -uncertainty_count, int(deal_id))

    confidence_batch = sorted(remaining, key=confidence_rank)[:3]
    for deal_id in confidence_batch:
        chosen.append(deal_id)
        records[deal_id] = {"deal_id": deal_id, "reason": "low_or_medium_confidence_then_uncertainty",
                            "proxies": {"confidence": audits[deal_id]["primary_trajectory_explanation"]["confidence"],
                                        "uncertainty_count": len(audits[deal_id]["uncertainties"])}}
    remaining = [deal_id for deal_id in ids if deal_id not in chosen]

    def influence_rank(deal_id: str) -> tuple[int, int, int, int]:
        audit = audits[deal_id]
        return (-int(audit["manager_influence"]["could_materially_improve"] is True),
                -len(audit["manager_behavior"]["weak_actions"]),
                -len(audit["manager_influence"]["what_could_be_done"]), int(deal_id))

    influence_batch = sorted(remaining, key=influence_rank)[:3]
    for deal_id in influence_batch:
        audit = audits[deal_id]
        chosen.append(deal_id)
        records[deal_id] = {"deal_id": deal_id, "reason": "influence_true_priority_then_weak_actions_and_opportunities",
                            "proxies": {"could_materially_improve": audit["manager_influence"]["could_materially_improve"],
                                        "weak_actions_count": len(audit["manager_behavior"]["weak_actions"]),
                                        "opportunities_count": len(audit["manager_influence"]["what_could_be_done"])}}
    remaining = [deal_id for deal_id in ids if deal_id not in chosen]

    covered_pipelines = {metadata[i].get("pipeline_id") for i in chosen}
    covered_managers = {metadata[i].get("manager_id") or metadata[i].get("manager_name") for i in chosen}
    coverage_batch: list[str] = []
    for _ in range(3):
        deal_id = min(remaining, key=lambda i: (
            -int(metadata[i].get("pipeline_id") not in covered_pipelines),
            -int((metadata[i].get("manager_id") or metadata[i].get("manager_name")) not in covered_managers),
            int(i),
        ))
        remaining.remove(deal_id)
        coverage_batch.append(deal_id)
        chosen.append(deal_id)
        pipeline = metadata[deal_id].get("pipeline_id")
        manager = metadata[deal_id].get("manager_id") or metadata[deal_id].get("manager_name")
        covered_pipelines.add(pipeline)
        covered_managers.add(manager)
        records[deal_id] = {"deal_id": deal_id, "reason": "maximize_missing_pipeline_and_manager_coverage",
                            "proxies": {"pipeline_id": pipeline, "manager_id": metadata[deal_id].get("manager_id"),
                                        "manager_name": metadata[deal_id].get("manager_name")}}

    distribution: dict[str, Any] = {"pipelines": {}, "managers": {}}
    for deal_id in chosen:
        row = metadata[deal_id]
        pipeline = str(row.get("pipeline_id"))
        manager = str(row.get("manager_id") or row.get("manager_name"))
        distribution["pipelines"][pipeline] = distribution["pipelines"].get(pipeline, 0) + 1
        distribution["managers"][manager] = distribution["managers"].get(manager, 0) + 1
    return {
        "status": "reliability_review_sample_selected",
        "outcome_blind": True,
        "method": "Select challenge cases without accessing outcome values: seeded random six; three ranked by low/medium confidence then uncertainty count; three prioritizing manager influence true then weak-action and opportunity counts (null/false remain eligible); three prioritize missing pipelines then missing managers. These proxies select audit-review challenges, not causal or semantic classifiers.",
        "seed": SEED,
        "selected_deal_ids": chosen,
        "selections": [records[i] for i in chosen],
        "manager_pipeline_distribution": distribution,
    }


def frozen_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    if not FREEZE.is_file():
        raise ValueError("primary_audit_freeze.json is required")
    freeze_raw = FREEZE.read_bytes()
    freeze = json.loads(freeze_raw.decode("utf-8-sig"))
    if (freeze.get("status") != "validation_50_v1_primary_audits_frozen_before_outcome"
            or freeze.get("phase") != "primary" or freeze.get("outcome_revealed") is not False
            or freeze.get("deal_count") != 50):
        raise ValueError("primary freeze must contain 50 audits and assert outcome_revealed=false")
    validation = check_audits.validate_phase("primary", HERE)
    if validation.get("status") != "PASS" or validation.get("deal_count") != 50:
        raise ValueError("primary audit validation failed")
    input_hash = sha256((HERE / "input_freeze.json").read_bytes())
    if freeze.get("input_freeze_sha256") != input_hash:
        raise ValueError("primary freeze input_freeze hash mismatch")
    frozen_files = freeze.get("files")
    if not isinstance(frozen_files, list) or len(frozen_files) != 50:
        raise ValueError("primary freeze must list 50 audit hashes")
    frozen_hashes: dict[str, str] = {}
    for row in frozen_files:
        deal_id = row.get("deal_id") if isinstance(row, dict) else None
        if not isinstance(deal_id, str) or deal_id in frozen_hashes:
            raise ValueError("invalid or duplicate deal in primary freeze")
        audit_path = HERE / "audits" / "primary" / f"{deal_id}.json"
        if row.get("audit_path") not in (f"audits/primary/{deal_id}.json", str(audit_path)):
            raise ValueError(f"unexpected audit path for {deal_id}")
        actual = sha256(audit_path.read_bytes())
        if row.get("audit_sha256") != actual:
            raise ValueError(f"primary audit hash mismatch for {deal_id}")
        frozen_hashes[deal_id] = actual
    cohort_raw = COHORT.read_bytes()
    if sha256(cohort_raw) != COHORT_SHA256:
        raise ValueError("cohort metadata hash mismatch")
    cohort = json.loads(cohort_raw.decode("utf-8-sig"))
    rows = cohort.get("deals", cohort) if isinstance(cohort, dict) else cohort
    metadata = {}
    for row in rows:
        # Deliberately project only allowlisted outcome-blind metadata fields.
        deal_id = row.get("deal_id")
        metadata[deal_id] = {key: row.get(key) for key in ("manager_id", "manager_name", "pipeline_id")}
    if set(metadata) != set(frozen_hashes):
        raise ValueError("cohort IDs differ from primary freeze")
    audits = {deal_id: json.loads((HERE / "audits" / "primary" / f"{deal_id}.json").read_text(encoding="utf-8-sig"))
              for deal_id in frozen_hashes}
    return audits, metadata, frozen_hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        synthetic = {str(i): {"primary_trajectory_explanation": {"confidence": ("low", "medium", "high")[i % 3]},
                              "uncertainties": ["u"] * (i % 4), "manager_behavior": {"weak_actions": ["w"] * (i % 5)},
                              "manager_influence": {"could_materially_improve": None if i % 3 else False, "what_could_be_done": ["o"] * (i % 3)}}
                     for i in range(1, 51)}
        meta = {str(i): {"manager_id": str(i % 8), "manager_name": f"m{i % 8}", "pipeline_id": str(i % 4)} for i in range(1, 51)}
        first, second = select(synthetic, meta), select(synthetic, meta)
        assert len(first["selected_deal_ids"]) == len(set(first["selected_deal_ids"])) == 15
        assert first["selected_deal_ids"] == second["selected_deal_ids"]
        assert len(first["manager_pipeline_distribution"]["pipelines"]) > 1
        print(json.dumps({"status": "PASS", "self_check": True}))
        return 0
    if OUTPUT.exists():
        parser.error("reliability_sample.json already exists; refusing overwrite")
    try:
        audits, metadata, audit_hashes = frozen_inputs()
        result = select(audits, metadata)
        result.update({"source_hashes": {"primary_freeze_sha256": sha256(FREEZE.read_bytes()),
                                         "input_freeze_sha256": sha256((HERE / "input_freeze.json").read_bytes()),
                                         "cohort_sha256": COHORT_SHA256, "primary_audit_sha256": audit_hashes}})
        with OUTPUT.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"status": "PASS", "selected": 15, "output": str(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
