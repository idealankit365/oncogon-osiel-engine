"use client";

import { useEffect, useMemo, useState } from "react";
import type { RankedCandidate } from "../lib/demo-data";
import type { DryRunResult } from "../lib/osiel-client";
import { evidenceSources, literatureRecords } from "../lib/literature-data";
import { ExperimentLab } from "./experiment-lab";
import type { LibraryCompound } from "../lib/compound-library";
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

const doses = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30];
const curveSeries = [
  { name: "Acetaminophen", color: "#705ed6", ic50: 0.28, values: [99, 96, 86, 48, 18, 8, 4, 3] },
  { name: "Apigenin", color: "#0aa989", ic50: 0.35, values: [99, 97, 89, 55, 22, 10, 5, 3] },
  { name: "Catechin", color: "#d9901a", ic50: 0.36, values: [100, 98, 91, 57, 25, 11, 6, 4] },
];

function WorkspaceHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: React.ReactNode }) {
  return <section className="module-heading"><div><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{children}</section>;
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="module-stat"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

function DoseResponseChart() {
  return <div className="curve-panel"><div className="chart-axis y"><span>100</span><span>75</span><span>50</span><span>25</span><span>0</span></div><svg viewBox="0 0 760 270" role="img" aria-label="Simulated dose response curves">
    {[35, 85, 135, 185, 235].map((y) => <line key={y} x1="42" y1={y} x2="735" y2={y} stroke="#e8eaf1" strokeWidth="1"/>)}
    {curveSeries.map((series) => {
      const points = series.values.map((value, index) => `${55 + index * 95},${235 - value * 2}`).join(" ");
      return <g key={series.name}><polyline points={points} fill="none" stroke={series.color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>{series.values.map((value, index) => <circle key={index} cx={55 + index * 95} cy={235 - value * 2} r="5" fill="white" stroke={series.color} strokeWidth="3"/>)}</g>;
    })}
  </svg><div className="chart-axis x">{doses.map((dose) => <span key={dose}>{dose}</span>)}</div><div className="axis-label">Dose (µM, logarithmic series) · Simulated relative viability (%)</div><div className="chart-legend">{curveSeries.map((series) => <span key={series.name}><i style={{ background: series.color }}/>{series.name} · IC50 {series.ic50} µM</span>)}</div></div>;
}

function PlateMap() {
  const wells = Array.from({ length: 96 }, (_, index) => {
    const row = Math.floor(index / 12);
    const column = index % 12;
    const type = column === 0 ? "negative" : column === 11 ? "positive" : row < 3 ? "compound-a" : row < 6 ? "compound-b" : "compound-c";
    return { label: `${String.fromCharCode(65 + row)}${column + 1}`, type };
  });
  return <div className="plate-wrap"><div className="plate-grid">{wells.map((well) => <span key={well.label} className={well.type} title={well.label}>{well.label}</span>)}</div><div className="plate-legend"><span><i className="negative"/>Vehicle control</span><span><i className="compound-a"/>Candidate 1</span><span><i className="compound-b"/>Candidate 2</span><span><i className="compound-c"/>Candidate 3</span><span><i className="positive"/>Positive control</span></div></div>;
}

export function ExperimentsWorkspace({ experiment, selectedIds, onRunExperiment }: Pick<Props, "experiment" | "selectedIds" | "onRunExperiment">) {
  const [tab, setTab] = useState<"overview" | "plate" | "curves" | "observations" | "qc">("overview");
  const observations = curveSeries.flatMap((series) => doses.map((dose, index) => ({ series: series.name, dose, viability: series.values[index], cv: (2.4 + index * 0.37).toFixed(1) })));
  return <>
    <WorkspaceHeader eyebrow="VALIDATE / EXPERIMENTS" title="CellTiter-Glo laboratory run" description="A complete, auditable 96-well dose-response workflow with an explicitly simulated output."><button className="primary" onClick={onRunExperiment}>Run fresh simulation</button></WorkspaceHeader>
    <div className="lab-status"><div><b>EXP-NSCLC-A549-001</b><span>Protocol locked · simulation-only</span></div><div className="lab-state"><i/>QC passed</div><div><b>{experiment?.observationCount ?? 72}</b><span>Synthetic observations</span></div><div><b>0</b><span>Training-eligible rows</span></div></div>
    <div className="module-tabs">{(["overview", "plate", "curves", "observations", "qc"] as const).map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item === "qc" ? "QC & review" : item[0].toUpperCase() + item.slice(1)}</button>)}</div>
    {tab === "overview" && <div className="module-grid two"><article className="module-card"><h2>Protocol definition</h2><dl className="spec-list"><div><dt>Biological model</dt><dd>A549 NSCLC cells</dd></div><div><dt>Readout</dt><dd>ATP-linked luminescent viability</dd></div><div><dt>Exposure</dt><dd>72 hours</dd></div><div><dt>Dose series</dt><dd>0.01–30 µM · 8 points</dd></div><div><dt>Replicates</dt><dd>3 technical replicates</dd></div><div><dt>Controls</dt><dd>Vehicle + positive control</dd></div></dl></article><article className="module-card"><h2>Execution state machine</h2><ol className="run-timeline"><li className="done"><b>Protocol validated</b><span>Task, endpoint, units and candidates resolved</span></li><li className="done"><b>Plate map generated</b><span>Three candidates × eight doses × three replicates</span></li><li className="done"><b>Response simulated</b><span>Bounded sigmoid curves with deterministic noise</span></li><li className="done"><b>QC evaluated</b><span>Controls, ranges, completeness and replicate CV checked</span></li><li className="locked"><b>Scientific review locked</b><span>Simulation can never enter a training snapshot</span></li></ol></article></div>}
    {tab === "plate" && <article className="module-card"><div className="card-title"><div><span>96-WELL LAYOUT</span><h2>Generated plate map</h2></div><b>8 rows × 12 columns</b></div><PlateMap/></article>}
    {tab === "curves" && <article className="module-card"><div className="card-title"><div><span>DOSE RESPONSE</span><h2>Visible simulation output</h2></div><b>Four-parameter logistic concept</b></div><DoseResponseChart/><div className="formula-note"><code>viability = bottom + (top − bottom) / (1 + (dose / IC50)^hill)</code><p>The reference engine derives a deterministic IC50 hypothesis, applies a bounded sigmoid response and small seeded replicate noise, then recalculates an estimated IC50. This verifies software behavior only.</p></div></article>}
    {tab === "observations" && <article className="module-card"><div className="card-title"><div><span>RAW-LIKE OUTPUT</span><h2>Observation preview</h2></div><b>Showing 24 of 72 rows</b></div><div className="module-table"><table><thead><tr><th>Candidate</th><th>Dose (µM)</th><th>Replicates</th><th>Mean viability</th><th>CV</th><th>Data class</th></tr></thead><tbody>{observations.map((row) => <tr key={`${row.series}-${row.dose}`}><td><b>{row.series}</b></td><td>{row.dose}</td><td>3</td><td>{row.viability}%</td><td>{row.cv}%</td><td><span className="status-chip simulated">Simulated</span></td></tr>)}</tbody></table></div></article>}
    {tab === "qc" && <div className="module-grid two"><article className="module-card"><h2>Automated quality checks</h2><ul className="qc-list"><li><i/>All 72 expected observations present <b>PASS</b></li><li><i/>Positive and vehicle controls present <b>PASS</b></li><li><i/>Viability bounded between 0 and 110% <b>PASS</b></li><li><i/>Three replicates per dose <b>PASS</b></li><li><i/>Replicate consistency within demo threshold <b>PASS</b></li></ul></article><article className="module-card danger-card"><h2>Governance decision</h2><div className="decision-seal">REJECTED</div><p>Training eligibility was rejected because every observation is marked <code>simulation_only=true</code>. The champion model remains unchanged.</p><div className="decision-meta"><span>Selected candidates <b>{selectedIds.length || 3}</b></span><span>Champion mutation <b>None</b></span></div></article></div>}
  </>;
}

function EvidenceWorkspace() {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState("all");
  const filtered = literatureRecords.filter((record) => `${record.title} ${record.compound} ${record.biologicalModel}`.toLowerCase().includes(query.toLowerCase()) && (level === "all" || record.evidenceLevel === level));
  return <>
    <WorkspaceHeader eyebrow="DISCOVER / EVIDENCE" title="Scientific literature and source registry" description="Curated paper metadata and lawful source links with assay context preserved.">
      <label className="module-search"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search papers or compounds"/></label>
    </WorkspaceHeader>
    <div className="module-stats"><Stat label="CURATED PAPERS" value={String(literatureRecords.length)} note="A549-focused evidence set"/><Stat label="DIRECT STUDIES" value={String(literatureRecords.filter((item) => item.evidenceLevel === "direct").length)} note="Compound + biological model"/><Stat label="OPEN LINKS" value={String(literatureRecords.filter((item) => item.access === "Open access").length)} note="Publisher or PMC access"/><Stat label="CLAIM STATUS" value="RUO" note="No clinical inference"/></div>
    <SourceConnectorConsole/>
    <div className="evidence-layout"><aside className="module-card source-panel"><h2>Registered sources</h2>{evidenceSources.map(([name, purpose, status]) => <div className="source-row" key={name}><i/><div><b>{name}</b><span>{purpose}</span></div><small>{status}</small></div>)}</aside><article className="module-card"><div className="card-title"><div><span>EVIDENCE INDEX</span><h2>Research records</h2></div><select value={level} onChange={(event) => setLevel(event.target.value)}><option value="all">All evidence</option><option value="direct">Direct</option><option value="supporting">Supporting</option><option value="method">Method</option></select></div><div className="paper-list">{filtered.map((paper) => <article key={paper.id}><div className="paper-top"><span className={`evidence-level ${paper.evidenceLevel}`}>{paper.evidenceLevel}</span><span>{paper.year} · {paper.journal}</span><b>PMID {paper.pmid}</b></div><h3>{paper.title}</h3><div className="paper-context"><span><b>Compound</b>{paper.compound}</span><span><b>Model</b>{paper.biologicalModel}</span><span><b>Assay</b>{paper.assay}</span></div><p>{paper.finding}</p><a href={paper.url} target="_blank" rel="noreferrer">Open authoritative record ↗</a></article>)}</div></article></div>
    <div className="claim-boundary"><b>Evidence rule:</b> paper findings are stored as study-specific observations. They do not overwrite simulated output, establish patient benefit, or become model labels without scientific curation and approval.</div>
  </>;
}

function RegistryWorkspace({ candidates }: Pick<Props, "candidates">) {
  const fallback = candidates.map((candidate): LibraryCompound => ({ compoundId:candidate.compound_id, displayName:candidate.display_name, formula:candidate.formula, origin:candidate.origin, recordClass:"curated-reference", evidenceGrade:candidate.evidence_grade, domain:candidate.applicability_domain, priorityScore:candidate.score, source:candidate.source }));
  const [items, setItems] = useState<LibraryCompound[]>(fallback);
  const [focus, setFocus] = useState(fallback[0]?.compoundId ?? "");
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => fetch(`/api/compounds?page=${page}&pageSize=25&query=${encodeURIComponent(query)}`, { signal: controller.signal }).then((response) => response.json()).then((data: { items?: LibraryCompound[] }) => {
      if (data.items) { setItems(data.items); if (data.items[0]) setFocus(data.items[0].compoundId); }
    }).finally(() => setLoading(false)).catch(() => setLoading(false)), 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [page, query]);
  const item = items.find((compound) => compound.compoundId === focus) ?? items[0];
  return <>
    <WorkspaceHeader eyebrow="DISCOVER / FEDERATED REGISTRY" title="10.10-billion-entry real-time chemical search" description="Search the provider-hosted REALDB map in real time, then import only a bounded shortlist for local RDKit review."><label className="module-search"><input value={query} onChange={(event) => { setLoading(true); setQuery(event.target.value); setPage(1); }} placeholder="Filter the 192 local reference records"/></label></WorkspaceHeader>
    <div className="module-stats"><Stat label="REMOTE MAP" value="10.10B" note="provider-reported indexed entries"/><Stat label="MAPPED / SEARCHABLE" value="9.43B" note="verified live map metadata"/><Stat label="LOCAL REFERENCES" value="192" note="bounded RDKit registry"/><Stat label="LOCAL PAGE" value={String(page)} note="25 records per page"/></div>
    <div className="library-boundary"><b>Architecture rule:</b> OSIEL does not fabricate or download ten billion compounds. CartBlanche searches its distributed map; OSIEL receives at most 100 structures, records the map identity and checksum, and runs local chemistry checks.</div>
    <Zinc22Search seedSmiles="CC(=O)Oc1ccccc1C(=O)O"/>
    <div className="module-grid registry-grid"><article className="module-card"><div className="card-title"><div><span>LOCAL REFERENCE CACHE</span><h2>{loading ? "Loading records…" : `${items.length} records in this view`}</h2></div><b>Page {page} of 8</b></div><div className="registry-list">{items.map((compound,index) => <button key={compound.compoundId} className={focus === compound.compoundId ? "active" : ""} onClick={() => setFocus(compound.compoundId)}><span className="registry-rank">{(page - 1) * 25 + index + 1}</span><div><b>{compound.displayName}</b><span>{compound.formula} · {compound.compoundId}</span></div><em>{compound.origin}</em></button>)}</div>{items.length === 0 && <div className="registry-empty">No local reference matches this filter. Use the real-time remote search above for chemical-space expansion.</div>}<div className="registry-pagination"><button onClick={() => { setLoading(true); setPage((value) => Math.max(1,value - 1)); }} disabled={page === 1 || Boolean(query)}>← Previous</button><span>Records {(page-1)*25+1}–{Math.min(page*25,192)} of 192 local references</span><button onClick={() => { setLoading(true); setPage((value) => Math.min(8,value + 1)); }} disabled={page === 8 || Boolean(query)}>Next →</button></div></article>{item && <article className="module-card identity-card"><span>STANDARDIZED LOCAL REFERENCE</span><h2>{item.displayName}</h2><div className="identity-sketch">⌬</div><dl className="spec-list"><div><dt>OSIEL ID</dt><dd>{item.compoundId}</dd></div><div><dt>Formula</dt><dd>{item.formula}</dd></div><div><dt>Record class</dt><dd>{item.recordClass}</dd></div><div><dt>Source</dt><dd>{item.source}</dd></div><div><dt>Evidence grade</dt><dd>{item.evidenceGrade}</dd></div><div><dt>Priority score</dt><dd>{item.priorityScore}/100</dd></div><div><dt>Domain</dt><dd>{item.domain}</dd></div></dl></article>}</div>
  </>;
}

function PredictionWorkspace({ candidates }: Pick<Props, "candidates">) {
  const [index, setIndex] = useState(0);
  const item = candidates[index] ?? candidates[0];
  return <><WorkspaceHeader eyebrow="ANALYZE / PREDICTION" title="Prediction and uncertainty studio" description="Inspect the hypothesis, interval, domain status and explanatory inputs separately."/><div className="module-grid two"><article className="module-card"><h2>Input context</h2><label className="control-field"><span>Candidate</span><select value={index} onChange={(event) => setIndex(Number(event.target.value))}>{candidates.map((candidate, candidateIndex) => <option key={candidate.compound_id} value={candidateIndex}>{candidate.display_name}</option>)}</select></label><dl className="spec-list"><div><dt>Cancer context</dt><dd>NSCLC</dd></div><div><dt>Biological model</dt><dd>A549</dd></div><div><dt>Endpoint</dt><dd>Activity hypothesis</dd></div><div><dt>Model</dt><dd>osiel-demo-activity@0.1</dd></div><div><dt>Applicability domain</dt><dd>{item?.applicability_domain}</dd></div></dl></article>{item && <article className="module-card prediction-result"><span>DETERMINISTIC DEMONSTRATION</span><div className="prediction-number"><strong>{item.activity}%</strong><small>activity hypothesis</small></div><div className="interval-band"><i style={{ left: `${Math.max(5, item.activity - item.uncertainty)}%`, width: `${Math.min(35, item.uncertainty * 2)}%` }}/><b style={{ left: `${item.activity}%` }}/></div><div className="interval-labels"><span>Lower bound</span><span>Point estimate</span><span>Upper bound</span></div><div className="prediction-cards"><div><span>Predicted IC50</span><b>{item.predicted_ic50_um.toFixed(2)} µM</b></div><div><span>Confidence</span><b>{item.confidence}%</b></div><div><span>Uncertainty</span><b>±{item.uncertainty}</b></div></div></article>}</div><article className="module-card"><div className="card-title"><div><span>EXPLANATION</span><h2>What influenced this output</h2></div><b>Not causal attribution</b></div><div className="feature-bars">{[["Molecular descriptors",82],["Task-context seed",74],["Structural analogue support",68],["Domain proximity",77],["Evidence completeness",61]].map(([label,value]) => <div key={String(label)}><span>{label}</span><i><b style={{ width: `${value}%` }}/></i><em>{value}</em></div>)}</div></article></>;
}

function RankingWorkspace() {
  const [activity, setActivity] = useState(34);
  const [admet, setAdmet] = useState(18);
  const [uncertainty, setUncertainty] = useState(5);
  return <><WorkspaceHeader eyebrow="ANALYZE / POLICIES" title="Transparent ranking policy" description="Adjust demonstration weights and see how the versioned multi-objective score is composed."/><div className="module-grid two"><article className="module-card"><h2>Policy controls</h2>{[["Predicted activity",activity,setActivity],["ADMET panel",admet,setAdmet],["Uncertainty penalty",uncertainty,setUncertainty]] .map(([label,value,setter]) => <label className="range-field" key={String(label)}><span>{label}<b>{value}%</b></span><input type="range" min="0" max="50" value={Number(value)} onChange={(event) => (setter as (v:number)=>void)(Number(event.target.value))}/></label>)}<p className="policy-note">Remaining weights: selectivity 14%, novelty 10%, feasibility 10%, evidence 9%. Saved production policies require named approval.</p></article><article className="module-card score-composition"><h2>Score composition</h2><div className="stacked-score"><i style={{ width: `${activity}%` }}/><i style={{ width: "14%" }}/><i style={{ width: `${admet}%` }}/><i style={{ width: "10%" }}/><i style={{ width: "10%" }}/><i style={{ width: "9%" }}/></div><strong>{Math.min(100, activity + admet + 43 - uncertainty)}<small>/100 illustrative maximum</small></strong><ul><li>Hard filters retain explicit reasons.</li><li>Out-of-domain risk cannot improve a score.</li><li>Pareto and diversity labels remain visible.</li></ul></article></div></>;
}

function GovernanceWorkspace({ audit = false }: { audit?: boolean }) {
  if (audit) return <><WorkspaceHeader eyebrow="VALIDATE / LINEAGE" title="Audit and provenance ledger" description="Append-only events connect source, identity, prediction, ranking, experiment and governance decisions."/><article className="module-card"><div className="audit-timeline">{[["13:46:21","source.release.resolved","PubChem / ChEMBL registry metadata resolved"],["13:46:22","ranking.completed","Six candidates ranked under rank-policy@1.0"],["13:46:23","experiment.created","A549 CellTiter-Glo protocol locked"],["13:46:24","simulation.completed","72 synthetic observations generated"],["13:46:24","result.qc.passed","Five automated checks passed"],["13:46:25","training.eligibility.rejected","Simulation-only gate enforced"],["13:46:25","champion.confirmed","osiel-demo-activity@0.1 unchanged"]].map(([time,event,detail],index) => <div key={event}><i>{index + 1}</i><time>{time}</time><b>{event}</b><span>{detail}</span><code>sha256:{(index + 17).toString(16)}a9…{index}f2</code></div>)}</div></article></>;
  return <><WorkspaceHeader eyebrow="VALIDATE / GOVERNANCE" title="Model governance control room" description="Real feedback can improve a challenger only after QC, provenance and independent approval."/><div className="module-stats"><Stat label="CHAMPION" value="0.1" note="Approved demo reference"/><Stat label="REAL APPROVED ROWS" value="0" note="Awaiting measured data"/><Stat label="SIMULATION ELIGIBLE" value="0" note="Always blocked"/><Stat label="AUTO-PROMOTIONS" value="0" note="Prohibited by policy"/></div><div className="module-grid two"><article className="module-card model-card"><span>ONLINE CHAMPION</span><h2>osiel-demo-activity@0.1</h2><p>Deterministic integration-test model. Not trained on a validated oncology dataset.</p><dl className="spec-list"><div><dt>State</dt><dd>Reference only</dd></div><div><dt>Dataset</dt><dd>demo-descriptors@0.1</dd></div><div><dt>Rollback</dt><dd>Resolvable</dd></div></dl><button className="primary wide" disabled>Train challenger · awaiting approved real data</button></article><article className="module-card"><h2>Closed-loop learning pipeline</h2><ol className="learning-pipeline">{["Import measured result","Assay QC and provenance","Independent scientific approval","Immutable dataset snapshot","Leakage-safe challenger training","Calibration and slice evaluation","Named promotion decision"].map((step,index) => <li key={step} className={index === 0 ? "blocked" : "waiting"}><i>{index+1}</i><span><b>{step}</b><small>{index === 0 ? "Blocked · no approved measured rows" : "Waiting for prior gate"}</small></span></li>)}</ol></article></div><div className="claim-boundary"><b>Learning boundary:</b> uploaded files are quarantined until reviewed; simulations and failed-QC measurements remain permanently ineligible. Champion replacement is never automatic.</div></>;
}

function SettingsWorkspace() {
  return <><WorkspaceHeader eyebrow="SYSTEM / SETTINGS" title="Workspace and safety controls" description="Visible configuration for the research-use reference environment."/><div className="module-grid two"><article className="module-card"><h2>Scientific controls</h2>{[["Research-use banner",true],["Simulation watermark",true],["Training-eligibility gate",true],["Automatic model promotion",false],["Clinical recommendations",false]].map(([label,enabled]) => <div className="setting-row" key={String(label)}><div><b>{label}</b><span>{enabled ? "Enforced" : "Disabled by policy"}</span></div><i className={enabled ? "on" : "off"}><span/></i></div>)}</article><article className="module-card"><h2>Environment</h2><dl className="spec-list"><div><dt>Workspace</dt><dd>Discovery Lab</dd></div><div><dt>Mode</dt><dd>Developer reference</dd></div><div><dt>API</dt><dd>FastAPI v0.1</dd></div><div><dt>Frontend</dt><dd>Next.js workbench</dd></div><div><dt>Persistence</dt><dd>SQLite reference</dd></div><div><dt>Production target</dt><dd>PostgreSQL + RDKit</dd></div></dl></article></div></>;
}

export function ModuleWorkspace(props: Props) {
  const content = useMemo(() => {
    if (props.activeNav === "Open discovery") return <OpenDiscoveryWorkspace/>;
    if (props.activeNav === "Recursion gap map") return <RecursionRoadmap/>;
    if (props.activeNav === "Compound registry") return <RegistryWorkspace candidates={props.candidates}/>;
    if (props.activeNav === "Evidence sources") return <EvidenceWorkspace/>;
    if (props.activeNav === "Prediction studio") return <PredictionWorkspace candidates={props.candidates}/>;
    if (props.activeNav === "Model laboratory") return <ModelLab/>;
    if (props.activeNav === "Ranking policies") return <RankingWorkspace/>;
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
