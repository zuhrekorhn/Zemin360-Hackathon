import os

# app.main import sırasında ayarları okuyor (CORS için). Testler veritabanına
# bağlanmıyor, ama DATABASE_URL tanımlı olmalı — gerçek .env yoksa da çalışsın.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/zemin360")
