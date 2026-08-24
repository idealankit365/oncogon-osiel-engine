from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from rdkit import Chem, RDConfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chemistry import chemistry  # noqa: E402


CURATED = [
    ("Quercetin", "O=c1c(O)c(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12", "natural"),
    ("Luteolin", "O=c1cc(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12", "natural"),
    ("Apigenin", "O=c1cc(-c2ccc(O)cc2)oc2cc(O)cc(O)c12", "natural"),
    ("Curcumin", "COc1cc(/C=C/C(=O)CC(=O)/C=C/c2ccc(O)c(OC)c2)ccc1O", "natural"),
    ("Resveratrol", "Oc1ccc(/C=C/c2cc(O)cc(O)c2)cc1", "natural"),
    ("Catechin", "Oc1cc(O)c2c(c1)O[C@@H](c1ccc(O)c(O)c1)[C@H](O)C2", "natural"),
    ("Caffeine", "Cn1c(=O)c2c(ncn2C)n(C)c1=O", "natural"),
    ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O", "synthetic"),
    ("Acetaminophen", "CC(=O)Nc1ccc(O)cc1", "synthetic"),
    ("5-Fluorouracil", "O=c1[nH]cc(F)c(=O)[nH]1", "synthetic"),
    ("Tamoxifen", "CC/C(=C(\\c1ccccc1)c1ccc(OCCN(C)C)cc1)c1ccccc1", "synthetic"),
    ("Gefitinib", "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1", "synthetic"),
]


def record(identifier: str, name: str, smiles: str, origin: str, curated: bool) -> dict[str, object] | None:
    try:
        standardized = chemistry.standardize(smiles)
    except Exception:
        return None
    return {
        "compound_id": f"CMP-{identifier}",
        "display_name": name,
        "source_id": identifier,
        "source_name": "Curated demo panel" if curated else "NCI reference structures (RDKit sample)",
        "origin": origin,
        "canonical_smiles": standardized.canonical_smiles,
        "inchikey": standardized.inchikey,
        "descriptors": standardized.descriptors.model_dump(),
        "evidence_grade": "B" if curated else "D",
        "evidence_mode": "curated" if curated else "reference-structure",
        "aliases": [],
        "created_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    output: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, (name, smiles, origin) in enumerate(CURATED, start=1):
        item = record(f"CUR-{index:04d}", name, smiles, origin, True)
        if item and item["inchikey"] not in seen:
            output.append(item)
            seen.add(str(item["inchikey"]))

    source = Path(RDConfig.RDDataDir) / "NCI" / "first_5K.smi"
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if len(output) >= 192:
                break
            smiles, nci_id = line.strip().split()[:2]
            origin = "natural" if int(nci_id) % 4 == 0 else "synthetic"
            item = record(f"NCI-{int(nci_id):06d}", f"NCI Reference {int(nci_id):04d}", smiles, origin, False)
            if item and item["inchikey"] not in seen:
                output.append(item)
                seen.add(str(item["inchikey"]))

    target = ROOT / "app" / "data" / "compounds.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {len(output)} validated structures to {target}")


if __name__ == "__main__":
    main()

