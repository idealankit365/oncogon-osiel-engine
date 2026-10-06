"use client";

import { useEffect, useState } from "react";
import { getBackendJson } from "../lib/osiel-client";

type Readiness = {
  mode: string;
  python_engine: boolean;
  compound_count: number;
  object_storage: boolean;
  authentication_enforced: boolean;
  plate_reader_validation: boolean;
  immutable_audit: boolean;
  validated_scientific_model: boolean;
  institution_approved: boolean;
  blockers: string[];
};
type Capabilities = { engine: string; mode: string; implemented: string[]; adapter_ready: string[]; excluded_from_phase_1: string[] };

export function ProductionCenter() {
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [services, setServices] = useState<Array<{ name: string; status: string }>>([]);
  async function refresh() {
    try {
      const [state, features, assistant, docking, modelLab, multimodal] = await Promise.all([
        getBackendJson<Readiness>("/v1/system/readiness"),
        getBackendJson<Capabilities>("/v1/system/capabilities"),
        getBackendJson<{ enabled: boolean; ingestion_enabled: boolean }>("/v1/assistant/capabilities"),
        getBackendJson<{ operator_enabled: boolean; binding_available: boolean }>("/v1/docking/capabilities"),
        getBackendJson<{ operator_enabled: boolean }>("/v1/model-lab/capabilities"),
        getBackendJson<{ enabled: boolean }>("/v1/multimodal/capabilities"),
      ]);
      setReadiness(state);
      setCapabilities(features);
      setServices([
        { name: "Backend", status: "Connected" },
        { name: "Database", status: "Reference persistence available" },
        { name: "Project knowledge", status: assistant.ingestion_enabled ? "Ingestion enabled" : "Ingestion disabled" },
        { name: "AI synthesis", status: assistant.enabled ? "Enabled" : "Not enabled" },
        { name: "Model lab", status: modelLab.operator_enabled ? "Enabled" : "Not enabled" },
        { name: "Docking", status: docking.operator_enabled && docking.binding_available ? "Available" : docking.binding_available ? "Not enabled" : "Unavailable on this host" },
        { name: "Multimodal", status: multimodal.enabled ? "Enabled" : "Not enabled" },
        { name: "Authentication", status: state.authentication_enforced ? "Enforced" : "Showcase mode" },
      ]);
      setError(null);
    } catch (cause) {
      setReadiness(null);
      setCapabilities(null);
      setServices([]);
      setError(cause instanceof Error ? cause.message : "Backend unavailable");
    }
  }
  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 0);
    return () => window.clearTimeout(timer);
    // Runtime status is loaded on mount and explicitly refreshed by the button.
  }, []);
  return <>
    <section className="module-heading"><div><span>SYSTEM / READINESS</span><h1>Production readiness control center</h1><p>Runtime state reported by FastAPI. Research use only.</p></div><button className="primary" onClick={() => void refresh()}>Refresh readiness</button></section>
    {error && <div className="production-warning"><b>Backend unavailable</b><span>{error}</span></div>}
    {readiness && <><div className="module-stats"><div className="module-stat"><span>BACKEND MODE</span><strong>{readiness.mode}</strong><small>Backend configuration</small></div><div className="module-stat"><span>COMPOUNDS</span><strong>{readiness.compound_count}</strong><small>Backend registry</small></div><div className="module-stat"><span>VALIDATED MODEL</span><strong>{readiness.validated_scientific_model ? "Yes" : "No"}</strong><small>Scientific validation gate</small></div><div className="module-stat"><span>INSTITUTION APPROVED</span><strong>{readiness.institution_approved ? "Yes" : "No"}</strong><small>External approval</small></div></div><article className="module-card"><h2>Readiness blockers</h2>{readiness.blockers.length ? <ul>{readiness.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul> : <p>No blockers reported by the backend.</p>}</article></>}
    {services.length > 0 && <article className="module-card"><h2>Service status</h2><div className="module-stats">{services.map((service) => <div className="module-stat" key={service.name}><span>{service.name.toUpperCase()}</span><strong>{service.status}</strong></div>)}</div></article>}
    {capabilities && <div className="module-grid two"><article className="module-card"><h2>Implemented scientific services</h2><ul>{capabilities.implemented.map((item) => <li key={item}>{item}</li>)}</ul></article><article className="module-card"><h2>Adapter targets</h2><ul>{capabilities.adapter_ready.map((item) => <li key={item}>{item}</li>)}</ul></article></div>}
    <div className="claim-boundary">Code completion does not equal scientific validation. Human review, instrument qualification, institutional identity and independent model validation remain required.</div>
  </>;
}
