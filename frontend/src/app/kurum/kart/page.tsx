"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { FirmaKartiFormAlanlari } from "@/components/firma-karti-formu";
import { GirisKapisi } from "@/components/giris-kapisi";
import {
  CevapAlani,
  HataKutusu,
  type Mesaj,
  Sohbet,
  type SohbetHatasi,
} from "@/components/sohbet";
import { Button } from "@/components/ui/button";
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

/**
 * Firma kartı (docs/kararlar.md F3, F9).
 *
 * Kart yoksa kısa bir sohbet: kayıt formundaki bilgiler sorulmaz. Taslak
 * gelince firma formda düzeltip onaylar; kart firma onaylamadan kaydedilmez.
 * Kart varsa görünüm ve "Kartı düzenle". Kart, iş birliği ortağı arayan
 * firmalara aday olarak gösterilir; genç arayan firmanın karta ihtiyacı yok.
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

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Firma kartı"
        aciklama="Firmanızın ne yaptığını anlatan kart. İş birliği ortağı arayan firmalar sizi bu kartla bulur."
      />

      {hata && kart === undefined ? (
        <HataKutusu hata={hata} tekrarDene={() => void oku()} />
      ) : null}

      {kart === undefined ? (
        hata ? null : (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        )
      ) : kart === null ? (
        <KartSohbeti
          onKaydedildi={(yeni) => {
            setKart(yeni);
            void tazele();
          }}
        />
      ) : (
        <KartGorunumu kart={kart} onGuncelle={setKart} />
      )}

      <footer className="mt-auto border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href="/kurum">Panele dön</Link>
        </Button>
      </footer>
    </Sayfa>
  );
}

/* --- Sohbet ve onay -------------------------------------------------------- */

function KartSohbeti({
  onKaydedildi,
}: {
  onKaydedildi: (kart: FirmaKartiYaniti) => void;
}) {
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

  useEffect(() => {
    sonMesaj.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [mesajlar, bekleniyor]);

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

  return (
    <div className="flex flex-col gap-6">
      <p className="text-xs text-pretty text-muted-foreground">
        Bu sohbet yapay zekâ desteğiyle ilerler. Kartınız siz onaylamadan
        kaydedilmez. Kayıtta verdiğiniz bilgiler tekrar sorulmaz.
      </p>
      <Sohbet
        ajanAdi="Zemin360"
        mesajlar={mesajlar}
        bekleniyor={bekleniyor}
        sonMesajRef={sonMesaj}
      />
      {hata ? <HataKutusu hata={hata} tekrarDene={tekrarDene} /> : null}
      <CevapAlani
        girdi={girdi}
        setGirdi={setGirdi}
        bekleniyor={bekleniyor}
        gonder={gonder}
      />
    </div>
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
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="font-heading text-xl font-semibold text-ana">
          Kartınızın taslağı
        </h2>
        <p className="text-sm text-pretty text-muted-foreground">
          Sohbetten çıkan kart bu. Gözden geçirin, gerekirse düzeltin ve
          onaylayın.
        </p>
      </div>
      <form className="flex flex-col gap-5" onSubmit={onayla}>
        <FirmaKartiFormAlanlari form={form} onDegis={setForm} />
        {hata ? <HataKutusu hata={hata} /> : null}
        <Button type="submit" size="lg" disabled={bekleniyor} className="w-fit">
          {bekleniyor ? "Kaydediliyor…" : "Kartı onayla"}
        </Button>
      </form>
    </section>
  );
}

/* --- Kart ve düzenleme ----------------------------------------------------- */

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

  if (duzenleniyor) {
    return (
      <form className="flex flex-col gap-5" onSubmit={kaydet}>
        <FirmaKartiFormAlanlari form={form} onDegis={setForm} />
        {hata ? <HataKutusu hata={hata} /> : null}
        <div className="flex flex-wrap gap-2">
          <Button type="submit" size="lg" disabled={bekleniyor}>
            {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
          </Button>
          <Button
            type="button"
            size="lg"
            variant="outline"
            disabled={bekleniyor}
            onClick={() => {
              setForm(kartiForma(kart));
              setHata(null);
              setDuzenleniyor(false);
            }}
          >
            Vazgeç
          </Button>
        </div>
      </form>
    );
  }

  return (
    <section className="flex flex-col gap-4 rounded-sm border border-kenar bg-card px-4 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-heading text-lg font-semibold text-ana">
          {kart.firma_adi}
        </h2>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => {
            setKaydedildi(false);
            setDuzenleniyor(true);
          }}
        >
          Kartı düzenle
        </Button>
      </div>
      <p className="text-sm text-pretty">{kart.ne_yapiyoruz}</p>
      <Satir baslik="Yetkinlikler">{kart.yetkinlikler.join(", ")}</Satir>
      {kart.onceki_isler ? (
        <Satir baslik="Önceki işler">{kart.onceki_isler}</Satir>
      ) : null}
      {kart.aranan_isbirligi ? (
        <Satir baslik="Aradığınız ortak">{kart.aranan_isbirligi}</Satir>
      ) : null}
      {kart.isbirligi_turleri.length > 0 ? (
        <Satir baslik="İş birliği türleri">
          {kart.isbirligi_turleri.map(isbirligiTuruEtiketi).join(", ")}
        </Satir>
      ) : null}
      {kaydedildi ? (
        <p className="text-sm text-muted-foreground" role="status">
          Kartınız kaydedildi.
        </p>
      ) : null}
      {!kart.embedding_var ? (
        // Rehber § 5.8: ne beklendiğini söyle, kesin süre verme.
        <p className="text-xs text-pretty text-muted-foreground" role="status">
          Kartınız eşleştirmeye hazırlanıyor. Birkaç saniye sonra sayfayı
          yenileyerek görebilirsiniz.
        </p>
      ) : null}
    </section>
  );
}

function Satir({
  baslik,
  children,
}: {
  baslik: string;
  children: React.ReactNode;
}) {
  return (
    <p className="text-sm text-pretty">
      <span className="font-medium text-ana">{baslik}: </span>
      {children}
    </p>
  );
}
