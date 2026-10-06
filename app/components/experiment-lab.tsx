"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { RankedCandidate } from "../lib/demo-data";
import type { DryRunResult } from "../lib/osiel-client";
import { Compound3DViewer } from "./compound-3d-viewer";

type LabTab = "study" | "builder" | "live" | "debugger" | "results" | "structure" | "history" | "review" | "integrations";
type RunMode = "nominal" | "warning" | "failure";
type ReviewStatus = "pending" | "approved" | "rejected";
type Recommendation = { compoundId: string; name: string; priority: number; reason: string; action: string };

type ExperimentRecord = {
  id: string;
  title: string;
  cancerType: string;
  cellLine: string;
  assayType: string;
  status: "completed" | "warning" | "failed" | "cancelled";
  reviewStatus: ReviewStatus;
  actorEmail: string;
  compoundIds: string[];
  observationCount: number;
  createdAt: string;
  updatedAt: string;
  payload: {
    doseMin: number;
    doseMax: number;
    dosePoints: number;
    replicates: number;
    durationHours: number;
    estimatedIc50: Record<string, number>;
    qcChecks: Array<{ label: string; status: "pass" | "warn" | "fail"; detail: string }>;
    disclaimer: string;
    failureReasons?: string[];
    recommendations?: Recommendation[];
    reportConclusion?: string;
    parentExperimentId?: string;
  };
};

type Props = {
  candidates: RankedCandidate[];
  selectedIds: string[];
  onRunExperiment: () => Promise<DryRunResult | null>;
};

const stages = [
  ["Validate protocol", "Checking endpoint, units, controls and selected candidates"],
  ["Resolve identities", "Matching standardized structures and registry identifiers"],
  ["Retrieve evidence", "Reading curated PubMed, PubChem and ChEMBL context"],
  ["Prepare virtual plate", "Assigning controls, dose series and technical replicates"],
  ["Initialize simulator", "Locking the deterministic seed and response model"],
  ["Generate observations", "Calculating 72 bounded synthetic viability measurements"],
  ["Fit response curves", "Estimating sigmoid parameters and IC50 hypotheses"],
  ["Run quality control", "Checking completeness, controls, ranges and replicate CV"],
  ["Apply governance gate", "Blocking simulated rows from model-training eligibility"],
  ["Publish result", "Saving the record, audit events and downloadable report"],
] as const;

const debugStages = [
  { module:"protocol.validator", input:"A549 · CellTiter-Glo · 8 doses · 3 replicates", operation:"Validate required fields, units, control plan and expected observation count.", output:"Protocol schema v1.0 accepted · 72 observations expected", check:"Required fields present; dose_min < dose_max; replicates ≥ 2", code:"expected_rows = candidates × doses × replicates\n3 × 8 × 3 = 72" },
  { module:"identity.resolver", input:"3 OSIEL compound identifiers", operation:"Resolve standardized names, formulas, source class and model-domain status.", output:"3/3 identities resolved · no duplicate structures", check:"Unique compound ID and canonical identity required", code:"identity = registry.resolve(compound_id)\nassert identity.status == 'resolved'" },
  { module:"evidence.retriever", input:"Compound + A549 + viability context", operation:"Match curated evidence metadata without converting literature claims into measurements.", output:"Source context attached · evidence remains study-specific", check:"Source URL, publication identity and evidence class retained", code:"context = evidence.search(compound, model='A549')\ncontext.data_class = 'literature_metadata'" },
  { module:"plate.mapper", input:"96 wells · 3 candidates · vehicle and positive controls", operation:"Assign dose groups, replicates and controls to deterministic well positions.", output:"Plate map complete · no well collisions", check:"Every well unique; every dose has replicates; controls present", code:"well_key = plate_id + ':' + well\nassert unique(well_key)" },
  { module:"simulation.seed", input:"Protocol fingerprint + candidate IDs", operation:"Create a reproducible seed so an auditor can repeat the exact software run.", output:"Deterministic seed locked · simulation_only=true", check:"Same input fingerprint must generate the same seed", code:"seed = sha256(protocol + compound_ids)[0:8]\nrandom.lock(seed)" },
  { module:"response.generator", input:"Dose series + candidate IC50 hypothesis + locked seed", operation:"Generate bounded sigmoid responses with small deterministic replicate variation.", output:"72 synthetic viability observations generated", check:"0% ≤ viability ≤ 110%; no NaN or infinite values", code:"y = bottom + (top-bottom) / (1 + (dose/IC50)^hill)\ny = clamp(y + seeded_noise, 0, 110)" },
  { module:"curve.fitter", input:"Dose and synthetic viability pairs", operation:"Estimate response parameters and an IC50 hypothesis for each candidate.", output:"3 curves fitted · parameters and residuals retained", check:"Fit converged; finite parameters; sufficient dose coverage", code:"θ* = argmin Σ(y_observed - y_4PL(θ))²\nreport IC50 with data_class='simulated'" },
  { module:"quality.control", input:"Observations, controls, plate map and fit diagnostics", operation:"Evaluate completeness, controls, bounds and replicate coefficient of variation.", output:"QC decision generated with pass/warn/fail reasons", check:"Expected rows; controls; bounds; median CV; missingness", code:"CV% = 100 × standard_deviation / mean\nstatus = all(gates) ? PASS : BLOCK" },
  { module:"governance.guard", input:"Data class, QC status and review state", operation:"Apply training eligibility and publication rules before any downstream use.", output:"0 simulated rows eligible · champion unchanged", check:"simulation_only must always imply training_eligible=false", code:"if row.simulation_only:\n    row.training_eligible = false" },
  { module:"result.publisher", input:"Result, diagnostics, provenance and governance decision", operation:"Assemble the auditable result package and experiment history record.", output:"JSON + CSV + review record ready", check:"Result links protocol, source context, QC and parent run", code:"package = sign({protocol, observations, qc, lineage})\naudit.append('result.published')" },
] as const;

const doses = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30];
const readinessItems = ["Named supervisor / PI approval recorded","Faculty biosafety / ethics route confirmed","Living data-management plan created","Cell identity and mycoplasma status verified","Plate reader calibration current","Reagent lot and expiry recorded","Vehicle, positive and intermediate QC controls locked"];
const requiredImportColumns = ["plate_id","well","compound_id","concentration_um","replicate","raw_luminescence","control_type"];

const seedHistory: ExperimentRecord[] = [
  {
    id: "EXP-NSCLC-A549-001", title: "A549 three-candidate dose response", cancerType: "NSCLC", cellLine: "A549", assayType: "CellTiter-Glo", status: "completed", reviewStatus: "approved", actorEmail: "demo-researcher@oncogon.local", compoundIds: ["OSIEL-CMP-0001", "OSIEL-CMP-0002", "OSIEL-CMP-0004"], observationCount: 72, createdAt: "2026-08-19T08:16:25.000Z", updatedAt: "2026-08-19T08:18:02.000Z",
    payload: { doseMin: 0.01, doseMax: 30, dosePoints: 8, replicates: 3, durationHours: 72, estimatedIc50: { "OSIEL-CMP-0001": 2.47, "OSIEL-CMP-0002": 3.12, "OSIEL-CMP-0004": 5.87 }, disclaimer: "Computational simulation only. No physical assay was performed.", qcChecks: [
      { label: "Expected observations", status: "pass", detail: "72 of 72 present" }, { label: "Control wells", status: "pass", detail: "Vehicle and positive controls present" }, { label: "Replicate consistency", status: "pass", detail: "Median CV 3.8%" }, { label: "Training eligibility", status: "pass", detail: "0 simulated rows eligible" },
    ] },
  },
  {
    id: "EXP-NSCLC-A549-000", title: "Range-finding verification", cancerType: "NSCLC", cellLine: "A549", assayType: "CellTiter-Glo", status: "warning", reviewStatus: "pending", actorEmail: "demo-researcher@oncogon.local", compoundIds: ["OSIEL-CMP-0003", "OSIEL-CMP-0007"], observationCount: 48, createdAt: "2026-08-18T10:41:00.000Z", updatedAt: "2026-08-18T10:41:00.000Z",
    payload: { doseMin: 0.01, doseMax: 30, dosePoints: 8, replicates: 3, durationHours: 72, estimatedIc50: { "OSIEL-CMP-0003": 4.64, "OSIEL-CMP-0007": 8.21 }, disclaimer: "Computational simulation only.", qcChecks: [{ label: "Replicate consistency", status: "warn", detail: "One dose exceeds the 15% CV threshold" }, { label: "Training eligibility", status: "pass", detail: "0 simulated rows eligible" }] },
  },
  {
    id: "EXP-BREAST-MDA-004", title: "MDA-MB-231 failed control scenario", cancerType: "TNBC", cellLine: "MDA-MB-231", assayType: "CellTiter-Glo", status: "failed", reviewStatus: "rejected", actorEmail: "demo-researcher@oncogon.local", compoundIds: ["OSIEL-CMP-0005"], observationCount: 24, createdAt: "2026-08-17T07:12:00.000Z", updatedAt: "2026-08-17T07:14:00.000Z",
    payload: { doseMin: 0.01, doseMax: 30, dosePoints: 8, replicates: 3, durationHours: 72, estimatedIc50: {}, disclaimer: "Computational failure scenario only.", qcChecks: [{ label: "Positive control response", status: "fail", detail: "Control did not cross the acceptance threshold" }, { label: "Result publication", status: "fail", detail: "Result blocked by QC" }] },
  },
];

function wait(ms: number) { return new Promise((resolve) => window.setTimeout(resolve, ms)); }

function recordStatus(mode: RunMode): ExperimentRecord["status"] { return mode === "failure" ? "failed" : mode === "warning" ? "warning" : "completed"; }

function qcFor(mode: RunMode, count: number): ExperimentRecord["payload"]["qcChecks"] {
  const rows: ExperimentRecord["payload"]["qcChecks"] = [
    { label: "Expected observations", status: mode === "failure" ? "fail" : "pass", detail: mode === "failure" ? `${Math.max(0, count - 6)} of ${count} present` : `${count} of ${count} present` },
    { label: "Control wells", status: mode === "failure" ? "fail" : "pass", detail: mode === "failure" ? "Positive control below acceptance threshold" : "Vehicle and positive controls present" },
    { label: "Viability bounds", status: "pass", detail: "All values between 0% and 110%" },
    { label: "Replicate consistency", status: mode === "warning" ? "warn" : mode === "failure" ? "fail" : "pass", detail: mode === "warning" ? "One dose has CV 17.4%; reviewer attention required" : mode === "failure" ? "Three doses exceed CV threshold" : "Median CV 3.8%" },
    { label: "Training eligibility", status: "pass", detail: "0 simulated rows eligible for training" },
  ];
  return rows;
}

function recommendNext(candidates: RankedCandidate[], excluded: string[], failed: boolean): Recommendation[] {
  return candidates.filter((item) => !excluded.includes(item.compound_id) && item.applicability_domain !== "outside").map((item) => {
    const safety = item.admet.filter((endpoint) => endpoint.className === "good").length;
    const priority = Number((item.score * .45 + item.activity * .22 + item.selectivity * .14 + item.confidence * .14 + safety * 1.25 - item.uncertainty * .05).toFixed(1));
    return { compoundId:item.compound_id, name:item.display_name, priority, reason:`OSIEL score ${item.score.toFixed(1)}, ${item.confidence}% confidence, ${item.selectivity}% selectivity and ${safety}/4 favorable ADMET signals.`, action:failed ? "Replace the failed candidate and repeat the same protocol with unchanged controls." : "Advance as the next diversity-aware candidate while retaining the current result as comparator." };
  }).sort((a,b) => b.priority - a.priority).slice(0,3);
}

function download(name: string, type: string, content: string) {
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(new Blob([content], { type }));
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(anchor.href);
}

function PlateMap({ names }: { names: string[] }) {
  const wells = Array.from({ length: 96 }, (_, index) => {
    const row = Math.floor(index / 12); const column = index % 12;
    const type = column === 0 ? "negative" : column === 11 ? "positive" : row < 3 ? "compound-a" : row < 6 ? "compound-b" : "compound-c";
    return { label: `${String.fromCharCode(65 + row)}${column + 1}`, type };
  });
  return <div className="plate-wrap"><div className="plate-grid">{wells.map((well) => <span key={well.label} className={well.type} title={well.label}>{well.label}</span>)}</div><div className="plate-legend"><span><i className="negative"/>Vehicle</span><span><i className="compound-a"/>{names[0] ?? "Candidate 1"}</span><span><i className="compound-b"/>{names[1] ?? "Candidate 2"}</span><span><i className="compound-c"/>{names[2] ?? "Candidate 3"}</span><span><i className="positive"/>Positive control</span></div></div>;
}

function CurveChart({ records }: { records: Array<{ name: string; color: string; ic50: number }> }) {
  const series = records.map((record, seriesIndex) => ({ ...record, values: doses.map((dose) => Math.max(3, Math.round(100 / (1 + Math.pow(dose / record.ic50, 1.25 + seriesIndex * 0.08))))) }));
  return <div className="curve-panel"><div className="chart-axis y"><span>100</span><span>75</span><span>50</span><span>25</span><span>0</span></div><svg viewBox="0 0 760 270" role="img" aria-label="Simulated dose response curves">
    {[35,85,135,185,235].map((y) => <line key={y} x1="42" y1={y} x2="735" y2={y} stroke="#e8eaf1"/>) }
    {series.map((item) => { const points = item.values.map((value,index) => `${55 + index * 95},${235 - value * 2}`).join(" "); return <g key={item.name}><polyline points={points} fill="none" stroke={item.color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>{item.values.map((value,index) => <circle key={index} cx={55 + index * 95} cy={235 - value * 2} r="5" fill="white" stroke={item.color} strokeWidth="3"/>)}</g>; })}
  </svg><div className="chart-axis x">{doses.map((dose) => <span key={dose}>{dose}</span>)}</div><div className="axis-label">Dose (µM, logarithmic series) · Simulated relative viability (%)</div><div className="chart-legend">{series.map((item) => <span key={item.name}><i style={{background:item.color}}/>{item.name} · IC50 {item.ic50.toFixed(2)} µM</span>)}</div></div>;
}

export function ExperimentLab({ candidates, selectedIds, onRunExperiment }: Props) {
  const [tab, setTab] = useState<LabTab>("study");
  const [title, setTitle] = useState("A549 three-candidate dose response");
  const [cellLine, setCellLine] = useState("A549");
  const [assay, setAssay] = useState("CellTiter-Glo");
  const [replicates, setReplicates] = useState(3);
  const [duration, setDuration] = useState(72);
  const [mode, setMode] = useState<RunMode>("nominal");
  const [running, setRunning] = useState(false);
  const [stageIndex, setStageIndex] = useState(-1);
  const [debugStep, setDebugStep] = useState(0);
  const [autoFollow, setAutoFollow] = useState(true);
  const [logs, setLogs] = useState<string[]>([]);
  const [history, setHistory] = useState<ExperimentRecord[]>(seedHistory);
  const [currentId, setCurrentId] = useState(seedHistory[0].id);
  const [role, setRole] = useState<"researcher" | "reviewer" | "admin">("researcher");
  const [persistence, setPersistence] = useState("Loading history…");
  const [importReport, setImportReport] = useState<{name:string;rows:number;mapped:string[];missing:string[]}|null>(null);
  const [institution, setInstitution] = useState("Independent South African university");
  const [supervisor, setSupervisor] = useState("");
  const [readiness, setReadiness] = useState<string[]>([]);
  const [queuedIds, setQueuedIds] = useState(() => (selectedIds.length ? selectedIds : candidates.slice(0,3).map((item) => item.compound_id)).slice(0,3));
  const [parentExperimentId, setParentExperimentId] = useState<string | undefined>();
  const [structureCompoundId, setStructureCompoundId] = useState(seedHistory[0].compoundIds[0]);
  const runToken = useRef(0);

  useEffect(() => {
    fetch("/api/experiments").then(async (response) => {
      if (!response.ok) throw new Error();
      const data = await response.json() as { experiments?: ExperimentRecord[] };
      if (data.experiments?.length) { setHistory(data.experiments); setCurrentId(data.experiments[0].id); }
      setPersistence("Durable D1 history active");
    }).catch(() => setPersistence("Reference history loaded; durable storage activates after deployment"));
  }, []);

  const current = history.find((item) => item.id === currentId) ?? history[0];
  const activeStructureId = current?.compoundIds.includes(structureCompoundId)
    ? structureCompoundId
    : current?.compoundIds[0];
  const activeStructureCandidate = candidates.find((item) => item.compound_id === activeStructureId);
  const selectedCandidates = queuedIds;
  const resultSeries = useMemo(() => {
    const colors = ["#705ed6", "#0aa989", "#d9901a"];
    return (current?.compoundIds ?? selectedCandidates).slice(0,3).map((id,index) => ({ name: candidates.find((item) => item.compound_id === id)?.display_name ?? id, color: colors[index], ic50: Number(current?.payload.estimatedIc50[id] ?? candidates.find((item) => item.compound_id === id)?.predicted_ic50_um ?? 2 + index) }));
  }, [current, candidates, selectedCandidates]);

  async function saveRecord(record: ExperimentRecord) {
    try {
      const response = await fetch("/api/experiments", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(record) });
      if (!response.ok) throw new Error();
      setPersistence("Saved to durable experiment history");
    } catch { setPersistence("Saved in this session; hosted database sync unavailable"); }
  }

  async function startRun() {
    if (running || selectedCandidates.length === 0) return;
    const token = ++runToken.current;
    setRunning(true); setStageIndex(0); setDebugStep(0); setLogs([]); setTab("debugger");
    const enginePromise = onRunExperiment();
    for (let index = 0; index < stages.length; index += 1) {
      if (runToken.current !== token) return;
      setStageIndex(index);
      setLogs((items) => [...items, `${new Date().toLocaleTimeString()}  ${stages[index][0]} — ${stages[index][1]}`]);
      await wait(index === 5 ? 900 : 520);
    }
    if (runToken.current !== token) return;
    const result = await enginePromise;
    const id = result?.experimentId && !result.experimentId.includes("EMBEDDED") ? result.experimentId : `EXP-${cellLine}-${Date.now().toString().slice(-6)}`;
    const count = selectedCandidates.length * 8 * replicates;
    const estimated = result?.estimatedIc50 ?? Object.fromEntries(selectedCandidates.map((compoundId,index) => [compoundId, Number((2.1 + index * 1.43).toFixed(2))]));
    const failureReasons = mode === "failure" ? ["Positive-control response was below the acceptance threshold.", "Six expected observations were missing.", "Three concentration groups exceeded the replicate-CV limit."] : mode === "warning" ? ["One concentration group exceeded the advisory replicate-CV threshold."] : [];
    const recommendations = recommendNext(candidates, selectedCandidates, mode === "failure");
    const record: ExperimentRecord = {
      id, title, cancerType: cellLine === "MDA-MB-231" ? "TNBC" : "NSCLC", cellLine, assayType: assay,
      status: recordStatus(mode), reviewStatus: "pending", actorEmail: "current-workspace-user", compoundIds: selectedCandidates,
      observationCount: mode === "failure" ? Math.max(0, count - 6) : count, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
      payload: { doseMin: 0.01, doseMax: 30, dosePoints: 8, replicates, durationHours: duration, estimatedIc50: estimated, qcChecks: qcFor(mode, count), disclaimer: result?.disclaimer ?? "Computational simulation only. No physical assay or wet-lab measurement was performed.", failureReasons, recommendations, parentExperimentId, reportConclusion: mode === "failure" ? "Run invalidated. Do not interpret potency; replace the failed candidate and repeat with identical controls." : parentExperimentId ? `Recovery simulation passed after replacing the candidate recommended from ${parentExperimentId}.` : mode === "warning" ? "Result retained for review, but repeat the flagged concentration before progression." : "All software QC gates passed. The result package is ready for scientific review and the next prioritized candidate can enter a follow-up simulation." },
    };
    setHistory((items) => [record, ...items.filter((item) => item.id !== record.id)]); setCurrentId(record.id);
    await saveRecord(record);
    setRunning(false); setStageIndex(stages.length); setDebugStep(stages.length - 1); setTab("debugger");
  }

  function applyRecommendation(recommendation: Recommendation) {
    const alternatives = (current?.payload.recommendations ?? []).filter((item) => item.compoundId !== recommendation.compoundId).map((item) => item.compoundId);
    setQueuedIds([recommendation.compoundId, ...alternatives].slice(0,3));
    setParentExperimentId(current?.id);
    setMode("nominal");
    setTitle(`Recovery test · ${recommendation.name}`);
    setTab("builder");
  }

  function cancelRun() {
    runToken.current += 1; setRunning(false); setLogs((items) => [...items, `${new Date().toLocaleTimeString()}  Run cancelled by operator`]); setStageIndex(-1); setTab("builder");
  }

  async function review(decision: ReviewStatus) {
    if (!current || role === "researcher") return;
    setHistory((items) => items.map((item) => item.id === current.id ? { ...item, reviewStatus: decision, updatedAt: new Date().toISOString() } : item));
    try { await fetch("/api/experiments", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: current.id, reviewStatus: decision }) }); } catch { /* visible local state remains usable */ }
  }

  const observationRows = resultSeries.flatMap((series) => doses.map((dose,index) => ({ compound: series.name, dose, replicate: (index % 3) + 1, viability: Math.max(3, Math.round(100 / (1 + Math.pow(dose / series.ic50, 1.3)))), cv: (2.6 + index * .43).toFixed(1) })));
  const csv = ["compound,dose_um,replicates,mean_viability_percent,cv_percent,data_class", ...observationRows.map((row) => `${row.compound},${row.dose},3,${row.viability},${row.cv},simulated`)].join("\n");
  const progress = Math.max(0, Math.min(100, Math.round(((stageIndex + 1) / stages.length) * 100)));
  const visibleDebugStep = autoFollow && stageIndex >= 0 ? Math.min(stageIndex, debugStages.length - 1) : debugStep;
  const debugDetail = debugStages[visibleDebugStep];
  const tracePackage = { run:{ title, cellLine, assay, scenario:mode, durationHours:duration }, inputs:{ compounds:selectedCandidates, doses, replicates }, stages:debugStages.map((item,index) => ({ index:index+1, module:item.module, status:index < stageIndex || stageIndex === stages.length ? "completed" : index === stageIndex && running ? "running" : "pending", input:item.input, operation:item.operation, output:item.output, validation:item.check })), events:logs, dataBoundary:"Computational simulation only; not a physical laboratory measurement." };
  const visibleRecommendations = current ? (current.payload.recommendations?.length ? current.payload.recommendations : recommendNext(candidates,current.compoundIds,current.status === "failed")) : [];
  const visibleFailureReasons = current?.payload.failureReasons?.length ? current.payload.failureReasons : current?.payload.qcChecks.filter((check) => check.status === "fail").map((check) => check.detail) ?? [];
  const readinessPercent = Math.round((readiness.length / readinessItems.length) * 100);
  const runSheet = { studyId:"OSIEL-A549-TEACHING-001", institutionProfile:institution, supervisor, researchQuestion:"Which prioritized candidates produce a reproducible A549 viability response under the locally approved assay SOP?", biologicalModel:"A549", assay:"CellTiter-Glo", plateFormat:"96-well", dataClass:"teaching simulation until measured instrument data is imported", readiness:readinessItems.map((item) => ({ item, confirmed:readiness.includes(item) })), sources:["NCATS Assay Guidance Manual","Promega CellTiter-Glo protocol","UCT research data management and biosafety guidance","Stellenbosch SunDMP guidance"] };
  const workflowCompound = candidates.find((item) => item.compound_id === (current?.compoundIds[0] ?? selectedCandidates[0]));
  const workflowExperimentId = current?.id ?? "NEW EXPERIMENT";
  const workflowCards: Array<{ step:string; title:string; owner:string; badge:string; summary:string; rows:string[]; action:string; target:LabTab }> = [
    { step:"1", title:"AI suggests a test", owner:"OSIEL AI", badge:"PREDICTION", summary:"Turn the selected candidate into a traceable experimental hypothesis.", rows:["Hypothesis and test rationale","Supporting evidence","Uncertainty and model context"], action:"Review experiment proposal", target:"builder" },
    { step:"2", title:"Researcher approves", owner:"Researcher", badge:"APPROVAL", summary:"Review protocol, controls and measurements before the experiment proceeds.", rows:["Protocol definition","Controls and dose plan","Acceptance rules"], action:"Open protocol builder", target:"builder" },
    { step:"3", title:"Lab execution", owner:"Research team", badge:"EXECUTION", summary:"Track the approved workflow against the same Experiment ID.", rows:["Experiment progress","Sample and plate context","Instrument workflow"], action:"Open live run", target:"live" },
    { step:"4", title:"Upload measured results", owner:"Lab assistant", badge:"MEASURED DATA", summary:"Bring instrument exports and supporting measurements into the governed record.", rows:["Instrument data import","Schema and QC validation","Source-file preservation"], action:"Open data integrations", target:"integrations" },
    { step:"5", title:"QC & scientific review", owner:"Researcher", badge:"REVIEW", summary:"Review quality controls, compare the result with the prediction context and record a decision.", rows:["Quality-control checks","Result interpretation","Approve, reject or repeat"], action:"Open scientific review", target:"review" },
    { step:"6", title:"Decide the next experiment", owner:"Researcher + OSIEL", badge:"NEXT ACTION", summary:"Keep the reviewed evidence linked to history and prepare the next governed run.", rows:["Preserve research history","Review next candidates","Create follow-up experiment"], action:"Review next action", target:"results" },
  ];

  return <div className="lab-console">
    <section className="module-heading"><div><span>VALIDATE / EXPERIMENTS</span><h1>End-to-end laboratory workflow</h1><p>Create, run, inspect, review and export a governed dose-response simulation.</p></div><div className="heading-actions"><span className="persistence-pill"><i/>{persistence}</span><button className="primary" onClick={startRun} disabled={running}>{running ? "Experiment running…" : "Run new experiment"}</button></div></section>
    <div className="lab-disclaimer"><b>Simulation-only environment</b><span>No physical instrument is connected and no displayed result is a biological measurement.</span></div>

    <section className="experiment-flow-shell">
      <div className="experiment-flow-heading">
        <div>
          <span>OSIEL EXPERIMENT WORKFLOW</span>
          <h2>AI prediction → Lab execution → Researcher review</h2>
          <p>One Experiment ID connects the hypothesis, approved protocol, experiment execution, measured evidence, quality review and the next research decision.</p>
        </div>
        <div className="experiment-flow-context">
          <span>{workflowExperimentId}</span>
          <b>{workflowCompound?.display_name ?? title}</b>
          <small>{running ? "Experiment running" : current ? `${current.status} · ${current.reviewStatus} review` : "Ready for a new experiment"}</small>
        </div>
      </div>

      <div className="experiment-flow-grid">
        {workflowCards.map((card) => <article className="experiment-flow-card" key={card.step}>
          <div className="experiment-flow-card-head">
            <i>{card.step}</i>
            <div><h3>{card.title}</h3><span>Owner: {card.owner}</span></div>
            <em>{card.badge}</em>
          </div>
          <p>{card.summary}</p>
          <ul>{card.rows.map((row) => <li key={row}><span>✓</span>{row}</li>)}</ul>
          <button onClick={() => setTab(card.target)}>{card.action} →</button>
        </article>)}
      </div>

      <div className="experiment-flow-footer">
        <strong>AI proposes. Researcher approves. Lab evidence validates.</strong>
        <span>Reviewed evidence remains linked to {workflowExperimentId} and can inform the next governed experiment.</span>
      </div>
    </section>

    <div className="lab-nav">{(["study","builder","live","debugger","results","structure","history","review","integrations"] as LabTab[]).map((item,index) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}><span>{String(index + 1).padStart(2,"0")}</span>{item === "study" ? "University study" : item === "live" ? "Live run" : item === "debugger" ? "Experiment debugger" : item === "structure" ? "3D structure" : item[0].toUpperCase() + item.slice(1)}{(item === "live" || item === "debugger") && running && <i/>}</button>)}</div>

    {tab === "study" && <><section className="university-hero"><div><span>UNIVERSITY-READY TEACHING TEMPLATE</span><h2>Cape Town research workflow</h2><p>A549 viability study planning aligned to public UCT and Stellenbosch governance concepts and authoritative assay guidance.</p></div><b>{readinessPercent}% READY</b></section><div className="university-notice"><b>No university endorsement</b><span>This independent teaching reference is not affiliated with or endorsed by the University of Cape Town or Stellenbosch University. Your local committee, supervisor and SOP always control physical work.</span></div><div className="module-grid university-grid"><article className="module-card"><div className="card-title"><div><span>STUDY ID · OSIEL-A549-TEACHING-001</span><h2>Research definition</h2></div><b>RUO</b></div><label className="lab-field"><span>Institution profile</span><select value={institution} onChange={(event) => setInstitution(event.target.value)}><option>Independent South African university</option><option>UCT governance reference</option><option>Stellenbosch governance reference</option></select></label><label className="lab-field"><span>Named supervisor / PI</span><input value={supervisor} onChange={(event) => setSupervisor(event.target.value)} placeholder="Required before a physical run"/></label><dl className="spec-list"><div><dt>Research question</dt><dd>Which prioritized candidates produce a reproducible A549 viability response under the locally approved SOP?</dd></div><div><dt>Teaching model</dt><dd>A549 · CellTiter-Glo · 96-well</dd></div><div><dt>Software output</dt><dd>Simulation until measured instrument data is imported and approved</dd></div></dl><div className="export-actions"><button onClick={() => download("OSIEL-A549-teaching-run-sheet.json","application/json",JSON.stringify(runSheet,null,2))}>Download student run sheet</button><button className="primary" onClick={() => { setCellLine("A549"); setAssay("CellTiter-Glo"); setMode("nominal"); setTitle("Cape Town A549 teaching simulation"); setTab("builder"); }}>Prepare teaching simulation →</button></div></article><article className="module-card readiness-card"><div className="card-title"><div><span>STOP / GO GATE</span><h2>Institutional readiness</h2></div><b>{readiness.length}/{readinessItems.length}</b></div><div className="readiness-progress"><i style={{width:`${readinessPercent}%`}}/></div>{readinessItems.map((item) => <label key={item}><input type="checkbox" checked={readiness.includes(item)} onChange={() => setReadiness((items) => items.includes(item) ? items.filter((value) => value !== item) : [...items,item])}/><span>{item}</span></label>)}<div className={readinessPercent === 100 && supervisor.trim() ? "go-decision ready" : "go-decision blocked"}><b>{readinessPercent === 100 && supervisor.trim() ? "SOFTWARE GATE COMPLETE" : "PHYSICAL RUN BLOCKED"}</b><span>{readinessPercent === 100 && supervisor.trim() ? "Hand the plan to the named supervisor for the institution’s final authorization." : "Complete every item and name the responsible supervisor. This does not itself grant laboratory approval."}</span></div></article></div><article className="module-card protocol-roadmap"><div className="card-title"><div><span>GUIDED WORKFLOW</span><h2>From approved plan to governed evidence</h2></div><b>Follow local SOP for operational details</b></div><ol>{[["Plan and approve","Define the question, DMP, responsibilities and applicable institutional approvals."],["Verify materials","Record standardized compound identity, cell provenance, authentication and contamination status."],["Lock controls and layout","Predefine vehicle, positive and intermediate QC controls, replicates and acceptance rules."],["Execute approved local SOP","A trained researcher performs exposure and reagent handling under the institution’s authorized protocol."],["Capture raw signal","Preserve the plate-reader export and metadata before normalization or fitting."],["Validate and normalize","Check schema, controls, completeness and replicate consistency before interpreting response."],["Scientific review","A separate reviewer approves or rejects the measured record and documents deviations."],["Governed learning","Only approved measured rows enter an immutable challenger dataset; simulations remain excluded."]].map(([name,detail],index) => <li key={name}><i>{index+1}</i><span><b>{name}</b><small>{detail}</small></span></li>)}</ol></article><div className="study-sources">{[["NCATS cell viability guidance","https://www.ncbi.nlm.nih.gov/books/NBK144065/"],["Promega CellTiter-Glo protocol","https://www.promega.com/resources/protocols/technical-bulletins/0/celltiter-glo-luminescent-cell-viability-assay-protocol/"],["UCT research data management","https://lib.uct.ac.za/digitalservices/documentation/rdm-policy"],["UCT biosafety","https://uct.ac.za/research-support-hub/integrity/biosafety"],["Stellenbosch SunDMP guidance","https://blogs.sun.ac.za/libraryresearchnews/2025/06/03/what-to-consider-before-using-sus-sundmp/" ]].map(([label,url]) => <a key={url} href={url} target="_blank" rel="noreferrer">{label}<span>Authoritative source ↗</span></a>)}</div></>}

    {tab === "builder" && <div className="module-grid builder-grid"><article className="module-card"><div className="card-title"><div><span>PROTOCOL</span><h2>Experiment definition</h2></div><b>Draft</b></div><label className="lab-field"><span>Experiment name</span><input value={title} onChange={(event) => setTitle(event.target.value)}/></label><div className="lab-form-grid"><label className="lab-field"><span>Cell line</span><select value={cellLine} onChange={(event) => setCellLine(event.target.value)}><option>A549</option><option>H1975</option><option>HCC827</option><option>MDA-MB-231</option></select></label><label className="lab-field"><span>Assay</span><select value={assay} onChange={(event) => setAssay(event.target.value)}><option>CellTiter-Glo</option><option>Resazurin viability</option><option>Caspase 3/7</option></select></label><label className="lab-field"><span>Technical replicates</span><select value={replicates} onChange={(event) => setReplicates(Number(event.target.value))}><option value="2">2</option><option value="3">3</option><option value="4">4</option></select></label><label className="lab-field"><span>Exposure</span><select value={duration} onChange={(event) => setDuration(Number(event.target.value))}><option value="24">24 hours</option><option value="48">48 hours</option><option value="72">72 hours</option></select></label></div><label className="lab-field"><span>Simulation scenario</span><select value={mode} onChange={(event) => setMode(event.target.value as RunMode)}><option value="nominal">Nominal — all QC checks pass</option><option value="warning">Warning — reviewer attention required</option><option value="failure">Failure — controls invalidate the run</option></select></label></article><article className="module-card"><div className="card-title"><div><span>CANDIDATES</span><h2>Selected research set</h2></div><b>{selectedCandidates.length} queued</b></div><div className="builder-candidates">{selectedCandidates.map((id,index) => { const item = candidates.find((candidate) => candidate.compound_id === id); return <div key={id}><i>{index + 1}</i><span><b>{item?.display_name ?? id}</b><small>{item?.formula ?? "Standardized identity"}</small></span><em>{item?.confidence ?? 0}% confidence</em></div>; })}</div><dl className="spec-list compact"><div><dt>Dose range</dt><dd>0.01–30 µM</dd></div><div><dt>Dose points</dt><dd>8 logarithmic</dd></div><div><dt>Controls</dt><dd>Vehicle + positive</dd></div><div><dt>Expected observations</dt><dd>{selectedCandidates.length * 8 * replicates}</dd></div></dl><button className="primary wide" onClick={startRun} disabled={!title.trim() || selectedCandidates.length === 0}>Validate and start simulation</button></article></div>}

    {tab === "live" && <div className="live-run-layout"><article className="module-card live-engine"><div className="live-orbit"><div className="orbit-ring one"/><div className="orbit-ring two"/><div className="orbit-core"><b>{progress}%</b><span>{running ? "PROCESSING" : stageIndex === stages.length ? "COMPLETE" : "READY"}</span></div></div><h2>{running ? stages[Math.max(0,stageIndex)][0] : stageIndex === stages.length ? "Experiment completed" : "No active run"}</h2><p>{running ? stages[Math.max(0,stageIndex)][1] : "Configure a protocol and start a fresh simulation."}</p><div className="progress-track"><i style={{width:`${progress}%`}}/></div><div className="live-actions"><span>Elapsed workflow stage {Math.max(0,stageIndex + 1)} of {stages.length}</span>{running && <button onClick={cancelRun}>Cancel experiment</button>}</div></article><article className="module-card stage-card"><h2>Processing stages</h2><ol className="stage-list">{stages.map(([name,detail],index) => <li key={name} className={index < stageIndex ? "done" : index === stageIndex && running ? "active" : "pending"}><i>{index < stageIndex || (!running && stageIndex === stages.length) ? "✓" : index + 1}</i><span><b>{name}</b><small>{detail}</small></span>{index === stageIndex && running && <em>RUNNING</em>}</li>)}</ol></article><article className="module-card log-console"><div className="card-title"><div><span>LIVE ACTIVITY</span><h2>Engine event log</h2></div><b>{logs.length} events</b></div><pre>{logs.length ? logs.join("\n") : "Waiting for an experiment run…"}</pre></article></div>}

    {tab === "debugger" && <div className="debugger-shell"><section className="debugger-header"><div><span>SCIENTIST INSPECTION MODE</span><h2>Experiment execution debugger</h2><p>Watch the engine transform inputs into a governed result, inspect each rule, and export the complete trace.</p></div><div className="debugger-actions"><label><input type="checkbox" checked={autoFollow} onChange={(event) => setAutoFollow(event.target.checked)}/> Auto-follow active step</label><button onClick={() => download("osiel-execution-trace.json","application/json",JSON.stringify(tracePackage,null,2))}>Export trace JSON</button>{running ? <button className="danger" onClick={cancelRun}>Stop run</button> : stageIndex === stages.length ? <button className="primary" onClick={() => setTab("results")}>Open result →</button> : <button className="primary" onClick={startRun}>Start debugger run</button>}</div></section><div className="debugger-status"><div><span>RUN STATE</span><b className={running ? "running" : stageIndex === stages.length ? "complete" : "idle"}>{running ? "EXECUTING" : stageIndex === stages.length ? "COMPLETE" : "READY"}</b></div><div><span>PROGRESS</span><b>{progress}%</b></div><div><span>TRACE EVENTS</span><b>{logs.length}</b></div><div><span>DATA CLASS</span><b>SIMULATED</b></div><div><span>TRAINING ELIGIBLE</span><b>0 ROWS</b></div></div><div className="debug-progress"><i style={{width:`${progress}%`}}/></div><div className="debugger-grid"><aside className="debug-step-list"><div className="debug-panel-title"><span>PIPELINE</span><b>{stages.length} inspectable stages</b></div>{debugStages.map((item,index) => { const state = index < stageIndex || stageIndex === stages.length ? "done" : index === stageIndex && running ? "running" : "pending"; return <button key={item.module} className={`${state} ${visibleDebugStep === index ? "selected" : ""}`} onClick={() => { setAutoFollow(false); setDebugStep(index); }}><i>{state === "done" ? "✓" : String(index+1).padStart(2,"0")}</i><span><b>{stages[index][0]}</b><small>{item.module}</small></span><em>{state}</em></button>; })}</aside><main className="debug-detail"><div className="debug-panel-title"><span>STEP {visibleDebugStep + 1} INSPECTOR</span><b>{debugDetail.module}</b></div><h3>{stages[visibleDebugStep][0]}</h3><p>{stages[visibleDebugStep][1]}</p><div className="debug-io"><article><span>INPUT</span><p>{visibleDebugStep === 0 ? `${cellLine} · ${assay} · ${selectedCandidates.length} candidates · ${replicates} replicates` : debugDetail.input}</p></article><i>→</i><article><span>TRANSFORMATION</span><p>{debugDetail.operation}</p></article><i>→</i><article><span>EXPECTED OUTPUT</span><p>{debugDetail.output}</p></article></div><div className="debug-code"><div><span>CALCULATION / LOGIC</span><b>Read-only</b></div><pre>{debugDetail.code}</pre></div><div className="debug-verification"><div><span>VERIFICATION RULE</span><b>{debugDetail.check}</b></div><em className={visibleDebugStep < stageIndex || stageIndex === stages.length ? "pass" : visibleDebugStep === stageIndex && running ? "running" : "waiting"}>{visibleDebugStep < stageIndex || stageIndex === stages.length ? "✓ VERIFIED" : visibleDebugStep === stageIndex && running ? "● EVALUATING" : "○ WAITING"}</em></div></main><aside className="debug-context"><div className="debug-panel-title"><span>RUN CONTEXT</span><b>Immutable inputs</b></div><dl><div><dt>Biological model</dt><dd>{cellLine}</dd></div><div><dt>Endpoint</dt><dd>{assay}</dd></div><div><dt>Dose series</dt><dd>0.01–30 µM · 8 points</dd></div><div><dt>Replicates</dt><dd>{replicates}</dd></div><div><dt>Exposure</dt><dd>{duration} hours</dd></div><div><dt>Scenario</dt><dd>{mode}</dd></div><div><dt>Expected rows</dt><dd>{selectedCandidates.length * 8 * replicates}</dd></div><div><dt>Seed policy</dt><dd>Deterministic</dd></div></dl><div className="debug-boundary"><b>Evidence boundary</b><span>Displayed values verify software behavior only. They are not measured biology.</span></div></aside></div><article className="debug-console"><div className="debug-panel-title"><span>STRUCTURED EXECUTION LOG</span><b>{logs.length} events · newest last</b></div><div className="debug-log-head"><span>TIME</span><span>LEVEL</span><span>MODULE</span><span>MESSAGE</span><span>STATUS</span></div>{logs.length ? logs.map((log,index) => <div className="debug-log-row" key={`${log}-${index}`}><time>{log.split("  ")[0]}</time><em>{index === 7 && mode !== "nominal" ? "WARN" : "INFO"}</em><code>{debugStages[Math.min(index,debugStages.length-1)].module}</code><span>{log.split("  ").slice(1).join("  ")}</span><b>{index < stageIndex || stageIndex === stages.length ? "DONE" : index === stageIndex && running ? "RUNNING" : "QUEUED"}</b></div>) : <div className="debug-empty">No execution events yet. Start a debugger run to watch each stage appear here.</div>}</article></div>}

    {tab === "results" && current && <><div className={`result-hero ${current.status}`}><div><span>EXPERIMENT RESULT · {current.id}</span><h2>{current.title}</h2><p>{current.cellLine} · {current.assayType} · {current.compoundIds.length} candidates</p></div><div className="result-state"><i>{current.status === "completed" ? "✓" : current.status === "warning" ? "!" : "×"}</i><span><b>{current.status === "completed" ? "QC PASSED" : current.status === "warning" ? "QC WARNING" : "QC FAILED"}</b><small>{current.status === "failed" ? "Publication blocked" : "Result package generated"}</small></span></div></div><div className="module-stats"><div className="module-stat"><span>OBSERVATIONS</span><strong>{current.observationCount}</strong><small>Synthetic, labelled rows</small></div><div className="module-stat"><span>CANDIDATES</span><strong>{current.compoundIds.length}</strong><small>Compared side by side</small></div><div className="module-stat"><span>QC CHECKS</span><strong>{current.payload.qcChecks.filter((check) => check.status === "pass").length}/{current.payload.qcChecks.length}</strong><small>Automated acceptance rules</small></div><div className="module-stat"><span>TRAINING ROWS</span><strong>0</strong><small>Governance gate enforced</small></div></div><div className="module-grid result-grid"><article className="module-card curve-card"><div className="card-title"><div><span>DOSE RESPONSE</span><h2>Candidate comparison</h2></div><b>Four-parameter logistic concept</b></div>{current.status === "failed" ? <div className="blocked-result"><b>Curve publication blocked</b><span>Positive-control and completeness checks failed. Inspect QC before repeating the run.</span></div> : <CurveChart records={resultSeries}/>}</article><article className="module-card"><h2>Estimated response summary</h2><div className="comparison-list">{resultSeries.map((item,index) => <div key={item.name}><i style={{background:item.color}}/><span><b>{item.name}</b><small>Candidate {index + 1}</small></span><strong>{item.ic50.toFixed(2)}<small>µM IC50</small></strong></div>)}</div><div className="formula-note"><code>y = bottom + (top − bottom) / (1 + (dose / IC50)^hill)</code><p>Values are deterministic software outputs for workflow verification—not measured potency.</p></div></article></div><section className={`ai-decision ${current.status}`}><div className="ai-decision-head"><div><span>OSIEL NEXT-EXPERIMENT ENGINE</span><h2>{current.status === "failed" ? "Failure diagnosis and replacement recommendation" : "Success report and next-priority recommendation"}</h2></div><b>{current.status === "failed" ? "RETEST REQUIRED" : "CONTINUE SCREEN"}</b></div><div className="decision-summary"><strong>{current.payload.reportConclusion ?? (current.status === "failed" ? "This run is invalid and must be repeated before interpreting compound response." : "The simulation passed QC and is ready for scientific review.")}</strong>{visibleFailureReasons.length > 0 && <ul>{visibleFailureReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}</div><div className="recommendation-grid">{visibleRecommendations.map((recommendation,index) => <article key={recommendation.compoundId} className={index === 0 ? "top" : ""}><div><i>{index + 1}</i><span><b>{recommendation.name}</b><small>{recommendation.compoundId}</small></span><strong>{recommendation.priority}<small>priority</small></strong></div><p>{recommendation.reason}</p><em>{recommendation.action}</em>{index === 0 && <button onClick={() => applyRecommendation(recommendation)}>Use this compound for next test →</button>}</article>)}</div><p className="ai-boundary">Recommendation is a transparent software prioritization based on the reference score, confidence, selectivity, ADMET flags and model-domain status. It is not proof of efficacy.</p></section><article className="module-card result-details"><div className="card-title"><div><span>OUTPUT PACKAGE</span><h2>Plate, observations and downloadable records</h2></div><div className="export-actions"><button onClick={() => download(`${current.id}.csv`,"text/csv",csv)}>Download CSV</button><button onClick={() => download(`${current.id}.json`,"application/json",JSON.stringify(current,null,2))}>Download JSON</button><button onClick={() => window.print()}>Print / save PDF</button></div></div><details open><summary>96-well plate map</summary><PlateMap names={resultSeries.map((item) => item.name)}/></details><details><summary>Observation preview — {observationRows.length} summarized rows</summary><div className="module-table"><table><thead><tr><th>Candidate</th><th>Dose (µM)</th><th>Replicates</th><th>Mean viability</th><th>CV</th><th>Class</th></tr></thead><tbody>{observationRows.map((row) => <tr key={`${row.compound}-${row.dose}`}><td><b>{row.compound}</b></td><td>{row.dose}</td><td>3</td><td>{row.viability}%</td><td>{row.cv}%</td><td><span className="status-chip simulated">Simulated</span></td></tr>)}</tbody></table></div></details></article></>}

    {tab === "history" && <div className="module-grid history-grid"><article className="module-card"><div className="card-title"><div><span>DURABLE RECORDS</span><h2>Experiment history</h2></div><b>{history.length} runs</b></div><div className="history-list">{history.map((item) => <button key={item.id} className={item.id === currentId ? "active" : ""} onClick={() => setCurrentId(item.id)}><i className={item.status}>{item.status === "completed" ? "✓" : item.status === "warning" ? "!" : "×"}</i><span><b>{item.title}</b><small>{item.id} · {new Date(item.createdAt).toLocaleString()}</small></span><em>{item.reviewStatus}</em></button>)}</div></article>{current && <article className="module-card history-detail"><span>SELECTED RUN</span><h2>{current.title}</h2><dl className="spec-list"><div><dt>Experiment ID</dt><dd>{current.id}</dd></div><div><dt>Status</dt><dd>{current.status}</dd></div><div><dt>Review</dt><dd>{current.reviewStatus}</dd></div><div><dt>Model</dt><dd>{current.cellLine}</dd></div><div><dt>Assay</dt><dd>{current.assayType}</dd></div><div><dt>Observations</dt><dd>{current.observationCount}</dd></div><div><dt>Operator</dt><dd>{current.actorEmail}</dd></div></dl><button className="primary wide" onClick={() => setTab("results")}>Open complete result</button></article>}</div>}

    {tab === "review" && current && <div className="module-grid review-grid"><article className="module-card"><div className="card-title"><div><span>QUALITY CONTROL</span><h2>Automated acceptance checks</h2></div><b>{current.id}</b></div><ul className="qc-checks">{current.payload.qcChecks.map((check) => <li key={check.label} className={check.status}><i>{check.status === "pass" ? "✓" : check.status === "warn" ? "!" : "×"}</i><span><b>{check.label}</b><small>{check.detail}</small></span><em>{check.status}</em></li>)}</ul></article><article className="module-card review-panel"><span>SEPARATION OF DUTIES</span><h2>Scientific review decision</h2><label className="lab-field"><span>Review role</span><select value={role} onChange={(event) => setRole(event.target.value as typeof role)}><option value="researcher">Researcher — cannot approve own run</option><option value="reviewer">Scientific reviewer</option><option value="admin">Workspace administrator</option></select></label><div className={`review-seal ${current.reviewStatus}`}>{current.reviewStatus.toUpperCase()}</div><p>{role === "researcher" ? "Approval controls are locked for the researcher role. Choose the reviewer role to demonstrate separation of duties." : "The reviewer may approve the research record or reject it with an auditable status change."}</p><div className="review-actions"><button onClick={() => review("rejected")} disabled={role === "researcher"}>Reject result</button><button className="primary" onClick={() => review("approved")} disabled={role === "researcher" || current.status === "failed"}>Approve record</button></div><div className="governance-lock"><b>Model-training gate remains locked</b><span>Approval publishes the record only. Simulated observations never become training data.</span></div></article></div>}

    {tab === "integrations" && <><div className="module-grid integration-grid">{[
      ["Plate reader", "Luminescence / absorbance", "Adapter ready", "Connect an authenticated instrument endpoint to replace simulated observations."],
      ["LIMS", "Experiment and sample records", "API contract ready", "Map study, plate, sample and result identifiers to the laboratory system."],
      ["Scientific sources", "PubMed · PubChem · ChEMBL", "Curated registry active", "Metadata and lawful source links remain separate from experimental measurements."],
      ["Model registry", "Champion / challenger", "Governance active", "Only approved immutable datasets can initiate an offline training evaluation."],
    ].map(([name,type,status,description]) => <article className="module-card integration-card" key={name}><div className="integration-icon">{name.slice(0,2).toUpperCase()}</div><span>{status}</span><h2>{name}</h2><b>{type}</b><p>{description}</p><button disabled>{name === "Scientific sources" ? "View source registry" : "Credentials required"}</button></article>)}</div><article className="module-card import-card advanced"><div><span>INSTRUMENT HANDOFF</span><h2>Validate a plate-reader CSV</h2><p>Validation happens locally in your browser; the file is not persisted. A valid schema is quarantined for QC and scientific review—it does not create potency claims or training data.</p><div className="schema-columns">{requiredImportColumns.map((column) => <code key={column}>{column}</code>)}</div></div><label className="file-button">Choose CSV<input type="file" accept=".csv,text/csv" onChange={async (event) => { const file = event.target.files?.[0]; if (!file) return; const lines = (await file.text()).split(/\r?\n/).filter(Boolean); const headers = (lines[0] ?? "").split(",").map((value) => value.trim().toLowerCase()); const mapped = requiredImportColumns.filter((column) => headers.includes(column)); setImportReport({name:file.name,rows:Math.max(0,lines.length-1),mapped,missing:requiredImportColumns.filter((column) => !headers.includes(column))}); }}/></label>{importReport ? <div className={`import-report ${importReport.missing.length ? "invalid" : "valid"}`}><b>{importReport.missing.length ? "SCHEMA BLOCKED" : "SCHEMA VALID · QUARANTINED FOR QC"}</b><span>{importReport.name} · {importReport.rows} rows · {importReport.mapped.length}/7 fields mapped</span>{importReport.missing.length > 0 && <small>Missing: {importReport.missing.join(", ")}</small>}<button disabled={importReport.missing.length > 0}>Continue to scientific QC</button></div> : <strong>No instrument file loaded</strong>}</article></>}

    {tab === "structure" && current && <div className="structure-result-shell">
      <section className="structure-result-head"><div><span>RESULT-LINKED MOLECULAR INSPECTION</span><h2>Interactive compound geometry</h2><p>Select any compound from {current.id}, then rotate, zoom, recolour and change its representation.</p></div><div><button onClick={() => setTab("results")}>← Result report</button><button onClick={() => setTab("review")}>Open QC review →</button></div></section>
      <div className="structure-candidate-tabs">{current.compoundIds.map((id,index) => { const item = candidates.find((candidate) => candidate.compound_id === id); return <button key={id} className={activeStructureId === id ? "active" : ""} onClick={() => setStructureCompoundId(id)}><i>{index + 1}</i><span><b>{item?.display_name ?? id}</b><small>{item?.formula ?? "Registered compound"}</small></span></button>; })}</div>
      {activeStructureCandidate ? <Compound3DViewer key={`${current.id}:${activeStructureCandidate.compound_id}`} candidate={activeStructureCandidate} experimentId={current.id} resultStatus={current.status}/> : <article className="molecule-viewer unavailable"><b>Registered structure not resolved</b><span>This historic result ID is not present in the currently loaded candidate registry. Connect the Python API or open a newer run; no molecular geometry was guessed.</span></article>}
    </div>}
  </div>;
}
