from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.kesif import grafik_derle
from app.api import health, kesif, yetenek_kartlari
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Keşif grafiğini uygulama ömrü boyunca tek bir checkpointer'la paylaştırır.

    Checkpointer kendi tablolarını (checkpoints, checkpoint_writes…) `setup()`
    ile oluşturur; bunlar LangGraph'a ait olduğu için Alembic'e girmiyor.
    """
    ayarlar = get_settings()
    async with AsyncPostgresSaver.from_conn_string(ayarlar.checkpointer_url) as checkpointer:
        await checkpointer.setup()
        app.state.kesif_grafigi = grafik_derle(checkpointer)
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

app.include_router(health.router)
app.include_router(kesif.router)
app.include_router(yetenek_kartlari.router)
