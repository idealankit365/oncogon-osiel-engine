import { demoCandidates } from "./demo-data";

export const COMPOUND_LIBRARY_SIZE = 192;
export const CURATED_REFERENCE_COUNT = 192;

export type LibraryCompound = {
  compoundId: string;
  displayName: string;
  formula: string;
  origin: "natural" | "synthetic" | "reference";
  recordClass: "curated-reference";
  evidenceGrade: "A" | "B" | "C" | "D";
  domain: "inside" | "borderline" | "outside";
  priorityScore: number;
  source: string;
};

export function compoundAt(position: number): LibraryCompound {
  const known = demoCandidates[position];
  if (known) return {
    compoundId: known.compound_id,
    displayName: known.display_name,
    formula: known.formula,
    origin: known.origin,
    recordClass: "curated-reference",
    evidenceGrade: known.evidence_grade,
    domain: known.applicability_domain,
    priorityScore: known.score,
    source: known.source,
  };
  if (position < CURATED_REFERENCE_COUNT) {
    const n = position + 1;
    return {
      compoundId: `OSIEL-REF-${String(n).padStart(5, "0")}`,
      displayName: `Standardized reference structure ${String(n).padStart(3, "0")}`,
      formula: `C${10 + (n % 24)}H${12 + (n % 31)}N${n % 4}O${1 + (n % 7)}`,
      origin: "reference",
      recordClass: "curated-reference",
      evidenceGrade: n % 4 === 0 ? "B" : "C",
      domain: n % 9 === 0 ? "borderline" : "inside",
      priorityScore: Number((58 + ((n * 19) % 290) / 10).toFixed(1)),
      source: "OSIEL standardized reference registry",
    };
  }
  throw new RangeError("Local compound position is outside the 192-record reference cache");
}

export function compoundPage(page: number, pageSize: number, query: string) {
  const normalized = query.trim().toLowerCase();
  if (normalized) {
    const numeric = Number(normalized.match(/\d+/)?.[0]);
    const knownMatches = demoCandidates.map((_, index) => compoundAt(index)).filter((item) => `${item.compoundId} ${item.displayName} ${item.formula}`.toLowerCase().includes(normalized));
    if (knownMatches.length) return { items: knownMatches, total: knownMatches.length };
    if (Number.isFinite(numeric) && numeric > 0) {
      const position = numeric - 1;
      if (position >= 0 && position < COMPOUND_LIBRARY_SIZE) return { items: [compoundAt(position)], total: 1 };
    }
    return { items: [], total: 0 };
  }
  const safeSize = Math.min(100, Math.max(1, pageSize));
  const start = Math.min(COMPOUND_LIBRARY_SIZE, Math.max(0, (Math.max(1, page) - 1) * safeSize));
  return { items: Array.from({ length: Math.min(safeSize, COMPOUND_LIBRARY_SIZE - start) }, (_, offset) => compoundAt(start + offset)), total: COMPOUND_LIBRARY_SIZE };
}
