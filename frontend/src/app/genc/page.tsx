"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
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
  type BanaGelenIlgi,
  type IsbirligiOzeti,
  banaGelenler,
  eslesmeyiKabulEt,
  eslesmeyiReddet,
  isbirliklerim,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import {
  CALISMA_MODELI_ETIKETLERI,
  DENEYIM_ETIKETLERI,
  MUSAITLIK_ETIKETLERI,
  etiketle,
  sehirEtiketi,
} from "@/lib/sabitler";

/**
 * Genç paneli (docs/faz-b-kimlik-ve-dongu.md § 7): kartlarım, kanıt
 * bekleyenler, bana gelen ilgiler (kabul et / reddet), iş birliklerim.
 *
 * Kabulden önce kurum gencin e-postasını görmez; kabul edince iki tarafın
 * e-postası açılır ve iş birliği başlar (§ 5).
 */

export default function GencPaneli() {
  return (
    <GirisKapisi roller={["genc"]}>
      <GencPaneliIcerigi />
    </GirisKapisi>
  );
}

function GencPaneliIcerigi() {
  const hesap = useGirisliHesap();
  const { tazele } = useOturum();

  const [ilgiler, setIlgiler] = useState<BanaGelenIlgi[] | null>(null);
  const [isbirlikleri, setIsbirlikleri] = useState<IsbirligiOzeti[] | null>(
    null,
  );
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      const [gelen, acik] = await Promise.all([
        banaGelenler(),
        isbirliklerim(),
      ]);
      setIlgiler(gelen);
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

  async function yanitla(ilgi: BanaGelenIlgi, kabul: boolean) {
    setHata(null);
    try {
      const yanit = kabul
        ? await eslesmeyiKabulEt(ilgi.eslesme_id)
        : await eslesmeyiReddet(ilgi.eslesme_id);
      setIlgiler((oncekiler) =>
        (oncekiler ?? []).map((kayit) =>
          kayit.eslesme_id === ilgi.eslesme_id
            ? {
                ...kayit,
                durum: yanit.durum,
                isbirligi_id: yanit.isbirligi_id,
                iletisim: yanit.iletisim,
              }
            : kayit,
        ),
      );
      if (kabul) setIsbirlikleri(await isbirliklerim());
      // İlgi bildirimi okunmuş sayılmaz ama panel güncel /me ister (kartlar).
      void tazele();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  const kartlar = hesap.yetenek_kartlari;
  const kanitBekleyenler = kartlar.filter((kart) => kart.kanit_bekleyen);
  const bekleyenIlgi =
    ilgiler?.filter((ilgi) => ilgi.durum === "ilgileniliyor").length ?? 0;

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Merhaba{hesap.ad ? `, ${hesap.ad}` : ""}
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          {bekleyenIlgi > 0
            ? `${bekleyenIlgi} kurum kartınla ilgileniyor ve yanıtını bekliyor.`
            : "Kartların, kanıtların ve sana gelen ilgiler burada."}
        </p>
      </header>

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      <PanelBolumu id="kartlar" baslik="Kartlarım">
        {kartlar.length === 0 ? (
          <BosDurum
            metin="Henüz yetenek kartın yok. Keşif Ajanı’yla kısa bir sohbet yap; ne yaptığını birlikte bir karta dönüştürelim."
            eylem={{ href: "/kesif", etiket: "Kart oluştur" }}
          />
        ) : (
          <ul className="flex flex-col divide-y divide-kenar rounded-sm border border-kenar">
            {kartlar.map((kart) => (
              <li key={kart.id}>
                <Link
                  href={`/kart/${kart.id}`}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 hover:bg-muted"
                >
                  <span className="font-medium text-ana">{kart.rol_alani}</span>
                  <span className="text-sm text-muted-foreground">
                    {etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}
                  </span>
                  <span className="ml-auto flex gap-2">
                    {kart.kanit_bekleyen ? (
                      <DurumEtiketi metin="Kanıt bekliyor" />
                    ) : null}
                    {!kart.embedding_var ? (
                      <DurumEtiketi metin="Eşleştirmeye hazır değil" />
                    ) : null}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </PanelBolumu>

      {kartlar.length > 0 ? (
        <PanelBolumu
          id="kanit"
          baslik="Kanıt bekleyenler"
          aciklama="Kanıtı olmayan çıktı kartı elemez; ama kanıt ve referans eşleşmede kartını öne çıkarır."
        >
          {kanitBekleyenler.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Tüm kartlarının çıktılarında kanıt var.
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {kanitBekleyenler.map((kart) => (
                <li
                  key={kart.id}
                  className="flex flex-wrap items-center gap-3 text-sm"
                >
                  <span>{kart.rol_alani}</span>
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/kart/${kart.id}`}>Kanıt ekle</Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </PanelBolumu>
      ) : null}

      <PanelBolumu
        id="ilgiler"
        baslik="Bana gelen ilgiler"
        aciklama="Bir kurum kartınla ilgilendiğinde burada görünür. Kabul edersen e-posta adresleriniz paylaşılır ve iş birliği açılır."
      >
        {ilgiler === null ? (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        ) : ilgiler.length === 0 ? (
          <BosDurum
            metin={
              kartlar.length === 0
                ? "İlgiler bir kartın olduğunda gelir. Önce kartını oluştur."
                : "Henüz bir kurum kartınla ilgilenmedi. Bir kurum ilgilendiğinde bildirim alırsın."
            }
            eylem={
              kartlar.length === 0
                ? { href: "/kesif", etiket: "Kart oluştur" }
                : undefined
            }
          />
        ) : (
          <ul className="flex flex-col gap-4">
            {ilgiler.map((ilgi) => (
              <IlgiKaydi
                key={ilgi.eslesme_id}
                ilgi={ilgi}
                onYanit={(kabul) => yanitla(ilgi, kabul)}
              />
            ))}
          </ul>
        )}
      </PanelBolumu>

      <PanelBolumu id="isbirlikleri" baslik="İş birliklerim">
        {isbirlikleri === null ? (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        ) : isbirlikleri.length === 0 ? (
          <BosDurum metin="Bir kurumun ilgisini kabul ettiğinde iş birliği burada açılır." />
        ) : (
          <ul className="flex flex-col gap-4">
            {isbirlikleri.map((isbirligi) => (
              <li
                key={isbirligi.isbirligi_id}
                className="flex flex-col gap-2 rounded-sm border border-kenar px-4 py-3"
              >
                <div className="flex flex-wrap items-baseline gap-x-3">
                  <span className="font-medium text-ana">
                    {isbirligi.kurum_adi}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {tarihYaz(isbirligi.baslangic_tarihi)} tarihinde başladı
                  </span>
                </div>
                <p className="text-sm text-pretty">
                  {isbirligi.problem_tanimi}
                </p>
                <IletisimSatiri
                  iletisim={isbirligi.iletisim}
                  karsiTaraf="kurum"
                />
              </li>
            ))}
          </ul>
        )}
      </PanelBolumu>
    </main>
  );
}

function IlgiKaydi({
  ilgi,
  onYanit,
}: {
  ilgi: BanaGelenIlgi;
  onYanit: (kabul: boolean) => Promise<void>;
}) {
  const ihtiyac = ilgi.ihtiyac_karti;
  const [bekleniyor, setBekleniyor] = useState(false);

  // Çift tıklamayı düğmede de kesiyoruz (backend zaten tekrarı yan etkisiz
  // karşılıyor); hata olursa düğmeler yeniden açılır.
  async function yanitVer(kabul: boolean) {
    setBekleniyor(true);
    try {
      await onYanit(kabul);
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-sm border border-kenar bg-card px-4 py-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-heading text-lg font-semibold text-ana">
          {ihtiyac.kurum.ad}
        </span>
        <span className="text-xs text-muted-foreground">
          “{ilgi.rol_alani}” kartınla · {tarihYaz(ilgi.son_aktivite_tarihi)}
        </span>
      </div>

      <p className="text-sm text-pretty">{ihtiyac.problem_tanimi}</p>
      {ihtiyac.basari_kriteri ? (
        <p className="text-sm text-pretty text-muted-foreground">
          Başarı ölçütü: {ihtiyac.basari_kriteri}
        </p>
      ) : null}
      <p className="text-xs text-muted-foreground">
        {[
          ihtiyac.sehir_tercihi ? sehirEtiketi(ihtiyac.sehir_tercihi) : null,
          ihtiyac.calisma_modeli
            ? etiketle(CALISMA_MODELI_ETIKETLERI, ihtiyac.calisma_modeli)
            : null,
          ihtiyac.musaitlik_tercihi
            ? etiketle(MUSAITLIK_ETIKETLERI, ihtiyac.musaitlik_tercihi)
            : null,
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>

      <div className="flex flex-wrap items-center gap-3 border-t border-kenar pt-3">
        {ilgi.durum === "ilgileniliyor" ? (
          <>
            <Button
              type="button"
              size="lg"
              disabled={bekleniyor}
              onClick={() => void yanitVer(true)}
            >
              Kabul et
            </Button>
            <Button
              type="button"
              size="lg"
              variant="outline"
              disabled={bekleniyor}
              onClick={() => void yanitVer(false)}
            >
              Reddet
            </Button>
            <span className="text-xs text-pretty text-muted-foreground">
              Kabul edersen e-posta adresleriniz iki tarafa açılır.
            </span>
          </>
        ) : ilgi.durum === "kabul_edildi" ? (
          <DurumEtiketi metin="Kabul ettin, iş birliği açıldı" baglanti />
        ) : (
          <DurumEtiketi metin="Reddettin" />
        )}
      </div>

      {ilgi.iletisim ? (
        <IletisimSatiri iletisim={ilgi.iletisim} karsiTaraf="kurum" />
      ) : null}
    </li>
  );
}
