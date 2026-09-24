"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  BelgeKarti,
  CiktiOzeti,
  EtiketSatiri,
  SkorRozeti,
} from "@/components/kart";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type IlgileniyorumYaniti,
  type Oneri,
  type Oneriler,
  eslestirmeOnerileri,
  ilgileniyorum,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { kimlikOku } from "@/lib/yerel";

/**
 * Eşleştirme önerileri — kurum tarafı (docs/agent-specs.md § 3).
 *
 * Bu ekranda yalnızca kurum var: gencin "eşleştin" bildirimi Faz 3+
 * kapsamında, bilinçli olarak yok.
 *
 * Skor ve gerekçe birlikte gösteriliyor — matching-algorithm.md § 6'nın
 * kararı: kuruma "şu yüzden" denmeden bir isim listesi sunulmuyor.
 */

const DURUM_ETIKETLERI: Record<string, string> = {
  onerildi: "Önerildi",
  ilgileniliyor: "İlgileniliyor",
  kabul_edildi: "İş birliği açıldı",
  reddedildi: "Reddedildi",
};

export default function OnerilerSayfasi() {
  const [kurumId, setKurumId] = useState<string | null>(null);
  const [veri, setVeri] = useState<Oneriler | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<Hata | null>(null);
  const [acilanIsbirligi, setAcilanIsbirligi] = useState<
    Record<string, string>
  >({});
  const okundu = useRef(false);

  const onerileriGetir = useCallback(async (kimlik: string) => {
    setHata(null);
    setYukleniyor(true);
    try {
      setVeri(await eslestirmeOnerileri(kimlik));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setYukleniyor(false);
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;

    // Demoda başka bir tarayıcıdan bakılabilsin diye adres çubuğu da kabul
    // ediliyor; yoksa Tanımlama'dan hatırlanan kimlik kullanılıyor.
    // Kimlik yalnızca tarayıcıda olduğu için okuma render sırasında değil,
    // bağlandıktan sonra yapılıyor (sunucu render'ıyla uyuşsun diye).
    async function baslat() {
      const adresten = new URLSearchParams(window.location.search).get("kurum");
      const kimlik = adresten ?? kimlikOku("kurum");
      setKurumId(kimlik);

      if (kimlik) await onerileriGetir(kimlik);
      else setYukleniyor(false);
    }

    void baslat();
  }, [onerileriGetir]);

  async function ilgilendigimiSoyle(oneri: Oneri) {
    setHata(null);
    try {
      const yanit: IlgileniyorumYaniti = await ilgileniyorum(oneri.eslesme_id);
      setAcilanIsbirligi((oncekiler) => ({
        ...oncekiler,
        [oneri.eslesme_id]: yanit.isbirligi_id,
      }));
      setVeri((onceki) =>
        onceki
          ? {
              ...onceki,
              oneriler: onceki.oneriler.map((kayit) =>
                kayit.eslesme_id === oneri.eslesme_id
                  ? { ...kayit, durum: yanit.durum }
                  : kayit,
              ),
            }
          : onceki,
      );
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Eşleştirme önerileri
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          İhtiyaç kartınla eşleşen yetenek kartları, skoruyla ve neden
          önerildiğinin gerekçesiyle birlikte. Karar senin.
        </p>
      </header>

      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={() => {
            if (kurumId) void onerileriGetir(kurumId);
          }}
        />
      ) : null}

      {yukleniyor ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
          />
          Eşleşmeler hesaplanıyor…
        </p>
      ) : null}

      {!yukleniyor && !kurumId ? <KurumYok /> : null}

      {!yukleniyor && veri ? (
        <OneriListesi
          veri={veri}
          acilanIsbirligi={acilanIsbirligi}
          onIlgileniyorum={ilgilendigimiSoyle}
        />
      ) : null}

      <footer className="mt-auto flex flex-wrap gap-3 border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href="/">Ana sayfaya dön</Link>
        </Button>
        {kurumId ? (
          <Button
            type="button"
            variant="outline"
            size="lg"
            disabled={yukleniyor}
            onClick={() => void onerileriGetir(kurumId)}
          >
            Yeniden hesapla
          </Button>
        ) : null}
      </footer>
    </main>
  );
}

function KurumYok() {
  return (
    <div className="flex flex-col items-start gap-3 rounded-sm border border-kenar bg-card px-5 py-4">
      <p className="text-sm text-pretty">
        Henüz bir ihtiyaç kartın yok. Eşleştirme, Tanımlama Ajanı’yla
        oluşturduğun karttan yola çıkıyor.
      </p>
      <Button asChild size="lg">
        <Link href="/tanimlama">İhtiyaç kartı oluştur</Link>
      </Button>
    </div>
  );
}

function OneriListesi({
  veri,
  acilanIsbirligi,
  onIlgileniyorum,
}: {
  veri: Oneriler;
  acilanIsbirligi: Record<string, string>;
  onIlgileniyorum: (oneri: Oneri) => void;
}) {
  if (veri.oneriler.length === 0) {
    return (
      <div className="flex flex-col gap-2 rounded-sm border border-kenar bg-card px-5 py-4">
        <p className="text-sm text-pretty">
          Şu an eşik değerini geçen bir eşleşme yok. Eşik{" "}
          <span className="font-mono">
            %{Math.round(veri.skor_esigi * 100)}
          </span>{" "}
          — bunun altındaki kartlar gösterilmiyor, çünkü zayıf bir öneri kuruma
          da gence de vakit kaybettiriyor.
        </p>
        <p className="text-sm text-pretty text-muted-foreground">
          Havuz büyüdükçe ya da ihtiyaç kartını netleştirdikçe yeniden dene.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {veri.az_sonuc_uyarisi ? (
        <p className="rounded-sm border border-kenar bg-muted px-5 py-3 text-sm text-pretty">
          Havuz henüz küçük: {veri.oneriler.length} öneri çıktı. Bunu
          gizlemiyoruz — az sayıda aday, kötü aday demek değil.
        </p>
      ) : null}

      {veri.oneriler.map((oneri) => (
        <OneriKarti
          key={oneri.eslesme_id}
          oneri={oneri}
          isbirligiId={acilanIsbirligi[oneri.eslesme_id]}
          onIlgileniyorum={() => onIlgileniyorum(oneri)}
        />
      ))}
    </div>
  );
}

function OneriKarti({
  oneri,
  isbirligiId,
  onIlgileniyorum,
}: {
  oneri: Oneri;
  isbirligiId?: string;
  onIlgileniyorum: () => void;
}) {
  const kart = oneri.yetenek_karti;
  const kararVerildi = oneri.durum !== "onerildi";

  return (
    <BelgeKarti
      baslik={kart.rol_alani}
      altbaslik={`Deneyim: ${kart.deneyim_seviyesi}`}
      rozet={<SkorRozeti skor={oneri.skor} />}
    >
      <section className="flex flex-col gap-1.5">
        <h4 className="font-heading text-sm font-semibold text-ana">
          Neden eşleşti
        </h4>
        {oneri.gerekce_metni ? (
          <p className="text-sm text-pretty">{oneri.gerekce_metni}</p>
        ) : (
          <p className="text-sm text-pretty text-muted-foreground">
            Gerekçe metni henüz üretilemedi (dil modeli kotası). Skor ve
            sıralama bundan etkilenmiyor; yeniden hesaplayınca gerekçe de gelir.
          </p>
        )}
      </section>

      <EtiketSatiri etiket="Araçlar" degerler={kart.araclar_teknolojiler} />
      <EtiketSatiri etiket="Sektör ilgisi" degerler={kart.sektor_ilgi_alani} />

      <section className="flex flex-col gap-3">
        <h4 className="font-heading text-sm font-semibold text-ana">
          Somut çıktılar
        </h4>
        {kart.somut_ciktilar.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Bu karta henüz somut çıktı eklenmemiş.
          </p>
        ) : (
          kart.somut_ciktilar.map((cikti) => (
            <CiktiOzeti key={cikti.id} cikti={cikti} />
          ))
        )}
      </section>

      <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-4">
        {kararVerildi ? (
          <p className="text-sm text-pretty">
            <span className="font-medium">
              {DURUM_ETIKETLERI[oneri.durum] ?? oneri.durum}.
            </span>{" "}
            {isbirligiId
              ? "İş birliği kaydı açıldı; iletişim bilgileri iki taraf da onaylayınca paylaşılır."
              : "Bu eşleşme için kararını daha önce verdin."}
          </p>
        ) : (
          <>
            <Button type="button" size="lg" onClick={onIlgileniyorum}>
              İlgileniyorum
            </Button>
            <span className="text-xs text-muted-foreground">
              Ayrı bir onay adımı yok: iş birliği kaydı hemen açılır.
            </span>
          </>
        )}
      </div>
    </BelgeKarti>
  );
}
