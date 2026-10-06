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
  async function refresh() {
    try {
      const [state, features] = await Promise.all([
        getBackendJson<Readiness>("/v1/system/readiness"),
        getBackendJson<Capabilities>("/v1/system/capabilities"),
      ]);
      setReadiness(state);
      setCapabilities(features);
      setError(null);
    } catch (cause) {
      setReadiness(null);
      setCapabilities(null);
      setError(cause instanceof Error ? cause.message : "Backend unavailable");
    }
  }
  useEffect(() => { Promise.all([getBackendJson<Readiness>("/v1/system/readiness"), getBackendJson<Capabilities>("/v1/system/capabilities")]).then(([state, features]) => { setReadiness(state); setCapabilities(features); }).catch((cause) => setError(cause instanceof Error ? cause.message : "Backend unavailable")); }, []);
  return <>
    <section className="module-heading"><div><span>SYSTEM / READINESS</span><h1>Production readiness control center</h1><p>Runtime state reported by FastAPI. Research use only.</p></div><button className="primary" onClick={() => void refresh()}>Refresh readiness</button></section>
    {error && <div className="production-warning"><b>Backend unavailable</b><span>{error}</span></div>}
    {readiness && <><div className="module-stats"><div className="module-stat"><span>BACKEND MODE</span><strong>{readiness.mode}</strong><small>Backend configuration</small></div><div className="module-stat"><span>COMPOUNDS</span><strong>{readiness.compound_count}</strong><small>Backend registry</small></div><div className="module-stat"><span>VALIDATED MODEL</span><strong>{readiness.validated_scientific_model ? "Yes" : "No"}</strong><small>Scientific validation gate</small></div><div className="module-stat"><span>INSTITUTION APPROVED</span><strong>{readiness.institution_approved ? "Yes" : "No"}</strong><small>External approval</small></div></div><article className="module-card"><h2>Readiness blockers</h2>{readiness.blockers.length ? <ul>{readiness.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul> : <p>No blockers reported by the backend.</p>}</article></>}
    {capabilities && <div className="module-grid two"><article className="module-card"><h2>Implemented scientific services</h2><ul>{capabilities.implemented.map((item) => <li key={item}>{item}</li>)}</ul></article><article className="module-card"><h2>Adapter targets</h2><ul>{capabilities.adapter_ready.map((item) => <li key={item}>{item}</li>)}</ul></article></div>}
    <div className="claim-boundary">Code completion does not equal scientific validation. Human review, instrument qualification, institutional identity and independent model validation remain required.</div>
  </>;
}
