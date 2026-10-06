"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchBulkDataSource, fetchTDCData, loadDataConnectors, searchChemspaceData, searchUniProtData,
  type DataConnectorCapability, type DataConnectorResult,
} from "../lib/osiel-client";

const bulkCodes = new Set(["nci60", "coconut", "npass", "anpdb", "lotus", "tox21", "toxcast"]);

export function SourceConnectorConsole() {
  const [items, setItems] = useState<DataConnectorCapability[]>([]);
  const [backendConnected, setBackendConnected] = useState(false);
  const [selected, setSelected] = useState("nci60");
  const [release, setRelease] = useState("operator-approved-release");
  const [query, setQuery] = useState("EGFR");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<DataConnectorResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { loadDataConnectors().then(({ items: loaded, backendConnected: connected }) => { setItems(loaded); setBackendConnected(connected); }).catch((cause) => { setItems([]); setBackendConnected(false); setError(cause instanceof Error ? cause.message : "Backend unavailable"); }); }, []);
  const current = useMemo(() => items.find((item) => item.source_code === selected), [items, selected]);

  async function run() {
    setBusy(true); setError(null); setResult(null);
    try {
      const output = bulkCodes.has(selected) ? await fetchBulkDataSource(selected, release)
        : selected === "tdc" ? await fetchTDCData()
          : selected === "uniprot" ? await searchUniProtData(query) : await searchChemspaceData(query);
      setResult(output);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Connector request failed"); }
    finally { setBusy(false); }
  }

  const previewCount = result ? (result.record_count ?? (Array.isArray(result.record_preview) ? result.record_preview.length : result.record_preview?.records?.length ?? 0)) : 0;
  return <section className="module-card source-console">
    <div className="card-title"><div><span>LIVE DATA INGESTION</span><h2>Scientific connector control center</h2></div><b className={backendConnected ? "connector-online" : "connector-offline"}>{backendConnected ? "RESEARCH ENGINE CONNECTED" : "ENGINE UNAVAILABLE"}</b></div>
    <p className="connector-intro">Every fetch is bounded and provenance-tracked. Bulk files remain quarantined until their release checksum, parser, schema and scientific review pass.</p>
    <div className="connector-grid">{items.map((item) => <button key={item.source_code} className={selected === item.source_code ? "active" : ""} onClick={() => { setSelected(item.source_code); setResult(null); setError(null); }}><i className={item.live_enabled && item.configured ? "ready" : "blocked"}/><span><b>{item.source_name}</b><small>{item.purpose}</small></span><em>{item.live_enabled && item.configured ? "READY" : item.connector_type === "licensed-api" ? "KEY REQUIRED" : "CONFIGURE"}</em></button>)}</div>
    {current && <div className="connector-runner"><div><span>Selected connector</span><strong>{current.source_name}</strong><small>{current.connector_type.replaceAll("-", " ")} · {current.licence_note || "Source-specific terms and attribution apply."}</small></div>{bulkCodes.has(selected) ? <label><span>Approved release ID</span><input value={release} onChange={(event) => setRelease(event.target.value)}/></label> : <label><span>{selected === "tdc" ? "Configured dataset" : "Search query"}</span><input value={selected === "tdc" ? "Tox · hERG" : query} disabled={selected === "tdc"} onChange={(event) => setQuery(event.target.value)}/></label>}<button className="primary" onClick={run} disabled={busy || !backendConnected}>{busy ? "Fetching and verifying…" : "Fetch data"}</button></div>}
    {error && <div className="connector-result failed"><b>FETCH BLOCKED</b><span>{error}</span></div>}
    {result && <div className={`connector-result ${result.status === "failed" ? "failed" : result.checksum_verified || result.status === "completed" ? "passed" : "quarantined"}`}><b>{(result.status || "completed").replaceAll("-", " ").toUpperCase()}</b><span>{result.source_name || result.source_code} · {previewCount} preview records · {result.byte_count ? `${result.byte_count.toLocaleString()} bytes` : "API response"}</span>{result.sha256 && <code>SHA-256 {result.sha256}</code>}<small>Training eligible: NO · {result.next_gate || "Scientific review and evidence mapping are still required."}</small></div>}
    <div className="connector-boundary"><b>Safety boundary</b><span>Fetching data does not prove a compound works. It only creates a traceable raw snapshot for standardization, QC and scientist approval.</span></div>
  </section>;
}
