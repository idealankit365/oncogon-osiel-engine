"use client";

import { useEffect, useState } from "react";
import type { RankedCandidate } from "../lib/ranked-candidate";
import {
  askScientificProfessor,
  ingestProfessorDocument,
  listProfessorDocuments,
  loadProfessorCapabilities,
  submitProfessorFeedback,
  type DryRunResult,
  type ProfessorAnswer,
  type ProfessorCapabilities,
  type ProfessorDocument,
} from "../lib/osiel-client";

const quickPrompts = [
  "What must I check before starting?",
  "Why did my experiment fail?",
  "Which compound should I test next?",
  "Can this result train the model?",
];

export function ProfessorAI({
  candidates,
  experiment,
}: {
  candidates: RankedCandidate[];
  experiment: DryRunResult | null;
}) {
  const [view, setView] = useState<"ask" | "library">("ask");
  const [question, setQuestion] = useState(quickPrompts[0]);

  const [history, setHistory] = useState<string[]>([]);
  const [serverAnswer, setServerAnswer] = useState<ProfessorAnswer | null>(null);
  const [capabilities, setCapabilities] = useState<ProfessorCapabilities | null>(null);
  const [documents, setDocuments] = useState<ProfessorDocument[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [projectScope, setProjectScope] = useState("general");
  const [courseScope, setCourseScope] = useState("general");
  const [busy, setBusy] = useState<"ask" | "upload" | "feedback" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [documentTitle, setDocumentTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceVersion, setSourceVersion] = useState("faculty-approved-v1");
  const [rightsNote, setRightsNote] = useState("");
  const [rightsApproved, setRightsApproved] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [feedbackDecision, setFeedbackDecision] = useState<"correct" | "partially-correct" | "incorrect" | "unsafe">("correct");
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [correction, setCorrection] = useState("");
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const top = candidates[0];

  useEffect(() => {
    let active = true;
    void (async () => {
      const capability = await loadProfessorCapabilities();
      if (!active) return;
      setCapabilities(capability);
      if (capability) setDocuments(await listProfessorDocuments(projectScope, courseScope));
    })();
    return () => { active = false; };
  }, [projectScope, courseScope]);

  async function ask(value = question) {
    const clean = value.trim();
    if (!clean || busy) return;
    setQuestion(clean);
    setHistory((items) => [clean, ...items.filter((item) => item !== clean)].slice(0, 6));
    setBusy("ask");
    setError(null);
    const response = await askScientificProfessor(
      clean,
      "Current oncology research workspace",
      candidates.slice(0, 5).map((item) => item.compound_id),
      {
        conversationId,
        projectScope,
        courseScope,
        documentIds: [...selectedDocuments],
      },
    );
    setBusy(null);
    setServerAnswer(response.answer);
    setConversationId(response.answer?.conversation_id ?? conversationId);
    setError(response.error);
    setFeedbackMessage(null);
  }

  async function uploadDocument() {
    if (!file || !documentTitle.trim() || !rightsApproved || rightsNote.trim().length < 4 || busy) {
      setUploadMessage("Choose a file, provide its title and licence note, and confirm that full-text indexing is permitted.");
      return;
    }
    setBusy("upload");
    setUploadMessage("Checking rights, hashing raw bytes, extracting pages and building the scoped index…");
    const result = await ingestProfessorDocument(file, {
      title: documentTitle.trim(),
      sourceUrl: sourceUrl.trim(),
      sourceVersion: sourceVersion.trim() || "uploaded",
      rightsNote: rightsNote.trim(),
      projectScope,
      courseScope,
    });
    setBusy(null);
    if (result.error || !result.document) {
      setUploadMessage(result.error || "Document ingestion failed.");
      return;
    }
    setUploadMessage(
      result.document.status === "quarantined"
        ? `Quarantined ${result.document.title}; prompt-like instructions were detected and it will not be retrieved.`
        : `Indexed ${result.document.title}: ${result.document.page_count} pages, ${result.document.chunk_count} immutable chunks.`,
    );
    setDocuments(await listProfessorDocuments(projectScope, courseScope));
    setSelectedDocuments((items) => new Set([...items, result.document!.document_id]));
  }

  async function sendFeedback() {
    if (!serverAnswer?.answer_id || busy) return;
    if (feedbackDecision !== "correct" && correction.trim().length < 4) {
      setFeedbackMessage("A faculty correction is required when the answer is not fully correct.");
      return;
    }
    setBusy("feedback");
    const evidenceIds = serverAnswer.evidence.filter((item) => item.used_by_model).map((item) => item.evidence_id);
    const result = await submitProfessorFeedback(serverAnswer.answer_id, {
      decision: feedbackDecision,
      correction: correction.trim(),
      reviewerNotes: feedbackNotes.trim(),
      evidenceIds,
    });
    setBusy(null);
    setFeedbackMessage(result.error || `Faculty review recorded as ${result.feedbackId}. It was not used for automatic retraining.`);
  }

  const answerText = serverAnswer?.answer ?? "No scientific answer available. Connect the backend and ask a question.";
  const actions = serverAnswer ? [serverAnswer.recommended_action] : [];
  const needs = serverAnswer?.missing_information ?? [];
  const mode = serverAnswer?.mode === "hybrid-ollama-rag"
    ? `Local ${serverAnswer.model || "Qwen"} · hybrid cited RAG`
    : serverAnswer?.mode === "local-ollama-rag"
      ? `Local ${serverAnswer.model || "Qwen"} · curated cited RAG`
      : serverAnswer
        ? "Python evidence gate · abstained"
        : "Backend unavailable";

  return <>
    <section className="module-heading">
      <div><span>ANALYZE / PROFESSOR AI</span><h1>Governed scientific professor</h1><p>Upload approved research, retrieve page-level evidence, ask Qwen locally and preserve faculty review.</p></div>
      <div className="professor-live-summary">
        <b>{capabilities ? "Python engine connected" : "Backend unavailable"}</b>
        <span>{capabilities?.document_count ?? 0} documents · {capabilities?.chunk_count ?? 0} chunks</span>
      </div>
    </section>

    <div className="professor-boundary">
      <b>{capabilities?.enabled ? "Local model enabled" : "Local model capability-gated"}</b>
      <span>Qwen composes prose only from supplied evidence. RDKit and validated endpoint models perform quantitative computation. Professor AI cannot authorize a laboratory or clinical action.</span>
    </div>

    <div className="professor-tabs" role="tablist" aria-label="Professor AI workspace">
      <button className={view === "ask" ? "active" : ""} onClick={() => setView("ask")}>Ask professor</button>
      <button className={view === "library" ? "active" : ""} onClick={() => setView("library")}>Controlled library <em>{documents.length}</em></button>
    </div>

    {view === "library" ? <div className="professor-library-grid">
      <article className="module-card professor-upload">
        <span>APPROVED DOCUMENT INGESTION</span>
        <h2>Build the university evidence library</h2>
        <p>Raw bytes and normalized page chunks are checksum-addressed. PDF, TXT and Markdown are supported.</p>
        <label>Project scope<input value={projectScope} onChange={(event) => setProjectScope(event.target.value)} /></label>
        <label>Course scope<input value={courseScope} onChange={(event) => setCourseScope(event.target.value)} /></label>
        <label>Paper or document<input type="file" accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown" onChange={(event) => { const next = event.target.files?.[0] ?? null; setFile(next); if (next && !documentTitle) setDocumentTitle(next.name.replace(/\.[^.]+$/, "")); }} /></label>
        <label>Document title<input value={documentTitle} onChange={(event) => setDocumentTitle(event.target.value)} placeholder="Exact paper or SOP title" /></label>
        <label>Original source URL<input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://…" /></label>
        <label>Source version<input value={sourceVersion} onChange={(event) => setSourceVersion(event.target.value)} /></label>
        <label>Licence / rights note<textarea value={rightsNote} onChange={(event) => setRightsNote(event.target.value)} placeholder="Who approved full-text indexing and under which licence?" /></label>
        <label className="professor-check"><input type="checkbox" checked={rightsApproved} onChange={(event) => setRightsApproved(event.target.checked)} /><span>I confirm this institution is permitted to index the uploaded full text.</span></label>
        <button className="primary" onClick={() => void uploadDocument()} disabled={busy === "upload" || !capabilities?.ingestion_enabled}>{busy === "upload" ? "Building immutable index…" : capabilities?.ingestion_enabled ? "Ingest and index" : "Ingestion disabled by operator"}</button>
        {uploadMessage && <div className="professor-warning">{uploadMessage}</div>}
      </article>

      <article className="module-card professor-documents">
        <span>SCOPED CORPUS</span><h2>Reviewable source versions</h2>
        {documents.length === 0 ? <div className="empty-professor">No documents are indexed in this project and course scope.</div> : documents.map((document) => <label className={`professor-document ${document.status}`} key={document.document_id}>
          <input type="checkbox" disabled={document.status !== "indexed"} checked={selectedDocuments.has(document.document_id)} onChange={() => setSelectedDocuments((items) => { const next = new Set(items); if (next.has(document.document_id)) next.delete(document.document_id); else next.add(document.document_id); return next; })} />
          <div><b>{document.title}</b><span>{document.page_count} pages · {document.chunk_count} chunks · {document.embedding_model || "FTS5 lexical"}</span><small>SHA {document.raw_sha256.slice(0, 16)}… · {document.source_version}</small>{document.prompt_injection_flags.length > 0 && <em>Quarantined: {document.prompt_injection_flags.join(", ")}</em>}</div>
        </label>)}
      </article>
    </div> : <div className="module-grid professor-grid">
      <article className="module-card professor-question">
        <span>ASK A SUPERVISOR-STYLE QUESTION</span>
        <div className="professor-scope-row"><label>Project<input value={projectScope} onChange={(event) => setProjectScope(event.target.value)} /></label><label>Course<input value={courseScope} onChange={(event) => setCourseScope(event.target.value)} /></label></div>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="Question for Professor AI" />
        <div className="prompt-chips">{quickPrompts.map((prompt) => <button key={prompt} onClick={() => void ask(prompt)} disabled={Boolean(busy)}>{prompt}</button>)}</div>
        <button className="primary" onClick={() => void ask()} disabled={Boolean(busy)}>{busy === "ask" ? "Retrieving, grounding and checking citations…" : "Ask Professor"}</button>
        {error && <div className="professor-warning">{error}</div>}
        {conversationId && <div className="professor-conversation"><b>Persisted consultation</b><span>{conversationId}</span></div>}
        {history.length > 0 && <div className="professor-history"><b>Recent questions</b>{history.map((item) => <button key={item} onClick={() => { setQuestion(item);  }}>{item}</button>)}</div>}
      </article>

      <article className="module-card professor-answer">
        <div className="assistant-label"><i>AI</i><span>OSIEL Professor<b>{mode}</b></span><em>{serverAnswer?.abstained ? "Abstained" : `${serverAnswer?.confidence ?? "unavailable"} confidence`}</em></div>
        <div className="professor-score-strip"><span>Retrieval <b>{Math.round((serverAnswer?.retrieval_score ?? 0) * 100)}%</b></span><span>Citation gate <b>{Math.round((serverAnswer?.citation_coverage ?? 0) * 100)}%</b></span><span>Documents <b>{selectedDocuments.size || "all scoped"}</b></span></div>
        <span className="answer-topic">{serverAnswer?.abstained ? "Evidence boundary" : "Scientific answer"}</span><h2>Professor response</h2><p>{answerText}</p>
        <div className="context-strip"><span>Current candidate <b>{top?.display_name ?? "not selected"}</b></span><span>Experiment <b>{experiment?.experimentId ?? "no experiment selected"}</b></span></div>
        <h3>Do this next</h3><ol>{actions.map((action) => <li key={action}>{action}</li>)}</ol>
        <div className="missing-box"><b>Missing or required information</b>{needs.map((item) => <span key={item}>{item}</span>)}</div>

        {serverAnswer ? <div className="professor-sources"><b>Retrieved evidence · open and verify the original</b>{serverAnswer.evidence.map((source) => {
          const label = `${source.evidence_id}${source.page_number ? ` · page ${source.page_number}` : ""} · ${source.title || source.display_name || source.source || "source"}`;
          return <div className={`professor-citation ${source.used_by_model ? "used" : ""}`} key={source.evidence_id}>{source.url ? <a href={source.url} target="_blank" rel="noreferrer">{label} ↗</a> : <span>{label}</span>}{source.quote && <small>{source.quote}</small>}<em>{source.used_by_model ? "Cited by model" : "Retrieved context"}{source.retrieval_score !== undefined ? ` · ${Math.round(source.retrieval_score * 100)}%` : ""}</em></div>;
        })}</div> : null}

        {serverAnswer?.retrieval_trace.length ? <details className="professor-trace" open><summary>Visible execution trace · {serverAnswer.retrieval_trace.length} stages</summary>{serverAnswer.retrieval_trace.map((event, index) => <div key={`${event.stage}-${index}`}><i className={event.status} /><span><b>{event.stage}</b>{event.message}</span><em>{event.status}</em></div>)}</details> : null}
        {serverAnswer?.warnings.map((warning) => <div className="professor-warning" key={warning}>{warning}</div>)}

        {serverAnswer?.answer_id && <details className="professor-feedback"><summary>Faculty correction and review</summary><p>Corrections are audited and held for evaluation. They never retrain or promote a model automatically.</p><label>Decision<select value={feedbackDecision} onChange={(event) => setFeedbackDecision(event.target.value as typeof feedbackDecision)}><option value="correct">Correct</option><option value="partially-correct">Partially correct</option><option value="incorrect">Incorrect</option><option value="unsafe">Unsafe</option></select></label><label>Reviewer notes<textarea value={feedbackNotes} onChange={(event) => setFeedbackNotes(event.target.value)} /></label>{feedbackDecision !== "correct" && <label>Required correction<textarea value={correction} onChange={(event) => setCorrection(event.target.value)} /></label>}<button onClick={() => void sendFeedback()} disabled={busy === "feedback"}>{busy === "feedback" ? "Recording review…" : "Record faculty review"}</button>{feedbackMessage && <div className="professor-warning">{feedbackMessage}</div>}</details>}
        <p className="ai-boundary">Research-use guidance only. It cannot replace a supervisor, institutional approval, local SOP, biosafety review, measured laboratory result or clinical professional.</p>
      </article>
    </div>}
  </>;
}
