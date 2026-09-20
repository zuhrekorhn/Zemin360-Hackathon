from fastapi import FastAPI

from app.api import health

app = FastAPI(
    title="Zemin360 API",
    description="Kurum–girişim ekosistemi için 6 uzman AI ajanı — ortak veri katmanı",
    version="0.1.0",
)

app.include_router(health.router)
