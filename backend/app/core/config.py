from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Gemini 3 `thinking_level` değerleri; "" = modelin kendi varsayılanı.
DUSUNME_SEVIYELERI = ("", "minimal", "low", "medium", "high")
# HS256 için anahtar en az 256 bit olmalı; 32 karakter bunun alt sınırı.
JWT_ANAHTAR_EN_AZ = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    app_env: str = "development"
    # Frontend origin'leri, virgülle ayrılmış (CORS). Varsayılan: Next.js dev sunucusu.
    cors_origins: str = "http://localhost:3000"

    # Kimlik (docs/faz-b-kimlik-ve-dongu.md § 1). JWT'yi imzalayan gizli anahtar.
    # Varsayılanı YOK: tanımlı değilse uygulama açılmaz — tahmin edilebilir bir
    # anahtarla imzalanmış token herkesin her hesabı taklit etmesine izin verir.
    jwt_gizli_anahtar: str
    # Demo hesaplarının ortak şifresi (scripts/demo_hesaplari.py). Yalnızca betik
    # okur; repoda şifre yok. Boşsa betik çalışmaz.
    demo_sifresi: str = ""
    # Canlılık taraması için cron kimliği (docs/faz-d-canlilik.md § 4). Canlıdaki
    # zamanlanmış görev `POST /canlilik/tarama`'yı `X-Tarama-Anahtari` başlığıyla
    # çağırır — kullanıcı token'ı değil: GİRVAK'ın token'ı 7 günde düşer ve tarama
    # sessizce durur. Boşsa başlık yolu kapalıdır, uç yalnızca GİRVAK token'ıyla.
    tarama_anahtari: str = ""

    # LLM: Gemini, ücretli katman (docs/architecture.md § Teknoloji Kararları).
    # İki katman var; hangi işin hangisini kullandığı app/core/llm.py'de.
    # Model adları buradan okunur ki .env'den kod değişmeden değiştirilebilsin.
    google_api_key: str = ""
    # Hızlı katman: yapılandırılmış çıkarım (Keşif ve Tanımlama sohbetleri).
    gemini_hizli_model: str = "gemini-3.6-flash"
    gemini_hizli_yedek_model: str = "gemini-3.1-flash-lite"
    # Hızlı katmanın düşünme seviyesi (Gemini 3 `thinking_level`); boş = modelin
    # varsayılanı. Güçlü katmana uygulanmaz. "minimal" ölçümle seçildi: modelin
    # varsayılanında çıktının %70-90'ı düşünmeydi (tur ~6 sn), üstelik iki
    # koşuda da kullanıcının söylemediği "tek başına yazdı" bilgisini taslağa
    # ekledi. minimal'de tur ~2 sn, uydurma yok, taslak aynı ya da daha iyi.
    gemini_hizli_dusunme: str = "minimal"
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
    # Kanıt okuma: GitHub API uygulama tokenı (yalnızca okuma). Boşsa anonim (saatte 60 istek).
    github_token: str = ""

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

    @field_validator("gemini_hizli_dusunme")
    @classmethod
    def _dusunme_seviyesi_gecerli(cls, v: str) -> str:
        # Yanlış yazılmış bir seviye sessizce yok sayılmasın: açılışta durdur.
        v = v.strip().lower()
        if v not in DUSUNME_SEVIYELERI:
            gecerliler = ", ".join(repr(s) for s in DUSUNME_SEVIYELERI)
            raise ValueError(f"GEMINI_HIZLI_DUSUNME={v!r} geçersiz. Geçerli değerler: {gecerliler}")
        return v

    @field_validator("jwt_gizli_anahtar")
    @classmethod
    def _jwt_anahtari_yeterince_uzun(cls, v: str) -> str:
        if len(v) < JWT_ANAHTAR_EN_AZ:
            raise ValueError(
                f"JWT_GIZLI_ANAHTAR en az {JWT_ANAHTAR_EN_AZ} karakter olmalı. Üretmek için: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return v

    @field_validator("tarama_anahtari")
    @classmethod
    def _tarama_anahtari_bos_ya_da_uzun(cls, v: str) -> str:
        v = v.strip()
        if v and len(v) < JWT_ANAHTAR_EN_AZ:
            raise ValueError(
                f"TARAMA_ANAHTARI ya boş olmalı ya da en az {JWT_ANAHTAR_EN_AZ} karakter. "
                'Üretmek için: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return v

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
