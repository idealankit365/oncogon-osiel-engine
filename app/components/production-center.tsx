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
  const [loading, setLoading] = useState(true);
  const [services, setServices] = useState<Array<{ name: string; status: string }>>([]);
  async function refresh() {
    setLoading(true);
    try {
      const [state, features, assistant, docking, modelLab, multimodal, publicConnectors, dataConnectors] = await Promise.all([
        getBackendJson<Readiness>("/v1/system/readiness"),
        getBackendJson<Capabilities>("/v1/system/capabilities"),
        getBackendJson<{ enabled: boolean; ingestion_enabled: boolean }>("/v1/assistant/capabilities"),
        getBackendJson<{ operator_enabled: boolean; binding_available: boolean }>("/v1/docking/capabilities"),
        getBackendJson<{ operator_enabled: boolean }>("/v1/model-lab/capabilities"),
        getBackendJson<{ enabled: boolean }>("/v1/multimodal/capabilities"),
        getBackendJson<Array<{ code: string; live_enabled: boolean }>>("/v1/open-discovery/connectors"),
        getBackendJson<Array<{ live_enabled: boolean; configured: boolean }>>("/v1/data-connectors"),
      ]);
      setReadiness(state);
      setCapabilities(features);
      setServices([
        { name: "Scientific Engine", status: "Operational" },
        { name: "Research Registry", status: `${state.compound_count} reference compounds` },
        { name: "Project Knowledge", status: assistant.ingestion_enabled ? "Available" : "Not enabled" },
        { name: "Public connectors", status: publicConnectors.some((connector) => connector.live_enabled && !["rdkit", "autodock-vina"].includes(connector.code)) ? "Enabled" : "Not enabled" },
        { name: "Licensed Data", status: dataConnectors.some((connector) => connector.live_enabled && connector.configured) ? "Configured" : "Not configured" },
        { name: "AI Synthesis", status: assistant.enabled ? "Available" : "Not enabled for this environment" },
        { name: "Model Laboratory", status: modelLab.operator_enabled ? "Available" : "Requires operator configuration" },
        { name: "Molecular Docking", status: docking.operator_enabled && docking.binding_available ? "Available" : docking.binding_available ? "Not enabled" : "Optional integration unavailable on this host" },
        { name: "Multimodal Analysis", status: multimodal.enabled ? "Available" : "Integration ready" },
        { name: "Research Archive", status: state.object_storage ? "Available" : "Not configured" },
      ]);
      setError(null);
    } catch (cause) {
      setReadiness(null);
      setCapabilities(null);
      setServices([]);
      console.error("Platform capability request failed", cause);
      setError("Platform capabilities are temporarily unavailable. Retry to refresh this view.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 0);
    return () => window.clearTimeout(timer);
    // Runtime status is loaded on mount and explicitly refreshed by the button.
  }, []);
  return <>
    <section className="module-heading"><div><span>OSIEL / PLATFORM</span><h1>Platform control center</h1><p>Research capabilities, governance gates, and optional integrations in this workspace.</p></div><button className="primary" onClick={() => void refresh()}>Refresh status</button></section>
    {loading && !readiness && !error && <article className="module-card"><h2>Reviewing platform capabilities…</h2></article>}
    {error && <div className="production-warning"><b>Workspace status unavailable</b><span>{error}</span></div>}
    {readiness && <><div className="module-stats"><div className="module-stat"><span>RESEARCH REGISTRY</span><strong>{readiness.compound_count}</strong><small>Reference compounds</small></div><div className="module-stat"><span>RESEARCH MODEL</span><strong>Active</strong><small>Computational simulation</small></div><div className="module-stat"><span>INDEPENDENT VALIDATION</span><strong>{readiness.validated_scientific_model ? "Recorded" : "Required"}</strong><small>Scientific governance</small></div><div className="module-stat"><span>DEPLOYMENT REVIEW</span><strong>{readiness.institution_approved ? "Approved" : "Pending"}</strong><small>Institutional approval</small></div></div><article className="module-card"><h2>Environment readiness</h2><p>Research simulation mode: {readiness.mode}. Computational estimates are not measured or clinical results.</p>{readiness.blockers.length > 0 && <details><summary>Review production gates</summary><ul>{readiness.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul></details>}</article></>}
    {services.length > 0 && <article className="module-card"><h2>Research and integration capabilities</h2><div className="module-stats">{services.map((service) => <div className="module-stat" key={service.name}><span>{service.name.toUpperCase()}</span><strong>{service.status}</strong></div>)}</div></article>}
    {capabilities && <details className="module-card"><summary>Technical capability details</summary><div className="module-grid two"><article className="module-card"><h2>Implemented services</h2><ul>{capabilities.implemented.map((item) => <li key={item}>{item}</li>)}</ul></article><article className="module-card"><h2>Integration targets</h2><ul>{capabilities.adapter_ready.map((item) => <li key={item}>{item}</li>)}</ul></article></div></details>}
    <div className="claim-boundary">Code completion does not equal scientific validation. Human review, instrument qualification, institutional identity and independent model validation remain required.</div>
  </>;
}
