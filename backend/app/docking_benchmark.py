from __future__ import annotations

import base64
import binascii
from datetime import UTC, datetime
from typing import Any

import numpy as np

from .immutable_storage import ImmutableObjectStore, object_store
from .repository import Repository
from .schemas import (
    DockingBenchmarkRequest,
    DockingBenchmarkRun,
    DockingPoseBenchmark,
    VinaDockingJob,
)


BENCHMARK_BOUNDARY = (
    "A successful redocking RMSD checks pose-recovery for this prepared complex and search box. "
    "It does not validate affinity ranking, enrichment, cellular activity, safety or efficacy. "
    "A qualified protocol also needs multiple complexes, decoys, sensitivity analysis and review."
)


class DockingBenchmarkInputError(ValueError):
    pass


class DockingBenchmarkService:
    """Heavy-atom, atom-order-preserving Kabsch RMSD for completed Vina jobs."""

    def __init__(
        self,
        repository: Repository,
        *,
        store: ImmutableObjectStore | None = None,
    ) -> None:
        self.repository = repository
        self.store = store or object_store

    def run(
        self,
        request: DockingBenchmarkRequest,
        actor: str,
    ) -> DockingBenchmarkRun:
        stored = self.repository.get_docking_job(request.docking_job_id)
        if not stored:
            raise KeyError("Docking job not found")
        job = VinaDockingJob.model_validate(stored)
        if job.status != "completed" or not job.output_pdbqt_base64:
            raise DockingBenchmarkInputError("Only a completed Vina job with retained poses can be benchmarked")
        reference = self._decode(request.reference_ligand_content_base64)
        reference_atoms = self._atoms(reference.decode("utf-8"))
        if len(reference_atoms) < 3:
            raise DockingBenchmarkInputError("Reference ligand must contain at least three heavy atoms")
        output = base64.b64decode(job.output_pdbqt_base64, validate=True).decode("utf-8")
        poses = self._poses(output)
        if not poses:
            raise DockingBenchmarkInputError("Docking output contains no parseable pose")

        reference_types = [atom[0] for atom in reference_atoms]
        reference_coordinates = np.asarray([atom[1] for atom in reference_atoms], dtype=np.float64)
        pose_results: list[DockingPoseBenchmark] = []
        atom_type_order_match = True
        for rank, pose_text in enumerate(poses, start=1):
            pose_atoms = self._atoms(pose_text)
            pose_types = [atom[0] for atom in pose_atoms]
            if pose_types != reference_types:
                atom_type_order_match = False
                continue
            pose_coordinates = np.asarray([atom[1] for atom in pose_atoms], dtype=np.float64)
            rmsd = self._aligned_rmsd(reference_coordinates, pose_coordinates)
            affinity = next(
                (pose.affinity_kcal_mol for pose in job.poses if pose.rank == rank),
                None,
            )
            pose_results.append(
                DockingPoseBenchmark(
                    pose_rank=rank,
                    affinity_kcal_mol=affinity,
                    aligned_heavy_atom_rmsd_angstrom=round(rmsd, 4),
                    atom_count=len(reference_atoms),
                )
            )
        if not pose_results:
            raise DockingBenchmarkInputError(
                "Reference and docked poses do not have the same heavy-atom type order; use the exact prepared co-crystal ligand"
            )

        best = min(pose_results, key=lambda item: item.aligned_heavy_atom_rmsd_angstrom)
        passed = best.aligned_heavy_atom_rmsd_angstrom <= request.rmsd_pass_threshold_angstrom
        reference_sha, reference_uri = self.store.put(
            reference,
            request.reference_ligand_filename,
            {
                "kind": "vina-redocking-reference-ligand",
                "docking_job_id": job.job_id,
                "actor": actor,
            },
        )
        benchmark = DockingBenchmarkRun(
            benchmark_id=self.repository.new_id("DBM"),
            docking_job_id=job.job_id,
            status="passed" if passed else "failed",
            method="atom-order-preserving heavy-atom Kabsch RMSD",
            rmsd_pass_threshold_angstrom=request.rmsd_pass_threshold_angstrom,
            best_pose_rank=best.pose_rank,
            best_rmsd_angstrom=best.aligned_heavy_atom_rmsd_angstrom,
            pose_results=pose_results,
            reference_sha256=reference_sha,
            reference_object_uri=reference_uri,
            atom_type_order_match=atom_type_order_match,
            scoring_qualified=False,
            warnings=[
                "Atom ordering must be identical to the docked input ligand.",
                "Symmetry-equivalent atom permutations are not corrected by this reference implementation.",
            ],
            created_at=datetime.now(UTC),
            scientific_boundary=BENCHMARK_BOUNDARY,
        )
        self.repository.save_docking_benchmark(
            benchmark.benchmark_id,
            job.job_id,
            benchmark.status,
            benchmark.model_dump(mode="json"),
        )
        self.repository.audit(
            actor,
            "docking.redocking_benchmark_completed",
            "docking_benchmark_run",
            benchmark.benchmark_id,
            {
                "docking_job_id": job.job_id,
                "status": benchmark.status,
                "best_pose_rank": benchmark.best_pose_rank,
                "best_rmsd_angstrom": benchmark.best_rmsd_angstrom,
                "threshold_angstrom": benchmark.rmsd_pass_threshold_angstrom,
                "scoring_qualified": False,
                "reference_sha256": reference_sha,
            },
        )
        return benchmark

    @staticmethod
    def _decode(encoded: str) -> bytes:
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise DockingBenchmarkInputError("Reference ligand is not valid base64") from exc
        if not content or len(content) > settings_limit():
            raise DockingBenchmarkInputError("Reference ligand size is invalid")
        if b"\x00" in content:
            raise DockingBenchmarkInputError("Reference ligand contains a NUL byte")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DockingBenchmarkInputError("Reference ligand must be UTF-8/ASCII PDBQT") from exc
        return content

    @staticmethod
    def _poses(text: str) -> list[str]:
        lines = text.splitlines()
        if not any(line.startswith("MODEL") for line in lines):
            return [text]
        poses: list[str] = []
        current: list[str] = []
        inside = False
        for line in lines:
            if line.startswith("MODEL"):
                current = []
                inside = True
                continue
            if line.startswith("ENDMDL") and inside:
                poses.append("\n".join(current))
                inside = False
                continue
            if inside:
                current.append(line)
        return poses

    @staticmethod
    def _atoms(text: str) -> list[tuple[str, tuple[float, float, float]]]:
        atoms: list[tuple[str, tuple[float, float, float]]] = []
        for line in text.splitlines():
            if not line.startswith(("ATOM  ", "HETATM")):
                continue
            tokens = line.split()
            atom_type = tokens[-1] if tokens else ""
            if atom_type.upper().startswith("H"):
                continue
            try:
                if len(line) >= 54:
                    coordinates = (
                        float(line[30:38]),
                        float(line[38:46]),
                        float(line[46:54]),
                    )
                else:
                    coordinates = (float(tokens[6]), float(tokens[7]), float(tokens[8]))
            except (ValueError, IndexError) as exc:
                raise DockingBenchmarkInputError("A PDBQT atom coordinate could not be parsed") from exc
            atoms.append((atom_type, coordinates))
        return atoms

    @staticmethod
    def _aligned_rmsd(reference: np.ndarray, mobile: np.ndarray) -> float:
        if reference.shape != mobile.shape or reference.ndim != 2 or reference.shape[1] != 3:
            raise DockingBenchmarkInputError("Reference and pose coordinate arrays do not match")
        reference_centered = reference - np.mean(reference, axis=0)
        mobile_centered = mobile - np.mean(mobile, axis=0)
        covariance = mobile_centered.T @ reference_centered
        left, _, right = np.linalg.svd(covariance)
        rotation = left @ right
        if np.linalg.det(rotation) < 0:
            left[:, -1] *= -1
            rotation = left @ right
        aligned = mobile_centered @ rotation
        return float(np.sqrt(np.mean(np.sum((aligned - reference_centered) ** 2, axis=1))))


def settings_limit() -> int:
    # Kept as a function so tests can exercise the parser without mutating global settings.
    from .config import settings

    return settings.vina_max_ligand_bytes
