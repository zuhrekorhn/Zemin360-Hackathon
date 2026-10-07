"""Dış servis arayüzleri ve kurulumu (docs/dogrulama.md § 14.4).

Her servis bir arayüzün arkasındadır, bir `.env` bayrağı vardır ve hatası akışı
düşürmez. Somut sınıflar yalnızca `kurulum.py`'de seçilir.
"""

from app.core.dis_servisler.eposta import Eposta, EpostaGonderici, dusmeden_gonder
from app.core.dis_servisler.kurulum import eposta_gonderici, servis_kipleri

__all__ = ["Eposta", "EpostaGonderici", "dusmeden_gonder", "eposta_gonderici", "servis_kipleri"]
