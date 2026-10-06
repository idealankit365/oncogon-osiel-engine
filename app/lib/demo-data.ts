export type AdmetDatum = {
  code: string;
  label: string;
  value: number;
  className: "good" | "watch" | "risk";
};

export type RankedCandidate = {
  rank: number;
  compound_id: string;
  display_name: string;
  origin: "natural" | "synthetic" | "reference";
  formula: string;
  score: number;
  activity: number;
  selectivity: number;
  confidence: number;
  uncertainty: number;
  predicted_ic50_um: number;
  evidence_grade: "A" | "B" | "C" | "D";
  applicability_domain: "inside" | "borderline" | "outside";
  source: string;
  note: string;
  admet: AdmetDatum[];
};

export const demoCandidates: RankedCandidate[] = [
  {
    rank: 1,
    compound_id: "OSIEL-CMP-0001",
    display_name: "Quercetin",
    origin: "natural",
    formula: "C15H10O7",
    score: 86.4,
    activity: 88,
    selectivity: 74,
    confidence: 82,
    uncertainty: 18,
    predicted_ic50_um: 2.47,
    evidence_grade: "B",
    applicability_domain: "inside",
    source: "PubChem identity · OSIEL reference hypothesis",
    note: "High activity signal with a balanced rule-based developability panel.",
    admet: [
      { code: "sol", label: "Solubility", value: 72, className: "good" },
      { code: "perm", label: "Permeability", value: 54, className: "watch" },
      { code: "herg", label: "hERG safety", value: 79, className: "good" },
      { code: "liver", label: "Liver safety", value: 68, className: "watch" },
    ],
  },
  {
    rank: 2,
    compound_id: "OSIEL-CMP-0002",
    display_name: "Luteolin",
    origin: "natural",
    formula: "C15H10O6",
    score: 83.7,
    activity: 84,
    selectivity: 77,
    confidence: 79,
    uncertainty: 21,
    predicted_ic50_um: 3.12,
    evidence_grade: "B",
    applicability_domain: "inside",
    source: "PubChem identity · OSIEL reference hypothesis",
    note: "Close activity/selectivity balance; structural redundancy requires review.",
    admet: [
      { code: "sol", label: "Solubility", value: 69, className: "watch" },
      { code: "perm", label: "Permeability", value: 61, className: "watch" },
      { code: "herg", label: "hERG safety", value: 81, className: "good" },
      { code: "liver", label: "Liver safety", value: 72, className: "good" },
    ],
  },
  {
    rank: 3,
    compound_id: "OSIEL-CMP-0005",
    display_name: "Gefitinib",
    origin: "synthetic",
    formula: "C22H24ClFN4O3",
    score: 81.2,
    activity: 91,
    selectivity: 82,
    confidence: 88,
    uncertainty: 12,
    predicted_ic50_um: 1.18,
    evidence_grade: "A",
    applicability_domain: "inside",
    source: "PubChem identity · reference comparator",
    note: "Reference comparator with strong model-domain coverage; not a treatment recommendation.",
    admet: [
      { code: "sol", label: "Solubility", value: 58, className: "watch" },
      { code: "perm", label: "Permeability", value: 85, className: "good" },
      { code: "herg", label: "hERG safety", value: 62, className: "watch" },
      { code: "liver", label: "Liver safety", value: 56, className: "watch" },
    ],
  },
  {
    rank: 4,
    compound_id: "OSIEL-CMP-0003",
    display_name: "Curcumin",
    origin: "natural",
    formula: "C21H20O6",
    score: 78.9,
    activity: 80,
    selectivity: 71,
    confidence: 73,
    uncertainty: 27,
    predicted_ic50_um: 4.64,
    evidence_grade: "B",
    applicability_domain: "borderline",
    source: "PubChem identity · OSIEL reference hypothesis",
    note: "Promising signal with higher uncertainty and a solubility watch flag.",
    admet: [
      { code: "sol", label: "Solubility", value: 38, className: "risk" },
      { code: "perm", label: "Permeability", value: 73, className: "good" },
      { code: "herg", label: "hERG safety", value: 78, className: "good" },
      { code: "liver", label: "Liver safety", value: 64, className: "watch" },
    ],
  },
  {
    rank: 5,
    compound_id: "OSIEL-CMP-0004",
    display_name: "Catechin",
    origin: "natural",
    formula: "C15H14O6",
    score: 75.6,
    activity: 71,
    selectivity: 76,
    confidence: 77,
    uncertainty: 23,
    predicted_ic50_um: 5.87,
    evidence_grade: "B",
    applicability_domain: "inside",
    source: "PubChem identity · OSIEL reference hypothesis",
    note: "Moderate predicted activity; retained for chemical diversity.",
    admet: [
      { code: "sol", label: "Solubility", value: 76, className: "good" },
      { code: "perm", label: "Permeability", value: 47, className: "risk" },
      { code: "herg", label: "hERG safety", value: 84, className: "good" },
      { code: "liver", label: "Liver safety", value: 74, className: "good" },
    ],
  },
  {
    rank: 6,
    compound_id: "OSIEL-CMP-0006",
    display_name: "5-Fluorouracil",
    origin: "synthetic",
    formula: "C4H3FN2O2",
    score: 73.3,
    activity: 86,
    selectivity: 57,
    confidence: 86,
    uncertainty: 14,
    predicted_ic50_um: 2.09,
    evidence_grade: "A",
    applicability_domain: "inside",
    source: "PubChem identity · reference comparator",
    note: "Reference control candidate; selectivity contribution lowers total priority.",
    admet: [
      { code: "sol", label: "Solubility", value: 90, className: "good" },
      { code: "perm", label: "Permeability", value: 45, className: "risk" },
      { code: "herg", label: "hERG safety", value: 88, className: "good" },
      { code: "liver", label: "Liver safety", value: 51, className: "watch" },
    ],
  },
  {
    rank: 7,
    compound_id: "OSIEL-CMP-0007",
    display_name: "Resveratrol",
    origin: "natural",
    formula: "C14H12O3",
    score: 70.8,
    activity: 68,
    selectivity: 69,
    confidence: 67,
    uncertainty: 33,
    predicted_ic50_um: 8.21,
    evidence_grade: "C",
    applicability_domain: "borderline",
    source: "PubChem identity · OSIEL reference hypothesis",
    note: "Uncertainty penalty dominates; suited to an information-gain experiment.",
    admet: [
      { code: "sol", label: "Solubility", value: 44, className: "risk" },
      { code: "perm", label: "Permeability", value: 77, className: "good" },
      { code: "herg", label: "hERG safety", value: 73, className: "good" },
      { code: "liver", label: "Liver safety", value: 67, className: "watch" },
    ],
  },
  {
    rank: 8,
    compound_id: "OSIEL-CMP-0012",
    display_name: "NCI reference 0012",
    origin: "reference",
    formula: "C10H10N2O",
    score: 63.1,
    activity: 61,
    selectivity: 58,
    confidence: 54,
    uncertainty: 46,
    predicted_ic50_um: 12.7,
    evidence_grade: "D",
    applicability_domain: "outside",
    source: "RDKit NCI structural reference set",
    note: "Outside the reference applicability domain; flagged, not discarded silently.",
    admet: [
      { code: "sol", label: "Solubility", value: 49, className: "risk" },
      { code: "perm", label: "Permeability", value: 68, className: "watch" },
      { code: "herg", label: "hERG safety", value: 43, className: "risk" },
      { code: "liver", label: "Liver safety", value: 48, className: "risk" },
    ],
  },
];

export function renumber(candidates: RankedCandidate[]): RankedCandidate[] {
  return [...candidates]
    .sort((a, b) => b.score - a.score)
    .map((candidate, index) => ({ ...candidate, rank: index + 1 }));
}
