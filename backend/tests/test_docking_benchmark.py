from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.docking_benchmark import DockingBenchmarkInputError, DockingBenchmarkService
from app.immutable_storage import ImmutableObjectStore
from app.repository import Repository
from app.schemas import DockingBenchmarkRequest, DockingBox, VinaDockingJob, VinaPose


def atom(serial: int, name: str, x: float, y: float, z: float, atom_type: str) -> str:
    return (
        f"HETATM{serial:5d} {name:<4} LIG A   1    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00     0.000 {atom_type}"
    )


REFERENCE = "\n".join(
    [
        "ROOT",
        atom(1, "C1", 0.0, 0.0, 0.0, "C"),
        atom(2, "N1", 1.0, 0.0, 0.0, "N"),
        atom(3, "O1", 0.0, 2.0, 0.0, "OA"),
        "ENDROOT",
        "TORSDOF 0",
    ]
) + "\n"


POSE = "\n".join(
    [
        "MODEL 1",
        atom(1, "C1", 4.0, -3.0, 2.0, "C"),
        atom(2, "N1", 4.0, -2.0, 2.0, "N"),
        atom(3, "O1", 2.0, -3.0, 2.0, "OA"),
        "ENDMDL",
    ]
) + "\n"


def completed_job(repository: Repository) -> VinaDockingJob:
    job = VinaDockingJob(
        job_id=repository.new_id("VIN"),
        status="completed",
        engine_version="1.2.7",
        scoring_function="vina",
        receptor_filename="receptor.pdbqt",
        receptor_sha256="a" * 64,
        receptor_object_uri=f"immutable://sha256/{'a' * 64}",
        ligand_filename="ligand.pdbqt",
        ligand_sha256="b" * 64,
        ligand_object_uri=f"immutable://sha256/{'b' * 64}",
        output_sha256="c" * 64,
        output_object_uri=f"immutable://sha256/{'c' * 64}",
        output_filename="ligand_out.pdbqt",
        output_pdbqt_base64=base64.b64encode(POSE.encode()).decode(),
        box=DockingBox(center_x=0, center_y=0, center_z=0, size_x=20, size_y=20, size_z=20),
        exhaustiveness=8,
        num_modes_requested=1,
        num_modes_returned=1,
        energy_range=3,
        cpu=1,
        seed=42,
        duration_seconds=1.2,
        poses=[VinaPose(rank=1, affinity_kcal_mol=-7.4, raw_energy_terms=[-7.4])],
        warnings=[],
        command_manifest=["python -m app.vina_worker"],
        scientific_boundary="software test",
        created_at=datetime.now(UTC),
    )
    repository.save_docking_job(job.job_id, job.status, job.model_dump(mode="json"))
    return job


def test_redocking_benchmark_recovers_rotated_translated_pose(
    repository: Repository,
    tmp_path: Path,
) -> None:
    job = completed_job(repository)
    service = DockingBenchmarkService(
        repository,
        store=ImmutableObjectStore(tmp_path / "objects"),
    )
    result = service.run(
        DockingBenchmarkRequest(
            docking_job_id=job.job_id,
            reference_ligand_filename="reference.pdbqt",
            reference_ligand_content_base64=base64.b64encode(REFERENCE.encode()).decode(),
            rmsd_pass_threshold_angstrom=2.0,
        ),
        "test-researcher",
    )
    assert result.status == "passed"
    assert result.best_pose_rank == 1
    assert result.best_rmsd_angstrom == pytest.approx(0, abs=1e-6)
    assert result.scoring_qualified is False
    assert result.reference_sha256


def test_redocking_requires_matching_atom_order(repository: Repository, tmp_path: Path) -> None:
    job = completed_job(repository)
    changed = REFERENCE.replace(" 0.000 OA", " 0.000 S")
    service = DockingBenchmarkService(
        repository,
        store=ImmutableObjectStore(tmp_path / "objects"),
    )
    with pytest.raises(DockingBenchmarkInputError, match="same heavy-atom type order"):
        service.run(
            DockingBenchmarkRequest(
                docking_job_id=job.job_id,
                reference_ligand_filename="reference.pdbqt",
                reference_ligand_content_base64=base64.b64encode(changed.encode()).decode(),
            ),
            "test",
        )
