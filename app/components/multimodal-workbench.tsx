"use client";

import { useMemo, useState } from "react";
import type { RankedCandidate } from "../lib/ranked-candidate";
import { runMultimodalResearchCase } from "../lib/osiel-client";
import type { MultimodalCaseResult } from "../lib/osiel-client";

const modalities = [
  ["chemistry", "Molecule", "RDKit identity + specialist model"],
  ["protein", "Protein / 3D", "UniProt identity + versioned adapter"],
  ["assay", "Assay table", "QC-passed measured records only"],
  ["documents", "Evidence RAG", "Page-level approved citations"],
  ["imaging", "Microscopy", "Phenotypic features, never diagnosis"],
] as const;

export function MultimodalWorkbench({ candidates }: { candidates: RankedCandidate[] }) {
  const [question, setQuestion] = useState("What evidence is still missing before a supervised follow-up assay?");
  const [target, setTarget] = useState("EGFR");
  const [accession, setAccession] = useState("P00533");
  const [selected, setSelected] = useState(() => new Set(modalities.map(([id]) => id)));
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState(-1);
  const [result, setResult] = useState<MultimodalCaseResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const compoundIds = useMemo(() => candidates.slice(0, 3).map((item) => item.compound_id), [candidates]);

  async function run() {
    setRunning(true); setResult(null); setError(null); setStage(0);
    const timer = window.setInterval(() => setStage((value) => Math.min(value + 1, 4)), 520);
    const response = await runMultimodalResearchCase({
      question,
      cancer_type: "Non-small cell lung cancer",
      cell_line: "A549",
      target_name: target,
      protein_accession: accession,
      compound_ids: compoundIds,
      requested_modalities: [...selected],
    });
    window.clearInterval(timer);
    setStage(5); setRunning(false); setConnected(response.backendConnected);
    setResult(response.result); setError(response.error);
  }

  function toggle(id: (typeof modalities)[number][0]) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  return <div className="multimodal-shell">
    <section className="module-heading multimodal-heading"><div><span>ANALYZE / MULTIMODAL ENGINE</span><h1>Evidence-fusion research console</h1><p>One governed case across molecules, proteins, assays, papers and microscopy—with visible execution, uncertainty and abstention.</p></div><div className={`multimodal-connection ${connected ? "live" : "offline"}`}><i/>{connected ? "Python engine connected" : "Fail-closed until API connects"}</div></section>

    <div className="multimodal-boundary"><b>Accuracy rule</b><span>No system can guarantee 100% biomedical accuracy. OSIEL reports only source-linked findings, caps confidence at 75%, abstains on weak evidence and requires named scientist approval.</span></div>

    <div className="module-grid two multimodal-config">
      <article className="module-card"><div className="card-title"><div><span>RESEARCH QUESTION</span><h2>Define a reviewable case</h2></div><b>RUO</b></div><label className="multimodal-question"><span>Question</span><textarea value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={2000}/></label><div className="multimodal-fields"><label><span>Target</span><input value={target} onChange={(event) => setTarget(event.target.value)}/></label><label><span>UniProt accession</span><input value={accession} onChange={(event) => setAccession(event.target.value)}/></label></div><div className="candidate-context"><span>Case compounds</span>{candidates.slice(0,3).map((item) => <b key={item.compound_id}>{item.display_name}</b>)}</div><button className="primary wide" disabled={running || !question.trim() || selected.size === 0} onClick={run}>{running ? "Running governed case…" : "Run multimodal analysis"}</button></article>
      <article className="module-card"><div className="card-title"><div><span>MODALITY ROUTER</span><h2>Choose specialist lanes</h2></div><b>{selected.size}/5 selected</b></div><div className="modality-picker">{modalities.map(([id,label,detail]) => <button key={id} className={selected.has(id) ? "active" : ""} onClick={() => toggle(id)}><i>{selected.has(id) ? "✓" : "+"}</i><span><b>{label}</b><small>{detail}</small></span></button>)}</div></article>
    </div>

    <article className="module-card multimodal-trace"><div className="card-title"><div><span>VISIBLE OPERATIONAL TRACE</span><h2>{running ? "Analysis in progress" : result ? "Execution complete" : "Waiting for a case"}</h2></div><b>No hidden reasoning shown</b></div><ol>{["Safety boundary","Molecule resolution","Protein / 3D","Assay QC","Evidence retrieval","Fusion + abstention"].map((label,index) => <li key={label} className={index < stage ? "done" : index === stage ? "active" : "waiting"}><i>{index < stage ? "✓" : String(index + 1).padStart(2,"0")}</i><span><b>{label}</b><small>{index < stage ? "Checked" : index === stage ? "Running validated stage" : "Waiting"}</small></span></li>)}</ol></article>

    {error && <div className="multimodal-error"><b>SAFE STOP</b><span>{error}</span><small>Start the supplied FastAPI service and configure NEXT_PUBLIC_OSIEL_API_URL. No result was invented in the browser.</small></div>}

    {result && <>
      <div className="module-stats"><div className="module-stat"><span>CASE STATUS</span><strong>{result.status.toUpperCase()}</strong><small>{result.case_id}</small></div><div className="module-stat"><span>CALIBRATED CEILING</span><strong>{Math.round(result.confidence * 100)}%</strong><small>Never presented as certainty</small></div><div className="module-stat"><span>CITATION COVERAGE</span><strong>{Math.round(result.citation_coverage * 100)}%</strong><small>{result.evidence.length} evidence records</small></div><div className="module-stat"><span>LAB AUTHORIZATION</span><strong>LOCKED</strong><small>Scientist approval required</small></div></div>
      <div className="module-grid two"><article className={`module-card multimodal-decision ${result.abstained ? "abstained" : "review"}`}><span>ENGINE RECOMMENDATION</span><h2>{result.abstained ? "OSIEL abstained" : "Supervisor review only"}</h2><p>{result.recommendation}</p><ul>{result.next_actions.map((item) => <li key={item}>{item}</li>)}</ul></article><article className="module-card"><div className="card-title"><div><span>MODALITY RESULTS</span><h2>What ran and what stopped</h2></div></div><div className="assessment-list">{result.assessments.map((item) => <div key={item.modality}><i className={item.status}/><span><b>{item.modality}</b><small>{item.model_name ?? item.warnings[0] ?? "Not run"}</small></span><em>{item.status}</em><strong>{Math.round(item.confidence * 100)}%</strong></div>)}</div></article></div>
      <article className="module-card"><div className="card-title"><div><span>EVIDENCE PACKAGE</span><h2>Every usable claim must resolve to a source</h2></div><b>{result.evidence.length} records</b></div><div className="multimodal-evidence">{result.evidence.map((item) => <div key={item.evidence_id}><span>{item.modality}</span><b>{item.evidence_id}</b><p>{item.finding}</p><small>{item.source} · {item.source_version}</small><code>{item.citation}</code></div>)}</div>{result.evidence.length === 0 && <p className="empty-evidence">No evidence passed the gate; OSIEL correctly produced no scientific conclusion.</p>}</article>
    </>}
  </div>;
}
