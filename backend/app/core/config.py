from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    app_env: str = "development"
    # Frontend origin'leri, virgülle ayrılmış (CORS). Varsayılan: Next.js dev sunucusu.
    cors_origins: str = "http://localhost:3000"

    # LLM: Gemini, ücretli katman (docs/architecture.md § Teknoloji Kararları).
    # İki katman var; hangi işin hangisini kullandığı app/core/llm.py'de.
    # Model adları buradan okunur ki .env'den kod değişmeden değiştirilebilsin.
    google_api_key: str = ""
    # Hızlı katman: yapılandırılmış çıkarım (Keşif ve Tanımlama sohbetleri).
    gemini_hizli_model: str = "gemini-3.6-flash"
    gemini_hizli_yedek_model: str = "gemini-3.1-flash-lite"
    # Güçlü katman: gerekçeli akıl yürütme (eşleştirme gerekçesi, doğrulama
    # rubriği). Varsayılan kararlı (preview olmayan) bir model: demo günü
    # preview modelin hız sınırı ya da kaldırılması sürpriz çıkarmasın. Yeni
    # anahtarlara kararlı bir Pro açık değil (gemini-2.5-pro 404 dönüyor,
    # gemini-pro-latest 3.1-pro-preview'a gidiyor); bu yüzden şimdilik en yeni
    # kararlı Flash. Pro gerekip gerekmediği karşılaştırmayla belirlenecek.
    gemini_guclu_model: str = "gemini-3.8-flash"
    # Yedekler sağlayıcı arızası (5xx, zaman aşımı) ve anlık hız sınırı (429)
    # için: sorun model başına oluştuğu için başka model o an genellikle boşta.
    gemini_guclu_yedek_model: str = "gemini-3.6-flash"
    # Tek çağrı bu süreyi aşarsa yedek modele geçilir.
    gemini_zaman_asimi_sn: float = 30

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
