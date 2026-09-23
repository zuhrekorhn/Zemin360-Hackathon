from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    app_env: str = "development"
    # Frontend origin'leri, virgülle ayrılmış (CORS). Varsayılan: Next.js dev sunucusu.
    cors_origins: str = "http://localhost:3000"

    # Keşif/Tanımlama ajanlarının LLM'i (docs/architecture.md § Teknoloji Kararları)
    google_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    # Embedding sağlayıcısı (docs/matching-algorithm.md § 2)
    voyage_api_key: str = ""
    voyage_model: str = "voyage-4"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def checkpointer_url(self) -> str:
        """LangGraph checkpointer'ın bağlantı adresi — aynı veritabanı, psycopg sürücüsüyle.

        langgraph-checkpoint-postgres asyncpg'yi desteklemiyor; uygulama verisi
        (app/db/session.py) asyncpg üzerinden okunmaya devam ediyor.
        """
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    @field_validator("database_url")
    @classmethod
    def _asyncpg_surucusu_kullan(cls, v: str) -> str:
        # "postgresql://" yazılırsa da async sürücüye çevir
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
