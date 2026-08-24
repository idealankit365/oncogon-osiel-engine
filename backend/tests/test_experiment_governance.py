from __future__ import annotations

import pytest

from app.experiments import ExperimentService
from app.repository import Repository
from app.schemas import ExperimentCreate, ResultApproval


def protocol(repository: Repository) -> ExperimentCreate:
    compounds = repository.list_compounds(limit=2)
    return ExperimentCreate(
        title="Breast cancer MTT software dry-run",
        compound_ids=[item.compound_id for item in compounds],
        cancer_type="Breast cancer",
        cell_line="MCF-7",
        dose_min_um=0.01,
        dose_max_um=10,
        dose_points=6,
        replicates=3,
    )


def test_experiment_dry_run_produces_qc_trace(
    repository: Repository, experiment_service: ExperimentService
) -> None:
    experiment = experiment_service.create(protocol(repository))
    result = experiment_service.simulate(experiment.experiment_id)
    assert result.simulation_only is True
    assert result.qc_status == "passed"
    assert len(result.observations) == 2 * 6 * 3
    assert "No physical assay" in result.disclaimer


def test_simulated_result_cannot_enter_training_pool(
    repository: Repository, experiment_service: ExperimentService
) -> None:
    experiment = experiment_service.create(protocol(repository))
    result = experiment_service.simulate(experiment.experiment_id)
    with pytest.raises(ValueError, match="never become training eligible"):
        experiment_service.approve(
            result.result_id,
            ResultApproval(
                decision="approve",
                reviewer="Dr Scientific Reviewer",
                reason="Software flow accepted; not biological evidence",
                training_eligible=True,
            ),
        )


def test_approval_does_not_mutate_model(
    repository: Repository, experiment_service: ExperimentService
) -> None:
    experiment = experiment_service.create(protocol(repository))
    result = experiment_service.simulate(experiment.experiment_id)
    decision = experiment_service.approve(
        result.result_id,
        ResultApproval(
            decision="approve",
            reviewer="Dr Scientific Reviewer",
            reason="Dry-run record is complete",
            training_eligible=False,
        ),
    )
    assert decision["model_mutated"] == "false"

