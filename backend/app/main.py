from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import get_settings

app = FastAPI(
    title="Zemin360 API",
    description="Kurum–girişim ekosistemi için 6 uzman AI ajanı — ortak veri katmanı",
    version="0.1.0",
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
