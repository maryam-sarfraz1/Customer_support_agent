"""Environment-based application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["openai", "gemini", "ollama", "fake"]
VectorStoreBackend = Literal["chroma", "memory"]


class Settings(BaseSettings):
    """All runtime configuration, sourced from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "Enterprise AI Customer Support Agent"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = True

    # --- Security ---
    secret_key: str = Field(
        default="change-me-in-production",
        description="HMAC secret for JWT signing.",
    )
    access_token_expire_minutes: int = 60 * 8
    jwt_algorithm: str = "HS256"
    allowed_origins: list[str] = ["*"]
    rate_limit_per_minute: int = 60

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/support.db"

    # --- LLM ---
    llm_provider: LLMProvider = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_fast_model: str = Field(
        default="",
        description=(
            "Optional smaller/faster model for classification steps "
            "(query understanding, verification). Falls back to llm_model."
        ),
    )
    llm_temperature: float = 0.1
    openai_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # --- Embeddings ---
    embedding_provider: LLMProvider = "openai"
    embedding_model: str = "text-embedding-3-small"

    # --- RAG / vector store ---
    vector_store: VectorStoreBackend = "chroma"
    chroma_persist_dir: str = "./data/chroma"
    collection_name: str = "support_kb"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_top_k: int = 5
    confidence_threshold: float = 0.55

    # --- Integrations ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = "support@example.com"
    email_enabled: bool = False

    slack_webhook_url: str = ""
    slack_signing_secret: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    # --- White-label branding (customer chat page / widget) ---
    company_name: str = "Acme Cloud"
    brand_color: str = "#2f6f5f"
    chat_greeting: str = "Hi! I'm the support assistant. Ask me anything about our products, orders, or billing."

    # --- Bootstrap admin user ---
    admin_email: str = "admin@example.com"
    admin_password: str = "admin-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
