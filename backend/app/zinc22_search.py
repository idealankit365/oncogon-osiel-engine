from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .chemistry import ChemistryService, StructureError, chemistry
from .config import settings
from .connectors.cartblanche import CartBlancheConnector, CartBlancheError
from .repository import Repository
from .schemas import ZincCandidate, ZincSearchJob, ZincSearchRequest


class ZincSearchDisabled(RuntimeError):
    pass


class ZincSearchError(RuntimeError):
    pass


class ZincSearchInputError(ValueError):
    pass


class Zinc22SearchService:
    """Persisted public-index search plus bounded local RDKit assessment."""

    def __init__(
        self,
        repository: Repository,
        *,
        enabled: bool | None = None,
        connector: CartBlancheConnector | None = None,
        chemistry_service: ChemistryService = chemistry,
        min_poll_seconds: int | None = None,
    ) -> None:
        self.repository = repository
        self.enabled = settings.zinc22_enabled if enabled is None else enabled
        self.connector = connector
        self.chemistry = chemistry_service
        self.min_poll_seconds = (
            settings.zinc22_min_poll_seconds
            if min_poll_seconds is None
            else max(0, min_poll_seconds)
        )

    @property
    def remote(self) -> CartBlancheConnector:
        if self.connector is None:
            self.connector = CartBlancheConnector()
        return self.connector

    def capability(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "provider": "ZINC-22 / CartBlanche22",
            "search_engine": "remote SmallWorld graph search",
            "mode": "direct bounded remote query plus local RDKit triage",
            "configured_map": settings.zinc22_map,
            "max_seed_structures_per_job": 1,
            "max_imported_results_per_job": 100,
            "publication_scale": "more than 37 billion searchable 2D structures at 2023 publication",
            "publication": "https://doi.org/10.1021/acs.jcim.2c01253",
            "service": settings.zinc22_base_url,
            "local_full_index": False,
            "scientific_boundary": (
                "OSIEL does not download or scan billions locally. The public provider searches its "
                "index and OSIEL evaluates only the returned shortlist."
            ),
        }

    def submit(self, request: ZincSearchRequest, actor: str) -> ZincSearchJob:
        if not self.enabled:
            raise ZincSearchDisabled(
                "Live ZINC-22 search is disabled by the operator. Set OSIEL_ZINC22_ENABLED=true "
                "after reviewing the provider's current usage terms and configuring a contact-bearing User-Agent."
            )
        try:
            seed = self.chemistry.standardize(request.seed_smiles)
        except StructureError as exc:
            raise ZincSearchInputError(str(exc)) from exc
        try:
            remote_result = self.remote.search(
                seed.canonical_smiles,
                request.graph_distance,
                request.anonymous_distance,
                request.max_results,
            )
        except Exception as exc:
            raise ZincSearchError(
                f"SmallWorld multi-billion search failed ({type(exc).__name__})"
            ) from exc

        candidates, quarantined = self._assess(
            seed.canonical_smiles,
            remote_result.records,
            request.max_results,
        )
        now = datetime.now(UTC)
        job = ZincSearchJob(
            job_id=self.repository.new_id("ZSR"),
            remote_query_id=self.repository.new_id("SWQ"),
            status="completed",
            remote_status="SUCCESS",
            request=request,
            canonical_seed_smiles=seed.canonical_smiles,
            candidates=candidates,
            remote_returned_count=len(remote_result.records),
            quarantined_count=quarantined,
            remote_result_sha256=remote_result.response_sha256,
            index_key=remote_result.map.key,
            index_name=remote_result.map.name,
            index_entries=remote_result.map.num_entries,
            index_mapped_entries=remote_result.map.num_mapped,
            poll_after_seconds=max(3, self.min_poll_seconds),
            warnings=[
                "The provider searched the named remote map; OSIEL imported only the bounded returned shortlist.",
                "Supplier catalogue membership, price, stock, synthesis success, identity and purity are not guaranteed.",
            ],
            source_url=f"{self.remote.base_url}/search/view",
            index_scope=(
                f"Provider-reported map {remote_result.map.name}: "
                f"{remote_result.map.num_entries:,} indexed entries and "
                f"{remote_result.map.num_mapped:,} mapped/searchable entries at execution time."
            ),
            created_at=now,
            updated_at=now,
        )
        self._save(job)
        self.repository.audit(
            actor,
            "zinc22.search.completed",
            "zinc_search_job",
            job.job_id,
            {
                "remote_query_id": job.remote_query_id,
                "index_key": job.index_key,
                "index_entries": job.index_entries,
                "index_mapped_entries": job.index_mapped_entries,
                "graph_distance": request.graph_distance,
                "anonymous_distance": request.anonymous_distance,
                "max_results": request.max_results,
                "retained_count": len(candidates),
                "remote_result_sha256": job.remote_result_sha256,
            },
        )
        return job

    def get(self, job_id: str) -> ZincSearchJob | None:
        payload = self.repository.get_zinc_search_job(job_id)
        return ZincSearchJob.model_validate(payload) if payload else None

    def refresh(self, job_id: str, actor: str) -> ZincSearchJob:
        job = self.get(job_id)
        if job is None:
            raise KeyError("ZINC-22 search job not found")
        # Direct SmallWorld jobs are final when POST returns. This endpoint remains
        # stable for clients and future provider modes, but it never resubmits a query.
        return job

    def _assess(
        self,
        seed_smiles: str,
        records: list[dict[str, Any]],
        max_results: int,
    ) -> tuple[list[ZincCandidate], int]:
        unique: dict[str, dict[str, Any]] = {}
        quarantined = 0
        # Guard CPU and response variability even if a provider unexpectedly returns a huge list.
        for position, record in enumerate(records[:1000], start=1):
            raw_smiles = record.get("smiles") or record.get("canonical_smiles")
            if not isinstance(raw_smiles, str) or not raw_smiles.strip():
                quarantined += 1
                continue
            try:
                standardized = self.chemistry.standardize(raw_smiles)
                alerts = self.chemistry.medicinal_chemistry_alerts(
                    standardized.canonical_smiles
                )
                similarity = self.chemistry.similarity(
                    seed_smiles,
                    standardized.canonical_smiles,
                )
            except StructureError:
                quarantined += 1
                continue
            violations = self.chemistry.lipinski_violations(standardized.descriptors)
            alert_count = sum(len(values) for values in alerts.values())
            ro5_score = max(0.0, 1.0 - len(violations) / 4)
            alert_score = max(0.0, 1.0 - min(alert_count, 3) / 3)
            priority = round(
                100
                * (
                    0.60 * similarity
                    + 0.15 * standardized.descriptors.qed
                    + 0.15 * ro5_score
                    + 0.10 * alert_score
                ),
                2,
            )
            remote_id = str(
                record.get("remote_id")
                or record.get("zinc_id")
                or record.get("sub_id")
                or record.get("id")
                or f"REMOTE-{position}"
            )
            candidate = {
                "remote_id": remote_id,
                "source_smiles": raw_smiles,
                "canonical_smiles": standardized.canonical_smiles,
                "inchikey": standardized.inchikey,
                "tranche": str(record["tranche"]) if record.get("tranche") else None,
                "catalogs": self._catalog_names(record.get("catalogs")),
                "descriptors": standardized.descriptors,
                "similarity_to_seed": round(similarity, 4),
                "lipinski_violations": violations,
                "pains_alerts": alerts["pains"],
                "brenk_alerts": alerts["brenk"],
                "nih_alerts": alerts["nih"],
                "quality_flags": sorted(set(standardized.quality_flags)),
                "priority_score": priority,
            }
            current = unique.get(standardized.inchikey)
            if current is None or priority > current["priority_score"]:
                unique[standardized.inchikey] = candidate
        ranked = sorted(
            unique.values(),
            key=lambda item: (item["priority_score"], item["similarity_to_seed"]),
            reverse=True,
        )[:max_results]
        return [
            ZincCandidate(rank=index, **item)
            for index, item in enumerate(ranked, start=1)
        ], quarantined

    @staticmethod
    def _catalog_names(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value[:160]]
        if not isinstance(value, list):
            return []
        output: list[str] = []
        for item in value:
            if isinstance(item, str):
                output.append(item[:160])
            elif isinstance(item, dict):
                name = item.get("name") or item.get("catalog_name") or item.get("short_name")
                if name:
                    output.append(str(name)[:160])
        return sorted(set(output))[:20]

    def _save(self, job: ZincSearchJob) -> None:
        self.repository.save_zinc_search_job(job.job_id, job.status, job.model_dump(mode="json"))
