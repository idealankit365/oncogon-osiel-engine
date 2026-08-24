from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SourceDefinition:
    code: str
    name: str
    phase: int
    mode: str
    endpoint: str
    licence_note: str
    purpose: str
    enabled_by_default: bool = False


SOURCES = (
    SourceDefinition(
        "pubchem",
        "PubChem",
        1,
        "official-api-and-bulk",
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        "Public resource; follow NCBI usage policies and record retrieval dates.",
        "Identifier, structure, property and BioAssay enrichment.",
        True,
    ),
    SourceDefinition(
        "chembl",
        "ChEMBL",
        1,
        "official-api-and-release-download",
        "https://www.ebi.ac.uk/chembl/api/data",
        "Verify release-specific terms; preserve source release and assay provenance.",
        "Curated structures, assays, targets and bioactivity records.",
        True,
    ),
    SourceDefinition(
        "nci60",
        "NCI-60 / CellMiner",
        1,
        "approved-bulk-connector",
        "https://discover.nci.nih.gov/cellminer/",
        "Public research data; preserve the NCI endpoint domain separately.",
        "Oncology cell-line response and screening reference data.",
    ),
    SourceDefinition(
        "tdc",
        "Therapeutics Data Commons",
        1,
        "official-python-connector",
        "https://tdcommons.ai/",
        "Dataset-specific licences vary; snapshot dataset and task versions.",
        "Benchmark tasks, splits and selected ADMET datasets.",
    ),
    SourceDefinition(
        "coconut",
        "COCONUT 2.0",
        1,
        "approved-bulk-connector",
        "https://coconut.naturalproducts.net/download",
        "Curated dataset advertised under CC0; keep upstream provenance and release.",
        "Natural-product structures, NP-likeness, QED and source metadata.",
    ),
    SourceDefinition(
        "npass",
        "NPASS 3.0",
        1,
        "approved-bulk-connector",
        "https://bidd.group/NPASS/downloadnpass.html",
        "Review and snapshot the current download/use terms before production use.",
        "Natural-product activity, species, target and quantitative evidence.",
    ),
    SourceDefinition(
        "anpdb",
        "African Natural Products Database",
        1,
        "approved-bulk-connector",
        "https://african-compounds.org",
        "Open-access research source; verify dataset and commercial-use terms per release.",
        "African compound, species, traditional-use, bioactivity and literature metadata.",
    ),
    SourceDefinition(
        "lotus",
        "LOTUS",
        1,
        "approved-bulk-connector",
        "https://lotus.naturalproducts.net/download",
        "Verify export licence and release; preserve organism occurrence evidence.",
        "Natural-product occurrence and organism provenance.",
    ),
    SourceDefinition(
        "tox21",
        "Tox21",
        1,
        "approved-bulk-connector",
        "https://tripod.nih.gov/tox21/pubdata",
        "Public programme; retain assay-level terms and endpoint definitions.",
        "Toxicity screening evidence.",
    ),
    SourceDefinition(
        "toxcast",
        "ToxCast",
        1,
        "approved-bulk-connector",
        "https://www.epa.gov/comptox-tools/exploring-toxcast-data",
        "Public US EPA data; retain assay versions and quality flags.",
        "Toxicity and pathway-screening endpoints.",
    ),
    SourceDefinition(
        "open-targets",
        "Open Targets Platform",
        1,
        "official-graphql-and-downloads",
        "https://api.platform.opentargets.org/api/v4/graphql",
        "Open data; preserve release, evidence type, upstream study and retrieval metadata.",
        "Disease-target evidence discovery and identifier resolution.",
    ),
    SourceDefinition(
        "uniprot",
        "UniProt",
        1,
        "official-rest-api-and-release-download",
        "https://rest.uniprot.org/",
        "Review UniProt terms and cite the release; preserve accession and sequence version.",
        "Target identity, sequence and cross-reference resolution.",
    ),
    SourceDefinition(
        "rcsb-pdb",
        "RCSB Protein Data Bank",
        1,
        "official-data-api",
        "https://data.rcsb.org/",
        "Public archive; cite the PDB entry and primary deposition/publication.",
        "Experimental macromolecular structure metadata and files.",
    ),
    SourceDefinition(
        "alphafold-db",
        "AlphaFold Protein Structure Database",
        1,
        "official-api-and-download",
        "https://alphafold.ebi.ac.uk/api/prediction/",
        "Use under current AlphaFold DB terms; cite database/model and retain confidence metadata.",
        "Predicted structures when qualified experimental structures are unavailable.",
    ),
    SourceDefinition(
        "zinc22",
        "ZINC22 / CartBlanche22",
        2,
        "bounded-smallworld-search",
        "https://sw.docking.org/search/maps",
        "Follow current service rules; one seed and at most 100 imported hits per OSIEL job; record map metadata and checksum; do not crawl.",
        "Provider-side multi-billion graph search with bounded local analogue triage.",
    ),
    SourceDefinition(
        "chemspace",
        "Chemspace",
        2,
        "licensed-api-connector-or-link-out",
        "https://chem-space.com/",
        "API key and current provider terms required; verify supplier identity, form and availability.",
        "Supplier search and procurement hand-off.",
    ),
    SourceDefinition(
        "rdkit",
        "RDKit",
        1,
        "local-open-source-library",
        "https://www.rdkit.org/",
        "BSD-licensed software; pin and record the exact version and feature definitions.",
        "Structure standardization, descriptors, fingerprints and medicinal-chemistry alerts.",
        True,
    ),
    SourceDefinition(
        "autodock-vina",
        "AutoDock Vina",
        2,
        "local-open-source-executable",
        "https://vina.scripps.edu/",
        "Apache-2.0 software; record version, inputs, box, exhaustiveness and random seed.",
        "Optional docking execution after receptor/ligand preparation and benchmark qualification.",
    ),
)


def source_payload() -> list[dict[str, object]]:
    return [asdict(source) for source in SOURCES]
