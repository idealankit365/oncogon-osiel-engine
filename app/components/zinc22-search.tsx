"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getBackendJson,
  refreshZincSearch,
  startZincSearch,
  type ZincCandidate,
  type ZincSearchJob,
} from "../lib/osiel-client";


function downloadCsv(job: ZincSearchJob) {
  const quote = (value: string | number) => `"${String(value).replaceAll('"', '""')}"`;
  const rows = [
    ["rank", "remote_id", "smiles", "inchikey", "similarity", "qed", "priority_score", "catalogs"],
    ...job.candidates.map((item) => [
      item.rank,
      item.remote_id,
      item.canonical_smiles,
      item.inchikey,
      item.similarity_to_seed,
      item.descriptors.qed,
      item.priority_score,
      item.catalogs.join(" | "),
    ]),
  ];
  const blob = new Blob([rows.map((row) => row.map(quote).join(",")).join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${job.job_id}-zinc22-shortlist.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function compactCount(value: number) {
  return new Intl.NumberFormat("en", { notation:"compact", maximumFractionDigits:2 }).format(value);
}


export function Zinc22Search({ seedSmiles }: { seedSmiles: string }) {
  const [enabled, setEnabled] = useState(false);
  useEffect(() => { getBackendJson<{ enabled: boolean }>("/v1/zinc22/capabilities").then((capability) => setEnabled(capability.enabled)).catch(() => setEnabled(false)); }, []);
  const [graphDistance,setGraphDistance] = useState(2);
  const [anonymousDistance,setAnonymousDistance] = useState(1);
  const [maxResults,setMaxResults] = useState(25);
  const [job,setJob] = useState<ZincSearchJob | null>(null);
  const [error,setError] = useState<string | null>(null);
  const [busy,setBusy] = useState(false);
  const [focusId,setFocusId] = useState<string | null>(null);
  const pending = job?.status === "submitted" || job?.status === "pending";
  const focused = useMemo<ZincCandidate | null>(() => job?.candidates.find((item) => item.remote_id === focusId) ?? job?.candidates[0] ?? null,[job,focusId]);

  async function submit() {
    setBusy(true);
    setError(null);
    setJob(null);
    const response = await startZincSearch({
      seed_smiles: seedSmiles,
      graph_distance: graphDistance,
      anonymous_distance: anonymousDistance,
      max_results: maxResults,
    });
    setBusy(false);
    if (response.job) setJob(response.job);
    else setError(response.error);
  }

  const refresh = useCallback(async () => {
    if (!job || busy) return;
    setBusy(true);
    const response = await refreshZincSearch(job.job_id);
    setBusy(false);
    if (response.job) {
      setJob(response.job);
      setError(response.job.error);
    } else setError(response.error);
  },[job,busy]);

  useEffect(() => {
    if (!job || !pending || busy) return;
    const timer = window.setTimeout(() => { void refresh(); }, Math.max(5,job.poll_after_seconds) * 1000);
    return () => window.clearTimeout(timer);
  },[job,pending,busy,refresh]);

  return <section className="module-card zinc-runner">
    <div className="card-title"><div><span>REMOTE MULTI-BILLION SEARCH</span><h2>ZINC-22 / CartBlanche SmallWorld</h2></div><b className="zinc-live">{enabled ? "PUBLIC SOURCE AVAILABLE" : "NOT ENABLED IN THIS ENVIRONMENT"}</b></div>
    <div className="zinc-boundary"><b>Where the billions live</b><span>The public CartBlanche server searches its distributed index. Your workstation sends one canonical seed and receives at most {maxResults} candidates for local RDKit assessment—it does not download billions of records.</span></div>
    <div className="zinc-controls">
      <label><span>Graph distance</span><select value={graphDistance} onChange={(event) => setGraphDistance(Number(event.target.value))}>{[0,1,2,3].map((value) => <option key={value} value={value}>{value}</option>)}</select><small>0 exact; larger values broaden edits</small></label>
      <label><span>Anonymous distance</span><select value={anonymousDistance} onChange={(event) => setAnonymousDistance(Number(event.target.value))}>{[0,1,2,3].map((value) => <option key={value} value={value}>{value}</option>)}</select><small>Allows topology variation</small></label>
      <label><span>Import limit</span><select value={maxResults} onChange={(event) => setMaxResults(Number(event.target.value))}>{[10,25,50,100].map((value) => <option key={value} value={value}>{value}</option>)}</select><small>RDKit-analyzed shortlist only</small></label>
      <button className="primary" onClick={submit} disabled={!enabled || busy || pending} title={!enabled ? "Public ZINC-22 search is not enabled in this environment" : undefined}>{busy && !job ? "Submitting public task…" : pending ? "Remote task running…" : "Search public ZINC-22"}</button>
    </div>
    <code className="zinc-seed" title={seedSmiles}>Seed · {seedSmiles}</code>
    {error && <div className="zinc-error"><b>LIVE SEARCH STATUS</b><span>{error}</span></div>}

    {job && <div className={`zinc-job ${job.status}`}>
      <div><span>OSIEL JOB</span><code>{job.job_id}</code></div><div><span>REMOTE QUERY</span><code>{job.remote_query_id}</code></div><div><span>STATE</span><b>{job.status} · {job.remote_status}</b></div><div><span>UPDATED</span><b>{new Date(job.updated_at).toLocaleTimeString()}</b></div>
      {pending && <button onClick={() => void refresh()} disabled={busy}>{busy ? "Checking…" : "Refresh now"}</button>}
    </div>}

    {(pending || (busy && !job)) && <div className="zinc-searching" role="status" aria-live="polite"><div className="od-spinner"><i/><span/></div><div><b>{job ? "CartBlanche is searching its remote index" : "Verifying the live map and searching public chemical space"}</b><span>{job ? "OSIEL tracks the remote task and preserves its source identity." : "The research engine is contacting the provider, validating the advertised index and importing only the bounded result set for local RDKit analysis."}</span></div></div>}

    {job?.status === "completed" && <>
      <div className="zinc-complete"><div><span>INDEX ENTRIES</span><strong>{compactCount(job.index_entries)}</strong></div><div><span>MAPPED / SEARCHABLE</span><strong>{compactCount(job.index_mapped_entries)}</strong></div><div><span>REMOTE RETURNED</span><strong>{job.remote_returned_count}</strong></div><div><span>STANDARDIZED SHORTLIST</span><strong>{job.candidates.length}</strong></div><button onClick={() => downloadCsv(job)} disabled={!job.candidates.length}>Download CSV</button></div>
      <div className="zinc-results">
        <div className="module-table"><table><thead><tr><th>#</th><th>Remote ID</th><th>Similarity</th><th>QED</th><th>MW</th><th>Alerts</th><th>Priority</th></tr></thead><tbody>{job.candidates.map((item) => <tr key={item.remote_id} className={focused?.remote_id === item.remote_id ? "focused" : ""} onClick={() => setFocusId(item.remote_id)}><td>{item.rank}</td><td><b>{item.remote_id}</b><small>{item.tranche || job.index_name}</small></td><td>{Math.round(item.similarity_to_seed * 100)}%</td><td>{item.descriptors.qed.toFixed(2)}</td><td>{item.descriptors.molecular_weight.toFixed(1)}</td><td>{item.pains_alerts.length + item.brenk_alerts.length + item.nih_alerts.length}</td><td><strong>{item.priority_score.toFixed(1)}</strong></td></tr>)}</tbody></table></div>
        {focused && <aside><span>REMOTE HIT {focused.rank}</span><h3>{focused.remote_id}</h3><code>{focused.inchikey}</code><div><strong>{focused.priority_score.toFixed(1)}</strong><small>/100 local chemistry priority</small></div><p>{focused.scientific_boundary}</p><dl className="spec-list"><div><dt>Formula</dt><dd>{focused.descriptors.molecular_formula}</dd></div><div><dt>cLogP</dt><dd>{focused.descriptors.clogp.toFixed(2)}</dd></div><div><dt>TPSA</dt><dd>{focused.descriptors.tpsa.toFixed(1)} Å²</dd></div><div><dt>Map</dt><dd>{job.index_name}</dd></div></dl><details><summary>Canonical SMILES and review flags</summary><code>{focused.canonical_smiles}</code><ul>{[...focused.lipinski_violations,...focused.pains_alerts,...focused.brenk_alerts,...focused.nih_alerts,...focused.quality_flags].map((flag) => <li key={flag}>{flag}</li>)}{focused.lipinski_violations.length + focused.pains_alerts.length + focused.brenk_alerts.length + focused.nih_alerts.length + focused.quality_flags.length === 0 && <li>No local catalogue flags.</li>}</ul></details></aside>}
      </div>
      <div className="zinc-proof"><span>{job.index_scope}</span><code>result sha256 · {job.remote_result_sha256 || "not supplied"}</code><a href={job.source_url} target="_blank" rel="noreferrer">Open CartBlanche ↗</a></div>
    </>}
    <p className="ai-boundary">A search hit is a structure record, not a purchased vial, successful synthesis, target interaction, biological response, or laboratory result. Supplier identity, form, stock, purity, IP and safety require separate verification.</p>
  </section>;
}
