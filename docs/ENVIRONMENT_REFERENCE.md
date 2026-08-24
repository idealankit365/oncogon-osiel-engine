# OSIEL environment reference

Use `.env.docker.example` for Docker and `.env.example` for direct local
development. Copy one to `.env`; never commit secrets.

| Group | Variables | Rule |
|---|---|---|
| Frontend/API | `NEXT_PUBLIC_OSIEL_API_URL`, `OSIEL_WEB_PORT`, `OSIEL_API_PORT`, `OSIEL_CORS_ORIGINS` | only the API URL is browser-visible |
| Runtime | `OSIEL_DEMO_MODE`, `OSIEL_API_KEY`, database/object paths | demo mode is research reference only |
| Public APIs | `OSIEL_PUBLIC_CONNECTORS_*` | use institutional contact and current provider policy |
| Bulk sources | `OSIEL_*_BULK_URL`, `OSIEL_*_BULK_SHA256` | direct approved HTTPS release plus expected checksum |
| Chemspace | `OSIEL_CHEMSPACE_*` | licensed server-side key/path only |
| ZINC22 | `OSIEL_ZINC22_*` | bounded remote search; never crawl the map |
| Vina | `OSIEL_VINA_*` | prepared inputs, CPU/time limits and benchmark gate |
| Model lab | `OSIEL_MODEL_LAB_*` | bounded endpoint snapshot and no auto-promotion |
| Professor | `OSIEL_OLLAMA_*`, `OSIEL_PROFESSOR_*` | citation-bound generation and approved documents |
| Multimodal | `OSIEL_MULTIMODAL_*`, specialist URLs/names/token | HTTPS/loopback, structured result and version required |
| Images | `OLLAMA_IMAGE`, `MINIO_IMAGE` | pin immutable digests for controlled releases |

The committed examples intentionally contain no working credentials, licensed
download URLs or institutional secrets. Disabled features report their exact
missing configuration through capability endpoints.
