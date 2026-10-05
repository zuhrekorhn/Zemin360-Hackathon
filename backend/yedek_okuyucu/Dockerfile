# Yedek okuyucu servisi (Railway'de ayrı servis). Derleme bağlamı: backend/
#   docker build -f yedek_okuyucu/Dockerfile -t zemin360-yedek-okuyucu .
# İmajdaki Playwright sürümü requirements.txt'tekiyle aynı olmalı (tarayıcı imajla gelir).
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /srv
COPY yedek_okuyucu/requirements.txt yedek_okuyucu/requirements.txt
RUN pip install --no-cache-dir -r yedek_okuyucu/requirements.txt

# SSRF kuralları backend'le tek kaynak: yalnızca o dosya kopyalanır.
COPY app/__init__.py app/__init__.py
COPY app/core/__init__.py app/core/__init__.py
COPY app/core/guvenli_istek.py app/core/guvenli_istek.py
COPY yedek_okuyucu/ yedek_okuyucu/

# Tarayıcı kök olmayan kullanıcıyla çalışır (imajdaki pwuser).
USER pwuser
ENV YEDEK_OKUYUCU_HOST=0.0.0.0 PYTHONUNBUFFERED=1
CMD ["python", "-m", "yedek_okuyucu"]
