"use client";

import { useEffect, useState } from "react";
import type { RankedCandidate } from "../lib/ranked-candidate";
import { getBackendJson, type DryRunResult } from "../lib/osiel-client";
import { Compound3DViewer } from "./compound-3d-viewer";

type BackendExperiment = {
  experiment_id: string;
  status: string;
  simulation_only: boolean;
  protocol: { title: string; compound_ids: string[]; cell_line: string; assay_type: string };
  created_at: string;
};

type Props = {
  candidates: RankedCandidate[];
  selectedIds: string[];
  initialResult: DryRunResult | null;
  onRunExperiment: () => Promise<DryRunResult | null>;
};

type BackendResult = { result_id: string; experiment_id: string; observations: unknown[]; estimated_ic50_um: Record<string, number>; qc_status: string; qc_checks: Record<string, boolean>; disclaimer: string };

export function ExperimentLab({ candidates, selectedIds, initialResult, onRunExperiment }: Props) {
  const [history, setHistory] = useState<BackendExperiment[]>([]);
  const [result, setResult] = useState<DryRunResult | null>(initialResult);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(initialResult?.experimentId ?? null);

  async function refresh() {
    setLoading(true);
    try {
      const records = await getBackendJson<BackendExperiment[]>("/v1/experiments");
      setHistory(records);
      setError(null);
    } catch {
      setHistory([]);
      setError("Please retry when the experiment workspace is available.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { getBackendJson<BackendExperiment[]>("/v1/experiments").then((records) => { setHistory(records); setLoading(false); }).catch(() => { setError("Please retry when the experiment workspace is available."); setLoading(false); }); }, []);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const response = await onRunExperiment();
      if (!response) throw new Error("Experiment service unavailable. No result was created.");
      setResult(response);
      setSelectedExperimentId(response.experimentId);
      await refresh();
    } catch (cause) {
      setResult(null);
      setError(cause instanceof Error ? cause.message : "Experiment service unavailable");
    } finally {
      setRunning(false);
    }
  }

  async function inspect(experimentId: string) {
    setSelectedExperimentId(experimentId);
    setResult(null);
    setError(null);
    try {
      const records = await getBackendJson<BackendResult[]>(`/v1/experiments/${encodeURIComponent(experimentId)}/results`);
      const record = records[0];
      if (!record) return;
      setResult({ experimentId, resultId: record.result_id, qcStatus: record.qc_status, qcChecks: record.qc_checks, observationCount: record.observations.length, estimatedIc50: record.estimated_ic50_um, backendConnected: true, disclaimer: record.disclaimer });
    } catch {
      setError("Experiment results could not be loaded. Retry when the research engine is available.");
    }
  }

  const compound = candidates.find((item) => item.compound_id === selectedId);
  return <div className="module-workspace">
    <section className="module-heading"><div><span>VALIDATE / EXPERIMENTS</span><h1>Experiment laboratory</h1><p>Computational runs and recorded research history. Research use only.</p></div></section>
    <div className="module-grid two">
      <article className="module-card">
        <h2>Computational dose-response dry-run</h2>
        <p>{selectedIds.length} ranked compounds selected. The run does not perform a physical assay.</p>
        <button className="primary" onClick={() => void run()} disabled={running || selectedIds.length === 0}>{running ? "Running…" : "Run computational experiment"}</button>
        {result && <div className="result-banner"><div><b>{result.experimentId}</b><span>{result.observationCount} simulated observations · QC {result.qcStatus}</span><p>{result.disclaimer}</p></div></div>}
        {error && <div className="professor-warning"><b>Experiment workspace unavailable</b><p>{error}</p><button onClick={() => void refresh()}>Retry</button></div>}
      </article>
      <article className="module-card"><h2>Computational experiment history</h2>
        {loading ? <p>Loading experiments…</p> : history.length === 0 ? <p>No experiments recorded yet.</p> : <div className="history-list">{history.map((item) => <div key={item.experiment_id}><b>{item.protocol.title}</b><small>{item.experiment_id} · {item.status} · {new Date(item.created_at).toLocaleString()}</small><p>{item.simulation_only ? "Computational simulation only" : "Measured result"}</p><button onClick={() => void inspect(item.experiment_id)} disabled={selectedExperimentId === item.experiment_id && Boolean(result)}>Inspect results and QC</button></div>)}</div>}
      </article>
    </div>
    {result && <article className="module-card"><h2>Protocol and quality checks</h2><p>{history.find((item) => item.experiment_id === result.experimentId)?.protocol.assay_type ?? "Computational assay"} · {history.find((item) => item.experiment_id === result.experimentId)?.protocol.cell_line ?? "Research cell line"}</p><ul>{Object.entries(result.qcChecks ?? {}).map(([check, passed]) => <li key={check}>{check.replaceAll("_", " ")}: {passed ? "Passed" : "Review required"}</li>)}</ul></article>}
    {result && <article className="module-card"><h2>Estimated IC50</h2><div className="module-table"><table><thead><tr><th>Compound</th><th>Estimated IC50 (µM)</th></tr></thead><tbody>{Object.entries(result.estimatedIc50).map(([id, value]) => <tr key={id}><td><button onClick={() => setSelectedId(id)}>{candidates.find((candidate) => candidate.compound_id === id)?.display_name ?? id}</button></td><td>{value.toFixed(2)}</td></tr>)}</tbody></table></div></article>}
    {compound && <Compound3DViewer candidate={compound} experimentId={result?.experimentId ?? ""} resultStatus="completed"/>}
    <p className="ai-boundary">Computational hypotheses require human scientific review. Simulated observations are not independently validated efficacy evidence and cannot train a validated model.</p>
  </div>;
}
