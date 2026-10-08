"use client";

import { Plus } from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { CalismaKarti } from "@/components/calisma-karti";
import { CalismaTercihleri } from "@/components/calisma-tercihleri";
import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { GuclendirPaneli } from "@/components/guclendir-paneli";
import {
  BelgeKarti,
  CiktiOzeti,
  EtiketSatiri,
  PilotRozeti,
} from "@/components/kart";
import {
  IsKalemiEkleFormu,
  KartAlanlariFormu,
} from "@/components/kart-duzenleme";
import {
  BasliklarAciklamasi,
  KartDurumuKutusu,
  KimlikKutusu,
  SiradakiAdimBandi,
} from "@/components/kart-yan-sutunu";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { YanPanel } from "@/components/ui/yan-panel";
import {
  type KanitDurumu,
  type YetenekKartiYaniti,
  kalemDurumu,
  yetenekKartiGetir,
  yetenekKartiHazirla,
} from "@/lib/api";
import { eksikler, kartinSiradakiAdimi } from "@/lib/calisma";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { DENEYIM_ETIKETLERI, etiketle } from "@/lib/sabitler";

/**
 * Yetenek kartı ve güven göstergesi (docs/agent-specs.md § 1 ve § 4).
 *
 * Kimin gördüğüne göre iki hâl (docs/kimlik-ve-dongu.md § 3):
 *   - Kartın sahibi genç (docs/kararlar.md G18): iki sütun. Solda kimlik,
 *     kartın durumu (eksik sayımı, puan değil), çalışma tercihleri; sağda
 *     sayfa düzeyinde tek "Sıradaki adım" bandı ve çalışmalar. Bir çalışmanın
 *     bütün eksikleri sağdan açılan "Güçlendir" panelinde adım adım.
 *   - Firma (kart ona önerilmişse) ve GİRVAK: kartı salt okunur görür;
 *     kanıt ayrıntısı (referans e-postaları, yanıt linkleri) firmaya hiç
 *     gitmez, güven göstergesi çalışmaların üzerinde.
 * Genç yalnızca kendi kartını açabildiği için "genç" rolü sahiplik demek.
 * Kart sahibinin e-postası hiçbir yerde gösterilmez (§ 1.5).
 */

export default function KartSayfasi() {
  return (
    <GirisKapisi>
      <KartIcerigi />
    </GirisKapisi>
  );
}

/** Ana sayfadan gelen "#guclendir-<çalışma>" bağlantısı hangi paneli açsın. */
function adrestekiCalisma(): string | null {
  if (typeof window === "undefined") return null;
  const eslesme = window.location.hash.match(/^#guclendir-(.+)$/);
  return eslesme ? eslesme[1] : null;
}

function KartIcerigi() {
  const parametreler = useParams<{ id: string }>();
  const kartId = parametreler.id;
  const hesap = useGirisliHesap();
  const sahibi = hesap.rol === "genc";

  const [kart, setKart] = useState<YetenekKartiYaniti | null>(null);
  // Çıktı başına kanıt durumu: referans listesi ve zaman aşımı yalnızca
  // /dogrulama/kanit/{id} yanıtında var (kart görünümü rubriği taşıyor,
  // referansları taşımıyor).
  const [kanitlar, setKanitlar] = useState<Record<string, KanitDurumu>>({});
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<Hata | null>(null);
  const [kartDuzenleniyor, setKartDuzenleniyor] = useState(false);
  const [isEkleniyor, setIsEkleniyor] = useState(false);
  const [kayitNotu, setKayitNotu] = useState<string | null>(null);
  // Sayfa giriş kapısından sonra istemcide çizildiği için adres okunabilir.
  const [panelCikti, setPanelCikti] = useState<string | null>(adrestekiCalisma);
  const okundu = useRef(false);

  const kartiGetir = useCallback(
    async (kimlik: string) => {
      setHata(null);
      try {
        const gelen = await yetenekKartiGetir(kimlik);
        setKart(gelen);
        if (!sahibi) return;

        // Zaman aşımı (bekliyor → yanit_yok) bu okuma anında hesaplanıyor;
        // ayrı bir zamanlayıcı yok (bilinçli, bkz. CLAUDE.md).
        const durumlar = await Promise.all(
          gelen.somut_ciktilar.map((cikti) => kalemDurumu(cikti.id)),
        );
        setKanitlar(
          Object.fromEntries(
            durumlar.map((durum) => [durum.somut_cikti_id, durum]),
          ),
        );
      } catch (sebep) {
        setHata(hatayaCevir(sebep));
      } finally {
        setYukleniyor(false);
      }
    },
    [sahibi],
  );

  useEffect(() => {
    if (okundu.current || !kartId) return;
    okundu.current = true;
    void kartiGetir(kartId);
  }, [kartId, kartiGetir]);

  /** Düzenleme sonrası: kanıt durumları (referans geçmişi dahil) da değişmiş olabilir. */
  function duzenlendi(_kart: YetenekKartiYaniti, not?: string) {
    setKayitNotu(not ?? "Kaydedildi.");
    if (kartId) void kartiGetir(kartId);
  }

  function kanidiGuncelle(durum: KanitDurumu) {
    setKanitlar((oncekiler) => ({
      ...oncekiler,
      [durum.somut_cikti_id]: durum,
    }));
    // Gösterge ve kanıtlar kart görünümünde de duruyor; iki yerde farklı
    // görünmesin. "Kanıt bekliyor" rozeti de yanıttan güncellenir.
    setKart((onceki) =>
      onceki
        ? {
            ...onceki,
            kanit_bekleyen: durum.kart_kanit_bekleyen,
            somut_ciktilar: onceki.somut_ciktilar.map((cikti) =>
              cikti.id === durum.somut_cikti_id
                ? {
                    ...cikti,
                    kanitlar: durum.kanitlar,
                    guven_skoru: durum.guven_skoru,
                  }
                : cikti,
            ),
          }
        : onceki,
    );
  }

  if (!sahibi) {
    return (
      <FirmaGorunumu
        kart={kart}
        yukleniyor={yukleniyor}
        hata={hata}
        tekrarDene={() => kartId && void kartiGetir(kartId)}
      />
    );
  }

  if (yukleniyor || !kart) {
    return (
      <Sayfa genislik="genis">
        {hata ? (
          <HataKutusu
            hata={hata}
            tekrarDene={() => kartId && void kartiGetir(kartId)}
          />
        ) : (
          <p className="text-sm text-muted-foreground" role="status">
            Kart yükleniyor…
          </p>
        )}
      </Sayfa>
    );
  }

  const calismalar = kart.somut_ciktilar.map((cikti) => {
    const durum = kanitlar[cikti.id];
    return {
      id: cikti.id,
      baslik: cikti.baslik,
      eksikler: eksikler({
        kanitSayisi: (durum?.kanitlar ?? cikti.kanitlar).length,
        referansSayisi: durum?.referanslar.length ?? 0,
        skor: durum?.guven_skoru ?? cikti.guven_skoru,
      }),
    };
  });
  const kartAdimi = kartinSiradakiAdimi(calismalar);
  const paneldeki = kart.somut_ciktilar.find((c) => c.id === panelCikti);

  return (
    <Sayfa genislik="genis">
      <h1 className="sr-only">Yetenek kartın</h1>
      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={() => kartId && void kartiGetir(kartId)}
        />
      ) : null}

      <div className="grid items-start gap-8 lg:grid-cols-[19rem_minmax(0,1fr)]">
        <aside
          aria-label="Kartın"
          className="flex flex-col gap-4 lg:sticky lg:top-24"
        >
          <KimlikKutusu
            kart={kart}
            onDuzenle={() => setKartDuzenleniyor(true)}
          />
          <KartDurumuKutusu calismalar={calismalar} onSec={setPanelCikti} />
          <CalismaTercihleri />
          <BasliklarAciklamasi />
        </aside>

        <div className="flex min-w-0 flex-col gap-6">
          {kartAdimi ? (
            <SiradakiAdimBandi
              adim={kartAdimi}
              onAc={() => setPanelCikti(kartAdimi.ciktiId)}
            />
          ) : null}

          {!kart.embedding_var ? (
            <EslestirmeyeHazirla
              hazirla={async () => {
                const guncel = await yetenekKartiHazirla(kart.id);
                setKart((onceki) =>
                  onceki
                    ? { ...onceki, embedding_var: guncel.embedding_var }
                    : onceki,
                );
              }}
            />
          ) : null}

          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-1">
              <h2 className="font-heading text-3xl font-semibold text-ana">
                Çalışmaların
              </h2>
              <p className="text-sm text-pretty text-muted-foreground">
                Her çalışma dört açıdan değerlendirilir. Güçlendirmek için
                çalışmanın üzerindeki düğmeyi kullan.
              </p>
            </div>
            <Button
              type="button"
              size="lg"
              className="px-4"
              onClick={() => setIsEkleniyor(true)}
            >
              <Plus aria-hidden="true" />
              Çalışma ekle
            </Button>
          </div>

          {kayitNotu ? (
            <p
              className="rounded-lg bg-baglanti/10 px-4 py-2.5 text-sm text-pretty text-ana"
              role="status"
            >
              {kayitNotu}
            </p>
          ) : null}

          {kart.somut_ciktilar.length === 0 ? (
            <div className="flex flex-col items-start gap-3 rounded-xl border border-dashed border-kenar px-6 py-8">
              <p className="font-heading text-lg font-semibold text-ana">
                Kartında henüz çalışma yok
              </p>
              <p className="text-sm text-pretty text-muted-foreground">
                Yaptığın bir işi ekle; kanıt ve referansla güçlendirdikçe
                fırsatlarda öne çıkarsın.
              </p>
            </div>
          ) : (
            kart.somut_ciktilar.map((cikti) => (
              <CalismaKarti
                key={cikti.id}
                kartId={kart.id}
                cikti={cikti}
                durum={kanitlar[cikti.id]}
                onGuclendir={() => setPanelCikti(cikti.id)}
                onGuncel={duzenlendi}
                onHata={setHata}
              />
            ))
          )}
        </div>
      </div>

      {paneldeki ? (
        <GuclendirPaneli
          acik
          onKapat={() => setPanelCikti(null)}
          kartId={kart.id}
          cikti={paneldeki}
          durum={kanitlar[paneldeki.id]}
          onDurum={kanidiGuncelle}
          onGuncel={duzenlendi}
          onHata={setHata}
        />
      ) : null}

      <YanPanel
        acik={isEkleniyor}
        onKapat={() => setIsEkleniyor(false)}
        ust="Kartına ekle"
        baslik="Yeni çalışma"
        alt="Yaptığın bir işi anlat. Kanıt ve referansı kaydettikten sonra Güçlendir'den eklersin."
      >
        <IsKalemiEkleFormu
          kartId={kart.id}
          onGuncel={duzenlendi}
          onHata={setHata}
          onKapat={() => setIsEkleniyor(false)}
        />
      </YanPanel>

      <YanPanel
        acik={kartDuzenleniyor}
        onKapat={() => setKartDuzenleniyor(false)}
        ust="Kartını düzenle"
        baslik={kart.rol_alani}
        alt="Rol, deneyim, araçlar ve ilgi alanların. Kaydedince kartın fırsatlarla yeniden eşleşir."
      >
        <KartAlanlariFormu
          kart={kart}
          onGuncel={duzenlendi}
          onHata={setHata}
          onKapat={() => setKartDuzenleniyor(false)}
        />
      </YanPanel>
    </Sayfa>
  );
}

/** Firma ve GİRVAK: kartı salt okunur görür. */
function FirmaGorunumu({
  kart,
  yukleniyor,
  hata,
  tekrarDene,
}: {
  kart: YetenekKartiYaniti | null;
  yukleniyor: boolean;
  hata: Hata | null;
  tekrarDene: () => void;
}) {
  return (
    <Sayfa>
      <SayfaBasligi
        baslik={`${kart?.genc_adi ?? "Genç"} · yetenek kartı`}
        aciklama="Her çalışma dört açıdan değerlendirilir: kanıt, sonuç, rol ve referans. Tek bir puana indirilmez; böylece neyin güçlü, neyin eksik olduğunu görürsünüz."
      />
      {hata ? <HataKutusu hata={hata} tekrarDene={tekrarDene} /> : null}
      {yukleniyor ? (
        <p className="text-sm text-muted-foreground" role="status">
          Kart yükleniyor…
        </p>
      ) : null}
      {!yukleniyor && kart ? (
        <>
          <BelgeKarti
            baslik={kart.rol_alani}
            altbaslik={`Deneyim: ${etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}`}
            rozet={<PilotRozeti sayi={kart.tamamlanan_pilot} />}
          >
            <EtiketSatiri
              etiket="Araçlar"
              degerler={kart.araclar_teknolojiler}
            />
            <EtiketSatiri
              etiket="Sektör ilgisi"
              degerler={kart.sektor_ilgi_alani}
            />
            <EtiketSatiri etiket="Sertifikalar" degerler={kart.sertifikalar} />
            <EtiketSatiri etiket="Diller" degerler={kart.diller} />
          </BelgeKarti>
          <section className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <h2 className="font-heading text-xl font-semibold text-ana">
                Çalışmaları
              </h2>
              {/* Rehber § 9.5: güven göstergesinin yapay zekâ açıklaması. */}
              <p className="text-xs text-muted-foreground">
                Kanıt, sonuç ve rol yapay zekâ desteğiyle değerlendirilir;
                referans puanını referans kişi verir.
              </p>
            </div>
            {kart.somut_ciktilar.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Bu kartta henüz çalışma yok.
              </p>
            ) : (
              kart.somut_ciktilar.map((cikti) => (
                <CiktiOzeti key={cikti.id} cikti={cikti} kartId={kart.id} />
              ))
            )}
          </section>
        </>
      ) : null}
    </Sayfa>
  );
}
