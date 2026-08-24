from __future__ import annotations

from pathlib import Path

import pytest

from app.config import settings
from app.experiments import ExperimentService
from app.prediction import DemoPredictionService
from app.ranking import RankingService
from app.repository import Repository


@pytest.fixture()
def repository(tmp_path: Path) -> Repository:
    repo = Repository(tmp_path / "test.db")
    count = repo.seed(settings.seed_path)
    assert count >= 180
    return repo


@pytest.fixture()
def predictor(repository: Repository) -> DemoPredictionService:
    return DemoPredictionService(repository)


@pytest.fixture()
def ranker(repository: Repository, predictor: DemoPredictionService) -> RankingService:
    return RankingService(repository, predictor)


@pytest.fixture()
def experiment_service(repository: Repository, predictor: DemoPredictionService) -> ExperimentService:
    return ExperimentService(repository, predictor)

