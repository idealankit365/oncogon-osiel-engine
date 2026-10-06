from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from .config import settings
from .prediction import DemoPredictionService
from .repository import Repository
from .schemas import (
    Compound,
    RankedCompound,
    RankingRequest,
    RankingRun,
    ScoreComponent,
)
from .synthetic_model import MODEL_VERSION


class RankingService:
    def __init__(self, repository: Repository, predictor: DemoPredictionService) -> None:
        self.repository = repository
        self.predictor = predictor

    def get(self, run_id: str) -> RankingRun | None:
        with self.repository.connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM ranking_run WHERE ranking_run_id = ?", (run_id,)
            ).fetchone()
        return RankingRun.model_validate_json(row["payload_json"]) if row else None

    def list(self, limit: int = 20) -> list[RankingRun]:
        with self.repository.connection() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM ranking_run ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [RankingRun.model_validate_json(row["payload_json"]) for row in rows]

    def rank(self, request: RankingRequest) -> RankingRun:
        compounds = self.repository.get_compounds(request.compound_ids)
        if len(compounds) < 2:
            raise ValueError("At least two resolvable compounds are required")
        seed = secrets.token_hex(16)

        provisional: list[tuple[Compound, object, list[ScoreComponent], list[str], str]] = []
        for compound in compounds:
            prediction = self.predictor.predict(
                compound,
                cancer_type=request.cancer_type,
                cell_line=request.cell_line,
                run_seed=seed,
            )
            hard_reasons: list[str] = []
            eligibility = "eligible"
            if prediction.applicability_domain == "outside":
                hard_reasons.append("Outside research model applicability domain")
                eligibility = "flagged"
            if compound.descriptors.molecular_weight > 900:
                hard_reasons.append("Molecular weight exceeds Phase-1 policy threshold")
                eligibility = "excluded"

            components = self._components(compound, prediction, request)
            provisional.append((compound, prediction, components, hard_reasons, eligibility))

        scores = [sum(item.contribution for item in components) for _, _, components, _, _ in provisional]
        order = sorted(range(len(provisional)), key=lambda index: scores[index], reverse=True)
        ranked: list[RankedCompound] = []
        selected_smiles: list[str] = []
        for rank_index, candidate_index in enumerate(order, start=1):
            compound, prediction, components, hard_reasons, eligibility = provisional[candidate_index]
            if eligibility != "excluded" and selected_smiles:
                maximum_similarity = max(
                    self.predictor._nearest_analogs(compound, limit=1)[0].tanimoto_similarity
                    if self.predictor._nearest_analogs(compound, limit=1)
                    else 0.0,
                    0.0,
                )
                if maximum_similarity > request.diversity_threshold:
                    hard_reasons.append("High structural redundancy; diversity review required")
                    eligibility = "flagged"
            selected_smiles.append(compound.canonical_smiles)
            ranked.append(
                RankedCompound(
                    rank=rank_index,
                    compound_id=compound.compound_id,
                    display_name=compound.display_name,
                    score=round(max(0.0, min(100.0, scores[candidate_index])), 2),
                    pareto_front=1 if rank_index <= max(1, len(order) // 3) else 2,
                    eligibility=eligibility,
                    hard_filter_reasons=hard_reasons,
                    components=components,
                    prediction=prediction,
                )
            )

        run = RankingRun(
            ranking_run_id=self.repository.new_id("RNK"),
            policy_version=settings.ranking_policy_version,
            cancer_type=request.cancer_type,
            cell_line=request.cell_line,
            simulation_seed=seed,
            model_version=MODEL_VERSION,
            model_class="synthetic_research_simulation",
            weights=request.weights,
            candidate_count=len(ranked),
            ranked=ranked,
            created_at=datetime.now(UTC),
        )
        self.repository.save_json_record(
            "ranking_run",
            "ranking_run_id",
            run.ranking_run_id,
            run.model_dump(mode="json"),
            policy_version=run.policy_version,
        )
        self.repository.audit(
            "demo-researcher",
            "ranking.completed",
            "ranking_run",
            run.ranking_run_id,
            {"policy_version": run.policy_version, "candidate_count": len(ranked), "model_version": MODEL_VERSION, "simulation_seed": seed},
        )
        return run

    @staticmethod
    def _components(compound: Compound, prediction: object, request: RankingRequest) -> list[ScoreComponent]:
        weights = request.weights
        admet_good = []
        for endpoint in prediction.admet:
            value = float(endpoint.predicted_value)
            admet_good.append(1 - value if endpoint.code in {"herg", "liver"} else value)
        admet_score = sum(admet_good) / len(admet_good)
        digest = hashlib.sha256(compound.inchikey.encode()).digest()
        novelty = 0.45 + digest[0] / 255 * 0.5
        feasibility = 0.6 * compound.descriptors.qed + 0.4 * max(
            0.0, 1 - compound.descriptors.rotatable_bonds / 18
        )
        evidence_map = {"A": 0.95, "B": 0.8, "C": 0.62, "D": 0.4}
        values = [
            ("activity", "Predicted activity", prediction.predicted_activity, weights.activity, "Research model activity hypothesis."),
            ("selectivity", "Predicted selectivity", min(1.0, prediction.predicted_selectivity_index / 30), weights.selectivity, "Normalized predicted selectivity index."),
            ("admet", "ADMET panel", admet_score, weights.admet, "Endpoint-specific developability screening panel."),
            ("novelty", "Structural novelty", novelty, weights.novelty, "Stable structure proxy; training-set similarity requires validation."),
            ("feasibility", "Feasibility", feasibility, weights.feasibility, "QED and molecular flexibility proxy pending chemist review."),
            ("evidence", "Evidence quality", evidence_map[compound.evidence_grade], weights.evidence, "Identity/provenance evidence grade, not efficacy evidence."),
            ("uncertainty", "Uncertainty penalty", prediction.uncertainty, -weights.uncertainty_penalty, "Penalty for uncertainty and model-domain risk."),
        ]
        return [
            ScoreComponent(
                code=code,
                label=label,
                value=round(value * 100, 2),
                weight=round(weight, 4),
                contribution=round(value * weight * 100, 4),
                explanation=explanation,
            )
            for code, label, value, weight, explanation in values
        ]
