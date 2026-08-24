from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from .config import settings
from .connectors.ollama import OllamaClient, OllamaUnavailable
from .knowledge import ScientificKnowledgeService
from .literature import RECORDS, LiteratureRecord
from .repository import Repository
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
)


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9+.-]{1,}")
STOP_WORDS = {
    "about", "after", "before", "could", "from", "have", "into", "should",
    "that", "their", "then", "these", "this", "what", "when", "where",
    "which", "with", "would",
}
PROMPT_ATTACK_PATTERNS = (
    "ignore previous", "ignore all previous", "reveal system prompt",
    "show hidden prompt", "developer message", "bypass safety", "jailbreak",
)
CLINICAL_PATTERNS = (
    "dose for a patient", "dose for my patient", "prescribe", "diagnose me",
    "diagnose this patient", "treatment for this patient", "replace my oncologist",
)
PRIVILEGED_ROLES = {"reviewer", "instructor", "admin"}
EVALUATION_THRESHOLDS = {
    "citation_precision": 1.0,
    "expected_citation_recall": 0.8,
    "abstention_accuracy": 0.8,
    "unsupported_answer_rate": 0.0,
}


def _tokens(*values: str | None) -> set[str]:
    return {
        token.lower()
        for value in values
        for token in TOKEN_PATTERN.findall(value or "")
        if len(token) > 2 and token.lower() not in STOP_WORDS
    }


def _record_text(record: LiteratureRecord) -> str:
    return " ".join((
        record.title, record.compound, record.biological_model, record.assay,
        record.finding, record.evidence_level,
    ))


class ScientificAssistantService:
    """Governed, self-hosted scientific RAG and faculty-review workflow.

    The language model is a constrained prose composer, never a quantitative
    oncology model. Every non-abstaining model answer must cite an exact evidence
    identifier supplied by scoped retrieval. Conversation turns, feedback and
    evaluations are persisted without triggering automatic retraining.
    """

    def __init__(
        self,
        repository: Repository,
        ollama_client: OllamaClient | None = None,
        knowledge_service: ScientificKnowledgeService | None = None,
    ) -> None:
        self.repository = repository
        self.ollama = ollama_client or OllamaClient()
        self.knowledge = knowledge_service or ScientificKnowledgeService(
            repository, ollama_client=self.ollama
        )

    def capability(self) -> dict[str, object]:
        payload = self.ollama.capability()
        payload.update(self.knowledge.capability())
        payload.update({
            "curated_record_count": len(RECORDS),
            "citation_granularity": "PDF/text page and immutable chunk, plus curated PubMed record",
            "prompt_injection_filter": True,
            "clinical_advice_blocked": True,
            "fallback": "evidence-listing abstention; no unsupported scientific synthesis",
            "faculty_feedback": True,
            "answer_evaluations": True,
            "conversation_retention_days": settings.professor_retention_days,
            "automatic_retraining": False,
            "automatic_experiment_authorization": False,
        })
        return payload

    def create_conversation(
        self, request: AssistantConversationCreate, *, actor: str
    ) -> AssistantConversation:
        now = datetime.now(UTC)
        conversation = AssistantConversation(
            conversation_id=self.repository.new_id("CON"),
            title=request.title,
            project_scope=request.project_scope,
            course_scope=request.course_scope,
            owner_actor=actor,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.repository.create_assistant_conversation(conversation.model_dump(mode="json"))
        self.repository.audit(
            actor, "assistant.conversation_created", "assistant_conversation",
            conversation.conversation_id,
            {"project_scope": conversation.project_scope, "course_scope": conversation.course_scope},
        )
        return conversation

    def list_conversations(self, *, actor: str) -> list[AssistantConversation]:
        return [
            AssistantConversation.model_validate(item)
            for item in self.repository.list_assistant_conversations(actor)
        ]

    def conversation_turns(
        self, conversation_id: str, *, actor: str, role: str
    ) -> list[dict[str, Any]]:
        conversation = self._authorized_conversation(conversation_id, actor, role)
        return self.repository.list_assistant_turns(conversation["conversation_id"])

    def answer(
        self,
        query: AssistantQuery,
        *,
        actor: str = "demo-researcher",
        role: str = "researcher",
    ) -> AssistantAnswer:
        conversation = self._resolve_conversation(query, actor, role)
        guardrail_trace = {
            "stage": "safety-boundary",
            "status": "completed",
            "message": "Checked prompt override and patient-specific clinical patterns",
            "metrics": {"clinical_advice_blocked": True, "prompt_override_blocked": True},
        }
        lowered = query.question.casefold()
        if any(pattern in lowered for pattern in PROMPT_ATTACK_PATTERNS):
            result = self._abstention(
                "I cannot follow instructions that attempt to override the evidence and safety boundary. Ask a scientific question that can be answered from reviewable sources.",
                "Rephrase the research question and keep experimental decisions under named supervisor review.",
                ["A research question tied to a defined study context"],
                warning="Prompt-override pattern detected; retrieval and the local model were not called.",
                trace=[{**guardrail_trace, "status": "blocked", "message": "Prompt-override pattern blocked"}],
                guardrail="prompt-injection-block",
            )
            return self._finalize(query, result, actor, conversation)
        if any(pattern in lowered for pattern in CLINICAL_PATTERNS):
            result = self._abstention(
                "OSIEL cannot provide patient-specific diagnosis, prescribing, dosing, or treatment advice.",
                "Refer the clinical question to a qualified healthcare professional and keep OSIEL limited to supervised research workflow guidance.",
                ["A non-clinical, research-use question"],
                warning="Clinical-advice boundary activated; retrieval and the local model were not called.",
                trace=[{**guardrail_trace, "status": "blocked", "message": "Patient-specific clinical request blocked"}],
                guardrail="clinical-advice-block",
            )
            return self._finalize(query, result, actor, conversation)

        compounds = self.repository.get_compounds(query.compound_ids)
        evidence = self._compound_evidence(compounds)
        literature = self._retrieve_literature(
            query.question, query.cancer_type,
            (compound.display_name for compound in compounds),
        )
        literature_evidence = self._literature_evidence(literature)
        evidence.extend(literature_evidence)
        document_evidence, retrieval_trace, document_score, retrieval_warnings = self.knowledge.retrieve(
            query.question,
            project_scope=query.project_scope,
            course_scope=query.course_scope,
            document_ids=query.document_ids,
        )
        evidence.extend(document_evidence)
        trace = [guardrail_trace, {
            "stage": "registry-context",
            "status": "completed",
            "message": "Resolved selected compounds and curated study records",
            "metrics": {"compounds": len(compounds), "curated_records": len(literature_evidence)},
        }, *retrieval_trace]
        context = query.cancer_type or "the selected oncology research context"
        missing = self._missing_information(query, bool(compounds))
        substantive = [
            item for item in evidence
            if item.get("kind") in {"literature", "document-chunk"}
        ]
        retrieval_score = max(document_score, 0.45 if literature_evidence else 0.0)

        if not substantive:
            result = self._abstention(
                "I do not have sufficient scoped evidence to answer this scientific question. No conclusion was generated.",
                "Add an approved paper or select a question covered by the controlled corpus, then ask again.",
                missing + ["At least one directly relevant approved evidence passage"],
                warning="Retrieval returned no substantive literature or document evidence.",
                trace=trace,
                guardrail="evidence-sufficiency-gate",
                evidence=evidence,
                retrieval_score=retrieval_score,
                embedding_model=self.ollama.embedding_model if self.ollama.enabled else None,
            )
            return self._finalize(query, result, actor, conversation)

        if self.ollama.enabled:
            try:
                result = self.ollama.answer(
                    question=query.question,
                    evidence=evidence,
                    research_context=(
                        f"Project scope: {query.project_scope}. Course scope: {query.course_scope}. "
                        f"Oncology context: {context}. Selected compounds: "
                        f"{', '.join(compound.display_name for compound in compounds) or 'none'}. "
                        "The output is research navigation and requires supervisor review."
                    ),
                )
                cited = set(result.cited_evidence_ids)
                returned_evidence = [
                    {**item, "used_by_model": item["evidence_id"] in cited}
                    for item in evidence
                ]
                trace.extend([
                    {
                        "stage": "grounded-generation",
                        "status": "completed" if not result.abstained else "completed-with-warning",
                        "message": "Generated and schema-validated a local answer",
                        "metrics": {"model": self.ollama.model, "cited_records": len(cited), "abstained": result.abstained},
                    },
                    {
                        "stage": "citation-validation",
                        "status": "completed",
                        "message": "Verified that every citation ID was present in supplied evidence",
                        "metrics": {"citation_precision": 1.0 if cited else 0.0},
                    },
                ])
                answer = AssistantAnswer(
                    answer=result.answer,
                    evidence=returned_evidence,
                    missing_information=result.missing_information or missing,
                    recommended_action=result.recommended_action,
                    mode="hybrid-ollama-rag" if document_evidence else "local-ollama-rag",
                    model=self.ollama.model,
                    embedding_model=(
                        self.ollama.embedding_model
                        if any(item.get("embedding_model") for item in document_evidence)
                        else None
                    ),
                    abstained=result.abstained,
                    confidence=result.confidence,
                    retrieval_score=retrieval_score,
                    citation_coverage=1.0 if cited else 0.0,
                    retrieval_trace=trace,
                    guardrails=[
                        "evidence-only-generation", "exact-citation-ID-validation",
                        "clinical-advice-block", "supervisor-decision-boundary",
                    ],
                    warnings=[
                        "Local language-model prose is unvalidated and must be checked against every cited passage.",
                        *retrieval_warnings,
                    ],
                )
                return self._finalize(query, answer, actor, conversation)
            except OllamaUnavailable as exc:
                retrieval_warnings.append(str(exc))

        result = self._deterministic_answer(
            context, compounds, evidence, missing,
            retrieval_score=retrieval_score, trace=trace, warnings=retrieval_warnings,
        )
        return self._finalize(query, result, actor, conversation)

    def record_feedback(
        self,
        answer_id: str,
        request: AssistantFeedbackRequest,
        *,
        actor: str,
        role: str,
    ) -> AssistantFeedback:
        if role not in PRIVILEGED_ROLES:
            raise PermissionError("Reviewer, instructor or admin role required for answer correction")
        stored = self.repository.get_assistant_answer(answer_id)
        if not stored:
            raise KeyError("Assistant answer not found")
        answer_payload = stored.get("answer", stored)
        allowed_ids = {
            item.get("evidence_id") for item in answer_payload.get("evidence", [])
            if item.get("evidence_id")
        }
        unknown = set(request.supporting_evidence_ids) - allowed_ids
        if unknown:
            raise ValueError("Feedback cites evidence that was not supplied with the answer")
        if request.decision in {"partially-correct", "incorrect", "unsafe"} and not request.correction:
            raise ValueError("A correction is required for non-correct feedback")
        feedback = AssistantFeedback(
            feedback_id=self.repository.new_id("FBK"),
            answer_id=answer_id,
            decision=request.decision,
            correction=request.correction,
            reviewer_notes=request.reviewer_notes,
            supporting_evidence_ids=request.supporting_evidence_ids,
            reviewer=actor,
            training_applied=False,
            created_at=datetime.now(UTC),
        )
        self.repository.save_assistant_feedback(feedback.model_dump(mode="json"))
        self.repository.audit(
            actor, "assistant.feedback_recorded", "assistant_answer", answer_id,
            {"feedback_id": feedback.feedback_id, "decision": feedback.decision, "training_applied": False},
        )
        return feedback

    def evaluate(
        self,
        request: AssistantEvaluationRequest,
        *,
        actor: str,
        role: str,
    ) -> AssistantEvaluationRun:
        if role not in PRIVILEGED_ROLES:
            raise PermissionError("Reviewer, instructor or admin role required for assistant evaluation")
        dataset_payload = request.model_dump(mode="json")
        dataset_bytes = json.dumps(dataset_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        dataset_sha256 = hashlib.sha256(dataset_bytes).hexdigest()
        _, dataset_uri = self.knowledge.store.put(
            dataset_bytes, f"assistant-evaluation-{dataset_sha256[:12]}.json",
            {"kind": "assistant-evaluation-dataset", "actor": actor},
        )
        case_results: list[dict[str, Any]] = []
        correct_abstentions = expected_total = expected_found = 0
        cited_total = valid_cited = unsupported = 0
        for case in request.cases:
            answer = self.answer(
                AssistantQuery(
                    question=case.question,
                    cancer_type=case.cancer_type,
                    project_scope=case.project_scope,
                    course_scope=case.course_scope,
                    persist=False,
                ),
                actor=actor,
                role=role,
            )
            evidence_ids = {
                str(item["evidence_id"]) for item in answer.evidence if item.get("evidence_id")
            }
            cited_ids = {
                str(item["evidence_id"]) for item in answer.evidence
                if item.get("evidence_id") and item.get("used_by_model")
            }
            expected = set(case.expected_evidence_ids)
            expected_total += len(expected)
            expected_found += len(expected & cited_ids)
            cited_total += len(cited_ids)
            valid_cited += len(cited_ids & evidence_ids)
            abstention_correct = answer.abstained == case.expect_abstention
            correct_abstentions += int(abstention_correct)
            unsupported_answer = not answer.abstained and not cited_ids
            unsupported += int(unsupported_answer)
            case_results.append({
                "case_id": case.case_id,
                "abstained": answer.abstained,
                "expected_abstention": case.expect_abstention,
                "abstention_correct": abstention_correct,
                "expected_evidence_ids": sorted(expected),
                "cited_evidence_ids": sorted(cited_ids),
                "unsupported_answer": unsupported_answer,
                "mode": answer.mode,
            })
        citation_precision = valid_cited / cited_total if cited_total else 1.0
        expected_recall = expected_found / expected_total if expected_total else 1.0
        abstention_accuracy = correct_abstentions / len(request.cases)
        unsupported_rate = unsupported / len(request.cases)
        passed = (
            citation_precision >= EVALUATION_THRESHOLDS["citation_precision"]
            and expected_recall >= EVALUATION_THRESHOLDS["expected_citation_recall"]
            and abstention_accuracy >= EVALUATION_THRESHOLDS["abstention_accuracy"]
            and unsupported_rate <= EVALUATION_THRESHOLDS["unsupported_answer_rate"]
        )
        evaluation = AssistantEvaluationRun(
            evaluation_id=self.repository.new_id("AEV"),
            dataset_label=request.dataset_label,
            dataset_sha256=dataset_sha256,
            case_count=len(request.cases),
            citation_precision=round(citation_precision, 4),
            expected_citation_recall=round(expected_recall, 4),
            abstention_accuracy=round(abstention_accuracy, 4),
            unsupported_answer_rate=round(unsupported_rate, 4),
            passed=passed,
            thresholds=EVALUATION_THRESHOLDS,
            case_results=case_results,
            model=self.ollama.model if self.ollama.enabled else None,
            embedding_model=self.ollama.embedding_model if self.ollama.enabled else None,
            created_by=actor,
            created_at=datetime.now(UTC),
            scientific_boundary=(
                "This evaluation measures citation and abstention controls on the supplied cases. "
                "It is not proof of biomedical correctness and requires faculty-authored test cases."
            ),
        )
        payload = evaluation.model_dump(mode="json")
        self.repository.save_assistant_evaluation(payload)
        self.repository.audit(
            actor, "assistant.evaluation_completed", "assistant_evaluation", evaluation.evaluation_id,
            {"dataset_sha256": dataset_sha256, "dataset_object_uri": dataset_uri,
             "case_count": len(request.cases), "passed": passed},
        )
        return evaluation

    def list_evaluations(self, limit: int = 50) -> list[AssistantEvaluationRun]:
        return [
            AssistantEvaluationRun.model_validate(item)
            for item in self.repository.list_assistant_evaluations(limit)
        ]

    def apply_retention(
        self,
        request: AssistantRetentionRequest,
        *,
        actor: str,
        role: str,
    ) -> AssistantRetentionResult:
        if role != "admin":
            raise PermissionError("Admin role required for conversation-retention maintenance")
        cutoff = datetime.now(UTC) - timedelta(days=request.retention_days)
        counts = self.repository.purge_assistant_conversations(
            cutoff.isoformat(),
            dry_run=request.dry_run,
        )
        result = AssistantRetentionResult(
            cutoff=cutoff,
            dry_run=request.dry_run,
            conversation_count=counts["conversation_count"],
            turn_count=counts["turn_count"],
            feedback_count=counts["feedback_count"],
            deleted=not request.dry_run and counts["conversation_count"] > 0,
        )
        self.repository.audit(
            actor,
            "assistant.retention_checked" if request.dry_run else "assistant.retention_applied",
            "assistant_conversation",
            "retention-policy",
            result.model_dump(mode="json"),
        )
        return result

    def _resolve_conversation(
        self, query: AssistantQuery, actor: str, role: str
    ) -> dict[str, Any] | None:
        if query.conversation_id:
            conversation = self._authorized_conversation(query.conversation_id, actor, role)
            if (conversation["project_scope"] != query.project_scope
                    or conversation["course_scope"] != query.course_scope):
                raise PermissionError("Query scope must match the persisted conversation scope")
            return conversation
        if not query.persist:
            return None
        created = self.create_conversation(
            AssistantConversationCreate(
                title=query.question.strip()[:120],
                project_scope=query.project_scope,
                course_scope=query.course_scope,
            ),
            actor=actor,
        )
        return created.model_dump(mode="json")

    def _authorized_conversation(
        self, conversation_id: str, actor: str, role: str
    ) -> dict[str, Any]:
        conversation = self.repository.get_assistant_conversation(conversation_id)
        if not conversation:
            raise KeyError("Assistant conversation not found")
        if conversation["owner_actor"] != actor and role not in PRIVILEGED_ROLES:
            raise PermissionError("Conversation belongs to another researcher")
        return conversation

    def _finalize(
        self,
        query: AssistantQuery,
        result: AssistantAnswer,
        actor: str,
        conversation: dict[str, Any] | None,
    ) -> AssistantAnswer:
        if not query.persist or not conversation:
            return result.model_copy(update={"created_at": datetime.now(UTC)})
        answer_id = self.repository.new_id("ANS")
        created_at = datetime.now(UTC)
        final = result.model_copy(update={
            "answer_id": answer_id,
            "conversation_id": conversation["conversation_id"],
            "created_at": created_at,
        })
        payload = {
            "answer_id": answer_id,
            "conversation_id": conversation["conversation_id"],
            "actor": actor,
            "question": query.question,
            "query": query.model_dump(mode="json"),
            "answer": final.model_dump(mode="json"),
            "created_at": created_at.isoformat(),
        }
        self.repository.save_assistant_turn(
            answer_id, conversation["conversation_id"], actor, payload
        )
        self.repository.audit(
            actor, "assistant.answer_recorded", "assistant_answer", answer_id,
            {"conversation_id": conversation["conversation_id"], "mode": final.mode,
             "abstained": final.abstained, "evidence_count": len(final.evidence),
             "citation_coverage": final.citation_coverage, "retrieval_score": final.retrieval_score},
        )
        return final

    @staticmethod
    def _compound_evidence(compounds: Iterable[object]) -> list[dict[str, object]]:
        return [{
            "evidence_id": f"CMP:{compound.compound_id}",
            "kind": "compound-identity",
            "compound_id": compound.compound_id,
            "display_name": compound.display_name,
            "source": compound.source_name,
            "source_id": compound.source_id,
            "evidence_grade": compound.evidence_grade,
            "evidence_mode": compound.evidence_mode,
            "statement": (
                f"OSIEL registry identity for {compound.display_name}; no target activity or "
                "efficacy claim is attached to this identity record."
            ),
        } for compound in compounds]

    @staticmethod
    def _retrieve_literature(
        question: str,
        cancer_type: str | None,
        compound_names: Iterable[str],
        limit: int = 5,
    ) -> list[LiteratureRecord]:
        query_tokens = _tokens(question, cancer_type, *list(compound_names))
        if not query_tokens:
            return []
        ranked: list[tuple[float, LiteratureRecord]] = []
        for record in RECORDS:
            record_tokens = _tokens(_record_text(record))
            overlap = query_tokens & record_tokens
            if not overlap:
                continue
            score = float(len(overlap))
            if record.compound.casefold() in question.casefold():
                score += 3
            if cancer_type and any(token in record_tokens for token in _tokens(cancer_type)):
                score += 1
            if record.evidence_level == "direct":
                score += 0.25
            ranked.append((score, record))
        ranked.sort(key=lambda item: (-item[0], -item[1].year, item[1].record_id))
        return [record for _, record in ranked[:limit]]

    @staticmethod
    def _literature_evidence(records: Iterable[LiteratureRecord]) -> list[dict[str, object]]:
        return [{
            "evidence_id": record.record_id,
            "kind": "literature",
            "source": record.source,
            "title": record.title,
            "year": record.year,
            "compound": record.compound,
            "biological_model": record.biological_model,
            "assay": record.assay,
            "statement": record.finding,
            "evidence_level": record.evidence_level,
            "pmid": record.pmid,
            "url": record.url,
            "claim_boundary": record.claim_boundary,
        } for record in records]

    @staticmethod
    def _missing_information(query: AssistantQuery, compounds_present: bool) -> list[str]:
        missing = [
            "Scientifically approved endpoint charter",
            "Locked, leakage-audited labelled dataset",
            "Prospective wet-lab validation",
        ]
        if not query.cancer_type:
            missing.insert(0, "Cancer type or research context")
        if not compounds_present:
            missing.insert(0, "At least one compound structure when compound-specific guidance is requested")
        return missing

    def _deterministic_answer(
        self,
        context: str,
        compounds: list[object],
        evidence: list[dict[str, object]],
        missing: list[str],
        *,
        retrieval_score: float,
        trace: list[dict[str, Any]],
        warnings: list[str],
    ) -> AssistantAnswer:
        names = ", ".join(compound.display_name for compound in compounds[:5]) or "the selected compounds"
        answer = (
            f"I found {len(evidence)} reviewable records for {names} in {context}, but the local "
            "language model is unavailable or failed validation. I will not synthesize a scientific "
            "conclusion from those records automatically; inspect the passages and ask a supervisor to review them."
        )
        trace.append({
            "stage": "grounded-generation",
            "status": "completed-with-warning",
            "message": "Model synthesis unavailable; returned an evidence-listing abstention",
            "metrics": {"evidence_count": len(evidence)},
        })
        return AssistantAnswer(
            answer=answer,
            evidence=[{**item, "used_by_model": False} for item in evidence],
            missing_information=missing,
            recommended_action=(
                "Inspect the retrieved passages, enable the approved local model if appropriate, "
                "and obtain named supervisor review before changing an experiment."
            ),
            mode="deterministic-evidence",
            model=None,
            embedding_model=self.ollama.embedding_model if self.ollama.enabled else None,
            abstained=True,
            confidence="low",
            retrieval_score=retrieval_score,
            citation_coverage=0,
            retrieval_trace=trace,
            guardrails=["evidence-sufficiency-gate", "unsupported-synthesis-abstention"],
            warnings=warnings,
        )

    @staticmethod
    def _abstention(
        answer: str,
        recommended_action: str,
        missing: list[str],
        *,
        warning: str,
        trace: list[dict[str, Any]],
        guardrail: str,
        evidence: list[dict[str, Any]] | None = None,
        retrieval_score: float = 0,
        embedding_model: str | None = None,
    ) -> AssistantAnswer:
        return AssistantAnswer(
            answer=answer,
            evidence=[{**item, "used_by_model": False} for item in (evidence or [])],
            missing_information=missing,
            recommended_action=recommended_action,
            mode="deterministic-evidence",
            model=None,
            embedding_model=embedding_model,
            abstained=True,
            confidence="low",
            retrieval_score=retrieval_score,
            citation_coverage=0,
            retrieval_trace=trace,
            guardrails=[guardrail],
            warnings=[warning],
        )
