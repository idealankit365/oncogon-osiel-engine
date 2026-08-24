from __future__ import annotations

import httpx

from app.connectors.chembl import ChEMBLConnector
from app.connectors.open_targets import OpenTargetsConnector
from app.connectors.pubchem import PubChemConnector
from app.connectors.structures import AlphaFoldConnector, RCSBConnector


def client_for(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def test_chembl_similarity_connector_parses_official_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/similarity/" in str(request.url)
        assert "/60.json" in str(request.url)
        return httpx.Response(
            200,
            json={
                "molecules": [
                    {
                        "molecule_chembl_id": "CHEMBL25",
                        "pref_name": "ASPIRIN",
                        "max_phase": 4,
                        "molecule_structures": {"canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O"},
                    }
                ]
            },
        )

    records = ChEMBLConnector(client_for(handler)).similar_molecules(
        "CC(=O)Oc1ccccc1C(=O)O",
        minimum_similarity_percent=60,
    )
    assert records[0].molecule_chembl_id == "CHEMBL25"
    assert records[0].canonical_smiles is not None


def test_pubchem_connector_parses_current_property_names() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/compound/name/aspirin/property/" in str(request.url)
        return httpx.Response(
            200,
            json={
                "PropertyTable": {
                    "Properties": [
                        {
                            "CID": 2244,
                            "Title": "Aspirin",
                            "ConnectivitySMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                            "SMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                            "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                            "MolecularFormula": "C9H8O4",
                            "MolecularWeight": "180.16",
                        }
                    ]
                }
            },
        )

    record = PubChemConnector(client_for(handler)).compound_by_name("aspirin")
    assert record.cid == 2244
    assert record.inchikey == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"


def test_open_targets_connector_filters_identifier_search_hits() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(
            200,
            json={
                "data": {
                    "search": {
                        "hits": [
                            {"id": "ENSG00000146648", "name": "EGFR", "entity": "target", "description": "receptor"},
                            {"id": "EFO_0003060", "name": "NSCLC", "entity": "disease", "description": "disease"},
                        ]
                    }
                }
            },
        )

    hits = OpenTargetsConnector(client_for(handler)).search("EGFR", entity="target")
    assert [item.entity_id for item in hits] == ["ENSG00000146648"]


def test_structure_connectors_parse_rcsb_and_alphafold_metadata() -> None:
    def rcsb_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/4WKQ")
        return httpx.Response(
            200,
            json={
                "struct": {"title": "EGFR kinase structure"},
                "rcsb_entry_info": {"resolution_combined": [1.85]},
            },
        )

    def alphafold_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/P00533")
        return httpx.Response(
            200,
            json=[
                {
                    "entryId": "AF-P00533-F1",
                    "modelCreatedDate": "2025-01-01",
                    "pdbUrl": "https://example.test/AF-P00533-F1.pdb",
                }
            ],
        )

    rcsb = RCSBConnector(client_for(rcsb_handler)).entry("4wkq")
    alphafold = AlphaFoldConnector(client_for(alphafold_handler)).prediction("p00533")
    assert rcsb.resolution_angstrom == 1.85
    assert alphafold.entry_id == "AF-P00533-F1"

