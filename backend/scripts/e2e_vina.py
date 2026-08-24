from __future__ import annotations

import argparse
import base64
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.docking_benchmark import DockingBenchmarkService
from app.immutable_storage import ImmutableObjectStore
from app.repository import Repository
from app.schemas import DockingBenchmarkRequest, DockingBox, VinaDockingRequest
from app.vina_docking import VinaDockingService


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute the pinned official 1IEP Vina example")
    parser.add_argument("--receptor", type=Path, default=Path("backend/data/vina-example/1iep_receptor.pdbqt"))
    parser.add_argument("--ligand", type=Path, default=Path("backend/data/vina-example/1iep_ligand.pdbqt"))
    parser.add_argument("--exhaustiveness", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.receptor.is_file() or not args.ligand.is_file():
        raise SystemExit(
            "Example inputs are missing. Run: PYTHONPATH=backend .venv/bin/python "
            "backend/scripts/fetch_vina_example.py"
        )

    with tempfile.TemporaryDirectory(prefix="osiel-vina-e2e-") as temporary:
        root = Path(temporary)
        repository = Repository(root / "vina-e2e.db")
        store = ImmutableObjectStore(root / "objects")
        service = VinaDockingService(
            repository,
            store=store,
            enabled=True,
            max_cpu=2,
            max_timeout_seconds=180,
        )
        request = VinaDockingRequest(
            receptor_filename=args.receptor.name,
            receptor_content_base64=base64.b64encode(args.receptor.read_bytes()).decode("ascii"),
            ligand_filename=args.ligand.name,
            ligand_content_base64=base64.b64encode(args.ligand.read_bytes()).decode("ascii"),
            box=DockingBox(
                center_x=15.190,
                center_y=53.903,
                center_z=16.917,
                size_x=20,
                size_y=20,
                size_z=20,
            ),
            scoring_function="vina",
            exhaustiveness=args.exhaustiveness,
            num_modes=3,
            energy_range=3,
            cpu=1,
            seed=20260822,
            timeout_seconds=180,
        )
        job = service.run(request, "vina-e2e-verifier")
        assert job.status == "completed"
        assert job.engine_version == "1.2.7"
        assert job.poses
        assert job.output_sha256
        benchmark = DockingBenchmarkService(repository, store=store).run(
            DockingBenchmarkRequest(
                docking_job_id=job.job_id,
                reference_ligand_filename=args.ligand.name,
                reference_ligand_content_base64=base64.b64encode(
                    args.ligand.read_bytes()
                ).decode("ascii"),
                rmsd_pass_threshold_angstrom=2.0,
            ),
            "vina-e2e-verifier",
        )
        report = {
                    "report_version": "1.0",
                    "executed_at": datetime.now(UTC).isoformat(),
                    "scenario": "official AutoDock Vina 1IEP example through OSIEL",
                    "job_id": job.job_id,
                    "status": job.status,
                    "engine_version": job.engine_version,
                    "duration_seconds": job.duration_seconds,
                    "poses": [pose.model_dump() for pose in job.poses],
                    "receptor_sha256": job.receptor_sha256,
                    "ligand_sha256": job.ligand_sha256,
                    "output_sha256": job.output_sha256,
                    "redocking_benchmark": {
                        "benchmark_id": benchmark.benchmark_id,
                        "status": benchmark.status,
                        "method": benchmark.method,
                        "threshold_angstrom": benchmark.rmsd_pass_threshold_angstrom,
                        "best_pose_rank": benchmark.best_pose_rank,
                        "best_rmsd_angstrom": benchmark.best_rmsd_angstrom,
                        "atom_type_order_match": benchmark.atom_type_order_match,
                        "scoring_qualified": benchmark.scoring_qualified,
                        "reference_sha256": benchmark.reference_sha256,
                        "scientific_boundary": benchmark.scientific_boundary,
                    },
                    "scientific_boundary": job.scientific_boundary,
                    "verified": True,
                }
        rendered = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")


if __name__ == "__main__":
    main()
