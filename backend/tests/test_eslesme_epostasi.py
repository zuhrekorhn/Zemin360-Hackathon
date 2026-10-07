"""Karşılıklı ilgiden sonra giden "eşleştiniz" e-postası (docs/api-contracts.md).

Dünya test_sahiplik.py'deki: E1 = I1 (kurum1 "Koop Bir") ↔ K1 (genc1 "Elif"), `onerildi`.
Gönderici sahte (`eposta_gonderilmez`): ağ yok, gönderilenler kaydedilir.
"""

from tests.test_sahiplik import senaryo


def test_genc_kabul_edince_ilan_sahibine_siz_diliyle_gider(eposta_gonderilmez):
    async def adimlar(istemci, d):
        await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": str(d.E1.id)}
        )
        assert eposta_gonderilmez.gonderilenler == []  # ilk ilgi: yalnızca bildirim

        kabul = await istemci.post(f"/eslestirme/{d.E1.id}/kabul", headers=d.genc1.baslik)
        assert kabul.status_code == 200
        (eposta,) = eposta_gonderilmez.gonderilenler
        assert eposta.alici == d.kurum1.profil.iletisim_email
        assert "Elif ile eşleştiniz" in eposta.konu
        assert f"/isbirligi/{kabul.json()['isbirligi_id']}" in eposta.metin
        assert "sayfanıza" in eposta.metin  # siz
        # Karşı tarafın adresi e-postada yok; "pilot" geçmez.
        assert d.genc1.profil.email not in eposta.metin + eposta.konu
        assert "pilot" not in (eposta.metin + eposta.konu).lower()

        # Aynı geçişin tekrarı yan etkisiz: ikinci e-posta gitmez.
        tekrar = await istemci.post(f"/eslestirme/{d.E1.id}/kabul", headers=d.genc1.baslik)
        assert tekrar.status_code == 200
        assert len(eposta_gonderilmez.gonderilenler) == 1

    senaryo(adimlar)


def test_karsilikli_ilgide_gence_sen_diliyle_gider(eposta_gonderilmez):
    async def adimlar(istemci, d):
        ilgi = await istemci.post(
            f"/eslestirme/{d.E1.id}/genc-ilgi",
            headers=d.genc1.baslik,
            json={"iletisim_onayi": True},
        )
        assert ilgi.status_code == 200
        assert eposta_gonderilmez.gonderilenler == []

        yanit = await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": str(d.E1.id)}
        )
        assert yanit.status_code == 200
        (eposta,) = eposta_gonderilmez.gonderilenler
        assert eposta.alici == d.genc1.profil.email
        assert eposta.metin.startswith("Merhaba Elif,")
        assert "Koop Bir ile eşleştiniz" in eposta.metin
        assert "sayfana" in eposta.metin  # sen
        assert d.kurum1.profil.iletisim_email not in eposta.metin

    senaryo(adimlar)


def test_red_ve_ilk_ilgi_e_posta_gondermez(eposta_gonderilmez):
    async def adimlar(istemci, d):
        await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": str(d.E1.id)}
        )
        await istemci.post(f"/eslestirme/{d.E1.id}/red", headers=d.genc1.baslik)
        assert eposta_gonderilmez.gonderilenler == []

    senaryo(adimlar)


def test_gonderim_hatasi_kabulu_dusurmez(eposta_gonderilmez):
    async def adimlar(istemci, d):
        async def patlayan(eposta):
            raise RuntimeError("sağlayıcı yanıt vermiyor")

        eposta_gonderilmez.gonder = patlayan
        await istemci.post(
            "/eslestirme/ilgileniyorum", headers=d.kurum1.baslik, json={"eslesme_id": str(d.E1.id)}
        )
        kabul = await istemci.post(f"/eslestirme/{d.E1.id}/kabul", headers=d.genc1.baslik)
        assert kabul.status_code == 200
        assert kabul.json()["durum"] == "kabul_edildi"
        assert kabul.json()["isbirligi_id"] is not None

    senaryo(adimlar)
