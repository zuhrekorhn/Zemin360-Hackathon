"use client";

import { useState } from "react";

import { IsKalemiFormu } from "@/components/is-kalemi-formu";
import { KartAlanlari } from "@/components/kart-alanlari";
import { OnayAlani } from "@/components/onay-alani";
import { Button } from "@/components/ui/button";
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
  eksikKartAlanlari,
  gostergeSifirlanir,
  kartAlanDegerleri,
  kartAlanlariniCevir,
} from "@/lib/kart-duzenleme";

/**
 * Gencin kendi kartını düzenlemesi (docs/agent-specs.md § 1). Her kayıt
 * kartı sunucuda yeniden hazırlatır (eşleşmeler ve güven göstergesi güncellenir).
 * Metinler: docs/icerik-rehberi.md.
 */

// Rehber § 5.8: ne beklendiğini söyler, kesin süre vermez.
export const YENIDEN_DEGERLENDIRME_NOTU =
  "Kaydedildi. Değişen çalışman yeniden değerlendiriliyor; güven göstergesi kısa süre içinde güncellenir. Sayfayı yenileyerek görebilirsin.";

export const SIFIRLAMA_ONAYI =
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
  const [alanlar, setAlanlar] = useState(() => kartAlanDegerleri(kart));
  const [bekleniyor, setBekleniyor] = useState(false);

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor || eksikKartAlanlari(alanlar).length > 0) return;
    setBekleniyor(true);
    const tamam = await calistir(
      () => kartGuncelle(kart.id, kartAlanlariniCevir(alanlar)),
      { onGuncel, onHata },
    );
    setBekleniyor(false);
    if (tamam) onKapat();
  }

  return (
    <form
      className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4"
      onSubmit={kaydet}
    >
      <KartAlanlari
        kimlik="kart"
        degerler={alanlar}
        onDegis={(alan, deger) =>
          setAlanlar((onceki) => ({ ...onceki, [alan]: deger }))
        }
      />
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
    // İddia formu kanıt düzenlemez; kanıt kart sayfasının kanıt bölümünde.
    kanit_linki: null,
    is_turu: cikti.is_turu ?? null,
    olculebilir_sonuc: cikti.olculebilir_sonuc ?? null,
    kendi_rolu: cikti.kendi_rolu ?? null,
  };
}

/**
 * Bir çalışmanın düzenleme formu (kart sayfasında "⋯ → Düzenle" ya da "sıradaki
 * adım" açar). Değerlendirilmiş çalışmanın göstergesi sıfırlanacaksa önce sorulur.
 */
export function IsKalemiDuzenleFormu({
  kartId,
  cikti,
  onGuncel,
  onHata,
  onKapat,
  onSil,
}: Ortak & {
  cikti: SomutCiktiYaniti;
  onKapat: () => void;
  /** Verilirse formun sağında "Çalışmayı sil" (onayı çağıran gösterir). */
  onSil?: () => void;
}) {
  const [taslak, setTaslak] = useState<SomutCiktiTaslagi>(() =>
    taslakHali(cikti),
  );
  const [bekleniyor, setBekleniyor] = useState(false);
  const [sifirlamaOnayi, setSifirlamaOnayi] = useState(false);

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor) return;
    const degisenler = degisenIsKalemiAlanlari(taslakHali(cikti), taslak);
    if (Object.keys(degisenler).length === 0) {
      onKapat();
      return;
    }
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
      sifirlanir && cikti.kanitlar.length > 0
        ? YENIDEN_DEGERLENDIRME_NOTU
        : undefined,
    );
    setBekleniyor(false);
    if (tamam) onKapat();
  }

  return (
    <form className="flex flex-col gap-3" onSubmit={kaydet}>
      <IsKalemiFormu
        kimlik={`duzenle-${cikti.id}`}
        cikti={taslak}
        referansGoster={false}
        kanitGoster={false}
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
          <Button type="button" size="sm" variant="ghost" onClick={onKapat}>
            Vazgeç
          </Button>
          {onSil ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="ml-auto text-destructive hover:text-destructive"
              onClick={onSil}
            >
              Çalışmayı sil
            </Button>
          ) : null}
        </div>
      )}
    </form>
  );
}

/** Çalışmayı silme onayı; onaylar sayfa içinde (rehber § 5.6). */
export function IsKalemiSilmeOnayi({
  kartId,
  cikti,
  onGuncel,
  onHata,
  onKapat,
}: Ortak & { cikti: SomutCiktiYaniti; onKapat: () => void }) {
  const [bekleniyor, setBekleniyor] = useState(false);

  async function sil() {
    setBekleniyor(true);
    await calistir(() => isKalemiSil(kartId, cikti.id), { onGuncel, onHata });
    setBekleniyor(false);
    onKapat();
  }

  return (
    <OnayAlani
      soru={`“${cikti.baslik}” silinsin mi? Kanıtı ve referans istekleri de silinir.`}
      onayEtiketi="Sil"
      bekleniyor={bekleniyor}
      bekleniyorEtiketi="Siliniyor…"
      onOnayla={() => void sil()}
      onVazgec={onKapat}
    />
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
        Kanıt ve referansı çalışmayı kaydettikten sonra ekleyebilirsin.
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
