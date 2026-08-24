from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen


COMMIT = "3c65c0b3e6c2c1d183f6a175ecb65e3c5ba91645"
FILES = {
    "1iep_receptor.pdbqt": "761469710e3915b89b274483076dfe49754be7956661bc42f4cc36a182399d59",
    "1iep_ligand.pdbqt": "37a20e58e77072c6b3ff07f285a345e647dd4e564af316a06e49518b15b7aa61",
}
BASE = f"https://raw.githubusercontent.com/ccsb-scripps/AutoDock-Vina/{COMMIT}/example/python_scripting"


def download(name: str, expected_sha256: str, destination: Path) -> None:
    request = Request(
        f"{BASE}/{name}",
        headers={"User-Agent": "Oncogon-OSIEL/0.2 Vina example fetcher"},
    )
    with urlopen(request, timeout=30) as response:
        content = response.read(5_000_001)
    if len(content) > 5_000_000:
        raise ValueError(f"{name} exceeded the 5 MB example limit")
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"checksum mismatch for {name}: expected {expected_sha256}, got {actual}")
    destination.write_bytes(content)
    print(f"verified {name} sha256:{actual}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch pinned official AutoDock Vina example inputs")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/data/vina-example"),
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, checksum in FILES.items():
        download(name, checksum, args.output / name)
    print(f"Official example ready in {args.output}")


if __name__ == "__main__":
    main()

