"""Bounded, reproducible perturbation for research showcase ranking runs.

This module creates computational estimates only. It never generates source evidence.
"""

import hashlib

from .schemas import Prediction

MODEL_VERSION = "osiel-research-sim@1.0"


def _unit(*parts: str) -> float:
    digest = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / (2**64 - 1)


def simulate_prediction(base: Prediction, seed: str) -> Prediction:
    """Preserve descriptor baseline and domain while varying a stored run seed."""
    delta = (_unit(seed, base.compound_id, base.cancer_type, base.cell_line or "", base.endpoint) - 0.5) * 0.12
    activity = min(0.95, max(0.05, base.predicted_activity + delta))
    domain_penalty = {"inside": 0.0, "borderline": 0.07, "outside": 0.17}[base.applicability_domain]
    uncertainty = min(0.24, max(0.04, base.uncertainty + abs(delta) * 0.2 + domain_penalty))
    confidence = min(0.92, max(0.55, 1 - uncertainty - domain_penalty))
    ic50 = min(200.0, max(0.004, base.predicted_ic50_um * 10 ** (-2.35 * delta)))
    selectivity = min(95.0, max(1.0, base.predicted_selectivity_index * (1 + delta)))
    return base.model_copy(update={
        "predicted_activity": round(activity, 4),
        "predicted_ic50_um": round(ic50, 4),
        "predicted_selectivity_index": round(selectivity, 3),
        "uncertainty": round(uncertainty, 4),
        "confidence": round(confidence, 4),
        "interval_low": round(max(0.0, activity - uncertainty), 4),
        "interval_high": round(min(1.0, activity + uncertainty), 4),
        "model_version": MODEL_VERSION,
        "evidence_summary": base.evidence_summary.replace("OSIEL demo adapter", "OSIEL research simulation model"),
    })
