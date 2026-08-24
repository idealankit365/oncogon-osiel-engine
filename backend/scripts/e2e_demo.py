"""Run the complete OSIEL developer-reference scenario and emit a JSON report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def run() -> dict[str, object]:
    client = TestClient(app)
    health = client.get("/health")
    health.raise_for_status()
    compounds_response = client.get("/v1/compounds", params={"limit": 8})
    compounds_response.raise_for_status()
    compounds = compounds_response.json()
    candidate_ids = [item["compound_id"] for item in compounds[:6]]

    ranking_response = client.post(
        "/v1/rankings",
        json={
            "compound_ids": candidate_ids,
            "cancer_type": "Non-small cell lung cancer",
            "cell_line": "A549",
            "diversity_threshold": 0.82,
        },
    )
    ranking_response.raise_for_status()
    ranking = ranking_response.json()
    selected = [item["compound_id"] for item in ranking["ranked"][:3]]

    experiment_response = client.post(
        "/v1/experiments",
        headers={"X-OSIEL-Actor": "e2e-demo-scientist"},
        json={
            "title": "NSCLC A549 computational workflow validation",
            "compound_ids": selected,
            "cancer_type": "Non-small cell lung cancer",
            "cell_line": "A549",
            "assay_type": "CellTiter-Glo",
            "endpoint": "IC50",
            "dose_min_um": 0.01,
            "dose_max_um": 30.0,
            "dose_points": 8,
            "replicates": 3,
            "duration_hours": 72,
            "positive_control": "Doxorubicin",
            "negative_control": "Vehicle",
            "source_ranking_run_id": ranking["ranking_run_id"],
        },
    )
    experiment_response.raise_for_status()
    experiment = experiment_response.json()

    simulation_response = client.post(
        f"/v1/experiments/{experiment['experiment_id']}/simulate"
    )
    simulation_response.raise_for_status()
    result = simulation_response.json()

    champion_before = client.get("/v1/models").json()
    prohibited_review = client.post(
        f"/v1/results/{result['result_id']}/review",
        json={
            "decision": "approve",
            "reviewer": "e2e-scientific-reviewer",
            "reason": "Testing the simulation-only training prohibition",
            "training_eligible": True,
        },
    )
    champion_after = client.get("/v1/models").json()
    audit = client.get("/v1/audit", params={"limit": 20}).json()

    return {
        "scenario": "OSIEL identity-to-governance developer-reference run",
        "research_use_only": True,
        "health": health.json(),
        "candidate_count": len(candidate_ids),
        "ranking_run_id": ranking["ranking_run_id"],
        "policy_version": ranking["policy_version"],
        "top_candidates": [
            {
                "rank": item["rank"],
                "compound_id": item["compound_id"],
                "display_name": item["display_name"],
                "score": item["score"],
                "uncertainty": item["prediction"]["uncertainty"],
                "applicability_domain": item["prediction"]["applicability_domain"],
                "predicted_ic50_um": item["prediction"]["predicted_ic50_um"],
            }
            for item in ranking["ranked"][:3]
        ],
        "experiment_id": experiment["experiment_id"],
        "result_id": result["result_id"],
        "simulation_only": result["simulation_only"],
        "synthetic_observations": len(result["observations"]),
        "estimated_ic50_um": result["estimated_ic50_um"],
        "qc_status": result["qc_status"],
        "qc_checks": result["qc_checks"],
        "training_eligibility_attempt": {
            "http_status": prohibited_review.status_code,
            "rejected": prohibited_review.status_code == 422,
            "detail": prohibited_review.json().get("detail"),
        },
        "champion_unchanged": champion_before == champion_after,
        "audit_events_returned": len(audit),
        "disclaimer": result["disclaimer"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    payload = run()
    rendered = json.dumps(payload, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
