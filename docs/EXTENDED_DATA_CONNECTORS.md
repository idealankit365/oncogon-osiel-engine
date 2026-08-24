# Extended scientific data connectors

## What is implemented

OSIEL now has executable connector code for all ten requested sources. The
connector control center is visible under **Evidence sources** and the Python
API exposes configuration status before any fetch is attempted.

| Source | Connection | Raw-data handling | Scientific boundary |
|---|---|---|---|
| NCI-60 / CellMiner | Approved release URL | Bounded download, SHA-256, immutable storage, preview | Preserved as a distinct cell-line assay domain |
| Therapeutics Data Commons | Official PyTDC package | Bounded dataframe snapshot stored as CSV | Dataset-specific terms and split policy still apply |
| COCONUT 2.0 | Approved CSV/SDF/database export URL | Checksum-controlled bulk snapshot | Organism and upstream-source provenance retained |
| NPASS | Approved NPASS release-file URL | Checksum-controlled bulk snapshot | Structure, activity, target and species files remain separate evidence tables |
| ANPDB | Approved downloadable release URL | Checksum-controlled bulk snapshot | African organism, geography, traditional use and literature are first-class provenance |
| LOTUS | Approved export URL | Checksum-controlled bulk snapshot | Occurrence is not proof of efficacy or availability |
| Tox21 | Approved public-data release URL | Checksum-controlled bulk snapshot | Assay, sample and curve/QC metadata must be retained |
| EPA ToxCast | Approved invitrodb release URL | Checksum-controlled bulk snapshot | invitrodb version and endpoint flags remain attached |
| UniProt | Official UniProtKB REST API | Bounded reviewed-entry search | Accessions and sequence versions are preserved |
| Chemspace | Licensed, operator-configured API | Bounded API response | Availability, price, purity, salt/form and lead time need supplier verification |

## Why bulk connectors require configuration

Several publishers expose a download page rather than a permanent versioned
API URL. OSIEL never scrapes that page or guesses which file is scientifically
appropriate. A university data steward selects a release, reviews its terms,
copies the direct HTTPS file URL and records the official checksum.

```dotenv
OSIEL_SOURCE_CONNECTORS_ENABLED=true
OSIEL_SOURCE_CONNECTOR_MAX_BYTES=100000000

OSIEL_NCI60_BULK_URL=https://approved-provider.example/release.csv
OSIEL_NCI60_BULK_SHA256=<64-lowercase-hex-characters>
```

The same `*_BULK_URL` and `*_BULK_SHA256` pair exists for COCONUT, NPASS,
ANPDB, LOTUS, Tox21 and ToxCast in `.env.example`.

Without an expected checksum the payload is still preserved, but its state is
`quarantined-checksum-required`. A mismatch becomes
`quarantined-checksum-mismatch`. Neither state can become training data.

## TDC

Install the optional pinned official-library adapter:

```bash
pip install -r backend/requirements-connectors.txt
```

The reference endpoint permits the `ADME`, `Tox` and `HTS` groups. Each dataset
snapshot is limited to 10,000 records and remains quarantined until its original
licence, task definition, label semantics and split policy are reviewed.

## Chemspace

Chemspace requires registration and a provider-issued API key. Copy the path
from the interactive contract supplied for that key; OSIEL deliberately does
not guess a licensed route or authentication contract.

```dotenv
OSIEL_CHEMSPACE_API_BASE_URL=https://api.chem-space.com
OSIEL_CHEMSPACE_SEARCH_PATH=<provider-documented-path>
OSIEL_CHEMSPACE_API_KEY=<secret>
```

Never commit the key. The browser never receives it; only the Python service
calls Chemspace.

## API routes

```text
GET  /v1/data-connectors
POST /v1/data-connectors/bulk/{source_code}/fetch
POST /v1/data-connectors/tdc/fetch
POST /v1/data-connectors/uniprot/search
POST /v1/data-connectors/chemspace/search
GET  /v1/data-connectors/jobs/{job_id}
```

Example bulk fetch:

```bash
curl -X POST http://localhost:8000/v1/data-connectors/bulk/nci60/fetch \
  -H 'Content-Type: application/json' \
  -H 'X-OSIEL-Actor: researcher@example.edu' \
  -d '{"release_id":"2025.3","max_preview_records":25}'
```

Example UniProt search:

```bash
curl -X POST http://localhost:8000/v1/data-connectors/uniprot/search \
  -H 'Content-Type: application/json' \
  -H 'X-OSIEL-Actor: researcher@example.edu' \
  -d '{"query":"gene:EGFR AND organism_id:9606","limit":10,"reviewed_only":true}'
```

## Ingestion state machine

```text
operator-approved release -> bounded fetch -> immutable raw artifact
-> checksum decision -> source parser -> canonical schema
-> structure/assay QC -> quarantine or accepted curated dataset
-> independent scientific approval -> eligible challenger dataset
```

Fetched rows never enter a model automatically. This layer solves lawful,
traceable data acquisition; it does not by itself validate an oncology model.

## Authoritative provider pages

- CellMiner: <https://discover.nci.nih.gov/cellminer/loadDownload.do>
- TDC: <https://tdcommons.ai/>
- COCONUT: <https://coconut.naturalproducts.net/download>
- NPASS: <https://bidd.group/NPASS/downloadnpass.html>
- ANPDB: <https://african-compounds.org>
- LOTUS: <https://lotus.naturalproducts.net/download>
- Tox21 public data: <https://tripod.nih.gov/tox21/pubdata>
- EPA ToxCast: <https://www.epa.gov/comptox-tools/exploring-toxcast-data>
- UniProt programmatic access: <https://www.uniprot.org/help/programmatic_access>
- Chemspace API: <https://chem-space.com/purchasing-saas/chemspace-api>
