"use client";

import { useEffect, useState } from "react";
import {
  getBackendJson,
  runDockingBenchmark,
  runVinaDocking,
  type DockingBenchmarkRun,
  type VinaDockingInput,
  type VinaDockingJob,
} from "../lib/osiel-client";

type Props = { openDiscoveryRunId: string | null };

const initialBox = {
  center_x: 0,
  center_y: 0,
  center_z: 0,
  size_x: 20,
  size_y: 20,
  size_z: 20,
};

async function toBase64(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const block = 0x8000;
  let binary = "";
  for (let index = 0; index < bytes.length; index += block) {
    binary += String.fromCharCode(...bytes.subarray(index, index + block));
  }
  return window.btoa(binary);
}

function downloadOutput(job: VinaDockingJob) {
  if (!job.output_pdbqt_base64 || !job.output_filename) return;
  const binary = window.atob(job.output_pdbqt_base64);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes], { type: "chemical/x-pdbqt" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = job.output_filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function VinaRunner({ openDiscoveryRunId }: Props) {
  const [capability, setCapability] = useState<{ operator_enabled: boolean; binding_available: boolean } | null>(null);
  useEffect(() => { getBackendJson<{ operator_enabled: boolean; binding_available: boolean }>("/v1/docking/capabilities").then(setCapability).catch(() => setCapability(null)); }, []);
  const [receptor, setReceptor] = useState<File | null>(null);
  const [ligand, setLigand] = useState<File | null>(null);
  const [box, setBox] = useState(initialBox);
  const [exhaustiveness, setExhaustiveness] = useState(8);
  const [numModes, setNumModes] = useState(9);
  const [cpu, setCpu] = useState(1);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [job, setJob] = useState<VinaDockingJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [referenceLigand, setReferenceLigand] = useState<File | null>(null);
  const [benchmark, setBenchmark] = useState<DockingBenchmarkRun | null>(null);
  const [benchmarkRunning, setBenchmarkRunning] = useState(false);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);

  function setBoxValue(key: keyof typeof initialBox, value: number) {
    setBox((current) => ({ ...current, [key]: value }));
  }

  async function execute() {
    if (!receptor || !ligand || running) {
      if (!receptor || !ligand) setError("Choose both a prepared receptor PDBQT and a prepared ligand PDBQT.");
      return;
    }
    setRunning(true);
    setJob(null);
    setBenchmark(null);
    setReferenceLigand(null);
    setError(null);
    setProgress(8);
    const timer = window.setInterval(() => setProgress((value) => Math.min(92, value + 7)), 650);
    try {
      const [receptorBase64, ligandBase64] = await Promise.all([toBase64(receptor), toBase64(ligand)]);
      const input: VinaDockingInput = {
        receptor_filename: receptor.name,
        receptor_content_base64: receptorBase64,
        ligand_filename: ligand.name,
        ligand_content_base64: ligandBase64,
        box,
        scoring_function: "vina",
        exhaustiveness,
        num_modes: numModes,
        energy_range: 3,
        cpu,
        seed: 20260822,
        timeout_seconds: 600,
        open_discovery_run_id: openDiscoveryRunId || null,
      };
      const response = await runVinaDocking(input);
      setJob(response.job);
      setError(response.error);
      setProgress(response.job ? 100 : 0);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Docking request could not be prepared.");
      setProgress(0);
    } finally {
      window.clearInterval(timer);
      setRunning(false);
    }
  }

  async function benchmarkPoseRecovery() {
    if (!job || !referenceLigand || benchmarkRunning) return;
    setBenchmarkRunning(true);
    setBenchmark(null);
    setBenchmarkError(null);
    const result = await runDockingBenchmark({
      docking_job_id: job.job_id,
      reference_ligand_filename: referenceLigand.name,
      reference_ligand_content_base64: await toBase64(referenceLigand),
      rmsd_pass_threshold_angstrom: 2.0,
    });
    setBenchmark(result.benchmark);
    setBenchmarkError(result.error);
    setBenchmarkRunning(false);
  }

  return <section className="module-card vina-runner">
    <div className="card-title"><div><span>REAL DOCKING WORKER</span><h2>AutoDock Vina 1.2.7 execution</h2></div><b className="vina-real">REAL PROCESS · NO SIMULATED SCORE</b></div>
    <div className="vina-boundary"><b>Prepared inputs only</b><span>OSIEL does not guess protonation, charges, tautomers, missing residues, waters, cofactors, or the binding pocket. Prepare and review PDBQT files before this step.</span></div>
    <div className="vina-input-grid">
      <label className={receptor ? "loaded" : ""}><span>1 · Rigid receptor PDBQT</span><input type="file" accept=".pdbqt" onChange={(event) => setReceptor(event.target.files?.[0] ?? null)}/><b>{receptor ? `${receptor.name} · ${(receptor.size / 1024).toFixed(1)} KB` : "Choose prepared receptor"}</b><small>Protein/receptor with reviewed atoms, hydrogens and AutoDock charges.</small></label>
      <label className={ligand ? "loaded" : ""}><span>2 · Ligand PDBQT</span><input type="file" accept=".pdbqt" onChange={(event) => setLigand(event.target.files?.[0] ?? null)}/><b>{ligand ? `${ligand.name} · ${(ligand.size / 1024).toFixed(1)} KB` : "Choose prepared ligand"}</b><small>Must contain ROOT, ENDROOT, TORSDOF and valid AutoDock atom types.</small></label>
    </div>
    <div className="vina-box-panel">
      <div><span>3 · SEARCH BOX CENTRE (Å)</span><div>{(["center_x", "center_y", "center_z"] as const).map((key) => <label key={key}><b>{key.at(-1)?.toUpperCase()}</b><input type="number" step="0.001" value={box[key]} onChange={(event) => setBoxValue(key, Number(event.target.value))}/></label>)}</div></div>
      <div><span>4 · SEARCH BOX SIZE (Å)</span><div>{(["size_x", "size_y", "size_z"] as const).map((key) => <label key={key}><b>{key.at(-1)?.toUpperCase()}</b><input type="number" min="6" max="50" step="0.5" value={box[key]} onChange={(event) => setBoxValue(key, Number(event.target.value))}/></label>)}</div></div>
      <label><span>EXHAUSTIVENESS</span><select value={exhaustiveness} onChange={(event) => setExhaustiveness(Number(event.target.value))}><option value={1}>1 · smoke test</option><option value={8}>8 · baseline</option><option value={16}>16 · deeper</option><option value={32}>32 · expensive</option></select></label>
      <label><span>POSES</span><select value={numModes} onChange={(event) => setNumModes(Number(event.target.value))}><option value={3}>3</option><option value={5}>5</option><option value={9}>9</option><option value={20}>20</option></select></label>
      <label><span>CPU</span><select value={cpu} onChange={(event) => setCpu(Number(event.target.value))}><option value={1}>1</option><option value={2}>2</option><option value={4}>4</option></select></label>
    </div>
    {capability && (!capability.operator_enabled || !capability.binding_available) && <p className="model-lab-lock">AutoDock Vina integration is not enabled on this host. No docking score will be generated.</p>}
    <button className="primary vina-run-button" onClick={execute} disabled={running || !receptor || !ligand || !capability?.operator_enabled || !capability.binding_available} title={!capability?.operator_enabled || !capability?.binding_available ? "Docking is not enabled in this environment" : undefined}>{running ? "Docking in progress…" : "Run AutoDock Vina"}</button>
    {(running || progress > 0) && <div className="vina-progress"><i style={{ width: `${progress}%` }}/><span>{running ? "Bounded child process running · timeout 600 s" : job ? "Worker completed and artifacts retained by SHA-256" : "Waiting"}</span></div>}
    {error && <div className="vina-error"><b>Docking did not run</b><span>{error}</span></div>}
    {job && <div className={`vina-result ${job.status}`}>
      <div className="vina-result-head"><div><span>{job.engine} {job.engine_version}</span><h3>{job.status === "completed" ? `${job.num_modes_returned} ranked pose${job.num_modes_returned === 1 ? "" : "s"}` : job.status}</h3></div><div><span>Job</span><code>{job.job_id}</code></div><div><span>Duration</span><b>{job.duration_seconds.toFixed(2)} s</b></div>{job.output_pdbqt_base64 && <button onClick={() => downloadOutput(job)}>Download poses</button>}</div>
      {job.error && <div className="vina-job-error">{job.error}</div>}
      {job.poses.length > 0 && <div className="vina-pose-grid">{job.poses.map((pose) => <article key={pose.rank}><span>POSE {pose.rank}</span><strong>{pose.affinity_kcal_mol.toFixed(3)}</strong><small>kcal/mol · Vina score</small><code>{pose.raw_energy_terms.join(" · ")}</code></article>)}</div>}
      <div className="vina-checksums"><span>Receptor <code>{job.receptor_sha256}</code></span><span>Ligand <code>{job.ligand_sha256}</code></span>{job.output_sha256 && <span>Output <code>{job.output_sha256}</code></span>}</div>
      <details><summary>Warnings, command manifest and interpretation boundary</summary><ul>{job.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul><pre>{job.command_manifest.join("\n")}</pre><p>{job.scientific_boundary}</p></details>
      {job.status === "completed" && <section className="vina-benchmark">
        <div><span>REDOCKING QUALIFICATION</span><h3>Can this setup recover the known crystallographic pose?</h3><p>Upload the exact prepared co-crystal ligand using the same heavy-atom order. OSIEL aligns each returned pose and calculates heavy-atom RMSD.</p></div>
        <label className={referenceLigand ? "loaded" : ""}><input type="file" accept=".pdbqt" onChange={(event) => { setReferenceLigand(event.target.files?.[0] ?? null); setBenchmark(null); setBenchmarkError(null); }}/><b>{referenceLigand ? referenceLigand.name : "Choose reference ligand PDBQT"}</b><small>Pass threshold · RMSD ≤ 2.0 Å</small></label>
        <button onClick={benchmarkPoseRecovery} disabled={!capability?.operator_enabled || !capability.binding_available || !referenceLigand || benchmarkRunning} title={!capability?.operator_enabled || !capability?.binding_available ? "Docking is not enabled in this environment" : undefined}>{benchmarkRunning ? "Aligning poses and calculating RMSD…" : "Run redocking benchmark"}</button>
        {benchmarkError && <div className="vina-error"><b>Benchmark stopped safely</b><span>{benchmarkError}</span></div>}
        {benchmark && <div className={`vina-benchmark-result ${benchmark.status}`}><div><span>POSE RECOVERY</span><strong>{benchmark.status.toUpperCase()}</strong></div><div><span>BEST POSE</span><strong>{benchmark.best_pose_rank ?? "—"}</strong></div><div><span>BEST RMSD</span><strong>{benchmark.best_rmsd_angstrom?.toFixed(3) ?? "—"} Å</strong></div><div><span>AFFINITY SCORING</span><strong>NOT QUALIFIED</strong></div><p>{benchmark.scientific_boundary}</p></div>}
      </section>}
    </div>}
  </section>;
}
