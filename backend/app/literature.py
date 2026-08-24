from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LiteratureRecord:
    record_id: str
    title: str
    year: int
    compound: str
    biological_model: str
    assay: str
    finding: str
    pmid: str
    url: str
    evidence_level: str
    source: str = "PubMed"
    claim_boundary: str = "Study-specific research evidence; not clinical efficacy."


RECORDS = (
    LiteratureRecord("LIT-001", "Apigenin inhibits cell proliferation, migration, and invasion by targeting Akt in the A549 human lung cancer cell line", 2017, "Apigenin", "A549 NSCLC cells", "MTT, colony formation, migration and invasion", "Reported dose- and time-dependent antiproliferative effects with PI3K/Akt observations.", "28125432", "https://pubmed.ncbi.nlm.nih.gov/28125432/", "direct"),
    LiteratureRecord("LIT-002", "Quercetin induces pro-apoptotic autophagy via SIRT1/AMPK signaling pathway in A549 and H1299", 2021, "Quercetin", "A549 and H1299 cells", "CCK-8, apoptosis, western blot and microscopy", "Reported dose-dependent viability reduction and autophagy-associated apoptosis in vitro.", "33709560", "https://pubmed.ncbi.nlm.nih.gov/33709560/", "direct"),
    LiteratureRecord("LIT-003", "Curcumin inhibits the development of non-small cell lung cancer by inhibiting autophagy and apoptosis", 2018, "Curcumin", "A549 and H1299 cells", "Viability, colony formation, apoptosis and autophagy", "Reported time- and dose-dependent viability effects with mTOR-pathway observations.", "29201217", "https://pubmed.ncbi.nlm.nih.gov/29201217/", "direct"),
    LiteratureRecord("LIT-004", "Curcumin and quercetin synergistically inhibit cancer cell proliferation in multiple cancer cells", 2019, "Curcumin + quercetin", "A549 and other cancer cell lines", "Cell-proliferation combination analysis", "Reported combination effects that require matched assay context before reuse.", "30599890", "https://pubmed.ncbi.nlm.nih.gov/30599890/", "supporting"),
    LiteratureRecord("LIT-005", "Identification of epigallocatechin-3-gallate as a potent inducer of p53-dependent apoptosis in A549", 2009, "EGCG / catechin family", "A549 cells", "Viability, caspase 3/7 and reporter assays", "Reported p53-dependent apoptosis for EGCG while distinguishing it from a catechin mixture.", "19406223", "https://pubmed.ncbi.nlm.nih.gov/19406223/", "supporting"),
    LiteratureRecord("LIT-006", "Green tea catechin EGCG attenuates viability of A549 cells via reducing Bcl-xL expression", 2014, "EGCG", "A549 cells", "MTT and gene-expression analysis", "Reported dose-dependent proliferation reduction in the stated in-vitro context.", "24944597", "https://pubmed.ncbi.nlm.nih.gov/24944597/", "supporting"),
    LiteratureRecord("LIT-007", "Butein and Frondoside-A combination exhibits additive anti-cancer effects on tumor cell viability", 2022, "Butein + Frondoside-A", "A549 and MDA-MB-231 cells", "CellTiter-Glo, colony growth and invasion", "Directly relevant CellTiter-Glo method example with repeated experiments.", "35008855", "https://pubmed.ncbi.nlm.nih.gov/35008855/", "method"),
    LiteratureRecord("LIT-008", "RNAi screening identifies KAT8 as a key molecule important for cancer cell survival", 2013, "RNAi perturbations", "A549 cells in 96-well plates", "CellTiter-Glo after five-day perturbation", "Plate-based A549 viability screening method with positive and negative controls.", "23638218", "https://pubmed.ncbi.nlm.nih.gov/23638218/", "method"),
    LiteratureRecord("LIT-009", "A novel small molecule, Rosline, inhibits growth and induces caspase-dependent apoptosis in A549", 2016, "Rosline", "A549 cells", "Library screen, viability and apoptosis", "Reported an A549 screening hit and subsequent mechanistic validation.", "27006094", "https://pubmed.ncbi.nlm.nih.gov/27006094/", "supporting"),
    LiteratureRecord("LIT-010", "Quercetin suppresses lung cancer growth by targeting Aurora B kinase", 2016, "Quercetin", "A549 cells and xenograft", "Kinase, cellular and in-vivo studies", "Mechanistic evidence connected quercetin exposure with Aurora B activity.", "27704720", "https://pubmed.ncbi.nlm.nih.gov/27704720/", "supporting"),
    LiteratureRecord("LIT-011", "Sesamin induces A549 cell mitophagy and mitochondrial apoptosis via reactive oxygen species", 2020, "Sesamin", "A549 cells", "CCK-8, migration, cell cycle and flow cytometry", "Reported viability and migration effects with mitochondrial measurements.", "32392913", "https://pubmed.ncbi.nlm.nih.gov/32392913/", "direct"),
    LiteratureRecord("LIT-012", "Zebularine inhibits the growth of A549 lung cancer cells via cell cycle arrest and apoptosis", 2013, "Zebularine", "A549 and normal pulmonary fibroblasts", "Growth, cell cycle, apoptosis and ROS", "Reported an approximately 70 µM IC50 at 72 hours in the study context.", "23661569", "https://pubmed.ncbi.nlm.nih.gov/23661569/", "direct"),
)


def search_literature(query: str | None = None, evidence_level: str | None = None) -> list[dict[str, object]]:
    needle = (query or "").strip().lower()
    output = []
    for record in RECORDS:
        if evidence_level and record.evidence_level != evidence_level:
            continue
        searchable = f"{record.title} {record.compound} {record.biological_model} {record.assay}".lower()
        if needle and needle not in searchable:
            continue
        output.append(asdict(record))
    return output
