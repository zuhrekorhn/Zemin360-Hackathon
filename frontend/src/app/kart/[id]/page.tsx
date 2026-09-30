"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import {
  IsKalemiEkleFormu,
  IsKalemiEylemleri,
  KartAlanlariFormu,
} from "@/components/kart-duzenleme";
import {
  BelgeKarti,
  CiktiOzeti,
  EtiketSatiri,
  PilotRozeti,
} from "@/components/kart";
import { KanitBolumu } from "@/components/kanit";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type KanitDurumu,
  type YetenekKartiYaniti,
  kanitDurumu,
  yetenekKartiGetir,
  yetenekKartiHazirla,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { DENEYIM_ETIKETLERI, etiketle } from "@/lib/sabitler";
import { panelYolu } from "@/lib/yonlendirme";

/**
 * Yetenek kartı + Doğrulama Ajanı ekranı (docs/agent-specs.md § 1 ve § 4).
 *
 * Kartın kendisi Keşif'te oluşuyor; burada her somut çıktıya kanıt ve
 * referans eklenip dört bileşenli güven göstergesi okunuyor. Kart sahibinin
 * e-postası hiçbir yerde gösterilmiyor (§ 1.5).
 *
 * Kimin gördüğüne göre iki hâl (docs/faz-b-kimlik-ve-dongu.md § 3):
 *   - Kartın sahibi genç: kanıt durumu, kanıt/referans ekleme, itiraz.
 *   - Kurum (kart ona önerilmişse) ve GİRVAK: kartı salt okunur görür;
 *     kanıt ayrıntısı (referans e-postaları, yanıt linkleri) kuruma hiç
 *     gitmez — rubrik zaten çıktıların güven göstergesinde.
 * Genç yalnızca kendi kartını açabildiği için "genç" rolü sahiplik demek.
 *
 * Sahibi kartı burada düzenler (docs/plans/genc-akisi.md § 6): kart alanları,
 * iş kalemi düzenle/sil/ekle. İçerik ya da link değişen işin güven göstergesi
 * sıfırlanır ve yeniden değerlendirilir; eski referans yanıtları geçmişte kalır.
 */

export default function KartSayfasi() {
  return (
    <GirisKapisi>
      <KartIcerigi />
    </GirisKapisi>
  );
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
  const okundu = useRef(false);

  const kartiGetir = useCallback(
    async (kimlik: string) => {
      setHata(null);
      setYukleniyor(true);
      try {
        const gelen = await yetenekKartiGetir(kimlik);
        setKart(gelen);
        if (!sahibi) return;

        // Zaman aşımı (bekliyor → yanit_yok) bu okuma anında hesaplanıyor;
        // ayrı bir zamanlayıcı yok (bilinçli, bkz. CLAUDE.md).
        const durumlar = await Promise.all(
          gelen.somut_ciktilar.map((cikti) => kanitDurumu(cikti.id)),
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
    // Rubrik kart görünümünde de duruyor; iki yerde farklı puan görünmesin.
    setKart((onceki) =>
      onceki
        ? {
            ...onceki,
            somut_ciktilar: onceki.somut_ciktilar.map((cikti) =>
              cikti.id === durum.somut_cikti_id
                ? {
                    ...cikti,
                    kanit_linki: durum.kanit_linki,
                    guven_skoru: durum.guven_skoru,
                  }
                : cikti,
            ),
          }
        : onceki,
    );
  }

  return (
    <Sayfa>
      <SayfaBasligi
        baslik={
          sahibi
            ? "Yetenek kartın"
            : `${kart?.genc_adi ?? "Genç"} · yetenek kartı`
        }
        aciklama={
          sahibi
            ? "Her çalışman dört açıdan değerlendirilir: kanıt, sonuç, rol ve referans. Tek bir puana indirilmez; böylece neyin güçlü, neyin eksik olduğunu görürsün."
            : "Her çalışma dört açıdan değerlendirilir: kanıt, sonuç, rol ve referans. Tek bir puana indirilmez; böylece neyin güçlü, neyin eksik olduğunu görürsünüz."
        }
      />

      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={() => {
            if (kartId) void kartiGetir(kartId);
          }}
        />
      ) : null}

      {yukleniyor ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
          />
          Kart yükleniyor…
        </p>
      ) : null}

      {!yukleniyor && kart ? (
        <>
          <BelgeKarti
            baslik={kart.rol_alani}
            altbaslik={`Deneyim: ${etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}`}
            rozet={
              <span className="flex flex-wrap gap-2">
                <PilotRozeti sayi={kart.tamamlanan_pilot} />
                {kart.kanit_bekleyen ? (
                  <span className="rounded-sm border border-kenar px-2.5 py-1 text-xs text-muted-foreground">
                    Kanıt bekliyor
                  </span>
                ) : null}
              </span>
            }
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
            {sahibi ? (
              <p className="text-xs text-muted-foreground">
                Firmalar kartını adınla ({kart.genc_adi}) birlikte böyle görür.
                E-postan yalnızca karşılıklı ilgi oluşunca o firmayla
                paylaşılır.
              </p>
            ) : null}
          </BelgeKarti>

          {kayitNotu ? (
            <p
              className="text-sm text-pretty text-muted-foreground"
              role="status"
            >
              {kayitNotu}
            </p>
          ) : null}

          {sahibi ? (
            kartDuzenleniyor ? (
              <KartAlanlariFormu
                kart={kart}
                onGuncel={duzenlendi}
                onHata={setHata}
                onKapat={() => setKartDuzenleniyor(false)}
              />
            ) : (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-fit"
                onClick={() => setKartDuzenleniyor(true)}
              >
                Kartı düzenle
              </Button>
            )
          ) : null}

          {sahibi && !kart.embedding_var ? (
            <EslestirmeyeHazirla
              hazirla={async () => {
                const guncel = await yetenekKartiHazirla(kart.id);
                // Çıktıların kanıt durumu ayrı tutuluyor; yalnızca bayrak değişti.
                setKart((onceki) =>
                  onceki
                    ? { ...onceki, embedding_var: guncel.embedding_var }
                    : onceki,
                );
              }}
            />
          ) : null}

          <section className="flex flex-col gap-6">
            <div className="flex flex-col gap-1">
              <h2 className="font-heading text-xl font-semibold text-ana">
                {sahibi ? "Çalışmaların" : "Çalışmaları"}
              </h2>
              {/* Rehber § 9.5: güven göstergesinin yapay zekâ açıklaması. */}
              <p className="text-xs text-muted-foreground">
                Kanıt, sonuç ve rol yapay zekâ desteğiyle değerlendirilir;
                referans puanını referans kişi verir.
              </p>
            </div>

            {kart.somut_ciktilar.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {sahibi
                  ? "Bu kartta henüz çalışma yok. Aşağıdan ekleyebilirsin."
                  : "Bu kartta henüz çalışma yok."}
              </p>
            ) : (
              kart.somut_ciktilar.map((cikti) => (
                <div key={cikti.id} className="flex flex-col gap-3">
                  <CiktiOzeti
                    cikti={cikti}
                    sahibiBakiyor={sahibi}
                    referansVar={
                      (kanitlar[cikti.id]?.referanslar.length ?? 0) > 0
                    }
                  />
                  {sahibi ? (
                    <IsKalemiEylemleri
                      kartId={kart.id}
                      cikti={cikti}
                      onGuncel={duzenlendi}
                      onHata={setHata}
                    />
                  ) : null}
                  {sahibi ? (
                    <KanitBolumu
                      somutCiktiId={cikti.id}
                      mevcutLink={cikti.kanit_linki}
                      durum={kanitlar[cikti.id]}
                      onDurum={kanidiGuncelle}
                      onHata={setHata}
                    />
                  ) : null}
                </div>
              ))
            )}

            {sahibi ? (
              isEkleniyor ? (
                <IsKalemiEkleFormu
                  kartId={kart.id}
                  onGuncel={duzenlendi}
                  onHata={setHata}
                  onKapat={() => setIsEkleniyor(false)}
                />
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  className="w-fit"
                  onClick={() => setIsEkleniyor(true)}
                >
                  Çalışma ekle
                </Button>
              )
            ) : null}
          </section>
        </>
      ) : null}

      <footer className="mt-auto flex flex-wrap gap-3 border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href={panelYolu(hesap.rol)}>Panele dön</Link>
        </Button>
      </footer>
    </Sayfa>
  );
}
