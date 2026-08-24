#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from app.repository import Repository
from app.schemas import ZincSearchRequest
from app.zinc22_search import Zinc22SearchService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one bounded live query against the configured public SmallWorld map"
    )
    parser.add_argument("--smiles", default="CC(=O)Oc1ccccc1C(=O)O", help="seed SMILES")
    parser.add_argument("--graph-distance", type=int, default=2, choices=range(4))
    parser.add_argument("--anonymous-distance", type=int, default=1, choices=range(4))
    parser.add_argument("--limit", type=int, default=25, choices=range(5, 101))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="osiel-zinc22-") as temp_directory:
        repository = Repository(Path(temp_directory) / "osiel.db")
        service = Zinc22SearchService(repository, enabled=True, min_poll_seconds=0)
        job = service.submit(
            ZincSearchRequest(
                seed_smiles=args.smiles,
                graph_distance=args.graph_distance,
                anonymous_distance=args.anonymous_distance,
                max_results=args.limit,
            ),
            "e2e-zinc22-script",
        )
        if job.status != "completed" or not job.candidates:
            raise SystemExit("Live provider returned no usable candidate shortlist")
        print(
            json.dumps(
                {
                    "scenario": "live public SmallWorld multi-billion search through OSIEL",
                    "job_id": job.job_id,
                    "remote_query_id": job.remote_query_id,
                    "index_key": job.index_key,
                    "index_name": job.index_name,
                    "index_entries": job.index_entries,
                    "index_mapped_entries": job.index_mapped_entries,
                    "remote_returned_count": job.remote_returned_count,
                    "retained_count": len(job.candidates),
                    "result_sha256": job.remote_result_sha256,
                    "top_candidates": [
                        {
                            "rank": item.rank,
                            "remote_id": item.remote_id,
                            "similarity": item.similarity_to_seed,
                            "priority_score": item.priority_score,
                        }
                        for item in job.candidates[:5]
                    ],
                    "scientific_boundary": job.scientific_boundary,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
