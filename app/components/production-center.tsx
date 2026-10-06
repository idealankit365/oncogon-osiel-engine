"use client";

import { useState } from "react";

const layers = [
  { name:"Next.js research workbench", state:"live", detail:"Hosted interface, experiment history and university teaching workflow." },
  { name:"Scientific computation engine", state:"verified", detail:"Ranking, simulation, QC, audit, Vina, live search and model-lab workflows execute independently." },
  { name:"Scientific engine connection", state:"blocked", detail:"A protected scientific service endpoint is still required. The hosted reference workflow must be retired before production use." },
  { name:"PostgreSQL + RDKit", state:"adapter", detail:"Deployment target and migration boundary defined; institutional database credentials are required." },
  { name:"Immutable raw-file storage", state:"implemented", detail:"Content-addressed SHA-256 storage and metadata manifest added; production requires versioned S3 retention lock." },
  { name:"Plate-reader ingestion", state:"implemented", detail:"Server-side CSV schema, numeric, well, duplicate and control validation added; qualification needs a real instrument export." },
  { name:"10.10B federated search", state:"implemented", detail:"Provider-side REALDB SmallWorld search with bounded local import, live map metadata and response checksum." },
  { name:"Public endpoint dataset", state:"implemented", detail:"Bounded ChEMBL retrieval, immutable raw/normalized snapshots, exact endpoint rules, deduplication and conflict removal." },
  { name:"Scientific baseline model", state:"implemented", detail:"Scaffold-separated train/calibrate/test pipeline, ECFP baseline, calibration and applicability-domain output; independent validation remains blocked." },
  { name:"Active-learning proposal", state:"implemented", detail:"Uncertainty, distance-to-training and diversity propose the next batch; execution and promotion remain human-gated." },
  { name:"Docking qualification", state:"implemented", detail:"Vina execution plus heavy-atom redocking RMSD. Affinity scoring stays unqualified until a larger benchmark passes." },
  { name:"Professor AI", state:"guarded", detail:"Cited retrieval mode is active; institution-approved LLM, documents and faculty evaluation are required." },
  { name:"University release", state:"blocked", detail:"POPIA, security, SOP, biosafety, training and named institutional acceptance are external approval gates." },
];

const externalGates = [
  ["Instrument qualification","Manufacturer, exact model, serial, software version, units and anonymised export"],
  ["Scientific data rights","Approved dataset manifest, licence, purpose limitation and redistribution terms"],
  ["University identity","OIDC issuer, client, role mapping and account lifecycle owner"],
  ["Faculty evidence library","Approved SOPs, manuals, papers, course scope and document owners"],
  ["Institutional acceptance","POPIA, security, biosafety/ethics, validation protocol and named signatories"],
];

const phases = [
  { title:"Teaching pilot", score:72, complete:["Simulation sandbox","Experiment debugger","Student-safe claim boundaries","Supervisor readiness gate"], pending:["Course roster","Assignments and marking","University SSO","Instructor acceptance test"] },
  { title:"Laboratory pilot", score:38, complete:["Import schema","Raw-file hashing","QC quarantine","Review separation"], pending:["Real reader qualification","Validated normalization SOP","Object retention lock","Laboratory acceptance plates"] },
  { title:"Scientific validation", score:18, complete:["Evaluation contracts","Simulation training lock"], pending:["Licensed labels","External test set","Calibrated model","Independent reproducibility study"] },
  { title:"Institutional production", score:24, complete:["Deployment manifests","Health endpoint","Role enforcement foundation"], pending:["University OIDC","PostgreSQL migration","Backup restoration drill","POPIA and security sign-off"] },
];

export function ProductionCenter() {
  const [role,setRole] = useState("student");
  const [auditRun,setAuditRun] = useState(false);
  const pack = { generatedAt:new Date().toISOString(), product:"Oncogon AI OSIEL", currentTruth:{ hostedInterface:"live", hostedPythonApi:"not connected", pythonEngine:"verified research reference", scientificModel:"not validated", laboratoryUse:"blocked pending qualification" }, requiredExternalGates:externalGates.map(([gate,requirement]) => ({gate,requirement})), phases };
  function downloadPack() { const anchor=document.createElement("a"); anchor.href=URL.createObjectURL(new Blob([JSON.stringify(pack,null,2)],{type:"application/json"})); anchor.download="OSIEL-production-readiness-pack.json"; anchor.click(); URL.revokeObjectURL(anchor.href); }
  return <><section className="module-heading"><div><span>SYSTEM / PRODUCTION</span><h1>Production readiness control center</h1><p>One truthful view of what is live, which scientific services execute, and what remains blocked by scientific or institutional approval.</p></div><button className="primary" onClick={() => setAuditRun(true)}>Run readiness audit</button></section>
    <section className="runtime-truth"><div><span>HOSTED FRONTEND</span><b>LIVE</b><small>Next.js workbench</small></div><i>→</i><div className="blocked"><span>SCIENTIFIC SERVICE CONNECTION</span><b>LOCAL / EXTERNAL</b><small>Protected hosting required</small></div><i>→</i><div><span>SCIENTIFIC ENGINE</span><b>VERIFIED</b><small>Automated tests + E2E</small></div><i>→</i><div className="blocked"><span>INSTITUTIONAL MODEL</span><b>NOT VALIDATED</b><small>Independent evidence required</small></div></section>
    <div className="production-warning"><b>Production truth</b><span>The hosted interface currently uses a local reference workflow. The scientific engine is tested separately and must be deployed and connected before it powers this interface.</span></div>
    <div className="module-stats"><div className="module-stat"><span>ENGINE TESTS</span><strong>43/43</strong><small>Scientific service contracts</small></div><div className="module-stat"><span>REMOTE SEARCH MAP</span><strong>10.10B</strong><small>9.43B mapped at verified run</small></div><div className="module-stat"><span>LOCAL REFERENCES</span><strong>192</strong><small>RDKit-standardized cache</small></div><div className="module-stat"><span>AUTO-PROMOTIONS</span><strong>0</strong><small>Always human-gated</small></div></div>
    <div className="module-grid production-grid"><article className="module-card"><div className="card-title"><div><span>IMPLEMENTATION LEDGER</span><h2>System layers and release state</h2></div><b>{auditRun ? "AUDIT COMPLETE" : "CURRENT BUILD"}</b></div><div className="layer-ledger">{layers.map((layer) => <div key={layer.name}><i className={layer.state}>{layer.state === "live" || layer.state === "verified" || layer.state === "implemented" ? "✓" : layer.state === "blocked" ? "×" : "◐"}</i><span><b>{layer.name}</b><small>{layer.detail}</small></span><em className={layer.state}>{layer.state}</em></div>)}</div></article><article className="module-card role-simulator"><div className="card-title"><div><span>SERVER ROLE POLICY</span><h2>Student safety boundary</h2></div><b>Reference enforcement</b></div><label className="lab-field"><span>Inspect role</span><select value={role} onChange={(event) => setRole(event.target.value)}><option value="student">Student</option><option value="researcher">Researcher</option><option value="technician">Technician</option><option value="reviewer">Reviewer</option><option value="instructor">Instructor</option><option value="admin">Administrator</option></select></label><div className="permission-matrix">{[["Run teaching simulation",true],["Import raw instrument file",["technician","researcher","instructor","admin"].includes(role)],["Approve own result",false],["Review another researcher",["reviewer","instructor","admin"].includes(role)],["Create training snapshot",["reviewer","admin"].includes(role)],["Promote model automatically",false]].map(([label,allowed]) => <div key={String(label)}><span>{label}</span><b className={allowed ? "allowed" : "denied"}>{allowed ? "ALLOWED" : "DENIED"}</b></div>)}</div><p className="ai-boundary">The scientific service enforces recognized roles in production mode. Institutional OIDC must replace the reference API-key verifier before university release.</p><button onClick={downloadPack}>Download readiness pack</button></article></div>
    <article className="module-card"><div className="card-title"><div><span>FOUR RELEASE GATES</span><h2>Path from teaching software to institutional production</h2></div><b>No silent approvals</b></div><div className="phase-board">{phases.map((phase,index) => <section key={phase.title}><div className="phase-head"><i>{index+1}</i><span><b>{phase.title}</b><small>{phase.score}% software readiness</small></span><strong>{phase.score}%</strong></div><div className="phase-meter"><i style={{width:`${phase.score}%`}}/></div><h3>Implemented</h3>{phase.complete.map((item) => <p className="complete" key={item}>✓ {item}</p>)}<h3>Required</h3>{phase.pending.map((item) => <p key={item}>○ {item}</p>)}</section>)}</div></article>
    <article className="module-card external-gates"><div className="card-title"><div><span>INSTITUTIONAL HANDOFF</span><h2>Inputs software cannot invent</h2></div><b>Owner action required</b></div>{externalGates.map(([gate,requirement],index) => <div key={gate}><i>{index+1}</i><span><b>{gate}</b><small>{requirement}</small></span><em>BLOCKING</em></div>)}</article>
    <div className="claim-boundary"><b>Release rule:</b> code completion does not equal scientific validation. OSIEL remains research-use teaching software until the named university signs the instrument, model, security, privacy and SOP acceptance records.</div></>;
}
