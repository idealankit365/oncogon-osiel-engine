"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AtomStyleSpec, GLViewer } from "3dmol";
import type { RankedCandidate } from "../lib/demo-data";
import {
  loadCompoundConformer,
  type CompoundConformer3D,
} from "../lib/osiel-client";

type Representation = "ball-stick" | "stick" | "spacefill";
type ColourMode = "Jmol" | "cyanCarbon" | "purpleCarbon" | "orangeCarbon";

const colourOptions: Array<{ value: ColourMode; label: string; swatch: string }> = [
  { value: "Jmol", label: "Element / CPK", swatch: "linear-gradient(135deg,#777 0 25%,#e94b4b 25% 50%,#4c7cf3 50% 75%,#f4f4f4 75%)" },
  { value: "cyanCarbon", label: "Cyan carbon", swatch: "#18c8c8" },
  { value: "purpleCarbon", label: "Purple carbon", swatch: "#8b63e6" },
  { value: "orangeCarbon", label: "Orange carbon", swatch: "#ed9b35" },
];

function molecularStyle(
  representation: Representation,
  colours: ColourMode,
): AtomStyleSpec {
  if (representation === "stick") {
    return { stick: { radius: 0.19, colorscheme: colours, aromaticStyle: "circle" } };
  }
  if (representation === "spacefill") {
    return { sphere: { scale: 0.92, colorscheme: colours } };
  }
  return {
    stick: { radius: 0.16, colorscheme: colours, aromaticStyle: "circle" },
    sphere: { scale: 0.28, colorscheme: colours },
  };
}

export function Compound3DViewer({
  candidate,
  experimentId,
  resultStatus,
}: {
  candidate: RankedCandidate;
  experimentId: string;
  resultStatus: "completed" | "warning" | "failed" | "cancelled";
}) {
  const host = useRef<HTMLDivElement | null>(null);
  const viewer = useRef<GLViewer | null>(null);
  const [conformer, setConformer] = useState<CompoundConformer3D | null>(null);
  const [sourceLabel, setSourceLabel] = useState("Resolving Python conformer…");
  const [backendConnected, setBackendConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [representation, setRepresentation] = useState<Representation>("ball-stick");
  const [colours, setColours] = useState<ColourMode>("Jmol");
  const [showHydrogens, setShowHydrogens] = useState(true);
  const [spinning, setSpinning] = useState(false);
  const [hoveredAtom, setHoveredAtom] = useState("Hover an atom to inspect its element");

  useEffect(() => {
    let active = true;
    loadCompoundConformer(candidate.compound_id, experimentId).then((result) => {
      if (!active) return;
      setConformer(result.conformer);
      setBackendConnected(result.backendConnected);
      setSourceLabel(result.sourceLabel);
      setError(result.error);
      setLoading(false);
    });
    return () => { active = false; };
  }, [candidate.compound_id, experimentId]);

  const applyStyle = useCallback(() => {
    if (!viewer.current) return;
    viewer.current.setStyle({}, molecularStyle(representation, colours));
    if (!showHydrogens) {
      viewer.current.setStyle(
        { elem: "H" },
        { stick: { hidden: true }, sphere: { hidden: true } },
      );
    }
    viewer.current.render();
  }, [colours, representation, showHydrogens]);

  useEffect(() => {
    if (!conformer || !host.current) return;
    let disposed = false;
    let resizeObserver: ResizeObserver | undefined;
    void import("3dmol").then(($3Dmol) => {
      if (disposed || !host.current) return;
      const element = host.current;
      const instance = $3Dmol.createViewer(element, {
        backgroundColor: "#07111f",
        antialias: true,
      });
      instance.addModel(conformer.mol_block, "sdf");
      instance.setStyle({}, molecularStyle("ball-stick", "Jmol"));
      instance.setHoverable(
        {},
        true,
        (atom: { elem?: string; serial?: number }) => {
          setHoveredAtom(`${atom.elem ?? "Atom"} · index ${atom.serial ?? "—"}`);
        },
        () => setHoveredAtom("Hover an atom to inspect its element"),
      );
      instance.zoomTo({}, 0);
      instance.render();
      viewer.current = instance;
      resizeObserver = new ResizeObserver(() => instance.resize());
      resizeObserver.observe(element);
    }).catch(() => setError("The WebGL molecular viewer could not be initialized."));
    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      viewer.current?.spin(false);
      viewer.current?.clear();
      viewer.current = null;
    };
  }, [conformer]);

  useEffect(() => { applyStyle(); }, [applyStyle]);

  function toggleSpin() {
    if (!viewer.current) return;
    const next = !spinning;
    viewer.current.spin(next ? "y" : false, 0.7);
    setSpinning(next);
  }

  if (loading) {
    return <article className="molecule-viewer loading"><div className="molecule-loader"><i/><b>Generating 3D coordinates</b><span>Resolving canonical identity → ETKDGv3 → force-field optimization → checksum</span></div></article>;
  }
  if (!conformer || error) {
    return <article className="molecule-viewer unavailable"><b>3D structure unavailable</b><span>{error}</span></article>;
  }

  return <section className="molecule-workbench">
    <div className="molecule-toolbar">
      <div className="molecule-identity">
        <span>POST-EXPERIMENT STRUCTURE · {experimentId}</span>
        <h2>{candidate.display_name}</h2>
        <p>{candidate.compound_id} · {candidate.formula} · result {resultStatus}</p>
      </div>
      <div className="molecule-source">
        <i className={backendConnected ? "live" : "bundled"}/>
        <span><b>{sourceLabel}</b><small>SHA-256 {conformer.sha256.slice(0, 14)}…</small></span>
      </div>
    </div>
    <div className="molecule-layout">
      <aside className="molecule-controls">
        <fieldset>
          <legend>Representation</legend>
          {([
            ["ball-stick", "Ball + stick"],
            ["stick", "Stick"],
            ["spacefill", "Space filling"],
          ] as Array<[Representation, string]>).map(([value, label]) => <button key={value} className={representation === value ? "active" : ""} onClick={() => setRepresentation(value)}>{label}</button>)}
        </fieldset>
        <fieldset>
          <legend>Colour atoms</legend>
          {colourOptions.map((option) => <button key={option.value} className={colours === option.value ? "active" : ""} onClick={() => setColours(option.value)}><i style={{ background: option.swatch }}/>{option.label}</button>)}
        </fieldset>
        <label className="hydrogen-toggle"><input type="checkbox" checked={showHydrogens} onChange={(event) => setShowHydrogens(event.target.checked)}/><span>Show hydrogens</span></label>
      </aside>
      <div className="molecule-stage-wrap">
        <div className="molecule-stage" ref={host} aria-label={`Interactive 3D molecular structure of ${candidate.display_name}`}/>
        <div className="molecule-stage-help"><span>Drag to rotate · wheel or pinch to zoom · right-drag to move</span><b>{hoveredAtom}</b></div>
        <div className="molecule-camera">
          <button title="Zoom in" onClick={() => viewer.current?.zoom(1.35, 250)}>＋</button>
          <button title="Zoom out" onClick={() => viewer.current?.zoom(0.74, 250)}>−</button>
          <button title="Rotate left" onClick={() => viewer.current?.rotate(-20, "y", 250)}>↶</button>
          <button title="Rotate right" onClick={() => viewer.current?.rotate(20, "y", 250)}>↷</button>
          <button className={spinning ? "active" : ""} title="Toggle spin" onClick={toggleSpin}>{spinning ? "Stop" : "Spin"}</button>
          <button title="Reset view" onClick={() => viewer.current?.zoomTo({}, 350)}>Reset</button>
        </div>
      </div>
      <aside className="molecule-metadata">
        <span>COMPUTED GEOMETRY</span>
        <dl>
          <div><dt>Coordinates</dt><dd>{conformer.coordinate_method}</dd></div>
          <div><dt>Optimization</dt><dd>{conformer.optimization_method} · {conformer.optimization_converged ? "converged" : "not converged"}</dd></div>
          <div><dt>Energy</dt><dd>{conformer.conformer_energy_kcal_mol === null ? "Not available" : `${conformer.conformer_energy_kcal_mol.toFixed(3)} kcal/mol`}</dd></div>
          <div><dt>Atoms</dt><dd>{conformer.atom_count} total · {conformer.heavy_atom_count} heavy</dd></div>
          <div><dt>Seed</dt><dd>{conformer.random_seed}</dd></div>
          <div><dt>Engine</dt><dd>RDKit {conformer.rdkit_version}</dd></div>
        </dl>
        <details><summary>Canonical SMILES</summary><code>{conformer.canonical_smiles}</code></details>
        {conformer.warnings.length > 0 && <div className="molecule-warning"><b>Geometry warning</b>{conformer.warnings.map((warning) => <span key={warning}>{warning}</span>)}</div>}
      </aside>
    </div>
    <div className="molecule-boundary"><b>What this means</b><span>{conformer.scientific_boundary} Changing colour changes visualization only; it does not change the molecule or experimental result.</span></div>
  </section>;
}
