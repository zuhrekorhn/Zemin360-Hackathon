"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { KilitliAd } from "@/components/ad-degisikligi";
import { Sayfa, SayfaBasligi, SayfaDurumu } from "@/components/sayfa";
import { GencProfilAlanlari } from "@/components/genc-profil-alanlari";
import { GirisKapisi } from "@/components/giris-kapisi";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { type GencProfil, profilGetir, profilGuncelle } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import {
  BOS_PROFIL_FORMU,
  formuProfileCevir,
  profildenForma,
  profilFormunuDogrula,
} from "@/lib/profil";

/**
 * Gencin profil düzenleme sayfası (docs/plans/genc-akisi.md § 6.1).
 *
 * Kayıt formundaki alanlar; yalnızca kendi profili (token'ın profili). Bu
 * alanlardan önce açılmış hesaplar paneldeki banttan buraya gelir ve eksikleri
 * ile KVKK onayını burada tamamlar.
 */
export default function ProfilSayfasi() {
  return (
    <GirisKapisi roller={["genc"]} genislik="form">
      <ProfilIcerigi />
    </GirisKapisi>
  );
}

function ProfilIcerigi() {
  const { tazele } = useOturum();
  const [profil, setProfil] = useState<GencProfil | null>(null);
  const [ad, setAd] = useState("");
  const [form, setForm] = useState(BOS_PROFIL_FORMU);
  const [kvkkOnay, setKvkkOnay] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [kaydedildi, setKaydedildi] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  function yukle(yeni: GencProfil) {
    setProfil(yeni);
    setAd(yeni.ad);
    setForm(profildenForma(yeni));
  }

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    profilGetir()
      .then(yukle)
      .catch((sebep) => setHata(hatayaCevir(sebep)));
  }, []);

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor || !profil) return;
    setHata(null);
    setKaydedildi(false);
    const hatalar = profilFormunuDogrula(form);
    if (!profil.ad_kilitli && !ad.trim()) hatalar.unshift("Adın boş olamaz.");
    if (hatalar.length > 0) {
      setHata({ metin: hatalar.join(" "), kota: false });
      return;
    }
    setBekleniyor(true);
    try {
      const yeni = await profilGuncelle({
        ...formuProfileCevir(form),
        // Kilitli ad formdan gönderilmez; değişikliği talep yolundan gider.
        ...(profil.ad_kilitli ? {} : { ad: ad.trim() }),
        ...(kvkkOnay ? { kvkk_onay: true } : {}),
      });
      yukle(yeni);
      setKaydedildi(true);
      // Paneldeki bant ve menü /me'den okunuyor.
      void tazele();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  if (!profil) {
    return <SayfaDurumu genislik="form" hata={hata} />;
  }

  return (
    <Sayfa genislik="form">
      <SayfaBasligi
        baslik="Profilim"
        aciklama={
          <>
            Yetkinliklerin kartında; burada çalışma tercihlerin ve eğitim
            bilgilerin var. E-postan ({profil.email}) yalnızca karşılıklı ilgi
            oluşunca paylaşılır.
          </>
        }
      />

      <form className="flex flex-col gap-6" onSubmit={kaydet}>
        {profil.ad_kilitli ? (
          <KilitliAd profil={profil} onTalep={setProfil} />
        ) : (
          <FormAlani etiket="Adın" htmlFor="ad">
            <Input
              id="ad"
              value={ad}
              onChange={(olay) => setAd(olay.target.value)}
              required
              autoComplete="name"
            />
          </FormAlani>
        )}

        <GencProfilAlanlari form={form} onDegis={setForm} />

        {profil.kvkk_onay_tarihi ? null : (
          <label className="flex items-start gap-2 text-sm text-pretty">
            <input
              type="checkbox"
              checked={kvkkOnay}
              onChange={(olay) => setKvkkOnay(olay.target.checked)}
              className="mt-0.5 accent-ana"
            />
            <span>
              <Link
                href="/kvkk"
                target="_blank"
                className="text-baglanti underline"
              >
                KVKK aydınlatma metnini
              </Link>{" "}
              okudum; verilerimin bu metinde anlatılan amaçlarla işlenmesini
              onaylıyorum.
            </span>
          </label>
        )}

        {hata ? <HataKutusu hata={hata} /> : null}
        {kaydedildi ? (
          <p className="text-sm text-muted-foreground" role="status">
            Profilin kaydedildi.
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" size="lg" disabled={bekleniyor}>
            {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
          </Button>
          <Link href="/genc" className="text-sm text-baglanti underline">
            Panele dön
          </Link>
        </div>
      </form>
    </Sayfa>
  );
}
