from __future__ import annotations

from pathlib import Path

import pytest

from app.conformer import CONFORMER_SEED, CompoundConformerService
from app.immutable_storage import ImmutableObjectStore
from app.repository import Repository


def test_generates_deterministic_immutable_3d_conformer(
    repository: Repository,
    tmp_path: Path,
) -> None:
    service = CompoundConformerService(
        repository,
        ImmutableObjectStore(tmp_path / "objects"),
    )
    first = service.generate("CMP-CUR-0001", actor="student-1", experiment_id="EXP-1")
    second = service.generate("CMP-CUR-0001", actor="student-1", experiment_id="EXP-1")

    assert first.random_seed == CONFORMER_SEED
    assert first.coordinate_method == "ETKDGv3"
    assert first.optimization_method in {"MMFF94", "UFF", "none"}
    assert first.atom_count > first.heavy_atom_count
    assert first.mol_block == second.mol_block
    assert first.sha256 == second.sha256
    assert first.object_uri == second.object_uri
    assert service.store.get(first.object_uri).decode("utf-8") == first.mol_block
    assert "not an experimental crystal structure" in first.scientific_boundary


def test_can_return_heavy_atoms_only(repository: Repository, tmp_path: Path) -> None:
    service = CompoundConformerService(
        repository,
        ImmutableObjectStore(tmp_path / "objects"),
    )
    conformer = service.generate("CMP-CUR-0002", include_hydrogens=False)
    assert conformer.includes_hydrogens is False
    assert conformer.atom_count == conformer.heavy_atom_count


def test_unknown_compound_is_rejected(repository: Repository, tmp_path: Path) -> None:
    service = CompoundConformerService(
        repository,
        ImmutableObjectStore(tmp_path / "objects"),
    )
    with pytest.raises(KeyError):
        service.generate("OSIEL-CMP-DOES-NOT-EXIST")
