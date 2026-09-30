"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { DogrulanmisFirma } from "@/components/dogrulanmis-firma";
import { OnayAlani } from "@/components/onay-alani";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import {
  BelgeKarti,
  CiktiOzeti,
  EtiketSatiri,
  PilotRozeti,
  SkorRozeti,
} from "@/components/kart";
import { IletisimSatiri } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type Oneri,
  type Oneriler,
  eslestirmeCalistir,
  eslestirmeOnerileri,
  ilgileniyorum,
  simdilikDegil,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { isbirligiTuruEtiketi } from "@/lib/firma-karti";
import { FIRMA_TURLERI } from "@/lib/firma-profil";
import {
  NEDEN_UYGUN,
  firmaDurumEtiketi,
  firmaEylemleri,
  ilgiGosterenleriAyir,
  onerininAdayAdi,
} from "@/lib/ilgi";
import { DENEYIM_ETIKETLERI, etiketle } from "@/lib/sabitler";

/**
 * Eşleştirme önerileri — kurum tarafı (docs/agent-specs.md § 3).
 *
 * Kurum "ilgileniyorum" der, genç kabul ya da red eder; iş birliği ve
 * e-postalar yalnızca kabulle açılır (docs/faz-b-kimlik-ve-dongu.md § 5).
 *
 * Skor ve gerekçe birlikte gösteriliyor — matching-algorithm.md § 6'nın
 * kararı: kuruma "şu yüzden" denmeden bir isim listesi sunulmuyor.
 *
 * Genç akışı (docs/plans/genc-akisi.md § 7.1): ilgi gösteren adaylar ayrı
 * bölümde, uyum sırası değişmeden; firma onlara "İlgileniyorum" (karşılıklı
 * ilgi, iş birliği açılır) ya da "Şimdilik değil" der. Durum etiketleri
 * docs/icerik-rehberi.md § 5.9 (lib/ilgi.ts).
 */

const DURUM_ACIKLAMALARI: Record<string, string> = {
  ilgileniliyor:
    "Gencin yanıtı bekleniyor; kabul ederse iletişim bilgileri açılır.",
  kabul_edildi: "İletişim bilgileri aşağıda.",
  reddedildi: "Bu eşleşme kapandı.",
  kapandi: "Bu aday için süreç kapandı.",
};

export default function OnerilerSayfasi() {
  return (
    <GirisKapisi roller={["kurum"]}>
      <OnerilerIcerigi />
    </GirisKapisi>
  );
}

function OnerilerIcerigi() {
  const hesap = useGirisliHesap();
  const kurumId = hesap.kurum_id;
  const kartVar = hesap.ihtiyac_kartlari.length > 0;
  // Kurum panelinden `?ihtiyac=<id>` ile gelinir; yoksa en son ihtiyaç kartı.
  const [ihtiyacKartiId, setIhtiyacKartiId] = useState<string | null>(null);
  const [veri, setVeri] = useState<Oneriler | null>(null);
  const [yukleniyor, setYukleniyor] = useState(kartVar);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  /**
   * `tazele` false: hesaplanmış listeyi okur (sayfa açılışı).
   * `tazele` true: pipeline'ı yeniden çalıştırır — skorlar güncellenir,
   * eksik gerekçeler üretilir, eskiyen öneriler düşer. Dil modeli çağrısı
   * burada olabilir, o yüzden açılışta değil yalnızca istenince.
   */
  const onerileriGetir = useCallback(
    async (kart: string | null, tazele = false) => {
      if (!kurumId) return;
      setHata(null);
      setYukleniyor(true);
      try {
        setVeri(
          await (tazele
            ? eslestirmeCalistir(kart)
            : eslestirmeOnerileri(kurumId, kart)),
        );
      } catch (sebep) {
        setHata(hatayaCevir(sebep));
      } finally {
        setYukleniyor(false);
      }
    },
    [kurumId],
  );

  useEffect(() => {
    if (okundu.current || !kartVar) return;
    okundu.current = true;
    // Adres çubuğu yalnızca tarayıcıda; okuma bağlandıktan sonra.
    const kart = new URLSearchParams(window.location.search).get("ihtiyac");
    setIhtiyacKartiId(kart);
    void onerileriGetir(kart);
  }, [kartVar, onerileriGetir]);

  async function durumuYaz(
    oneri: Oneri,
    istek: (eslesmeId: string) => ReturnType<typeof ilgileniyorum>,
  ) {
    setHata(null);
    try {
      const yanit = await istek(oneri.eslesme_id);
      setVeri((onceki) =>
        onceki
          ? {
              ...onceki,
              oneriler: onceki.oneriler.map((kayit) =>
                kayit.eslesme_id === oneri.eslesme_id
                  ? {
                      ...kayit,
                      durum: yanit.durum,
                      iletisim: yanit.iletisim,
                      isbirligi_id: yanit.isbirligi_id,
                      genc_ilgi_gosterdi: yanit.durum === "genc_ilgilendi",
                    }
                  : kayit,
              ),
            }
          : onceki,
      );
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  const ilgilendigimiSoyle = (oneri: Oneri) => durumuYaz(oneri, ilgileniyorum);

  // Onay kartın içinde sorulur (SimdilikDegilDugmesi, rehber § 5.6).
  function simdilikDegilDe(oneri: Oneri) {
    void durumuYaz(oneri, simdilikDegil);
  }

  const gosterilenKart = veri
    ? hesap.ihtiyac_kartlari.find((kart) => kart.id === veri.ihtiyac_karti_id)
    : undefined;
  // Ortak ilanının adayları firmalar (docs/plans/firma-akisi.md § 4).
  const ortak = gosterilenKart?.aranan === "firma";

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="Uygun adaylar"
        aciklama={
          ortak
            ? "İhtiyacınıza uyan firmalar, uyumuyla ve neden uygun olduklarıyla birlikte. Karar sizin."
            : "İhtiyacınıza uyan gençler, uyumuyla ve neden uygun olduklarıyla birlikte. Karar sizin."
        }
      >
        {gosterilenKart ? (
          <p className="border-l-2 border-kenar pl-3 text-sm text-pretty">
            {gosterilenKart.problem_tanimi}
          </p>
        ) : null}
      </SayfaBasligi>

      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={() => void onerileriGetir(ihtiyacKartiId)}
        />
      ) : null}

      {yukleniyor ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
          />
          Adaylar hazırlanıyor…
        </p>
      ) : null}

      {!kartVar ? <KurumYok /> : null}

      {!yukleniyor && veri ? (
        <OneriListesi
          veri={veri}
          ortak={ortak}
          onIlgileniyorum={ilgilendigimiSoyle}
          onSimdilikDegil={simdilikDegilDe}
        />
      ) : null}

      <footer className="mt-auto flex flex-wrap gap-3 border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href="/kurum">Panele dön</Link>
        </Button>
        {kartVar ? (
          <Button
            type="button"
            variant="outline"
            size="lg"
            disabled={yukleniyor}
            onClick={() =>
              void onerileriGetir(
                veri?.ihtiyac_karti_id ?? ihtiyacKartiId,
                true,
              )
            }
          >
            Yeniden hesapla
          </Button>
        ) : null}
      </footer>
    </Sayfa>
  );
}

function KurumYok() {
  return (
    <div className="flex flex-col items-start gap-3 rounded-sm border border-kenar bg-card px-5 py-4">
      <p className="text-sm text-pretty">
        Henüz bir ihtiyaç tanımlamadınız. Kısa bir sohbetle ihtiyacınızı
        netleştirin, size uygun adayları gösterelim.
      </p>
      <Button asChild size="lg">
        <Link href="/tanimlama">İhtiyacınızı tanımlayın</Link>
      </Button>
    </div>
  );
}

function OneriListesi({
  veri,
  ortak,
  onIlgileniyorum,
  onSimdilikDegil,
}: {
  veri: Oneriler;
  ortak: boolean;
  onIlgileniyorum: (oneri: Oneri) => void;
  onSimdilikDegil: (oneri: Oneri) => void;
}) {
  const { ilgiGosterenler, digerleri } = ilgiGosterenleriAyir(veri.oneriler);
  if (veri.oneriler.length === 0 && ortak) {
    return (
      <div className="flex flex-col gap-2 rounded-sm border border-kenar bg-card px-5 py-4">
        <p className="text-sm text-pretty">
          Şu an ihtiyacınıza yeterince uyan bir firma yok. Firmalar kartlarını
          oluşturdukça yeni adaylar çıkabilir.
        </p>
        <p className="text-sm text-pretty text-muted-foreground">
          İhtiyacınızdaki problemi ve başarı kriterini netleştirmek de yardımcı
          olur.
        </p>
      </div>
    );
  }
  if (veri.oneriler.length === 0) {
    return (
      <div className="flex flex-col gap-2 rounded-sm border border-kenar bg-card px-5 py-4">
        <p className="text-sm text-pretty">
          Şu an ihtiyacınıza yeterince uyan bir aday yok. Yalnızca yeterince
          uyan adayları gösteriyoruz; zayıf bir öneri iki tarafın da vaktini
          alır.
        </p>
        <p className="text-sm text-pretty text-muted-foreground">
          Yeni gençler katıldıkça ya da ihtiyacınızı netleştirdikçe yeniden
          hesaplayın.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {veri.az_sonuc_uyarisi ? (
        <p className="rounded-sm border border-kenar bg-muted px-5 py-3 text-sm text-pretty">
          Havuz henüz küçük: {veri.oneriler.length} aday çıktı. Az sayıda aday,
          kötü aday demek değil.
        </p>
      ) : null}

      {ilgiGosterenler.length > 0 ? (
        <section className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h2 className="font-heading text-xl font-semibold text-ana">
              İlgi gösterenler
            </h2>
            <p className="text-sm text-pretty text-muted-foreground">
              Bu adaylar ihtiyacınızla ilgilendiklerini bildirdi. Siz de
              ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır ve iş
              birliği başlar.
            </p>
          </div>
          {ilgiGosterenler.map((oneri) => (
            <OneriKarti
              key={oneri.eslesme_id}
              oneri={oneri}
              onIlgileniyorum={() => onIlgileniyorum(oneri)}
              onSimdilikDegil={() => onSimdilikDegil(oneri)}
            />
          ))}
        </section>
      ) : null}

      {digerleri.length > 0 && ilgiGosterenler.length > 0 ? (
        <h2 className="font-heading text-xl font-semibold text-ana">Adaylar</h2>
      ) : null}
      {digerleri.map((oneri) => (
        <OneriKarti
          key={oneri.eslesme_id}
          oneri={oneri}
          onIlgileniyorum={() => onIlgileniyorum(oneri)}
          onSimdilikDegil={() => onSimdilikDegil(oneri)}
        />
      ))}
    </div>
  );
}

function OneriKarti({
  oneri,
  onIlgileniyorum,
  onSimdilikDegil,
}: {
  oneri: Oneri;
  onIlgileniyorum: () => void;
  onSimdilikDegil: () => void;
}) {
  if (oneri.firma_karti)
    return (
      <FirmaAdayiKarti
        oneri={oneri}
        onIlgileniyorum={onIlgileniyorum}
        onSimdilikDegil={onSimdilikDegil}
      />
    );
  const kart = oneri.yetenek_karti;
  if (!kart) return null;
  const eylemler = firmaEylemleri(oneri.durum);
  const ilgiGosterdi = oneri.durum === "genc_ilgilendi";

  return (
    <BelgeKarti
      baslik={kart.rol_alani}
      altbaslik={`${kart.genc_adi} · Deneyim: ${etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}`}
      rozet={
        <span className="flex flex-wrap gap-2">
          {ilgiGosterdi ? (
            <span className="rounded-sm border border-baglanti px-2.5 py-1 text-xs text-baglanti">
              {firmaDurumEtiketi(oneri.durum)}
            </span>
          ) : null}
          <PilotRozeti sayi={kart.tamamlanan_pilot} />
          <SkorRozeti skor={oneri.skor} />
        </span>
      }
    >
      <section className="flex flex-col gap-1.5">
        <h4 className="font-heading text-sm font-semibold text-ana">
          {NEDEN_UYGUN}
        </h4>
        {oneri.gerekce_metni ? (
          <p className="text-sm text-pretty">{oneri.gerekce_metni}</p>
        ) : (
          <p className="text-sm text-pretty text-muted-foreground">
            Bu aday için açıklama henüz hazır değil. Uyum ve sıralama bundan
            etkilenmiyor; “Yeniden hesapla” ile tekrar denenir.
          </p>
        )}
      </section>

      <EtiketSatiri etiket="Araçlar" degerler={kart.araclar_teknolojiler} />
      <EtiketSatiri etiket="Sektör ilgisi" degerler={kart.sektor_ilgi_alani} />

      <section className="flex flex-col gap-3">
        <h4 className="font-heading text-sm font-semibold text-ana">
          Çalışmaları
        </h4>
        {kart.somut_ciktilar.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Bu karta henüz çalışma eklenmemiş.
          </p>
        ) : (
          kart.somut_ciktilar.map((cikti) => (
            <CiktiOzeti key={cikti.id} cikti={cikti} />
          ))
        )}
      </section>

      <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-4">
        {ilgiGosterdi ? (
          <>
            <Button type="button" size="lg" onClick={onIlgileniyorum}>
              İlgileniyorum
            </Button>
            <SimdilikDegilDugmesi
              adayAdi={onerininAdayAdi(oneri)}
              onOnayla={onSimdilikDegil}
            />
            <span className="text-xs text-pretty text-muted-foreground">
              İlgilenirseniz iletişim bilgileriniz paylaşılır ve iş birliği
              başlar.
            </span>
          </>
        ) : eylemler.ilgileniyorum ? (
          <>
            <Button type="button" size="lg" onClick={onIlgileniyorum}>
              İlgileniyorum
            </Button>
            <span className="text-xs text-muted-foreground">
              Gence bildirilir; kabul ederse iş birliği açılır ve e-postalar
              paylaşılır.
            </span>
          </>
        ) : (
          <p className="text-sm text-pretty">
            <span className="font-medium">
              {firmaDurumEtiketi(oneri.durum)}.
            </span>{" "}
            {DURUM_ACIKLAMALARI[oneri.durum] ?? ""}
            {oneri.isbirligi_id ? (
              <>
                {" "}
                <Link
                  href={`/isbirligi/${oneri.isbirligi_id}`}
                  className="text-baglanti underline"
                >
                  İş birliğine gidin
                </Link>
              </>
            ) : null}
          </p>
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

/**
 * Ortak ilanında önerilen firma (docs/plans/firma-akisi.md § 0 kararlar 8, 16-17).
 * Eylemler genç adayındakiyle aynı kurala bağlı (`firmaEylemleri`); metinler
 * karşı tarafı "firma" diye anar.
 */
function FirmaAdayiKarti({
  oneri,
  onIlgileniyorum,
  onSimdilikDegil,
}: {
  oneri: Oneri;
  onIlgileniyorum: () => void;
  onSimdilikDegil: () => void;
}) {
  const eylemler = firmaEylemleri(oneri.durum);
  const ilgiGosterdi = oneri.durum === "genc_ilgilendi";
  const firma = oneri.firma_karti;
  if (!firma) return null;
  const tur = FIRMA_TURLERI.find((t) => t.deger === firma.tur)?.etiket;
  return (
    <BelgeKarti
      baslik={firma.firma_adi}
      altbaslik={[tur, firma.sektor, firma.sehir].filter(Boolean).join(" · ")}
      rozet={
        <span className="flex flex-wrap gap-2">
          <DogrulanmisFirma dogrulandi={firma.dogrulandi} />
          {firma.tamamlanan_isbirligi > 0 ? (
            <span className="rounded-sm border border-baglanti px-2.5 py-1 text-xs text-baglanti">
              {firma.tamamlanan_isbirligi} tamamlanan iş birliği
            </span>
          ) : null}
          <SkorRozeti skor={oneri.skor} />
        </span>
      }
    >
      <section className="flex flex-col gap-1.5">
        <h4 className="font-heading text-sm font-semibold text-ana">
          {NEDEN_UYGUN}
        </h4>
        {oneri.gerekce_metni ? (
          <p className="text-sm text-pretty">{oneri.gerekce_metni}</p>
        ) : (
          <p className="text-sm text-pretty text-muted-foreground">
            Bu aday için açıklama henüz hazır değil. Uyum ve sıralama bundan
            etkilenmiyor; “Yeniden hesapla” ile tekrar denenir.
          </p>
        )}
      </section>

      <section className="flex flex-col gap-1.5">
        <h4 className="font-heading text-sm font-semibold text-ana">
          Ne yapıyor?
        </h4>
        <p className="text-sm text-pretty">{firma.ne_yapiyoruz}</p>
      </section>
      <EtiketSatiri etiket="Yetkinlikler" degerler={firma.yetkinlikler} />
      {firma.onceki_isler ? (
        <section className="flex flex-col gap-1.5">
          <h4 className="font-heading text-sm font-semibold text-ana">
            Önceki işler
          </h4>
          <p className="text-sm text-pretty">{firma.onceki_isler}</p>
        </section>
      ) : null}
      {firma.isbirligi_turleri.length > 0 ? (
        <EtiketSatiri
          etiket="İş birliği türleri"
          degerler={firma.isbirligi_turleri.map(isbirligiTuruEtiketi)}
        />
      ) : null}

      <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-4">
        {ilgiGosterdi ? (
          <>
            <Button type="button" size="lg" onClick={onIlgileniyorum}>
              İlgileniyorum
            </Button>
            <SimdilikDegilDugmesi
              adayAdi={onerininAdayAdi(oneri)}
              onOnayla={onSimdilikDegil}
            />
            <span className="text-xs text-pretty text-muted-foreground">
              İlgilenirseniz iletişim bilgileriniz paylaşılır ve iş birliği
              başlar.
            </span>
          </>
        ) : eylemler.ilgileniyorum ? (
          <>
            <Button type="button" size="lg" onClick={onIlgileniyorum}>
              İlgileniyorum
            </Button>
            <span className="text-xs text-pretty text-muted-foreground">
              Firmaya bildirilir; kabul ederse iş birliği açılır ve e-postalar
              paylaşılır.
            </span>
          </>
        ) : (
          <p className="text-sm text-pretty">
            <span className="font-medium">
              {firmaDurumEtiketi(oneri.durum)}.
            </span>{" "}
            {oneri.durum === "ilgileniliyor"
              ? "Firmanın yanıtı bekleniyor; kabul ederse iletişim bilgileri açılır."
              : oneri.durum === "kabul_edildi"
                ? "İletişim bilgileri aşağıda."
                : ""}
            {oneri.isbirligi_id ? (
              <>
                {" "}
                <Link
                  href={`/isbirligi/${oneri.isbirligi_id}`}
                  className="text-baglanti underline"
                >
                  İş birliğine gidin
                </Link>
              </>
            ) : null}
          </p>
        )}
      </div>

      {oneri.iletisim ? (
        <IletisimSatiri iletisim={oneri.iletisim} karsiTaraf="genc" />
      ) : null}
    </BelgeKarti>
  );
}

/**
 * "Şimdilik değil": onay kartın içinde (rehber § 5.6); adaya nedeni yazılmaz.
 */
function SimdilikDegilDugmesi({
  adayAdi,
  onOnayla,
}: {
  adayAdi: string;
  onOnayla: () => void;
}) {
  const [acik, setAcik] = useState(false);
  if (acik) {
    return (
      <OnayAlani
        soru={`${adayAdi} için “Şimdilik değil” denilsin mi? Adaya bu fırsatın kapandığı bildirilir; neden yazılmaz.`}
        onayEtiketi="Şimdilik değil"
        onOnayla={() => {
          setAcik(false);
          onOnayla();
        }}
        onVazgec={() => setAcik(false)}
      />
    );
  }
  return (
    <Button
      type="button"
      size="lg"
      variant="outline"
      onClick={() => setAcik(true)}
    >
      Şimdilik değil
    </Button>
  );
}
