#!/usr/bin/env python3
"""Build the hosted viewer's real RDKit conformer bundle.

The static bundle lets the owner-only hosted UI demonstrate 3D interaction when the
separate Python API is not running. A connected API remains the primary source and
regenerates the same conformer from the canonical registry structure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.conformer import CompoundConformerService
from app.repository import repository


DEMO_MAPPING = {
    "OSIEL-CMP-0001": "CMP-CUR-0001",  # Quercetin
    "OSIEL-CMP-0002": "CMP-CUR-0002",  # Luteolin
    "OSIEL-CMP-0003": "CMP-CUR-0004",  # Curcumin
    "OSIEL-CMP-0004": "CMP-CUR-0006",  # Catechin
    "OSIEL-CMP-0005": "CMP-CUR-0012",  # Gefitinib
    "OSIEL-CMP-0006": "CMP-CUR-0010",  # 5-Fluorouracil
    "OSIEL-CMP-0007": "CMP-CUR-0005",  # Resveratrol
    "OSIEL-CMP-0012": "CMP-NCI-000012",  # NCI reference 0012
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("public/demo-conformers.json"),
    )
    args = parser.parse_args()

    repository.seed()
    service = CompoundConformerService(repository)
    records: list[dict[str, object]] = []
    for demo_id, registry_id in DEMO_MAPPING.items():
        conformer = service.generate(
            registry_id,
            include_hydrogens=True,
            actor="demo-bundle-generator",
        )
        records.append(
            {
                "compound_id": demo_id,
                "registry_compound_id": registry_id,
                "display_name": conformer.display_name,
                "canonical_smiles": conformer.canonical_smiles,
                "mol_block": conformer.mol_block,
                "format": conformer.format,
                "coordinate_method": conformer.coordinate_method,
                "optimization_method": conformer.optimization_method,
                "optimization_converged": conformer.optimization_converged,
                "conformer_energy_kcal_mol": conformer.conformer_energy_kcal_mol,
                "random_seed": conformer.random_seed,
                "includes_hydrogens": conformer.includes_hydrogens,
                "atom_count": conformer.atom_count,
                "heavy_atom_count": conformer.heavy_atom_count,
                "rdkit_version": conformer.rdkit_version,
                "sha256": conformer.sha256,
                "warnings": conformer.warnings,
                "scientific_boundary": conformer.scientific_boundary,
                "source_mode": "bundled-rdkit-reference",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"schema_version": "OSIEL-DEMO-CONFORMERS-1.0", "records": records}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} RDKit conformers to {args.output}")


if __name__ == "__main__":
    main()
