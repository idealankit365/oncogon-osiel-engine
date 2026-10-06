"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import type { RankedCandidate } from "./lib/ranked-candidate";
import { checkBackend, getBackendJson, listRankingRuns, loadRankingRun, loadRankedWorkspace, rankingExportUrl, runDryExperiment } from "./lib/osiel-client";
import type { DryRunResult } from "./lib/osiel-client";
import { ModuleWorkspace } from "./components/module-workspaces";

type IconName =
  | "grid" | "flask" | "database" | "molecule" | "chart" | "robot"
  | "shield" | "book" | "settings" | "search" | "bell" | "play"
  | "check" | "chevron" | "download" | "plus" | "activity" | "menu";

const iconPaths: Record<IconName, ReactNode> = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
  flask: <><path d="M9 3h6M10 3v6l-5.7 9.3A1.8 1.8 0 0 0 5.8 21h12.4a1.8 1.8 0 0 0 1.5-2.7L14 9V3"/><path d="M7.2 15h9.6"/></>,
  database: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></>,
  molecule: <><circle cx="6" cy="12" r="2.4"/><circle cx="17.5" cy="6" r="2.4"/><circle cx="18" cy="18" r="2.4"/><path d="m8.2 10.8 7.1-3.7M8.3 13.2l7.4 3.6M17.7 8.4l.2 7.2"/></>,
  chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></>,
  robot: <><rect x="4" y="7" width="16" height="13" rx="3"/><path d="M12 3v4M8 12h.01M16 12h.01M8 16h8"/></>,
  shield: <><path d="M12 3 4.5 6v5.2c0 4.7 3.1 8.1 7.5 9.8 4.4-1.7 7.5-5.1 7.5-9.8V6L12 3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></>,
  book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5v-16ZM20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5v-16Z"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1-2.9 2.9-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21h-4v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1-2.9-2.9.1-.1a1.6 1.6 0 0 0 .3-1.8A1.6 1.6 0 0 0 3.1 14H3v-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1 2.9-2.9.1.1A1.6 1.6 0 0 0 9 4.6a1.6 1.6 0 0 0 1-1.5V3h4v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1 2.9 2.9-.1.1a1.6 1.6 0 0 0-.3 1.8 1.6 1.6 0 0 0 1.5 1h.1v4h-.1a1.6 1.6 0 0 0-1.5 1Z"/></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
  play: <path d="m8 5 11 7-11 7V5Z"/>,
  check: <path d="m5 12 4 4L19 6"/>,
  chevron: <path d="m9 18 6-6-6-6"/>,
  download: <><path d="M12 3v12m-5-5 5 5 5-5M4 21h16"/></>,
  plus: <path d="M12 5v14M5 12h14"/>,
  activity: <path d="M3 12h4l2.2-6 4 12 2.2-6H21"/>,
  menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
};

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths[name]}</svg>;
}

const navGroups = [
  { label: "DISCOVER", items: [["grid", "Research cockpit"], ["activity", "Open discovery"], ["molecule", "Compound registry"], ["database", "Evidence sources"]] },
  { label: "ANALYZE", items: [["activity", "Prediction studio"], ["molecule", "Model laboratory"], ["chart", "Ranking policies"], ["robot", "Multimodal engine"], ["book", "Scientific copilot"]] },
  { label: "VALIDATE", items: [["flask", "Experiments"], ["shield", "Model governance"], ["book", "Audit & lineage"]] },
  { label: "SYSTEM", items: [["settings", "Production center"], ["shield", "Recursion gap map"]] },
] as const;
const navLabels = [...navGroups.flatMap((group) => group.items.map(([, label]) => label)), "Workspace settings"];
const navSlug = (label: string) => label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

const workflow = [
  ["01", "Identity", "Standardize & deduplicate"],
  ["02", "Context", "Cancer task registry"],
  ["03", "Predict", "Activity + uncertainty"],
  ["04", "Screen", "Endpoint-level ADMET"],
  ["05", "Prioritize", "Policy + Pareto fronts"],
  ["06", "Experiment", "Protocol dry-run"],
  ["07", "Govern", "QC + approval gate"],
];

function MoleculeSketch({ accent = false }: { accent?: boolean }) {
  return (
    <svg className={`molecule-sketch ${accent ? "accent" : ""}`} viewBox="0 0 96 54" aria-label="Stylized molecular structure">
      <g fill="none" stroke="currentColor" strokeWidth="1.5"><path d="m16 27 11-18h21l11 18-11 18H27Z"/><path d="m59 27 10-17h17M59 27l10 17h17"/><path d="M31 14h14M22 28l8 13M48 41l8-13"/></g>
      <circle cx="87" cy="10" r="3" fill="currentColor"/><circle cx="87" cy="44" r="3" fill="currentColor"/>
    </svg>
  );
}

function Metric({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: string }) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}><Icon name={tone === "mint" ? "database" : tone === "cyan" ? "activity" : tone === "amber" ? "flask" : "shield"}/></div><div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></article>;
}

function ScoreBar({ label, value, tone = "violet" }: { label: string; value: number; tone?: string }) {
  return <div className="score-row"><div><span>{label}</span><b>{value}%</b></div><div className="bar"><i className={tone} style={{ "--bar-value": `${value}%` } as CSSProperties}/></div></div>;
}

function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export default function Home() {
  const [activeNav, setActiveNav] = useState("Research cockpit");
  const [navReady, setNavReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [origin, setOrigin] = useState<"all" | "natural" | "synthetic">("all");
  const [cancerType, setCancerType] = useState("Non-small cell lung cancer");
  const [cellLine, setCellLine] = useState("A549");
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState<"score" | "activity" | "confidence">("score");
  const [candidates, setCandidates] = useState<RankedCandidate[]>([]);
  const [focusId, setFocusId] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [rankingRunId, setRankingRunId] = useState("");
  const [runHistory, setRunHistory] = useState<Array<{ ranking_run_id: string; cancer_type: string; cell_line: string | null; created_at: string; candidate_count: number }>>([]);
  const [engineState, setEngineState] = useState<"ready" | "running" | "complete">("ready");
  const [engineMessage, setEngineMessage] = useState("Preparing research workspace…");
  const [connectionState, setConnectionState] = useState<"connecting" | "connected" | "unavailable" | "error">("connecting");
  const [models, setModels] = useState<Array<{ name: string; version: string; alias: string; metrics?: { validated?: boolean } }>>([]);
  const [compoundCount, setCompoundCount] = useState<number | null>(null);
  const [detailTab, setDetailTab] = useState<"overview" | "evidence" | "admet">("overview");
  const [experiment, setExperiment] = useState<DryRunResult | null>(null);
  const [experimentStage, setExperimentStage] = useState(-1);

  useEffect(() => {
    const readLocation = () => {
      const label = navLabels.find((item) => navSlug(item) === window.location.hash.slice(1));
      if (label) setActiveNav(label);
    };
    const timer = window.setTimeout(() => { readLocation(); setNavReady(true); }, 0);
    window.addEventListener("hashchange", readLocation);
    return () => { window.clearTimeout(timer); window.removeEventListener("hashchange", readLocation); };
  }, []);
  useEffect(() => {
    if (!navReady) return;
    const hash = `#${navSlug(activeNav)}`;
    if (window.location.hash !== hash) window.history.replaceState(null, "", hash);
  }, [activeNav, navReady]);

  const visible = useMemo(() => {
    const filtered = candidates.filter((candidate) => {
      const matchesOrigin = origin === "all" || candidate.origin === origin;
      const matchesSearch = `${candidate.display_name} ${candidate.formula} ${candidate.compound_id}`.toLowerCase().includes(query.toLowerCase());
      return matchesOrigin && matchesSearch;
    });
    return [...filtered].sort((a, b) => b[sortBy] - a[sortBy]).map((candidate, index) => ({ ...candidate, rank: index + 1 }));
  }, [candidates, origin, query, sortBy]);

  const focused = candidates.find((item) => item.compound_id === focusId) ?? visible[0];

  async function runEngine(runId?: string) {
    setEngineState("running");
    setExperiment(null);
    setCandidates([]);
    setRankingRunId("");
    try {
      await checkBackend();
      const history = await listRankingRuns();
      const selectedRun = runId === "new" ? null : (runId ?? history.find((item) => item.model_version === "osiel-research-sim@1.0")?.ranking_run_id ?? null);
      const [result, health, runtimeModels] = await Promise.all([
        selectedRun ? loadRankingRun(selectedRun) : loadRankedWorkspace(cancerType, cellLine, origin),
        getBackendJson<{ compound_count: number }>("/health"),
        getBackendJson<typeof models>("/v1/models"),
      ]);
      setRunHistory((selectedRun ? history : await listRankingRuns()).filter((item) => item.model_version === "osiel-research-sim@1.0"));
      if (selectedRun) {
        const previous = history.find((item) => item.ranking_run_id === selectedRun);
        if (previous) { setCancerType(previous.cancer_type); setCellLine(previous.cell_line || "A549"); }
      }
      setCandidates(result.candidates);
      setRankingRunId(result.rankingRunId);
      setConnectionState("connected");
      setCompoundCount(health.compound_count);
      setModels(runtimeModels);
      setEngineMessage(result.message);
      setSelected(new Set(result.candidates.slice(0, 3).map((item) => item.compound_id)));
      setFocusId(result.candidates[0]?.compound_id ?? "");
      setEngineState("complete");
    } catch (error) {
      setCandidates([]);
      setSelected(new Set());
      setFocusId("");
      setRankingRunId("");
      setCompoundCount(null);
      setModels([]);
      setConnectionState("unavailable");
      console.error("Research engine request failed", error);
      setEngineMessage("Research workspace is temporarily unavailable. Retry when service is restored.");
      setEngineState("ready");
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { void runEngine(); }, 0);
    return () => window.clearTimeout(timer);
    // Initial context is loaded once; subsequent context changes require an explicit run.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function startExperiment() {
    if (selected.size === 0) return null;
    setExperiment(null);
    setExperimentStage(0);
    try {
      const result = await runDryExperiment([...selected], cancerType, cellLine, rankingRunId);
      setExperimentStage(4);
      setExperiment(result);
      return result;
    } catch (error) {
      setExperimentStage(-1);
      setExperiment(null);
      setEngineMessage(error instanceof Error ? error.message : "Experiment service unavailable.");
      return null;
    }
  }

  function toggleCandidate(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  const topMean = visible.length ? Math.round(visible.slice(0, 5).reduce((total, item) => total + item.score, 0) / Math.min(5, visible.length)) : 0;

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="brand"><div className="brand-mark"><span>O</span></div><div><strong>ONCOGON <em>AI</em></strong><small>OSIEL RESEARCH ENGINE</small></div></div>
        <div className="workspace-card"><span>RESEARCH WORKSPACE</span><div className="workspace-identity"><div className="avatar">OS</div><div><b>Research workspace</b><small>Research use only</small></div></div></div>
        <nav className="side-nav">
          {navGroups.map((group) => <div className="nav-group" key={group.label}><p>{group.label}</p>{group.items.map(([icon, label]) => <button key={label} className={activeNav === label ? "active" : ""} onClick={() => { setActiveNav(label); setSidebarOpen(false); }}><Icon name={icon as IconName}/><span>{label}</span>{label === "Experiments" && <i>{experiment ? 1 : 0}</i>}</button>)}</div>)}
        </nav>
        <div className="sidebar-foot"><div className="model-status"><span className="pulse"/><div><b>{models.some((model) => model.alias === "champion" && model.metrics?.validated) ? "Validated model available" : "No validated production model"}</b><small>Research use only</small></div></div><button onClick={() => setActiveNav("Settings")}><Icon name="settings"/><span>Workspace settings</span></button><p>Research use only · v0.1.0</p></div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Toggle navigation"><Icon name="menu"/></button>
          <div className="breadcrumb"><span>OSIEL</span><Icon name="chevron" size={13}/><b>{activeNav}</b></div>
          <label className="global-search"><Icon name="search" size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search compounds, IDs, evidence…"/><kbd>⌘ K</kbd></label>
          <div className="top-actions"><div className="avatar small">OS</div></div>
        </header>

        <div className="page-content">
          {activeNav !== "Research cockpit" ? <ModuleWorkspace
            activeNav={activeNav}
            candidates={candidates}
            selectedIds={[...selected]}
            experiment={experiment}
            onRunExperiment={startExperiment}
            onBackToCockpit={() => setActiveNav("Research cockpit")}
          /> : <>
          <section className="page-heading">
            <div><div className="eyebrow"><span>OSIEL / DISCOVERY</span><Badge tone="violet">Computational hypothesis</Badge></div><h1>Compound Prioritization Cockpit</h1><p>Traceable chemical intelligence, uncertainty-aware ranking, and governed experimental learning in one research loop.</p></div>
            <div className="heading-actions">{rankingRunId ? <a className="secondary" role="button" href={rankingExportUrl(rankingRunId)} download={`osiel-ranking-${rankingRunId}.json`} title="Download the current ranking as JSON"><Icon name="download"/> Export run</a> : <button className="secondary" disabled title="Run a ranking before exporting"><Icon name="download"/> Export run</button>}<button className="primary" onClick={() => void runEngine("new")} disabled={engineState === "running"}><Icon name={engineState === "running" ? "activity" : "play"}/>{engineState === "running" ? "Analyzing candidates…" : "Run OSIEL engine"}</button></div>
          </section>

          {connectionState === "unavailable" && <section className="notice-bar"><Icon name="shield"/><div><b>Research workspace is temporarily unavailable.</b> Please retry.</div><button onClick={() => void runEngine()}>Retry</button></section>}
          <section className="notice-bar"><Icon name="shield"/><div><b>Research-use system.</b> Rankings are in-silico prioritization hypotheses—not clinical guidance or measured efficacy.</div><button onClick={() => setActiveNav("Model governance")}>View claim boundaries</button></section>

          <section className="context-card">
            <div className="context-title"><div className="section-icon"><Icon name="activity"/></div><div><span>SCIENTIFIC CONTEXT</span><h2>Define the governed prediction task</h2></div></div>
            <div className="context-grid">
              <label><span>Cancer context</span><select value={cancerType} onChange={(event) => setCancerType(event.target.value)}><option>Non-small cell lung cancer</option><option>Triple-negative breast cancer</option><option>Colorectal adenocarcinoma</option><option>Pancreatic ductal adenocarcinoma</option></select></label>
              <label><span>Cell line</span><select value={cellLine} onChange={(event) => setCellLine(event.target.value)}><option>A549</option><option>H1975</option><option>HCC827</option><option>MDA-MB-231</option></select></label>
              <label><span>Endpoint</span><select value="activity_probability" disabled title="This research model evaluates activity probability; IC50 is reported as a computational estimate."><option value="activity_probability">Activity probability</option></select></label>
              <div className="segmented-field"><span>Candidate origin</span><div>{(["all", "natural", "synthetic"] as const).map((value) => <button key={value} className={origin === value ? "active" : ""} onClick={() => setOrigin(value)}>{value === "all" ? "All" : value[0].toUpperCase() + value.slice(1)}</button>)}</div></div>
            </div>
            <div className="context-meta"><span><i className="dot green"/> Task <b>{cancerType} · {cellLine}</b></span><span>Model domain: <b>reported per candidate</b></span><span>Ranking: <b>{rankingRunId || "not run"}</b></span></div>
          </section>

          <section className="metrics-grid">
            <Metric label="REFERENCE COMPOUNDS" value={compoundCount === null ? "—" : String(compoundCount)} detail="Research registry" tone="mint"/>
            <Metric label="CANDIDATES IN VIEW" value={String(visible.length)} detail={`${visible.filter((item) => item.applicability_domain === "inside").length} inside model domain`} tone="cyan"/>
            <Metric label="TOP-5 MEAN SCORE" value={candidates.length ? `${topMean}/100` : "—"} detail="Computational ranking" tone="violet"/>
            <Metric label="EXPERIMENT QUEUE" value={String(selected.size)} detail="Selected for computational dry-run" tone="amber"/>
          </section>

          {runHistory.length > 0 && <section className="module-card"><div className="section-heading"><div><span>RESEARCH MEMORY</span><h2>Recent analysis runs</h2></div></div><div className="context-meta">{runHistory.slice(0, 5).map((run) => <button className="secondary" key={run.ranking_run_id} disabled={engineState === "running"} onClick={() => void runEngine(run.ranking_run_id)}>{run.ranking_run_id} · {run.cell_line || run.cancer_type} · {run.candidate_count} candidates · {new Date(run.created_at).toLocaleTimeString()}</button>)}</div></section>}
          <section className="workflow-card">
            <div className="section-heading"><div><span>END-TO-END ENGINE</span><h2>Evidence-to-experiment loop</h2></div><div className={`run-state ${engineState}`}><i/>{engineState === "running" ? "Processing" : engineState === "complete" ? "Run complete" : "Ready"}</div></div>
            <div className="workflow">
              {workflow.map(([number, title, detail], index) => <div className={`workflow-step ${engineState === "complete" || (engineState === "running" && index < 5) ? "done" : ""}`} key={number}><div className="step-number">{engineState !== "ready" && index < 5 ? <Icon name="check" size={15}/> : number}</div><div><b>{title}</b><span>{detail}</span></div>{index < workflow.length - 1 && <Icon name="chevron" size={15}/>}</div>)}
            </div>
            <p className="engine-message"><Icon name="activity" size={15}/>{engineMessage}</p>
          </section>

          <section className="workbench-grid">
            <div className="ranking-card card">
              <div className="section-heading"><div><span>CANDIDATE RANKING</span><h2>Prioritized compounds</h2></div><div className="table-tools"><label><Icon name="search" size={15}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter"/></label><select value={sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)}><option value="score">Sort: score</option><option value="activity">Sort: activity</option><option value="confidence">Sort: confidence</option></select></div></div>
              <div className="table-wrap">
                <table><thead><tr><th><span className="check-box muted"/></th><th>#</th><th>Compound</th><th>Origin</th><th>Activity</th><th>Confidence</th><th>OSIEL score</th><th>Domain</th><th/></tr></thead>
                  <tbody>{visible.map((candidate) => <tr key={candidate.compound_id} className={candidate.compound_id === focusId ? "focused" : ""} onClick={() => setFocusId(candidate.compound_id)}>
                    <td><button className={`check-box ${selected.has(candidate.compound_id) ? "checked" : ""}`} onClick={(event) => { event.stopPropagation(); toggleCandidate(candidate.compound_id); }} aria-label={`Select ${candidate.display_name}`}>{selected.has(candidate.compound_id) && <Icon name="check" size={12}/>}</button></td>
                    <td><b className="rank">{candidate.rank}</b></td>
                    <td><div className="compound-cell"><div className="compound-thumb"><MoleculeSketch/></div><div><strong>{candidate.display_name}</strong><span>{candidate.formula} · {candidate.compound_id.replace("OSIEL-", "")}</span></div></div></td>
                    <td><Badge tone={candidate.origin === "natural" ? "mint" : candidate.origin === "synthetic" ? "blue" : "neutral"}>{candidate.origin}</Badge></td>
                    <td><div className="mini-score"><span>{candidate.activity}%</span><i><b style={{ width: `${candidate.activity}%` }}/></i></div></td>
                    <td>{candidate.confidence}% <small className="uncertainty">±{candidate.uncertainty}</small></td>
                    <td><div className="score-pill"><strong>{candidate.score.toFixed(1)}</strong><span>/100</span></div></td>
                    <td><span className={`domain ${candidate.applicability_domain}`}><i/>{candidate.applicability_domain}</span></td>
                    <td><button className="row-arrow" aria-label={`Open ${candidate.display_name}`} onClick={(event) => { event.stopPropagation(); setFocusId(candidate.compound_id); }}><Icon name="chevron" size={16}/></button></td>
                  </tr>)}</tbody>
                </table>
                {visible.length === 0 && <div className="empty-state"><Icon name="search"/><b>{connectionState === "unavailable" ? "Research workspace unavailable" : "No compounds match this view"}</b><span>{connectionState === "unavailable" ? "Please retry when the workspace is available." : "Clear the search or change candidate origin."}</span></div>}
              </div>
              <div className="table-footer"><span>Showing {visible.length} ranked candidates</span><span><i className="dot purple"/> Selected: <b>{selected.size}</b></span></div>
            </div>

            {focused ? <aside className="candidate-card card">
              <div className="candidate-hero"><div><Badge tone={focused.origin === "natural" ? "mint" : "blue"}>{focused.origin}</Badge><MoleculeSketch accent/></div><div className="candidate-score-ring" style={{ "--score": `${focused.score * 3.6}deg` } as CSSProperties}><div><b>{focused.score.toFixed(0)}</b><span>OSIEL</span></div></div></div>
              <div className="candidate-name"><span>{focused.compound_id}</span><h2>{focused.display_name}</h2><p>{focused.formula}</p></div>
              <div className="detail-tabs">{(["overview", "evidence", "admet"] as const).map((tab) => <button key={tab} className={detailTab === tab ? "active" : ""} onClick={() => setDetailTab(tab)}>{tab[0].toUpperCase() + tab.slice(1)}</button>)}</div>
              {detailTab === "overview" && <div className="detail-panel"><div className="prediction-callout"><span>Predicted IC50</span><strong>{focused.predicted_ic50_um.toFixed(2)} <small>µM</small></strong><Badge tone={focused.confidence >= 75 ? "mint" : "amber"}>{focused.confidence}% confidence</Badge></div><ScoreBar label="Predicted activity" value={focused.activity}/><ScoreBar label="Selectivity" value={focused.selectivity} tone="cyan"/><ScoreBar label="Model confidence" value={focused.confidence} tone="mint"/><div className="detail-note"><Icon name="robot"/><p>{focused.note}</p></div></div>}
              {detailTab === "evidence" && <div className="detail-panel"><div className="evidence-grade"><b>{focused.evidence_grade}</b><div><span>Evidence grade</span><strong>{focused.evidence_grade === "A" ? "Curated reference" : focused.evidence_grade === "B" ? "Verified identity" : "Limited context"}</strong></div></div><dl className="evidence-list"><div><dt>Source</dt><dd>{focused.source}</dd></div><div><dt>Model domain</dt><dd>{focused.applicability_domain}</dd></div><div><dt>Uncertainty</dt><dd>{focused.uncertainty}%</dd></div><div><dt>Claim type</dt><dd>In-silico hypothesis</dd></div></dl><button className="wide-secondary" onClick={() => setActiveNav("Audit & lineage")}><Icon name="book"/> Inspect lineage record</button></div>}
              {detailTab === "admet" && <div className="detail-panel admet-list">{focused.admet.map((endpoint) => <div key={endpoint.code}><div className={`admet-symbol ${endpoint.className}`}>{endpoint.label[0]}</div><div><span>{endpoint.label}</span><b>{endpoint.value}/100</b></div><Badge tone={endpoint.className === "good" ? "mint" : endpoint.className === "risk" ? "red" : "amber"}>{endpoint.className}</Badge></div>)}<p>Backend-provided endpoint estimates are separate research hypotheses. Production adapters target ADMET-AI or validated endpoint models.</p></div>}
            </aside> : <aside className="candidate-card card"><div className="empty-state">Select a candidate to inspect its results.</div></aside>}
          </section>

          <section className="lower-grid">
            <article className="experiment-card card">
              <div className="section-heading"><div><span>EXPERIMENT ORCHESTRATOR</span><h2>Computational dose-response dry-run</h2></div><Badge tone="amber">Simulation only</Badge></div>
              <div className="protocol-summary"><div><span>Assay</span><b>CellTiter-Glo</b></div><div><span>Dose range</span><b>0.01–30 µM</b></div><div><span>Replicates</span><b>3 × 8 points</b></div><div><span>Duration</span><b>72 hours</b></div></div>
              <div className="experiment-flow">{["Plan protocol", "Generate plate map", "Simulate response", "Run QC", "Lock result"].map((stage, index) => <div key={stage} className={experimentStage >= index ? "done" : experimentStage === index - 1 ? "next" : ""}><i>{experimentStage > index ? <Icon name="check" size={13}/> : index + 1}</i><span>{stage}</span></div>)}</div>
              {experiment ? <div className="result-banner"><div className="result-icon"><Icon name="check"/></div><div><b>Dry-run {experiment.qcStatus}</b><span>{experiment.observationCount} synthetic observations · {experiment.resultId}</span></div><Badge tone="mint">No model mutation</Badge></div> : <div className="experiment-empty"><Icon name="flask"/><div><b>{selected.size} compounds queued</b><span>Creates an auditable software-flow test; it does not perform a physical experiment.</span></div></div>}
              <div className="experiment-actions"><button className="primary wide" onClick={startExperiment} disabled={selected.size === 0 || (experimentStage >= 0 && experimentStage < 4)}><Icon name="play"/>{experimentStage >= 0 && experimentStage < 4 ? "Running governed dry-run…" : "Run computational experiment"}</button><button className="secondary wide" onClick={() => setActiveNav("Experiments")}>Open full laboratory output</button></div>
            </article>

            <article className="governance-card card">
              <div className="section-heading"><div><span>MODEL GOVERNANCE</span><h2>Champion / challenger gate</h2></div><Icon name="shield"/></div>
              <div className="model-row champion"><div className="model-badge"><Icon name="check"/></div><div><span>RESEARCH MODEL</span><b>{models.find((model) => model.alias === "research")?.name ?? "No research model configured"}</b><small>Computational simulation · independent validation required</small></div><Badge tone="amber">Research only</Badge></div>
              <div className="model-divider"><span>Evaluation boundary</span></div>
              <div className="model-row"><div className="model-badge challenger"><Icon name="activity"/></div><div><span>CHALLENGER</span><b>Awaiting approved dataset</b><small>Training never starts from a UI upload</small></div><Badge>Locked</Badge></div>
              <ul className="gate-list"><li><Icon name="check"/> Scientific result approval required</li><li><Icon name="check"/> Immutable snapshot and leakage audit</li><li><Icon name="check"/> Independent evaluation and named reviewer</li></ul>
            </article>
          </section>

          <footer className="page-footer"><div><strong>OSIEL</strong> · Oncogon Scientific Intelligence & Experimental Learning Engine</div><div>Research showcase v0.1.0 <span/> Research use only</div></footer>
          </>}
        </div>
      </main>
      {sidebarOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}/>} 
    </div>
  );
}
