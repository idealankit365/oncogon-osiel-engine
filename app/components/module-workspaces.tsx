"use client";

import { useEffect, useMemo, useState } from "react";
import type { RankedCandidate } from "../lib/ranked-candidate";
import type { DryRunResult } from "../lib/osiel-client";
import { getBackendJson } from "../lib/osiel-client";
import { ExperimentLab } from "./experiment-lab";

import { ProfessorAI } from "./professor-ai";
import { ProductionCenter } from "./production-center";
import { OpenDiscoveryWorkspace } from "./open-discovery-workspace";
import { RecursionRoadmap } from "./recursion-roadmap";
import { ModelLab } from "./model-lab";
import { Zinc22Search } from "./zinc22-search";
import { SourceConnectorConsole } from "./source-connectors";
import { MultimodalWorkbench } from "./multimodal-workbench";

type Props = {
  activeNav: string;
  candidates: RankedCandidate[];
  selectedIds: string[];
  experiment: DryRunResult | null;
  onRunExperiment: () => Promise<DryRunResult | null>;
  onBackToCockpit: () => void;
};

function WorkspaceHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: React.ReactNode }) {
  return <section className="module-heading"><div><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{children}</section>;
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="module-stat"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

type LiteratureRecord = { id: string; title: string; year: number; compound: string; biological_model: string; assay: string; finding: string; pmid: string; url: string; evidence_level: string; claim_boundary: string };
type RegistryCompound = { compound_id: string; display_name: string; origin: string; source_name: string; evidence_grade: string; evidence_mode: string; descriptors: { molecular_formula: string } };

function EvidenceWorkspace() {
  const [records, setRecords] = useState<LiteratureRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState("all");
  useEffect(() => { getBackendJson<LiteratureRecord[]>("/v1/literature").then(setRecords).catch((cause) => { setRecords([]); setError(cause instanceof Error ? cause.message : "Backend unavailable"); }); }, []);
  const filtered = records.filter((record) => `${record.title} ${record.compound} ${record.biological_model}`.toLowerCase().includes(query.toLowerCase()) && (level === "all" || record.evidence_level === level));
  return <><WorkspaceHeader eyebrow="DISCOVER / EVIDENCE" title="Scientific literature and source registry" description="Backend curated citations and study context. Research use only."><label className="module-search"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search papers or compounds"/></label></WorkspaceHeader>
    <div className="module-stats"><Stat label="CURATED PAPERS" value={error ? "—" : String(records.length)} note="Backend literature registry"/><Stat label="CLAIM STATUS" value="RUO" note="No clinical inference"/></div>
    {error && <div className="registry-empty">Backend unavailable. {error}</div>}
    <SourceConnectorConsole/>
    <article className="module-card"><div className="card-title"><div><span>EVIDENCE INDEX</span><h2>Research records</h2></div><select value={level} onChange={(event) => setLevel(event.target.value)}><option value="all">All evidence</option><option value="direct">Direct</option><option value="supporting">Supporting</option><option value="method">Method</option></select></div><div className="paper-list">{filtered.map((paper) => <article key={paper.id}><div className="paper-top"><span className={`evidence-level ${paper.evidence_level}`}>{paper.evidence_level}</span><span>{paper.year}</span><b>PMID {paper.pmid}</b></div><h3>{paper.title}</h3><div className="paper-context"><span><b>Compound</b>{paper.compound}</span><span><b>Model</b>{paper.biological_model}</span><span><b>Assay</b>{paper.assay}</span></div><p>{paper.finding}</p><a href={paper.url} target="_blank" rel="noreferrer">Open authoritative record ↗</a></article>)}</div>{!error && filtered.length === 0 && <p>No literature records match this filter.</p>}</article>
    <div className="claim-boundary"><b>Evidence rule:</b> study-specific observations do not establish patient benefit or become model labels without scientific curation and approval.</div>
  </>;
}

function RegistryWorkspace() {
  const [items, setItems] = useState<RegistryCompound[]>([]);
  const [focus, setFocus] = useState("");
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ limit: "25", offset: String((page - 1) * 25) });
    if (query.trim()) params.set("query", query.trim());
    getBackendJson<RegistryCompound[]>(`/v1/compounds?${params}`).then((data) => { if (active) { setItems(data); setFocus(data[0]?.compound_id ?? ""); setError(null); } }).catch((cause) => { if (active) { setItems([]); setError(cause instanceof Error ? cause.message : "Backend unavailable"); } }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page, query]);
  const item = items.find((compound) => compound.compound_id === focus) ?? items[0];
  return <><WorkspaceHeader eyebrow="DISCOVER / REGISTRY" title="Compound registry" description="Compounds are retrieved from the FastAPI scientific registry."><label className="module-search"><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search backend compounds"/></label></WorkspaceHeader>
    <Zinc22Search seedSmiles="CC(=O)Oc1ccccc1C(=O)O"/>
    {error && <div className="registry-empty">Backend unavailable. {error}</div>}
    <div className="module-grid registry-grid"><article className="module-card"><div className="card-title"><div><span>BACKEND REGISTRY</span><h2>{loading ? "Loading records…" : `${items.length} records in this view`}</h2></div><b>Page {page}</b></div><div className="registry-list">{items.map((compound, index) => <button key={compound.compound_id} className={focus === compound.compound_id ? "active" : ""} onClick={() => setFocus(compound.compound_id)}><span className="registry-rank">{(page - 1) * 25 + index + 1}</span><div><b>{compound.display_name}</b><span>{compound.descriptors.molecular_formula} · {compound.compound_id}</span></div><em>{compound.origin}</em></button>)}</div>{!loading && !error && items.length === 0 && <div className="registry-empty">No compounds match this view.</div>}<div className="registry-pagination"><button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page === 1}>← Previous</button><span>Page {page}</span><button onClick={() => setPage((value) => value + 1)} disabled={items.length < 25}>Next →</button></div></article>{item && <article className="module-card identity-card"><span>BACKEND COMPOUND</span><h2>{item.display_name}</h2><dl className="spec-list"><div><dt>OSIEL ID</dt><dd>{item.compound_id}</dd></div><div><dt>Formula</dt><dd>{item.descriptors.molecular_formula}</dd></div><div><dt>Record class</dt><dd>{item.evidence_mode}</dd></div><div><dt>Source</dt><dd>{item.source_name}</dd></div><div><dt>Evidence grade</dt><dd>{item.evidence_grade}</dd></div></dl></article>}</div>
  </>;
}

function PredictionWorkspace({ candidates }: Pick<Props, "candidates">) {
  const [index, setIndex] = useState(0);
  const item = candidates[index];
  return <><WorkspaceHeader eyebrow="ANALYZE / PREDICTION" title="Prediction and uncertainty studio" description="Inspect backend ranking predictions and their research boundaries."/><div className="module-grid two"><article className="module-card"><h2>Input context</h2><label className="control-field"><span>Candidate</span><select value={index} onChange={(event) => setIndex(Number(event.target.value))}>{candidates.map((candidate, candidateIndex) => <option key={candidate.compound_id} value={candidateIndex}>{candidate.display_name}</option>)}</select></label>{!item && <p>No backend prediction available. Run the OSIEL engine when scientific services are connected.</p>}</article>{item && <article className="module-card prediction-result"><span>BACKEND COMPUTATIONAL HYPOTHESIS</span><div className="prediction-number"><strong>{item.activity}%</strong><small>activity hypothesis</small></div><div className="prediction-cards"><div><span>Predicted IC50</span><b>{item.predicted_ic50_um.toFixed(2)} µM</b></div><div><span>Confidence</span><b>{item.confidence}%</b></div><div><span>Uncertainty</span><b>±{item.uncertainty}</b></div></div></article>}</div><article className="module-card"><div className="card-title"><div><span>EXPLANATION</span><h2>What influenced this output</h2></div><b>Not causal attribution</b></div><p>Detailed model explanation is not available for this run.</p></article></>;
}

function RankingWorkspace({ candidates }: Pick<Props, "candidates">) {
  return <><WorkspaceHeader eyebrow="ANALYZE / POLICIES" title="Transparent ranking policy" description="Scores returned by the FastAPI ranking service; human review remains required."/><article className="module-card"><h2>Current backend ranking</h2>{candidates.length === 0 ? <p>No backend ranking available. Run the OSIEL engine when connected.</p> : <div className="module-table"><table><thead><tr><th>Rank</th><th>Compound</th><th>Score</th><th>Domain</th></tr></thead><tbody>{candidates.map((candidate) => <tr key={candidate.compound_id}><td>{candidate.rank}</td><td>{candidate.display_name}</td><td>{candidate.score.toFixed(1)}</td><td>{candidate.applicability_domain}</td></tr>)}</tbody></table></div>}</article><div className="claim-boundary">Ranking is a computational hypothesis, not independently validated efficacy evidence.</div></>;
}

type AuditEvent = { audit_id: string; action: string; actor: string; resource_type: string; resource_id: string; occurred_at: string; detail: Record<string, unknown> };
type ModelRecord = { model_id: string; name: string; version: string; alias: string; status: string; dataset_version: string; metrics: { validated?: boolean; demo_adapter?: boolean } };
function GovernanceWorkspace({ audit = false }: { audit?: boolean }) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { Promise.all([
    getBackendJson<AuditEvent[]>("/v1/audit"),
    getBackendJson<ModelRecord[]>("/v1/models"),
    getBackendJson<Record<string, unknown>>("/v1/system/capabilities"),
    getBackendJson<Record<string, unknown>>("/v1/system/readiness"),
  ]).then(([auditEvents, modelRecords]) => { setEvents(auditEvents); setModels(modelRecords); setError(null); }).catch((cause) => { setEvents([]); setModels([]); setError(cause instanceof Error ? cause.message : "Backend unavailable"); }); }, []);
  if (audit) return <><WorkspaceHeader eyebrow="VALIDATE / LINEAGE" title="Audit and provenance ledger" description="Backend recorded scientific and governance events."/><article className="module-card">{error ? <p>Backend unavailable. {error}</p> : events.length === 0 ? <p>No audit events recorded yet.</p> : <div className="audit-timeline">{events.map((event, index) => <div key={event.audit_id}><i>{index + 1}</i><time>{new Date(event.occurred_at).toLocaleString()}</time><b>{event.action}</b><span>{event.resource_type} · {event.resource_id} · {event.actor}</span><code>{event.audit_id}</code></div>)}</div>}</article></>;
  const validated = models.filter((model) => model.metrics?.validated);
  return <><WorkspaceHeader eyebrow="VALIDATE / GOVERNANCE" title="Model governance control room" description="Backend model registry and readiness; human scientific approval is required."/>{error ? <article className="module-card">Backend unavailable. {error}</article> : <><div className="module-stats"><Stat label="REGISTERED MODELS" value={String(models.length)} note="Backend registry"/><Stat label="VALIDATED MODELS" value={String(validated.length)} note="Evidence gate"/></div><div className="module-grid two">{models.map((model) => <article className="module-card model-card" key={model.model_id}><span>{model.alias.toUpperCase()}</span><h2>{model.name}@{model.version}</h2><p>{model.metrics?.validated ? "Validated model" : "Development reference. Not a validated production model."}</p><dl className="spec-list"><div><dt>State</dt><dd>{model.status}</dd></div><div><dt>Dataset</dt><dd>{model.dataset_version}</dd></div></dl></article>)}</div>{validated.length === 0 && <div className="claim-boundary">No validated production model configured.</div>}</>}<div className="claim-boundary">Research use only. Model promotion requires independent review; simulated observations cannot become training data.</div></>;
}

function SettingsWorkspace() {
  const [readiness, setReadiness] = useState<{ mode: string; authentication_enforced: boolean; validated_scientific_model: boolean; blockers: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getBackendJson<{ mode: string; authentication_enforced: boolean; validated_scientific_model: boolean; blockers: string[] }>("/v1/system/readiness").then(setReadiness).catch((cause) => setError(cause instanceof Error ? cause.message : "Backend unavailable")); }, []);
  return <><WorkspaceHeader eyebrow="SYSTEM / SETTINGS" title="Workspace and safety controls" description="Backend-reported research environment and release gates."/><article className="module-card"><h2>Environment</h2>{error ? <p>Backend unavailable. {error}</p> : !readiness ? <p>Loading backend readiness…</p> : <dl className="spec-list"><div><dt>Mode</dt><dd>{readiness.mode}</dd></div><div><dt>Authentication enforced</dt><dd>{readiness.authentication_enforced ? "Yes" : "No"}</dd></div><div><dt>Validated scientific model</dt><dd>{readiness.validated_scientific_model ? "Yes" : "No"}</dd></div><div><dt>Readiness blockers</dt><dd>{readiness.blockers.length}</dd></div></dl>}</article><div className="claim-boundary">Research use only. Human scientific review required.</div></>;
}

export function ModuleWorkspace(props: Props) {
  const content = useMemo(() => {
    if (props.activeNav === "Open discovery") return <OpenDiscoveryWorkspace/>;
    if (props.activeNav === "Recursion gap map") return <RecursionRoadmap/>;
    if (props.activeNav === "Compound registry") return <RegistryWorkspace/>;
    if (props.activeNav === "Evidence sources") return <EvidenceWorkspace/>;
    if (props.activeNav === "Prediction studio") return <PredictionWorkspace candidates={props.candidates}/>;
    if (props.activeNav === "Model laboratory") return <ModelLab/>;
    if (props.activeNav === "Ranking policies") return <RankingWorkspace candidates={props.candidates}/>;
    if (props.activeNav === "Scientific copilot") return <ProfessorAI candidates={props.candidates} experiment={props.experiment}/>;
    if (props.activeNav === "Multimodal engine") return <MultimodalWorkbench candidates={props.candidates}/>;
    if (props.activeNav === "Experiments") return <ExperimentLab candidates={props.candidates} selectedIds={props.selectedIds} onRunExperiment={props.onRunExperiment}/>;
    if (props.activeNav === "Model governance") return <GovernanceWorkspace/>;
    if (props.activeNav === "Audit & lineage") return <GovernanceWorkspace audit/>;
    if (props.activeNav === "Production center") return <ProductionCenter/>;
    return <SettingsWorkspace/>;
  }, [props]);
  return <div className="module-workspace"><button className="back-cockpit" onClick={props.onBackToCockpit}>← Back to research cockpit</button>{content}<footer className="page-footer"><div><strong>OSIEL</strong> · Scientific evidence-to-experiment workspace</div><div>Research use only · Simulated output clearly labelled</div></footer></div>;
}
