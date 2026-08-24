from __future__ import annotations

import base64
import binascii
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .config import settings
from .immutable_storage import ImmutableObjectStore, object_store
from .repository import Repository
from .schemas import VinaDockingJob, VinaDockingRequest, VinaPose


SCIENTIFIC_BOUNDARY = (
    "AutoDock Vina scores are approximate pose-ranking outputs in kcal/mol. They are not "
    "measured binding affinities, cellular activity, safety, efficacy, or clinical evidence. "
    "Interpretation requires receptor/ligand preparation review, redocking controls, sensitivity "
    "analysis, orthogonal computation, and experimental validation."
)


class VinaDisabledError(RuntimeError):
    pass


class DockingInputError(ValueError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


class VinaDockingService:
    """Runs the official Vina Python engine in a bounded child process.

    The API accepts prepared PDBQT files only. Preparation is scientifically consequential and
    is intentionally not guessed from a raw PDB or SMILES string in this reference service.
    """

    def __init__(
        self,
        repository: Repository,
        *,
        store: ImmutableObjectStore | None = None,
        enabled: bool | None = None,
        max_cpu: int | None = None,
        max_timeout_seconds: int | None = None,
        runner: Runner = subprocess.run,
    ) -> None:
        self.repository = repository
        self.store = store or object_store
        self.enabled = settings.vina_enabled if enabled is None else enabled
        self.max_cpu = settings.vina_max_cpu if max_cpu is None else max(1, max_cpu)
        self.max_timeout_seconds = (
            settings.vina_max_timeout_seconds
            if max_timeout_seconds is None
            else max(10, max_timeout_seconds)
        )
        self.runner = runner

    @staticmethod
    def binding_available() -> bool:
        return importlib.util.find_spec("vina") is not None

    def capability(self) -> dict[str, str | int | bool | None]:
        version: str | None = None
        if self.binding_available():
            try:
                import vina

                version = vina.__version__
            except Exception:
                version = "installed-version-unresolved"
        return {
            "operator_enabled": self.enabled,
            "binding_available": self.binding_available(),
            "engine_version": version,
            "execution_model": "bounded child process; no shell",
            "accepted_input": "prepared rigid-receptor and ligand PDBQT",
            "max_cpu": self.max_cpu,
            "max_timeout_seconds": self.max_timeout_seconds,
            "validated_scientific_protocol": False,
        }

    def run(self, request: VinaDockingRequest, actor: str) -> VinaDockingJob:
        if not self.enabled:
            raise VinaDisabledError(
                "Vina execution is disabled by the server operator. Set OSIEL_VINA_ENABLED=true "
                "only on an authenticated, resource-limited worker."
            )
        if not self.binding_available():
            raise VinaDisabledError(
                "The vina==1.2.7 Python binding is not installed in this API environment."
            )
        if request.cpu > self.max_cpu:
            raise DockingInputError(
                f"requested cpu={request.cpu} exceeds the server limit of {self.max_cpu}"
            )
        if request.timeout_seconds > self.max_timeout_seconds:
            raise DockingInputError(
                f"requested timeout exceeds the server limit of {self.max_timeout_seconds} seconds"
            )
        if request.open_discovery_run_id and not self.repository.get_open_discovery_run(
            request.open_discovery_run_id
        ):
            raise DockingInputError("linked Open Discovery run does not exist")

        receptor = self._decode(
            request.receptor_content_base64,
            request.receptor_filename,
            settings.vina_max_receptor_bytes,
            kind="receptor",
        )
        ligand = self._decode(
            request.ligand_content_base64,
            request.ligand_filename,
            settings.vina_max_ligand_bytes,
            kind="ligand",
        )
        self._validate_pdbqt(receptor, kind="receptor")
        self._validate_pdbqt(ligand, kind="ligand")

        job_id = self.repository.new_id("VIN")
        created_at = datetime.now(UTC)
        receptor_sha, receptor_uri = self.store.put(
            receptor,
            request.receptor_filename,
            {"job_id": job_id, "actor": actor, "kind": "vina-receptor-input"},
        )
        ligand_sha, ligand_uri = self.store.put(
            ligand,
            request.ligand_filename,
            {"job_id": job_id, "actor": actor, "kind": "vina-ligand-input"},
        )
        started = time.perf_counter()
        warnings = self._warnings(request)
        manifest = [
            f"{sys.executable} -m app.vina_worker",
            "--receptor <immutable-receptor.pdbqt>",
            "--ligand <immutable-ligand.pdbqt>",
            "--output <immutable-output.pdbqt>",
            f"--scoring {request.scoring_function}",
            f"--center {request.box.center_x} {request.box.center_y} {request.box.center_z}",
            f"--size {request.box.size_x} {request.box.size_y} {request.box.size_z}",
            f"--exhaustiveness {request.exhaustiveness}",
            f"--num-modes {request.num_modes}",
            f"--energy-range {request.energy_range}",
            f"--cpu {request.cpu}",
            f"--seed {request.seed}",
        ]

        with tempfile.TemporaryDirectory(prefix=f"osiel-{job_id.lower()}-") as temporary:
            folder = Path(temporary)
            receptor_path = folder / "receptor.pdbqt"
            ligand_path = folder / "ligand.pdbqt"
            output_path = folder / "vina_output.pdbqt"
            receptor_path.write_bytes(receptor)
            ligand_path.write_bytes(ligand)
            command = [
                sys.executable,
                "-m",
                "app.vina_worker",
                "--receptor",
                str(receptor_path),
                "--ligand",
                str(ligand_path),
                "--output",
                str(output_path),
                "--scoring",
                request.scoring_function,
                "--center",
                str(request.box.center_x),
                str(request.box.center_y),
                str(request.box.center_z),
                "--size",
                str(request.box.size_x),
                str(request.box.size_y),
                str(request.box.size_z),
                "--exhaustiveness",
                str(request.exhaustiveness),
                "--num-modes",
                str(request.num_modes),
                "--energy-range",
                str(request.energy_range),
                "--cpu",
                str(request.cpu),
                "--seed",
                str(request.seed),
            ]
            environment = os.environ.copy()
            backend_root = str(Path(__file__).resolve().parent.parent)
            environment["PYTHONPATH"] = os.pathsep.join(
                value
                for value in (backend_root, environment.get("PYTHONPATH", ""))
                if value
            )
            try:
                completed = self.runner(
                    command,
                    cwd=folder,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=request.timeout_seconds,
                    check=False,
                    start_new_session=True,
                )
            except subprocess.TimeoutExpired:
                return self._failure_job(
                    job_id,
                    request,
                    receptor_sha,
                    receptor_uri,
                    ligand_sha,
                    ligand_uri,
                    "timed-out",
                    f"Vina exceeded the {request.timeout_seconds}-second job timeout.",
                    warnings,
                    manifest,
                    started,
                    created_at,
                    actor,
                )
            except OSError as exc:
                return self._failure_job(
                    job_id,
                    request,
                    receptor_sha,
                    receptor_uri,
                    ligand_sha,
                    ligand_uri,
                    "failed",
                    f"Vina worker could not start: {type(exc).__name__}.",
                    warnings,
                    manifest,
                    started,
                    created_at,
                    actor,
                )

            if completed.returncode != 0:
                error = self._worker_error(completed.stderr)
                return self._failure_job(
                    job_id,
                    request,
                    receptor_sha,
                    receptor_uri,
                    ligand_sha,
                    ligand_uri,
                    "failed",
                    error,
                    warnings,
                    manifest,
                    started,
                    created_at,
                    actor,
                )
            try:
                payload = self._worker_payload(completed.stdout)
                output = output_path.read_bytes()
                if not output or len(output) > 20_000_000:
                    raise ValueError("worker output size is invalid")
                energies = payload.get("energies") or []
                poses = [
                    VinaPose(
                        rank=index,
                        affinity_kcal_mol=round(float(row[0]), 4),
                        raw_energy_terms=[round(float(item), 4) for item in row],
                    )
                    for index, row in enumerate(energies, start=1)
                    if row
                ]
                if not poses:
                    raise ValueError("worker returned no ranked poses")
            except (ValueError, OSError, json.JSONDecodeError, TypeError) as exc:
                return self._failure_job(
                    job_id,
                    request,
                    receptor_sha,
                    receptor_uri,
                    ligand_sha,
                    ligand_uri,
                    "failed",
                    f"Vina worker output could not be validated: {type(exc).__name__}.",
                    warnings,
                    manifest,
                    started,
                    created_at,
                    actor,
                )

            output_name = f"{Path(request.ligand_filename).stem}_vina_out.pdbqt"
            output_sha, output_uri = self.store.put(
                output,
                output_name,
                {
                    "job_id": job_id,
                    "actor": actor,
                    "kind": "vina-ranked-poses",
                    "receptor_sha256": receptor_sha,
                    "ligand_sha256": ligand_sha,
                },
            )
            job = VinaDockingJob(
                job_id=job_id,
                status="completed",
                engine_version=str(payload.get("engine_version") or "unknown"),
                scoring_function=request.scoring_function,
                receptor_filename=request.receptor_filename,
                receptor_sha256=receptor_sha,
                receptor_object_uri=receptor_uri,
                ligand_filename=request.ligand_filename,
                ligand_sha256=ligand_sha,
                ligand_object_uri=ligand_uri,
                output_sha256=output_sha,
                output_object_uri=output_uri,
                output_filename=output_name,
                output_pdbqt_base64=base64.b64encode(output).decode("ascii"),
                box=request.box,
                exhaustiveness=request.exhaustiveness,
                num_modes_requested=request.num_modes,
                num_modes_returned=len(poses),
                energy_range=request.energy_range,
                cpu=request.cpu,
                seed=request.seed,
                duration_seconds=round(time.perf_counter() - started, 4),
                poses=poses,
                warnings=warnings,
                open_discovery_run_id=request.open_discovery_run_id,
                command_manifest=manifest,
                scientific_boundary=SCIENTIFIC_BOUNDARY,
                created_at=created_at,
            )
            self._persist_and_audit(job, actor)
            return job

    def _failure_job(
        self,
        job_id: str,
        request: VinaDockingRequest,
        receptor_sha: str,
        receptor_uri: str,
        ligand_sha: str,
        ligand_uri: str,
        status: str,
        error: str,
        warnings: list[str],
        manifest: list[str],
        started: float,
        created_at: datetime,
        actor: str,
    ) -> VinaDockingJob:
        job = VinaDockingJob(
            job_id=job_id,
            status=status,
            scoring_function=request.scoring_function,
            receptor_filename=request.receptor_filename,
            receptor_sha256=receptor_sha,
            receptor_object_uri=receptor_uri,
            ligand_filename=request.ligand_filename,
            ligand_sha256=ligand_sha,
            ligand_object_uri=ligand_uri,
            box=request.box,
            exhaustiveness=request.exhaustiveness,
            num_modes_requested=request.num_modes,
            num_modes_returned=0,
            energy_range=request.energy_range,
            cpu=request.cpu,
            seed=request.seed,
            duration_seconds=round(time.perf_counter() - started, 4),
            poses=[],
            warnings=warnings,
            error=error[:2000],
            open_discovery_run_id=request.open_discovery_run_id,
            command_manifest=manifest,
            scientific_boundary=SCIENTIFIC_BOUNDARY,
            created_at=created_at,
        )
        self._persist_and_audit(job, actor)
        return job

    def _persist_and_audit(self, job: VinaDockingJob, actor: str) -> None:
        self.repository.save_docking_job(job.job_id, job.status, job.model_dump(mode="json"))
        self.repository.audit(
            actor,
            "docking.completed" if job.status == "completed" else "docking.failed",
            "docking_job",
            job.job_id,
            {
                "status": job.status,
                "engine_version": job.engine_version,
                "receptor_sha256": job.receptor_sha256,
                "ligand_sha256": job.ligand_sha256,
                "output_sha256": job.output_sha256,
                "pose_count": job.num_modes_returned,
                "open_discovery_run_id": job.open_discovery_run_id,
            },
        )

    @staticmethod
    def _decode(encoded: str, filename: str, limit: int, *, kind: str) -> bytes:
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise DockingInputError(f"{kind} content is not valid base64") from exc
        if not content:
            raise DockingInputError(f"{kind} file is empty")
        if len(content) > limit:
            raise DockingInputError(f"{kind} file exceeds the {limit}-byte server limit")
        if Path(filename).name != filename or not filename.lower().endswith(".pdbqt"):
            raise DockingInputError(f"{kind} filename must be a safe .pdbqt basename")
        return content

    @staticmethod
    def _validate_pdbqt(content: bytes, *, kind: str) -> None:
        if b"\x00" in content:
            raise DockingInputError(f"{kind} PDBQT contains a NUL byte")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DockingInputError(f"{kind} PDBQT must be UTF-8/ASCII text") from exc
        atom_count = sum(
            line.startswith(("ATOM  ", "HETATM"))
            for line in text.splitlines()
        )
        if atom_count == 0:
            raise DockingInputError(f"{kind} PDBQT contains no ATOM or HETATM records")
        if kind == "ligand":
            required = ("ROOT", "ENDROOT", "TORSDOF")
            missing = [marker for marker in required if marker not in text]
            if missing:
                raise DockingInputError(
                    f"ligand PDBQT is missing required markers: {', '.join(missing)}"
                )

    @staticmethod
    def _worker_payload(stdout: str) -> dict[str, Any]:
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            raise ValueError("worker returned no JSON")
        return json.loads(lines[-1])

    @staticmethod
    def _worker_error(stderr: str) -> str:
        lines = [line.strip() for line in stderr.splitlines() if line.strip()]
        if not lines:
            return "Vina worker failed without a diagnostic message."
        try:
            payload = json.loads(lines[-1])
            return f"Vina worker failed: {str(payload.get('error') or 'unknown error')[:1900]}"
        except json.JSONDecodeError:
            return f"Vina worker failed: {lines[-1][:1900]}"

    @staticmethod
    def _warnings(request: VinaDockingRequest) -> list[str]:
        warnings = [
            "Prepared PDBQT inputs were accepted as supplied; OSIEL did not verify protonation, tautomer, charge, missing residues, cofactors, waters or pocket choice.",
            "A negative Vina score is not a measured affinity or proof of biological activity.",
        ]
        volume = request.box.size_x * request.box.size_y * request.box.size_z
        if volume > 27_000:
            warnings.append("Docking box volume exceeds 27,000 Å³; search cost and false poses may increase.")
        if request.exhaustiveness < 8:
            warnings.append("Exhaustiveness is below the common starting value of 8; convergence may be weak.")
        return warnings

