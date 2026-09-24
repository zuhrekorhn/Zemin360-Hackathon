from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.kesif import grafik_derle as kesif_grafigi_derle
from app.agents.tanimlama import grafik_derle as tanimlama_grafigi_derle
from app.api import (
    dogrulama,
    eslestirme,
    health,
    ihtiyac_kartlari,
    kesif,
    tanimlama,
    yetenek_kartlari,
)
from app.core.config import get_settings
from app.core.hatalar import hata_isleyicilerini_kur


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """İki sohbet grafiğini uygulama ömrü boyunca tek checkpointer'la paylaştırır.

    Checkpointer kendi tablolarını (checkpoints, checkpoint_writes…) `setup()`
    ile oluşturur; bunlar LangGraph'a ait olduğu için Alembic'e girmiyor.
    """
    ayarlar = get_settings()
    async with AsyncPostgresSaver.from_conn_string(ayarlar.checkpointer_url) as checkpointer:
        await checkpointer.setup()
        app.state.kesif_grafigi = kesif_grafigi_derle(checkpointer)
        app.state.tanimlama_grafigi = tanimlama_grafigi_derle(checkpointer)
        yield


app = FastAPI(
    title="Zemin360 API",
    description="Kurum–girişim ekosistemi için 6 uzman AI ajanı — ortak veri katmanı",
    version="0.1.0",
    lifespan=lifespan,
)

# Frontend (Next.js) farklı bir origin'den çağırıyor; bu olmadan tarayıcı
# istekleri sessizce düşürür. İzinli origin'ler .env'den (CORS_ORIGINS) okunur.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Yakalanmayan hatalar da CORS başlığıyla ve JSON gövdeyle dönsün
# (ayrıntı için app/core/hatalar.py).
hata_isleyicilerini_kur(app)

app.include_router(health.router)
app.include_router(kesif.router)
app.include_router(yetenek_kartlari.router)
app.include_router(tanimlama.router)
app.include_router(ihtiyac_kartlari.router)
app.include_router(eslestirme.router)
app.include_router(dogrulama.router)
