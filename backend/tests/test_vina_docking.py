from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.immutable_storage import ImmutableObjectStore
from app.main import app
from app.repository import Repository
from app.schemas import DockingBox, VinaDockingRequest
from app.vina_docking import DockingInputError, VinaDisabledError, VinaDockingService


requires_vina = pytest.mark.skipif(
    not VinaDockingService.binding_available(),
    reason="optional AutoDock Vina binding is unavailable on this host",
)


RECEPTOR = b"""REMARK synthetic software-test receptor only
ATOM      1  C1  REC A   1       0.000   0.000   0.000  1.00  0.00     0.000 C
END
"""

LIGAND = b"""REMARK synthetic software-test ligand only
ROOT
HETATM    1  C1  LIG A   1       1.000   1.000   1.000  1.00  0.00     0.000 C
ENDROOT
TORSDOF 0
"""


def encoded(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def request(**overrides: object) -> VinaDockingRequest:
    payload: dict[str, object] = {
        "receptor_filename": "receptor.pdbqt",
        "receptor_content_base64": encoded(RECEPTOR),
        "ligand_filename": "ligand.pdbqt",
        "ligand_content_base64": encoded(LIGAND),
        "box": DockingBox(
            center_x=0,
            center_y=0,
            center_z=0,
            size_x=20,
            size_y=20,
            size_z=20,
        ),
        "exhaustiveness": 8,
        "num_modes": 3,
        "cpu": 1,
        "timeout_seconds": 60,
    }
    payload.update(overrides)
    return VinaDockingRequest.model_validate(payload)


def successful_runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
    output = Path(command[command.index("--output") + 1])
    output.write_text(
        "MODEL 1\nREMARK VINA RESULT: -7.500 0.000 0.000\nENDMDL\n",
        encoding="utf-8",
    )
    return subprocess.CompletedProcess(
        command,
        0,
        stdout=json.dumps({"engine_version": "1.2.7", "energies": [[-7.5, -8.2, 0, 0.7, 0]]}),
        stderr="",
    )


@requires_vina
def test_vina_job_persists_real_worker_contract_without_shell(
    repository: Repository,
    tmp_path: Path,
) -> None:
    service = VinaDockingService(
        repository,
        store=ImmutableObjectStore(tmp_path / "objects"),
        enabled=True,
        runner=successful_runner,
    )
    result = service.run(request(), "test-researcher")

    assert result.status == "completed"
    assert result.engine_version == "1.2.7"
    assert result.poses[0].affinity_kcal_mol == -7.5
    assert result.output_sha256
    assert result.output_pdbqt_base64
    assert result.command_manifest[0].endswith("-m app.vina_worker")
    assert all("/tmp/" not in item for item in result.command_manifest)
    assert repository.get_docking_job(result.job_id) is not None


def test_vina_operator_gate_is_enforced(repository: Repository) -> None:
    service = VinaDockingService(repository, enabled=False)
    with pytest.raises(VinaDisabledError, match="disabled by the server operator"):
        service.run(request(), "test-researcher")


@requires_vina
def test_vina_rejects_unprepared_ligand(repository: Repository, tmp_path: Path) -> None:
    service = VinaDockingService(
        repository,
        store=ImmutableObjectStore(tmp_path / "objects"),
        enabled=True,
        runner=successful_runner,
    )
    bad = request(ligand_content_base64=encoded(b"HETATM    1  C\n"))
    with pytest.raises(DockingInputError, match="missing required markers"):
        service.run(bad, "test-researcher")


@requires_vina
def test_vina_timeout_is_recorded(repository: Repository, tmp_path: Path) -> None:
    def timed_out(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, 10)

    service = VinaDockingService(
        repository,
        store=ImmutableObjectStore(tmp_path / "objects"),
        enabled=True,
        runner=timed_out,
    )
    result = service.run(request(), "test-researcher")
    assert result.status == "timed-out"
    assert result.poses == []
    assert "timeout" in (result.error or "")


def test_vina_api_reports_disabled_default() -> None:
    client = TestClient(app)
    capability = client.get("/v1/docking/capabilities")
    assert capability.status_code == 200
    assert capability.json()["binding_available"] is VinaDockingService.binding_available()
    assert capability.json()["operator_enabled"] is False

    response = client.post("/v1/docking/jobs", json=request().model_dump(mode="json"))
    assert response.status_code == 503
