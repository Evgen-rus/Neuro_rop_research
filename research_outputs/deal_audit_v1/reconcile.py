"""Freeze evidence-grounded deal audits before outcome labels are opened."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = json.loads((ROOT / "paired_audit_freeze_v2.json").read_text(encoding="utf-8-sig"))
RELIABILITY = json.loads((ROOT / "reliability.json").read_text(encoding="utf-8-sig"))
FINAL = ROOT / "audits" / "final"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check_frozen_inputs() -> None:
    for item in FREEZE["files"]:
        path = ROOT / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path


def check_evidence(deal_id: str, audit: dict) -> None:
    view = {
        event["source_line"]: event
        for event in map(json.loads, (ROOT / "views" / f"{deal_id}.jsonl").read_text(encoding="utf-8-sig").splitlines())
    }
    assert audit["deal_id"] == deal_id
    for evidence in audit["evidence"]:
        event = view[evidence["source_line"]]
        assert datetime.fromisoformat(event["timestamp"]) == datetime.fromisoformat(evidence["timestamp"]), (
            deal_id, evidence["source_line"], event["timestamp"], evidence["timestamp"]
        )
        assert event["event_type"] == evidence["event_type"], (deal_id, evidence["source_line"])
    for point in [audit["primary_trajectory_explanation"], *audit["turning_points"]]:
        assert all(0 <= index < len(audit["evidence"]) for index in point["evidence_indices"])


def main() -> None:
    assert FREEZE["status"] == "canonical_paired_audits_frozen_before_outcome"
    assert FREEZE["outcome_revealed"] is False
    assert RELIABILITY["outcome_accessed"] is False
    assert len(RELIABILITY["deals"]) == 23
    check_frozen_inputs()
    assert not list(FINAL.glob("*.json")), "Final audits already exist"
    outputs: dict[str, dict] = {}
    decisions = []

    for comparison in RELIABILITY["deals"]:
        deal_id = comparison["deal_id"]
        a = read_json(ROOT / "audits" / "run_A" / f"{deal_id}.json")
        b_path = ROOT / ("audits/run_B_replacement/19007.json" if deal_id == "19007" else f"audits/run_B/{deal_id}.json")
        b = read_json(b_path)
        final = copy.deepcopy(a)
        amendments = []

        if deal_id == "18635":
            final["evidence"][14]["paraphrase"] = (
                "Customer says contract documents arrived but were not yet reviewed; seller says the invoice was sent, "
                "and customer will check it. Payment is not confirmed."
            )
            amendments.append("Corrected the July 22 document/invoice paraphrase against source line 103.")
        elif deal_id == "6885":
            final["evidence"][13]["paraphrase"] = (
                "Customer could not yet reach the contract signer; a half-payment appeared in a payment list, "
                "and a payment order was expected. No bank receipt is confirmed."
            )
            amendments.append("Reconciled both clauses of the February 20 call at source line 80.")
        elif deal_id == "18765":
            final["evidence"][12]["paraphrase"] = (
                "Message asks what criteria determine the director's choice; its recorded direction is unknown."
            )
            final["deal_dynamics"]["late"] = final["deal_dynamics"]["late"].replace(
                "a 23 Sep reply said", "a 23 Sep message of unknown direction said"
            )
            final["uncertainties"].append("The 23 Sep message has unknown recorded direction; do not attribute it to either party.")
            amendments.append("Removed unsupported sender attribution for source line 74.")
        elif deal_id == "6135":
            late = b["evidence"][5]
            assert late["source_line"] == 99
            if not any(e["source_line"] == 99 for e in final["evidence"]):
                final["evidence"].append(copy.deepcopy(late))
            final["deal_dynamics"]["late"] += (
                " A later seller-side call reports a 70% advance and component ordering; "
                "this is not independent bank confirmation (source line 99)."
            )
            final["uncertainties"].append("The reported 70% advance is seller-side speech, not a bank record.")
            amendments.append("Included B's late seller-side payment discussion without treating funds as verified.")

        if comparison["ratings"]["W"][0] == "DISAGREE":
            final["uncertainties"].append(
                "Independent audits differed on whether the observed process gap was a manager weakness; "
                "the listed action is a possible improvement, not a proven cause."
            )
            amendments.append("Qualified manager-weakness disagreement.")
        if deal_id in {"5971", "6135", "18485"}:
            final["uncertainties"].append(
                "Run A auditor previously handled source preprocessing; this deal's paired independence is limited."
            )
        if deal_id == "19007":
            amendments.append("Used fresh canonical B replacement; excluded prior non-blind B audit.")

        check_evidence(deal_id, final)
        outputs[deal_id] = final
        decisions.append({
            "deal_id": deal_id,
            "base": "run_A",
            "reason": "Run A retains more addressed evidence; B was used for semantic challenge and supported amendments.",
            "ratings": {field: comparison["ratings"][field][0] for field in RELIABILITY["field_order"]},
            "amendments": amendments,
            "critic_flags": comparison["flags"],
        })

    FINAL.mkdir(exist_ok=True)
    for deal_id, audit in outputs.items():
        with (FINAL / f"{deal_id}.json").open("x", encoding="utf-8") as file:
            json.dump(audit, file, ensure_ascii=False, indent=2)
            file.write("\n")
    with (ROOT / "reconciliation_decisions.json").open("x", encoding="utf-8") as file:
        json.dump({"version": "1.0", "outcome_accessed": False, "deals": decisions}, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"Wrote {len(outputs)} outcome-blind final audits")


if __name__ == "__main__":
    main()
