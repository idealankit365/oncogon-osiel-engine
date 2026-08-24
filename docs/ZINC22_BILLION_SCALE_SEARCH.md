# Live multi-billion compound search

## What OSIEL searches

OSIEL now performs a real, bounded structure query through the public SmallWorld service used by the CartBlanche/ZINC ecosystem. The remote provider—not the local workstation—holds and searches the index. OSIEL sends one canonical seed SMILES, requests at most 100 graph-neighbour hits, and then runs local RDKit standardization, identity deduplication, Morgan similarity, QED, Rule-of-Five and PAINS/Brenk/NIH checks on the returned shortlist.

On 22 August 2026 the live provider advertised and OSIEL verified this configured map:

| Field | Live value |
|---|---:|
| Map key | `REALDB-2025-07.smi.anon` |
| Provider label | `REALDB-25Q3-9.4B` |
| Indexed entries | 10,102,659,506 |
| Mapped/searchable entries | 9,425,750,819 |
| Status | Available |

These numbers are not hard-coded into an experiment result. The connector reads `/search/maps` at execution time, refuses an unavailable or unknown map, and stores the provider-reported values with the run. Coverage and map names can change.

The 2023 ZINC-22 publication separately reported more than 37 billion searchable 2D make-on-demand structures across its federated collection. A single configured SmallWorld map is not the entire ZINC-22 universe.

## Verified live run

The executable smoke test queried aspirin with graph distance 2, anonymous distance 1 and limit 25:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/e2e_zinc22.py
```

The 22 August 2026 run completed in approximately eight seconds, returned 24 remote structures, retained 24 after RDKit checks, and recorded response SHA-256 `dc2af910c35e69875ac2f9c3748ece1ea40605a779f6b405244eac126c02a94e`.

This is a service-availability smoke test, not a permanent golden result. Provider data and ranking order can change. Unit tests use a fixed transport fixture and do not call the public service.

## Enable the connector

Keep live search off in offline tests. For a research workstation, set a contact-bearing user agent and opt in:

```bash
OSIEL_ZINC22_ENABLED=true
OSIEL_ZINC22_BASE_URL=https://sw.docking.org
OSIEL_ZINC22_MAP=REALDB-2025-07.smi.anon
OSIEL_ZINC22_TIMEOUT_SECONDS=45
OSIEL_PUBLIC_CONNECTOR_USER_AGENT="Oncogon-OSIEL/0.2 research-use (contact: lab@example.edu)"
```

Restart the Python API, open **Open discovery**, finish a seed run, and use **ZINC-22 / CartBlanche SmallWorld**.

## API

Start a bounded query:

```bash
curl -X POST http://localhost:8000/v1/zinc22/searches \
  -H 'Content-Type: application/json' \
  -H 'X-OSIEL-Actor: student@example.edu' \
  -d '{
    "seed_smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "graph_distance": 2,
    "anonymous_distance": 1,
    "max_results": 25
  }'
```

Related routes:

- `GET /v1/zinc22/capabilities`
- `POST /v1/zinc22/searches`
- `GET /v1/zinc22/searches/{job_id}`
- `POST /v1/zinc22/searches/{job_id}/refresh` (stable no-resubmit contract; direct jobs are already final)

Each completed record includes the map key/name/counts, canonical seed, remote query ID, returned and quarantined counts, bounded candidates, local descriptor/alert results, response checksum, timestamps and scientific boundary.

## What “searched ten billion” means

It means the query was executed by a remote provider against a map whose metadata reported 10.10 billion entries. It does **not** mean:

- ten billion structures were downloaded, scored by RDKit, docked, or stored locally;
- every ZINC-22 catalogue was searched;
- the hit is in stock, purchasable, novel, patented, pure, safe or successfully synthesizable;
- the hit binds a target or affects a cell line;
- SmallWorld graph distance is a validated oncology-activity model.

Current REALDB results can use provider catalogue identifiers such as `s_...`; OSIEL therefore calls the field `remote_id`, not `zinc_id`.

## Safety and load controls

- one seed structure per job;
- graph and anonymous distances limited to 0–3;
- 5–100 imported hits;
- advertised-map validation before search;
- HTTPS-only operator-configured base URL;
- 10 MB response ceiling;
- canonicalization and identity deduplication;
- invalid structures quarantined;
- immutable result checksum and audit event;
- no crawler, bulk enumeration, automatic purchase or fake fallback.

Before shared or high-volume use, confirm the provider’s current policy, add caching and institutional rate limits, and coordinate with the service owner. Free query access does not make physical compounds or high-throughput docking free.

## Sources

- [ZINC-22 paper](https://doi.org/10.1021/acs.jcim.2c01253)
- [CartBlanche22 interface](https://cartblanche22.docking.org/)
- [Public SmallWorld map metadata](https://sw.docking.org/search/maps)
- [CartBlanche22 source repository](https://github.com/docking-org/cartblanche22)

