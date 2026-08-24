from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Oncogon AI OSIEL"
    api_version: str = "v1"
    standardization_version: str = "OSIEL-STD-1.0.0"
    feature_version: str = "ECFP4-2048-CHIRAL-1.0.0"
    model_version: str = "osiel-demo-baseline-1.0.0"
    ranking_policy_version: str = "natural-product-discovery-1.0.0"
    demo_mode: bool = os.getenv("OSIEL_DEMO_MODE", "true").lower() == "true"
    api_key: str | None = os.getenv("OSIEL_API_KEY")
    public_connectors_enabled: bool = (
        os.getenv("OSIEL_PUBLIC_CONNECTORS_ENABLED", "false").lower() == "true"
    )
    public_connector_timeout_seconds: float = float(
        os.getenv("OSIEL_PUBLIC_CONNECTOR_TIMEOUT_SECONDS", "12")
    )
    public_connector_user_agent: str = os.getenv(
        "OSIEL_PUBLIC_CONNECTOR_USER_AGENT",
        "Oncogon-OSIEL/0.2 research-use (configure-contact-before-shared-deployment)",
    )
    source_connectors_enabled: bool = (
        os.getenv("OSIEL_SOURCE_CONNECTORS_ENABLED", "false").lower() == "true"
    )
    source_connector_max_bytes: int = max(
        1_000_000,
        min(500_000_000, int(os.getenv("OSIEL_SOURCE_CONNECTOR_MAX_BYTES", "100000000"))),
    )
    nci60_bulk_url: str = os.getenv("OSIEL_NCI60_BULK_URL", "")
    nci60_bulk_sha256: str = os.getenv("OSIEL_NCI60_BULK_SHA256", "")
    coconut_bulk_url: str = os.getenv("OSIEL_COCONUT_BULK_URL", "")
    coconut_bulk_sha256: str = os.getenv("OSIEL_COCONUT_BULK_SHA256", "")
    npass_bulk_url: str = os.getenv("OSIEL_NPASS_BULK_URL", "")
    npass_bulk_sha256: str = os.getenv("OSIEL_NPASS_BULK_SHA256", "")
    anpdb_bulk_url: str = os.getenv("OSIEL_ANPDB_BULK_URL", "")
    anpdb_bulk_sha256: str = os.getenv("OSIEL_ANPDB_BULK_SHA256", "")
    lotus_bulk_url: str = os.getenv("OSIEL_LOTUS_BULK_URL", "")
    lotus_bulk_sha256: str = os.getenv("OSIEL_LOTUS_BULK_SHA256", "")
    tox21_bulk_url: str = os.getenv("OSIEL_TOX21_BULK_URL", "")
    tox21_bulk_sha256: str = os.getenv("OSIEL_TOX21_BULK_SHA256", "")
    toxcast_bulk_url: str = os.getenv("OSIEL_TOXCAST_BULK_URL", "")
    toxcast_bulk_sha256: str = os.getenv("OSIEL_TOXCAST_BULK_SHA256", "")
    chemspace_api_base_url: str = os.getenv(
        "OSIEL_CHEMSPACE_API_BASE_URL", "https://api.chem-space.com"
    )
    chemspace_search_path: str = os.getenv("OSIEL_CHEMSPACE_SEARCH_PATH", "")
    chemspace_api_key: str | None = os.getenv("OSIEL_CHEMSPACE_API_KEY") or None
    vina_enabled: bool = os.getenv("OSIEL_VINA_ENABLED", "false").lower() == "true"
    vina_max_cpu: int = max(1, min(16, int(os.getenv("OSIEL_VINA_MAX_CPU", "4"))))
    vina_max_timeout_seconds: int = max(
        30,
        min(3600, int(os.getenv("OSIEL_VINA_MAX_TIMEOUT_SECONDS", "600"))),
    )
    vina_max_receptor_bytes: int = max(
        1_000_000,
        min(50_000_000, int(os.getenv("OSIEL_VINA_MAX_RECEPTOR_BYTES", "15000000"))),
    )
    vina_max_ligand_bytes: int = max(
        100_000,
        min(10_000_000, int(os.getenv("OSIEL_VINA_MAX_LIGAND_BYTES", "3000000"))),
    )
    ollama_enabled: bool = os.getenv("OSIEL_OLLAMA_ENABLED", "false").lower() == "true"
    ollama_base_url: str = os.getenv("OSIEL_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OSIEL_OLLAMA_MODEL", "qwen3:8b")
    ollama_embedding_model: str = os.getenv(
        "OSIEL_OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b"
    )
    ollama_timeout_seconds: float = max(
        10,
        min(300, float(os.getenv("OSIEL_OLLAMA_TIMEOUT_SECONDS", "120"))),
    )
    professor_ingestion_enabled: bool = (
        os.getenv("OSIEL_PROFESSOR_INGESTION_ENABLED", "false").lower() == "true"
    )
    professor_max_document_bytes: int = max(
        100_000,
        min(50_000_000, int(os.getenv("OSIEL_PROFESSOR_MAX_DOCUMENT_BYTES", "20000000"))),
    )
    professor_max_pages: int = max(
        1,
        min(1000, int(os.getenv("OSIEL_PROFESSOR_MAX_PAGES", "500"))),
    )
    professor_max_chunks: int = max(
        10,
        min(10_000, int(os.getenv("OSIEL_PROFESSOR_MAX_CHUNKS", "2000"))),
    )
    professor_retrieval_k: int = max(
        3,
        min(20, int(os.getenv("OSIEL_PROFESSOR_RETRIEVAL_K", "8"))),
    )
    professor_retention_days: int = max(
        1,
        min(3650, int(os.getenv("OSIEL_PROFESSOR_RETENTION_DAYS", "180"))),
    )
    zinc22_enabled: bool = os.getenv("OSIEL_ZINC22_ENABLED", "false").lower() == "true"
    zinc22_base_url: str = os.getenv(
        "OSIEL_ZINC22_BASE_URL", "https://sw.docking.org"
    )
    zinc22_map: str = os.getenv("OSIEL_ZINC22_MAP", "REALDB-2025-07.smi.anon")
    zinc22_timeout_seconds: float = max(
        5,
        min(120, float(os.getenv("OSIEL_ZINC22_TIMEOUT_SECONDS", "45"))),
    )
    zinc22_min_poll_seconds: int = max(
        3,
        min(60, int(os.getenv("OSIEL_ZINC22_MIN_POLL_SECONDS", "5"))),
    )
    model_lab_enabled: bool = os.getenv("OSIEL_MODEL_LAB_ENABLED", "false").lower() == "true"
    model_lab_max_records: int = max(
        100,
        min(10_000, int(os.getenv("OSIEL_MODEL_LAB_MAX_RECORDS", "2000"))),
    )
    model_lab_max_candidates: int = max(
        20,
        min(2000, int(os.getenv("OSIEL_MODEL_LAB_MAX_CANDIDATES", "500"))),
    )
    multimodal_enabled: bool = (
        os.getenv("OSIEL_MULTIMODAL_ENABLED", "false").lower() == "true"
    )
    multimodal_timeout_seconds: float = max(
        5,
        min(300, float(os.getenv("OSIEL_MULTIMODAL_TIMEOUT_SECONDS", "90"))),
    )
    multimodal_max_response_bytes: int = max(
        10_000,
        min(5_000_000, int(os.getenv("OSIEL_MULTIMODAL_MAX_RESPONSE_BYTES", "1000000"))),
    )
    chem_model_url: str = os.getenv("OSIEL_CHEM_MODEL_URL", "")
    chem_model_name: str = os.getenv("OSIEL_CHEM_MODEL_NAME", "chemprop-dmpnn")
    protein_model_url: str = os.getenv("OSIEL_PROTEIN_MODEL_URL", "")
    protein_model_name: str = os.getenv("OSIEL_PROTEIN_MODEL_NAME", "esm")
    vision_model_url: str = os.getenv("OSIEL_VISION_MODEL_URL", "")
    vision_model_name: str = os.getenv("OSIEL_VISION_MODEL_NAME", "cellprofiler-adapter")
    multimodal_api_token: str | None = os.getenv("OSIEL_MULTIMODAL_API_TOKEN") or None
    object_store_path: Path = Path(
        os.getenv("OSIEL_OBJECT_STORE_PATH", Path(__file__).parent.parent / "data" / "objects")
    )
    allowed_roles: tuple[str, ...] = ("student", "researcher", "technician", "reviewer", "instructor", "admin")
    database_path: Path = Path(
        os.getenv("OSIEL_DATABASE_PATH", Path(__file__).parent.parent / "data" / "osiel.db")
    )
    seed_path: Path = Path(
        os.getenv("OSIEL_SEED_PATH", Path(__file__).parent / "data" / "compounds.json")
    )
    cors_origins: tuple[str, ...] = tuple(
        value.strip()
        for value in os.getenv(
            "OSIEL_CORS_ORIGINS", "http://localhost:3000,http://localhost:4173"
        ).split(",")
        if value.strip()
    )


settings = Settings()
