from __future__ import annotations

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.conformer import CONFORMER_SEED, CompoundConformerService
from app.immutable_storage import ImmutableObjectStore
from app.repository import Repository


COMPOUND_IDS = [
    "CMP-CUR-0001",
    "CMP-CUR-0002",
    "CMP-CUR-0004",
    "CMP-CUR-0006",
    "CMP-CUR-0012",
    "CMP-CUR-0010",
    "CMP-CUR-0005",
    "CMP-NCI-000012",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify deterministic OSIEL 3D conformers")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="osiel-conformer-e2e-") as temporary:
        root = Path(temporary)
        repository = Repository(root / "conformers.db")
        repository.seed(settings.seed_path)
        store = ImmutableObjectStore(root / "objects")
        service = CompoundConformerService(repository, store)
        records = [service.generate(compound_id, actor="conformer-e2e") for compound_id in COMPOUND_IDS]
        repeated = service.generate(COMPOUND_IDS[0], actor="conformer-e2e-repeat")
        assert repeated.sha256 == records[0].sha256
        assert repeated.mol_block == records[0].mol_block
        for item in records:
            assert store.get(item.object_uri).decode("utf-8") == item.mol_block
            assert item.random_seed == CONFORMER_SEED
            assert "V2000" in item.mol_block

        report = {
            "report_version": "1.0",
            "executed_at": datetime.now(UTC).isoformat(),
            "scenario": "registered canonical SMILES to deterministic interactive 3D conformer",
            "coordinate_method": "RDKit ETKDGv3",
            "random_seed": CONFORMER_SEED,
            "records": [
                {
                    "compound_id": item.compound_id,
                    "display_name": item.display_name,
                    "optimization_method": item.optimization_method,
                    "optimization_converged": item.optimization_converged,
                    "energy_kcal_mol": item.conformer_energy_kcal_mol,
                    "atom_count": item.atom_count,
                    "heavy_atom_count": item.heavy_atom_count,
                    "sha256": item.sha256,
                    "immutable_read_verified": True,
                }
                for item in records
            ],
            "deterministic_repeat_verified": True,
            "viewer": "3Dmol.js 2.5.5 with rotation, wheel/pinch zoom, camera controls, representations and colour schemes",
            "verified": True,
            "scientific_boundary": records[0].scientific_boundary,
        }
        rendered = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")


if __name__ == "__main__":
    main()
