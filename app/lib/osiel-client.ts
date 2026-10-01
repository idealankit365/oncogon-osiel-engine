import { demoCandidates, renumber } from "./demo-data";
import type { RankedCandidate } from "./demo-data";

const API_BASE = (process.env.NEXT_PUBLIC_OSIEL_API_URL ?? "").replace(/\/$/, "");

export type DataConnectorCapability = {
  source_code: string;
  source_name: string;
  connector_type: string;
  configured: boolean;
  live_enabled: boolean;
  landing_url?: string;
  documentation_url?: string;
  purpose?: string;
  licence_note?: string;
  checksum_configured?: boolean;
  requires_api_key?: boolean;
};

export type DataConnectorResult = {
  job_id?: string;
  source_code: string;
  source_name?: string;
  release_id?: string;
  status?: string;
  filename?: string;
  byte_count?: number;
  sha256?: string;
  checksum_verified?: boolean;
  record_count?: number;
  record_preview?: { records?: Array<Record<string, unknown>> } | Array<Record<string, unknown>>;
  provider_response?: unknown;
  error?: string;
  training_eligible?: boolean;
  next_gate?: string;
};

const connectorFallback: DataConnectorCapability[] = [
  ["nci60", "NCI-60 / CellMiner", "approved-bulk-release", "Cancer-cell-line compound responses"],
  ["tdc", "Therapeutics Data Commons", "official-python-library", "Drug-discovery benchmark datasets"],
  ["coconut", "COCONUT 2.0", "approved-bulk-release", "Natural-product structures and annotations"],
  ["npass", "NPASS", "approved-bulk-release", "Natural-product activities, targets and species"],
  ["anpdb", "African Natural Products Database", "approved-bulk-release", "African compounds, organisms and literature"],
  ["lotus", "LOTUS", "approved-bulk-release", "Natural-product occurrence and organism provenance"],
  ["tox21", "Tox21", "approved-bulk-release", "Public high-throughput toxicity assays"],
  ["toxcast", "EPA ToxCast", "approved-bulk-release", "EPA invitrodb toxicity and pathway endpoints"],
  ["uniprot", "UniProt", "official-rest-api", "Protein identity, sequence and cross-references"],
  ["chemspace", "Chemspace", "licensed-api", "Supplier availability and procurement hand-off"],
].map(([source_code, source_name, connector_type, purpose]) => ({
  source_code, source_name, connector_type, purpose, configured: false, live_enabled: false,
}));

export async function loadDataConnectors(): Promise<{ items: DataConnectorCapability[]; backendConnected: boolean }> {
  try {
    const response = await apiFetch("/v1/data-connectors");
    if (!response.ok) throw new Error(`Connector API returned ${response.status}`);
    return { items: await response.json() as DataConnectorCapability[], backendConnected: true };
  } catch {
    return { items: connectorFallback, backendConnected: false };
  }
}

export async function fetchBulkDataSource(sourceCode: string, releaseId: string): Promise<DataConnectorResult> {
  const response = await apiFetch(`/v1/data-connectors/bulk/${encodeURIComponent(sourceCode)}/fetch`, {
    method: "POST",
    headers: { "X-OSIEL-Actor": "workbench-researcher", "X-OSIEL-Role": "researcher" },
    body: JSON.stringify({ release_id: releaseId, max_preview_records: 25 }),
  }, 120_000);
  if (!response.ok) throw new Error(await response.text());
  return await response.json() as DataConnectorResult;
}

export async function fetchTDCData(): Promise<DataConnectorResult> {
  const response = await apiFetch("/v1/data-connectors/tdc/fetch", {
    method: "POST",
    headers: { "X-OSIEL-Actor": "workbench-researcher", "X-OSIEL-Role": "researcher" },
    body: JSON.stringify({ group: "tox", dataset: "hERG", max_records: 1000 }),
  }, 120_000);
  if (!response.ok) throw new Error(await response.text());
  return await response.json() as DataConnectorResult;
}

export async function searchUniProtData(query: string): Promise<DataConnectorResult> {
  const response = await apiFetch("/v1/data-connectors/uniprot/search", {
    method: "POST",
    headers: { "X-OSIEL-Actor": "workbench-researcher", "X-OSIEL-Role": "researcher" },
    body: JSON.stringify({ query, limit: 10, reviewed_only: true }),
  });
  if (!response.ok) throw new Error(await response.text());
  const records = await response.json() as Array<Record<string, unknown>>;
  return { source_code: "uniprot", source_name: "UniProt", status: "completed", record_count: records.length, record_preview: records, training_eligible: false };
}

export async function searchChemspaceData(query: string): Promise<DataConnectorResult> {
  const response = await apiFetch("/v1/data-connectors/chemspace/search", {
    method: "POST",
    headers: { "X-OSIEL-Actor": "workbench-researcher", "X-OSIEL-Role": "researcher" },
    body: JSON.stringify({ query, limit: 25 }),
  });
  if (!response.ok) throw new Error(await response.text());
  return await response.json() as DataConnectorResult;
}

type ApiCompound = {
  compound_id: string;
  display_name: string;
  origin: string;
  source_name: string;
  evidence_grade: "A" | "B" | "C" | "D";
  descriptors: { molecular_formula: string };
};

type ApiRanked = {
  rank: number;
  compound_id: string;
  display_name: string;
  score: number;
  eligibility: "eligible" | "flagged" | "excluded";
  hard_filter_reasons: string[];
  prediction: {
    predicted_activity: number;
    predicted_ic50_um: number;
    predicted_selectivity_index: number;
    confidence: number;
    uncertainty: number;
    applicability_domain: "inside" | "borderline" | "outside";
    evidence_summary: string;
    admet: Array<{
      code: string;
      label: string;
      predicted_value: number | string;
      classification: string;
    }>;
  };
};

type ApiRankingRun = {
  ranking_run_id: string;
  ranked: ApiRanked[];
};

export type WorkspaceResult = {
  candidates: RankedCandidate[];
  backendConnected: boolean;
  rankingRunId: string;
  message: string;
};

export type DryRunResult = {
  experimentId: string;
  resultId: string;
  qcStatus: string;
  observationCount: number;
  estimatedIc50: Record<string, number>;
  backendConnected: boolean;
  disclaimer: string;
};

export type CompoundConformer3D = {
  compound_id: string;
  registry_compound_id?: string;
  display_name: string;
  canonical_smiles: string;
  mol_block: string;
  format: "mol-v2000";
  coordinate_method: string;
  optimization_method: "MMFF94" | "UFF" | "none";
  optimization_converged: boolean;
  conformer_energy_kcal_mol: number | null;
  random_seed: number;
  includes_hydrogens: boolean;
  atom_count: number;
  heavy_atom_count: number;
  rdkit_version: string;
  sha256: string;
  object_uri?: string;
  warnings: string[];
  scientific_boundary: string;
  source_mode?: "bundled-rdkit-reference";
};

type DemoConformerBundle = {
  schema_version: string;
  records: CompoundConformer3D[];
};

async function apiFetch(path: string, init?: RequestInit, timeoutMs = 30_000): Promise<Response> {
  if (!API_BASE) throw new Error("No backend URL configured");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } finally {
    clearTimeout(timeout);
  }
}

export async function loadCompoundConformer(
  compoundId: string,
  experimentId?: string,
): Promise<{
  conformer: CompoundConformer3D | null;
  backendConnected: boolean;
  sourceLabel: string;
  error: string | null;
}> {
  try {
    const parameters = new URLSearchParams({ include_hydrogens: "true" });
    if (experimentId) parameters.set("experiment_id", experimentId);
    const response = await apiFetch(
      `/v1/compounds/${encodeURIComponent(compoundId)}/conformer-3d?${parameters.toString()}`,
      { headers: { "X-OSIEL-Actor": "workbench-researcher" } },
      60_000,
    );
    if (!response.ok) throw new Error(`Conformer API returned ${response.status}`);
    return {
      conformer: await response.json() as CompoundConformer3D,
      backendConnected: true,
      sourceLabel: "Live Python · RDKit ETKDGv3",
      error: null,
    };
  } catch {
    try {
      const response = await fetch("/demo-conformers.json", { cache: "force-cache" });
      if (!response.ok) throw new Error(`Bundle returned ${response.status}`);
      const bundle = await response.json() as DemoConformerBundle;
      const conformer = bundle.records.find((item) => (
        item.compound_id === compoundId || item.registry_compound_id === compoundId
      ));
      if (!conformer) throw new Error("Compound is not present in the bundled reference set");
      return {
        conformer,
        backendConnected: false,
        sourceLabel: "Bundled Python-generated RDKit conformer",
        error: null,
      };
    } catch {
      return {
        conformer: null,
        backendConnected: false,
        sourceLabel: "Unavailable",
        error: "No verified 3D conformer is available for this compound. Connect the Python API; no structure was fabricated.",
      };
    }
  }
}

function fallbackFor(origin: "all" | "natural" | "synthetic"): RankedCandidate[] {
  const items = origin === "all"
    ? demoCandidates
    : demoCandidates.filter((item) => item.origin === origin);
  return renumber(items);
}

function classify(value: string): "good" | "watch" | "risk" {
  const normalized = value.toLowerCase();
  if (normalized.includes("low") || normalized.includes("good") || normalized.includes("safe")) return "good";
  if (normalized.includes("high") || normalized.includes("risk") || normalized.includes("poor")) return "risk";
  return "watch";
}

export async function loadRankedWorkspace(
  cancerType: string,
  cellLine: string,
  origin: "all" | "natural" | "synthetic",
): Promise<WorkspaceResult> {
  try {
    const compoundResponse = await apiFetch("/v1/compounds?limit=36");
    if (!compoundResponse.ok) throw new Error(`Compound API returned ${compoundResponse.status}`);
    const compounds = (await compoundResponse.json()) as ApiCompound[];
    const candidates = compounds
      .filter((item) => origin === "all" || item.origin === origin)
      .slice(0, 20);
    if (candidates.length < 2) throw new Error("Not enough candidates for ranking");

    const response = await apiFetch("/v1/rankings", {
      method: "POST",
      body: JSON.stringify({
        compound_ids: candidates.map((item) => item.compound_id),
        cancer_type: cancerType,
        cell_line: cellLine,
        diversity_threshold: 0.82,
      }),
    });
    if (!response.ok) throw new Error(`Ranking API returned ${response.status}`);
    const ranking = (await response.json()) as ApiRankingRun;
    const byId = new Map(candidates.map((item) => [item.compound_id, item]));
    const mapped = ranking.ranked.map((item): RankedCandidate => {
      const compound = byId.get(item.compound_id);
      return {
        rank: item.rank,
        compound_id: item.compound_id,
        display_name: item.display_name,
        origin: compound?.origin === "natural" || compound?.origin === "synthetic" ? compound.origin : "reference",
        formula: compound?.descriptors.molecular_formula ?? "—",
        score: item.score,
        activity: Math.round(item.prediction.predicted_activity * 100),
        selectivity: Math.round(Math.min(1, item.prediction.predicted_selectivity_index / 30) * 100),
        confidence: Math.round(item.prediction.confidence * 100),
        uncertainty: Math.round(item.prediction.uncertainty * 100),
        predicted_ic50_um: item.prediction.predicted_ic50_um,
        evidence_grade: compound?.evidence_grade ?? "D",
        applicability_domain: item.prediction.applicability_domain,
        source: compound?.source_name ?? "OSIEL compound registry",
        note: item.hard_filter_reasons[0] ?? item.prediction.evidence_summary,
        admet: item.prediction.admet.slice(0, 4).map((endpoint) => ({
          code: endpoint.code,
          label: endpoint.label,
          value: Math.round(Number(endpoint.predicted_value) * 100),
          className: classify(endpoint.classification),
        })),
      };
    });
    return {
      candidates: mapped,
      backendConnected: true,
      rankingRunId: ranking.ranking_run_id,
      message: `Python engine ranked ${mapped.length} compounds.`,
    };
  } catch {
    return {
      candidates: fallbackFor(origin),
      backendConnected: false,
      rankingRunId: "RNK-EMBEDDED-DEMO",
      message: "Embedded deterministic demo loaded. Set NEXT_PUBLIC_OSIEL_API_URL for live Python calls.",
    };
  }
}

export async function runDryExperiment(
  compoundIds: string[],
  cancerType: string,
  cellLine: string,
  rankingRunId: string,
): Promise<DryRunResult> {
  try {
    const created = await apiFetch("/v1/experiments", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher", "X-OSIEL-Role": "researcher" },
      body: JSON.stringify({
        title: `${cancerType} computational dose-response dry-run`,
        compound_ids: compoundIds,
        cancer_type: cancerType,
        cell_line: cellLine,
        assay_type: "CellTiter-Glo",
        endpoint: "IC50",
        dose_min_um: 0.01,
        dose_max_um: 30,
        dose_points: 8,
        replicates: 3,
        duration_hours: 72,
        positive_control: "Doxorubicin",
        negative_control: "Vehicle",
        source_ranking_run_id: rankingRunId.startsWith("RNK-") && !rankingRunId.includes("EMBEDDED") ? rankingRunId : null,
      }),
    });
    if (!created.ok) throw new Error(`Experiment API returned ${created.status}`);
    const experiment = (await created.json()) as { experiment_id: string };
    const response = await apiFetch(`/v1/experiments/${experiment.experiment_id}/simulate`, { method: "POST" });
    if (!response.ok) throw new Error(`Simulation API returned ${response.status}`);
    const result = (await response.json()) as {
      result_id: string;
      observations: unknown[];
      estimated_ic50_um: Record<string, number>;
      qc_status: string;
      disclaimer: string;
    };
    return {
      experimentId: experiment.experiment_id,
      resultId: result.result_id,
      qcStatus: result.qc_status,
      observationCount: result.observations.length,
      estimatedIc50: result.estimated_ic50_um,
      backendConnected: true,
      disclaimer: result.disclaimer,
    };
  } catch {
    const estimated = Object.fromEntries(
      compoundIds.map((id, index) => [id, Number((1.8 + index * 1.37).toFixed(2))]),
    );
    return {
      experimentId: "EXP-EMBEDDED-DRY-RUN",
      resultId: "RES-EMBEDDED-DRY-RUN",
      qcStatus: "passed",
      observationCount: compoundIds.length * 8 * 3,
      estimatedIc50: estimated,
      backendConnected: false,
      disclaimer: "Computational UI dry-run only. No physical assay or wet-lab measurement was performed.",
    };
  }
}

export type OpenDiscoveryInput = {
  disease: string;
  target_symbol: string | null;
  seed_compound_name: string | null;
  seed_smiles: string | null;
  pdb_id: string | null;
  uniprot_accession: string | null;
  candidate_limit: number;
  public_connectors: boolean;
};

export type OpenWorkflowEvent = {
  sequence: number;
  stage: string;
  label: string;
  status: "completed" | "completed-with-warning" | "skipped" | "failed";
  message: string;
  duration_ms: number;
  metrics: Record<string, string | number | boolean>;
  evidence_ids: string[];
};

export type OpenSourceEvidence = {
  evidence_id: string;
  source_code: string;
  source_name: string;
  mode: "local-registry" | "official-api" | "link-out" | "computation";
  status: "resolved" | "available" | "deferred" | "failed";
  url: string;
  statement: string;
  licence_note: string;
  source_record_id: string | null;
  retrieved_at: string;
};

export type OpenCandidate = {
  rank: number;
  compound_id: string;
  display_name: string;
  source_name: string;
  source_record_id: string;
  canonical_smiles: string;
  inchikey: string;
  similarity_to_seed: number;
  descriptors: {
    molecular_formula: string;
    molecular_weight: number;
    clogp: number;
    tpsa: number;
    h_bond_donors: number;
    h_bond_acceptors: number;
    rotatable_bonds: number;
    ring_count: number;
    fraction_csp3: number;
    qed: number;
  };
  lipinski_violations: string[];
  pains_alerts: string[];
  brenk_alerts: string[];
  nih_alerts: string[];
  quality_flags: string[];
  priority_score: number;
  score_components: Array<{
    code: string;
    label: string;
    normalized_value: number;
    weight: number;
    contribution: number;
    explanation: string;
  }>;
  disposition: "prioritize" | "review" | "deprioritize";
  disposition_reason: string;
};

export type OpenDiscoveryResult = {
  run_id: string;
  status: "completed" | "completed-with-warning" | "failed";
  execution_mode: "local-python" | "local-python-plus-public-apis";
  request: OpenDiscoveryInput;
  seed: {
    canonical_smiles: string;
    inchikey: string;
    descriptors: OpenCandidate["descriptors"];
    quality_flags: string[];
  };
  seed_name: string;
  events: OpenWorkflowEvent[];
  evidence: OpenSourceEvidence[];
  candidates: OpenCandidate[];
  docking: {
    status: "ready" | "not-ready" | "not-run";
    engine: string;
    executable_detected: boolean;
    receptor_id: string | null;
    required_inputs: string[];
    missing_inputs: string[];
    run_manifest: Record<string, string | number | boolean | null>;
    result_score_kcal_mol: number | null;
    scientific_boundary: string;
  };
  next_actions: string[];
  claim_boundary: string;
  created_at: string;
  backendConnected: boolean;
  modeMessage: string;
};

const referenceDescriptors: OpenCandidate["descriptors"] = {
  molecular_formula: "C15H10O5",
  molecular_weight: 270.24,
  clogp: 2.58,
  tpsa: 90.9,
  h_bond_donors: 3,
  h_bond_acceptors: 5,
  rotatable_bonds: 1,
  ring_count: 3,
  fraction_csp3: 0,
  qed: 0.63,
};

function fallbackOpenDiscovery(input: OpenDiscoveryInput): OpenDiscoveryResult {
  const now = new Date().toISOString();
  const names = ["NCI Reference 0108", "NCI Reference 0013", "Curcumin", "Tamoxifen", "Caffeine", "Aspirin", "Resveratrol", "5-Fluorouracil", "Catechin", "Apigenin", "Luteolin", "Quercetin"];
  const similarities = [0.20, 0.164, 0.152, 0.092, 0.09, 0.077, 0.068, 0.068, 0.067, 0.058, 0.057, 0.056];
  const candidates = names.slice(0, input.candidate_limit).map((name, index): OpenCandidate => {
    const similarity = similarities[index] ?? Math.max(0.12, 0.22 - index * 0.015);
    const qed = Math.max(0.35, referenceDescriptors.qed - index * 0.035);
    const score = Number((similarity * 45 + qed * 20 + 15 + 10 + 7.5).toFixed(2));
    return {
      rank: index + 1,
      compound_id: `EMBEDDED-${String(index + 1).padStart(3, "0")}`,
      display_name: name,
      source_name: "Embedded reference fixture",
      source_record_id: `FIXTURE-${index + 1}`,
      canonical_smiles: "Structure available from the connected Python engine",
      inchikey: `EMBEDDED-DEMO-${index + 1}`,
      similarity_to_seed: similarity,
      descriptors: { ...referenceDescriptors, qed },
      lipinski_violations: [],
      pains_alerts: index === 3 ? ["example review flag"] : [],
      brenk_alerts: [],
      nih_alerts: [],
      quality_flags: [],
      priority_score: score,
      score_components: [
        { code: "seed-similarity", label: "Seed similarity", normalized_value: similarity, weight: 0.45, contribution: Number((similarity * 45).toFixed(2)), explanation: "Embedded UI fixture; connect Python for a real RDKit Morgan similarity calculation." },
        { code: "qed", label: "QED", normalized_value: qed, weight: 0.2, contribution: Number((qed * 20).toFixed(2)), explanation: "Embedded UI fixture; connect Python for a real RDKit QED calculation." },
        { code: "lipinski", label: "Rule-of-Five adherence", normalized_value: 1, weight: 0.15, contribution: 15, explanation: "No example Rule-of-Five flag in this embedded fixture." },
        { code: "alerts", label: "Alert burden", normalized_value: index === 3 ? 0.67 : 1, weight: 0.1, contribution: index === 3 ? 6.7 : 10, explanation: "Example catalogue status; connect Python for RDKit alert matching." },
        { code: "source-evidence", label: "Source evidence completeness", normalized_value: 0.75, weight: 0.1, contribution: 7.5, explanation: "Reference-fixture provenance only." },
      ],
      disposition: index < 2 ? "review" : index > 4 ? "deprioritize" : "review",
      disposition_reason: "Embedded example only; rerun with the Python API before scientific review.",
    };
  });
  const stages = [
    ["target-evidence", "Resolve disease and target evidence", "Official Open Targets link prepared; no association data retrieved."],
    ["structure-resolution", "Resolve target structure", "No prepared receptor supplied; structure qualification remains open."],
    ["seed-resolution", "Resolve and standardize seed ligand", `${input.seed_compound_name || "Seed"} fixture resolved for the hosted demonstration.`],
    ["analogue-search", "Retrieve structural analogues", "Embedded reference panel loaded; public services were not crawled."],
    ["standardization", "Standardize and deduplicate candidates", "Reference-fixture identities loaded; connect Python for RDKit computation."],
    ["medchem-alerts", "Evaluate medicinal-chemistry alerts", "Example review flags displayed; connect Python for PAINS/Brenk/NIH matching."],
    ["transparent-ranking", "Rank screening candidates", "Five-component chemistry-priority formula displayed."],
    ["docking-readiness", "Check AutoDock Vina prerequisites", "Docking not run; qualified receptor, ligands, box and benchmark are missing."],
    ["procurement-handoff", "Prepare sourcing hand-off", "Chemspace link prepared; no order or availability claim made."],
    ["review-gate", "Require scientific review", "Human review remains mandatory."],
  ];
  return {
    run_id: "ODR-EMBEDDED-REFERENCE",
    status: "completed-with-warning",
    execution_mode: "local-python",
    request: input,
    seed: {
      canonical_smiles: input.seed_smiles || "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
      inchikey: "XGALLCVXEZPNRQ-UHFFFAOYSA-N",
      descriptors: { ...referenceDescriptors, molecular_formula: "C22H24ClFN4O3", molecular_weight: 446.91, clogp: 4.28, qed: 0.52 },
      quality_flags: [],
    },
    seed_name: input.seed_compound_name || "User-supplied seed",
    events: stages.map(([stage, label, message], index) => ({
      sequence: index + 1,
      stage,
      label,
      status: [1, 5, 7, 8].includes(index) ? "completed-with-warning" : "completed",
      message,
      duration_ms: 0,
      metrics: { embedded_fixture: true },
      evidence_ids: [],
    })),
    evidence: [
      { evidence_id: "EMB-E01", source_code: "open-targets", source_name: "Open Targets Platform", mode: "link-out", status: "deferred", url: `https://platform.opentargets.org/search?q=${encodeURIComponent(input.disease)}`, statement: "Official search link only; no live data retrieved in hosted fallback.", licence_note: "Preserve evidence provenance and retrieval date.", source_record_id: null, retrieved_at: now },
      { evidence_id: "EMB-E02", source_code: "zinc22", source_name: "ZINC22 / CartBlanche22", mode: "link-out", status: "deferred", url: "https://cartblanche22.docking.org/", statement: "Expansion source registered; no shared service was crawled.", licence_note: "Use approved export or deployment and follow service rules.", source_record_id: null, retrieved_at: now },
      { evidence_id: "EMB-E03", source_code: "chemspace", source_name: "Chemspace", mode: "link-out", status: "available", url: "https://chem-space.com/", statement: "Supplier search hand-off only; availability was not checked.", licence_note: "Current provider terms and API key apply.", source_record_id: null, retrieved_at: now },
    ],
    candidates,
    docking: {
      status: "not-run",
      engine: "AutoDock Vina",
      executable_detected: false,
      receptor_id: input.pdb_id || input.uniprot_accession,
      required_inputs: ["prepared receptor PDBQT", "prepared ligand PDBQT", "validated docking box", "redocking benchmark"],
      missing_inputs: ["Python worker and Vina executable", "prepared receptor PDBQT", "prepared ligand PDBQT", "validated docking box", "redocking benchmark"],
      run_manifest: { execute: false, candidate_count: candidates.length, random_seed: 20260822 },
      result_score_kcal_mol: null,
      scientific_boundary: "No docking score exists. A real Vina result would remain an approximate pose-ranking output, not efficacy evidence.",
    },
    next_actions: [
      "Connect NEXT_PUBLIC_OSIEL_API_URL to execute the Python/RDKit workflow.",
      "Review candidate identity, alert flags and score components with a medicinal chemist.",
      "Resolve and prepare a qualified receptor before any docking run.",
      "Verify supplier, salt, stereochemistry, purity and safety approval before ordering.",
    ],
    claim_boundary: "This embedded result demonstrates the interface only. It does not predict target binding, efficacy or safety, execute docking, place an order, or perform a laboratory experiment.",
    created_at: now,
    backendConnected: false,
    modeMessage: "Hosted embedded reference. Configure the Python API to run RDKit and optional official connectors.",
  };
}

export async function runOpenDiscovery(input: OpenDiscoveryInput): Promise<OpenDiscoveryResult> {
  try {
    const response = await apiFetch("/v1/open-discovery/runs", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher" },
      body: JSON.stringify(input),
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Open discovery API returned ${response.status}: ${detail}`);
    }
    const result = (await response.json()) as Omit<OpenDiscoveryResult, "backendConnected" | "modeMessage">;
    return {
      ...result,
      backendConnected: true,
      modeMessage: result.execution_mode === "local-python-plus-public-apis"
        ? "Python/RDKit engine completed with operator-enabled official public APIs."
        : "Python/RDKit engine completed against the versioned local reference registry.",
    };
  } catch {
    return fallbackOpenDiscovery(input);
  }
}

export type VinaDockingInput = {
  receptor_filename: string;
  receptor_content_base64: string;
  ligand_filename: string;
  ligand_content_base64: string;
  box: {
    center_x: number;
    center_y: number;
    center_z: number;
    size_x: number;
    size_y: number;
    size_z: number;
  };
  scoring_function: "vina" | "vinardo";
  exhaustiveness: number;
  num_modes: number;
  energy_range: number;
  cpu: number;
  seed: number;
  timeout_seconds: number;
  open_discovery_run_id: string | null;
};

export type VinaDockingJob = {
  job_id: string;
  status: "completed" | "blocked" | "failed" | "timed-out";
  engine: string;
  engine_version: string | null;
  scoring_function: "vina" | "vinardo";
  receptor_filename: string;
  receptor_sha256: string;
  receptor_object_uri: string;
  ligand_filename: string;
  ligand_sha256: string;
  ligand_object_uri: string;
  output_sha256: string | null;
  output_object_uri: string | null;
  output_filename: string | null;
  output_pdbqt_base64: string | null;
  box: VinaDockingInput["box"];
  exhaustiveness: number;
  num_modes_requested: number;
  num_modes_returned: number;
  energy_range: number;
  cpu: number;
  seed: number;
  duration_seconds: number;
  poses: Array<{ rank: number; affinity_kcal_mol: number; raw_energy_terms: number[] }>;
  warnings: string[];
  error: string | null;
  open_discovery_run_id: string | null;
  command_manifest: string[];
  scientific_boundary: string;
  created_at: string;
};

export type VinaDockingResult = {
  job: VinaDockingJob | null;
  backendConnected: boolean;
  error: string | null;
};

export async function runVinaDocking(input: VinaDockingInput): Promise<VinaDockingResult> {
  try {
    const response = await apiFetch("/v1/docking/jobs", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher" },
      body: JSON.stringify(input),
    }, Math.min((input.timeout_seconds + 20) * 1000, 3_620_000));
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as { detail?: string };
      return {
        job: null,
        backendConnected: true,
        error: payload.detail || `Docking API returned ${response.status}`,
      };
    }
    return {
      job: await response.json() as VinaDockingJob,
      backendConnected: true,
      error: null,
    };
  } catch {
    return {
      job: null,
      backendConnected: false,
      error: "A connected Python API is required for real Vina execution. No score was simulated.",
    };
  }
}

export type ZincCandidate = {
  rank: number;
  remote_id: string;
  source_smiles: string;
  canonical_smiles: string;
  inchikey: string;
  tranche: string | null;
  catalogs: string[];
  descriptors: OpenCandidate["descriptors"];
  similarity_to_seed: number;
  lipinski_violations: string[];
  pains_alerts: string[];
  brenk_alerts: string[];
  nih_alerts: string[];
  quality_flags: string[];
  priority_score: number;
  scientific_boundary: string;
};

export type ZincSearchJob = {
  job_id: string;
  remote_query_id: string;
  status: "submitted" | "pending" | "completed" | "failed";
  remote_status: string;
  request: {
    seed_smiles: string;
    graph_distance: number;
    anonymous_distance: number;
    max_results: number;
  };
  canonical_seed_smiles: string;
  candidates: ZincCandidate[];
  remote_returned_count: number;
  quarantined_count: number;
  remote_result_sha256: string | null;
  index_key: string;
  index_name: string;
  index_entries: number;
  index_mapped_entries: number;
  poll_after_seconds: number;
  error: string | null;
  warnings: string[];
  source_url: string;
  index_scope: string;
  scientific_boundary: string;
  created_at: string;
  updated_at: string;
};

export type ZincSearchResult = {
  job: ZincSearchJob | null;
  backendConnected: boolean;
  error: string | null;
};

async function zincResponse(response: Response): Promise<ZincSearchResult> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as { detail?: string };
    return { job: null, backendConnected: true, error: payload.detail || `ZINC-22 API returned ${response.status}` };
  }
  return { job: await response.json() as ZincSearchJob, backendConnected: true, error: null };
}

export async function startZincSearch(input: ZincSearchJob["request"]): Promise<ZincSearchResult> {
  try {
    const response = await apiFetch("/v1/zinc22/searches", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher" },
      body: JSON.stringify(input),
    }, 45_000);
    return zincResponse(response);
  } catch {
    return { job: null, backendConnected: false, error: "A connected Python API is required for real ZINC-22 search. No remote results were fabricated." };
  }
}

export async function refreshZincSearch(jobId: string): Promise<ZincSearchResult> {
  try {
    const response = await apiFetch(`/v1/zinc22/searches/${encodeURIComponent(jobId)}/refresh`, {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher" },
    }, 45_000);
    return zincResponse(response);
  } catch {
    return { job: null, backendConnected: false, error: "The Python API could not refresh the remote ZINC-22 task; the task was not resubmitted." };
  }
}

export type ProfessorEvidence = {
  evidence_id: string;
  kind: "compound-identity" | "literature" | string;
  source?: string;
  source_id?: string;
  display_name?: string;
  title?: string;
  year?: number;
  pmid?: string;
  url?: string;
  statement?: string;
  evidence_level?: string;
  used_by_model?: boolean;
  document_id?: string;
  page_number?: number;
  section?: string;
  quote?: string;
  source_url?: string;
  source_version?: string;
  document_sha256?: string;
  retrieval_score?: number;
  retrieval_methods?: string[];
};

export type ProfessorTraceEvent = {
  stage: string;
  status: "completed" | "completed-with-warning" | "blocked" | "skipped";
  message: string;
  metrics: Record<string, string | number | boolean>;
};

export type ProfessorAnswer = {
  answer_id: string | null;
  conversation_id: string | null;
  answer: string;
  evidence: ProfessorEvidence[];
  missing_information: string[];
  recommended_action: string;
  mode: "deterministic-evidence" | "local-ollama-rag" | "hybrid-ollama-rag";
  model: string | null;
  embedding_model: string | null;
  abstained: boolean;
  confidence: "low" | "medium";
  retrieval_score: number;
  citation_coverage: number;
  retrieval_trace: ProfessorTraceEvent[];
  guardrails: string[];
  warnings: string[];
  created_at: string | null;
  notice: { research_use_only: boolean; message: string };
};

export type ProfessorCapabilities = {
  provider: string;
  enabled: boolean;
  model: string;
  embedding_model: string;
  ingestion_enabled: boolean;
  document_count: number;
  indexed_document_count: number;
  chunk_count: number;
  retrieval: string;
  page_level_citations: boolean;
  immutable_raw_and_normalized_artifacts: boolean;
  prompt_injection_filter: boolean;
  clinical_advice_blocked: boolean;
  faculty_feedback: boolean;
  answer_evaluations: boolean;
  automatic_retraining: boolean;
};

export type ProfessorDocument = {
  document_id: string;
  title: string;
  filename: string;
  media_type: string;
  source_url: string | null;
  source_version: string;
  rights_status: string;
  rights_note: string;
  project_scope: string;
  course_scope: string;
  tags: string[];
  status: "indexed" | "quarantined";
  raw_sha256: string;
  normalized_sha256: string | null;
  parser_version: string;
  chunker_version: string;
  embedding_model: string | null;
  page_count: number;
  chunk_count: number;
  prompt_injection_flags: string[];
  warnings: string[];
  created_by: string;
  created_at: string;
  duplicate: boolean;
};

export type ProfessorResult = {
  answer: ProfessorAnswer | null;
  backendConnected: boolean;
  error: string | null;
};

export async function askScientificProfessor(
  question: string,
  cancerType: string,
  compoundIds: string[],
  options: {
    conversationId?: string | null;
    projectScope?: string;
    courseScope?: string;
    documentIds?: string[];
  } = {},
): Promise<ProfessorResult> {
  try {
    const response = await apiFetch("/v1/assistant/query", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher", "X-OSIEL-Role": "researcher" },
      body: JSON.stringify({
        question,
        cancer_type: cancerType,
        compound_ids: compoundIds.slice(0, 20),
        conversation_id: options.conversationId || null,
        project_scope: options.projectScope || "general",
        course_scope: options.courseScope || "general",
        document_ids: (options.documentIds || []).slice(0, 50),
        persist: true,
      }),
    }, 140_000);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as { detail?: string };
      return { answer: null, backendConnected: true, error: payload.detail || `Assistant API returned ${response.status}` };
    }
    return { answer: await response.json() as ProfessorAnswer, backendConnected: true, error: null };
  } catch {
    return {
      answer: null,
      backendConnected: false,
      error: "Python assistant unavailable; the embedded curated guidance is shown instead.",
    };
  }
}

export async function loadProfessorCapabilities(): Promise<ProfessorCapabilities | null> {
  try {
    const response = await apiFetch("/v1/assistant/capabilities", undefined, 10_000);
    return response.ok ? await response.json() as ProfessorCapabilities : null;
  } catch {
    return null;
  }
}

export async function listProfessorDocuments(
  projectScope = "general",
  courseScope = "general",
): Promise<ProfessorDocument[]> {
  try {
    const query = new URLSearchParams({ project_scope: projectScope, course_scope: courseScope });
    const response = await apiFetch(`/v1/assistant/documents?${query.toString()}`, {
      headers: { "X-OSIEL-Actor": "workbench-researcher", "X-OSIEL-Role": "researcher" },
    });
    return response.ok ? await response.json() as ProfessorDocument[] : [];
  } catch {
    return [];
  }
}

async function fileAsBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  const chunkSize = 0x8000;
  let binary = "";
  for (let start = 0; start < bytes.length; start += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(start, start + chunkSize));
  }
  return btoa(binary);
}

export async function ingestProfessorDocument(
  file: File,
  input: {
    title: string;
    sourceUrl?: string;
    sourceVersion: string;
    rightsNote: string;
    projectScope: string;
    courseScope: string;
  },
): Promise<{ document: ProfessorDocument | null; error: string | null }> {
  const mediaType = file.type === "application/pdf"
    ? "application/pdf"
    : file.name.toLowerCase().endsWith(".md")
      ? "text/markdown"
      : "text/plain";
  try {
    const response = await apiFetch("/v1/assistant/documents", {
      method: "POST",
      headers: {
        "X-OSIEL-Actor": "workbench-instructor",
        "X-OSIEL-Role": "instructor",
      },
      body: JSON.stringify({
        filename: file.name,
        title: input.title,
        media_type: mediaType,
        content_base64: await fileAsBase64(file),
        source_url: input.sourceUrl || null,
        source_version: input.sourceVersion,
        rights_status: "approved",
        rights_note: input.rightsNote,
        project_scope: input.projectScope,
        course_scope: input.courseScope,
        tags: [],
      }),
    }, 180_000);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as { detail?: string };
      return { document: null, error: payload.detail || `Document API returned ${response.status}` };
    }
    return { document: await response.json() as ProfessorDocument, error: null };
  } catch {
    return { document: null, error: "The Python document-ingestion engine is unavailable." };
  }
}

export async function submitProfessorFeedback(
  answerId: string,
  input: {
    decision: "correct" | "partially-correct" | "incorrect" | "unsafe";
    correction?: string;
    reviewerNotes: string;
    evidenceIds: string[];
  },
): Promise<{ feedbackId: string | null; error: string | null }> {
  try {
    const response = await apiFetch(`/v1/assistant/answers/${encodeURIComponent(answerId)}/feedback`, {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-instructor", "X-OSIEL-Role": "instructor" },
      body: JSON.stringify({
        decision: input.decision,
        correction: input.correction || null,
        reviewer_notes: input.reviewerNotes,
        supporting_evidence_ids: input.evidenceIds,
      }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as { detail?: string };
      return { feedbackId: null, error: payload.detail || `Feedback API returned ${response.status}` };
    }
    const payload = await response.json() as { feedback_id: string };
    return { feedbackId: payload.feedback_id, error: null };
  } catch {
    return { feedbackId: null, error: "The Python feedback service is unavailable." };
  }
}

export type ModelLabCapabilities = {
  operator_enabled: boolean;
  source: string;
  supported_tasks: string[];
  feature_definition: string;
  baseline: string;
  calibration: string;
  evaluation: string;
  active_learning: string;
  automatic_promotion: boolean;
  max_source_records: number;
  max_candidate_pool: number;
  scientific_boundary: string;
};

export type ActivityDatasetSnapshot = {
  snapshot_id: string;
  status: "ready" | "blocked";
  source: "ChEMBL";
  source_release: string;
  target_chembl_id: string;
  target_label: string;
  standard_type: string;
  assay_type: string;
  active_pchembl_threshold: number;
  inactive_pchembl_threshold: number;
  record_count: number;
  active_count: number;
  inactive_count: number;
  unique_scaffold_count: number;
  ambiguous_removed: number;
  invalid_removed: number;
  duplicate_removed: number;
  conflict_removed: number;
  raw_sha256: string;
  raw_object_uri: string;
  normalized_sha256: string;
  normalized_object_uri: string;
  request_urls: string[];
  warnings: string[];
  training_eligible: boolean;
  created_at: string;
};

export type ActivityModelRun = {
  model_id: string;
  status: "completed" | "blocked" | "failed";
  model_name: string;
  model_version: string;
  model_type: string;
  snapshot_id: string;
  target_chembl_id: string;
  target_label: string;
  endpoint: string;
  feature_version: string;
  split_strategy: string;
  train_count: number;
  calibration_count: number;
  test_count: number;
  train_scaffolds: number;
  calibration_scaffolds: number;
  test_scaffolds: number;
  scaffold_overlap_count: number;
  metrics: null | {
    auroc: number;
    average_precision: number;
    balanced_accuracy: number;
    sensitivity: number;
    specificity: number;
    brier_score: number;
    expected_calibration_error: number;
    test_prevalence: number;
    test_count: number;
  };
  artifact_sha256: string | null;
  artifact_object_uri: string | null;
  evaluation_gate: "passed-reference-gate" | "failed-reference-gate" | "not-run";
  promotion_eligible: boolean;
  warnings: string[];
  created_at: string;
};

export type ModelLabCandidate = {
  candidate_id: string;
  display_name: string;
  smiles: string;
};

export type ActiveLearningBatch = {
  batch_id: string;
  model_id: string;
  status: "proposed";
  candidate_count: number;
  requested_batch_size: number;
  suggestions: Array<{
    priority: number;
    candidate_id: string;
    display_name: string;
    canonical_smiles: string;
    active_probability: number;
    uncertainty: number;
    nearest_training_similarity: number;
    diversity_to_selected: number;
    acquisition_score: number;
    reason: string;
  }>;
  selection_policy: string;
  approval_required: boolean;
  experiment_started: boolean;
  created_at: string;
  scientific_boundary: string;
};

async function responseDetail(response: Response): Promise<string> {
  const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as { detail?: string };
  return payload.detail || `HTTP ${response.status}`;
}

export async function getModelLabCapabilities(): Promise<{ capabilities: ModelLabCapabilities | null; backendConnected: boolean; error: string | null }> {
  try {
    const response = await apiFetch("/v1/model-lab/capabilities");
    if (!response.ok) return { capabilities: null, backendConnected: true, error: await responseDetail(response) };
    return { capabilities: await response.json() as ModelLabCapabilities, backendConnected: true, error: null };
  } catch {
    return { capabilities: null, backendConnected: false, error: "Connect the supplied Python API to run the evidence-backed model laboratory." };
  }
}

export async function createChemblSnapshot(input: {
  target_chembl_id: string;
  target_label: string;
  standard_type: "IC50" | "EC50" | "Ki" | "Kd";
  assay_type: "B" | "F";
  max_records: number;
  active_pchembl_threshold: number;
  inactive_pchembl_threshold: number;
  minimum_assay_confidence: number;
}): Promise<{ snapshot: ActivityDatasetSnapshot | null; backendConnected: boolean; error: string | null }> {
  try {
    const response = await apiFetch("/v1/model-lab/chembl/snapshots", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher" },
      body: JSON.stringify(input),
    }, 180_000);
    if (!response.ok) return { snapshot: null, backendConnected: true, error: await responseDetail(response) };
    return { snapshot: await response.json() as ActivityDatasetSnapshot, backendConnected: true, error: null };
  } catch {
    return { snapshot: null, backendConnected: false, error: "The Python/ChEMBL model-lab service is not connected. No dataset was fabricated." };
  }
}

export async function trainActivityModel(snapshotId: string): Promise<{ run: ActivityModelRun | null; backendConnected: boolean; error: string | null }> {
  try {
    const response = await apiFetch("/v1/model-lab/models", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-ml-reviewer" },
      body: JSON.stringify({
        snapshot_id: snapshotId,
        test_fraction: 0.20,
        calibration_fraction: 0.20,
        random_seed: 20260822,
        minimum_records: 100,
      }),
    }, 240_000);
    if (!response.ok) return { run: null, backendConnected: true, error: await responseDetail(response) };
    return { run: await response.json() as ActivityModelRun, backendConnected: true, error: null };
  } catch {
    return { run: null, backendConnected: false, error: "The Python model worker is not connected. No evaluation metrics were simulated." };
  }
}

export async function proposeActiveLearning(
  modelId: string,
  candidates: ModelLabCandidate[],
): Promise<{ batch: ActiveLearningBatch | null; backendConnected: boolean; error: string | null }> {
  try {
    const response = await apiFetch("/v1/model-lab/active-learning-batches", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher" },
      body: JSON.stringify({
        model_id: modelId,
        candidates,
        batch_size: Math.min(8, candidates.length),
        maximum_pair_similarity: 0.75,
      }),
    }, 120_000);
    if (!response.ok) return { batch: null, backendConnected: true, error: await responseDetail(response) };
    return { batch: await response.json() as ActiveLearningBatch, backendConnected: true, error: null };
  } catch {
    return { batch: null, backendConnected: false, error: "The Python active-learning service is not connected. No priorities were fabricated." };
  }
}

export type DockingBenchmarkRun = {
  benchmark_id: string;
  docking_job_id: string;
  status: "passed" | "failed" | "invalid";
  method: string;
  rmsd_pass_threshold_angstrom: number;
  best_pose_rank: number | null;
  best_rmsd_angstrom: number | null;
  pose_results: Array<{
    pose_rank: number;
    affinity_kcal_mol: number | null;
    aligned_heavy_atom_rmsd_angstrom: number;
    atom_count: number;
  }>;
  reference_sha256: string;
  reference_object_uri: string;
  atom_type_order_match: boolean;
  scoring_qualified: boolean;
  warnings: string[];
  created_at: string;
  scientific_boundary: string;
};

export async function runDockingBenchmark(input: {
  docking_job_id: string;
  reference_ligand_filename: string;
  reference_ligand_content_base64: string;
  rmsd_pass_threshold_angstrom: number;
}): Promise<{ benchmark: DockingBenchmarkRun | null; backendConnected: boolean; error: string | null }> {
  try {
    const response = await apiFetch("/v1/docking/benchmarks", {
      method: "POST",
      headers: { "X-OSIEL-Actor": "workbench-researcher" },
      body: JSON.stringify(input),
    }, 60_000);
    if (!response.ok) return { benchmark: null, backendConnected: true, error: await responseDetail(response) };
    return { benchmark: await response.json() as DockingBenchmarkRun, backendConnected: true, error: null };
  } catch {
    return { benchmark: null, backendConnected: false, error: "The Python benchmark service is not connected. No RMSD was simulated." };
  }
}

export type MultimodalCaseResult = {
  case_id: string;
  status: "completed" | "abstained" | "blocked";
  question: string;
  assessments: Array<{
    modality: "chemistry" | "protein" | "assay" | "documents" | "imaging";
    status: "completed" | "completed-with-warning" | "blocked" | "skipped";
    model_name: string | null;
    model_version: string | null;
    evidence_ids: string[];
    confidence: number;
    findings: string[];
    warnings: string[];
  }>;
  evidence: Array<{
    evidence_id: string;
    modality: string;
    source: string;
    source_version: string;
    citation: string;
    finding: string;
    confidence: number;
  }>;
  recommendation: string;
  rationale: string[];
  next_actions: string[];
  missing_information: string[];
  conflicts: string[];
  confidence: number;
  citation_coverage: number;
  abstained: boolean;
  human_approval_required: boolean;
  approved: boolean;
  trace: Array<{
    sequence: number;
    stage: string;
    status: "completed" | "completed-with-warning" | "blocked" | "skipped";
    message: string;
    metrics: Record<string, unknown>;
  }>;
  scientific_boundary: string;
};

export async function runMultimodalResearchCase(input: {
  question: string;
  cancer_type?: string;
  cell_line?: string;
  target_name?: string;
  protein_accession?: string;
  compound_ids: string[];
  requested_modalities: string[];
}): Promise<{ result: MultimodalCaseResult | null; backendConnected: boolean; error: string | null }> {
  try {
    const response = await apiFetch("/v1/multimodal/cases", {
      method: "POST",
      headers: {
        "X-OSIEL-Actor": "workbench-researcher",
        "X-OSIEL-Role": "researcher",
      },
      body: JSON.stringify({
        ...input,
        project_scope: "discovery-lab",
        course_scope: "general",
        artifacts: [],
        document_ids: [],
      }),
    }, 180_000);
    if (!response.ok) return { result: null, backendConnected: true, error: await responseDetail(response) };
    return { result: await response.json() as MultimodalCaseResult, backendConnected: true, error: null };
  } catch {
    return {
      result: null,
      backendConnected: false,
      error: "The Python multimodal orchestrator is not connected. OSIEL stopped safely and generated no scientific conclusion.",
    };
  }
}

export async function approveModel(
  modelId: string,
  reviewer = "faculty-ml-reviewer",
  reason = "Model evaluated on frozen Bemis-Murcko test scaffolds and verified for research challenger tracking.",
): Promise<{ approved: boolean; error: string | null; detail?: string }> {
  try {
    const params = new URLSearchParams({ reviewer, reason });
    const response = await apiFetch(`/v1/models/${encodeURIComponent(modelId)}/approve?${params.toString()}`, {
      method: "POST",
      headers: {
        "X-OSIEL-Actor": reviewer,
        "X-OSIEL-Role": "reviewer",
      },
    });
    if (!response.ok) return { approved: false, error: await responseDetail(response) };
    const data = await response.json() as { approved: boolean; reason?: string };
    return { approved: data.approved, error: null, detail: data.reason };
  } catch (err) {
    return { approved: false, error: err instanceof Error ? err.message : String(err) };
  }
}

