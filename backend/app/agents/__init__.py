"""Altı ajanın kuralları ve dil modeli çağrıları (docs/agent-specs.md).

Sohbet ajanları (Keşif, Tanımlama, firma kartı) ortak motoru paylaşır
(`sohbet_motoru.py`); diğerleri tek seferlik hesaplardır. Bu paket veritabanına
yazmaz; orkestrasyon `app/servisler/`'de.
"""
