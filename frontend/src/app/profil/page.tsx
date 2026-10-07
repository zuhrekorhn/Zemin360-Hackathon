"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { KilitliAd } from "@/components/ad-degisikligi";
import { BagliHesaplar } from "@/components/bagli-hesaplar";
import {
  BaglantiAlanlari,
  EgitimAlanlari,
} from "@/components/genc-profil-alanlari";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { Sayfa, SayfaBasligi, SayfaDurumu } from "@/components/sayfa";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { type GencProfil, profilGetir, profilGuncelle } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import {
  BOS_PROFIL_FORMU,
  hesapGovdesi,
  hesapHatalari,
  profildenForma,
} from "@/lib/profil";
import { kartYolu } from "@/lib/yonlendirme";

/**
 * Hesabım (docs/agent-specs.md § 1, docs/kararlar.md G18): ad, eğitim,
 * bağlantılar ve KVKK tek formda, tek "Kaydet"le; altında bağlı hesaplar
 * (docs/dogrulama.md § 6) kendi eylemleriyle ayrı bir kutuda. Çalışma
 * tercihleri kart sayfasında: bu form onları göndermez (`hesapGovdesi`).
 * Bu alanlardan önce açılmış hesaplar eksiklerini ve KVKK onayını burada tamamlar.
 */
export default function ProfilSayfasi() {
  return (
    <GirisKapisi roller={["genc"]} genislik="form">
      <ProfilIcerigi />
    </GirisKapisi>
  );
}

/** Formun bir bölümü: başlıksız fieldset'leri ayıran ince çizgi. */
function Bolum({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-t border-kenar px-5 py-5 first:border-t-0">
      {children}
    </div>
  );
}

function ProfilIcerigi() {
  const hesap = useGirisliHesap();
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
    const hatalar = hesapHatalari(form);
    if (!profil.ad_kilitli && !ad.trim()) hatalar.unshift("Adın boş olamaz.");
    if (hatalar.length > 0) {
      setHata({ metin: hatalar.join(" "), kota: false });
      return;
    }
    setBekleniyor(true);
    try {
      const yeni = await profilGuncelle({
        ...hesapGovdesi(form),
        // Kilitli ad formdan gönderilmez; değişikliği talep yolundan gider.
        ...(profil.ad_kilitli ? {} : { ad: ad.trim() }),
        ...(kvkkOnay ? { kvkk_onay: true } : {}),
      });
      yukle(yeni);
      setKaydedildi(true);
      // Ana sayfadaki "Tamamlanacaklar" ve menüdeki ad /me'den okunuyor.
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
        baslik="Hesabım"
        aciklama={
          <>
            Kayıt bilgilerin ve bağlı hesapların. Şehir, çalışma modeli ve
            müsaitlik gibi tercihlerin{" "}
            <Link
              href={`${kartYolu(hesap.yetenek_karti)}${hesap.yetenek_karti ? "#tercihler" : ""}`}
              className="text-baglanti underline underline-offset-4"
            >
              kartında
            </Link>
            .
          </>
        }
      />

      <form
        className="flex flex-col rounded-md border border-kenar bg-card"
        onSubmit={kaydet}
      >
        <Bolum>
          <div className="flex flex-col gap-4">
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
            <div className="flex flex-col gap-1">
              <span className="text-sm font-medium">E-posta</span>
              <span className="text-sm text-muted-foreground">
                {profil.email} · yalnızca karşılıklı ilgi oluşunca o firmayla
                paylaşılır.
              </span>
            </div>
          </div>
        </Bolum>

        <Bolum>
          <EgitimAlanlari form={form} onDegis={setForm} />
        </Bolum>

        <Bolum>
          <BaglantiAlanlari form={form} onDegis={setForm} />
        </Bolum>

        {profil.kvkk_onay_tarihi ? null : (
          <Bolum>
            <label className="flex items-start gap-2 text-sm text-pretty">
              <input
                type="checkbox"
                checked={kvkkOnay}
                onChange={(olay) => setKvkkOnay(olay.target.checked)}
                className="mt-0.5 size-4 accent-ana"
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
          </Bolum>
        )}

        <div className="flex flex-col gap-3 rounded-b-md border-t border-kenar bg-zemin/60 px-5 py-4">
          {hata ? <HataKutusu hata={hata} /> : null}
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" size="lg" disabled={bekleniyor}>
              {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
            </Button>
            {kaydedildi ? (
              <span className="text-sm text-muted-foreground" role="status">
                Kaydedildi.
              </span>
            ) : null}
          </div>
        </div>
      </form>

      <BagliHesaplar />
    </Sayfa>
  );
}
