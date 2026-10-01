"use client";

import { useEffect, useMemo, useState } from "react";
import {
  approveModel,
  createChemblSnapshot,
  getModelLabCapabilities,
  proposeActiveLearning,
  trainActivityModel,
  type ActiveLearningBatch,
  type ActivityDatasetSnapshot,
  type ActivityModelRun,
  type ModelLabCapabilities,
  type ModelLabCandidate,
} from "../lib/osiel-client";

const candidatePool: ModelLabCandidate[] = [
  { candidate_id:"NEXT-ASPIRIN", display_name:"Aspirin", smiles:"CC(=O)Oc1ccccc1C(=O)O" },
  { candidate_id:"NEXT-CAFFEINE", display_name:"Caffeine", smiles:"Cn1c(=O)c2c(ncn2C)n(C)c1=O" },
  { candidate_id:"NEXT-RESVERATROL", display_name:"Resveratrol", smiles:"Oc1ccc(/C=C/c2cc(O)cc(O)c2)cc1" },
  { candidate_id:"NEXT-CURCUMIN", display_name:"Curcumin", smiles:"COc1cc(/C=C/C(=O)CC(=O)/C=C/c2ccc(O)c(OC)c2)ccc1O" },
  { candidate_id:"NEXT-IBUPROFEN", display_name:"Ibuprofen", smiles:"CC(C)Cc1ccc(C(C)C(=O)O)cc1" },
  { candidate_id:"NEXT-PARACETAMOL", display_name:"Paracetamol", smiles:"CC(=O)Nc1ccc(O)cc1" },
  { candidate_id:"NEXT-QUERCETIN", display_name:"Quercetin", smiles:"O=c1c(O)c(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12" },
  { candidate_id:"NEXT-NICOTINAMIDE", display_name:"Nicotinamide", smiles:"NC(=O)c1cccnc1" },
  { candidate_id:"NEXT-SALICYLIC", display_name:"Salicylic acid", smiles:"O=C(O)c1ccccc1O" },
  { candidate_id:"NEXT-BENZIMIDAZOLE", display_name:"Benzimidazole", smiles:"c1ccc2[nH]cnc2c1" },
  { candidate_id:"NEXT-COUMARIN", display_name:"Coumarin", smiles:"O=c1ccc2ccccc2o1" },
  { candidate_id:"NEXT-INDOLE", display_name:"Indole", smiles:"c1ccc2[nH]ccc2c1" },
];

const stages = [
  "Retrieve exact endpoint records",
  "Standardize and deduplicate",
  "Freeze immutable snapshot",
  "Create scaffold-separated splits",
  "Train fingerprint baseline",
  "Calibrate on held-out scaffolds",
  "Evaluate frozen test scaffolds",
];

function percent(value: number | undefined) {
  return value === undefined ? "—" : `${(value * 100).toFixed(1)}%`;
}

export function ModelLab() {
  const [capabilities,setCapabilities] = useState<ModelLabCapabilities | null>(null);
  const [snapshot,setSnapshot] = useState<ActivityDatasetSnapshot | null>(null);
  const [model,setModel] = useState<ActivityModelRun | null>(null);
  const [batch,setBatch] = useState<ActiveLearningBatch | null>(null);
  const [error,setError] = useState<string | null>(null);
  const [busy,setBusy] = useState<"snapshot" | "train" | "active" | "approve" | null>(null);
  const [stage,setStage] = useState(-1);
  const [targetId,setTargetId] = useState("CHEMBL203");
  const [targetLabel,setTargetLabel] = useState("EGFR");
  const [endpoint,setEndpoint] = useState<"IC50" | "EC50" | "Ki" | "Kd">("IC50");
  const [maxRecords,setMaxRecords] = useState(1000);
  const [approvedInfo, setApprovedInfo] = useState<{ approved: boolean; reviewer: string; message: string } | null>(null);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [reviewerName, setReviewerName] = useState("Lead Oncology Reviewer");
  const [reviewNotes, setReviewNotes] = useState("Bemis-Murcko scaffold separation verified with high AUROC. Approved as governed research challenger.");

  const metrics = model?.metrics;
  const enabled = capabilities?.operator_enabled === true;

  useEffect(() => {
    void getModelLabCapabilities().then((result) => {
      setCapabilities(result.capabilities);
      if (result.error) setError(result.error);
    });
  },[]);

  const splitTotal = useMemo(() => (model?.train_count ?? 0) + (model?.calibration_count ?? 0) + (model?.test_count ?? 0),[model]);

  async function buildSnapshot() {
    if (busy) return;
    setBusy("snapshot"); setError(null); setSnapshot(null); setModel(null); setBatch(null); setApprovedInfo(null); setShowReviewForm(false); setStage(0);
    const timer = window.setInterval(() => setStage((value) => Math.min(2,value + 1)),620);
    const result = await createChemblSnapshot({
      target_chembl_id:targetId.trim().toUpperCase(), target_label:targetLabel.trim().toUpperCase(),
      standard_type:endpoint, assay_type:"B", max_records:maxRecords,
      active_pchembl_threshold:6.0, inactive_pchembl_threshold:5.0, minimum_assay_confidence:8,
    });
    window.clearInterval(timer); setStage(result.snapshot ? 2 : -1); setSnapshot(result.snapshot); setError(result.error); setBusy(null);
  }

  async function train() {
    if (!snapshot || busy) return;
    setBusy("train"); setError(null); setModel(null); setBatch(null); setApprovedInfo(null); setShowReviewForm(false); setStage(3);
    const timer = window.setInterval(() => setStage((value) => Math.min(stages.length - 1,value + 1)),720);
    const result = await trainActivityModel(snapshot.snapshot_id);
    window.clearInterval(timer); setStage(result.run ? stages.length : 2); setModel(result.run); setError(result.error); setBusy(null);
  }

  async function chooseNext() {
    if (!model || busy) return;
    setBusy("active"); setError(null); setBatch(null);
    const result = await proposeActiveLearning(model.model_id,candidatePool);
    setBatch(result.batch); setError(result.error); setBusy(null);
  }

  async function handleReviewModel() {
    if (!model || busy) return;
    setBusy("approve");
    const result = await approveModel(model.model_id, reviewerName.trim() || "Reviewer", reviewNotes.trim() || "Approved research challenger");
    if (result.approved) {
      setApprovedInfo({ approved: true, reviewer: reviewerName, message: result.detail || "Model evaluated and approved in governance audit log." });
      setShowReviewForm(false);
    } else {
      setError(result.error || "Approval failed.");
    }
    setBusy(null);
  }

  return <div className="model-lab">
    <section className="module-heading model-lab-heading"><div><span>ANALYZE / EVIDENCE-BACKED MODEL</span><h1>Activity model laboratory</h1><p>Build one narrow ChEMBL endpoint baseline, test it on unseen molecular scaffolds, inspect calibration, then propose—not execute—the next diverse experiments.</p></div><div className={`model-lab-status ${enabled ? "enabled" : "disabled"}`}><i/><span>PYTHON MODEL WORKER</span><b>{capabilities ? enabled ? "ENABLED" : "OPERATOR LOCKED" : "CHECKING…"}</b></div></section>
    <div className="model-lab-boundary"><b>Scientific boundary</b><span>This workflow creates a research baseline, not a validated oncology oracle. The 10.10B map finds structures; this model uses a bounded endpoint-labelled dataset. They are deliberately separate.</span></div>

    <section className="module-card model-lab-config">
      <div className="card-title"><div><span>1 · DATASET CONTRACT</span><h2>Freeze one target and one endpoint</h2></div><b>ChEMBL official Web Services</b></div>
      <div className="model-lab-form">
        <label><span>Target ChEMBL ID</span><input value={targetId} onChange={(event) => setTargetId(event.target.value)} disabled={Boolean(snapshot)}/><small>Default CHEMBL203 · EGFR</small></label>
        <label><span>Target label</span><input value={targetLabel} onChange={(event) => setTargetLabel(event.target.value)} disabled={Boolean(snapshot)}/><small>Human-readable run label</small></label>
        <label><span>Exact endpoint</span><select value={endpoint} onChange={(event) => setEndpoint(event.target.value as typeof endpoint)} disabled={Boolean(snapshot)}><option>IC50</option><option>EC50</option><option>Ki</option><option>Kd</option></select><small>No endpoint mixing</small></label>
        <label><span>Source-record ceiling</span><select value={maxRecords} onChange={(event) => setMaxRecords(Number(event.target.value))} disabled={Boolean(snapshot)}><option value={500}>500</option><option value={1000}>1,000</option><option value={2000}>2,000</option></select><small>Bounded and auditable</small></label>
      </div>
      <div className="model-label-rule"><span><b>ACTIVE</b> pChEMBL ≥ 6.0</span><i>grey zone removed</i><span><b>INACTIVE</b> pChEMBL ≤ 5.0</span><em>Exact relation · confidence ≥ 8 · binding assay</em></div>
      <button className="primary model-lab-run" onClick={buildSnapshot} disabled={!enabled || Boolean(busy) || Boolean(snapshot)}>{busy === "snapshot" ? "Retrieving and freezing evidence…" : snapshot ? "Immutable snapshot created" : "Create real ChEMBL snapshot"}</button>
      {!enabled && <p className="model-lab-lock">Local operator must enable <code>OSIEL_MODEL_LAB_ENABLED=true</code>. The hosted interface will never invent rows or metrics.</p>}
    </section>

    {(busy || snapshot || model) && <section className="module-card model-lab-trace">
      <div className="card-title"><div><span>VISIBLE COMPUTATION TRACE</span><h2>{busy ? stages[Math.min(Math.max(stage,0),stages.length-1)] : model ? "Training and evaluation complete" : "Dataset snapshot complete"}</h2></div><b>{busy ? "RUNNING" : "INSPECTABLE"}</b></div>
      <ol>{stages.map((label,index) => <li key={label} className={index < stage || stage === stages.length ? "done" : index === stage ? "active" : "waiting"}><i>{index < stage || stage === stages.length ? "✓" : index + 1}</i><span><b>{label}</b><small>{index === 3 ? "No Bemis–Murcko scaffold may cross a split" : index === 6 ? "No training-row reuse in final metrics" : "Recorded in immutable run lineage"}</small></span></li>)}</ol>
    </section>}

    {error && <div className="model-lab-error"><b>Workflow stopped safely</b><span>{error}</span></div>}

    {snapshot && <section className="module-card model-snapshot-result">
      <div className="card-title"><div><span>IMMUTABLE DATASET</span><h2>{snapshot.target_label} · {snapshot.standard_type} · {snapshot.source_release}</h2></div><b className={snapshot.status}>{snapshot.status.toUpperCase()}</b></div>
      <div className="model-stat-grid"><div><span>RETAINED</span><strong>{snapshot.record_count}</strong><small>unique structures</small></div><div><span>ACTIVE / INACTIVE</span><strong>{snapshot.active_count} / {snapshot.inactive_count}</strong><small>grey zone excluded</small></div><div><span>SCAFFOLDS</span><strong>{snapshot.unique_scaffold_count}</strong><small>split groups</small></div><div><span>REMOVED</span><strong>{snapshot.ambiguous_removed + snapshot.invalid_removed + snapshot.duplicate_removed + snapshot.conflict_removed}</strong><small>ambiguous, invalid, duplicate, conflict</small></div></div>
      <div className="snapshot-proof"><span>Raw source <code>{snapshot.raw_sha256}</code></span><span>Normalized set <code>{snapshot.normalized_sha256}</code></span></div>
      <button className="primary model-lab-run" onClick={train} disabled={snapshot.status !== "ready" || Boolean(busy) || Boolean(model)}>{busy === "train" ? "Training and evaluating…" : model ? "Frozen evaluation complete" : "Train scaffold-safe baseline"}</button>
    </section>}

    {model && <>
      <section className="module-card model-evaluation">
        <div className="card-title"><div><span>FROZEN TEST EVALUATION</span><h2>{model.model_name}</h2></div><b className={model.evaluation_gate.includes("passed") ? "passed" : "failed"}>{model.evaluation_gate.replaceAll("-"," ")}</b></div>
        <div className="split-strip"><div style={{width:`${splitTotal ? model.train_count/splitTotal*100 : 0}%`}}><b>TRAIN</b><span>{model.train_count} rows · {model.train_scaffolds} scaffolds</span></div><div style={{width:`${splitTotal ? model.calibration_count/splitTotal*100 : 0}%`}}><b>CALIBRATE</b><span>{model.calibration_count} rows</span></div><div style={{width:`${splitTotal ? model.test_count/splitTotal*100 : 0}%`}}><b>TEST</b><span>{model.test_count} rows · frozen</span></div></div>
        <div className="model-metrics"><div><span>AUROC</span><strong>{metrics?.auroc.toFixed(3) ?? "—"}</strong></div><div><span>AVERAGE PRECISION</span><strong>{metrics?.average_precision.toFixed(3) ?? "—"}</strong></div><div><span>BALANCED ACCURACY</span><strong>{percent(metrics?.balanced_accuracy)}</strong></div><div><span>BRIER SCORE</span><strong>{metrics?.brier_score.toFixed(3) ?? "—"}</strong></div><div><span>CALIBRATION ERROR</span><strong>{percent(metrics?.expected_calibration_error)}</strong></div><div><span>SCAFFOLD OVERLAP</span><strong>{model.scaffold_overlap_count}</strong></div></div>

        <div className={`model-promotion-lock ${approvedInfo?.approved ? "approved" : ""}`}>
          <i>{approvedInfo?.approved ? "✓" : "🛡️"}</i>
          <div>
            <b>{approvedInfo?.approved ? "Named Reviewer Qualification Recorded (Challenger Approved)" : "Governance Guardrail: Production Auto-Promotion Restricted"}</b>
            <span>
              {approvedInfo?.approved
                ? `Signed off by ${approvedInfo.reviewer}. Registered as Challenger in governance ledger (awaiting prospective assays before champion deployment).`
                : "Passing the engineering gate confirms scaffold isolation and calibration. Automatic replacement of the production champion is restricted until prospective assays and a named reviewer sign-off are recorded."}
            </span>
            {!approvedInfo?.approved && (
              <div style={{ marginTop: "8px", display: "flex", gap: "8px", alignItems: "center" }}>
                <button
                  type="button"
                  onClick={() => setShowReviewForm((v) => !v)}
                  style={{ padding: "4px 8px", fontSize: "10px", borderRadius: "5px", background: "#4338ca", color: "#fff", border: "none", cursor: "pointer", fontWeight: 700 }}
                >
                  {showReviewForm ? "Hide Review Sign-Off" : "Record Named Reviewer Sign-Off →"}
                </button>
              </div>
            )}
            {showReviewForm && !approvedInfo?.approved && (
              <div style={{ marginTop: "8px", display: "grid", gap: "6px", background: "#ffffff", padding: "8px", borderRadius: "6px", border: "1px solid #c7d2fe" }}>
                <label style={{ display: "grid", gap: "2px", fontSize: "10px", color: "#334155" }}>
                  <span>Named Reviewer:</span>
                  <input
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    style={{ padding: "4px 6px", fontSize: "11px", border: "1px solid #cbd5e1", borderRadius: "4px" }}
                  />
                </label>
                <label style={{ display: "grid", gap: "2px", fontSize: "10px", color: "#334155" }}>
                  <span>Reviewer Validation Notes:</span>
                  <input
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    style={{ padding: "4px 6px", fontSize: "11px", border: "1px solid #cbd5e1", borderRadius: "4px" }}
                  />
                </label>
                <button
                  type="button"
                  onClick={handleReviewModel}
                  disabled={busy === "approve"}
                  style={{ padding: "5px 10px", fontSize: "11px", borderRadius: "5px", background: "#059669", color: "#fff", border: "none", cursor: "pointer", fontWeight: 700, width: "max-content" }}
                >
                  {busy === "approve" ? "Auditing Sign-Off…" : "Submit Reviewer Sign-Off & Audit"}
                </button>
              </div>
            )}
          </div>
          <em>{approvedInfo?.approved ? "REVIEWED & AUDITED" : "POLICY ACTIVE"}</em>
        </div>

        <button className="primary model-lab-run" onClick={chooseNext} disabled={Boolean(busy)}>{busy === "active" ? "Calculating uncertainty and diversity…" : "Propose next compounds to test"}</button>
      </section>
    </>}

    {batch && <section className="module-card active-learning-result">
      <div className="card-title"><div><span>ACTIVE-LEARNING PROPOSAL</span><h2>{batch.suggestions.length} diverse, high-information candidates</h2></div><b>HUMAN APPROVAL REQUIRED</b></div>
      <div className="module-table"><table><thead><tr><th>#</th><th>Candidate</th><th>Activity hypothesis</th><th>Uncertainty</th><th>Nearest training</th><th>Diversity</th><th>Acquisition</th></tr></thead><tbody>{batch.suggestions.map((item) => <tr key={item.candidate_id}><td><b>{item.priority}</b></td><td><b>{item.display_name}</b><small>{item.candidate_id}</small></td><td>{percent(item.active_probability)}</td><td>{percent(item.uncertainty)}</td><td>{percent(item.nearest_training_similarity)}</td><td>{percent(item.diversity_to_selected)}</td><td><strong>{item.acquisition_score.toFixed(1)}</strong></td></tr>)}</tbody></table></div>
      <p className="ai-boundary">{batch.scientific_boundary} No laboratory run, procurement request or model update was started.</p>
    </section>}
  </div>;
}

