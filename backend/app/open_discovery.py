from __future__ import annotations

import importlib.util
import shutil
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from .chemistry import ChemistryService, StructureError, chemistry
from .config import settings
from .connectors.chembl import ChEMBLConnector
from .connectors.open_targets import OpenTargetsConnector
from .connectors.pubchem import PubChemConnector
from .connectors.structures import AlphaFoldConnector, RCSBConnector
from .repository import Repository
from .schemas import (
    CandidateAssessment,
    CandidateScoreComponent,
    Compound,
    DockingReadiness,
    OpenDiscoveryRequest,
    OpenDiscoveryRun,
    SourceEvidence,
    StandardizedCompound,
    WorkflowEvent,
)


CLAIM_BOUNDARY = (
    "This run prioritizes structures for human review using similarity and medicinal-chemistry "
    "heuristics. It does not predict target binding, cellular efficacy, safety, synthesize a "
    "compound, execute docking, or perform a wet-lab experiment."
)


@dataclass(frozen=True)
class _CandidateRecord:
    compound_id: str
    display_name: str
    source_name: str
    source_record_id: str
    smiles: str
    evidence_grade: str


class OpenDiscoveryService:
    """Traceable public-source analogue triage for the OSIEL research demo.

    The workflow deliberately separates target/structure evidence retrieval from the
    chemistry-only priority score. This prevents a disease label from being presented
    as if it had changed a model prediction when no validated target-specific model ran.
    """

    def __init__(
        self,
        repository: Repository,
        *,
        chemistry_service: ChemistryService = chemistry,
        allow_public_connectors: bool | None = None,
        detect_vina: bool = True,
        chembl: ChEMBLConnector | None = None,
        pubchem: PubChemConnector | None = None,
        open_targets: OpenTargetsConnector | None = None,
        rcsb: RCSBConnector | None = None,
        alphafold: AlphaFoldConnector | None = None,
    ) -> None:
        self.repository = repository
        self.chemistry = chemistry_service
        self.allow_public_connectors = (
            settings.public_connectors_enabled
            if allow_public_connectors is None
            else allow_public_connectors
        )
        self.vina_path = None
        if detect_vina:
            self.vina_path = (
                "python:vina"
                if importlib.util.find_spec("vina") is not None
                else shutil.which("vina")
            )
        # Keep network clients lazy so offline/test deployments never initialize proxy
        # transports or sockets merely by importing the FastAPI application.
        self.chembl = chembl
        self.pubchem = pubchem
        self.open_targets = open_targets
        self.rcsb = rcsb
        self.alphafold = alphafold

    @property
    def chembl_connector(self) -> ChEMBLConnector:
        if self.chembl is None:
            self.chembl = ChEMBLConnector()
        return self.chembl

    @property
    def pubchem_connector(self) -> PubChemConnector:
        if self.pubchem is None:
            self.pubchem = PubChemConnector()
        return self.pubchem

    @property
    def open_targets_connector(self) -> OpenTargetsConnector:
        if self.open_targets is None:
            self.open_targets = OpenTargetsConnector()
        return self.open_targets

    @property
    def rcsb_connector(self) -> RCSBConnector:
        if self.rcsb is None:
            self.rcsb = RCSBConnector()
        return self.rcsb

    @property
    def alphafold_connector(self) -> AlphaFoldConnector:
        if self.alphafold is None:
            self.alphafold = AlphaFoldConnector()
        return self.alphafold

    def connector_status(self) -> list[dict[str, str | bool]]:
        return [
            {
                "code": "open-targets",
                "name": "Open Targets Platform",
                "purpose": "Disease and target identifier search",
                "integration": "official GraphQL API",
                "live_enabled": self.allow_public_connectors,
            },
            {
                "code": "pubchem",
                "name": "PubChem",
                "purpose": "Seed identity and structure resolution",
                "integration": "official PUG REST API",
                "live_enabled": self.allow_public_connectors,
            },
            {
                "code": "chembl",
                "name": "ChEMBL",
                "purpose": "Public structure-similarity retrieval",
                "integration": "official ChEMBL Web Services",
                "live_enabled": self.allow_public_connectors,
            },
            {
                "code": "rcsb-pdb",
                "name": "RCSB Protein Data Bank",
                "purpose": "Experimental structure metadata",
                "integration": "official Data API",
                "live_enabled": self.allow_public_connectors,
            },
            {
                "code": "alphafold-db",
                "name": "AlphaFold Protein Structure Database",
                "purpose": "Predicted structure metadata by UniProt accession",
                "integration": "official API",
                "live_enabled": self.allow_public_connectors,
            },
            {
                "code": "zinc22",
                "name": "ZINC22 / CartBlanche22",
                "purpose": "Billion-scale make-on-demand search",
                "integration": "separate asynchronous SmallWorld remote-search adapter; no crawler",
                "live_enabled": settings.zinc22_enabled,
            },
            {
                "code": "rdkit",
                "name": "RDKit",
                "purpose": "Standardization, descriptors, fingerprints and alerts",
                "integration": "local open-source computation",
                "live_enabled": True,
            },
            {
                "code": "autodock-vina",
                "name": "AutoDock Vina",
                "purpose": "Optional local docking after input qualification",
                "integration": "local executable adapter",
                "live_enabled": bool(self.vina_path),
            },
        ]

    def run(self, request: OpenDiscoveryRequest, actor: str = "demo-researcher") -> OpenDiscoveryRun:
        run_id = self.repository.new_id("ODR")
        created_at = datetime.now(UTC)
        events: list[WorkflowEvent] = []
        evidence: list[SourceEvidence] = []
        use_live = bool(request.public_connectors and self.allow_public_connectors)

        def add_evidence(
            source_code: str,
            source_name: str,
            mode: str,
            status: str,
            url: str,
            statement: str,
            licence_note: str,
            source_record_id: str | None = None,
        ) -> SourceEvidence:
            item = SourceEvidence(
                evidence_id=f"{run_id}-E{len(evidence) + 1:02d}",
                source_code=source_code,
                source_name=source_name,
                mode=mode,
                status=status,
                url=url,
                statement=statement,
                licence_note=licence_note,
                source_record_id=source_record_id,
                retrieved_at=datetime.now(UTC),
            )
            evidence.append(item)
            return item

        def add_event(
            stage: str,
            label: str,
            status: str,
            message: str,
            started: float,
            *,
            metrics: dict[str, float | int | str | bool] | None = None,
            evidence_ids: list[str] | None = None,
        ) -> None:
            events.append(
                WorkflowEvent(
                    sequence=len(events) + 1,
                    stage=stage,
                    label=label,
                    status=status,
                    message=message,
                    duration_ms=max(0, int((time.perf_counter() - started) * 1000)),
                    metrics=metrics or {},
                    evidence_ids=evidence_ids or [],
                )
            )

        # 1. Resolve target and disease labels without manufacturing an association claim.
        started = time.perf_counter()
        target_evidence_ids: list[str] = []
        target_status = "completed"
        target_message = "Public target-evidence search is available as a governed link-out."
        target_url = f"https://platform.opentargets.org/search?q={quote(request.disease)}"
        if use_live:
            try:
                disease_hits = self.open_targets_connector.search(request.disease, entity="disease")
                target_hits = (
                    self.open_targets_connector.search(request.target_symbol, entity="target")
                    if request.target_symbol
                    else []
                )
                resolved = add_evidence(
                    "open-targets",
                    "Open Targets Platform",
                    "official-api",
                    "resolved" if disease_hits or target_hits else "available",
                    target_url,
                    (
                        f"Resolved {len(disease_hits)} disease and {len(target_hits)} target search hits. "
                        "No association score was inferred."
                    ),
                    "Open data; preserve API retrieval time and upstream evidence provenance.",
                    ",".join([item.entity_id for item in [*disease_hits[:1], *target_hits[:1]]]) or None,
                )
                target_evidence_ids.append(resolved.evidence_id)
                target_message = resolved.statement
            except Exception as exc:  # external APIs must degrade without hiding the failure
                target_status = "completed-with-warning"
                failed = add_evidence(
                    "open-targets",
                    "Open Targets Platform",
                    "official-api",
                    "failed",
                    target_url,
                    f"Live identifier search failed: {type(exc).__name__}.",
                    "Open data; preserve API retrieval time and upstream evidence provenance.",
                )
                target_evidence_ids.append(failed.evidence_id)
                target_message = "Live Open Targets lookup failed; the workflow continued without target evidence."
        else:
            available = add_evidence(
                "open-targets",
                "Open Targets Platform",
                "link-out",
                "deferred",
                target_url,
                "Official target-evidence search link prepared; no association data were retrieved in this run.",
                "Open data; preserve evidence-level provenance and retrieval date.",
            )
            target_evidence_ids.append(available.evidence_id)
            if request.public_connectors and not self.allow_public_connectors:
                target_status = "completed-with-warning"
                target_message = "Live public APIs were requested but are disabled by the server operator."
        add_event(
            "target-evidence",
            "Resolve disease and target evidence",
            target_status,
            target_message,
            started,
            metrics={"live_api": use_live, "target_supplied": bool(request.target_symbol)},
            evidence_ids=target_evidence_ids,
        )

        # 2. Resolve experimental/predicted structure metadata when identifiers are supplied.
        started = time.perf_counter()
        structure_ids: list[str] = []
        structure_status = "skipped"
        structure_message = "No PDB ID or UniProt accession supplied; receptor preparation remains unresolved."
        if request.pdb_id:
            structure_status = "completed"
            url = f"https://www.rcsb.org/structure/{request.pdb_id.upper()}"
            if use_live:
                try:
                    item = self.rcsb_connector.entry(request.pdb_id)
                    ev = add_evidence(
                        "rcsb-pdb",
                        "RCSB Protein Data Bank",
                        "official-api",
                        "resolved",
                        url,
                        f"Resolved {item.pdb_id}: {item.title}; resolution {item.resolution_angstrom or 'not reported'} Å.",
                        "Public archive; cite the structure and primary deposition.",
                        item.pdb_id,
                    )
                    structure_message = ev.statement
                except Exception as exc:
                    structure_status = "completed-with-warning"
                    ev = add_evidence(
                        "rcsb-pdb",
                        "RCSB Protein Data Bank",
                        "official-api",
                        "failed",
                        url,
                        f"Live structure lookup failed: {type(exc).__name__}.",
                        "Public archive; cite the structure and primary deposition.",
                        request.pdb_id.upper(),
                    )
                    structure_message = "RCSB metadata could not be retrieved; the supplied PDB ID remains unqualified."
            else:
                ev = add_evidence(
                    "rcsb-pdb",
                    "RCSB Protein Data Bank",
                    "link-out",
                    "available",
                    url,
                    "Experimental structure link recorded; file preparation was not performed.",
                    "Public archive; cite the structure and primary deposition.",
                    request.pdb_id.upper(),
                )
                structure_message = ev.statement
            structure_ids.append(ev.evidence_id)
        elif request.uniprot_accession:
            structure_status = "completed"
            url = f"https://alphafold.ebi.ac.uk/entry/{request.uniprot_accession.upper()}"
            if use_live:
                try:
                    item = self.alphafold_connector.prediction(request.uniprot_accession)
                    ev = add_evidence(
                        "alphafold-db",
                        "AlphaFold Protein Structure Database",
                        "official-api",
                        "resolved",
                        url,
                        f"Resolved predicted model {item.entry_id}; confidence must be inspected residue by residue.",
                        "Use under AlphaFold DB terms; cite the database and underlying model.",
                        item.entry_id,
                    )
                    structure_message = ev.statement
                except Exception as exc:
                    structure_status = "completed-with-warning"
                    ev = add_evidence(
                        "alphafold-db",
                        "AlphaFold Protein Structure Database",
                        "official-api",
                        "failed",
                        url,
                        f"Live prediction lookup failed: {type(exc).__name__}.",
                        "Use under AlphaFold DB terms; cite the database and underlying model.",
                        request.uniprot_accession.upper(),
                    )
                    structure_message = "AlphaFold metadata could not be retrieved; no model was downloaded."
            else:
                ev = add_evidence(
                    "alphafold-db",
                    "AlphaFold Protein Structure Database",
                    "link-out",
                    "available",
                    url,
                    "Predicted-structure link recorded; pLDDT and pocket suitability were not assessed.",
                    "Use under AlphaFold DB terms; cite the database and underlying model.",
                    request.uniprot_accession.upper(),
                )
                structure_message = ev.statement
            structure_ids.append(ev.evidence_id)
        add_event(
            "structure-resolution",
            "Resolve target structure",
            structure_status,
            structure_message,
            started,
            evidence_ids=structure_ids,
        )

        # 3. Resolve and standardize the seed ligand.
        started = time.perf_counter()
        seed, seed_name, seed_source = self._resolve_seed(request, use_live)
        seed_evidence = add_evidence(**seed_source)
        add_event(
            "seed-resolution",
            "Resolve and standardize seed ligand",
            "completed",
            f"{seed_name} standardized to {seed.inchikey}; {len(seed.quality_flags)} quality flags.",
            started,
            metrics={
                "molecular_weight": seed.descriptors.molecular_weight,
                "qed": seed.descriptors.qed,
                "quality_flags": len(seed.quality_flags),
            },
            evidence_ids=[seed_evidence.evidence_id],
        )

        # 4. Search local structures and optionally retrieve ChEMBL analogues.
        started = time.perf_counter()
        records = self._local_candidates()
        analog_evidence_ids: list[str] = []
        analog_status = "completed"
        analog_message = f"Scanned {len(records)} standardized local reference structures."
        if use_live:
            try:
                external = self.chembl_connector.similar_molecules(
                    seed.canonical_smiles,
                    minimum_similarity_percent=60,
                    limit=min(100, request.candidate_limit * 4),
                )
                added = 0
                for item in external:
                    if not item.canonical_smiles:
                        continue
                    records.append(
                        _CandidateRecord(
                            compound_id=item.molecule_chembl_id,
                            display_name=item.preferred_name or item.molecule_chembl_id,
                            source_name="ChEMBL",
                            source_record_id=item.molecule_chembl_id,
                            smiles=item.canonical_smiles,
                            evidence_grade="B",
                        )
                    )
                    added += 1
                chembl_ev = add_evidence(
                    "chembl",
                    "ChEMBL",
                    "official-api",
                    "resolved",
                    "https://www.ebi.ac.uk/chembl/",
                    f"Retrieved {added} similarity records at a 60% service threshold.",
                    "Preserve the ChEMBL release, molecule IDs and assay-level provenance.",
                )
                analog_evidence_ids.append(chembl_ev.evidence_id)
                analog_message = f"Combined {len(records) - added} local structures with {added} ChEMBL records."
            except Exception as exc:
                analog_status = "completed-with-warning"
                chembl_ev = add_evidence(
                    "chembl",
                    "ChEMBL",
                    "official-api",
                    "failed",
                    "https://www.ebi.ac.uk/chembl/",
                    f"Live similarity lookup failed: {type(exc).__name__}.",
                    "Preserve the ChEMBL release, molecule IDs and assay-level provenance.",
                )
                analog_evidence_ids.append(chembl_ev.evidence_id)
                analog_message = "ChEMBL was unavailable; local reference structures were used."
        local_ev = add_evidence(
            "osiel-registry",
            "OSIEL standardized reference registry",
            "local-registry",
            "resolved",
            "https://pubchem.ncbi.nlm.nih.gov/",
            f"Loaded {len(self._local_candidates())} versioned local structures with upstream source IDs.",
            "Local records retain their upstream source labels; registry membership is not activity evidence.",
        )
        zinc_ev = add_evidence(
            "zinc22",
            "ZINC22 / CartBlanche22",
            "link-out",
            "deferred",
            "https://cartblanche22.docking.org/",
            "Billion-scale follow-up search is registered but was not crawled or downloaded in this run.",
            "Follow server usage rules; prefer an approved export or institutional deployment for scale.",
        )
        analog_evidence_ids.extend([local_ev.evidence_id, zinc_ev.evidence_id])
        add_event(
            "analogue-search",
            "Retrieve structural analogues",
            analog_status,
            analog_message,
            started,
            metrics={"candidate_records": len(records), "live_api": use_live},
            evidence_ids=analog_evidence_ids,
        )

        # 5–7. Standardize, flag and transparently prioritize candidates.
        started = time.perf_counter()
        standardized, quarantined = self._standardize_and_deduplicate(records, seed)
        add_event(
            "standardization",
            "Standardize and deduplicate candidates",
            "completed-with-warning" if quarantined else "completed",
            f"Resolved {len(standardized)} unique parent structures; quarantined {quarantined} invalid records.",
            started,
            metrics={"unique_structures": len(standardized), "quarantined": quarantined},
        )

        started = time.perf_counter()
        assessments = self._assess_candidates(
            seed,
            standardized,
            candidate_limit=request.candidate_limit,
        )
        flagged = sum(
            bool(item.pains_alerts or item.brenk_alerts or item.nih_alerts)
            for item in assessments
        )
        add_event(
            "medchem-alerts",
            "Evaluate medicinal-chemistry alerts",
            "completed-with-warning" if flagged else "completed",
            f"RDKit PAINS, Brenk and NIH catalogues flagged {flagged} of {len(assessments)} displayed candidates for review.",
            started,
            metrics={"displayed": len(assessments), "flagged": flagged},
        )

        started = time.perf_counter()
        add_event(
            "transparent-ranking",
            "Rank screening candidates",
            "completed",
            "Applied a documented chemistry-priority formula; no disease-specific efficacy model was run.",
            started,
            metrics={
                "ranked": len(assessments),
                "prioritize": sum(item.disposition == "prioritize" for item in assessments),
                "review": sum(item.disposition == "review" for item in assessments),
            },
        )

        # 8. Build a non-executing docking manifest and expose every missing prerequisite.
        started = time.perf_counter()
        docking = self._docking_readiness(request, assessments)
        add_event(
            "docking-readiness",
            "Check AutoDock Vina prerequisites",
            "completed-with-warning",
            f"Docking was not run; {len(docking.missing_inputs)} prerequisite groups remain unresolved.",
            started,
            metrics={
                "vina_detected": docking.executable_detected,
                "missing_inputs": len(docking.missing_inputs),
                "docking_executed": False,
            },
        )

        # 9. Prepare lawful procurement/search hand-offs rather than automating a purchase.
        started = time.perf_counter()
        procurement = add_evidence(
            "chemspace",
            "Chemspace",
            "link-out",
            "available",
            "https://chem-space.com/",
            "Supplier search hand-off prepared; availability, salt form, price and lead time were not resolved.",
            "API access requires an approved key and compliance with current provider terms.",
        )
        add_event(
            "procurement-handoff",
            "Prepare sourcing hand-off",
            "completed-with-warning",
            "No order was placed. A scientist must verify identity, form, purity, supplier and institutional approval.",
            started,
            evidence_ids=[procurement.evidence_id],
        )

        # 10. Enforce the human review gate.
        started = time.perf_counter()
        add_event(
            "review-gate",
            "Require scientific review",
            "completed",
            "Candidate selection, docking interpretation and wet-lab execution remain human-controlled decisions.",
            started,
            metrics={"automatic_order": False, "automatic_lab_execution": False},
        )

        run_status = (
            "completed-with-warning"
            if any(item.status == "completed-with-warning" for item in events)
            else "completed"
        )
        run = OpenDiscoveryRun(
            run_id=run_id,
            status=run_status,
            execution_mode="local-python-plus-public-apis" if use_live else "local-python",
            request=request,
            seed=seed,
            seed_name=seed_name,
            events=events,
            evidence=evidence,
            candidates=assessments,
            docking=docking,
            next_actions=[
                "Review the top structures, alert matches and score components with a medicinal chemist.",
                "Resolve an experimental PDB structure where possible; otherwise inspect AlphaFold confidence and pocket suitability.",
                "Run an approved ZINC22/CartBlanche or supplier search to expand beyond the local reference panel.",
                "Prepare receptor and ligand files, validate the docking box against a co-crystal, then run and benchmark Vina separately.",
                "Order only after identity, stereochemistry, salt form, purity, availability, budget and institutional safety approval are verified.",
            ],
            claim_boundary=CLAIM_BOUNDARY,
            created_at=created_at,
        )
        self.repository.save_open_discovery_run(
            run.run_id,
            run.status,
            run.model_dump(mode="json"),
        )
        self.repository.audit(
            actor,
            "open_discovery.completed",
            "open_discovery_run",
            run.run_id,
            {
                "status": run.status,
                "execution_mode": run.execution_mode,
                "candidate_count": len(run.candidates),
                "docking_executed": False,
                "public_connectors_requested": request.public_connectors,
            },
        )
        return run

    def _resolve_seed(
        self,
        request: OpenDiscoveryRequest,
        use_live: bool,
    ) -> tuple[StandardizedCompound, str, dict[str, Any]]:
        if request.seed_smiles:
            standardized = self.chemistry.standardize(request.seed_smiles)
            return standardized, request.seed_compound_name or "User-supplied seed", {
                "source_code": "user-input",
                "source_name": "User-supplied structure",
                "mode": "local-registry",
                "status": "resolved",
                "url": "https://www.rdkit.org/",
                "statement": "User-supplied SMILES parsed, parent-standardized and fingerprinted locally with RDKit.",
                "licence_note": "The user is responsible for structure rights, identity and provenance.",
                "source_record_id": None,
            }

        name = (request.seed_compound_name or "").strip()
        matches = self.repository.list_compounds(limit=50, query=name)
        local = next(
            (item for item in matches if item.display_name.casefold() == name.casefold()),
            matches[0] if matches else None,
        )
        if local:
            return self.chemistry.standardize(local.canonical_smiles), local.display_name, {
                "source_code": "osiel-registry",
                "source_name": local.source_name,
                "mode": "local-registry",
                "status": "resolved",
                "url": self._compound_source_url(local),
                "statement": f"Resolved local record {local.compound_id} with upstream ID {local.source_id}.",
                "licence_note": "Local reference provenance must be checked against the named upstream source before reuse.",
                "source_record_id": local.source_id,
            }
        if use_live:
            item = self.pubchem_connector.compound_by_name(name)
            return self.chemistry.standardize(item.isomeric_smiles or item.canonical_smiles), item.title, {
                "source_code": "pubchem",
                "source_name": "PubChem",
                "mode": "official-api",
                "status": "resolved",
                "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{item.cid}",
                "statement": f"Resolved PubChem CID {item.cid} through PUG REST and standardized it locally.",
                "licence_note": "Public resource; follow NCBI usage policies and retain CID plus retrieval date.",
                "source_record_id": str(item.cid),
            }
        raise ValueError(
            f"Seed compound '{name}' is not in the local registry. Supply seed_smiles or enable "
            "both request.public_connectors and OSIEL_PUBLIC_CONNECTORS_ENABLED."
        )

    def _local_candidates(self) -> list[_CandidateRecord]:
        return [
            _CandidateRecord(
                compound_id=item.compound_id,
                display_name=item.display_name,
                source_name=item.source_name,
                source_record_id=item.source_id,
                smiles=item.canonical_smiles,
                evidence_grade=item.evidence_grade,
            )
            for item in self.repository.list_compounds(limit=200)
        ]

    def _standardize_and_deduplicate(
        self,
        records: list[_CandidateRecord],
        seed: StandardizedCompound,
    ) -> tuple[list[tuple[_CandidateRecord, StandardizedCompound, float]], int]:
        unique: dict[str, tuple[_CandidateRecord, StandardizedCompound, float]] = {}
        quarantined = 0
        for record in records:
            try:
                standardized = self.chemistry.standardize(record.smiles)
                if standardized.inchikey == seed.inchikey:
                    continue
                similarity = self.chemistry.similarity(
                    seed.canonical_smiles,
                    standardized.canonical_smiles,
                )
                current = unique.get(standardized.inchikey)
                if current is None or similarity > current[2]:
                    unique[standardized.inchikey] = (record, standardized, similarity)
            except StructureError:
                quarantined += 1
        return sorted(unique.values(), key=lambda item: item[2], reverse=True), quarantined

    def _assess_candidates(
        self,
        seed: StandardizedCompound,
        standardized: list[tuple[_CandidateRecord, StandardizedCompound, float]],
        *,
        candidate_limit: int,
    ) -> list[CandidateAssessment]:
        scored: list[dict[str, Any]] = []
        # Alert matching is comparatively expensive; retain a broad similarity window first.
        window = standardized[: max(candidate_limit * 4, 40)]
        for record, item, similarity in window:
            alerts = self.chemistry.medicinal_chemistry_alerts(item.canonical_smiles)
            violations = self.chemistry.lipinski_violations(item.descriptors)
            alert_count = len(alerts["pains"]) + len(alerts["brenk"]) + len(alerts["nih"])
            ro5_value = max(0.0, 1.0 - len(violations) / 4)
            alert_value = max(0.0, 1.0 - min(alert_count, 3) / 3)
            grade_value = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25}.get(
                record.evidence_grade,
                0.25,
            )
            components = [
                CandidateScoreComponent(
                    code="seed-similarity",
                    label="Seed similarity",
                    normalized_value=round(similarity, 4),
                    weight=0.45,
                    contribution=round(similarity * 45, 2),
                    explanation="ECFP4-like Morgan Tanimoto similarity; useful for analogue triage, not binding proof.",
                ),
                CandidateScoreComponent(
                    code="qed",
                    label="QED",
                    normalized_value=round(item.descriptors.qed, 4),
                    weight=0.20,
                    contribution=round(item.descriptors.qed * 20, 2),
                    explanation="RDKit quantitative estimate of drug-likeness; a heuristic, not an efficacy endpoint.",
                ),
                CandidateScoreComponent(
                    code="lipinski",
                    label="Rule-of-Five adherence",
                    normalized_value=round(ro5_value, 4),
                    weight=0.15,
                    contribution=round(ro5_value * 15, 2),
                    explanation=f"{len(violations)} classic oral drug-likeness threshold flags.",
                ),
                CandidateScoreComponent(
                    code="alerts",
                    label="Alert burden",
                    normalized_value=round(alert_value, 4),
                    weight=0.10,
                    contribution=round(alert_value * 10, 2),
                    explanation=f"{alert_count} PAINS/Brenk/NIH catalogue matches; matches require expert review.",
                ),
                CandidateScoreComponent(
                    code="source-evidence",
                    label="Source evidence completeness",
                    normalized_value=grade_value,
                    weight=0.10,
                    contribution=round(grade_value * 10, 2),
                    explanation=f"OSIEL source grade {record.evidence_grade}; grade is provenance completeness, not biological activity.",
                ),
            ]
            score = round(sum(component.contribution for component in components), 2)
            quality_flags = list(item.quality_flags)
            if item.stereo_status == "undefined":
                quality_flags.append("undefined-stereochemistry")
            if score >= 65 and len(violations) <= 1 and alert_count == 0:
                disposition = "prioritize"
                reason = "Strong seed similarity and chemistry heuristics with no catalogue alerts."
            elif score < 35 or len(violations) >= 2 or alert_count >= 3:
                disposition = "deprioritize"
                reason = "Low combined chemistry score or multiple review flags; retain for audit, not automatic deletion."
            else:
                disposition = "review"
                reason = "Potential analogue with one or more uncertainty, alert or property checks requiring expert review."
            scored.append(
                {
                    "record": record,
                    "item": item,
                    "similarity": similarity,
                    "violations": violations,
                    "alerts": alerts,
                    "quality_flags": sorted(set(quality_flags)),
                    "score": score,
                    "components": components,
                    "disposition": disposition,
                    "reason": reason,
                }
            )
        scored.sort(key=lambda value: (value["score"], value["similarity"]), reverse=True)
        output: list[CandidateAssessment] = []
        for rank, value in enumerate(scored[:candidate_limit], start=1):
            record = value["record"]
            item = value["item"]
            output.append(
                CandidateAssessment(
                    rank=rank,
                    compound_id=record.compound_id,
                    display_name=record.display_name,
                    source_name=record.source_name,
                    source_record_id=record.source_record_id,
                    canonical_smiles=item.canonical_smiles,
                    inchikey=item.inchikey,
                    similarity_to_seed=round(value["similarity"], 4),
                    descriptors=item.descriptors,
                    lipinski_violations=value["violations"],
                    pains_alerts=value["alerts"]["pains"],
                    brenk_alerts=value["alerts"]["brenk"],
                    nih_alerts=value["alerts"]["nih"],
                    quality_flags=value["quality_flags"],
                    priority_score=value["score"],
                    score_components=value["components"],
                    disposition=value["disposition"],
                    disposition_reason=value["reason"],
                )
            )
        if not output:
            raise ValueError("No valid non-seed candidate structures were available for prioritization")
        return output

    def _docking_readiness(
        self,
        request: OpenDiscoveryRequest,
        assessments: list[CandidateAssessment],
    ) -> DockingReadiness:
        required = [
            "qualified receptor structure and prepared receptor PDBQT",
            "protonated 3D ligand states and prepared ligand PDBQT files",
            "validated docking-box centre and dimensions",
            "positive-control redocking benchmark and acceptance threshold",
            "recorded Vina version, exhaustiveness and random seed",
        ]
        missing = list(required)
        if not self.vina_path:
            missing.append("AutoDock Vina executable on the worker PATH")
        if not settings.vina_enabled:
            missing.append("server operator gate OSIEL_VINA_ENABLED=true")
        receptor_reference = request.pdb_id or request.uniprot_accession
        return DockingReadiness(
            status="not-run",
            executable_detected=bool(self.vina_path),
            receptor_id=receptor_reference,
            required_inputs=required,
            missing_inputs=missing,
            run_manifest={
                "execute": False,
                "target_symbol": request.target_symbol,
                "receptor_reference": receptor_reference,
                "candidate_count": len(assessments),
                "exhaustiveness": 8,
                "random_seed": 20260822,
                "vina_path": self.vina_path,
            },
            result_score_kcal_mol=None,
            scientific_boundary=(
                "No affinity value is emitted until a real Vina process completes with qualified inputs. "
                "Even then, a docking score is an approximate pose-ranking result, not evidence of efficacy."
            ),
        )

    @staticmethod
    def _compound_source_url(compound: Compound) -> str:
        if "pubchem" in compound.source_name.casefold():
            return f"https://pubchem.ncbi.nlm.nih.gov/compound/{quote(compound.source_id)}"
        if compound.source_id.upper().startswith("CHEMBL"):
            return f"https://www.ebi.ac.uk/chembl/explore/compound/{quote(compound.source_id)}"
        return "https://pubchem.ncbi.nlm.nih.gov/"
