from __future__ import annotations

import pytest

from app.chemistry import StructureError, chemistry


def test_standardization_preserves_raw_and_derives_parent() -> None:
    result = chemistry.standardize("CC[NH+](CC)CC.[Cl-]")
    assert result.raw_smiles.endswith(".[Cl-]")
    assert "." not in result.parent_smiles
    assert result.inchikey
    assert "multi-fragment-input" in result.quality_flags
    assert "fragment-parent-derived" in result.transformations


def test_invalid_structure_is_quarantinable() -> None:
    with pytest.raises(StructureError, match="quarantined"):
        chemistry.standardize("this-is-not-smiles")


def test_descriptor_contract() -> None:
    result = chemistry.standardize("CC(=O)Oc1ccccc1C(=O)O")
    assert result.descriptors.molecular_formula == "C9H8O4"
    assert 179 < result.descriptors.molecular_weight < 181
    assert result.standardization_version.startswith("OSIEL-STD")

