from __future__ import annotations

from app.prediction import DemoPredictionService
from app.ranking import RankingService
from app.repository import Repository
from app.schemas import RankingRequest


def test_seed_has_more_than_150_validated_compounds(repository: Repository) -> None:
    assert repository.count_compounds() >= 180


def test_prediction_is_reproducible_in_value_not_identity(
    repository: Repository, predictor: DemoPredictionService
) -> None:
    compound = repository.list_compounds(limit=1)[0]
    first = predictor.predict(compound, "Breast cancer", "MCF-7")
    second = predictor.predict(compound, "Breast cancer", "MCF-7")
    assert first.prediction_id != second.prediction_id
    assert first.predicted_activity == second.predicted_activity
    assert first.predicted_ic50_um == second.predicted_ic50_um
    assert first.model_version == second.model_version
    assert first.notice.research_use_only is True


def test_prediction_changes_with_scientific_context(
    repository: Repository, predictor: DemoPredictionService
) -> None:
    compound = repository.list_compounds(limit=1)[0]
    breast = predictor.predict(compound, "Breast cancer", "MCF-7")
    lung = predictor.predict(compound, "Lung cancer", "A549")
    assert breast.predicted_activity != lung.predicted_activity


def test_ranking_exposes_every_score_component(
    repository: Repository, ranker: RankingService
) -> None:
    compounds = repository.list_compounds(limit=6)
    run = ranker.rank(
        RankingRequest(
            compound_ids=[item.compound_id for item in compounds],
            cancer_type="Breast cancer",
            cell_line="MCF-7",
        )
    )
    assert len(run.ranked) == 6
    assert [item.rank for item in run.ranked] == list(range(1, 7))
    assert all(len(item.components) == 7 for item in run.ranked)
    assert all(item.prediction.uncertainty >= 0 for item in run.ranked)
    assert run.policy_version

