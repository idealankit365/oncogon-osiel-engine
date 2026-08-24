from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import (
    Crippen,
    Descriptors,
    FilterCatalog,
    Lipinski,
    rdFingerprintGenerator,
    rdMolDescriptors,
)
from rdkit.Chem.MolStandardize import rdMolStandardize

from .config import settings
from .schemas import DescriptorSet, StandardizedCompound


class StructureError(ValueError):
    """Raised when a submitted molecular structure cannot be safely interpreted."""


@dataclass(frozen=True)
class Fingerprint:
    value: object
    version: str


class ChemistryService:
    def __init__(self) -> None:
        self._fingerprinter = rdFingerprintGenerator.GetMorganGenerator(
            radius=2, fpSize=2048, includeChirality=True
        )
        self._alert_catalogs = {
            "pains": self._filter_catalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS),
            "brenk": self._filter_catalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK),
            "nih": self._filter_catalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.NIH),
        }

    @staticmethod
    def _filter_catalog(catalog: object) -> FilterCatalog.FilterCatalog:
        params = FilterCatalog.FilterCatalogParams()
        params.AddCatalog(catalog)
        return FilterCatalog.FilterCatalog(params)

    def standardize(self, raw_smiles: str) -> StandardizedCompound:
        raw_smiles = raw_smiles.strip()
        molecule = Chem.MolFromSmiles(raw_smiles)
        if molecule is None:
            raise StructureError("SMILES parsing failed; record must be quarantined")

        transformations: list[str] = ["parsed", "sanitized"]
        quality_flags: list[str] = []
        raw_fragments = Chem.GetMolFrags(molecule)
        cleaned = rdMolStandardize.Cleanup(molecule)
        parent = rdMolStandardize.FragmentParent(cleaned)
        parent = rdMolStandardize.Uncharger().uncharge(parent)
        Chem.SanitizeMol(parent)

        if len(raw_fragments) > 1:
            transformations.append("fragment-parent-derived")
            quality_flags.append("multi-fragment-input")
        if Chem.GetFormalCharge(molecule) != Chem.GetFormalCharge(parent):
            transformations.append("charge-normalized")

        canonical = Chem.MolToSmiles(parent, isomericSmiles=True, canonical=True)
        non_isomeric = Chem.MolToSmiles(parent, isomericSmiles=False, canonical=True)
        stereo_centers = Chem.FindMolChiralCenters(parent, includeUnassigned=True)
        if not stereo_centers:
            stereo_status = "none"
        elif any(label == "?" for _, label in stereo_centers):
            stereo_status = "undefined"
            quality_flags.append("undefined-stereochemistry")
        else:
            stereo_status = "defined"

        descriptors = self.descriptors(parent)
        return StandardizedCompound(
            raw_smiles=raw_smiles,
            canonical_smiles=canonical,
            parent_smiles=non_isomeric,
            inchi=Chem.MolToInchi(parent),
            inchikey=Chem.MolToInchiKey(parent),
            stereo_status=stereo_status,
            descriptors=descriptors,
            quality_flags=quality_flags,
            transformations=transformations,
            standardization_version=settings.standardization_version,
        )

    def descriptors(self, molecule: Chem.Mol) -> DescriptorSet:
        return DescriptorSet(
            molecular_formula=rdMolDescriptors.CalcMolFormula(molecule),
            molecular_weight=round(Descriptors.MolWt(molecule), 4),
            clogp=round(Crippen.MolLogP(molecule), 4),
            tpsa=round(rdMolDescriptors.CalcTPSA(molecule), 4),
            h_bond_donors=int(Lipinski.NumHDonors(molecule)),
            h_bond_acceptors=int(Lipinski.NumHAcceptors(molecule)),
            rotatable_bonds=int(Lipinski.NumRotatableBonds(molecule)),
            ring_count=int(Lipinski.RingCount(molecule)),
            fraction_csp3=round(rdMolDescriptors.CalcFractionCSP3(molecule), 4),
            qed=round(Descriptors.qed(molecule), 4),
        )

    def fingerprint(self, smiles: str) -> Fingerprint:
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            raise StructureError("Cannot fingerprint invalid molecular structure")
        return Fingerprint(self._fingerprinter.GetFingerprint(molecule), settings.feature_version)

    def similarity(self, left_smiles: str, right_smiles: str) -> float:
        from rdkit import DataStructs

        left = self.fingerprint(left_smiles).value
        right = self.fingerprint(right_smiles).value
        return float(DataStructs.TanimotoSimilarity(left, right))

    @staticmethod
    def lipinski_violations(descriptors: DescriptorSet) -> list[str]:
        """Return human-readable Rule-of-Five flags without treating them as proof of failure."""

        violations: list[str] = []
        if descriptors.molecular_weight > 500:
            violations.append("molecular weight > 500 Da")
        if descriptors.clogp > 5:
            violations.append("cLogP > 5")
        if descriptors.h_bond_donors > 5:
            violations.append("hydrogen-bond donors > 5")
        if descriptors.h_bond_acceptors > 10:
            violations.append("hydrogen-bond acceptors > 10")
        return violations

    def medicinal_chemistry_alerts(self, smiles: str) -> dict[str, list[str]]:
        """Evaluate RDKit PAINS/Brenk/NIH catalogues as review flags, not hard filters."""

        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            raise StructureError("Cannot evaluate alerts for an invalid molecular structure")
        output: dict[str, list[str]] = {}
        for code, catalog in self._alert_catalogs.items():
            descriptions = sorted({match.GetDescription() for match in catalog.GetMatches(molecule)})
            output[code] = descriptions
        return output


chemistry = ChemistryService()
