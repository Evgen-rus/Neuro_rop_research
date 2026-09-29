"""Attach outcomes only after the final deal audits have been frozen."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evidence(audit: dict) -> list[dict]:
    refs = []
    for index in audit["primary_trajectory_explanation"]["evidence_indices"]:
        item = audit["evidence"][index]
        refs.append({key: item[key] for key in ("timestamp", "event_type", "event_id", "source_line", "paraphrase")})
    return refs


def main() -> None:
    freeze = read(ROOT / "final_audit_freeze.json")
    assert freeze["status"] == "final_deal_audits_frozen_before_outcome"
    assert freeze["outcome_revealed"] is False
    assert freeze["deal_count"] == 23
    for item in freeze["files"]:
        path = ROOT / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path

    manifest_path = REPO / "dataset" / "manifest.json"
    manifest = read(manifest_path)
    metadata = {str(deal["deal_id"]): deal for deal in manifest["deals"]}
    labels = {deal_id: deal["outcome"] for deal_id, deal in metadata.items()}
    assert Counter(labels.values()) == {"WON": 12, "LOST": 11}
    assert len(labels) == 23
    taxonomy = read(ROOT / "taxonomy.json")
    views = {item["deal_id"]: item for item in read(ROOT / "audit_manifest.json")["deals"]}
    quality = {str(item["deal_id"]): item for item in read(REPO / "dataset" / "summary.json")["deals"]}
    audits = {deal_id: read(ROOT / "audits" / "final" / f"{deal_id}.json") for deal_id in labels}
    assert all(audits[deal_id]["deal_id"] == deal_id for deal_id in labels)

    patterns = []
    for pattern in taxonomy["patterns"]:
        lost = pattern["lost_deals"]
        won = pattern["won_counterexamples"]
        assert len(lost) == len(set(lost)) and len(won) == len(set(won))
        assert all(labels[deal_id] == "LOST" for deal_id in lost)
        assert all(labels[deal_id] == "WON" for deal_id in won)
        patterns.append({
            "id": pattern["id"], "name": pattern["name"],
            "lost_count": len(lost), "lost_denominator": 11,
            "won_counterexample_count": len(won), "won_denominator": 12,
            "lost_deals": lost, "won_counterexamples": won,
            "membership_is_selective": True,
        })

    by_outcome = {}
    for label in ("WON", "LOST"):
        group = [deal_id for deal_id in labels if labels[deal_id] == label]
        durations = [float(metadata[deal_id]["life_days"]) for deal_id in group]
        amounts = [float(metadata[deal_id]["amount"]) for deal_id in group]
        tokens = [views[deal_id]["approx_tokens"]["original"] for deal_id in group]
        view_tokens = [views[deal_id]["approx_tokens"]["view"] for deal_id in group]
        by_outcome[label] = {
            "count": len(group), "deal_ids": group,
            "median_life_days": statistics.median(durations),
            "median_amount_rub": statistics.median(amounts),
            "median_original_approx_tokens": statistics.median(tokens),
            "median_view_approx_tokens": statistics.median(view_tokens),
            "pipeline_counts": dict(Counter(metadata[deal_id]["pipeline_id"] for deal_id in group)),
            "calls_ge36_without_transcript": sum(quality[deal_id]["calls_ge36_without_transcript"] for deal_id in group),
        }

    detail = {}
    for deal_id, audit in audits.items():
        item = {
            "outcome": labels[deal_id],
            "trajectory_category": audit["primary_trajectory_explanation"]["category"],
            "trajectory_explanation": audit["primary_trajectory_explanation"]["explanation"],
            "controllability": audit["primary_trajectory_explanation"]["controllability"],
            "confidence": audit["primary_trajectory_explanation"]["confidence"],
            "primary_evidence": evidence(audit),
            "manager_strong_actions": audit["manager_behavior"]["strong_actions"],
            "manager_weak_actions": audit["manager_behavior"]["weak_actions"],
            "customer_positive_signals": audit["customer_behavior"]["positive_signals"],
            "customer_negative_signals": audit["customer_behavior"]["negative_signals"],
            "uncertainties": audit["uncertainties"],
        }
        if labels[deal_id] == "LOST":
            item["observed_preclosure_driver"] = taxonomy["lost_preclosure_drivers"][deal_id]
        detail[deal_id] = item

    result = {
        "version": "1.0",
        "method": "Outcome labels joined from dataset/manifest.json only after final_audit_freeze.json was verified; final audit files were not edited after label access.",
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "final_audit_freeze_sha256": hashlib.sha256((ROOT / "final_audit_freeze.json").read_bytes()).hexdigest(),
        "sample": by_outcome,
        "patterns": patterns,
        "deals": detail,
        "limits": [
            "23 deals from one manager are a development dataset, not a causal or predictive test.",
            "Pattern memberships were selected from observed frozen audits and are not exhaustive classifiers over every deal.",
            "Customer-reported budget, security, and project pauses are not independently verified objective facts.",
            "Original/view token counts are UTF-8 byte/4 proxies, not model tokenizer counts.",
            "Same-day outcome leakage and lifecycle cutoff exclusions remain possible as described in input_contract.md.",
        ],
    }
    path = ROOT / "won_vs_lost.json"
    with path.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print("Wrote outcome aggregation for 12 WON and 11 LOST")


if __name__ == "__main__":
    main()
