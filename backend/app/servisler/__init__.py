"""Servis katmanı: birden fazla uç noktanın ve arka plan işinin paylaştığı orkestrasyon.

Katmanlar (docs/architecture.md):
  - app/agents/    saf kurallar ve LLM çağrıları (karar burada, veritabanı yok)
  - app/servisler/ veritabanı, bildirim ve kuralları bir araya getiren işler
  - app/api/       uç noktalar: yetki, istek/yanıt şeması, servisi çağırma

Uç nokta ince kalır; aynı iş iki uçta ya da bir uçla bir arka plan işinde
yazılmaz.
"""
