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
  type Oneri,
  type Oneriler,
  eslestirmeCalistir,
  eslestirmeOnerileri,
  ilgileniyorum,
  me,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { DENEYIM_ETIKETLERI, etiketle } from "@/lib/sabitler";

/**
 * Eşleştirme önerileri — kurum tarafı (docs/agent-specs.md § 3).
 *
 * Kurum "ilgileniyorum" der, genç kabul ya da red eder; iş birliği ve
 * e-postalar yalnızca kabulle açılır (docs/faz-b-kimlik-ve-dongu.md § 5).
 *
 * Skor ve gerekçe birlikte gösteriliyor — matching-algorithm.md § 6'nın
 * kararı: kuruma "şu yüzden" denmeden bir isim listesi sunulmuyor.
 */

const DURUM_ETIKETLERI: Record<string, string> = {
  onerildi: "Önerildi",
  ilgileniliyor: "İlgini bildirdin",
  kabul_edildi: "Kabul edildi, iş birliği açıldı",
  reddedildi: "Aday şu an kabul etmedi",
};

const DURUM_ACIKLAMALARI: Record<string, string> = {
  ilgileniliyor:
    "Gencin yanıtı bekleniyor; kabul ederse iletişim bilgileri açılır.",
  kabul_edildi: "İletişim bilgileri aşağıda.",
  reddedildi: "Bu eşleşme kapandı.",
};

export default function OnerilerSayfasi() {
  const [kurumId, setKurumId] = useState<string | null>(null);
  const [veri, setVeri] = useState<Oneriler | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  /**
   * `tazele` false: hesaplanmış listeyi okur (sayfa açılışı).
   * `tazele` true: pipeline'ı yeniden çalıştırır — skorlar güncellenir,
   * eksik gerekçeler üretilir, eskiyen öneriler düşer. Dil modeli çağrısı
   * burada olabilir, o yüzden açılışta değil yalnızca istenince.
   */
  const onerileriGetir = useCallback(async (kimlik: string, tazele = false) => {
    setHata(null);
    setYukleniyor(true);
    try {
      setVeri(
        await (tazele ? eslestirmeCalistir() : eslestirmeOnerileri(kimlik)),
      );
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setYukleniyor(false);
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;

    // Kurum kimliği token'daki hesaptan (/me); başka kurumun önerileri
    // backend'de 404. Token yalnızca tarayıcıda olduğu için okuma render
    // sırasında değil, bağlandıktan sonra yapılıyor.
    async function baslat() {
      let kimlik: string | null = null;
      try {
        kimlik = (await me()).kurum_id;
      } catch (sebep) {
        setHata(hatayaCevir(sebep));
      }
      setKurumId(kimlik);

      if (kimlik) await onerileriGetir(kimlik);
      else setYukleniyor(false);
    }

    void baslat();
  }, [onerileriGetir]);

  async function ilgilendigimiSoyle(oneri: Oneri) {
    setHata(null);
    try {
      const yanit = await ilgileniyorum(oneri.eslesme_id);
      setVeri((onceki) =>
        onceki
          ? {
              ...onceki,
              oneriler: onceki.oneriler.map((kayit) =>
                kayit.eslesme_id === oneri.eslesme_id
                  ? { ...kayit, durum: yanit.durum, iletisim: yanit.iletisim }
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

      {!yukleniyor && !kurumId && !hata ? <KurumYok /> : null}

      {!yukleniyor && veri ? (
        <OneriListesi veri={veri} onIlgileniyorum={ilgilendigimiSoyle} />
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
            onClick={() => void onerileriGetir(kurumId, true)}
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
  onIlgileniyorum,
}: {
  veri: Oneriler;
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
          onIlgileniyorum={() => onIlgileniyorum(oneri)}
        />
      ))}
    </div>
  );
}

function OneriKarti({
  oneri,
  onIlgileniyorum,
}: {
  oneri: Oneri;
  onIlgileniyorum: () => void;
}) {
  const kart = oneri.yetenek_karti;
  const kararVerildi = oneri.durum !== "onerildi";

  return (
    <BelgeKarti
      baslik={kart.rol_alani}
      altbaslik={`${kart.genc_adi} · Deneyim: ${etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}`}
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
            Bu öneri için henüz güvenilir bir gerekçe metni yok. Skor ve
            sıralama bundan etkilenmiyor; yeniden hesaplayınca gerekçe tekrar
            denenir.
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
            {DURUM_ACIKLAMALARI[oneri.durum] ?? ""}
          </p>
        ) : (
          <>
            <Button type="button" size="lg" onClick={onIlgileniyorum}>
              İlgileniyorum
            </Button>
            <span className="text-xs text-muted-foreground">
              Gence bildirilir; kabul ederse iş birliği açılır ve e-postalar
              paylaşılır.
            </span>
          </>
        )}
      </div>

      {oneri.iletisim ? (
        <dl className="grid gap-1 text-sm sm:grid-cols-[auto_1fr] sm:gap-x-4">
          <dt className="text-muted-foreground">Gencin e-postası</dt>
          <dd className="break-all">
            <a
              className="text-baglanti underline"
              href={`mailto:${oneri.iletisim.genc_email}`}
            >
              {oneri.iletisim.genc_email}
            </a>
          </dd>
        </dl>
      ) : null}
    </BelgeKarti>
  );
}
