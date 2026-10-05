"""Başarı ölçütünün saf kuralları (app/core/basari_olcutu.py)."""

from app.core.basari_olcutu import hedef_sorulmali, olcum_belirlenecek


def test_olcutu_olmayan_eski_kart_isaretlenmez():
    assert olcum_belirlenecek(None) is False


def test_hedefi_olmayan_olcut_belirlenecek():
    assert olcum_belirlenecek({}) is True
    assert olcum_belirlenecek({"metrik": "memnuniyet", "olcum_bilinmiyor": True}) is True
    assert olcum_belirlenecek({"hedef_deger": "yarısı"}) is False


def test_hedef_sorusu_kurali():
    kriter = {"basari_kriteri": "Sayım süresi kısalsın"}
    assert hedef_sorulmali({**kriter, "basari_olcutu": None}) is True
    assert hedef_sorulmali({**kriter, "basari_olcutu": {"hedef_deger": "%50"}}) is False
    assert hedef_sorulmali({**kriter, "basari_olcutu": {"olcum_bilinmiyor": True}}) is False
    assert hedef_sorulmali({"basari_kriteri": None, "basari_olcutu": None}) is False
