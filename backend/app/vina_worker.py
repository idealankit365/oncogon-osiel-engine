from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Isolated AutoDock Vina worker")
    value.add_argument("--receptor", required=True)
    value.add_argument("--ligand", required=True)
    value.add_argument("--output", required=True)
    value.add_argument("--scoring", choices=("vina", "vinardo"), default="vina")
    value.add_argument("--center", nargs=3, type=float, required=True)
    value.add_argument("--size", nargs=3, type=float, required=True)
    value.add_argument("--exhaustiveness", type=int, required=True)
    value.add_argument("--num-modes", type=int, required=True)
    value.add_argument("--energy-range", type=float, required=True)
    value.add_argument("--cpu", type=int, required=True)
    value.add_argument("--seed", type=int, required=True)
    return value


def restrict_process() -> None:
    """Apply portable-enough file/core limits; the parent owns the wall timeout."""

    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (50_000_000, 50_000_000))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    except (ImportError, OSError, ValueError):
        pass


def main() -> int:
    args = parser().parse_args()
    restrict_process()
    receptor = Path(args.receptor)
    ligand = Path(args.ligand)
    output = Path(args.output)
    if not receptor.is_file() or not ligand.is_file():
        print(json.dumps({"error": "worker input file is missing"}), file=sys.stderr)
        return 2

    try:
        import vina
        from vina import Vina

        engine = Vina(
            sf_name=args.scoring,
            cpu=args.cpu,
            seed=args.seed,
            verbosity=0,
        )
        engine.set_receptor(str(receptor))
        engine.set_ligand_from_file(str(ligand))
        engine.compute_vina_maps(center=args.center, box_size=args.size)
        engine.dock(exhaustiveness=args.exhaustiveness, n_poses=args.num_modes)
        engine.write_poses(
            str(output),
            n_poses=args.num_modes,
            energy_range=args.energy_range,
            overwrite=True,
        )
        energies = engine.energies(
            n_poses=args.num_modes,
            energy_range=args.energy_range,
        )
        print(
            json.dumps(
                {
                    "engine_version": vina.__version__,
                    "energies": [[round(float(item), 6) for item in row] for row in energies],
                    "output_bytes": output.stat().st_size,
                },
                separators=(",", ":"),
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": str(exc)[:2000],
                    "error_type": type(exc).__name__,
                },
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

