"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getBackendJson,
  runOpenDiscovery,
  type OpenCandidate,
  type OpenDiscoveryInput,
  type OpenDiscoveryResult,
} from "../lib/osiel-client";
import { VinaRunner } from "./vina-runner";
import { Zinc22Search } from "./zinc22-search";

const defaultInput: OpenDiscoveryInput = {
  disease: "Non-small cell lung cancer",
  target_symbol: "EGFR",
  seed_compound_name: "Gefitinib",
  seed_smiles: null,
  pdb_id: null,
  uniprot_accession: null,
  candidate_limit: 8,
  public_connectors: false,
};

const sourceMap = [
  ["Open Targets", "Disease / target IDs", "Official GraphQL"],
  ["PubChem", "Seed identity", "Official PUG REST"],
  ["ChEMBL", "Structure analogues", "Official Web Services"],
  ["RCSB PDB", "Experimental structure", "Official Data API"],
  ["AlphaFold DB", "Predicted structure", "Official API"],
  ["ZINC22", "Search-space expansion", "Opt-in remote task"],
  ["RDKit", "Descriptors + alerts", "Local computation"],
  ["AutoDock Vina", "Docking adapter", "Qualified local worker"],
] as const;

const stageLabels = [
  "Target evidence",
  "Target structure",
  "Seed identity",
  "Analogue search",
  "Standardization",
  "Medchem alerts",
  "Priority ranking",
  "Docking readiness",
  "Sourcing hand-off",
  "Human review",
];

function valueOrNull(value: string): string | null {
  const clean = value.trim();
  return clean || null;
}

function statusLabel(status: OpenDiscoveryResult["status"]): string {
  return status === "completed-with-warning" ? "Completed with review flags" : status;
}

function CandidateFlags({ candidate }: { candidate: OpenCandidate }) {
  const alertCount = candidate.pains_alerts.length + candidate.brenk_alerts.length + candidate.nih_alerts.length;
  return <div className="od-flags">
    <span className={candidate.lipinski_violations.length ? "warn" : "pass"}>Ro5 {candidate.lipinski_violations.length ? `${candidate.lipinski_violations.length} flags` : "pass"}</span>
    <span className={alertCount ? "warn" : "pass"}>Alerts {alertCount}</span>
    {candidate.quality_flags.length > 0 && <span className="warn">Identity {candidate.quality_flags.length}</span>}
  </div>;
}

export function OpenDiscoveryWorkspace() {
  const [publicSourcesEnabled, setPublicSourcesEnabled] = useState(false);
  useEffect(() => { getBackendJson<Array<{ code: string; live_enabled: boolean }>>("/v1/open-discovery/connectors").then((connectors) => setPublicSourcesEnabled(connectors.some((source) => source.code !== "rdkit" && source.live_enabled))).catch(() => setPublicSourcesEnabled(false)); }, []);
  const [input, setInput] = useState(defaultInput);
  const [seedSmiles, setSeedSmiles] = useState("");
  const [pdbId, setPdbId] = useState("");
  const [uniprot, setUniprot] = useState("");
  const [running, setRunning] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);
  const [result, setResult] = useState<OpenDiscoveryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focusId, setFocusId] = useState("");

  const focused = useMemo(
    () => result?.candidates.find((candidate) => candidate.compound_id === focusId) ?? result?.candidates[0] ?? null,
    [focusId, result],
  );

  async function execute() {
    if (running) return;
    const request: OpenDiscoveryInput = {
      ...input,
      target_symbol: valueOrNull(input.target_symbol ?? ""),
      seed_compound_name: valueOrNull(input.seed_compound_name ?? ""),
      seed_smiles: valueOrNull(seedSmiles),
      pdb_id: valueOrNull(pdbId)?.toUpperCase() ?? null,
      uniprot_accession: valueOrNull(uniprot)?.toUpperCase() ?? null,
    };
    setResult(null);
    setError(null);
    setRunning(true);
    setActiveStage(0);
    try {
      const run = await runOpenDiscovery(request);
      setResult(run);
      setFocusId(run.candidates[0]?.compound_id ?? "");
    } catch {
      setResult(null);
      setError("Please retry when discovery is available.");
    } finally {
      setActiveStage(stageLabels.length);
      setRunning(false);
    }
  }

  return <div className="open-discovery">
    {error && <div className="registry-empty"><b>Discovery workspace unavailable.</b> {error}</div>}
    <section className="module-heading od-heading">
      <div>
        <span>DISCOVER / OPEN WORKFLOW</span>
        <h1>Public-source discovery orchestrator</h1>
        <p>A reviewable evidence-to-candidate workflow using local scientific computation and operator-enabled public sources.</p>
      </div>
      <button className="primary" onClick={execute} disabled={running}>
        {running ? "Running workflow…" : "Run open discovery"}
      </button>
    </section>

    <div className="od-boundary">
      <b>Capability boundary</b>
      <span>This is not Recursion LOWE, PhenoMap, MatchMaker, generative chemistry, robotics, or a validated oncology model. It is a reviewable public-source research workflow.</span>
    </div>

    <section className="od-config module-card">
      <div className="card-title"><div><span>RUN DEFINITION</span><h2>Scientific inputs and execution mode</h2></div><b>All fields remain in the run record</b></div>
      <div className="od-form-grid">
        <label><span>Disease context</span><input value={input.disease} onChange={(event) => setInput({ ...input, disease: event.target.value })}/><small>Retrieval context—not a model feature.</small></label>
        <label><span>Target symbol</span><input value={input.target_symbol ?? ""} onChange={(event) => setInput({ ...input, target_symbol: event.target.value })}/><small>Example: EGFR, RAF1, KRAS.</small></label>
        <label><span>Seed compound</span><input value={input.seed_compound_name ?? ""} onChange={(event) => setInput({ ...input, seed_compound_name: event.target.value })}/><small>Known local record or PubChem name.</small></label>
        <label><span>Candidate limit</span><select value={input.candidate_limit} onChange={(event) => setInput({ ...input, candidate_limit: Number(event.target.value) })}><option value={5}>5</option><option value={8}>8</option><option value={12}>12</option><option value={20}>20</option></select><small>Top transparent chemistry priorities.</small></label>
        <label className="wide"><span>Seed SMILES <em>optional override</em></span><input value={seedSmiles} onChange={(event) => setSeedSmiles(event.target.value)} placeholder="Paste canonical or isomeric SMILES"/><small>The research engine standardizes and fingerprints this structure with RDKit.</small></label>
        <label><span>Experimental PDB ID <em>optional</em></span><input value={pdbId} onChange={(event) => setPdbId(event.target.value)} placeholder="Example: 4WKQ" maxLength={4}/><small>Preferred for qualified docking.</small></label>
        <label><span>UniProt accession <em>optional</em></span><input value={uniprot} onChange={(event) => setUniprot(event.target.value)} placeholder="Example: P00533"/><small>AlphaFold fallback; confidence review required.</small></label>
      </div>
      <label className="od-toggle">
        <input type="checkbox" checked={input.public_connectors && publicSourcesEnabled} disabled={!publicSourcesEnabled} onChange={(event) => setInput({ ...input, public_connectors: event.target.checked })}/>
        <i><span/></i>
        <div><b>Live public sources</b><span>{publicSourcesEnabled ? "Enable approved public source calls for this run." : "Not enabled in this environment. Local analysis remains available."}</span></div>
      </label>
    </section>

    {!running && !result && <>
      <section className="od-source-grid">
        {sourceMap.map(([name, purpose, mode]) => <article key={name}><i/>
          <span>{mode}</span><b>{name}</b><small>{purpose}</small>
        </article>)}
      </section>
      <section className="module-card od-ready">
        <div><span>READY TO RUN</span><h2>What the engine will actually do</h2><p>Resolve a seed, scan local/open candidates, calculate molecular properties, surface structural-alert matches, rank by a visible formula, and stop at every step that needs real scientific inputs or authorization.</p></div>
        <ol>{stageLabels.map((stage, index) => <li key={stage}><i>{String(index + 1).padStart(2, "0")}</i>{stage}</li>)}</ol>
      </section>
    </>}

    {running && <section className="module-card od-running">
      <div className="od-spinner"><i/><span/></div>
      <div><span>OPERATIONAL TRACE</span><h2>{stageLabels[Math.min(activeStage, stageLabels.length - 1)]}</h2><p>Showing pipeline state, not hidden model reasoning.</p></div>
      <div className="od-progress"><i style={{ width: `${Math.max(8, ((activeStage + 1) / stageLabels.length) * 100)}%` }}/></div>
      <ol>{stageLabels.map((stage, index) => <li key={stage} className={index < activeStage ? "done" : index === activeStage ? "active" : "waiting"}><i>{index < activeStage ? "✓" : index + 1}</i><span>{stage}</span></li>)}</ol>
    </section>}

    {result && <>
      <section className={`od-run-banner ${result.backendConnected ? "live" : "unavailable"}`}>
        <div><i/><span>{"PYTHON ENGINE"}</span><b>{result.modeMessage}</b></div>
        <div><span>Run ID</span><code>{result.run_id}</code></div>
        <div><span>Status</span><b>{statusLabel(result.status)}</b></div>
        <div><span>Docking</span><b>No score · {result.docking.status}</b></div>
      </section>

      <section className="module-card od-trace-card">
        <div className="card-title"><div><span>VISIBLE EXECUTION TRACE</span><h2>{result.events.length} inspectable workflow stages</h2></div><b>{new Date(result.created_at).toLocaleString()}</b></div>
        <div className="od-trace">
          {result.events.map((event) => <article key={event.stage} className={event.status}>
            <div className="od-trace-number">{String(event.sequence).padStart(2, "0")}</div>
            <div><span>{event.stage}</span><b>{event.label}</b><p>{event.message}</p></div>
            <div className="od-trace-meta"><span>{event.status.replaceAll("-", " ")}</span><small>{event.duration_ms} ms</small></div>
          </article>)}
        </div>
      </section>

      <section className="od-results-grid">
        <article className="module-card od-candidate-table">
          <div className="card-title"><div><span>CHEMISTRY PRIORITY</span><h2>{result.candidates.length} candidate structures</h2></div><b>Not predicted efficacy</b></div>
          <div className="module-table"><table><thead><tr><th>#</th><th>Candidate</th><th>Similarity</th><th>QED</th><th>Flags</th><th>Priority</th><th>Disposition</th></tr></thead><tbody>
            {result.candidates.map((candidate) => <tr key={candidate.compound_id} className={focused?.compound_id === candidate.compound_id ? "focused" : ""} onClick={() => setFocusId(candidate.compound_id)}>
              <td><b>{candidate.rank}</b></td><td><b>{candidate.display_name}</b><small>{candidate.source_name} · {candidate.source_record_id}</small></td><td>{Math.round(candidate.similarity_to_seed * 100)}%</td><td>{candidate.descriptors.qed.toFixed(2)}</td><td><CandidateFlags candidate={candidate}/></td><td><strong className="od-score">{candidate.priority_score.toFixed(1)}</strong></td><td><span className={`od-disposition ${candidate.disposition}`}>{candidate.disposition}</span></td>
            </tr>)}
          </tbody></table></div>
        </article>

        {focused && <aside className="module-card od-candidate-detail">
          <span>CANDIDATE {focused.rank}</span><h2>{focused.display_name}</h2><code>{focused.inchikey}</code>
          <div className="od-detail-score"><strong>{focused.priority_score.toFixed(1)}</strong><span>/100 chemistry priority</span></div>
          <p>{focused.disposition_reason}</p>
          <dl className="spec-list"><div><dt>Formula</dt><dd>{focused.descriptors.molecular_formula}</dd></div><div><dt>MW</dt><dd>{focused.descriptors.molecular_weight.toFixed(1)} Da</dd></div><div><dt>cLogP</dt><dd>{focused.descriptors.clogp.toFixed(2)}</dd></div><div><dt>TPSA</dt><dd>{focused.descriptors.tpsa.toFixed(1)} Å²</dd></div></dl>
          <h3>Score composition</h3>
          <div className="od-components">{focused.score_components.map((component) => <div key={component.code} title={component.explanation}><span>{component.label}</span><i><b style={{ width: `${component.normalized_value * 100}%` }}/></i><strong>+{component.contribution.toFixed(1)}</strong></div>)}</div>
          <details><summary>Canonical structure and all flags</summary><code className="od-smiles">{focused.canonical_smiles}</code><ul>{[...focused.lipinski_violations, ...focused.pains_alerts, ...focused.brenk_alerts, ...focused.nih_alerts, ...focused.quality_flags].map((flag) => <li key={flag}>{flag}</li>)}{focused.lipinski_violations.length + focused.pains_alerts.length + focused.brenk_alerts.length + focused.nih_alerts.length + focused.quality_flags.length === 0 && <li>No catalogue or identity flags in this run.</li>}</ul></details>
        </aside>}
      </section>

      <section className="od-bottom-grid">
        <article className="module-card od-docking">
          <div className="card-title"><div><span>DOCKING ADAPTER</span><h2>{result.docking.engine}: {result.docking.status}</h2></div><b className="no-score">NO SCORE EMITTED</b></div>
          <p>{result.docking.scientific_boundary}</p>
          <div className="od-docking-state"><span>Executable detected <b>{result.docking.executable_detected ? "Yes" : "No"}</b></span><span>Receptor reference <b>{result.docking.receptor_id || "Missing"}</b></span><span>Execution <b>Blocked</b></span></div>
          <h3>Missing prerequisites</h3><ul>{result.docking.missing_inputs.map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
        <article className="module-card od-next">
          <div className="card-title"><div><span>HUMAN-IN-THE-LOOP</span><h2>Recommended next actions</h2></div><b>Supervisor gate</b></div>
          <ol>{result.next_actions.map((action, index) => <li key={action}><i>{index + 1}</i><span>{action}</span></li>)}</ol>
        </article>
      </section>

      <Zinc22Search seedSmiles={result.seed.canonical_smiles}/>

      <VinaRunner openDiscoveryRunId={result.run_id}/>

      <section className="module-card od-evidence">
        <div className="card-title"><div><span>PROVENANCE LEDGER</span><h2>{result.evidence.length} source records and hand-offs</h2></div><b>Retrieval mode preserved</b></div>
        <div className="od-evidence-grid">{result.evidence.map((item) => <article key={item.evidence_id}><div><span className={item.status}>{item.status}</span><code>{item.mode}</code></div><h3>{item.source_name}</h3><p>{item.statement}</p><small>{item.licence_note}</small><a href={item.url} target="_blank" rel="noreferrer">Open official source ↗</a></article>)}</div>
      </section>

      <div className="od-final-boundary"><b>Run interpretation:</b> {result.claim_boundary}</div>
    </>}
  </div>;
}
