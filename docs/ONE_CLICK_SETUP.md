# OSIEL one-click setup

## Prerequisite

Install Docker Desktop on Windows/macOS, or Docker Engine with Compose v2 on
Linux. Allocate at least 8 GB RAM for the base application. The optional Qwen
model download needs additional disk/RAM/VRAM.

## Start the complete base application

macOS, Linux or WSL2:

```bash
./start-osiel.sh
```

Windows PowerShell:

```powershell
.\start-osiel.ps1
```

The script creates `.env` from `.env.docker.example` only when missing, builds
the frontend and API images, installs pinned Node/Python dependencies, creates
the database/object volumes and waits for healthy services.

Open:

- Workbench: <http://localhost:3000>
- Python API documentation: <http://localhost:8000/v1/docs>
- OpenAPI JSON: <http://localhost:8000/v1/openapi.json>
- API health: <http://localhost:8000/health>

## Start with local AI Professor models

```bash
./start-osiel.sh --with-ai
```

This additionally starts the official Ollama image and downloads the configured
Qwen chat and embedding model tags. On the known RTX 4070 Ti 12 GB workstation,
Qwen3-8B is the supported local target; the initial download can take time.
The AI Professor remains citation-bound and cannot authorize laboratory work.

For the RTX 4070 Ti workstation with NVIDIA Container Toolkit support:

```bash
./start-osiel.sh --with-ai-gpu
```

PowerShell:

```powershell
.\start-osiel.ps1 --with-ai
```

## Stop without deleting data

```bash
./stop-osiel.sh
```

Database, immutable objects and model cache remain in named Docker volumes.
The stop script intentionally refuses a `--purge` shortcut. Volume deletion is
a manual, backup-aware operation.

## Useful commands

```bash
make up
make up-ai
make up-ai-gpu
make logs
make down
make verify
make package
```

Equivalent npm scripts are `docker:up`, `docker:up:ai`, `docker:logs`,
`docker:down`, `verify:handoff` and `package:handoff`.

## Safe default behaviour

The first launch is a complete local research reference, but outbound source
downloads, document ingestion, Vina execution, model training and specialist
multimodal endpoints remain disabled. Enable each only after configuring its
licence, checksum, credentials and validation gate in `.env`.

PostgreSQL and MinIO are provided under the `future-infra` Compose profile as
infrastructure targets only. The working reference API currently uses SQLite
and content-addressed local object storage; it does not falsely claim that the
future services are already wired into persistence.
