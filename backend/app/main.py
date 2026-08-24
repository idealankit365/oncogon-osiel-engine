from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from .assistant import ScientificAssistantService
from .chemistry import StructureError, chemistry
from .conformer import CompoundConformerService, ConformerGenerationError
from .config import settings
from .data_connectors import ScientificDataConnectorService
from .docking_benchmark import DockingBenchmarkInputError, DockingBenchmarkService
from .experiments import ExperimentService
from .governance import ModelGovernanceService
from .knowledge import KnowledgeIngestionDisabled, KnowledgeInputError
from .literature import search_literature
from .model_lab import (
    ModelLabDisabled,
    ModelLabInputError,
    ModelLabService,
    ModelTrainingError,
)
from .multimodal_engine import MultimodalResearchEngine
from .open_discovery import OpenDiscoveryService
from .prediction import DemoPredictionService
from .plate_reader import PlateReaderService
from .ranking import RankingService
from .repository import repository
from .security import ActorContext, require_actor
from .schemas import (
    AssistantAnswer,
    AssistantConversation,
    AssistantConversationCreate,
    AssistantEvaluationRequest,
    AssistantEvaluationRun,
    AssistantFeedback,
    AssistantFeedbackRequest,
    AssistantQuery,
    AssistantRetentionRequest,
    AssistantRetentionResult,
    ActiveLearningBatch,
    ActiveLearningRequest,
    ActivityDatasetSnapshot,
    ActivityModelPrediction,
    ActivityModelPredictionRequest,
    ActivityModelRun,
    ChEMBLActivitySnapshotRequest,
    BulkSourceFetchRequest,
    ChemspaceSearchRequest,
    Compound,
    CompoundConformer3D,
    DatasetSnapshot,
    DockingBenchmarkRequest,
    DockingBenchmarkRun,
    Experiment,
    ExperimentCreate,
    ExperimentResult,
    KnowledgeDocument,
    KnowledgeDocumentIngest,
    OpenDiscoveryRequest,
    OpenDiscoveryRun,
    Prediction,
    PredictionRequest,
    PlateReaderImportRequest,
    PlateReaderValidation,
    ProductionReadiness,
    RankingRequest,
    RankingRun,
    ResultApproval,
    ModelTrainingRequest,
    MultimodalCaseRequest,
    MultimodalCaseResult,
    MultimodalReviewRequest,
    MultimodalReviewResult,
    StandardizeRequest,
    StandardizedCompound,
    TDCFetchRequest,
    UniProtSearchRequest,
    VinaDockingJob,
    VinaDockingRequest,
    ZincSearchJob,
    ZincSearchRequest,
)
from .source_registry import SOURCES, source_payload
from .vina_docking import DockingInputError, VinaDisabledError, VinaDockingService
from .zinc22_search import (
    Zinc22SearchService,
    ZincSearchDisabled,
    ZincSearchError,
    ZincSearchInputError,
)


repository.seed()
predictor = DemoPredictionService(repository)
ranker = RankingService(repository, predictor)
experiments = ExperimentService(repository, predictor)
governance = ModelGovernanceService(repository)
assistant = ScientificAssistantService(repository)
plate_reader = PlateReaderService(repository)
open_discovery = OpenDiscoveryService(repository)
vina_docking = VinaDockingService(repository)
docking_benchmark = DockingBenchmarkService(repository)
zinc22_search = Zinc22SearchService(repository)
model_lab = ModelLabService(repository)
compound_conformers = CompoundConformerService(repository)
data_connectors = ScientificDataConnectorService(repository)
multimodal = MultimodalResearchEngine(repository, assistant)

app = FastAPI(
    title="Oncogon AI OSIEL API",
    version="0.1.0",
    description=(
        "Research-use compound prioritization, evidence, experimental dry-run and governed "
        "learning API. Not a clinical decision system."
    ),
    openapi_url="/v1/openapi.json",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def actor(value: str | None) -> str:
    return (value or "demo-researcher").strip()[:120]


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "demo_mode": settings.demo_mode,
        "compound_count": repository.count_compounds(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/v1/system/capabilities")
def capabilities() -> dict[str, object]:
    return {
        "engine": "Oncogon Scientific Intelligence & Experimental Learning Engine (OSIEL)",
        "mode": "developer reference / computational dry-run",
        "implemented": [
            "versioned structure standardization",
            "190+ reference compound registry",
            "official-source connector contracts",
            "deterministic demo prediction with uncertainty and OOD",
            "endpoint-level ADMET rule panel",
            "transparent weighted and Pareto-labelled ranking",
            "experiment planning and computational dry-run",
            "QC, review, audit and dataset snapshot gates",
            "champion/challenger governance boundary",
            "public-source open-discovery orchestration with operational trace",
            "RDKit similarity, QED, Lipinski and PAINS/Brenk/NIH candidate triage",
            "non-executing AutoDock Vina readiness manifest with explicit missing inputs",
            "operator-gated AutoDock Vina 1.2.7 execution with immutable inputs and outputs",
            "opt-in local Ollama/Qwen evidence composer with structured citations and abstention",
            "immutable PDF/text knowledge ingestion with scoped FTS5 and optional Qwen3 embeddings",
            "persisted Professor conversations, faculty corrections and citation/abstention evaluations",
            "operator-gated asynchronous ZINC-22/CartBlanche remote search with local RDKit triage",
            "immutable ChEMBL endpoint snapshot with exact-relation, threshold and duplicate controls",
            "three-way scaffold-separated activity baseline with calibration and frozen evaluation",
            "applicability-domain-aware prediction and diversity-constrained active-learning proposals",
            "heavy-atom Vina redocking RMSD benchmark with immutable reference ligand",
            "deterministic RDKit ETKDGv3 compound conformers with immutable checksums",
            "bounded checksum-controlled NCI-60, COCONUT, NPASS, ANPDB, LOTUS, Tox21 and ToxCast bulk connectors",
            "optional official PyTDC dataset connector with immutable snapshots",
            "official UniProtKB REST sequence and identifier connector",
            "operator-configured licensed Chemspace search connector",
            "fail-closed multimodal research orchestration with cited evidence fusion and abstention",
            "validated-feedback gate that never applies automatic reinforcement learning",
        ],
        "adapter_ready": [
            "PostgreSQL + RDKit cartridge",
            "S3/Iceberg/Parquet lakehouse",
            "MLflow registry",
            "Prefect pipelines",
            "Kafka transactional outbox",
            "OIDC/SSO and PostgreSQL RLS",
            "Chemprop and ADMET-AI serving",
        ],
        "excluded_from_phase_1": [
            "clinical treatment recommendation",
            "automatic model mutation",
            "generative chemistry",
            "docking as efficacy evidence",
            "patient-identifiable data",
            "proprietary phenomics, MatchMaker or Recursion laboratory automation",
            "automatic execution of active-learning proposals",
        ],
    }


@app.get("/v1/system/readiness", response_model=ProductionReadiness)
def production_readiness() -> ProductionReadiness:
    blockers = []
    if settings.demo_mode:
        blockers.append("OSIEL_DEMO_MODE must be false")
    if not settings.api_key:
        blockers.append("Production API credential or OIDC integration is not configured")
    blockers.extend([
        "Validated oncology model and approved dataset are not mounted",
        "Institutional security, POPIA and scientific approvals are not recorded",
        "Specific plate-reader adapter must be qualified against real exports",
    ])
    return ProductionReadiness(
        mode="demonstration" if settings.demo_mode else "production",
        python_engine=True,
        compound_count=repository.count_compounds(),
        object_storage=True,
        authentication_enforced=not settings.demo_mode and bool(settings.api_key),
        plate_reader_validation=True,
        immutable_audit=True,
        blockers=blockers,
    )


@app.post("/v1/plate-reader/imports/validate", response_model=PlateReaderValidation)
def validate_plate_reader_import(
    request: PlateReaderImportRequest,
    context: ActorContext = Depends(require_actor),
) -> PlateReaderValidation:
    try:
        return plate_reader.validate(request, context.subject)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/sources")
def sources() -> list[dict[str, object]]:
    return source_payload()


@app.get("/v1/data-connectors")
def data_connector_capabilities() -> list[dict[str, object]]:
    """Report real connector code paths and their operator configuration state."""
    return data_connectors.capabilities()


@app.post("/v1/data-connectors/bulk/{source_code}/fetch", status_code=status.HTTP_201_CREATED)
def fetch_bulk_source(
    source_code: str,
    request: BulkSourceFetchRequest,
    context: ActorContext = Depends(require_actor),
) -> dict[str, object]:
    try:
        return data_connectors.fetch_bulk(
            source_code,
            request.release_id,
            request.max_preview_records,
            context.subject,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Bulk connector is not registered") from exc


@app.post("/v1/data-connectors/tdc/fetch", status_code=status.HTTP_201_CREATED)
def fetch_tdc_source(
    request: TDCFetchRequest,
    context: ActorContext = Depends(require_actor),
) -> dict[str, object]:
    try:
        return data_connectors.fetch_tdc(
            request.group, request.dataset, request.max_records, context.subject
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/data-connectors/uniprot/search")
def search_uniprot(
    request: UniProtSearchRequest,
    context: ActorContext = Depends(require_actor),
) -> list[dict[str, object]]:
    del context
    try:
        return data_connectors.uniprot_search(request.query, request.limit, request.reviewed_only)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"UniProt request failed: {type(exc).__name__}") from exc


@app.post("/v1/data-connectors/chemspace/search")
def search_chemspace(
    request: ChemspaceSearchRequest,
    context: ActorContext = Depends(require_actor),
) -> dict[str, object]:
    del context
    try:
        return data_connectors.chemspace_search(request.query, request.limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chemspace request failed: {type(exc).__name__}") from exc


@app.get("/v1/data-connectors/jobs/{job_id}")
def get_data_connector_job(job_id: str) -> dict[str, object]:
    payload = data_connectors.get_job(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Source connector job not found")
    return payload


@app.get("/v1/open-discovery/connectors")
def open_discovery_connectors() -> list[dict[str, str | bool]]:
    """Report connector code paths and whether outbound execution is operator-enabled."""
    return open_discovery.connector_status()


@app.get("/v1/zinc22/capabilities")
def zinc22_capabilities() -> dict[str, object]:
    return zinc22_search.capability()


@app.post("/v1/zinc22/searches", response_model=ZincSearchJob, status_code=status.HTTP_201_CREATED)
def create_zinc22_search(
    request: ZincSearchRequest,
    context: ActorContext = Depends(require_actor),
) -> ZincSearchJob:
    try:
        return zinc22_search.submit(request, context.subject)
    except ZincSearchDisabled as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ZincSearchInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ZincSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/zinc22/searches/{job_id}", response_model=ZincSearchJob)
def get_zinc22_search(job_id: str) -> ZincSearchJob:
    job = zinc22_search.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ZINC-22 search job not found")
    return job


@app.post("/v1/zinc22/searches/{job_id}/refresh", response_model=ZincSearchJob)
def refresh_zinc22_search(
    job_id: str,
    context: ActorContext = Depends(require_actor),
) -> ZincSearchJob:
    try:
        return zinc22_search.refresh(job_id, context.subject)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/docking/capabilities")
def docking_capabilities() -> dict[str, str | int | bool | None]:
    return vina_docking.capability()


@app.post("/v1/docking/jobs", response_model=VinaDockingJob, status_code=status.HTTP_201_CREATED)
def create_docking_job(
    request: VinaDockingRequest,
    context: ActorContext = Depends(require_actor),
) -> VinaDockingJob:
    try:
        return vina_docking.run(request, context.subject)
    except VinaDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DockingInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/docking/jobs/{job_id}", response_model=VinaDockingJob)
def get_docking_job(job_id: str) -> VinaDockingJob:
    payload = repository.get_docking_job(job_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Docking job not found")
    return VinaDockingJob.model_validate(payload)


@app.post(
    "/v1/docking/benchmarks",
    response_model=DockingBenchmarkRun,
    status_code=status.HTTP_201_CREATED,
)
def create_docking_benchmark(
    request: DockingBenchmarkRequest,
    context: ActorContext = Depends(require_actor),
) -> DockingBenchmarkRun:
    try:
        return docking_benchmark.run(request, context.subject)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DockingBenchmarkInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/model-lab/capabilities")
def model_lab_capabilities() -> dict[str, object]:
    return model_lab.capability()


@app.get("/v1/model-lab/snapshots", response_model=list[ActivityDatasetSnapshot])
def list_activity_snapshots(limit: int = Query(default=20, ge=1, le=100)) -> list[ActivityDatasetSnapshot]:
    return [ActivityDatasetSnapshot.model_validate(item) for item in repository.list_activity_snapshots(limit)]


@app.post(
    "/v1/model-lab/chembl/snapshots",
    response_model=ActivityDatasetSnapshot,
    status_code=status.HTTP_201_CREATED,
)
def create_activity_snapshot(
    request: ChEMBLActivitySnapshotRequest,
    context: ActorContext = Depends(require_actor),
) -> ActivityDatasetSnapshot:
    try:
        return model_lab.create_snapshot(request, context.subject)
    except ModelLabDisabled as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ModelLabInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=502,
            detail=f"ChEMBL snapshot retrieval failed ({type(exc).__name__})",
        ) from exc


@app.get("/v1/model-lab/models", response_model=list[ActivityModelRun])
def list_activity_models(limit: int = Query(default=20, ge=1, le=100)) -> list[ActivityModelRun]:
    return [ActivityModelRun.model_validate(item) for item in repository.list_activity_models(limit)]


@app.post(
    "/v1/model-lab/models",
    response_model=ActivityModelRun,
    status_code=status.HTTP_201_CREATED,
)
def train_activity_model(
    request: ModelTrainingRequest,
    context: ActorContext = Depends(require_actor),
) -> ActivityModelRun:
    try:
        return model_lab.train(request, context.subject)
    except ModelLabDisabled as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ModelLabInputError, ModelTrainingError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/v1/model-lab/predictions",
    response_model=list[ActivityModelPrediction],
)
def predict_with_activity_model(
    request: ActivityModelPredictionRequest,
) -> list[ActivityModelPrediction]:
    try:
        return model_lab.predict(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelLabInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/v1/model-lab/active-learning-batches",
    response_model=ActiveLearningBatch,
    status_code=status.HTTP_201_CREATED,
)
def propose_active_learning_batch(
    request: ActiveLearningRequest,
    context: ActorContext = Depends(require_actor),
) -> ActiveLearningBatch:
    try:
        return model_lab.propose_active_learning(request, context.subject)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelLabInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/open-discovery/runs", response_model=OpenDiscoveryRun, status_code=status.HTTP_201_CREATED)
def create_open_discovery_run(
    request: OpenDiscoveryRequest,
    x_osiel_actor: str | None = Header(default=None),
) -> OpenDiscoveryRun:
    try:
        return open_discovery.run(request, actor(x_osiel_actor))
    except (StructureError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/open-discovery/runs/{run_id}", response_model=OpenDiscoveryRun)
def get_open_discovery_run(run_id: str) -> OpenDiscoveryRun:
    payload = repository.get_open_discovery_run(run_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Open-discovery run not found")
    return OpenDiscoveryRun.model_validate(payload)


@app.get("/v1/literature")
def literature(
    query: str | None = Query(default=None, max_length=200),
    evidence_level: str | None = Query(default=None, pattern="^(direct|supporting|method)$"),
) -> list[dict[str, object]]:
    """Return curated citations and study-context summaries, never copied full text."""
    return search_literature(query=query, evidence_level=evidence_level)


@app.post("/v1/sources/{source_code}/sync", status_code=status.HTTP_202_ACCEPTED)
def request_source_sync(
    source_code: str,
    context: ActorContext = Depends(require_actor),
) -> dict[str, object]:
    source = next((item for item in SOURCES if item.code == source_code), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Source is not registered")
    job_id = repository.new_id("SYNC")
    detail = {
        "source": source.name,
        "mode": source.mode,
        "endpoint": source.endpoint,
        "status": "manifest-required",
        "message": (
            "The connector is registered. Production synchronization requires an approved licence "
            "snapshot, release identifier, checksum destination and source-specific parser."
        ),
    }
    with repository.connection() as connection:
        connection.execute(
            "INSERT INTO source_sync_job VALUES (?, ?, ?, ?, ?)",
            (job_id, source_code, "manifest-required", __import__("json").dumps(detail), datetime.now(UTC).isoformat()),
        )
    repository.audit(context.subject, "source.sync_requested", "source", source_code, detail)
    return {"job_id": job_id, **detail}


@app.get("/v1/compounds", response_model=list[Compound])
def list_compounds(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    query: str | None = Query(default=None, max_length=200),
    origin: str | None = Query(default=None),
) -> list[Compound]:
    return repository.list_compounds(limit=limit, offset=offset, query=query, origin=origin)


@app.get("/v1/compounds/{compound_id}", response_model=Compound)
def get_compound(compound_id: str) -> Compound:
    compound = repository.get_compound(compound_id)
    if not compound:
        raise HTTPException(status_code=404, detail="Compound not found")
    return compound


@app.get("/v1/compounds/{compound_id}/conformer-3d", response_model=CompoundConformer3D)
def get_compound_conformer_3d(
    compound_id: str,
    include_hydrogens: bool = Query(default=True),
    experiment_id: str | None = Query(default=None, max_length=120),
    x_osiel_actor: str | None = Header(default=None),
) -> CompoundConformer3D:
    try:
        return compound_conformers.generate(
            compound_id,
            include_hydrogens=include_hydrogens,
            actor=actor(x_osiel_actor),
            experiment_id=experiment_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Compound not found") from exc
    except ConformerGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/compounds/standardize", response_model=StandardizedCompound)
def standardize_compound(request: StandardizeRequest) -> StandardizedCompound:
    try:
        return chemistry.standardize(request.smiles)
    except StructureError as exc:
        repository.audit(
            "demo-researcher",
            "structure.quarantined",
            "submission",
            repository.new_id("SUB"),
            {"reason": str(exc)},
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/predictions", response_model=list[Prediction])
def create_predictions(request: PredictionRequest) -> list[Prediction]:
    compounds = repository.get_compounds(request.compound_ids)
    if len(compounds) != len(request.compound_ids):
        raise HTTPException(status_code=404, detail="One or more compounds could not be resolved")
    return [
        predictor.predict(compound, request.cancer_type, request.cell_line, request.endpoint)
        for compound in compounds
    ]


@app.post("/v1/rankings", response_model=RankingRun)
def create_ranking(request: RankingRequest) -> RankingRun:
    try:
        return ranker.rank(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/experiments", response_model=Experiment, status_code=status.HTTP_201_CREATED)
def create_experiment(
    request: ExperimentCreate,
    x_osiel_actor: str | None = Header(default=None),
) -> Experiment:
    try:
        return experiments.create(request, actor(x_osiel_actor))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/experiments", response_model=list[Experiment])
def list_experiments(limit: int = Query(default=50, ge=1, le=200)) -> list[Experiment]:
    return experiments.list(limit)


@app.post("/v1/experiments/{experiment_id}/simulate", response_model=ExperimentResult)
def simulate_experiment(experiment_id: str) -> ExperimentResult:
    try:
        return experiments.simulate(experiment_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/results/{result_id}/review")
def review_result(
    result_id: str,
    request: ResultApproval,
    context: ActorContext = Depends(require_actor),
) -> DatasetSnapshot | dict[str, str]:
    if not settings.demo_mode and context.role not in {"reviewer", "instructor", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer role required")
    if not settings.demo_mode and request.reviewer != context.subject:
        raise HTTPException(status_code=422, detail="Reviewer must match authenticated subject")
    try:
        return experiments.approve(result_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/models")
def list_models() -> list[dict[str, object]]:
    return governance.list_models()


@app.post("/v1/models/challenger/evaluate")
def evaluate_challenger() -> dict[str, object]:
    return governance.evaluate_challenger()


@app.post("/v1/models/{model_id}/approve")
def approve_model(
    model_id: str,
    reviewer: str = Query(min_length=2, max_length=120),
    reason: str = Query(min_length=4, max_length=1000),
    context: ActorContext = Depends(require_actor),
) -> dict[str, object]:
    if not settings.demo_mode and context.role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Independent reviewer role required")
    if not settings.demo_mode and reviewer != context.subject:
        raise HTTPException(status_code=422, detail="Reviewer must match authenticated subject")
    try:
        return governance.approve(model_id, reviewer, reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/audit")
def audit_log(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, object]]:
    return repository.list_audit(limit)


@app.get("/v1/multimodal/capabilities")
def multimodal_capabilities() -> dict[str, object]:
    return multimodal.capabilities()


@app.post(
    "/v1/multimodal/cases",
    response_model=MultimodalCaseResult,
    status_code=status.HTTP_201_CREATED,
)
def create_multimodal_case(
    request: MultimodalCaseRequest,
    context: ActorContext = Depends(require_actor),
) -> MultimodalCaseResult:
    try:
        return multimodal.run(request, actor=context.subject, role=context.role)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/v1/multimodal/cases/{case_id}", response_model=MultimodalCaseResult)
def get_multimodal_case(case_id: str) -> MultimodalCaseResult:
    result = multimodal.get(case_id)
    if not result:
        raise HTTPException(status_code=404, detail="Multimodal case not found")
    return result


@app.post(
    "/v1/multimodal/cases/{case_id}/reviews",
    response_model=MultimodalReviewResult,
    status_code=status.HTTP_201_CREATED,
)
def review_multimodal_case(
    case_id: str,
    request: MultimodalReviewRequest,
    context: ActorContext = Depends(require_actor),
) -> MultimodalReviewResult:
    try:
        return multimodal.review(
            case_id, request, actor=context.subject, role=context.role
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/assistant/query", response_model=AssistantAnswer)
def assistant_query(
    request: AssistantQuery,
    context: ActorContext = Depends(require_actor),
) -> AssistantAnswer:
    try:
        return assistant.answer(request, actor=context.subject, role=context.role)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/v1/assistant/capabilities")
def assistant_capabilities() -> dict[str, object]:
    """Describe the optional local model without probing or starting it."""
    return assistant.capability()


@app.post("/v1/assistant/documents", response_model=KnowledgeDocument, status_code=201)
def ingest_assistant_document(
    request: KnowledgeDocumentIngest,
    context: ActorContext = Depends(require_actor),
) -> KnowledgeDocument:
    try:
        return assistant.knowledge.ingest(request, actor=context.subject, role=context.role)
    except KnowledgeIngestionDisabled as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KnowledgeInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/v1/assistant/documents", response_model=list[KnowledgeDocument])
def list_assistant_documents(
    project_scope: str | None = Query(default=None, max_length=120),
    course_scope: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=500),
    _context: ActorContext = Depends(require_actor),
) -> list[KnowledgeDocument]:
    return assistant.knowledge.list_documents(
        project_scope=project_scope,
        course_scope=course_scope,
        limit=limit,
    )


@app.post("/v1/assistant/conversations", response_model=AssistantConversation, status_code=201)
def create_assistant_conversation(
    request: AssistantConversationCreate,
    context: ActorContext = Depends(require_actor),
) -> AssistantConversation:
    return assistant.create_conversation(request, actor=context.subject)


@app.get("/v1/assistant/conversations", response_model=list[AssistantConversation])
def list_assistant_conversations(
    context: ActorContext = Depends(require_actor),
) -> list[AssistantConversation]:
    return assistant.list_conversations(actor=context.subject)


@app.get("/v1/assistant/conversations/{conversation_id}/turns")
def list_assistant_conversation_turns(
    conversation_id: str,
    context: ActorContext = Depends(require_actor),
) -> list[dict[str, object]]:
    try:
        return assistant.conversation_turns(
            conversation_id,
            actor=context.subject,
            role=context.role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/v1/assistant/answers/{answer_id}/feedback", response_model=AssistantFeedback, status_code=201)
def record_assistant_feedback(
    answer_id: str,
    request: AssistantFeedbackRequest,
    context: ActorContext = Depends(require_actor),
) -> AssistantFeedback:
    try:
        return assistant.record_feedback(
            answer_id,
            request,
            actor=context.subject,
            role=context.role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/assistant/evaluations", response_model=AssistantEvaluationRun, status_code=201)
def evaluate_assistant(
    request: AssistantEvaluationRequest,
    context: ActorContext = Depends(require_actor),
) -> AssistantEvaluationRun:
    try:
        return assistant.evaluate(
            request,
            actor=context.subject,
            role=context.role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/v1/assistant/evaluations", response_model=list[AssistantEvaluationRun])
def list_assistant_evaluations(
    limit: int = Query(default=50, ge=1, le=200),
    _context: ActorContext = Depends(require_actor),
) -> list[AssistantEvaluationRun]:
    return assistant.list_evaluations(limit)


@app.post("/v1/assistant/maintenance/retention", response_model=AssistantRetentionResult)
def apply_assistant_retention(
    request: AssistantRetentionRequest,
    context: ActorContext = Depends(require_actor),
) -> AssistantRetentionResult:
    try:
        return assistant.apply_retention(
            request,
            actor=context.subject,
            role=context.role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
