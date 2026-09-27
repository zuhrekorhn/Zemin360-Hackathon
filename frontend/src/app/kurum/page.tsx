"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { SkorRozeti } from "@/components/kart";
import {
  BosDurum,
  DurumEtiketi,
  IletisimSatiri,
  PanelBolumu,
  tarihYaz,
} from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type IsbirligiOzeti,
  type KurumOnerisi,
  isbirliklerim,
  onerilerim,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { ISBIRLIGI_DURUM_ETIKETLERI, ilerlemeMetni } from "@/lib/takip";

/**
 * Kurum paneli (docs/faz-b-kimlik-ve-dongu.md § 7): ihtiyaç kartlarım (her
 * biri kendi önerilerine gider), önerilerim (durumları ve gencin adıyla),
 * iş birliklerim (e-postalarla).
 *
 * Panel yalnızca okur; eşleştirmeyi çalıştırmak (dil modeli çağrısı olabilir)
 * öneriler sayfasının işi.
 */

const DURUMLAR: Record<string, { metin: string; baglanti?: boolean }> = {
  onerildi: { metin: "Önerildi" },
  ilgileniliyor: { metin: "Gencin yanıtı bekleniyor" },
  kabul_edildi: { metin: "Kabul edildi", baglanti: true },
  reddedildi: { metin: "Aday şu an kabul etmedi" },
};

export default function KurumPaneli() {
  return (
    <GirisKapisi roller={["kurum"]}>
      <KurumPaneliIcerigi />
    </GirisKapisi>
  );
}

function KurumPaneliIcerigi() {
  const hesap = useGirisliHesap();
  const [oneriler, setOneriler] = useState<KurumOnerisi[] | null>(null);
  const [isbirlikleri, setIsbirlikleri] = useState<IsbirligiOzeti[] | null>(
    null,
  );
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      const [gelen, acik] = await Promise.all([onerilerim(), isbirliklerim()]);
      setOneriler(gelen);
      setIsbirlikleri(acik);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  const kartlar = hesap.ihtiyac_kartlari;

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          {hesap.ad ?? "Kurum paneli"}
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          İhtiyaç kartların, önerilerin ve açılan iş birliklerin burada.
        </p>
      </header>

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      <PanelBolumu id="ihtiyaclar" baslik="İhtiyaç kartlarım">
        {kartlar.length === 0 ? (
          <BosDurum
            metin="Henüz ihtiyaç kartın yok. Tanımlama Ajanı’yla kısa bir sohbet yap; ihtiyacını ölçülebilir bir karta çevirelim."
            eylem={{ href: "/tanimlama", etiket: "İhtiyaç kartı oluştur" }}
          />
        ) : (
          <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
            {kartlar.map((kart) => (
              <li
                key={kart.id}
                className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:gap-4"
              >
                <div className="flex flex-1 flex-col gap-1">
                  <span className="text-sm text-pretty">
                    {kart.problem_tanimi}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {tarihYaz(kart.olusturma_tarihi)}
                    {!kart.embedding_var ? " · eşleştirmeye hazır değil" : null}
                  </span>
                </div>
                <Button asChild size="sm" className="w-fit shrink-0">
                  <Link href={`/kurum/oneriler?ihtiyac=${kart.id}`}>
                    Önerileri gör
                  </Link>
                </Button>
              </li>
            ))}
          </ul>
        )}
      </PanelBolumu>

      <PanelBolumu
        id="oneriler"
        baslik="Önerilerim"
        aciklama="Tüm ihtiyaç kartlarından; en son hareket olan önce. İlgini bir ihtiyaç kartının öneriler sayfasından bildirirsin."
      >
        {oneriler === null ? (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        ) : oneriler.length === 0 ? (
          <BosDurum
            metin={
              kartlar.length === 0
                ? "Öneriler bir ihtiyaç kartından çıkar. Önce kartını oluştur."
                : "Henüz öneri yok. Bir ihtiyaç kartının önerilerini açtığında eşleştirme çalışır ve adaylar burada da listelenir."
            }
            eylem={
              kartlar.length === 0
                ? { href: "/tanimlama", etiket: "İhtiyaç kartı oluştur" }
                : {
                    href: `/kurum/oneriler?ihtiyac=${kartlar[0].id}`,
                    etiket: "Önerileri gör",
                  }
            }
          />
        ) : (
          <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
            {oneriler.map((oneri) => {
              const durum = DURUMLAR[oneri.durum] ?? { metin: oneri.durum };
              return (
                <li
                  key={oneri.eslesme_id}
                  className="flex flex-col gap-2 px-4 py-3"
                >
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <Link
                      href={`/kart/${oneri.yetenek_karti_id}`}
                      className="font-medium text-ana underline-offset-4 hover:underline"
                    >
                      {oneri.genc_adi}
                    </Link>
                    <span className="text-sm text-muted-foreground">
                      {oneri.rol_alani}
                    </span>
                    <span className="ml-auto flex items-center gap-2">
                      <DurumEtiketi
                        metin={durum.metin}
                        baglanti={durum.baglanti}
                      />
                      <SkorRozeti skor={oneri.skor} />
                    </span>
                  </div>
                  <p className="line-clamp-1 text-xs text-muted-foreground">
                    {oneri.problem_tanimi}
                  </p>
                  {oneri.durum === "onerildi" ? (
                    <Link
                      href={`/kurum/oneriler?ihtiyac=${oneri.ihtiyac_karti_id}`}
                      className="w-fit text-sm text-baglanti underline"
                    >
                      Gerekçeyi oku, ilgini bildir
                    </Link>
                  ) : null}
                  {oneri.iletisim ? (
                    <IletisimSatiri
                      iletisim={oneri.iletisim}
                      karsiTaraf="genc"
                    />
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </PanelBolumu>

      <PanelBolumu id="isbirlikleri" baslik="İş birliklerim">
        {isbirlikleri === null ? (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        ) : isbirlikleri.length === 0 ? (
          <BosDurum metin="Bir genç ilgini kabul ettiğinde iş birliği burada açılır ve e-postası görünür." />
        ) : (
          <ul className="flex flex-col gap-4">
            {isbirlikleri.map((isbirligi) => (
              <li
                key={isbirligi.isbirligi_id}
                className="flex flex-col gap-2 rounded-sm border border-kenar px-4 py-3"
              >
                <div className="flex flex-wrap items-baseline gap-x-3">
                  <span className="font-medium text-ana">
                    {isbirligi.genc_adi}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {isbirligi.rol_alani}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {tarihYaz(isbirligi.baslangic_tarihi)} tarihinde başladı
                  </span>
                </div>
                <p className="line-clamp-2 text-sm text-pretty">
                  {isbirligi.problem_tanimi}
                </p>
                <IletisimSatiri
                  iletisim={isbirligi.iletisim}
                  karsiTaraf="genc"
                />
                <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-2">
                  <DurumEtiketi
                    metin={
                      ISBIRLIGI_DURUM_ETIKETLERI[isbirligi.durum] ??
                      isbirligi.durum
                    }
                    baglanti={isbirligi.durum === "tamamlandi"}
                  />
                  <span className="text-xs text-muted-foreground">
                    {ilerlemeMetni(isbirligi.durum, isbirligi.ilerleme)}
                  </span>
                  <Button
                    asChild
                    size="sm"
                    variant="outline"
                    className="ml-auto"
                  >
                    <Link href={`/isbirligi/${isbirligi.isbirligi_id}`}>
                      {isbirligi.durum === "plan_bekliyor"
                        ? "Planı gör"
                        : "İş birliğini aç"}
                    </Link>
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </PanelBolumu>
    </main>
  );
}
