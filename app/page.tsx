"use client";

import { useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { demoCandidates } from "./lib/demo-data";
import type { RankedCandidate } from "./lib/demo-data";
import { loadRankedWorkspace, runDryExperiment } from "./lib/osiel-client";
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [origin, setOrigin] = useState<"all" | "natural" | "synthetic">("all");
  const [cancerType, setCancerType] = useState("Non-small cell lung cancer");
  const [cellLine, setCellLine] = useState("A549");
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState<"score" | "activity" | "confidence">("score");
  const [candidates, setCandidates] = useState<RankedCandidate[]>(demoCandidates);
  const [focusId, setFocusId] = useState(demoCandidates[0].compound_id);
  const [selected, setSelected] = useState<Set<string>>(new Set(demoCandidates.slice(0, 3).map((item) => item.compound_id)));
  const [rankingRunId, setRankingRunId] = useState("RNK-EMBEDDED-DEMO");
  const [engineState, setEngineState] = useState<"ready" | "running" | "complete">("ready");
  const [backendConnected, setBackendConnected] = useState(false);
  const [engineMessage, setEngineMessage] = useState("Embedded deterministic reference workspace ready.");
  const [detailTab, setDetailTab] = useState<"overview" | "evidence" | "admet">("overview");
  const [experiment, setExperiment] = useState<DryRunResult | null>(null);
  const [experimentStage, setExperimentStage] = useState(-1);

  const visible = useMemo(() => {
    const filtered = candidates.filter((candidate) => {
      const matchesOrigin = origin === "all" || candidate.origin === origin;
      const matchesSearch = `${candidate.display_name} ${candidate.formula} ${candidate.compound_id}`.toLowerCase().includes(query.toLowerCase());
      return matchesOrigin && matchesSearch;
    });
    return [...filtered].sort((a, b) => b[sortBy] - a[sortBy]).map((candidate, index) => ({ ...candidate, rank: index + 1 }));
  }, [candidates, origin, query, sortBy]);

  const focused = candidates.find((item) => item.compound_id === focusId) ?? visible[0] ?? demoCandidates[0];

  async function runEngine() {
    setEngineState("running");
    setExperiment(null);
    const result = await loadRankedWorkspace(cancerType, cellLine, origin);
    setCandidates(result.candidates);
    setRankingRunId(result.rankingRunId);
    setBackendConnected(result.backendConnected);
    setEngineMessage(result.message);
    setSelected(new Set(result.candidates.slice(0, 3).map((item) => item.compound_id)));
    setFocusId(result.candidates[0]?.compound_id ?? focusId);
    setEngineState("complete");
  }

  async function startExperiment() {
    if (selected.size === 0) return null;
    setExperiment(null);
    setExperimentStage(0);
    const interval = window.setInterval(() => setExperimentStage((stage) => Math.min(stage + 1, 3)), 460);
    const result = await runDryExperiment([...selected], cancerType, cellLine, rankingRunId);
    window.clearInterval(interval);
    setExperimentStage(4);
    setExperiment(result);
    setBackendConnected(result.backendConnected || backendConnected);
    return result;
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
        <div className="workspace-card"><span>RESEARCH WORKSPACE</span><button><div className="avatar">DR</div><div><b>Discovery Lab</b><small>Phase 1 · RUO</small></div><Icon name="chevron" size={14}/></button></div>
        <nav className="side-nav">
          {navGroups.map((group) => <div className="nav-group" key={group.label}><p>{group.label}</p>{group.items.map(([icon, label]) => <button key={label} className={activeNav === label ? "active" : ""} onClick={() => { setActiveNav(label); setSidebarOpen(false); }}><Icon name={icon as IconName}/><span>{label}</span>{label === "Experiments" && <i>3</i>}</button>)}</div>)}
        </nav>
        <div className="sidebar-foot"><div className="model-status"><span className="pulse"/><div><b>Champion online</b><small>osiel-demo-activity@0.1</small></div></div><button onClick={() => setActiveNav("Settings")}><Icon name="settings"/><span>Workspace settings</span></button><p>Research use only · v0.1.0</p></div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Toggle navigation"><Icon name="menu"/></button>
          <div className="breadcrumb"><span>OSIEL</span><Icon name="chevron" size={13}/><b>{activeNav}</b></div>
          <label className="global-search"><Icon name="search" size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search compounds, IDs, evidence…"/><kbd>⌘ K</kbd></label>
          <div className="top-actions"><button aria-label="Notifications"><Icon name="bell"/></button><div className={`connection ${backendConnected ? "live" : "demo"}`}><span/>{backendConnected ? "Python API live" : "Embedded demo"}</div><div className="avatar small">DR</div></div>
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
            <div className="heading-actions"><button className="secondary"><Icon name="download"/> Export run</button><button className="primary" onClick={runEngine} disabled={engineState === "running"}><Icon name={engineState === "running" ? "activity" : "play"}/>{engineState === "running" ? "Running OSIEL…" : "Run OSIEL engine"}</button></div>
          </section>

          <section className="notice-bar"><Icon name="shield"/><div><b>Research-use system.</b> Rankings are in-silico prioritization hypotheses—not clinical guidance or measured efficacy.</div><button>View claim boundaries</button></section>

          <section className="context-card">
            <div className="context-title"><div className="section-icon"><Icon name="activity"/></div><div><span>SCIENTIFIC CONTEXT</span><h2>Define the governed prediction task</h2></div></div>
            <div className="context-grid">
              <label><span>Cancer context</span><select value={cancerType} onChange={(event) => setCancerType(event.target.value)}><option>Non-small cell lung cancer</option><option>Triple-negative breast cancer</option><option>Colorectal adenocarcinoma</option><option>Pancreatic ductal adenocarcinoma</option></select></label>
              <label><span>Cell line</span><select value={cellLine} onChange={(event) => setCellLine(event.target.value)}><option>A549</option><option>H1975</option><option>HCC827</option><option>MDA-MB-231</option></select></label>
              <label><span>Endpoint</span><select defaultValue="activity_probability"><option value="activity_probability">Activity probability</option><option value="IC50">IC50 (separate task)</option><option value="GI50">GI50 (separate task)</option></select></label>
              <div className="segmented-field"><span>Candidate origin</span><div>{(["all", "natural", "synthetic"] as const).map((value) => <button key={value} className={origin === value ? "active" : ""} onClick={() => setOrigin(value)}>{value === "all" ? "All" : value[0].toUpperCase() + value.slice(1)}</button>)}</div></div>
            </div>
            <div className="context-meta"><span><i className="dot green"/> Task <b>OSIEL-ACTIVITY-NSCLC-v1</b></span><span>Split: <b>scaffold-safe</b></span><span>Policy: <b>rank-policy@1.0</b></span><span>Updated: <b>deterministic demo</b></span></div>
          </section>

          <section className="metrics-grid">
            <Metric label="FEDERATED CHEMICAL SPACE" value="10.10B" detail="9.43B mapped remotely + 192 local" tone="mint"/>
            <Metric label="CANDIDATES IN VIEW" value={String(visible.length)} detail={`${visible.filter((item) => item.applicability_domain === "inside").length} inside model domain`} tone="cyan"/>
            <Metric label="TOP-5 MEAN SCORE" value={`${topMean}/100`} detail="Transparent 7-component policy" tone="violet"/>
            <Metric label="EXPERIMENT QUEUE" value={String(selected.size)} detail="Selected for computational dry-run" tone="amber"/>
          </section>

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
                    <td><button className="row-arrow" aria-label="Open candidate"><Icon name="chevron" size={16}/></button></td>
                  </tr>)}</tbody>
                </table>
                {visible.length === 0 && <div className="empty-state"><Icon name="search"/><b>No compounds match this view</b><span>Clear the search or change candidate origin.</span></div>}
              </div>
              <div className="table-footer"><span>Showing {visible.length} ranked local candidates · expand through the live 10.10B remote search</span><span><i className="dot purple"/> Selected: <b>{selected.size}</b></span></div>
            </div>

            <aside className="candidate-card card">
              <div className="candidate-hero"><div><Badge tone={focused.origin === "natural" ? "mint" : "blue"}>{focused.origin}</Badge><MoleculeSketch accent/></div><div className="candidate-score-ring" style={{ "--score": `${focused.score * 3.6}deg` } as CSSProperties}><div><b>{focused.score.toFixed(0)}</b><span>OSIEL</span></div></div></div>
              <div className="candidate-name"><span>{focused.compound_id}</span><h2>{focused.display_name}</h2><p>{focused.formula}</p></div>
              <div className="detail-tabs">{(["overview", "evidence", "admet"] as const).map((tab) => <button key={tab} className={detailTab === tab ? "active" : ""} onClick={() => setDetailTab(tab)}>{tab[0].toUpperCase() + tab.slice(1)}</button>)}</div>
              {detailTab === "overview" && <div className="detail-panel"><div className="prediction-callout"><span>Predicted IC50</span><strong>{focused.predicted_ic50_um.toFixed(2)} <small>µM</small></strong><Badge tone={focused.confidence >= 75 ? "mint" : "amber"}>{focused.confidence}% confidence</Badge></div><ScoreBar label="Predicted activity" value={focused.activity}/><ScoreBar label="Selectivity" value={focused.selectivity} tone="cyan"/><ScoreBar label="Model confidence" value={focused.confidence} tone="mint"/><div className="detail-note"><Icon name="robot"/><p>{focused.note}</p></div></div>}
              {detailTab === "evidence" && <div className="detail-panel"><div className="evidence-grade"><b>{focused.evidence_grade}</b><div><span>Evidence grade</span><strong>{focused.evidence_grade === "A" ? "Curated reference" : focused.evidence_grade === "B" ? "Verified identity" : "Limited context"}</strong></div></div><dl className="evidence-list"><div><dt>Source</dt><dd>{focused.source}</dd></div><div><dt>Model domain</dt><dd>{focused.applicability_domain}</dd></div><div><dt>Uncertainty</dt><dd>{focused.uncertainty}%</dd></div><div><dt>Claim type</dt><dd>In-silico hypothesis</dd></div></dl><button className="wide-secondary"><Icon name="book"/> Inspect lineage record</button></div>}
              {detailTab === "admet" && <div className="detail-panel admet-list">{focused.admet.map((endpoint) => <div key={endpoint.code}><div className={`admet-symbol ${endpoint.className}`}>{endpoint.label[0]}</div><div><span>{endpoint.label}</span><b>{endpoint.value}/100</b></div><Badge tone={endpoint.className === "good" ? "mint" : endpoint.className === "risk" ? "red" : "amber"}>{endpoint.className}</Badge></div>)}<p>Rule-based demo endpoints are separate estimates. Production adapters target ADMET-AI or validated endpoint models.</p></div>}
            </aside>
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
              <div className="model-row champion"><div className="model-badge"><Icon name="check"/></div><div><span>CHAMPION</span><b>osiel-demo-activity@0.1</b><small>Approved reference · 2026-08-19</small></div><Badge tone="mint">Online</Badge></div>
              <div className="model-divider"><span>Evaluation boundary</span></div>
              <div className="model-row"><div className="model-badge challenger"><Icon name="activity"/></div><div><span>CHALLENGER</span><b>Awaiting approved dataset</b><small>Training never starts from a UI upload</small></div><Badge>Locked</Badge></div>
              <ul className="gate-list"><li><Icon name="check"/> Scientific result approval required</li><li><Icon name="check"/> Immutable snapshot and leakage audit</li><li><Icon name="check"/> Independent evaluation and named reviewer</li></ul>
            </article>
          </section>

          <footer className="page-footer"><div><strong>OSIEL</strong> · Oncogon Scientific Intelligence & Experimental Learning Engine</div><div>Developer reference v0.1.0 <span/> Research use only</div></footer>
          </>}
        </div>
      </main>
      {sidebarOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}/>} 
    </div>
  );
}
