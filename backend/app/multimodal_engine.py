from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .assistant import CLINICAL_PATTERNS, PROMPT_ATTACK_PATTERNS, ScientificAssistantService
from .config import settings
from .model_gateway import ModelAdapterUnavailable, ScientificModelGateway
from .repository import Repository
from .schemas import (
    AssistantQuery,
    ModalityAssessment,
    MultimodalCaseRequest,
    MultimodalCaseResult,
    MultimodalEvidence,
    MultimodalReviewRequest,
    MultimodalReviewResult,
    MultimodalTraceEvent,
)


MODALITY_ORDER = ("chemistry", "protein", "assay", "documents", "imaging")


class MultimodalResearchEngine:
    """Evidence-first orchestration across scientific modalities.

    The engine exposes a reviewable operational trace, not private model reasoning.
    Quantitative scientific values must originate from a versioned specialist model,
    registered structure, or supplied assay record; the language model never invents them.
    """

    def __init__(
        self,
        repository: Repository,
        assistant: ScientificAssistantService,
        gateway: ScientificModelGateway | None = None,
    ) -> None:
        self.repository = repository
        self.assistant = assistant
        self.gateway = gateway or ScientificModelGateway()

    def capabilities(self) -> dict[str, Any]:
        return {
            "enabled": settings.multimodal_enabled,
            "modalities": list(MODALITY_ORDER),
            "model_adapters": self.gateway.capabilities(),
            "local_chemistry": True,
            "document_rag": True,
            "visible_operational_trace": True,
            "hidden_chain_of_thought_returned": False,
            "confidence_ceiling": 0.75,
            "abstention": True,
            "human_approval_required": True,
            "automatic_lab_execution": False,
            "automatic_retraining": False,
        }

    def run(self, request: MultimodalCaseRequest, actor: str, role: str) -> MultimodalCaseResult:
        case_id = self.repository.new_id("MMC")
        lowered = request.question.casefold()
        if any(pattern in lowered for pattern in PROMPT_ATTACK_PATTERNS):
            return self._blocked(case_id, request, actor, "Prompt-override pattern detected")
        if any(pattern in lowered for pattern in CLINICAL_PATTERNS):
            return self._blocked(case_id, request, actor, "Patient-specific clinical request detected")

        assessments: list[ModalityAssessment] = []
        evidence: list[MultimodalEvidence] = []
        missing: list[str] = []
        trace: list[MultimodalTraceEvent] = [MultimodalTraceEvent(
            sequence=1,
            stage="safety-boundary",
            status="completed",
            message="Research-use, prompt-injection and clinical-advice boundaries passed",
            metrics={"automatic_lab_execution": False, "automatic_retraining": False},
        )]

        for modality in MODALITY_ORDER:
            if modality not in request.requested_modalities:
                assessments.append(ModalityAssessment(modality=modality, status="skipped"))
                trace.append(self._trace(trace, modality, "skipped", "Modality not requested"))
                continue
            assessment, items, modality_missing = getattr(self, f"_{modality}")(
                request, actor=actor, role=role
            )
            assessments.append(assessment)
            evidence.extend(items)
            missing.extend(modality_missing)
            trace.append(self._trace(
                trace,
                modality,
                assessment.status,
                assessment.findings[0] if assessment.findings else assessment.warnings[0],
                {"evidence_count": len(items), "confidence": assessment.confidence},
            ))

        substantive = [item for item in evidence if item.modality in {"documents", "assay"}]
        completed = [item for item in assessments if item.status.startswith("completed")]
        conflicts = self._conflicts(assessments)
        cited = len({item.evidence_id for item in evidence})
        findings = sum(len(item.findings) for item in completed)
        citation_coverage = min(1.0, cited / max(1, findings))
        confidence = min(
            0.75,
            (sum(item.confidence for item in completed) / max(1, len(completed)))
            * citation_coverage
            * (0.8 if conflicts else 1.0),
        )
        abstained = not substantive or citation_coverage < 0.5 or confidence < 0.35
        if abstained:
            status = "abstained"
            recommendation = (
                "No compound or laboratory action is recommended because the case lacks sufficient "
                "cited assay or document evidence."
            )
            next_actions = [
                "Attach an approved, versioned paper or immutable assay result relevant to the exact endpoint.",
                "Resolve missing protein, cell-line and control metadata, then rerun the case.",
                "Ask a named supervisor to review the evidence package before any wet-lab action.",
            ]
        else:
            status = "completed"
            recommendation = (
                "Advance only to supervisor review of the cited evidence package; do not treat this "
                "computational synthesis as measured activity or laboratory authorization."
            )
            next_actions = [
                "Resolve every conflict and warning against the original source.",
                "Lock the endpoint, controls, plate map and acceptance criteria in an approved protocol.",
                "Record a named scientist's approval before creating an experimental work order.",
            ]
        rationale = [
            f"{len(completed)} requested modalities completed or completed with warnings.",
            f"{cited} immutable or source-resolvable evidence identifiers support the visible findings.",
            "Confidence is capped at 0.75 and reduced for missing citations or cross-modality conflicts.",
        ]
        result = MultimodalCaseResult(
            case_id=case_id,
            status=status,
            question=request.question,
            assessments=assessments,
            evidence=evidence,
            recommendation=recommendation,
            rationale=rationale,
            next_actions=next_actions,
            missing_information=list(dict.fromkeys(missing)),
            conflicts=conflicts,
            confidence=round(confidence, 4),
            citation_coverage=round(citation_coverage, 4),
            abstained=abstained,
            trace=trace,
            created_at=datetime.now(UTC),
        )
        self._persist(result, actor)
        return result

    def get(self, case_id: str) -> MultimodalCaseResult | None:
        payload = self.repository.get_multimodal_case(case_id)
        return MultimodalCaseResult.model_validate(payload) if payload else None

    def review(
        self,
        case_id: str,
        request: MultimodalReviewRequest,
        *,
        actor: str,
        role: str,
    ) -> MultimodalReviewResult:
        if role not in {"reviewer", "instructor", "admin"}:
            raise PermissionError("Reviewer, instructor or admin role required")
        case = self.get(case_id)
        if not case:
            raise KeyError("Multimodal case not found")
        known_ids = {item.evidence_id for item in case.evidence}
        unknown = set(request.supporting_evidence_ids) - known_ids
        if unknown:
            raise ValueError("Review cites evidence IDs that were not supplied with the case")
        exclusion_reasons: list[str] = []
        if request.decision != "approved-for-review":
            exclusion_reasons.append("Review decision is not approved")
        if not request.measured_data:
            exclusion_reasons.append("Feedback is not linked to measured data")
        if not request.qc_passed:
            exclusion_reasons.append("Measured data did not pass assay QC")
        if not request.raw_sha256:
            exclusion_reasons.append("Immutable raw-data SHA-256 is missing")
        if case.abstained:
            exclusion_reasons.append("The source case abstained")
        if not request.supporting_evidence_ids:
            exclusion_reasons.append("No case evidence IDs were confirmed by the reviewer")
        result = MultimodalReviewResult(
            review_id=self.repository.new_id("MMR"), case_id=case_id,
            decision=request.decision, reviewer=actor, reviewer_notes=request.reviewer_notes,
            correction=request.correction,
            supporting_evidence_ids=request.supporting_evidence_ids,
            training_candidate=not exclusion_reasons,
            exclusion_reasons=exclusion_reasons, created_at=datetime.now(UTC),
        )
        payload = result.model_dump(mode="json")
        self.repository.save_multimodal_review(payload)
        self.repository.audit(actor, "multimodal.review_recorded", "multimodal_case", case_id, {
            "review_id": result.review_id, "decision": result.decision,
            "training_candidate": result.training_candidate, "training_applied": False,
            "exclusion_reasons": result.exclusion_reasons,
        })
        return result

    def _chemistry(self, request: MultimodalCaseRequest, **_: Any):
        compounds = self.repository.get_compounds(request.compound_ids)
        missing_ids = set(request.compound_ids) - {item.compound_id for item in compounds}
        evidence: list[MultimodalEvidence] = []
        findings: list[str] = []
        grades = {"A": 0.7, "B": 0.6, "C": 0.45, "D": 0.3}
        for compound in compounds:
            evidence_id = f"CMP:{compound.compound_id}"
            evidence.append(MultimodalEvidence(
                evidence_id=evidence_id,
                modality="chemistry",
                source=compound.source_name,
                source_version="registry-record",
                citation=f"{compound.source_name}:{compound.source_id}",
                finding=(
                    f"Registered identity {compound.display_name}; MW {compound.descriptors.molecular_weight:.2f}, "
                    f"cLogP {compound.descriptors.clogp:.2f}, QED {compound.descriptors.qed:.2f}."
                ),
                confidence=grades[compound.evidence_grade],
            ))
            findings.append(evidence[-1].finding)
        warnings = []
        missing = []
        if missing_ids:
            warnings.append(f"Unresolved compound IDs: {', '.join(sorted(missing_ids))}")
        if not compounds:
            missing.append("At least one standardized compound identity")
            return ModalityAssessment(
                modality="chemistry", status="blocked", warnings=["No registered compound was supplied"]
            ), evidence, missing
        adapter = self._optional_adapter("chemistry", request, evidence)
        if adapter:
            findings.extend(adapter["findings"])
            warnings.extend(adapter["warnings"])
        confidence = sum(item.confidence for item in evidence) / len(evidence)
        return ModalityAssessment(
            modality="chemistry",
            status="completed-with-warning" if warnings else "completed",
            model_name=adapter["model_name"] if adapter else "RDKit registry descriptors",
            model_version=adapter["model_version"] if adapter else settings.standardization_version,
            evidence_ids=[item.evidence_id for item in evidence],
            confidence=confidence,
            findings=findings,
            warnings=warnings,
        ), evidence, missing

    def _protein(self, request: MultimodalCaseRequest, **_: Any):
        if not request.protein_accession:
            return ModalityAssessment(
                modality="protein", status="blocked", warnings=["No UniProt accession was supplied"]
            ), [], ["Reviewed UniProt accession and target identity"]
        try:
            adapter = self.gateway.invoke("protein", self._adapter_payload(request, []))
        except ModelAdapterUnavailable as exc:
            return ModalityAssessment(
                modality="protein", status="blocked", warnings=[str(exc)]
            ), [], ["Configured, validated protein-model service or reviewed structure evidence"]
        evidence = self._adapter_evidence("protein", adapter)
        return ModalityAssessment(
            modality="protein", status="completed",
            model_name=adapter["model_name"], model_version=adapter["model_version"],
            evidence_ids=[item.evidence_id for item in evidence],
            confidence=adapter["confidence"], findings=adapter["findings"], warnings=adapter["warnings"],
        ), evidence, []

    def _assay(self, request: MultimodalCaseRequest, **_: Any):
        if not request.assay_summary:
            return ModalityAssessment(
                modality="assay", status="blocked", warnings=["No immutable assay summary was supplied"]
            ), [], ["Immutable assay result with controls, units, replicates and QC status"]
        checksum = str(request.assay_summary.get("sha256", ""))
        qc_status = str(request.assay_summary.get("qc_status", "unknown"))
        source_id = str(request.assay_summary.get("result_id", "unresolved"))
        verified = len(checksum) == 64 and qc_status.casefold() == "passed"
        finding = f"Assay summary {source_id} reports QC status {qc_status}; values remain study-specific."
        evidence = [MultimodalEvidence(
            evidence_id=f"ASSAY:{source_id}", modality="assay", source="OSIEL immutable assay store",
            source_version=str(request.assay_summary.get("source_version", "unknown")),
            citation=f"OSIEL result {source_id}", finding=finding,
            confidence=0.7 if verified else 0.25, checksum=checksum if len(checksum) == 64 else None,
        )]
        warnings = [] if verified else ["Assay summary lacks a passing QC state or valid SHA-256 checksum"]
        return ModalityAssessment(
            modality="assay", status="completed" if verified else "completed-with-warning",
            model_name="validated-assay-parser", model_version="OSIEL-ASSAY-1.0",
            evidence_ids=[evidence[0].evidence_id], confidence=evidence[0].confidence,
            findings=[finding], warnings=warnings,
        ), evidence, ([] if verified else ["Qualified assay QC and immutable raw-file checksum"])

    def _documents(self, request: MultimodalCaseRequest, *, actor: str, role: str):
        answer = self.assistant.answer(AssistantQuery(
            question=request.question,
            cancer_type=request.cancer_type,
            compound_ids=request.compound_ids,
            project_scope=request.project_scope,
            course_scope=request.course_scope,
            document_ids=request.document_ids,
            persist=False,
        ), actor=actor, role=role)
        evidence: list[MultimodalEvidence] = []
        for item in answer.evidence:
            if item.get("kind") not in {"literature", "document-chunk"}:
                continue
            evidence.append(MultimodalEvidence(
                evidence_id=str(item.get("evidence_id")), modality="documents",
                source=str(item.get("source") or item.get("title") or "approved corpus"),
                source_version=str(item.get("source_version") or item.get("year") or "versioned-record"),
                citation=str(item.get("url") or item.get("citation") or item.get("evidence_id")),
                finding=str(item.get("statement") or item.get("text") or "Retrieved evidence passage")[:1000],
                confidence=min(0.7, max(0.2, answer.retrieval_score)),
                checksum=str(item.get("text_sha256")) if item.get("text_sha256") else None,
            ))
        status = "completed" if evidence and not answer.abstained else "blocked"
        return ModalityAssessment(
            modality="documents", status=status,
            model_name=answer.model or "deterministic evidence retrieval",
            model_version="OSIEL-PROFESSOR-RAG-1.0",
            evidence_ids=[item.evidence_id for item in evidence],
            confidence=min(0.7, answer.retrieval_score) if evidence else 0,
            findings=[answer.answer] if evidence else [],
            warnings=answer.warnings if evidence else ["Professor AI abstained: no sufficient scoped evidence"],
        ), evidence, answer.missing_information

    def _imaging(self, request: MultimodalCaseRequest, **_: Any):
        images = [item for item in request.artifacts if item.media_type == "microscopy-image"]
        if not images:
            return ModalityAssessment(
                modality="imaging", status="blocked", warnings=["No immutable microscopy image was supplied"]
            ), [], ["Microscopy image checksum, acquisition metadata and validated analysis model"]
        try:
            adapter = self.gateway.invoke("imaging", self._adapter_payload(request, []))
        except ModelAdapterUnavailable as exc:
            return ModalityAssessment(
                modality="imaging", status="blocked", warnings=[str(exc)]
            ), [], ["Configured and benchmarked image-analysis service"]
        evidence = self._adapter_evidence("imaging", adapter)
        warnings = [*adapter["warnings"], "Image features are phenotypic measurements, not diagnosis"]
        return ModalityAssessment(
            modality="imaging", status="completed-with-warning",
            model_name=adapter["model_name"], model_version=adapter["model_version"],
            evidence_ids=[item.evidence_id for item in evidence], confidence=adapter["confidence"],
            findings=adapter["findings"], warnings=warnings,
        ), evidence, []

    def _optional_adapter(self, modality: str, request: MultimodalCaseRequest, evidence: list[MultimodalEvidence]):
        try:
            return self.gateway.invoke(modality, self._adapter_payload(request, evidence))
        except ModelAdapterUnavailable:
            return None

    @staticmethod
    def _adapter_payload(request: MultimodalCaseRequest, evidence: list[MultimodalEvidence]) -> dict[str, Any]:
        return {
            "question": request.question,
            "cancer_type": request.cancer_type,
            "cell_line": request.cell_line,
            "target_name": request.target_name,
            "protein_accession": request.protein_accession,
            "compound_ids": request.compound_ids,
            "artifacts": [item.model_dump() for item in request.artifacts],
            "evidence": [item.model_dump() for item in evidence],
            "research_use_only": True,
        }

    @staticmethod
    def _adapter_evidence(modality: str, adapter: dict[str, Any]) -> list[MultimodalEvidence]:
        rows: list[MultimodalEvidence] = []
        for index, item in enumerate(adapter["evidence"][:20]):
            if not isinstance(item, dict) or not item.get("citation"):
                continue
            rows.append(MultimodalEvidence(
                evidence_id=str(item.get("evidence_id") or f"{modality.upper()}:{index + 1}"),
                modality=modality,
                source=str(item.get("source") or adapter["model_name"]),
                source_version=str(item.get("source_version") or adapter["model_version"]),
                citation=str(item["citation"]),
                finding=str(item.get("finding") or adapter["findings"][0])[:1000],
                confidence=min(0.75, adapter["confidence"]),
                checksum=str(item.get("checksum")) if item.get("checksum") else None,
            ))
        return rows

    @staticmethod
    def _conflicts(assessments: list[ModalityAssessment]) -> list[str]:
        positive = any("support" in finding.casefold() for item in assessments for finding in item.findings)
        negative = any(
            token in finding.casefold()
            for item in assessments for finding in item.findings
            for token in ("does not support", "inactive", "failed qc", "contraindicat")
        )
        return ["Modalities contain both supporting and non-supporting findings; resolve against raw evidence."] if positive and negative else []

    @staticmethod
    def _trace(
        trace: list[MultimodalTraceEvent], stage: str, status: str, message: str,
        metrics: dict[str, Any] | None = None,
    ) -> MultimodalTraceEvent:
        return MultimodalTraceEvent(
            sequence=len(trace) + 1, stage=stage, status=status,
            message=message[:500], metrics=metrics or {},
        )

    def _blocked(
        self, case_id: str, request: MultimodalCaseRequest, actor: str, reason: str
    ) -> MultimodalCaseResult:
        result = MultimodalCaseResult(
            case_id=case_id, status="blocked", question=request.question,
            assessments=[], evidence=[],
            recommendation="No recommendation was generated because the safety boundary blocked the request.",
            rationale=[reason], next_actions=["Reframe this as a supervised, non-clinical research question."],
            missing_information=[], conflicts=[], confidence=0, citation_coverage=0, abstained=True,
            trace=[MultimodalTraceEvent(
                sequence=1, stage="safety-boundary", status="blocked", message=reason,
            )], created_at=datetime.now(UTC),
        )
        self._persist(result, actor)
        return result

    def _persist(self, result: MultimodalCaseResult, actor: str) -> None:
        payload = result.model_dump(mode="json")
        self.repository.save_multimodal_case(result.case_id, result.status, actor, payload)
        self.repository.audit(actor, "multimodal.case_completed", "multimodal_case", result.case_id, {
            "status": result.status,
            "confidence": result.confidence,
            "evidence_count": len(result.evidence),
            "human_approval_required": True,
        })
