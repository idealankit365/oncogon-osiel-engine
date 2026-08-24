from __future__ import annotations

import math
from datetime import UTC, datetime

from rdkit import Chem, rdBase
from rdkit.Chem import AllChem

from .immutable_storage import ImmutableObjectStore, object_store
from .repository import Repository
from .schemas import CompoundConformer3D


CONFORMER_SEED = 20_260_822
MAX_OPTIMIZATION_ITERATIONS = 500


class ConformerGenerationError(ValueError):
    """Raised when a registered structure cannot produce a safe 3D conformer."""


class CompoundConformerService:
    """Generate deterministic, content-addressed RDKit conformers.

    ETKDGv3 creates one plausible low-energy geometry from the registered canonical
    SMILES. MMFF94 is preferred for local optimization, with UFF as a transparent
    fallback. The output is useful for molecular identity inspection; it is never
    promoted to experimental or protein-bound structural evidence.
    """

    def __init__(
        self,
        repository: Repository,
        store: ImmutableObjectStore | None = None,
    ) -> None:
        self.repository = repository
        self.store = store or object_store

    def generate(
        self,
        compound_id: str,
        *,
        include_hydrogens: bool = True,
        actor: str = "demo-researcher",
        experiment_id: str | None = None,
    ) -> CompoundConformer3D:
        compound = self.repository.get_compound(compound_id)
        if compound is None:
            raise KeyError(compound_id)

        parent = Chem.MolFromSmiles(compound.canonical_smiles)
        if parent is None:
            raise ConformerGenerationError("Registered canonical SMILES could not be parsed")
        molecule = Chem.AddHs(parent)
        molecule.SetProp("_Name", f"{compound.display_name} | {compound.compound_id}")

        warnings: list[str] = []
        parameters = AllChem.ETKDGv3()
        parameters.randomSeed = CONFORMER_SEED
        parameters.enforceChirality = True
        parameters.useRandomCoords = False
        status = AllChem.EmbedMolecule(molecule, parameters)
        if status != 0:
            parameters.useRandomCoords = True
            status = AllChem.EmbedMolecule(molecule, parameters)
            warnings.append("ETKDGv3 required deterministic random-coordinate fallback")
        if status != 0:
            raise ConformerGenerationError("RDKit ETKDGv3 could not generate a 3D conformer")

        optimization_method: str = "none"
        optimization_converged = False
        energy: float | None = None
        try:
            if AllChem.MMFFHasAllMoleculeParams(molecule):
                optimization_method = "MMFF94"
                result = AllChem.MMFFOptimizeMolecule(
                    molecule,
                    mmffVariant="MMFF94",
                    maxIters=MAX_OPTIMIZATION_ITERATIONS,
                )
                optimization_converged = result == 0
                properties = AllChem.MMFFGetMoleculeProperties(molecule, mmffVariant="MMFF94")
                force_field = AllChem.MMFFGetMoleculeForceField(molecule, properties)
                energy = float(force_field.CalcEnergy()) if force_field else None
            elif AllChem.UFFHasAllMoleculeParams(molecule):
                optimization_method = "UFF"
                warnings.append("MMFF94 parameters unavailable; UFF fallback used")
                result = AllChem.UFFOptimizeMolecule(
                    molecule,
                    maxIters=MAX_OPTIMIZATION_ITERATIONS,
                )
                optimization_converged = result == 0
                force_field = AllChem.UFFGetMoleculeForceField(molecule)
                energy = float(force_field.CalcEnergy()) if force_field else None
            else:
                warnings.append("No MMFF94 or UFF parameters; ETKDGv3 coordinates are unoptimized")
        except Exception as exc:  # RDKit force-field failures vary by molecule/build.
            warnings.append(f"Force-field optimization unavailable ({type(exc).__name__})")
            optimization_method = "none"
            optimization_converged = False
            energy = None

        if optimization_method != "none" and not optimization_converged:
            warnings.append(
                f"{optimization_method} did not converge within "
                f"{MAX_OPTIMIZATION_ITERATIONS} iterations"
            )
        if energy is not None and not math.isfinite(energy):
            warnings.append("Non-finite force-field energy was discarded")
            energy = None

        output = molecule if include_hydrogens else Chem.RemoveHs(molecule)
        mol_block = Chem.MolToMolBlock(
            output,
            confId=0,
            kekulize=True,
            forceV3000=False,
        )
        payload = mol_block.encode("utf-8")
        digest, object_uri = self.store.put(
            payload,
            f"{compound.compound_id}.mol",
            {
                "kind": "rdkit-conformer-3d",
                "compound_id": compound.compound_id,
                "canonical_smiles": compound.canonical_smiles,
                "coordinate_method": "ETKDGv3",
                "optimization_method": optimization_method,
                "random_seed": CONFORMER_SEED,
                "includes_hydrogens": include_hydrogens,
                "rdkit_version": rdBase.rdkitVersion,
            },
        )
        conformer = CompoundConformer3D(
            compound_id=compound.compound_id,
            display_name=compound.display_name,
            canonical_smiles=compound.canonical_smiles,
            mol_block=mol_block,
            coordinate_method="ETKDGv3",
            optimization_method=optimization_method,
            optimization_converged=optimization_converged,
            conformer_energy_kcal_mol=round(energy, 6) if energy is not None else None,
            random_seed=CONFORMER_SEED,
            includes_hydrogens=include_hydrogens,
            atom_count=output.GetNumAtoms(),
            heavy_atom_count=parent.GetNumHeavyAtoms(),
            rdkit_version=rdBase.rdkitVersion,
            sha256=digest,
            object_uri=object_uri,
            warnings=warnings,
            created_at=datetime.now(UTC),
        )
        self.repository.audit(
            actor,
            "compound.conformer_3d_generated",
            "compound",
            compound.compound_id,
            {
                "sha256": digest,
                "experiment_id": experiment_id,
                "coordinate_method": conformer.coordinate_method,
                "optimization_method": conformer.optimization_method,
                "optimization_converged": conformer.optimization_converged,
                "includes_hydrogens": include_hydrogens,
                "scientific_boundary": conformer.scientific_boundary,
            },
        )
        return conformer
