"use client";

import { Pencil } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { EtiketSatiri } from "@/components/kart";
import { FirmaKartiFormAlanlari } from "@/components/firma-karti-formu";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { OnayCubugu } from "@/components/onay-cubugu";
import { DurumEtiketi } from "@/components/panel";
import { Sayfa, SayfaBasligi, SayfaDurumu } from "@/components/sayfa";
import {
  CevapAlani,
  HataKutusu,
  type Mesaj,
  Sohbet,
  type SohbetHatasi,
} from "@/components/sohbet";
import { FirmaKartiOnizleme } from "@/components/sohbet-onizlemeleri";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import { YanPanel } from "@/components/ui/yan-panel";
import {
  type FirmaKartiTaslagi,
  type FirmaKartiYaniti,
  firmaKartiDuzenle,
  firmaKartiOnayla,
  firmaKartiSohbetBaslat,
  firmaKartiSohbetCevap,
  firmaKartim,
} from "@/lib/api";
import {
  type FirmaKartiFormu,
  degisenKartAlanlari,
  formuKartaCevir,
  isbirligiTuruEtiketi,
  kartFormunuDogrula,
  kartiForma,
} from "@/lib/firma-karti";
import { hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import { cn } from "@/lib/utils";

/**
 * Firma kartı (docs/kararlar.md F3, F9, F21).
 *
 * Kart yoksa kısa bir sohbet (solda sohbet, sağda kartın canlı hali): kayıt
 * formundaki bilgiler sorulmaz. Taslak gelince firma formda düzeltip onaylar;
 * kart firma onaylamadan kaydedilmez. Kart varsa görünüm ve sağdan açılan
 * "Kartı düzenle" paneli. Kart, iş birliği ortağı arayan firmalara aday olarak
 * gösterilir; genç arayan firmanın karta ihtiyacı yok.
 */
export default function FirmaKartiSayfasi() {
  return (
    <GirisKapisi roller={["kurum"]}>
      <FirmaKartiIcerigi />
    </GirisKapisi>
  );
}

function FirmaKartiIcerigi() {
  const { tazele } = useOturum();
  // undefined: henüz okunmadı; null: kart yok (sohbet).
  const [kart, setKart] = useState<FirmaKartiYaniti | null | undefined>();
  const [hata, setHata] = useState<SohbetHatasi | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      setKart(await firmaKartim());
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  if (kart === undefined) {
    return <SayfaDurumu hata={hata} tekrarDene={() => void oku()} />;
  }
  if (kart === null) {
    return (
      <KartSohbeti
        onKaydedildi={(yeni) => {
          setKart(yeni);
          void tazele();
        }}
      />
    );
  }
  return <KartGorunumu kart={kart} onGuncelle={setKart} />;
}

/* --- Sohbet ve onay -------------------------------------------------------- */

function KartSohbeti({
  onKaydedildi,
}: {
  onKaydedildi: (kart: FirmaKartiYaniti) => void;
}) {
  const hesap = useGirisliHesap();
  const [oturumId, setOturumId] = useState<string | null>(null);
  const [mesajlar, setMesajlar] = useState<Mesaj[]>([]);
  const [taslak, setTaslak] = useState<FirmaKartiTaslagi | null>(null);
  const [taslakHazir, setTaslakHazir] = useState(false);
  const [girdi, setGirdi] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<SohbetHatasi | null>(null);
  const bekleyenCevap = useRef<string | null>(null);
  const baslatildi = useRef(false);
  const sonMesaj = useRef<HTMLDivElement | null>(null);

  const sohbetiBaslat = useCallback(async () => {
    setHata(null);
    setBekleniyor(true);
    try {
      const yanit = await firmaKartiSohbetBaslat();
      setOturumId(yanit.oturum_id);
      setMesajlar(yanit.soru ? [{ kim: "ajan", metin: yanit.soru }] : []);
      setTaslak(yanit.taslak);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }, []);

  useEffect(() => {
    // StrictMode efekti iki kez çalıştırıyor; ikinci oturum açılmasın.
    if (baslatildi.current) return;
    baslatildi.current = true;
    void sohbetiBaslat();
  }, [sohbetiBaslat]);

  async function cevapGonder(cevap: string) {
    if (!oturumId) return;
    setHata(null);
    setBekleniyor(true);
    bekleyenCevap.current = cevap;
    try {
      const yanit = await firmaKartiSohbetCevap(oturumId, cevap);
      bekleyenCevap.current = null;
      setTaslak(yanit.taslak);
      if (yanit.taslak_hazir) {
        setTaslakHazir(true);
      } else if (yanit.soru) {
        setMesajlar((onceki) => [
          ...onceki,
          { kim: "ajan", metin: yanit.soru as string },
        ]);
      }
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  function gonder() {
    const cevap = girdi.trim();
    if (!cevap || bekleniyor) return;
    setMesajlar((onceki) => [...onceki, { kim: "kullanici", metin: cevap }]);
    setGirdi("");
    void cevapGonder(cevap);
  }

  function tekrarDene() {
    if (bekleyenCevap.current) void cevapGonder(bekleyenCevap.current);
    else if (!oturumId) void sohbetiBaslat();
  }

  if (taslakHazir && taslak && oturumId) {
    return (
      <TaslakOnayi
        oturumId={oturumId}
        taslak={taslak}
        onKaydedildi={onKaydedildi}
      />
    );
  }

  // Solda sohbet, sağda kartın canlı hali (Keşif'le aynı iskelet).
  return (
    <Sayfa genislik="genis">
      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex min-w-0 flex-col gap-6">
          <SayfaBasligi
            baslik="Firma kartınızı oluşturun"
            aciklama="Kısa bir sohbetle firmanızın ne yaptığını bir karta dönüştüreceğiz; iş birliği ortağı arayan firmalar sizi bu kartla bulur. Bu sohbet yapay zekâ desteğiyle ilerler. Kartınız siz onaylamadan kaydedilmez. Kayıtta verdiğiniz bilgiler tekrar sorulmaz."
          />
          {hata ? <HataKutusu hata={hata} tekrarDene={tekrarDene} /> : null}
          <Sohbet
            ajanAdi="Zemin360"
            mesajlar={mesajlar}
            bekleniyor={bekleniyor}
            sonMesajRef={sonMesaj}
            altKisim={
              <CevapAlani
                girdi={girdi}
                setGirdi={setGirdi}
                bekleniyor={bekleniyor}
                gonder={gonder}
              />
            }
          />
        </div>
        <aside aria-label="Firma kartınız" className="lg:sticky lg:top-24">
          <FirmaKartiOnizleme taslak={taslak} firmaAdi={hesap.ad ?? ""} />
        </aside>
      </div>
    </Sayfa>
  );
}

function TaslakOnayi({
  oturumId,
  taslak,
  onKaydedildi,
}: {
  oturumId: string;
  taslak: FirmaKartiTaslagi;
  onKaydedildi: (kart: FirmaKartiYaniti) => void;
}) {
  const [form, setForm] = useState<FirmaKartiFormu>(() => kartiForma(taslak));
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<SohbetHatasi | null>(null);

  async function onayla(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor) return;
    const hatalar = kartFormunuDogrula(form);
    if (hatalar.length > 0) {
      setHata({ metin: hatalar.join(" "), kota: false });
      return;
    }
    setHata(null);
    setBekleniyor(true);
    try {
      onKaydedildi(await firmaKartiOnayla(oturumId, formuKartaCevir(form)));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setBekleniyor(false);
    }
  }

  return (
    <Sayfa genislik="form">
      <SayfaBasligi
        baslik="Kartınızı gözden geçirin"
        aciklama="Sohbetten çıkan kart bu. Yanlış anlaşılan bir şey varsa düzeltin; doğruysa onaylayın. Kartınız siz onaylamadan kaydedilmez."
      />
      <form className="flex flex-col gap-8" onSubmit={onayla}>
        <section className={cn(KUTU, "flex flex-col gap-4 px-5 py-5")}>
          <h2 className="font-heading text-xl font-semibold text-ana">
            Firma kartı
          </h2>
          <FirmaKartiFormAlanlari form={form} onDegis={setForm} />
        </section>
        {hata ? <HataKutusu hata={hata} /> : null}
        {/* Onay her zaman görünür: uzun formda sayfanın sonuna inmek gerekmesin. */}
        <OnayCubugu
          metin="Doğruysa onaylayın; kartınız kaydedilir ve iş birliği ortağı arayan firmalara aday olarak önerilir. Sonra istediğiniz zaman düzenleyebilirsiniz. E-postanız kartta görünmez."
          etiket="Kartı onayla"
          bekleniyor={bekleniyor}
        />
      </form>
    </Sayfa>
  );
}

/* --- Kart ve düzenleme ----------------------------------------------------- */

const DUZENLEME_FORMU = "firma-karti-duzenleme-formu";

function KartGorunumu({
  kart,
  onGuncelle,
}: {
  kart: FirmaKartiYaniti;
  onGuncelle: (kart: FirmaKartiYaniti) => void;
}) {
  const [duzenleniyor, setDuzenleniyor] = useState(false);
  const [form, setForm] = useState<FirmaKartiFormu>(() => kartiForma(kart));
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<SohbetHatasi | null>(null);
  const [kaydedildi, setKaydedildi] = useState(false);

  function paneliKapat() {
    setForm(kartiForma(kart));
    setHata(null);
    setDuzenleniyor(false);
  }

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor) return;
    const hatalar = kartFormunuDogrula(form);
    if (hatalar.length > 0) {
      setHata({ metin: hatalar.join(" "), kota: false });
      return;
    }
    const degisen = degisenKartAlanlari(kart, form);
    if (Object.keys(degisen).length === 0) {
      setDuzenleniyor(false);
      return;
    }
    setHata(null);
    setBekleniyor(true);
    try {
      const yeni = await firmaKartiDuzenle(degisen);
      onGuncelle(yeni);
      setForm(kartiForma(yeni));
      setDuzenleniyor(false);
      setKaydedildi(true);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Firma kartı"
        aciklama="Firmanızın ne yaptığını anlatan kart. İş birliği ortağı arayan firmalar sizi bu kartla bulur."
        eylem={
          <Button
            type="button"
            variant="outline"
            size="lg"
            onClick={() => {
              setKaydedildi(false);
              setDuzenleniyor(true);
            }}
          >
            <Pencil aria-hidden="true" />
            Kartı düzenle
          </Button>
        }
      />

      {kaydedildi ? (
        <p
          role="status"
          className="rounded-xl bg-baglanti/10 px-5 py-3 text-sm text-baglanti"
        >
          Kartınız kaydedildi.
        </p>
      ) : null}
      {!kart.embedding_var ? (
        // Rehber § 5.8: ne beklendiğini söyle, kesin süre verme.
        <p
          role="status"
          className="rounded-xl bg-muted px-5 py-3 text-sm text-pretty"
        >
          Kartınız eşleştirmeye hazırlanıyor. Birkaç saniye sonra sayfayı
          yenileyerek görebilirsiniz.
        </p>
      ) : null}

      <article className={cn(KUTU, "flex flex-col gap-5 px-6 py-6")}>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <h2 className="font-heading text-xl leading-snug font-semibold text-ana">
            {kart.firma_adi}
          </h2>
          {kart.tamamlanan_isbirligi ? (
            <DurumEtiketi
              metin={`${kart.tamamlanan_isbirligi} tamamlanan iş birliği`}
              baglanti
            />
          ) : null}
        </div>
        <p className="text-[15px] leading-relaxed text-pretty">
          {kart.ne_yapiyoruz}
        </p>
        <EtiketSatiri etiket="Yetkinlikler" degerler={kart.yetkinlikler} />
        <EtiketSatiri
          etiket="İş birliği türleri"
          degerler={kart.isbirligi_turleri.map(isbirligiTuruEtiketi)}
        />
        {kart.onceki_isler ? (
          <Bolum baslik="Önceki işler">{kart.onceki_isler}</Bolum>
        ) : null}
        {kart.aranan_isbirligi ? (
          <Bolum baslik="Aradığınız ortak">{kart.aranan_isbirligi}</Bolum>
        ) : null}
      </article>

      <YanPanel
        acik={duzenleniyor}
        onKapat={paneliKapat}
        ust="Kartı düzenleyin"
        baslik={kart.firma_adi}
        alt="Ne yaptığınızı, yetkinliklerinizi ve aradığınız ortağı güncelleyin."
        etek={
          <>
            <Button
              type="submit"
              form={DUZENLEME_FORMU}
              size="lg"
              disabled={bekleniyor}
            >
              {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
            </Button>
            <Button
              type="button"
              size="lg"
              variant="ghost"
              disabled={bekleniyor}
              onClick={paneliKapat}
            >
              Vazgeç
            </Button>
          </>
        }
      >
        <form
          id={DUZENLEME_FORMU}
          className="flex flex-col gap-5"
          onSubmit={kaydet}
        >
          <FirmaKartiFormAlanlari form={form} onDegis={setForm} />
          {hata ? <HataKutusu hata={hata} /> : null}
        </form>
      </YanPanel>
    </Sayfa>
  );
}

function Bolum({
  baslik,
  children,
}: {
  baslik: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-1 border-t border-kenar pt-4">
      <h3 className="font-heading text-sm font-semibold text-ana">{baslik}</h3>
      <p className="text-sm leading-relaxed text-pretty">{children}</p>
    </section>
  );
}
