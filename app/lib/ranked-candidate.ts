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
