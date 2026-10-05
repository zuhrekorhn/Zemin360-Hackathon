"""Tüm modeller burada import edilir — Alembic autogenerate ve relationship çözümü için şart."""

from app.db.base import Base
from app.models.bagli_hesap import BagliHesap, ProfilKodu
from app.models.bildirim import Bildirim
from app.models.canlilik_olayi import CanlilikOlayi
from app.models.eposta_dogrulama import EpostaDogrulama
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.gozlem import DegerlendirmeGozlemi, KanitGozlemi, ServisGunlugu
from app.models.guven_skoru import GuvenSkoru
from app.models.hesap import Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.inceleme_isareti import IncelemeIsareti
from app.models.isbirligi import Isbirligi
from app.models.kanit_parcasi import KanitMetinParcasi, KanitParcasi
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.milestone import Milestone
from app.models.referans_istegi import ReferansIstegi
from app.models.servis_kullanimi import ServisKullanimi
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_kaniti import YetenekKaniti
from app.models.yetenek_karti import YetenekKarti

__all__ = [
    "BagliHesap",
    "Base",
    "Bildirim",
    "CanlilikOlayi",
    "DegerlendirmeGozlemi",
    "EpostaDogrulama",
    "Eslesme",
    "FirmaKarti",
    "GuvenSkoru",
    "Hesap",
    "IhtiyacKarti",
    "IncelemeIsareti",
    "Isbirligi",
    "KanitGozlemi",
    "KanitMetinParcasi",
    "KanitParcasi",
    "Kullanici",
    "Kurum",
    "Milestone",
    "ProfilKodu",
    "ReferansIstegi",
    "ServisGunlugu",
    "ServisKullanimi",
    "SomutCikti",
    "YetenekKaniti",
    "YetenekKarti",
]
