from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    service_name: str = "callforce-api"
    api_version: str = "v1"
    database_url: str = Field(
        default="postgresql://callforce:callforce@localhost:5432/callforce",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_storage_uri: str = Field(default="", alias="RATE_LIMIT_STORAGE_URI")
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_collection_name: str = Field(
        default="callforce_knowledge_chunks",
        alias="QDRANT_COLLECTION_NAME",
    )
    qdrant_vector_size: int = Field(default=384, alias="QDRANT_VECTOR_SIZE")
    qdrant_distance: str = Field(default="Cosine", alias="QDRANT_DISTANCE")
    llm_provider: str = Field(default="auto", alias="LLM_PROVIDER")
    llm_max_tokens: int = Field(default=1024, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")
    # Feature Flags
    enable_voice_agents: bool = Field(default=True, alias="ENABLE_VOICE_AGENTS")
    enable_whatsapp_channel: bool = Field(default=True, alias="ENABLE_WHATSAPP_CHANNEL")


    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_fast_model: str = Field(default="gpt-4o-mini", alias="OPENAI_FAST_MODEL")
    openai_smart_model: str = Field(default="gpt-4o", alias="OPENAI_SMART_MODEL")
    access_token_secret: str = Field(
        default="local-development-token-secret",
        alias="ACCESS_TOKEN_SECRET",
    )
    fernet_key: str = Field(default="", alias="FERNET_KEY")
    access_token_ttl_minutes: int = Field(default=15, alias="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=30, alias="REFRESH_TOKEN_TTL_DAYS")
    store_backend: str = Field(default="sqlalchemy", alias="STORE_BACKEND")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    allow_legacy_tenant_header: bool = Field(
        default=False,
        alias="ALLOW_LEGACY_TENANT_HEADER",
    )
    seed_demo_data: bool = Field(default=True, alias="SEED_DEMO_DATA")
    demo_tenant_id: str = Field(
        default="00000000-0000-0000-0000-000000000001",
        alias="DEMO_TENANT_ID",
    )
    api_public_url: str = Field(default="http://localhost:8000", alias="API_PUBLIC_URL")
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")
    yandex_api_key: str = Field(default="", alias="YANDEX_API_KEY")

    # Payment / YooKassa
    yookassa_shop_id: str = Field(default="", alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(default="", alias="YOOKASSA_SECRET_KEY")
    iiko_api_login: str = Field(default="", alias="IIKO_API_LOGIN")
    iiko_api_password: str = Field(default="", alias="IIKO_API_PASSWORD")
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(default="", alias="TWILIO_PHONE_NUMBER")
    asterisk_ari_username: str = Field(default="", alias="ASTERISK_ARI_USERNAME")
    asterisk_ari_password: str = Field(default="", alias="ASTERISK_ARI_PASSWORD")
    vllm_base_url: str = Field(default="", alias="VLLM_BASE_URL")
    vllm_api_key: str = Field(default="not-needed", alias="VLLM_API_KEY")
    vllm_model: str = Field(default="Qwen/Qwen2.5-7B-Instruct", alias="VLLM_MODEL")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )

    # SMTP
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="noreply@callforce.local", alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")

    @model_validator(mode="after")
    def _validate_qdrant_for_prod(self) -> "Settings":
        """Fail fast: production requires a real Qdrant URL."""
        if self.app_env not in ("local", "test", "development") and not self.qdrant_url:
            raise ValueError(
                "QDRANT_URL is required for non-local environments. "
                "Set QDRANT_URL to your Qdrant instance (e.g. http://qdrant:6333)."
            )
        return self

    @property
    def effective_qdrant_url(self) -> str:
        """Return :memory: for local/test when QDRANT_URL is not set."""
        if not self.qdrant_url and self.app_env in ("local", "test", "development"):
            return ":memory:"
        return self.qdrant_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
