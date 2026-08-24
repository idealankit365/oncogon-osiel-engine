from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ScientificNotice(BaseModel):
    research_use_only: bool = True
    message: str = (
        "In-silico research-prioritization hypothesis. Experimental validation and "
        "qualified scientific review are required."
    )


class StandardizeRequest(BaseModel):
    smiles: str = Field(min_length=1, max_length=10_000)
    display_name: str | None = Field(default=None, max_length=300)
    origin: Literal["natural", "synthetic", "semi-synthetic", "unknown"] = "unknown"


class DescriptorSet(BaseModel):
    molecular_formula: str
    molecular_weight: float
    clogp: float
    tpsa: float
    h_bond_donors: int
    h_bond_acceptors: int
    rotatable_bonds: int
    ring_count: int
    fraction_csp3: float
    qed: float


class StandardizedCompound(BaseModel):
    raw_smiles: str
    canonical_smiles: str
    parent_smiles: str
    inchi: str
    inchikey: str
    stereo_status: Literal["defined", "undefined", "none"]
    descriptors: DescriptorSet
    quality_flags: list[str] = []
    transformations: list[str] = []
    standardization_version: str


class Compound(BaseModel):
    compound_id: str
    display_name: str
    source_id: str
    source_name: str
    origin: str
    canonical_smiles: str
    inchikey: str
    descriptors: DescriptorSet
    evidence_grade: Literal["A", "B", "C", "D"]
    evidence_mode: Literal["curated", "reference-structure", "demonstration"]
    aliases: list[str] = []


class CompoundConformer3D(BaseModel):
    compound_id: str
    display_name: str
    canonical_smiles: str
    mol_block: str
    format: Literal["mol-v2000"] = "mol-v2000"
    coordinate_method: str
    optimization_method: Literal["MMFF94", "UFF", "none"]
    optimization_converged: bool
    conformer_energy_kcal_mol: float | None = None
    random_seed: int
    includes_hydrogens: bool
    atom_count: int
    heavy_atom_count: int
    rdkit_version: str
    sha256: str
    object_uri: str
    warnings: list[str] = []
    created_at: datetime
    scientific_boundary: str = (
        "Deterministic computational conformer for identity inspection only. It is not an "
        "experimental crystal structure, protein-bound pose, docking result or proof of activity."
    )


class PredictionRequest(BaseModel):
    compound_ids: list[str] = Field(min_length=1, max_length=100)
    cancer_type: str = Field(min_length=2, max_length=120)
    cell_line: str | None = Field(default=None, max_length=120)
    endpoint: Literal["activity_probability", "IC50", "GI50"] = "activity_probability"

    @field_validator("compound_ids")
    @classmethod
    def unique_compounds(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class ScoreComponent(BaseModel):
    code: str
    label: str
    value: float
    weight: float
    contribution: float
    explanation: str


class ADMETEndpoint(BaseModel):
    code: str
    label: str
    predicted_value: float | str
    unit: str | None = None
    classification: str
    confidence: float
    applicability_domain: Literal["inside", "borderline", "outside"]
    model_version: str


class AnalogEvidence(BaseModel):
    compound_id: str
    display_name: str
    tanimoto_similarity: float
    source_name: str


class Prediction(BaseModel):
    prediction_id: str
    compound_id: str
    display_name: str
    cancer_type: str
    cell_line: str | None
    endpoint: str
    predicted_activity: float
    predicted_ic50_um: float
    predicted_selectivity_index: float
    uncertainty: float
    confidence: float
    applicability_domain: Literal["inside", "borderline", "outside"]
    interval_low: float
    interval_high: float
    model_version: str
    dataset_version: str
    feature_version: str
    standardization_version: str
    nearest_analogs: list[AnalogEvidence]
    admet: list[ADMETEndpoint]
    evidence_summary: str
    created_at: datetime
    notice: ScientificNotice = ScientificNotice()


class ChEMBLActivitySnapshotRequest(BaseModel):
    target_chembl_id: str = Field(default="CHEMBL203", pattern=r"^CHEMBL[0-9]+$")
    target_label: str = Field(default="EGFR", min_length=2, max_length=120)
    standard_type: Literal["IC50", "EC50", "Ki", "Kd"] = "IC50"
    assay_type: Literal["B", "F"] = "B"
    max_records: int = Field(default=1000, ge=100, le=10_000)
    active_pchembl_threshold: float = Field(default=6.0, ge=3, le=12)
    inactive_pchembl_threshold: float = Field(default=5.0, ge=3, le=12)
    minimum_assay_confidence: int = Field(default=8, ge=0, le=9)

    @model_validator(mode="after")
    def thresholds_have_a_grey_zone(self) -> "ChEMBLActivitySnapshotRequest":
        if self.inactive_pchembl_threshold >= self.active_pchembl_threshold:
            raise ValueError("inactive threshold must be lower than active threshold")
        return self


class ActivityDatasetSnapshot(BaseModel):
    snapshot_id: str
    status: Literal["ready", "blocked"]
    source: Literal["ChEMBL"] = "ChEMBL"
    source_release: str
    target_chembl_id: str
    target_label: str
    standard_type: str
    assay_type: str
    active_pchembl_threshold: float
    inactive_pchembl_threshold: float
    record_count: int = Field(ge=0)
    active_count: int = Field(ge=0)
    inactive_count: int = Field(ge=0)
    unique_scaffold_count: int = Field(ge=0)
    ambiguous_removed: int = Field(ge=0)
    invalid_removed: int = Field(ge=0)
    duplicate_removed: int = Field(ge=0)
    conflict_removed: int = Field(ge=0)
    raw_sha256: str
    raw_object_uri: str
    normalized_sha256: str
    normalized_object_uri: str
    request_urls: list[str]
    warnings: list[str] = Field(default_factory=list)
    training_eligible: bool = False
    created_at: datetime
    notice: ScientificNotice = ScientificNotice()


class ModelTrainingRequest(BaseModel):
    snapshot_id: str = Field(pattern=r"^ADS-[A-Z0-9]{12}$")
    test_fraction: float = Field(default=0.20, ge=0.10, le=0.35)
    calibration_fraction: float = Field(default=0.20, ge=0.10, le=0.30)
    random_seed: int = Field(default=20260822, ge=1, le=2_147_483_647)
    minimum_records: int = Field(default=100, ge=24, le=5000)

    @model_validator(mode="after")
    def split_budget_is_valid(self) -> "ModelTrainingRequest":
        if self.test_fraction + self.calibration_fraction > 0.55:
            raise ValueError("test and calibration fractions leave too little training data")
        return self


class ModelEvaluationMetrics(BaseModel):
    auroc: float = Field(ge=0, le=1)
    average_precision: float = Field(ge=0, le=1)
    balanced_accuracy: float = Field(ge=0, le=1)
    sensitivity: float = Field(ge=0, le=1)
    specificity: float = Field(ge=0, le=1)
    brier_score: float = Field(ge=0, le=1)
    expected_calibration_error: float = Field(ge=0, le=1)
    test_prevalence: float = Field(ge=0, le=1)
    test_count: int = Field(ge=1)


class ActivityModelRun(BaseModel):
    model_id: str
    status: Literal["completed", "blocked", "failed"]
    model_name: str
    model_version: str
    model_type: str
    snapshot_id: str
    target_chembl_id: str
    target_label: str
    endpoint: str
    feature_version: str
    split_strategy: str
    train_count: int = Field(ge=0)
    calibration_count: int = Field(ge=0)
    test_count: int = Field(ge=0)
    train_scaffolds: int = Field(ge=0)
    calibration_scaffolds: int = Field(ge=0)
    test_scaffolds: int = Field(ge=0)
    scaffold_overlap_count: int = Field(ge=0)
    metrics: ModelEvaluationMetrics | None = None
    artifact_sha256: str | None = None
    artifact_object_uri: str | None = None
    evaluation_gate: Literal["passed-reference-gate", "failed-reference-gate", "not-run"]
    promotion_eligible: bool = False
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    notice: ScientificNotice = ScientificNotice()


class ModelPredictionItem(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=300)
    smiles: str = Field(min_length=1, max_length=4000)


class ActivityModelPredictionRequest(BaseModel):
    model_id: str = Field(pattern=r"^MDL-[A-Z0-9]{12}$")
    candidates: list[ModelPredictionItem] = Field(min_length=1, max_length=500)


class ActivityModelPrediction(BaseModel):
    candidate_id: str
    display_name: str
    canonical_smiles: str
    inchikey: str
    active_probability: float = Field(ge=0, le=1)
    predicted_class: Literal["active", "inactive"]
    uncertainty: float = Field(ge=0, le=1)
    nearest_training_similarity: float = Field(ge=0, le=1)
    applicability_domain: Literal["inside", "borderline", "outside"]
    model_id: str
    endpoint: str
    warnings: list[str] = Field(default_factory=list)
    notice: ScientificNotice = ScientificNotice()


class ActiveLearningRequest(BaseModel):
    model_id: str = Field(pattern=r"^MDL-[A-Z0-9]{12}$")
    candidates: list[ModelPredictionItem] = Field(min_length=3, max_length=500)
    batch_size: int = Field(default=8, ge=2, le=50)
    maximum_pair_similarity: float = Field(default=0.75, ge=0.2, le=0.95)


class ActiveLearningSuggestion(BaseModel):
    priority: int = Field(ge=1)
    candidate_id: str
    display_name: str
    canonical_smiles: str
    active_probability: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)
    nearest_training_similarity: float = Field(ge=0, le=1)
    diversity_to_selected: float = Field(ge=0, le=1)
    acquisition_score: float = Field(ge=0, le=100)
    reason: str


class ActiveLearningBatch(BaseModel):
    batch_id: str
    model_id: str
    status: Literal["proposed"] = "proposed"
    candidate_count: int
    requested_batch_size: int
    suggestions: list[ActiveLearningSuggestion]
    selection_policy: str
    approval_required: bool = True
    experiment_started: bool = False
    created_at: datetime
    scientific_boundary: str


class RankingWeights(BaseModel):
    activity: float = 0.34
    selectivity: float = 0.14
    admet: float = 0.18
    novelty: float = 0.10
    feasibility: float = 0.10
    evidence: float = 0.09
    uncertainty_penalty: float = 0.05

    @field_validator("uncertainty_penalty", "activity", "selectivity", "admet", "novelty", "feasibility", "evidence")
    @classmethod
    def bounded(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("weights must be between 0 and 1")
        return value


class RankingRequest(BaseModel):
    compound_ids: list[str] = Field(min_length=2, max_length=100)
    cancer_type: str = Field(min_length=2, max_length=120)
    cell_line: str | None = None
    weights: RankingWeights = RankingWeights()
    diversity_threshold: float = Field(default=0.82, ge=0.2, le=1.0)


class RankedCompound(BaseModel):
    rank: int
    compound_id: str
    display_name: str
    score: float
    pareto_front: int
    eligibility: Literal["eligible", "flagged", "excluded"]
    hard_filter_reasons: list[str]
    components: list[ScoreComponent]
    prediction: Prediction


class RankingRun(BaseModel):
    ranking_run_id: str
    policy_version: str
    cancer_type: str
    weights: RankingWeights
    candidate_count: int
    ranked: list[RankedCompound]
    created_at: datetime
    notice: ScientificNotice = ScientificNotice()


class ExperimentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    compound_ids: list[str] = Field(min_length=1, max_length=24)
    cancer_type: str
    cell_line: str
    assay_type: Literal["MTT", "SRB", "CellTiter-Glo", "Apoptosis", "Custom"] = "MTT"
    endpoint: Literal["IC50", "GI50", "viability"] = "IC50"
    dose_min_um: float = Field(default=0.01, gt=0)
    dose_max_um: float = Field(default=10.0, gt=0)
    dose_points: int = Field(default=8, ge=4, le=16)
    replicates: int = Field(default=3, ge=2, le=8)
    duration_hours: int = Field(default=48, ge=1, le=336)
    positive_control: str = "Doxorubicin"
    negative_control: str = "Vehicle"
    source_ranking_run_id: str | None = None

    @field_validator("dose_max_um")
    @classmethod
    def dose_range_is_positive(cls, value: float) -> float:
        return value


class Experiment(BaseModel):
    experiment_id: str
    status: Literal["planned", "simulated", "results-uploaded", "qc-passed", "approved", "rejected"]
    simulation_only: bool
    protocol: ExperimentCreate
    created_at: datetime
    created_by: str


class SimulatedObservation(BaseModel):
    compound_id: str
    dose_um: float
    replicate: int
    viability_percent: float


class ExperimentResult(BaseModel):
    result_id: str
    experiment_id: str
    simulation_only: bool
    observations: list[SimulatedObservation]
    estimated_ic50_um: dict[str, float]
    qc_status: Literal["passed", "failed", "pending"]
    qc_checks: dict[str, bool]
    created_at: datetime
    disclaimer: str


class ResultApproval(BaseModel):
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=4, max_length=1000)
    training_eligible: bool = False


class DatasetSnapshot(BaseModel):
    snapshot_id: str
    dataset_version: str
    source_result_ids: list[str]
    status: Literal["proposed", "approved", "rejected"]
    record_count: int
    checksum: str
    created_at: datetime
    model_mutated: bool = False


class KnowledgeDocumentIngest(BaseModel):
    filename: str = Field(min_length=3, max_length=240)
    title: str = Field(min_length=3, max_length=500)
    media_type: Literal["application/pdf", "text/plain", "text/markdown"]
    content_base64: str = Field(min_length=4, max_length=70_000_000)
    source_url: str | None = Field(default=None, max_length=2000)
    source_version: str = Field(default="uploaded", min_length=1, max_length=120)
    rights_status: Literal["approved", "restricted", "link-only", "unknown"] = "unknown"
    rights_note: str = Field(default="", max_length=1000)
    project_scope: str = Field(default="general", min_length=1, max_length=120)
    course_scope: str = Field(default="general", min_length=1, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=20)


class KnowledgeDocument(BaseModel):
    document_id: str
    title: str
    filename: str
    media_type: str
    source_url: str | None = None
    source_version: str
    rights_status: str
    rights_note: str
    project_scope: str
    course_scope: str
    tags: list[str]
    status: Literal["indexed", "quarantined"]
    raw_sha256: str
    raw_object_uri: str
    normalized_sha256: str | None = None
    normalized_object_uri: str | None = None
    parser_version: str
    chunker_version: str
    embedding_model: str | None = None
    page_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    prompt_injection_flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    duplicate: bool = False


class AssistantConversationCreate(BaseModel):
    title: str = Field(default="Scientific research consultation", min_length=3, max_length=240)
    project_scope: str = Field(default="general", min_length=1, max_length=120)
    course_scope: str = Field(default="general", min_length=1, max_length=120)


class AssistantConversation(BaseModel):
    conversation_id: str
    title: str
    project_scope: str
    course_scope: str
    owner_actor: str
    status: Literal["active", "closed"] = "active"
    turn_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class AssistantTraceEvent(BaseModel):
    stage: str
    status: Literal["completed", "completed-with-warning", "blocked", "skipped"]
    message: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class AssistantQuery(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    cancer_type: str | None = Field(default=None, max_length=180)
    compound_ids: list[str] = Field(default_factory=list, max_length=20)
    conversation_id: str | None = Field(default=None, pattern=r"^CON-[A-Z0-9]{12}$")
    project_scope: str = Field(default="general", min_length=1, max_length=120)
    course_scope: str = Field(default="general", min_length=1, max_length=120)
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    persist: bool = True


class AssistantAnswer(BaseModel):
    answer_id: str | None = None
    conversation_id: str | None = None
    answer: str
    evidence: list[dict[str, Any]]
    missing_information: list[str]
    recommended_action: str
    mode: Literal[
        "deterministic-evidence",
        "local-ollama-rag",
        "hybrid-ollama-rag",
    ] = "deterministic-evidence"
    model: str | None = None
    embedding_model: str | None = None
    abstained: bool = False
    confidence: Literal["low", "medium"] = "low"
    retrieval_score: float = Field(default=0, ge=0, le=1)
    citation_coverage: float = Field(default=0, ge=0, le=1)
    retrieval_trace: list[AssistantTraceEvent] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    notice: ScientificNotice = ScientificNotice()


class AssistantFeedbackRequest(BaseModel):
    decision: Literal["correct", "partially-correct", "incorrect", "unsafe"]
    correction: str | None = Field(default=None, max_length=5000)
    reviewer_notes: str = Field(default="", max_length=2000)
    supporting_evidence_ids: list[str] = Field(default_factory=list, max_length=20)


class AssistantFeedback(BaseModel):
    feedback_id: str
    answer_id: str
    decision: Literal["correct", "partially-correct", "incorrect", "unsafe"]
    correction: str | None = None
    reviewer_notes: str
    supporting_evidence_ids: list[str]
    reviewer: str
    training_applied: bool = False
    created_at: datetime


class AssistantEvaluationCase(BaseModel):
    case_id: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=3, max_length=2000)
    cancer_type: str | None = Field(default=None, max_length=180)
    expected_evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    expect_abstention: bool = False
    project_scope: str = Field(default="general", min_length=1, max_length=120)
    course_scope: str = Field(default="general", min_length=1, max_length=120)


class AssistantEvaluationRequest(BaseModel):
    dataset_label: str = Field(min_length=3, max_length=240)
    cases: list[AssistantEvaluationCase] = Field(min_length=1, max_length=50)


class AssistantEvaluationRun(BaseModel):
    evaluation_id: str
    dataset_label: str
    dataset_sha256: str
    case_count: int = Field(ge=1)
    citation_precision: float = Field(ge=0, le=1)
    expected_citation_recall: float = Field(ge=0, le=1)
    abstention_accuracy: float = Field(ge=0, le=1)
    unsupported_answer_rate: float = Field(ge=0, le=1)
    passed: bool
    thresholds: dict[str, float]
    case_results: list[dict[str, Any]]
    model: str | None = None
    embedding_model: str | None = None
    created_by: str
    created_at: datetime
    scientific_boundary: str


class AssistantRetentionRequest(BaseModel):
    retention_days: int = Field(default=180, ge=1, le=3650)
    dry_run: bool = True


class AssistantRetentionResult(BaseModel):
    cutoff: datetime
    dry_run: bool
    conversation_count: int = Field(ge=0)
    turn_count: int = Field(ge=0)
    feedback_count: int = Field(ge=0)
    deleted: bool


class MultimodalArtifact(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=200)
    media_type: Literal[
        "microscopy-image", "plate-table", "protein-structure", "scientific-document"
    ]
    object_uri: str = Field(min_length=3, max_length=2000)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    description: str = Field(default="", max_length=500)


class MultimodalCaseRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    cancer_type: str | None = Field(default=None, max_length=180)
    cell_line: str | None = Field(default=None, max_length=120)
    target_name: str | None = Field(default=None, max_length=180)
    protein_accession: str | None = Field(default=None, max_length=40)
    compound_ids: list[str] = Field(default_factory=list, max_length=20)
    assay_summary: dict[str, Any] | None = None
    artifacts: list[MultimodalArtifact] = Field(default_factory=list, max_length=20)
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    project_scope: str = Field(default="general", min_length=1, max_length=120)
    course_scope: str = Field(default="general", min_length=1, max_length=120)
    requested_modalities: list[Literal["chemistry", "protein", "assay", "documents", "imaging"]] = Field(
        default_factory=lambda: ["chemistry", "protein", "assay", "documents", "imaging"],
        min_length=1,
        max_length=5,
    )

    @field_validator("compound_ids", "document_ids", "requested_modalities")
    @classmethod
    def unique_multimodal_values(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class MultimodalEvidence(BaseModel):
    evidence_id: str
    modality: Literal["chemistry", "protein", "assay", "documents", "imaging"]
    source: str
    source_version: str
    citation: str
    finding: str
    confidence: float = Field(ge=0, le=1)
    checksum: str | None = None


class ModalityAssessment(BaseModel):
    modality: Literal["chemistry", "protein", "assay", "documents", "imaging"]
    status: Literal["completed", "completed-with-warning", "blocked", "skipped"]
    model_name: str | None = None
    model_version: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    findings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MultimodalTraceEvent(BaseModel):
    sequence: int = Field(ge=1)
    stage: str
    status: Literal["completed", "completed-with-warning", "blocked", "skipped"]
    message: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class MultimodalCaseResult(BaseModel):
    case_id: str
    status: Literal["completed", "abstained", "blocked"]
    question: str
    assessments: list[ModalityAssessment]
    evidence: list[MultimodalEvidence]
    recommendation: str
    rationale: list[str]
    next_actions: list[str]
    missing_information: list[str]
    conflicts: list[str]
    confidence: float = Field(ge=0, le=0.75)
    citation_coverage: float = Field(ge=0, le=1)
    abstained: bool
    human_approval_required: bool = True
    approved: bool = False
    trace: list[MultimodalTraceEvent]
    created_at: datetime
    scientific_boundary: str = (
        "Research-use evidence synthesis and prioritization only. It is not a clinical conclusion, "
        "measured efficacy, autonomous laboratory authorization, or a substitute for supervisor review."
    )


class MultimodalReviewRequest(BaseModel):
    decision: Literal["approved-for-review", "needs-correction", "rejected", "unsafe"]
    reviewer_notes: str = Field(min_length=3, max_length=3000)
    correction: str | None = Field(default=None, max_length=5000)
    supporting_evidence_ids: list[str] = Field(default_factory=list, max_length=50)
    measured_data: bool = False
    qc_passed: bool = False
    raw_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")

    @model_validator(mode="after")
    def correction_is_required_when_not_approved(self) -> "MultimodalReviewRequest":
        if self.decision in {"needs-correction", "rejected", "unsafe"} and not self.correction:
            raise ValueError("A correction is required for non-approved feedback")
        return self


class MultimodalReviewResult(BaseModel):
    review_id: str
    case_id: str
    decision: Literal["approved-for-review", "needs-correction", "rejected", "unsafe"]
    reviewer: str
    reviewer_notes: str
    correction: str | None = None
    supporting_evidence_ids: list[str]
    training_candidate: bool
    training_applied: bool = False
    exclusion_reasons: list[str]
    created_at: datetime
    scientific_boundary: str = (
        "Feedback is stored for governed evaluation. It never updates a model directly; only "
        "measured, QC-passed, checksum-verified and independently approved records may enter a "
        "future challenger dataset snapshot."
    )


class ZincSearchRequest(BaseModel):
    seed_smiles: str = Field(min_length=1, max_length=4000)
    graph_distance: int = Field(default=2, ge=0, le=3)
    anonymous_distance: int = Field(default=1, ge=0, le=3)
    max_results: int = Field(default=25, ge=5, le=100)


class ZincCandidate(BaseModel):
    rank: int = Field(ge=1)
    remote_id: str
    source_smiles: str
    canonical_smiles: str
    inchikey: str
    tranche: str | None = None
    catalogs: list[str] = Field(default_factory=list)
    descriptors: DescriptorSet
    similarity_to_seed: float = Field(ge=0, le=1)
    lipinski_violations: list[str]
    pains_alerts: list[str]
    brenk_alerts: list[str]
    nih_alerts: list[str]
    quality_flags: list[str]
    priority_score: float = Field(ge=0, le=100)
    scientific_boundary: str = (
        "Remote catalogue hit and local chemistry triage only; not target binding, activity, "
        "availability, identity/purity confirmation, or experimental evidence."
    )


class ZincSearchJob(BaseModel):
    job_id: str
    remote_query_id: str
    status: Literal["submitted", "pending", "completed", "failed"]
    remote_status: str
    request: ZincSearchRequest
    canonical_seed_smiles: str
    candidates: list[ZincCandidate] = Field(default_factory=list)
    remote_returned_count: int = Field(default=0, ge=0)
    quarantined_count: int = Field(default=0, ge=0)
    remote_result_sha256: str | None = None
    index_key: str
    index_name: str
    index_entries: int = Field(ge=0)
    index_mapped_entries: int = Field(ge=0)
    poll_after_seconds: int = Field(ge=3)
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    source_url: str = "https://sw.docking.org/"
    index_scope: str = (
        "Remote ZINC-22/CartBlanche SmallWorld index. The 2023 ZINC-22 publication reported "
        "more than 37 billion searchable 2D make-on-demand structures; live coverage changes."
    )
    scientific_boundary: str = (
        "The remote service performs structure search; OSIEL imports only a bounded shortlist. "
        "A hit is not proof of purchase availability, synthesis, target binding, efficacy, or safety."
    )
    created_at: datetime
    updated_at: datetime


class PlateReaderImportRequest(BaseModel):
    filename: str = Field(min_length=3, max_length=240)
    content_base64: str = Field(min_length=4, max_length=20_000_000)
    instrument_manufacturer: str = Field(min_length=2, max_length=120)
    instrument_model: str = Field(min_length=1, max_length=120)
    instrument_serial: str = Field(min_length=1, max_length=120)
    software_version: str = Field(min_length=1, max_length=80)
    signal_unit: Literal["RLU", "RFU", "OD", "AU"] = "RLU"
    expected_plate_format: Literal["96", "384"] = "96"


class PlateReaderValidation(BaseModel):
    import_id: str
    filename: str
    sha256: str
    byte_count: int
    row_count: int
    mapped_columns: list[str]
    missing_columns: list[str]
    duplicate_wells: list[str]
    invalid_wells: list[str]
    control_types: list[str]
    plate_ids: list[str]
    schema_valid: bool
    qc_ready: bool
    quarantined: bool = True
    training_eligible: bool = False
    object_uri: str
    warnings: list[str]
    created_at: datetime


class ProductionReadiness(BaseModel):
    mode: Literal["demonstration", "production"]
    python_engine: bool
    compound_count: int
    object_storage: bool
    authentication_enforced: bool
    plate_reader_validation: bool
    immutable_audit: bool
    validated_scientific_model: bool = False
    institution_approved: bool = False
    blockers: list[str]


class BulkSourceFetchRequest(BaseModel):
    release_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    max_preview_records: int = Field(default=25, ge=1, le=100)


class TDCFetchRequest(BaseModel):
    group: Literal["adme", "tox", "hts"]
    dataset: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9 ._()+/-]{0,119}$")
    max_records: int = Field(default=1000, ge=1, le=10_000)


class UniProtSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=10, ge=1, le=50)
    reviewed_only: bool = True


class ChemspaceSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=25, ge=1, le=100)


class OpenDiscoveryRequest(BaseModel):
    """Inputs for the public-source, research-use discovery workflow.

    A seed structure is required either directly or through a resolvable local/public
    compound name. Disease and target labels provide retrieval context; they do not
    make the cheminformatics score target-specific.
    """

    disease: str = Field(default="Non-small cell lung cancer", min_length=2, max_length=180)
    target_symbol: str | None = Field(default="EGFR", min_length=2, max_length=40)
    seed_compound_name: str | None = Field(default="Gefitinib", min_length=2, max_length=160)
    seed_smiles: str | None = Field(default=None, min_length=1, max_length=4000)
    pdb_id: str | None = Field(default=None, pattern=r"^[0-9][A-Za-z0-9]{3}$")
    uniprot_accession: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{4,14}$",
    )
    candidate_limit: int = Field(default=12, ge=3, le=50)
    public_connectors: bool = False

    @model_validator(mode="after")
    def seed_is_present(self) -> "OpenDiscoveryRequest":
        if not (self.seed_smiles or self.seed_compound_name):
            raise ValueError("seed_smiles or seed_compound_name is required")
        return self


class SourceEvidence(BaseModel):
    evidence_id: str
    source_code: str
    source_name: str
    mode: Literal["local-registry", "official-api", "link-out", "computation"]
    status: Literal["resolved", "available", "deferred", "failed"]
    url: str
    statement: str
    licence_note: str
    source_record_id: str | None = None
    retrieved_at: datetime


class WorkflowEvent(BaseModel):
    sequence: int
    stage: str
    label: str
    status: Literal["completed", "completed-with-warning", "skipped", "failed"]
    message: str
    duration_ms: int = Field(ge=0)
    metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class CandidateScoreComponent(BaseModel):
    code: str
    label: str
    normalized_value: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=100)
    explanation: str


class CandidateAssessment(BaseModel):
    rank: int = Field(ge=1)
    compound_id: str
    display_name: str
    source_name: str
    source_record_id: str
    canonical_smiles: str
    inchikey: str
    similarity_to_seed: float = Field(ge=0, le=1)
    descriptors: DescriptorSet
    lipinski_violations: list[str]
    pains_alerts: list[str]
    brenk_alerts: list[str]
    nih_alerts: list[str]
    quality_flags: list[str]
    priority_score: float = Field(ge=0, le=100)
    score_components: list[CandidateScoreComponent]
    disposition: Literal["prioritize", "review", "deprioritize"]
    disposition_reason: str


class DockingReadiness(BaseModel):
    status: Literal["ready", "not-ready", "not-run"]
    engine: str = "AutoDock Vina"
    executable_detected: bool
    receptor_id: str | None = None
    required_inputs: list[str]
    missing_inputs: list[str]
    run_manifest: dict[str, str | float | int | bool | None]
    result_score_kcal_mol: float | None = None
    scientific_boundary: str


class DockingBox(BaseModel):
    center_x: float = Field(ge=-1000, le=1000)
    center_y: float = Field(ge=-1000, le=1000)
    center_z: float = Field(ge=-1000, le=1000)
    size_x: float = Field(gt=0, le=50)
    size_y: float = Field(gt=0, le=50)
    size_z: float = Field(gt=0, le=50)

    @model_validator(mode="after")
    def minimum_box_size(self) -> "DockingBox":
        if min(self.size_x, self.size_y, self.size_z) < 6:
            raise ValueError("each docking-box dimension must be at least 6 Å")
        return self


class VinaDockingRequest(BaseModel):
    receptor_filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\.pdbqt$")
    receptor_content_base64: str = Field(min_length=4, max_length=70_000_000)
    ligand_filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\.pdbqt$")
    ligand_content_base64: str = Field(min_length=4, max_length=15_000_000)
    box: DockingBox
    scoring_function: Literal["vina", "vinardo"] = "vina"
    exhaustiveness: int = Field(default=8, ge=1, le=64)
    num_modes: int = Field(default=9, ge=1, le=20)
    energy_range: float = Field(default=3.0, ge=1, le=10)
    cpu: int = Field(default=1, ge=1, le=16)
    seed: int = Field(default=20260822, ge=1, le=2_147_483_647)
    timeout_seconds: int = Field(default=300, ge=10, le=3600)
    open_discovery_run_id: str | None = Field(default=None, pattern=r"^ODR-[A-Z0-9]{12}$")


class VinaPose(BaseModel):
    rank: int = Field(ge=1)
    affinity_kcal_mol: float
    raw_energy_terms: list[float]


class VinaDockingJob(BaseModel):
    job_id: str
    status: Literal["completed", "blocked", "failed", "timed-out"]
    engine: str = "AutoDock Vina"
    engine_version: str | None = None
    scoring_function: Literal["vina", "vinardo"]
    receptor_filename: str
    receptor_sha256: str
    receptor_object_uri: str
    ligand_filename: str
    ligand_sha256: str
    ligand_object_uri: str
    output_sha256: str | None = None
    output_object_uri: str | None = None
    output_filename: str | None = None
    output_pdbqt_base64: str | None = None
    box: DockingBox
    exhaustiveness: int
    num_modes_requested: int
    num_modes_returned: int
    energy_range: float
    cpu: int
    seed: int
    duration_seconds: float = Field(ge=0)
    poses: list[VinaPose]
    warnings: list[str]
    error: str | None = None
    open_discovery_run_id: str | None = None
    command_manifest: list[str]
    scientific_boundary: str
    created_at: datetime


class DockingBenchmarkRequest(BaseModel):
    docking_job_id: str = Field(pattern=r"^VIN-[A-Z0-9]{12}$")
    reference_ligand_filename: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\.pdbqt$"
    )
    reference_ligand_content_base64: str = Field(min_length=4, max_length=15_000_000)
    rmsd_pass_threshold_angstrom: float = Field(default=2.0, gt=0, le=10)


class DockingPoseBenchmark(BaseModel):
    pose_rank: int = Field(ge=1)
    affinity_kcal_mol: float | None = None
    aligned_heavy_atom_rmsd_angstrom: float = Field(ge=0)
    atom_count: int = Field(ge=1)


class DockingBenchmarkRun(BaseModel):
    benchmark_id: str
    docking_job_id: str
    status: Literal["passed", "failed", "invalid"]
    method: str
    rmsd_pass_threshold_angstrom: float
    best_pose_rank: int | None = None
    best_rmsd_angstrom: float | None = None
    pose_results: list[DockingPoseBenchmark] = Field(default_factory=list)
    reference_sha256: str
    reference_object_uri: str
    atom_type_order_match: bool
    scoring_qualified: bool = False
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    scientific_boundary: str


class OpenDiscoveryRun(BaseModel):
    run_id: str
    status: Literal["completed", "completed-with-warning", "failed"]
    execution_mode: Literal["local-python", "local-python-plus-public-apis"]
    request: OpenDiscoveryRequest
    seed: StandardizedCompound
    seed_name: str
    events: list[WorkflowEvent]
    evidence: list[SourceEvidence]
    candidates: list[CandidateAssessment]
    docking: DockingReadiness
    next_actions: list[str]
    claim_boundary: str
    created_at: datetime
