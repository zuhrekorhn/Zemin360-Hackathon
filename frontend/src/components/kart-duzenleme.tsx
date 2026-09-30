"use client";

import { useState } from "react";

import { IsKalemiFormu } from "@/components/is-kalemi-formu";
import { OnayAlani } from "@/components/onay-alani";
import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type SomutCiktiTaslagi,
  type SomutCiktiYaniti,
  type YetenekKartiYaniti,
  isKalemiEkle,
  isKalemiGuncelle,
  isKalemiSil,
  kartGuncelle,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import {
  degisenIsKalemiAlanlari,
  gostergeSifirlanir,
  listeMetni,
  virgulluListe,
} from "@/lib/kart-duzenleme";
import { DENEYIM_ETIKETLERI } from "@/lib/sabitler";

/**
 * Gencin kendi kartını düzenlemesi (docs/plans/genc-akisi.md § 6.1). Her kayıt
 * kartı sunucuda yeniden hazırlatır (eşleşmeler ve güven göstergesi güncellenir).
 * Metinler: docs/plans/genc-akisi-metinler.md.
 */

// Rehber § 5.8: ne beklendiğini söyler, kesin süre vermez.
export const YENIDEN_DEGERLENDIRME_NOTU =
  "Kaydedildi. Değişen çalışman yeniden değerlendiriliyor; güven göstergesi kısa süre içinde güncellenir. Sayfayı yenileyerek görebilirsin.";

const SIFIRLAMA_ONAYI =
  "Bu çalışma daha önce değerlendirildi. Kaydedersen güven göstergesi sıfırlanır ve yeniden değerlendirilir; önceki referans yanıtları geçmiş olarak kalır.";

type Ortak = {
  kartId: string;
  onGuncel: (kart: YetenekKartiYaniti, not?: string) => void;
  onHata: (hata: Hata | null) => void;
};

async function calistir(
  is: () => Promise<YetenekKartiYaniti>,
  { onGuncel, onHata }: Omit<Ortak, "kartId">,
  not?: string,
): Promise<boolean> {
  onHata(null);
  try {
    onGuncel(await is(), not);
    return true;
  } catch (sebep) {
    onHata(hatayaCevir(sebep));
    return false;
  }
}

export function KartAlanlariFormu({
  kart,
  onGuncel,
  onHata,
  onKapat,
}: Omit<Ortak, "kartId"> & { kart: YetenekKartiYaniti; onKapat: () => void }) {
  const [rol, setRol] = useState(kart.rol_alani);
  const [deneyim, setDeneyim] = useState(kart.deneyim_seviyesi);
  const [sektor, setSektor] = useState(listeMetni(kart.sektor_ilgi_alani));
  const [araclar, setAraclar] = useState(listeMetni(kart.araclar_teknolojiler));
  const [sertifikalar, setSertifikalar] = useState(
    listeMetni(kart.sertifikalar),
  );
  const [diller, setDiller] = useState(listeMetni(kart.diller));
  const [bekleniyor, setBekleniyor] = useState(false);

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor || !rol.trim()) return;
    setBekleniyor(true);
    const tamam = await calistir(
      () =>
        kartGuncelle(kart.id, {
          rol_alani: rol.trim(),
          deneyim_seviyesi: deneyim,
          sektor_ilgi_alani: virgulluListe(sektor),
          araclar_teknolojiler: virgulluListe(araclar),
          sertifikalar: virgulluListe(sertifikalar),
          diller: virgulluListe(diller),
        }),
      { onGuncel, onHata },
    );
    setBekleniyor(false);
    if (tamam) onKapat();
  }

  const listeAlanlari: [string, string, string, (v: string) => void][] = [
    ["sektor", "Sektör ilgisi", sektor, setSektor],
    ["araclar", "Araçlar ve yöntemler", araclar, setAraclar],
    ["sertifikalar", "Sertifikalar", sertifikalar, setSertifikalar],
    ["diller", "Diller", diller, setDiller],
  ];

  return (
    <form
      className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4"
      onSubmit={kaydet}
    >
      <FormAlani etiket="Rol / alan" htmlFor="kart-rol">
        <Input
          id="kart-rol"
          value={rol}
          required
          onChange={(olay) => setRol(olay.target.value)}
        />
      </FormAlani>
      <FormAlani etiket="Deneyim" htmlFor="kart-deneyim">
        <select
          id="kart-deneyim"
          value={deneyim}
          onChange={(olay) => setDeneyim(olay.target.value)}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
        >
          {Object.entries(DENEYIM_ETIKETLERI).map(([deger, etiket]) => (
            <option key={deger} value={deger}>
              {etiket}
            </option>
          ))}
        </select>
      </FormAlani>
      {listeAlanlari.map(([kimlik, etiket, deger, degistir]) => (
        <FormAlani key={kimlik} etiket={etiket} htmlFor={`kart-${kimlik}`}>
          <Input
            id={`kart-${kimlik}`}
            value={deger}
            placeholder="ör. eğitim, sivil toplum (virgülle ayır)"
            onChange={(olay) => degistir(olay.target.value)}
          />
        </FormAlani>
      ))}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" disabled={bekleniyor}>
          {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onKapat}>
          Vazgeç
        </Button>
      </div>
    </form>
  );
}

function taslakHali(cikti: SomutCiktiYaniti): SomutCiktiTaslagi {
  return {
    baslik: cikti.baslik,
    aciklama: cikti.aciklama,
    kanit_linki: cikti.kanit_linki,
    is_turu: cikti.is_turu ?? null,
    olculebilir_sonuc: cikti.olculebilir_sonuc ?? null,
    kendi_rolu: cikti.kendi_rolu ?? null,
  };
}

/** Bir çalışmanın "Düzenle" ve "Sil" eylemleri; onaylar sayfa içinde (rehber § 5.6). */
export function IsKalemiEylemleri({
  kartId,
  cikti,
  onGuncel,
  onHata,
}: Ortak & { cikti: SomutCiktiYaniti }) {
  const [acik, setAcik] = useState(false);
  const [taslak, setTaslak] = useState<SomutCiktiTaslagi>(taslakHali(cikti));
  const [bekleniyor, setBekleniyor] = useState(false);
  const [silmeOnayi, setSilmeOnayi] = useState(false);
  const [sifirlamaOnayi, setSifirlamaOnayi] = useState(false);

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor) return;
    const degisenler = degisenIsKalemiAlanlari(taslakHali(cikti), taslak);
    if (Object.keys(degisenler).length === 0) {
      setAcik(false);
      return;
    }
    // Değerlendirilmiş çalışmanın göstergesi sıfırlanacaksa önce sorulur.
    if (
      gostergeSifirlanir(degisenler) &&
      cikti.guven_skoru &&
      !sifirlamaOnayi
    ) {
      setSifirlamaOnayi(true);
      return;
    }
    await kaydetOnayli();
  }

  async function kaydetOnayli() {
    const degisenler = degisenIsKalemiAlanlari(taslakHali(cikti), taslak);
    const sifirlanir = gostergeSifirlanir(degisenler);
    setSifirlamaOnayi(false);
    setBekleniyor(true);
    const tamam = await calistir(
      () => isKalemiGuncelle(kartId, cikti.id, degisenler),
      { onGuncel, onHata },
      sifirlanir && taslak.kanit_linki ? YENIDEN_DEGERLENDIRME_NOTU : undefined,
    );
    setBekleniyor(false);
    if (tamam) setAcik(false);
  }

  async function sil() {
    setBekleniyor(true);
    await calistir(() => isKalemiSil(kartId, cikti.id), { onGuncel, onHata });
    setBekleniyor(false);
    setSilmeOnayi(false);
  }

  if (silmeOnayi) {
    return (
      <OnayAlani
        soru={`“${cikti.baslik}” silinsin mi? Kanıtı ve referans istekleri de silinir.`}
        onayEtiketi="Sil"
        bekleniyor={bekleniyor}
        bekleniyorEtiketi="Siliniyor…"
        onOnayla={() => void sil()}
        onVazgec={() => setSilmeOnayi(false)}
      />
    );
  }

  if (!acik) {
    return (
      <div className="flex gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => {
            setTaslak(taslakHali(cikti));
            setAcik(true);
          }}
        >
          Düzenle
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => setSilmeOnayi(true)}
        >
          Sil
        </Button>
      </div>
    );
  }

  return (
    <form
      className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4"
      onSubmit={kaydet}
    >
      <IsKalemiFormu
        kimlik={`duzenle-${cikti.id}`}
        cikti={taslak}
        referansGoster={false}
        onDegis={(alan, deger) =>
          setTaslak((onceki) => ({ ...onceki, [alan]: deger }))
        }
      />
      {sifirlamaOnayi ? (
        <OnayAlani
          soru={SIFIRLAMA_ONAYI}
          onayEtiketi="Kaydet"
          bekleniyor={bekleniyor}
          bekleniyorEtiketi="Kaydediliyor…"
          onOnayla={() => void kaydetOnayli()}
          onVazgec={() => setSifirlamaOnayi(false)}
        />
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button type="submit" size="sm" disabled={bekleniyor}>
            {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setAcik(false)}
          >
            Vazgeç
          </Button>
        </div>
      )}
    </form>
  );
}

const BOS_IS_KALEMI: SomutCiktiTaslagi = {
  baslik: "",
  aciklama: null,
  kanit_linki: null,
};

/** Formdan yeni çalışma (sohbetle ekleme ayrı, dondurma sonrası). */
export function IsKalemiEkleFormu({
  kartId,
  onGuncel,
  onHata,
  onKapat,
}: Ortak & { onKapat: () => void }) {
  const [taslak, setTaslak] = useState<SomutCiktiTaslagi>(BOS_IS_KALEMI);
  const [bekleniyor, setBekleniyor] = useState(false);

  async function ekle(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor || !taslak.baslik.trim()) return;
    setBekleniyor(true);
    const bosIseNull = (deger: string | null | undefined) =>
      deger?.trim() || null;
    const tamam = await calistir(
      () =>
        isKalemiEkle(kartId, {
          baslik: taslak.baslik.trim(),
          aciklama: bosIseNull(taslak.aciklama),
          olculebilir_sonuc: bosIseNull(taslak.olculebilir_sonuc),
          kendi_rolu: bosIseNull(taslak.kendi_rolu),
          kanit_linki: bosIseNull(taslak.kanit_linki),
          is_turu: bosIseNull(taslak.is_turu),
        }),
      { onGuncel, onHata },
      taslak.kanit_linki?.trim() ? YENIDEN_DEGERLENDIRME_NOTU : undefined,
    );
    setBekleniyor(false);
    if (tamam) {
      setTaslak(BOS_IS_KALEMI);
      onKapat();
    }
  }

  return (
    <form
      className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4"
      onSubmit={ekle}
    >
      <IsKalemiFormu
        kimlik="yeni-is-kalemi"
        cikti={taslak}
        referansGoster={false}
        onDegis={(alan, deger) =>
          setTaslak((onceki) => ({ ...onceki, [alan]: deger }))
        }
      />
      <p className="text-xs text-pretty text-muted-foreground">
        Referans kişi eklemek için çalışmayı kaydettikten sonra kanıt bölümünü
        kullan.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" disabled={bekleniyor}>
          {bekleniyor ? "Ekleniyor…" : "Çalışmayı ekle"}
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onKapat}>
          Vazgeç
        </Button>
      </div>
    </form>
  );
}
